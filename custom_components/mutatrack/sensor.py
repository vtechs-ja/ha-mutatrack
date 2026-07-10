"""Sensor platform for MutaTrack.

Entity descriptions are keyed to const.FIELD_INDEX names, which are
UNVERIFIED (see docs/api-reference.md). device_class/state_class are only
assigned where reasonably confident from the field name; ambiguous fields
(work_state, software_version, last_update_timestamp, charger_work_enable)
are left as plain diagnostic sensors until Phase 2 confirms their actual
format.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PN, CONF_SN, DOMAIN
from .coordinator import MutaTrackCoordinator


@dataclass(frozen=True, kw_only=True)
class MutaTrackSensorDescription(SensorEntityDescription):
    """Sensor description keyed to a const.FIELD_INDEX field name."""


SENSOR_DESCRIPTIONS: tuple[MutaTrackSensorDescription, ...] = (
    MutaTrackSensorDescription(
        key="battery_voltage",
        translation_key="battery_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MutaTrackSensorDescription(
        key="pv1_voltage",
        translation_key="pv1_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    MutaTrackSensorDescription(
        key="pv2_voltage",
        translation_key="pv2_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    MutaTrackSensorDescription(
        key="inverter_voltage",
        translation_key="inverter_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MutaTrackSensorDescription(
        key="grid_voltage",
        translation_key="grid_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MutaTrackSensorDescription(
        key="load_current",
        translation_key="load_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MutaTrackSensorDescription(
        key="battery_current",
        translation_key="battery_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MutaTrackSensorDescription(
        key="inverter_current",
        translation_key="inverter_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    MutaTrackSensorDescription(
        key="grid_current",
        translation_key="grid_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    MutaTrackSensorDescription(
        key="pv_total_power",
        translation_key="pv_total_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MutaTrackSensorDescription(
        key="load_power",
        translation_key="load_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MutaTrackSensorDescription(
        key="grid_power",
        translation_key="grid_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MutaTrackSensorDescription(
        key="battery_power",
        translation_key="battery_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MutaTrackSensorDescription(
        key="rated_power",
        translation_key="rated_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MutaTrackSensorDescription(
        key="battery_soc",
        translation_key="battery_soc",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MutaTrackSensorDescription(
        key="inverter_frequency",
        translation_key="inverter_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MutaTrackSensorDescription(
        key="grid_frequency",
        translation_key="grid_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MutaTrackSensorDescription(
        key="ac_radiator_temperature",
        translation_key="ac_radiator_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MutaTrackSensorDescription(
        key="transformer_temperature",
        translation_key="transformer_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MutaTrackSensorDescription(
        key="dc_radiator_temperature",
        translation_key="dc_radiator_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MutaTrackSensorDescription(
        key="bms_battery_temperature",
        translation_key="bms_battery_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Cumulative energy fields — device_class/state_class required for HA
    # Energy Dashboard compatibility, per docs/architecture.md.
    MutaTrackSensorDescription(
        key="accumulated_charge_energy",
        translation_key="accumulated_charge_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    MutaTrackSensorDescription(
        key="accumulated_discharge_energy",
        translation_key="accumulated_discharge_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    MutaTrackSensorDescription(
        key="accumulated_buy_energy",
        translation_key="accumulated_buy_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    MutaTrackSensorDescription(
        key="accumulated_sell_energy",
        translation_key="accumulated_sell_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    MutaTrackSensorDescription(
        key="accumulated_load_energy",
        translation_key="accumulated_load_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    MutaTrackSensorDescription(
        key="accumulated_self_use_energy",
        translation_key="accumulated_self_use_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    MutaTrackSensorDescription(
        key="pv_cumulative_generation",
        translation_key="pv_cumulative_generation",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # Ambiguous/unverified format — plain diagnostic sensors, no device_class.
    MutaTrackSensorDescription(
        key="work_state",
        translation_key="work_state",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MutaTrackSensorDescription(
        key="software_version",
        translation_key="software_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    MutaTrackSensorDescription(
        key="last_update_timestamp",
        translation_key="last_update_timestamp",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    MutaTrackSensorDescription(
        key="charger_work_enable",
        translation_key="charger_work_enable",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MutaTrack sensors from a config entry."""
    coordinator: MutaTrackCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        MutaTrackSensor(coordinator, config_entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class MutaTrackSensor(CoordinatorEntity[MutaTrackCoordinator], SensorEntity):
    """A single MutaTrack field exposed as a sensor entity."""

    entity_description: MutaTrackSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MutaTrackCoordinator,
        config_entry: ConfigEntry,
        description: MutaTrackSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        pn = config_entry.data[CONF_PN]
        sn = config_entry.data[CONF_SN]
        self._attr_unique_id = f"{pn}_{sn}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{pn}_{sn}")},
            "name": f"MutaTrack ({pn})",
            "manufacturer": "Must / Eybond (via ValueClouds)",
        }

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.entity_description.key)
