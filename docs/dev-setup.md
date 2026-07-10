# Local Dev Setup

Status: harness confirmed working end-to-end against a real account
(2026-07-10) — login and device data fetch both succeed live. Not yet
tested inside an actual Home Assistant instance.

## API test harness

`scripts/api_harness.py` is a standalone script (outside
`custom_components/`) for validating the ValueClouds API directly, without
needing a full Home Assistant instance running. It imports the
integration's own `api.py`/`const.py` directly via `importlib` (bypassing
`custom_components/mutatrack/__init__.py`, which has Home Assistant-only
imports), so the request logic it exercises is never a hand-maintained
duplicate of what actually ships.

### Setup

```bash
cp .env.example .env        # fill in real credentials, this file is gitignored
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python3 scripts/api_harness.py
```

### Credentials

- `.env` (gitignored, never commit): `VALUECLOUDS_EMAIL`,
  `VALUECLOUDS_PASSWORD`, `VALUECLOUDS_PN`, `VALUECLOUDS_SN`,
  `VALUECLOUDS_DEVCODE`.
- **No device-list discovery endpoint exists** (confirmed absent during
  live capture — see docs/api-reference.md). PN/SN/devcode must be
  captured manually: open the SmartValue/ValueClouds web app, open browser
  DevTools → Network tab, and inspect the query string of a
  `queryDeviceOneDataxxx` (or similar `ppe/api/auth/web/...`) request.
  Leaving these blank in `.env` runs the harness in login-only mode.
- **Handling `.env` in this session:** don't `cat`/`grep` the raw file
  when checking whether it's populated — that echoes plaintext credentials
  into whatever transcript/log is capturing tool output. Use a masked
  check instead, e.g.:
  `awk -F= '/^VALUECLOUDS_/{print $1"="($2==""?"<empty>":"<set>")}' .env`

### What the harness does

1. `POST /ppr/web/login/login` — confirms auth works, prints a truncated
   token. Uses the corrected `{account, sha1(password), project}` shape
   (see docs/api-reference.md) — the originally-documented plaintext
   `{email, password}` shape does not work.
2. If PN/SN/devcode are set, calls `GET .../queryDeviceOneDataxxx` and
   prints every returned field (self-describing `id`/`title`/`unit`/`val`,
   no index-guessing needed), flagging which ones fall into
   `const.PRIMARY_TELEMETRY_IDS` (core sensors) vs. diagnostic-only.
3. Saves the raw field list (credentials scrubbed, but real PN/SN
   included) to `tests/fixtures/sample_device_data.json` for use in mocked
   unit tests.

## Testing against a real HA instance

_(Not yet done. Next step: HA dev container or `custom_components`
symlink into a test HA config, then walk through the config flow UI and
confirm sensors register correctly, Energy Dashboard picks up the energy
entities, and diagnostics download works.)_
