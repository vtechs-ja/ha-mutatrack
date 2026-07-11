"""DataUpdateCoordinator for MutaTrack.

One coordinator per config entry (per device), one API call per poll cycle,
per the design decisions in docs/architecture.md.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, TypedDict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MutaTrackApiClient, MutaTrackApiError, MutaTrackAuthError
from .const import DOMAIN
from .forecast import BatteryForecastEngine, ForecastResult

_LOGGER = logging.getLogger(__name__)


class MutaTrackField(TypedDict):
    """A single parsed field reading."""

    title: str
    unit: str | None
    raw_value: str
    value: float | str


class MutaTrackCoordinator(DataUpdateCoordinator[dict[str, MutaTrackField]]):
    """Coordinates polling and parses the raw field list into an id-keyed dict."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api_client: MutaTrackApiClient,
        scan_interval_seconds: int,
        battery_capacity_kwh: float | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=timedelta(seconds=scan_interval_seconds),
        )
        self._api_client = api_client
        self.forecast_engine = BatteryForecastEngine(battery_capacity_kwh)
        self.forecast: ForecastResult | None = None

    async def _async_update_data(self) -> dict[str, MutaTrackField]:
        try:
            raw_fields = await self._api_client.async_get_device_data()
        except MutaTrackAuthError as err:
            # Distinct from a generic UpdateFailed so entities/diagnostics can
            # tell "cloud auth is broken" apart from "device looks offline".
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except MutaTrackApiError as err:
            raise UpdateFailed(f"Error communicating with ValueClouds API: {err}") from err

        parsed = _parse_fields(raw_fields)
        self.forecast = self.forecast_engine.update(parsed)
        self._update_capacity_deviation_issue()
        return parsed

    def _update_capacity_deviation_issue(self) -> None:
        issue_id = f"battery_capacity_deviation_{self.config_entry.entry_id}"
        if self.forecast and self.forecast.deviation_warning:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="battery_capacity_deviation",
            )
        else:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)


def _parse_fields(raw_fields: list[dict[str, Any]]) -> dict[str, MutaTrackField]:
    """Map the raw {id, title, unit, val} list onto an id-keyed dict.

    Values are opportunistically parsed as float (most fields are numeric
    readings); fields that aren't valid floats (e.g. "Chg Off", "L16",
    timestamps) are kept as their original string.
    """
    parsed: dict[str, MutaTrackField] = {}
    for entry in raw_fields:
        field_id = entry.get("id")
        if not field_id:
            continue

        raw_value = entry.get("val", "")
        try:
            value: float | str = float(raw_value)
        except (TypeError, ValueError):
            value = raw_value

        parsed[field_id] = {
            "title": entry.get("title") or field_id,
            "unit": entry.get("unit") or None,
            "raw_value": raw_value,
            "value": value,
        }
    return parsed
