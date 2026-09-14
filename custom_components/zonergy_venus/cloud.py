"""Cloud coordinator and entity base for Zonergy Venus."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .cloud_api import (
    ZonergyCloudApi,
    ZonergyCloudAuthError,
    ZonergyCloudError,
)
from .const import (
    CLOUD_BASE_URL,
    CLOUD_SCAN_INTERVAL,
    CONF_DEVICE_ID,
    CONF_DEVICE_SN,
    CONF_INVERTER_MODEL,
    CONF_PLANT_ID,
    CONF_PLANT_NAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class ZonergyCloudCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll the official Zonergy cloud read-only endpoints."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: ZonergyCloudApi,
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"Zonergy cloud {entry.data[CONF_DEVICE_SN]}",
            update_interval=timedelta(seconds=CLOUD_SCAN_INTERVAL),
        )
        self.entry = entry
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.api.async_device_data(
                plant_id=self.entry.data[CONF_PLANT_ID],
                device_id=self.entry.data[CONF_DEVICE_ID],
            )
        except ZonergyCloudAuthError as err:
            raise ConfigEntryAuthFailed from err
        except ZonergyCloudError as err:
            raise UpdateFailed(str(err)) from err


class ZonergyCloudEntity(CoordinatorEntity[ZonergyCloudCoordinator], Entity):
    """Base class for an entity read from Zonergy cloud."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ZonergyCloudCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self.key = key
        serial = coordinator.entry.data[CONF_DEVICE_SN]
        self._attr_unique_id = f"{serial}_cloud_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"cloud_{serial}")},
            manufacturer="Zonergy",
            model=coordinator.entry.data.get(CONF_INVERTER_MODEL, "Venus"),
            name=coordinator.entry.data.get(CONF_PLANT_NAME) or "Zonergy Venus",
            serial_number=serial,
            configuration_url=CLOUD_BASE_URL,
        )

    @property
    def available(self) -> bool:
        """Return whether the coordinator has this value."""
        return super().available and self.native_cloud_value is not None

    @property
    def native_cloud_value(self) -> Any:
        """Return the unmodified value for this cloud key."""
        return self.coordinator.data.get(self.key)
