"""Thin async client for the ValueClouds cloud API.

Login and device-data shapes below are confirmed against live traffic
2026-07-10 (see docs/api-reference.md) — not the originally-documented
(and incorrect) shapes from the reverse-engineered community gist. This
client hands back the raw list of {id, title, unit, val, ...} dicts from
queryDeviceOneDataxxx untouched; coordinator.py decides what to do with it,
so a field-list change never requires touching this file.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import aiohttp

from .const import (
    DEFAULT_DEVADDR,
    DEFAULT_I18N,
    DEVICE_ONE_DATA_ENDPOINT,
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
        self._secret: str | None = None

    async def async_login(self) -> str:
        """Log in and cache the session token. Raises MutaTrackAuthError on failure.

        Confirmed against live traffic 2026-07-10: the login body requires
        `account` (not `email`), a client-side SHA1 hash of the plaintext
        password (not the plaintext itself), and a `project` field ("IOT")
        identifying the white-label tenant — none of which were in the
        original reverse-engineered doc. The API also returns HTTP 200 on
        both success AND failure; the real signal is the `success`/`code`
        fields in the JSON body, not the HTTP status. See
        docs/api-reference.md for full details.
        """
        hashed_password = hashlib.sha1(self._password.encode("utf-8")).hexdigest()
        payload = {
            "account": self._email,
            "password": hashed_password,
            "project": "IOT",
        }
        try:
            async with self._session.post(LOGIN_ENDPOINT, json=payload) as resp:
                if resp.status != 200:
                    raise MutaTrackAuthError(
                        f"Login failed with HTTP status {resp.status}"
                    )
                body = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise MutaTrackApiError(f"Login request failed: {err}") from err

        if not (body or {}).get("success"):
            message = (
                (body or {}).get("message")
                or (body or {}).get("errorMessage")
                or "Login was rejected"
            )
            raise MutaTrackAuthError(message)

        data = (body or {}).get("data") or {}
        token = data.get("token")
        if not token:
            raise MutaTrackAuthError("Login response did not include a token")

        self._token = token
        self._secret = data.get("secret")
        return token

    async def async_get_device_data(self) -> list[dict[str, Any]]:
        """Fetch the raw list of named field readings for the configured device.

        Logs in first if there is no cached token. On an auth-rejection
        response, performs exactly one reactive re-login and retry, matching
        the observed behavior of the reference implementation (see
        docs/api-reference.md) rather than a proactive TTL-based refresh.

        Uses queryDeviceOneDataxxx (confirmed live 2026-07-10), which
        returns self-describing {id, title, unit, val, packetname, ...}
        entries — not the originally-documented deviceDats endpoint, which
        returns an undocumented positional array with no way to verify
        field ordering. See docs/api-reference.md for the full endpoint
        catalogue, including other discovered endpoints not yet used here.
        """
        if self._token is None:
            await self.async_login()

        try:
            return await self._async_fetch_device_data()
        except MutaTrackAuthError:
            _LOGGER.debug("Token rejected, re-authenticating and retrying once")
            await self.async_login()
            return await self._async_fetch_device_data()

    async def _async_fetch_device_data(self) -> list[dict[str, Any]]:
        params = {
            "pn": self._pn,
            "sn": self._sn,
            "devcode": self._devcode,
            "devaddr": DEFAULT_DEVADDR,
            "i18n": DEFAULT_I18N,
        }
        headers = {
            "Token": self._token or "",
            "project": HEADER_PROJECT,
            "i18n": DEFAULT_I18N,
        }
        try:
            async with self._session.get(
                DEVICE_ONE_DATA_ENDPOINT, params=params, headers=headers
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

        # Confirmed live 2026-07-10: this API returns HTTP 200 on both
        # success and failure — check the body's own success signal, not
        # just HTTP status.
        if (body or {}).get("success") is False:
            code = (body or {}).get("code")
            message = (body or {}).get("message") or "Device data request failed"
            if code in (401, 403) or "token" in message.lower() or "auth" in message.lower():
                raise MutaTrackAuthError(message)
            raise MutaTrackApiError(message)

        fields = (body or {}).get("data")
        if not isinstance(fields, list):
            raise MutaTrackApiError("Device data response 'data' was not a list")

        return fields
