"""Base entity for Zonergy Venus."""

from __future__ import annotations

from aioesphomeapi.model import EntityInfo
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .manager import ZonergyVenusManager


class ZonergyVenusEntity(Entity):
    """Representation of one entity provided by the companion firmware."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, manager: ZonergyVenusManager, info: EntityInfo) -> None:
        self.manager = manager
        self.info = info
        self._attr_name = info.name
        self._attr_icon = info.icon or None
        self._attr_unique_id = (
            f"{manager.device_identifier}_{type(info).__name__.lower()}_"
            f"{info.device_id}_{info.key}"
        )

        api_info = manager.device_info
        device_name = (
            (api_info.friendly_name or api_info.name) if api_info else None
        ) or "Zonergy Venus"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, manager.device_identifier)},
            manufacturer="Zonergy",
            model="Venus hybrid inverter via ESPHome RS485",
            name=device_name,
            serial_number=api_info.mac_address if api_info else None,
            sw_version=api_info.esphome_version if api_info else None,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to API push updates."""
        self.async_on_remove(
            self.manager.async_add_listener(self._handle_manager_update)
        )

    @property
    def available(self) -> bool:
        """Return whether the gateway and this entity are available."""
        if not self.manager.available:
            return False
        state = self.manager.state_for(self.info)
        return state is not None and not getattr(state, "missing_state", False)

    def _handle_manager_update(self) -> None:
        if self.hass is not None:
            self.async_write_ha_state()
