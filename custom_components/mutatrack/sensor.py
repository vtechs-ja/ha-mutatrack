"""Sensor platform for MutaTrack.

Entities are built dynamically from whatever fields the API actually
returns (via queryDeviceOneDataxxx — self-describing id/title/unit/val),
rather than a hardcoded static list. Fields in const.PRIMARY_TELEMETRY_IDS
(the leaner querySPDeviceLastData set, confirmed a strict subset) become
regular sensors; everything else (settings/control-read values, machine
info, etc.) becomes a read-only diagnostic-category sensor. See
docs/architecture.md and docs/api-reference.md for the full rationale.
"""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    BATTERY_SOC_FIELD_ID,
    CONF_PN,
    CONF_SN,
    DOMAIN,
    ENERGY_FIELD_IDS,
    PRIMARY_TELEMETRY_IDS,
)
from .coordinator import MutaTrackCoordinator

# Raw API unit string -> (device_class, HA unit constant). Units not listed
# here (e.g. unitless settings/status strings, or units like "S"/"Var" only
# seen on settings fields) are exposed without a device_class — still a
# usable sensor, just without unit-based coercion/rounding in the UI.
UNIT_TO_DEVICE_CLASS: dict[str, tuple[SensorDeviceClass, str]] = {
    "V": (SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT),
    "A": (SensorDeviceClass.CURRENT, UnitOfElectricCurrent.AMPERE),
    "W": (SensorDeviceClass.POWER, UnitOfPower.WATT),
    "VA": (SensorDeviceClass.APPARENT_POWER, UnitOfApparentPower.VOLT_AMPERE),
    "Hz": (SensorDeviceClass.FREQUENCY, UnitOfFrequency.HERTZ),
    "kWh": (SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR),
    "°C": (SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MutaTrack sensors from a config entry.

    Entities are built from whatever fields were present on the first
    successful poll (guaranteed by async_config_entry_first_refresh in
    __init__.py). A firmware/model variance that adds or removes fields
    will only be picked up on integration reload, not live — acceptable
    for v1 given how rarely this vendor's field set is likely to change.
    """
    coordinator: MutaTrackCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities: list[SensorEntity] = [
        MutaTrackSensor(coordinator, config_entry, field_id)
        for field_id in coordinator.data
    ]
    entities.append(MutaTrackBatteryForecastSensor(coordinator, config_entry))
    async_add_entities(entities)


class MutaTrackSensor(CoordinatorEntity[MutaTrackCoordinator], SensorEntity):
    """A single MutaTrack field exposed as a sensor entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MutaTrackCoordinator,
        config_entry: ConfigEntry,
        field_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._field_id = field_id

        field = coordinator.data[field_id]
        self._attr_name = field["title"]

        unit = field["unit"]
        if unit in UNIT_TO_DEVICE_CLASS:
            device_class, ha_unit = UNIT_TO_DEVICE_CLASS[unit]
            self._attr_device_class = device_class
            self._attr_native_unit_of_measurement = ha_unit
        elif unit:
            self._attr_native_unit_of_measurement = unit

        if field_id == BATTERY_SOC_FIELD_ID:
            self._attr_device_class = SensorDeviceClass.BATTERY
            self._attr_native_unit_of_measurement = PERCENTAGE

        if field_id in ENERGY_FIELD_IDS:
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        elif isinstance(field["value"], (int, float)) and field_id in PRIMARY_TELEMETRY_IDS:
            self._attr_state_class = SensorStateClass.MEASUREMENT

        if field_id not in PRIMARY_TELEMETRY_IDS:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

        pn = config_entry.data[CONF_PN]
        sn = config_entry.data[CONF_SN]
        self._attr_unique_id = f"{pn}_{sn}_{field_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{pn}_{sn}")},
            "name": f"MutaTrack ({pn})",
            "manufacturer": "Must / Eybond (via ValueClouds)",
        }

    @property
    def native_value(self):
        field = self.coordinator.data.get(self._field_id)
        return field["value"] if field else None


class MutaTrackBatteryForecastSensor(CoordinatorEntity[MutaTrackCoordinator], SensorEntity):
    """v1.5 battery runtime forecast — see forecast.py for the engine.

    Not part of the dynamic per-field sensor loop above: this is a derived
    value, not a raw API field.
    """

    _attr_has_entity_name = True
    _attr_name = "Battery time remaining"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    def __init__(
        self, coordinator: MutaTrackCoordinator, config_entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        pn = config_entry.data[CONF_PN]
        sn = config_entry.data[CONF_SN]
        self._attr_unique_id = f"{pn}_{sn}_battery_time_remaining"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{pn}_{sn}")},
            "name": f"MutaTrack ({pn})",
            "manufacturer": "Must / Eybond (via ValueClouds)",
        }

    @property
    def native_value(self):
        forecast = self.coordinator.forecast
        if forecast is None or forecast.seconds_remaining is None:
            return None
        return round(forecast.seconds_remaining / 60)

    @property
    def extra_state_attributes(self):
        forecast = self.coordinator.forecast
        if forecast is None:
            return {}
        return {
            "rate_method": forecast.rate_method,
            "capacity_source": forecast.capacity_source,
            "capacity_kwh": forecast.capacity_kwh,
            "calibration_confidence": forecast.calibration_confidence,
            "deviation_warning": forecast.deviation_warning,
            "observed_cycles": forecast.observed_cycles,
        }
