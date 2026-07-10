"""Thin async client for the ValueClouds cloud API.

Endpoint/auth details are unverified against official documentation — see
docs/api-reference.md. This client intentionally does no field-name mapping
of its own; it hands back the raw positional array and lets sensor.py
(via const.FIELD_INDEX) decide what to do with it, so a field-map
correction never requires touching this file.
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import (
    DEFAULT_DEVADDR,
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    DEVICE_DATS_ENDPOINT,
    HEADER_I18N,
    HEADER_PROJECT,
    LOGIN_ENDPOINT,
)

_LOGGER = logging.getLogger(__name__)


class MutaTrackApiError(Exception):
    """Generic error talking to the ValueClouds API."""


class MutaTrackAuthError(MutaTrackApiError):
    """Raised when login fails or the session token is rejected."""


class MutaTrackApiClient:
    """Client for the ValueClouds cloud API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        email: str,
        password: str,
        pn: str,
        sn: str,
        devcode: str,
    ) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._pn = pn
        self._sn = sn
        self._devcode = devcode
        self._token: str | None = None

    async def async_login(self) -> str:
        """Log in and cache the session token. Raises MutaTrackAuthError on failure."""
        payload = {"email": self._email, "password": self._password}
        try:
            async with self._session.post(LOGIN_ENDPOINT, json=payload) as resp:
                if resp.status != 200:
                    raise MutaTrackAuthError(
                        f"Login failed with HTTP status {resp.status}"
                    )
                body = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise MutaTrackApiError(f"Login request failed: {err}") from err

        token = (body or {}).get("data", {}).get("token")
        if not token:
            raise MutaTrackAuthError("Login response did not include a token")

        self._token = token
        return token

    async def async_get_device_data(self) -> list[Any]:
        """Fetch the raw positional field array for the configured device.

        Logs in first if there is no cached token. On a 401/403 (token
        rejected), performs exactly one reactive re-login and retry, matching
        the observed behavior of the reference implementation (see
        docs/api-reference.md) rather than a proactive TTL-based refresh.
        """
        if self._token is None:
            await self.async_login()

        try:
            return await self._async_fetch_device_data()
        except MutaTrackAuthError:
            _LOGGER.debug("Token rejected, re-authenticating and retrying once")
            await self.async_login()
            return await self._async_fetch_device_data()

    async def _async_fetch_device_data(self) -> list[Any]:
        params = {
            "page": DEFAULT_PAGE,
            "pageSize": DEFAULT_PAGE_SIZE,
            "devaddr": DEFAULT_DEVADDR,
            "devcode": self._devcode,
            "pn": self._pn,
            "sn": self._sn,
        }
        headers = {
            "Token": self._token or "",
            "project": HEADER_PROJECT,
            "i18n": HEADER_I18N,
        }
        try:
            async with self._session.get(
                DEVICE_DATS_ENDPOINT, params=params, headers=headers
            ) as resp:
                if resp.status in (401, 403):
                    raise MutaTrackAuthError(
                        f"Device data request rejected with HTTP status {resp.status}"
                    )
                if resp.status != 200:
                    raise MutaTrackApiError(
                        f"Device data request failed with HTTP status {resp.status}"
                    )
                body = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise MutaTrackApiError(f"Device data request failed: {err}") from err

        rows = (body or {}).get("data", {}).get("row") or []
        if not rows:
            raise MutaTrackApiError("Device data response contained no rows")

        fields = rows[0].get("field")
        if not isinstance(fields, list):
            raise MutaTrackApiError("Device data response 'field' was not a list")

        return fields
