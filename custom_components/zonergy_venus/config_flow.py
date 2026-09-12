"""Config flow for Zonergy Venus."""

from __future__ import annotations

import asyncio
from typing import Any

from aioesphomeapi import (
    APIClient,
    APIConnectionError,
    InvalidAuthAPIError,
    InvalidEncryptionKeyAPIError,
)
from aioesphomeapi.model import DeviceInfo, EntityInfo
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_ENCRYPTION_KEY,
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
            device_info, entities, _ = (
                await client.device_info_and_list_entities()
            )
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
    """Handle a config flow for a Zonergy Venus ESPHome gateway."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual setup."""
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
                vol.Required(CONF_HOST): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Required(CONF_PORT, default=DEFAULT_PORT): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=65535,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(CONF_ENCRYPTION_KEY, default=""): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.PASSWORD
                    )
                ),
                vol.Optional(CONF_PASSWORD, default=""): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.PASSWORD
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )
