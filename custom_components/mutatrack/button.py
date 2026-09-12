"""Button platform for MutaTrack.

v1 has exactly one button: resetting the battery forecast engine's learned
calibration (empirical capacity, observed cycle count, round-trip stats).
Useful after a physical battery replacement, or to recover from a bad-data
episode polluting the EMA (see forecast.py's outlier guard and
IMPLEMENTATION_PLAN.md's 2026-09-12 entry for the incident that prompted
this).
"""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PN, CONF_SN, DOMAIN
from .coordinator import MutaTrackCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MutaTrackCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([MutaTrackResetCalibrationButton(coordinator, config_entry)])


class MutaTrackResetCalibrationButton(CoordinatorEntity[MutaTrackCoordinator], ButtonEntity):
    """Discards learned battery calibration and starts recalibrating."""

    _attr_has_entity_name = True
    _attr_name = "Reset battery calibration"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, coordinator: MutaTrackCoordinator, config_entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        pn = config_entry.data[CONF_PN]
        sn = config_entry.data[CONF_SN]
        self._attr_unique_id = f"{pn}_{sn}_reset_battery_calibration"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{pn}_{sn}")},
            "name": f"MutaTrack ({pn})",
            "manufacturer": "Must / Eybond (via ValueClouds)",
        }

    async def async_press(self) -> None:
        await self.coordinator.async_reset_forecast_calibration()
