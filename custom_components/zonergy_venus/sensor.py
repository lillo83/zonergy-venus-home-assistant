"""Sensor platform for Zonergy Venus."""

from __future__ import annotations

import math

from aioesphomeapi.model import (
    SensorInfo,
    SensorState,
    TextSensorInfo,
    TextSensorState,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
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
    """Set up numeric and text sensors discovered through ESPHome."""
    manager = entry.runtime_data
    entities = []
    for info in manager.entity_infos:
        if isinstance(info, SensorInfo):
            entities.append(ZonergyNumericSensor(manager, info))
        elif isinstance(info, TextSensorInfo):
            entities.append(ZonergyTextSensor(manager, info))
    async_add_entities(entities)


class ZonergyNumericSensor(ZonergyVenusEntity, SensorEntity):
    """A numeric value read from the inverter."""

    def __init__(self, manager: ZonergyVenusManager, info: SensorInfo) -> None:
        super().__init__(manager, info)
        self._attr_native_unit_of_measurement = info.unit_of_measurement or None
        self._attr_suggested_display_precision = info.accuracy_decimals
        if info.device_class:
            try:
                self._attr_device_class = SensorDeviceClass(info.device_class)
            except ValueError:
                pass
        if info.state_class is not None and info.state_class.name != "NONE":
            try:
                self._attr_state_class = SensorStateClass(
                    info.state_class.name.lower()
                )
            except ValueError:
                pass

    @property
    def native_value(self) -> float | None:
        """Return the last value pushed by ESPHome."""
        state = self.manager.state_for(self.info)
        if not isinstance(state, SensorState) or state.missing_state:
            return None
        return state.state if math.isfinite(state.state) else None


class ZonergyTextSensor(ZonergyVenusEntity, SensorEntity):
    """A textual inverter state provided by the firmware."""

    @property
    def native_value(self) -> str | None:
        """Return the last text pushed by ESPHome."""
        state = self.manager.state_for(self.info)
        if not isinstance(state, TextSensorState) or state.missing_state:
            return None
        return state.state
