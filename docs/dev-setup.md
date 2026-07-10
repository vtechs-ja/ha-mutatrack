# Local Dev Setup

Status: planned, not yet implemented (see IMPLEMENTATION_PLAN.md Phase 2).

## API test harness

A standalone script (outside `custom_components/`) for validating the
ValueClouds API directly, without needing a full Home Assistant instance
running.

### Credentials

- Copy `.env.example` to `.env` (gitignored, never commit) and fill in:
  - `VALUECLOUDS_EMAIL`
  - `VALUECLOUDS_PASSWORD`
- The harness loads these from `.env` — do not hardcode credentials in any
  script or fixture.

### What the harness should do

1. `POST /ppr/web/login/login` — confirm auth works, capture the session
   token.
2. Discover the account's device list (endpoint TBD — investigate whether
   one exists separate from `deviceDats`) to confirm PN/SN/devcode rather
   than requiring manual DevTools lookup.
3. `GET /drt/api/auth/web/deviceDats` with the discovered PN/SN/devcode —
   capture one raw response.
4. Cross-check the raw positional array against
   `docs/api-reference.md`'s hypothesized field map; record confirmations
   or corrections there.
5. Save the raw response as a fixture (with credentials/PII scrubbed) for
   use in mocked unit tests.

## Testing against a real HA instance

_(To be filled in once Phase 1 sensor/config_flow code exists — e.g. HA
dev container, `custom_components` symlink into a test HA config, manual
config-flow walkthrough.)_
