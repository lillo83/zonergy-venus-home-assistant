"""Select platform for Zonergy Venus."""

from __future__ import annotations

from aioesphomeapi.model import SelectInfo, SelectState
from homeassistant.components.select import SelectEntity
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
    """Set up inverter option selectors, such as the operating mode."""
    manager = entry.runtime_data
    async_add_entities(
        ZonergySelect(manager, info)
        for info in manager.entity_infos
        if isinstance(info, SelectInfo)
        and (
            manager.connection_type != CONNECTION_BLUETOOTH
            or info.name.startswith(BLE_ENTITY_PREFIX)
        )
    )


class ZonergySelect(ZonergyVenusEntity, SelectEntity):
    """A selector that writes an option to an inverter holding register."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, manager: ZonergyVenusManager, info: SelectInfo) -> None:
        super().__init__(manager, info)
        self._attr_options = list(info.options)

    @property
    def current_option(self) -> str | None:
        """Return the last option reported by the gateway."""
        state = self.manager.state_for(self.info)
        if not isinstance(state, SelectState) or state.missing_state:
            return None
        return state.state

    async def async_select_option(self, option: str) -> None:
        """Write the selected option to the inverter."""
        if not self.manager.available:
            raise HomeAssistantError("The ESPHome gateway is unavailable")
        self.manager.client.select_command(
            self.info.key, option, device_id=self.info.device_id
        )
