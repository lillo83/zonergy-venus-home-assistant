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

from .cloud import ZonergyCloudCoordinator, ZonergyCloudEntity
from .const import BLE_ENTITY_PREFIX, CONNECTION_BLUETOOTH
from .entity import ZonergyVenusEntity
from .manager import ZonergyVenusManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[ZonergyVenusManager],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors discovered through ESPHome."""
    manager = entry.runtime_data
    if isinstance(manager, ZonergyCloudCoordinator):
        async_add_entities(
            [ZonergyCloudOnlineSensor(manager), ZonergyCloudRegisterSensor(manager)]
        )
        return

    async_add_entities(
        ZonergyBinarySensor(manager, info)
        for info in manager.entity_infos
        if isinstance(info, BinarySensorInfo)
        and (
            manager.connection_type != CONNECTION_BLUETOOTH
            or info.name.startswith(BLE_ENTITY_PREFIX)
        )
    )


class ZonergyBinarySensor(ZonergyVenusEntity, BinarySensorEntity):
    """A binary state pushed by the ESPHome gateway."""

    def __init__(self, manager: ZonergyVenusManager, info: BinarySensorInfo) -> None:
        super().__init__(manager, info)
        if info.device_class:
            try:
                self._attr_device_class = BinarySensorDeviceClass(info.device_class)
            except ValueError:
                pass

    @property
    def is_on(self) -> bool | None:
        """Return the current binary state."""
        state = self.manager.state_for(self.info)
        if not isinstance(state, BinarySensorState) or state.missing_state:
            return None
        return state.state


class ZonergyCloudOnlineSensor(ZonergyCloudEntity, BinarySensorEntity):
    """Whether the cloud reports the inverter as online."""

    _attr_translation_key = "cloud_online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: ZonergyCloudCoordinator) -> None:
        super().__init__(coordinator, "cloud_online")

    @property
    def is_on(self) -> bool | None:
        """Return cloud connectivity state."""
        value = self.coordinator.data.get("device_status")
        if value is None:
            value = self.coordinator.data.get("status")
        if value is None:
            return None
        if isinstance(value, str):
            return value.lower() in {"1", "2", "true", "online", "normal", "fault"}
        return bool(value)

    @property
    def native_cloud_value(self) -> bool | None:
        """Expose the resolved value to the common availability check."""
        return self.is_on


class ZonergyCloudRegisterSensor(ZonergyCloudEntity, BinarySensorEntity):
    """Whether live read-only register access is responding."""

    _attr_translation_key = "cloud_register_read"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: ZonergyCloudCoordinator) -> None:
        super().__init__(coordinator, "_register_read_available")

    @property
    def is_on(self) -> bool | None:
        """Return whether live registers were received."""
        value = self.coordinator.data.get("_register_read_available")
        return value if isinstance(value, bool) else None

    @property
    def native_cloud_value(self) -> bool | None:
        """Expose the resolved value to the common availability check."""
        return self.is_on

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Expose register diagnostics without logging account credentials."""
        attributes = {
            "identificativo_usato": str(
                self.coordinator.data.get("_register_device_id", "")
            )
        }
        error = self.coordinator.data.get("_register_read_error")
        if error:
            attributes["ultimo_errore"] = str(error)
        return attributes
