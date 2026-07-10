"""DataUpdateCoordinator for MutaTrack.

One coordinator per config entry (per device), one API call per poll cycle,
per the design decisions in docs/architecture.md.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MutaTrackApiClient, MutaTrackApiError, MutaTrackAuthError
from .const import DOMAIN, FIELD_INDEX

_LOGGER = logging.getLogger(__name__)


class MutaTrackCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinates polling and parses the raw field array into a name-keyed dict."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api_client: MutaTrackApiClient,
        scan_interval_seconds: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=timedelta(seconds=scan_interval_seconds),
        )
        self._api_client = api_client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            raw_fields = await self._api_client.async_get_device_data()
        except MutaTrackAuthError as err:
            # Distinct from a generic UpdateFailed so entities/diagnostics can
            # tell "cloud auth is broken" apart from "device looks offline".
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except MutaTrackApiError as err:
            raise UpdateFailed(f"Error communicating with ValueClouds API: {err}") from err

        return _parse_fields(raw_fields)


def _parse_fields(raw_fields: list[Any]) -> dict[str, Any]:
    """Map the raw positional array onto named fields, tolerant of short arrays.

    Field map is unverified (see docs/api-reference.md) — a firmware/model
    variance could shift indices without warning, so a missing index is
    treated as "not currently available" rather than an error.
    """
    parsed: dict[str, Any] = {}
    for name, one_indexed_position in FIELD_INDEX.items():
        zero_indexed_position = one_indexed_position - 1
        if 0 <= zero_indexed_position < len(raw_fields):
            parsed[name] = raw_fields[zero_indexed_position]
        else:
            parsed[name] = None
    return parsed
