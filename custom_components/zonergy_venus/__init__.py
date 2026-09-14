"""Zonergy Venus integration using ESPHome or the Zonergy cloud."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .cloud import ZonergyCloudCoordinator
from .cloud_api import ZonergyCloudApi, ZonergyCloudError
from .const import (
    CONF_CONNECTION_TYPE,
    CONF_DEVICE_SN,
    CONF_ENCRYPTION_KEY,
    CONF_REALTIME_DEVICE_ID,
    CONNECTION_CLOUD,
    CONNECTION_ESPHOME,
    PLATFORMS,
)
from .manager import ZonergyVenusManager

type ZonergyVenusRuntime = ZonergyVenusManager | ZonergyCloudCoordinator
type ZonergyVenusConfigEntry = ConfigEntry[ZonergyVenusRuntime]


async def async_setup_entry(
    hass: HomeAssistant, entry: ZonergyVenusConfigEntry
) -> bool:
    """Set up Zonergy Venus from a config entry."""
    connection_type = entry.data.get(
        CONF_CONNECTION_TYPE,
        CONNECTION_ESPHOME if CONF_HOST in entry.data else CONNECTION_CLOUD,
    )
    if connection_type == CONNECTION_CLOUD:
        api = ZonergyCloudApi(
            async_get_clientsession(hass),
            account=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
        )
        if CONF_REALTIME_DEVICE_ID not in entry.data:
            try:
                devices = await api.async_discover_devices()
            except ZonergyCloudError:
                devices = []
            device = next(
                (
                    item
                    for item in devices
                    if item.serial_number == entry.data.get(CONF_DEVICE_SN)
                ),
                None,
            )
            if device is not None:
                hass.config_entries.async_update_entry(
                    entry,
                    data={
                        **entry.data,
                        CONF_REALTIME_DEVICE_ID: device.realtime_id,
                    },
                )
        coordinator = ZonergyCloudCoordinator(hass, entry, api)
        await coordinator.async_config_entry_first_refresh()
        entry.runtime_data = coordinator
        await hass.config_entries.async_forward_entry_setups(
            entry, ["sensor", "binary_sensor"]
        )
        return True

    manager = ZonergyVenusManager(
        hass,
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        password=entry.data.get(CONF_PASSWORD) or None,
        encryption_key=entry.data.get(CONF_ENCRYPTION_KEY) or None,
    )

    try:
        await manager.async_start()
    except TimeoutError as err:
        await manager.async_stop()
        raise ConfigEntryNotReady(
            f"ESPHome node {entry.data[CONF_HOST]} did not become ready"
        ) from err

    entry.runtime_data = manager
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ZonergyVenusConfigEntry
) -> bool:
    """Unload a config entry."""
    platforms = (
        ["sensor", "binary_sensor"]
        if isinstance(entry.runtime_data, ZonergyCloudCoordinator)
        else PLATFORMS
    )
    if not await hass.config_entries.async_unload_platforms(entry, platforms):
        return False

    if isinstance(entry.runtime_data, ZonergyVenusManager):
        await entry.runtime_data.async_stop()
    return True
