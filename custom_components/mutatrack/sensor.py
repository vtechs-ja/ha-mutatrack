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
    PV1_POWER_FIELD_ID,
    PV2_POWER_FIELD_ID,
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
    entities.append(MutaTrackBatteryCapacitySensor(coordinator, config_entry))
    entities.append(MutaTrackRoundTripEfficiencySensor(coordinator, config_entry))
    if PV1_POWER_FIELD_ID in coordinator.data and PV2_POWER_FIELD_ID in coordinator.data:
        entities.append(MutaTrackPvStringBalanceSensor(coordinator, config_entry))
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
            "stop_soc_percent": forecast.stop_soc_percent,
        }


class MutaTrackBatteryCapacitySensor(CoordinatorEntity[MutaTrackCoordinator], SensorEntity):
    """Standalone, graphable view of the forecast engine's active capacity.

    Duplicates the `capacity_kwh` attribute on the forecast sensor, but as
    its own entity — HA doesn't chart attributes, only entity states, and
    watching this trend over months is the whole point (capacity fade =
    battery degradation signal).
    """

    _attr_has_entity_name = True
    _attr_name = "Battery capacity estimate"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    # No device_class: HA's ENERGY device_class requires state_class
    # TOTAL/TOTAL_INCREASING (a cumulative counter), but capacity can rise
    # or fall — this is a plain measurement, so device_class is left unset.
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator: MutaTrackCoordinator, config_entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        pn = config_entry.data[CONF_PN]
        sn = config_entry.data[CONF_SN]
        self._attr_unique_id = f"{pn}_{sn}_battery_capacity_estimate"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{pn}_{sn}")},
            "name": f"MutaTrack ({pn})",
            "manufacturer": "Must / Eybond (via ValueClouds)",
        }

    @property
    def native_value(self):
        forecast = self.coordinator.forecast
        if forecast is None or forecast.capacity_kwh is None:
            return None
        return round(forecast.capacity_kwh, 2)

    @property
    def extra_state_attributes(self):
        forecast = self.coordinator.forecast
        if forecast is None:
            return {}
        return {
            "capacity_source": forecast.capacity_source,
            "calibration_confidence": forecast.calibration_confidence,
            "observed_cycles": forecast.observed_cycles,
        }


class MutaTrackRoundTripEfficiencySensor(CoordinatorEntity[MutaTrackCoordinator], SensorEntity):
    """Battery round-trip efficiency (energy out / energy in per cycle).

    A second, independent battery-health signal alongside capacity fade —
    rising internal resistance shows up here even before capacity itself
    visibly declines.
    """

    _attr_has_entity_name = True
    _attr_name = "Battery round-trip efficiency"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator: MutaTrackCoordinator, config_entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        pn = config_entry.data[CONF_PN]
        sn = config_entry.data[CONF_SN]
        self._attr_unique_id = f"{pn}_{sn}_round_trip_efficiency"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{pn}_{sn}")},
            "name": f"MutaTrack ({pn})",
            "manufacturer": "Must / Eybond (via ValueClouds)",
        }

    @property
    def native_value(self):
        forecast = self.coordinator.forecast
        if forecast is None:
            return None
        value = forecast.round_trip_efficiency_percent
        return round(value, 1) if value is not None else None

    @property
    def extra_state_attributes(self):
        forecast = self.coordinator.forecast
        if forecast is None:
            return {}
        return {"cycles_observed": forecast.round_trip_cycles}


class MutaTrackPvStringBalanceSensor(CoordinatorEntity[MutaTrackCoordinator], SensorEntity):
    """PV1 vs PV2 string power balance, as a percent deviation from even.

    Only meaningful for installs where both strings are the same
    orientation/size (confirmed true for Deron's install) — a drifting
    ratio then signals a differential fault (soiling, shading, a failing
    string) on one side, since both strings see the same sun at the same
    moment and need no external weather reference to compare against each
    other.
    """

    _attr_has_entity_name = True
    _attr_name = "PV string balance"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator: MutaTrackCoordinator, config_entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        pn = config_entry.data[CONF_PN]
        sn = config_entry.data[CONF_SN]
        self._attr_unique_id = f"{pn}_{sn}_pv_string_balance"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{pn}_{sn}")},
            "name": f"MutaTrack ({pn})",
            "manufacturer": "Must / Eybond (via ValueClouds)",
        }

    @property
    def native_value(self):
        pv1 = self.coordinator.data.get(PV1_POWER_FIELD_ID)
        pv2 = self.coordinator.data.get(PV2_POWER_FIELD_ID)
        if not pv1 or not pv2:
            return None
        pv1_w, pv2_w = pv1["value"], pv2["value"]
        if not isinstance(pv1_w, (int, float)) or not isinstance(pv2_w, (int, float)):
            return None
        # Below this, both strings are essentially dark (night) — the ratio
        # is meaningless noise, not a real balance reading.
        if pv2_w < 30:
            return None
        return round((pv1_w / pv2_w - 1) * 100, 1)
