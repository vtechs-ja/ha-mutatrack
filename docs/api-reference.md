# ValueClouds API Reference

Status: authentication and the primary v1 data endpoint are both confirmed
live against Deron's real account (2026-07-10). The original doc's login
shape and its `deviceDats` positional field map were both **wrong** — see
below for corrections. Several additional endpoints were also discovered
during live capture; some are confirmed working, one is not yet accessible
(auth gap).

Original source: [Ig0rr0/valueclouds](https://github.com/Ig0rr0/valueclouds)
gist, cross-referenced in the [Confluence product doc](https://vtechs.atlassian.net/wiki/spaces/VTechEng/pages/59506690/MutaTrack+Product+Brief+Starter+Tech+Spec+Roadmap) —
that doc was built against a *different* inverter unit's community gist and
should now be treated as a starting hint only, not ground truth. This file
supersedes it on every point of conflict.

## Authentication — CORRECTED 2026-07-10 against live traffic

The original doc's login shape (`{email, password}`, no extra fields) does
**not** work — it returns `code 24` ("corresponding project not found").
Confirmed working shape, captured from real browser DevTools traffic:

| Item | Detail |
| --- | --- |
| Login endpoint | `POST https://api.valueclouds.com/ppr/web/login/login` |
| Payload | `{"account": <email>, "password": <sha1_hex_of_plaintext_password>, "project": "IOT"}` — field is `account`, not `email`; password is client-side SHA1-hashed, not sent plaintext; `project` is a required tenant identifier |
| Success response | HTTP 200, body `{"code": 0, "success": true, "data": {"token", "secret", "account", "userId", ...}}` |
| Failure response | **Also HTTP 200** — failure is signaled only by `"success": false` and a nonzero `code` in the body (e.g. `code 24` = project missing/wrong, `code 115140` = bad account/password). Any client must check the body, not just HTTP status. |
| Token use | `Token` header on subsequent requests — confirmed live via `queryDeviceOneDataxxx` |
| `secret` field | Returned but unused so far. Purpose unconfirmed — possibly used for request signing on endpoints we haven't gotten working yet (e.g. `device/warnings`, see below). |
| Refresh pattern | Reactive re-login on HA start and on sensor `unavailable`, not a proactive TTL-based refresh |

`custom_components/mutatrack/api.py` implements this confirmed shape.

## Primary v1 data endpoint — `queryDeviceOneDataxxx` (confirmed)

This replaces the originally-documented `deviceDats` endpoint entirely for
v1. Unlike `deviceDats`'s undocumented positional array, this endpoint
returns **self-describing named fields** — no index-guessing required.

| Item | Detail |
| --- | --- |
| Endpoint | `GET https://api.valueclouds.com/ppe/api/auth/web/queryDeviceOneDataxxx` |
| Query params | `pn, sn, devcode, devaddr, i18n` |
| Headers | `Token`, `project: IOT`, `i18n: en_US` |
| `devaddr` | **255** for Deron's account — the original doc's guess of `1` was wrong |
| `devcode` | **6409**, confirmed for Deron's inverter |
| Response shape | `data` = list of `{id, title, unit, val, packet, packetname, num, groupNumber, date, type}` — confirmed 115 fields live |
| Sample response | `tests/fixtures/queryDeviceOneDataxxx_sample.json` (git-ignored is not needed; scrubbed of credentials, contains real PN/SN — review before committing if that's a concern) |

**v1 sensor field selection:** `const.PRIMARY_TELEMETRY_IDS` (48 ids) marks
which fields become regular sensors vs. diagnostic-category sensors. This
set was derived from `querySPDeviceLastData` (see below), confirmed live to
be a strict subset of `queryDeviceOneDataxxx`'s 115 ids — so a single API
call gets both core telemetry and settings-visibility, no second request
needed. See `docs/architecture.md`.

**Notable field categories observed (see sample fixture for the complete
115-field list):**
- Battery: voltage, current, SOC, charge status, battery type
- PV: per-string voltage/current/power, total power, today/total generation
- Output/load: per-phase voltage/current/power/apparent power/load %
- Grid/mains: per-phase voltage/current/power, today/total export
- Temperatures, hardware/firmware version, product type
- **Settings/control current values** (`eybond_ctrl_*_read` ids): output
  priority, charge current limits, voltage cutoffs/thresholds, time-of-day
  charge/discharge windows, and more — see "Write endpoint" note below.

## Other discovered endpoints (not used in v1 — reference for future work)

Captured from the same live browser session. Not wired into the
integration; keeping them here so Phase 2+ work doesn't have to
re-discover them.

| Endpoint | Status | Notes |
| --- | --- | --- |
| `GET /ppe/api/auth/web/querySPDeviceLastData` | Confirmed working | Same params as `queryDeviceOneDataxxx`. Returns 48 fields grouped under `data.pars.{gd_,pv_,sy_,bt_,bc_}` — pure telemetry, no settings fields. Confirmed a strict subset of `queryDeviceOneDataxxx`'s ids, which is why v1 doesn't call this separately. Sample: `tests/fixtures/querySPDeviceLastData_sample.json`. |
| `GET /ppe/api/auth/web/queryDeviceEnergyFlow` | Confirmed working | Returns a structured real-time power-flow summary: `bt_status` (battery), `pv_status`, `gd_status` (grid), `bc_status` (load), plus unused-for-this-inverter categories (oil/wind/micro/motor/pump/generator — likely shared schema across Eybond's broader product line). Good candidate for directly powering a future custom power-flow card/dashboard example without per-field math, and worth considering for v1.5's forecast.py math instead of deriving from individual sensors. |
| `GET /alm/api/auth/web/device/warnings` | **Not working** | Returns `code 306: "Missing authentication information"` even with a valid `Token` header. Likely needs an additional signed parameter (possibly using the `secret` from login) that we haven't reverse-engineered. Would provide device alerts/warnings for a future diagnostic/binary_sensor entity. Needs further DevTools capture (watch for this request when the app actually shows a warning, or capture whatever extra header/param the app sends) before it can be used. |
| `POST/GET /drt/api/auth/web/deviceDats` (original doc's endpoint) | Superseded, not re-verified | Original doc claimed this was the data endpoint; not tested against the corrected auth flow. No reason to revisit unless `queryDeviceOneDataxxx` stops working, since it offers strictly less (undocumented positional array vs. self-describing fields). |

### Write endpoint — deliberately not researched

The `eybond_ctrl_*_read` field ids in `queryDeviceOneDataxxx` strongly
suggest a companion write/set endpoint exists (mirroring DessMonitor's
reported settings-write API). **Per explicit decision, this has not been
probed or investigated further** — v2 (write support) is out of scope for
the current build. If picked up later, the safest path is passive: capture
what request fires when a setting is changed in the SmartValue app via
DevTools, rather than guessing at write endpoints against a live inverter.

## Known gaps

- Write/control endpoints — deliberately unresearched, see above.
- No official API docs, versioning, or rate-limit info.
- No confirmed token TTL / refresh-token flow.
- `device/warnings` auth requirement unresolved.
- Purpose of the login response's `secret` field is unconfirmed.
- Whether other Eybond white-label tenants (SmartESS, DessMonitor, etc.)
  share this exact API shape — v3 scope, not investigated.

## Live validation findings

**2026-07-10 — Login (confirmed):** see "Authentication" above. Real bug
caught: the originally-documented shape would have shipped a broken
integration; corrected and verified end-to-end via `scripts/api_harness.py`
against the real account.

**2026-07-10 — Device data (confirmed):** `deviceDats`'s field-index map
is abandoned in favor of `queryDeviceOneDataxxx`'s self-describing fields
(see above) — this eliminates the entire class of "is index 14 really PV
total power" risk the original doc carried. `devaddr` corrected from the
guessed `1` to the confirmed `255`. `devcode` confirmed as `6409`.
Full pipeline (login → fetch → parse) verified live via
`scripts/api_harness.py`.

**Still open:**
- `device/warnings` endpoint auth.
- `secret` field purpose.
- Whether `queryDeviceEnergyFlow` should replace some of v1.5's
  forecast.py math (not yet decided).
