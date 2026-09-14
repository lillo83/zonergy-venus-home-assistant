"""Sensor platform for Zonergy Venus."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from aioesphomeapi.model import (
    SensorInfo,
    SensorState,
    TextSensorInfo,
    TextSensorState,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .cloud import ZonergyCloudCoordinator, ZonergyCloudEntity
from .entity import ZonergyVenusEntity
from .manager import ZonergyVenusManager


@dataclass(frozen=True, kw_only=True)
class ZonergyCloudSensorDescription(SensorEntityDescription):
    """Describe a numeric value returned by Zonergy cloud."""

    value_keys: tuple[str, ...]


CLOUD_SENSORS: tuple[ZonergyCloudSensorDescription, ...] = (
    ZonergyCloudSensorDescription(
        key="pv_power",
        translation_key="pv_power",
        value_keys=("pv_input_power",),
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="load_power",
        translation_key="load_power",
        value_keys=("r_load_power", "total_load_active_power"),
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="grid_power",
        translation_key="grid_power",
        value_keys=("r_active_power", "grid_active_power"),
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="battery_power",
        translation_key="battery_power",
        value_keys=("battery_cd_power", "inverter_battery_cd_power"),
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="battery_soc",
        translation_key="battery_soc",
        value_keys=("battery_soc",),
        native_unit_of_measurement="%",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="battery_voltage",
        translation_key="battery_voltage",
        value_keys=(
            "inverter_battery_voltage",
            "battery_voltage",
            "battery_avg_voltage",
        ),
        native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="battery_current",
        translation_key="battery_current",
        value_keys=("inverter_battery_current", "battery_current"),
        native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="grid_voltage",
        translation_key="grid_voltage",
        value_keys=("r_grid_voltage",),
        native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="grid_current",
        translation_key="grid_current",
        value_keys=("r_grid_current",),
        native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="grid_frequency",
        translation_key="grid_frequency",
        value_keys=("r_grid_freq",),
        native_unit_of_measurement="Hz",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="pv1_voltage",
        translation_key="pv1_voltage",
        value_keys=("pv1_input_voltage",),
        native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="pv1_current",
        translation_key="pv1_current",
        value_keys=("pv1_input_current",),
        native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="pv1_power",
        translation_key="pv1_power",
        value_keys=("pv1_input_power",),
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="pv2_voltage",
        translation_key="pv2_voltage",
        value_keys=("pv2_input_voltage",),
        native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="pv2_current",
        translation_key="pv2_current",
        value_keys=("pv2_input_current",),
        native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="pv2_power",
        translation_key="pv2_power",
        value_keys=("pv2_input_power",),
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="inverter_temperature",
        translation_key="inverter_temperature",
        value_keys=("inverter_rad_temp", "internal_temp"),
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="dcdc_temperature",
        translation_key="dcdc_temperature",
        value_keys=("dcdc_rad_temp",),
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="internal_temperature",
        translation_key="internal_temperature",
        value_keys=("internal_temp",),
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="pv_temperature",
        translation_key="pv_temperature",
        value_keys=("pv_temp",),
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="bus_voltage",
        translation_key="bus_voltage",
        value_keys=("bus_voltage",),
        native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="negative_bus_voltage",
        translation_key="negative_bus_voltage",
        value_keys=("dcbus_voltage",),
        native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="total_bus_voltage",
        translation_key="total_bus_voltage",
        value_keys=("total_dcbus_voltage",),
        native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="balance_bridge_current",
        translation_key="balance_bridge_current",
        value_keys=("balance_bridge_current",),
        native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="balance_bridge_power",
        translation_key="balance_bridge_power",
        value_keys=("balance_bridge_power",),
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="battery_soh",
        translation_key="battery_soh",
        value_keys=("battery_soh",),
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="battery_modules",
        translation_key="battery_modules",
        value_keys=("battery_actual_com_list",),
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="load_voltage",
        translation_key="load_voltage",
        value_keys=("r_load_voltage",),
        native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="load_current",
        translation_key="load_current",
        value_keys=("r_load_current",),
        native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="load_frequency",
        translation_key="load_frequency",
        value_keys=("load_freq",),
        native_unit_of_measurement="Hz",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="inverter_voltage",
        translation_key="inverter_voltage",
        value_keys=("r_inverter_voltage",),
        native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="inverter_current",
        translation_key="inverter_current",
        value_keys=("r_inverter_current",),
        native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="inverter_frequency",
        translation_key="inverter_frequency",
        value_keys=("r_inverter_freq",),
        native_unit_of_measurement="Hz",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="inverter_power",
        translation_key="inverter_power",
        value_keys=("r_inverter_power",),
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="ct_current",
        translation_key="ct_current",
        value_keys=("s_grid_current",),
        native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="ct_power",
        translation_key="ct_power",
        value_keys=("s_active_power",),
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="grid_apparent_power",
        translation_key="grid_apparent_power",
        value_keys=("r_apperent_power",),
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="grid_reactive_power",
        translation_key="grid_reactive_power",
        value_keys=("r_reactive_power",),
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZonergyCloudSensorDescription(
        key="today_generation",
        translation_key="today_generation",
        value_keys=("today_generation",),
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    ZonergyCloudSensorDescription(
        key="month_generation",
        translation_key="month_generation",
        value_keys=("month_generation",),
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    ZonergyCloudSensorDescription(
        key="total_generation",
        translation_key="total_generation",
        value_keys=("total_generation",),
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    ZonergyCloudSensorDescription(
        key="year_generation",
        translation_key="year_generation",
        value_keys=("year_generation",),
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    *(
        ZonergyCloudSensorDescription(
            key=key,
            translation_key=key,
            value_keys=(key,),
            native_unit_of_measurement="kWh",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
        )
        for key in (
            "today_buy_grid",
            "month_buy_grid",
            "year_buy_grid",
            "total_buy_grid",
            "today_sell_grid",
            "month_sell_grid",
            "year_sell_grid",
            "total_sell_grid",
            "today_battery_charge",
            "month_battery_charge",
            "year_battery_charge",
            "total_battery_charge",
            "today_battery_discharge",
            "month_battery_discharge",
            "year_battery_discharge",
            "total_battery_discharge",
        )
    ),
    *(
        ZonergyCloudSensorDescription(
            key=key,
            translation_key=key,
            value_keys=(key,),
            native_unit_of_measurement="min",
            device_class=SensorDeviceClass.DURATION,
            state_class=SensorStateClass.TOTAL_INCREASING,
        )
        for key in ("power_hours", "grid_hours", "work_hours")
    ),
    ZonergyCloudSensorDescription(
        key="power_on_numbers",
        translation_key="power_on_numbers",
        value_keys=("power_on_numbers",),
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    ZonergyCloudSensorDescription(
        key="grid_connecteds",
        translation_key="grid_connecteds",
        value_keys=("grid_connecteds",),
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[ZonergyVenusManager],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up numeric and text sensors discovered through ESPHome."""
    manager = entry.runtime_data
    if isinstance(manager, ZonergyCloudCoordinator):
        async_add_entities(
            ZonergyCloudSensor(manager, description)
            for description in CLOUD_SENSORS
        )
        return

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
                self._attr_state_class = SensorStateClass(info.state_class.name.lower())
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


class ZonergyCloudSensor(ZonergyCloudEntity, SensorEntity):
    """A numeric sensor populated by the official Zonergy cloud."""

    entity_description: ZonergyCloudSensorDescription

    def __init__(
        self,
        coordinator: ZonergyCloudCoordinator,
        description: ZonergyCloudSensorDescription,
    ) -> None:
        ZonergyCloudEntity.__init__(self, coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | None:
        """Return the first numeric value supplied for this measurement."""
        for key in self.entity_description.value_keys:
            value: Any = self.coordinator.data.get(key)
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)) and math.isfinite(value):
                return value
            if isinstance(value, str):
                try:
                    numeric = float(value)
                except ValueError:
                    continue
                if math.isfinite(numeric):
                    return numeric
        return None

    @property
    def native_cloud_value(self) -> Any:
        """Expose the resolved cloud value to the common availability check."""
        return self.native_value
