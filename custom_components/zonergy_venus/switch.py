"""Switch platform for Zonergy Venus."""

from __future__ import annotations

from typing import Any

from aioesphomeapi.model import SwitchInfo, SwitchState
from homeassistant.components.switch import SwitchEntity
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
    """Set up writable inverter switches."""
    manager = entry.runtime_data
    async_add_entities(
        ZonergySwitch(manager, info)
        for info in manager.entity_infos
        if isinstance(info, SwitchInfo)
        and (
            manager.connection_type != CONNECTION_BLUETOOTH
            or info.name.startswith(BLE_ENTITY_PREFIX)
        )
    )


class ZonergySwitch(ZonergyVenusEntity, SwitchEntity):
    """A switch that writes to an inverter holding register."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, manager: ZonergyVenusManager, info: SwitchInfo) -> None:
        super().__init__(manager, info)
        self._attr_assumed_state = info.assumed_state

    @property
    def is_on(self) -> bool | None:
        """Return the last switch state from the gateway."""
        state = self.manager.state_for(self.info)
        return state.state if isinstance(state, SwitchState) else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Write the enabled value to the inverter."""
        self._send_command(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Write the disabled value to the inverter."""
        self._send_command(False)

    def _send_command(self, state: bool) -> None:
        if not self.manager.available:
            raise HomeAssistantError("The ESPHome gateway is unavailable")
        self.manager.client.switch_command(
            self.info.key, state, device_id=self.info.device_id
        )
