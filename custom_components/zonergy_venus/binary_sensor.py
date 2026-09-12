"""Binary sensor platform for Zonergy Venus."""

from __future__ import annotations

from aioesphomeapi.model import BinarySensorInfo, BinarySensorState
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import ZonergyVenusEntity
from .manager import ZonergyVenusManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[ZonergyVenusManager],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors discovered through ESPHome."""
    manager = entry.runtime_data
    async_add_entities(
        ZonergyBinarySensor(manager, info)
        for info in manager.entity_infos
        if isinstance(info, BinarySensorInfo)
    )


class ZonergyBinarySensor(ZonergyVenusEntity, BinarySensorEntity):
    """A binary state pushed by the ESPHome gateway."""

    def __init__(
        self, manager: ZonergyVenusManager, info: BinarySensorInfo
    ) -> None:
        super().__init__(manager, info)
        if info.device_class:
            try:
                self._attr_device_class = BinarySensorDeviceClass(
                    info.device_class
                )
            except ValueError:
                pass

    @property
    def is_on(self) -> bool | None:
        """Return the current binary state."""
        state = self.manager.state_for(self.info)
        if not isinstance(state, BinarySensorState) or state.missing_state:
            return None
        return state.state
