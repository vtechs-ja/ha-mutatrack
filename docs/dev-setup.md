# Local Dev Setup

Status: harness implemented (`scripts/api_harness.py`), not yet run against
a real account (see IMPLEMENTATION_PLAN.md Phase 2).

## API test harness

`scripts/api_harness.py` is a standalone script (outside
`custom_components/`) for validating the ValueClouds API directly, without
needing a full Home Assistant instance running. It imports the
integration's own `api.py`/`const.py` directly via `importlib` (bypassing
`custom_components/mutatrack/__init__.py`, which has Home Assistant-only
imports), so the field map and request logic it exercises are never a
hand-maintained duplicate of what actually ships.

### Setup

```bash
cp .env.example .env        # fill in real credentials, this file is gitignored
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python3 scripts/api_harness.py
```

### Credentials

- `.env` (gitignored, never commit): `VALUECLOUDS_EMAIL`,
  `VALUECLOUDS_PASSWORD`, plus optionally `VALUECLOUDS_PN`,
  `VALUECLOUDS_SN`, `VALUECLOUDS_DEVCODE`.
- **No device-list discovery endpoint is confirmed yet** — the ValueClouds
  API doesn't document one, and none was found in the reference gist. Until
  one is researched, PN/SN/devcode must be captured manually: open the
  SmartValue/ValueClouds web app, open browser DevTools → Network tab, and
  inspect the query string of a `deviceDats` request. Leaving these blank
  in `.env` runs the harness in login-only mode.
- If a discovery endpoint *is* found during this manual capture (e.g. an
  account/device-list call the web app makes before `deviceDats`), record
  it in `docs/api-reference.md` and this becomes a good follow-up
  enhancement to the harness/config flow.

### What the harness does

1. `POST /ppr/web/login/login` — confirms auth works, prints a truncated
   token.
2. If PN/SN/devcode are set, calls `GET /drt/api/auth/web/deviceDats` and
   prints the raw positional array alongside its mapping through
   `const.FIELD_INDEX`, so you can eyeball each value against what you
   actually observe on the inverter/app at that moment.
3. Saves the raw array (credentials/PII scrubbed) to
   `tests/fixtures/sample_device_data.json` for use in mocked unit tests.
4. Does **not** auto-edit docs — after running, manually record
   confirmations/corrections in `docs/api-reference.md`'s "Live validation
   findings" section based on what you observed.

## Testing against a real HA instance

_(To be filled in once Phase 1 sensor/config_flow code exists — e.g. HA
dev container, `custom_components` symlink into a test HA config, manual
config-flow walkthrough.)_
