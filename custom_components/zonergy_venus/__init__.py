"""Zonergy Venus integration using the ESPHome native API."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_ENCRYPTION_KEY, DOMAIN, PLATFORMS
from .manager import ZonergyVenusManager

type ZonergyVenusConfigEntry = ConfigEntry[ZonergyVenusManager]


async def async_setup_entry(
    hass: HomeAssistant, entry: ZonergyVenusConfigEntry
) -> bool:
    """Set up Zonergy Venus from a config entry."""
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
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False

    await entry.runtime_data.async_stop()
    return True
