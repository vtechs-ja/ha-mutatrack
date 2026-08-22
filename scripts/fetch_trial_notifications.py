#!/usr/bin/env python3
"""Fetch persistent_notification.* entities from the live HA instance.

Used to review the power-comfort trial's output (see
docs/ha-automations.md) without needing a text-file notify target/HA
restart — persistent_notification entities are already queryable over the
REST API.

Reads HA_URL / HA_TOKEN from .env (see docs/dev-setup.md).
"""
import json
import os
import sys
import urllib.request

from dotenv import load_dotenv

load_dotenv()

HA_URL = os.environ["HA_URL"].rstrip("/")
HA_TOKEN = os.environ["HA_TOKEN"]


def main() -> None:
    title_filter = sys.argv[1] if len(sys.argv) > 1 else None

    req = urllib.request.Request(
        f"{HA_URL}/api/states",
        headers={"Authorization": f"Bearer {HA_TOKEN}"},
    )
    with urllib.request.urlopen(req) as resp:
        states = json.load(resp)

    for entity in states:
        if not entity["entity_id"].startswith("persistent_notification."):
            continue
        title = entity["attributes"].get("title", "")
        if title_filter and title_filter not in title:
            continue
        print(f"[{entity['last_updated']}] {title}")
        print(f"  {entity['attributes'].get('message', entity['state'])}")
        print()


if __name__ == "__main__":
    main()
