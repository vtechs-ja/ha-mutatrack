"""Config flow for MutaTrack.

v1.1 (per IMPLEMENTATION_PLAN.md) adds config-flow validation and re-auth
flow improvements; this is the v1 baseline: email/password + manual PN/SN
override, with a login test before saving so a bad password fails fast
instead of surfacing as a mysterious "unavailable" sensor later.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MutaTrackApiClient, MutaTrackApiError, MutaTrackAuthError
from .const import (
    BATTERY_TYPE_OPTIONS,
    BATTERY_TYPE_UNSPECIFIED,
    CONF_BATTERY_CAPACITY_KWH,
    CONF_BATTERY_TYPE,
    CONF_DEVCODE,
    CONF_PN,
    CONF_SN,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_PN): str,
        vol.Required(CONF_SN): str,
        vol.Required(CONF_DEVCODE): str,
    }
)


class MutaTrackConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MutaTrack."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(
                f"{user_input[CONF_PN]}_{user_input[CONF_SN]}"
            )
            self._abort_if_unique_id_configured()

            try:
                await _async_validate_credentials(self.hass, user_input)
            except MutaTrackAuthError:
                errors["base"] = "invalid_auth"
            except MutaTrackApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating MutaTrack credentials")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"MutaTrack ({user_input[CONF_PN]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> MutaTrackOptionsFlow:
        return MutaTrackOptionsFlow(config_entry)


class MutaTrackOptionsFlow(config_entries.OptionsFlow):
    """Optional v1.5 battery capacity/type, editable after initial setup.

    Capacity is a free-text field (not a NumberSelector) so it can be left
    blank — the forecast engine falls back to an empirically-derived
    capacity when no value is configured, per the v1.5 design.
    """

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            raw_capacity = user_input.get(CONF_BATTERY_CAPACITY_KWH, "").strip()
            if not raw_capacity:
                capacity_kwh: float | None = None
            else:
                try:
                    capacity_kwh = float(raw_capacity)
                    if capacity_kwh <= 0:
                        raise ValueError
                except ValueError:
                    errors[CONF_BATTERY_CAPACITY_KWH] = "invalid_capacity"

            if not errors:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_BATTERY_CAPACITY_KWH: capacity_kwh,
                        CONF_BATTERY_TYPE: user_input.get(
                            CONF_BATTERY_TYPE, BATTERY_TYPE_UNSPECIFIED
                        ),
                    },
                )

        current_capacity = self.config_entry.options.get(CONF_BATTERY_CAPACITY_KWH)
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_BATTERY_CAPACITY_KWH,
                    default=str(current_capacity) if current_capacity is not None else "",
                ): str,
                vol.Optional(
                    CONF_BATTERY_TYPE,
                    default=self.config_entry.options.get(
                        CONF_BATTERY_TYPE, BATTERY_TYPE_UNSPECIFIED
                    ),
                ): vol.In(BATTERY_TYPE_OPTIONS),
            }
        )
        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors
        )


async def _async_validate_credentials(hass, data: dict[str, Any]) -> None:
    """Attempt a login to confirm credentials work before saving the entry."""
    session = async_get_clientsession(hass)
    client = MutaTrackApiClient(
        session,
        email=data[CONF_EMAIL],
        password=data[CONF_PASSWORD],
        pn=data[CONF_PN],
        sn=data[CONF_SN],
        devcode=data[CONF_DEVCODE],
    )
    await client.async_login()


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
