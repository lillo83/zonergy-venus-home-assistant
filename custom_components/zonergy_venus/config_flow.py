"""Config flow for Zonergy Venus."""

from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol
from aioesphomeapi import (
    APIClient,
    APIConnectionError,
    InvalidAuthAPIError,
    InvalidEncryptionKeyAPIError,
)
from aioesphomeapi.model import DeviceInfo, EntityInfo
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .cloud_api import (
    ZonergyCloudApi,
    ZonergyCloudAuthError,
    ZonergyCloudConnectionError,
    ZonergyCloudDevice,
    ZonergyCloudError,
)
from .const import (
    CONF_CONNECTION_TYPE,
    CONF_DEVICE_ID,
    CONF_DEVICE_SN,
    CONF_ENCRYPTION_KEY,
    CONF_INVERTER_MODEL,
    CONF_PLANT_ID,
    CONF_PLANT_NAME,
    CONF_REGISTER_DEVICE_ID,
    CONNECTION_CLOUD,
    CONNECTION_ESPHOME,
    DEFAULT_PORT,
    DOMAIN,
    REQUIRED_ENTITY_NAMES,
)


class CannotConnect(Exception):
    """Raised when the ESPHome gateway cannot be reached."""


class InvalidGateway(Exception):
    """Raised when the ESPHome node is not the Zonergy companion firmware."""


async def async_validate_input(
    data: dict[str, Any],
) -> tuple[DeviceInfo, list[EntityInfo]]:
    """Connect and validate the ESPHome entity set."""
    client = APIClient(
        data[CONF_HOST],
        data[CONF_PORT],
        password=data.get(CONF_PASSWORD) or None,
        client_info="Zonergy Venus Home Assistant setup",
        noise_psk=data.get(CONF_ENCRYPTION_KEY) or None,
    )
    try:
        async with asyncio.timeout(15):
            await client.connect(login=True)
            device_info, entities, _ = await client.device_info_and_list_entities()
    except (InvalidAuthAPIError, InvalidEncryptionKeyAPIError):
        raise
    except (APIConnectionError, TimeoutError) as err:
        raise CannotConnect from err
    finally:
        await client.disconnect(force=True)

    names = {entity.name for entity in entities}
    if not REQUIRED_ENTITY_NAMES.issubset(names):
        raise InvalidGateway
    return device_info, entities


class ZonergyVenusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle setup for an ESPHome gateway or Zonergy cloud."""

    VERSION = 1

    def __init__(self) -> None:
        self._cloud_credentials: dict[str, str] = {}
        self._cloud_devices: dict[str, ZonergyCloudDevice] = {}
        self._reauth_entry: config_entries.ConfigEntry | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ZonergyVenusOptionsFlow:
        """Return the cloud options flow."""
        return ZonergyVenusOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user choose the connection method."""
        return self.async_show_menu(
            step_id="user", menu_options=[CONNECTION_ESPHOME, CONNECTION_CLOUD]
        )

    async def async_step_esphome(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure the local ESPHome RS485 gateway."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                device_info, _ = await async_validate_input(user_input)
            except (InvalidAuthAPIError, InvalidEncryptionKeyAPIError):
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidGateway:
                errors["base"] = "invalid_gateway"
            else:
                unique_id = device_info.mac_address.replace(":", "").lower()
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured(
                    updates={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PORT: user_input[CONF_PORT],
                    }
                )
                clean_data = dict(user_input)
                clean_data[CONF_CONNECTION_TYPE] = CONNECTION_ESPHOME
                clean_data[CONF_PASSWORD] = clean_data.get(CONF_PASSWORD, "")
                clean_data[CONF_ENCRYPTION_KEY] = clean_data.get(
                    CONF_ENCRYPTION_KEY, ""
                )
                title = device_info.friendly_name or device_info.name
                return self.async_create_entry(
                    title=title or "Zonergy Venus", data=clean_data
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): selector.TextSelector(),
                vol.Required(CONF_PORT, default=DEFAULT_PORT): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=65535,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(CONF_ENCRYPTION_KEY, default=""): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
                vol.Optional(CONF_PASSWORD, default=""): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
            }
        )
        return self.async_show_form(
            step_id="esphome", data_schema=schema, errors=errors
        )

    async def async_step_cloud(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Authenticate and discover the user's cloud inverters."""
        errors: dict[str, str] = {}
        if user_input is not None:
            api = ZonergyCloudApi(
                async_get_clientsession(self.hass),
                account=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
            )
            try:
                devices = await api.async_discover_devices()
            except ZonergyCloudAuthError:
                errors["base"] = "invalid_cloud_auth"
            except (ZonergyCloudConnectionError, ZonergyCloudError):
                errors["base"] = "cannot_connect_cloud"
            else:
                if not devices:
                    errors["base"] = "no_cloud_devices"
                else:
                    self._cloud_credentials = {
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    }
                    self._cloud_devices = {
                        f"{device.plant_id}:{device.device_id}": device
                        for device in devices
                    }
                    if len(devices) == 1:
                        return await self._async_create_cloud_entry(devices[0])
                    return await self.async_step_cloud_device()

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): selector.TextSelector(),
                vol.Required(CONF_PASSWORD): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
            }
        )
        return self.async_show_form(step_id="cloud", data_schema=schema, errors=errors)

    async def async_step_cloud_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select one inverter when the account contains several."""
        if user_input is not None:
            return await self._async_create_cloud_entry(
                self._cloud_devices[user_input[CONF_DEVICE_ID]]
            )

        options = [
            selector.SelectOptionDict(
                value=value,
                label=f"{device.plant_name} — {device.model}",
            )
            for value, device in self._cloud_devices.items()
        ]
        return self.async_show_form(
            step_id="cloud_device",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_ID): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=options)
                    )
                }
            ),
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Start reauthentication after Zonergy rejects saved credentials."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Validate and save replacement Zonergy credentials."""
        assert self._reauth_entry is not None
        errors: dict[str, str] = {}

        if user_input is not None:
            api = ZonergyCloudApi(
                async_get_clientsession(self.hass),
                account=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
            )
            try:
                devices = await api.async_discover_devices()
            except ZonergyCloudAuthError:
                errors["base"] = "invalid_cloud_auth"
            except (ZonergyCloudConnectionError, ZonergyCloudError):
                errors["base"] = "cannot_connect_cloud"
            else:
                serial = self._reauth_entry.data[CONF_DEVICE_SN]
                device = next(
                    (item for item in devices if item.serial_number == serial), None
                )
                if device is None:
                    errors["base"] = "cloud_device_missing"
                else:
                    return self.async_update_reload_and_abort(
                        self._reauth_entry,
                        data_updates={
                            CONF_USERNAME: user_input[CONF_USERNAME],
                            CONF_PASSWORD: user_input[CONF_PASSWORD],
                            CONF_PLANT_ID: device.plant_id,
                            CONF_PLANT_NAME: device.plant_name,
                            CONF_DEVICE_ID: device.device_id,
                            CONF_INVERTER_MODEL: device.model,
                            CONF_REGISTER_DEVICE_ID: device.register_device_id,
                        },
                        reason="reauth_successful",
                    )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=self._reauth_entry.data[CONF_USERNAME],
                    ): selector.TextSelector(),
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def _async_create_cloud_entry(self, device: ZonergyCloudDevice) -> FlowResult:
        """Create a read-only cloud config entry."""
        await self.async_set_unique_id(f"cloud_{device.serial_number}")
        self._abort_if_unique_id_configured()
        data: dict[str, Any] = {
            **self._cloud_credentials,
            CONF_CONNECTION_TYPE: CONNECTION_CLOUD,
            CONF_PLANT_ID: device.plant_id,
            CONF_PLANT_NAME: device.plant_name,
            CONF_DEVICE_ID: device.device_id,
            CONF_DEVICE_SN: device.serial_number,
            CONF_INVERTER_MODEL: device.model,
            CONF_REGISTER_DEVICE_ID: device.register_device_id,
        }
        return self.async_create_entry(
            title=f"{device.plant_name} — {device.model}", data=data
        )


class ZonergyVenusOptionsFlow(config_entries.OptionsFlow):
    """Configure optional cloud register access."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Set the original Wi-Fi dongle serial number."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(
            CONF_REGISTER_DEVICE_ID,
            self.config_entry.data.get(CONF_REGISTER_DEVICE_ID, ""),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_REGISTER_DEVICE_ID, default=current
                    ): selector.TextSelector()
                }
            ),
        )
