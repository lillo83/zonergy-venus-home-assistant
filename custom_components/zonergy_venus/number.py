"""Number platform for Zonergy Venus."""

from __future__ import annotations

from aioesphomeapi.model import NumberInfo, NumberState
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import BLE_ENTITY_PREFIX, CONNECTION_BLUETOOTH
from .entity import ZonergyVenusEntity
from .manager import ZonergyVenusManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[ZonergyVenusManager],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up writable inverter numeric controls."""
    manager = entry.runtime_data
    async_add_entities(
        ZonergyNumber(manager, info)
        for info in manager.entity_infos
        if isinstance(info, NumberInfo)
        and (
            manager.connection_type != CONNECTION_BLUETOOTH
            or info.name.startswith(BLE_ENTITY_PREFIX)
        )
    )


class ZonergyNumber(ZonergyVenusEntity, NumberEntity):
    """A number that writes to an inverter holding register."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, manager: ZonergyVenusManager, info: NumberInfo) -> None:
        super().__init__(manager, info)
        self._attr_native_min_value = info.min_value
        self._attr_native_max_value = info.max_value
        self._attr_native_step = info.step
        self._attr_native_unit_of_measurement = info.unit_of_measurement or None
        if info.mode is not None:
            try:
                self._attr_mode = NumberMode(info.mode.name.lower())
            except ValueError:
                pass

    @property
    def native_value(self) -> float | None:
        """Return the last numeric state from the gateway."""
        state = self.manager.state_for(self.info)
        if not isinstance(state, NumberState) or state.missing_state:
            return None
        return state.state

    async def async_set_native_value(self, value: float) -> None:
        """Write a numeric value to the inverter."""
        if not self.manager.available:
            raise HomeAssistantError("The ESPHome gateway is unavailable")
        self.manager.client.number_command(
            self.info.key, value, device_id=self.info.device_id
        )
