#!/usr/bin/env python3
"""Local test harness for the ValueClouds API.

Validates login and (if PN/SN/devcode are known) device data retrieval
against a real account, without needing a running Home Assistant instance.
See docs/dev-setup.md for usage and docs/api-reference.md for what this is
meant to confirm.

This script imports the integration's own api.py/const.py directly (via
importlib, bypassing custom_components/mutatrack/__init__.py, which has
Home Assistant-only imports) so the field map and API logic used here are
never a hand-maintained duplicate of what actually ships.

Usage:
    cp .env.example .env   # fill in credentials
    pip install -r requirements-dev.txt
    python3 scripts/api_harness.py
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

import aiohttp
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
MUTATRACK_DIR = REPO_ROOT / "custom_components" / "mutatrack"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"

_PKG_NAME = "_mutatrack_standalone"


def _load_standalone_mutatrack_modules():
    """Load const.py and api.py without executing __init__.py (HA-only imports)."""
    pkg = types.ModuleType(_PKG_NAME)
    pkg.__path__ = [str(MUTATRACK_DIR)]
    sys.modules[_PKG_NAME] = pkg

    def _load(modname: str, filename: str):
        spec = importlib.util.spec_from_file_location(
            f"{_PKG_NAME}.{modname}", MUTATRACK_DIR / filename
        )
        module = importlib.util.module_from_spec(spec)
        module.__package__ = _PKG_NAME
        sys.modules[f"{_PKG_NAME}.{modname}"] = module
        spec.loader.exec_module(module)
        return module

    const = _load("const", "const.py")
    api = _load("api", "api.py")
    return const, api


const, api = _load_standalone_mutatrack_modules()


async def main() -> int:
    load_dotenv(REPO_ROOT / ".env")

    email = os.environ.get("VALUECLOUDS_EMAIL")
    password = os.environ.get("VALUECLOUDS_PASSWORD")
    pn = os.environ.get("VALUECLOUDS_PN") or None
    sn = os.environ.get("VALUECLOUDS_SN") or None
    devcode = os.environ.get("VALUECLOUDS_DEVCODE") or None

    if not email or not password:
        print(
            "VALUECLOUDS_EMAIL and VALUECLOUDS_PASSWORD must be set in .env "
            "(copy .env.example first).",
            file=sys.stderr,
        )
        return 1

    async with aiohttp.ClientSession() as session:
        client = api.MutaTrackApiClient(
            session, email=email, password=password, pn=pn or "", sn=sn or "", devcode=devcode or ""
        )

        print(f"Logging in as {email} ...")
        try:
            token = await client.async_login()
        except api.MutaTrackAuthError as err:
            print(f"AUTH FAILED: {err}", file=sys.stderr)
            return 1
        except api.MutaTrackApiError as err:
            print(f"REQUEST FAILED: {err}", file=sys.stderr)
            return 1

        print(f"Login OK. Token (truncated): {token[:8]}...")

        if not (pn and sn and devcode):
            print(
                "\nVALUECLOUDS_PN/SN/DEVCODE not set — stopping after login-only "
                "check. No device-list discovery endpoint is confirmed yet "
                "(see docs/api-reference.md); capture PN/SN/devcode manually "
                "via browser DevTools on the SmartValue/ValueClouds web app "
                "and re-run to validate device data."
            )
            return 0

        print(f"\nFetching device data for pn={pn} sn={sn} devcode={devcode} ...")
        try:
            raw_fields = await client.async_get_device_data()
        except api.MutaTrackApiError as err:
            print(f"DEVICE DATA REQUEST FAILED: {err}", file=sys.stderr)
            return 1

        print(f"\nRaw field array ({len(raw_fields)} values):")
        print(json.dumps(raw_fields, indent=2))

        print("\nMapped against const.FIELD_INDEX (1-indexed):")
        index_to_name = {v: k for k, v in const.FIELD_INDEX.items()}
        for one_indexed_pos in sorted(index_to_name):
            name = index_to_name[one_indexed_pos]
            zero_indexed_pos = one_indexed_pos - 1
            value = (
                raw_fields[zero_indexed_pos]
                if zero_indexed_pos < len(raw_fields)
                else "<out of range>"
            )
            print(f"  [{one_indexed_pos:2}] {name:35} = {value!r}")

        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
        fixture_path = FIXTURES_DIR / "sample_device_data.json"
        fixture_path.write_text(
            json.dumps(
                {
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                    "note": "Credentials/PN/SN scrubbed. Raw field array only.",
                    "field_count": len(raw_fields),
                    "raw_fields": raw_fields,
                },
                indent=2,
            )
        )
        print(f"\nSaved raw sample (no credentials) to {fixture_path}")
        print(
            "\nNext: compare the printed mapping against what you know is "
            "actually true for your inverter, then record confirmations or "
            "corrections in docs/api-reference.md's 'Live validation "
            "findings' section."
        )
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
