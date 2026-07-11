"""The MutaTrack integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MutaTrackApiClient
from .const import (
    CONF_BATTERY_CAPACITY_KWH,
    CONF_DEVCODE,
    CONF_PN,
    CONF_SN,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
)
from .coordinator import MutaTrackCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MutaTrack from a config entry."""
    session = async_get_clientsession(hass)
    api_client = MutaTrackApiClient(
        session,
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
        pn=entry.data[CONF_PN],
        sn=entry.data[CONF_SN],
        devcode=entry.data[CONF_DEVCODE],
    )

    coordinator = MutaTrackCoordinator(
        hass,
        entry,
        api_client,
        scan_interval_seconds=DEFAULT_SCAN_INTERVAL_SECONDS,
        battery_capacity_kwh=entry.options.get(CONF_BATTERY_CAPACITY_KWH),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when options (e.g. battery capacity/type) change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
