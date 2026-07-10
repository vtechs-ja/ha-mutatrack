"""Diagnostics support for MutaTrack."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .const import CONF_SN, DOMAIN

TO_REDACT = {CONF_EMAIL, CONF_PASSWORD, CONF_SN}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry, with credentials/PII redacted."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    return {
        "config_entry_data": async_redact_data(dict(config_entry.data), TO_REDACT),
        "coordinator_data": coordinator.data,
        "last_update_success": coordinator.last_update_success,
    }
