# ValueClouds API Reference

Status: partially verified live against Deron's real account on 2026-07-10
(login only so far). Original field-index map below is still
unverified — reverse-engineered from a community gist for a *different*
inverter unit. See "Live validation findings" at the bottom for what's
confirmed vs. still hypothesis.

Source: [Ig0rr0/valueclouds](https://github.com/Ig0rr0/valueclouds) gist,
cross-referenced in the [Confluence product doc](https://vtechs.atlassian.net/wiki/spaces/VTechEng/pages/59506690/MutaTrack+Product+Brief+Starter+Tech+Spec+Roadmap).

## Authentication — CORRECTED 2026-07-10 against live traffic

The original doc's login shape (`{email, password}`, no extra fields) does
**not** work — it returns `code 24` ("corresponding project not found").
Confirmed working shape, captured from real browser DevTools traffic:

| Item | Detail |
| --- | --- |
| Login endpoint | `POST https://api.valueclouds.com/ppr/web/login/login` |
| Payload | `{"account": <email>, "password": <sha1_hex_of_plaintext_password>, "project": "IOT"}` — note field is `account`, not `email`; password is client-side SHA1-hashed, not sent plaintext; `project` is a required tenant identifier |
| Success response | HTTP 200, body `{"code": 0, "success": true, "data": {"token", "secret", "account", "userId", ...}}` |
| Failure response | **Also HTTP 200** — failure is signaled only by `"success": false` and a nonzero `code` in the body (e.g. `code 24` = project missing/wrong, `code 115140` = bad account/password). Any client must check the body, not just HTTP status. |
| Token use | `Token` header on subsequent requests (assumed, consistent with deviceDats usage — not yet independently re-confirmed post-fix) |
| `secret` field | New finding, not in the original doc. Purpose unconfirmed — possibly used for request signing on other endpoints. Not yet used by the integration; worth investigating if other endpoints require it. |
| Refresh pattern (observed) | Reactive re-login on HA start and on sensor `unavailable`, not a proactive TTL-based refresh (this part of the original doc still stands) |

`custom_components/mutatrack/api.py` has been updated to match this
confirmed shape as of the same date.

## Data endpoint

| Item | Detail |
| --- | --- |
| Endpoint | `GET https://api.valueclouds.com/drt/api/auth/web/deviceDats` |
| Query params | `page, pageSize, devaddr, devcode, pn, sn, date` |
| Headers | `Token`, `project: IOT`, `i18n: ru_RU` |
| Response shape | `data.row[0].field` — flat positional array of ~45 values, no field names |
| Observed polling cadence | Every 5 min in the reference gist; device pushes to app roughly every 5 min |

## Field index map (hypothesis — unverified against this account)

| Index | Field | Unit |
| --- | --- | --- |
| 1 | Last update timestamp | — |
| 2 | Battery voltage | V |
| 3 | PV1 voltage | V |
| 4 | PV2 voltage | V |
| 5 | Inverter voltage | V |
| 6 | BMS battery voltage | V |
| 7 | Load current | A |
| 8 | Battery current | A |
| 9 | PV1 charger current | A |
| 10 | BMS battery current | A |
| 11 | PV2 charger current | A |
| 12 | PV1 charger power | W |
| 13 | PV2 charger power | W |
| 14 | PV total power | W |
| 15 | Battery SOC | % |
| 16 | Load power | W |
| 17 | Grid power | W |
| 18 | Work state (OffGrid/OnGrid) | — |
| 19 | Grid voltage | V |
| 20 | Software version | — |
| 21 | Rated power | W |
| 22 | Inverter current | A |
| 23 | Grid current | A |
| 24 | Inverter active power | W |
| 25–30 | Apparent/reactive power (inverter, grid, load) | VA / var |
| 31–32 | Inverter / grid frequency | Hz |
| 33–35 | AC radiator / transformer / DC radiator temperature | °C |
| 36–41 | Accumulated charge / discharge / buy / sell / load / self-use energy | kWh |
| 42 | Battery power | W |
| 43 | Charger work enable | — |
| 44 | PV cumulative generation | kWh |
| 45 | BMS battery temperature | °C |

## Known gaps

- No write/control endpoints identified — out of scope for v1/v2 research
  gate, see IMPLEMENTATION_PLAN.md and Confluence roadmap.
- No official API docs, versioning, or rate-limit info.
- No confirmed token TTL / refresh-token flow.
- Deron's exact inverter devcode/model is unconfirmed — this is the first
  thing Phase 2 needs to establish.

## Live validation findings

**2026-07-10 — Login (confirmed):**
- Original doc's login payload/response assumptions were wrong; corrected
  shape is documented above and implemented in `api.py`.
- Confirmed: this API returns HTTP 200 on both success and failure — any
  future endpoint work must check the body's `success`/`code` fields, not
  rely on HTTP status alone. `api.py`'s device-data path has been
  defensively updated to do this too, though that specific path is not yet
  independently re-confirmed live (blocked on PN/SN/devcode below).
- New/unexplained field: login response includes a `secret` value not
  present in the original doc. Not yet used anywhere; flag for
  investigation if other endpoints turn out to need it (e.g. for request
  signing).

**Still open (blocked on PN/SN/devcode capture):**
- Field-index map (45 positional fields) — unverified.
- `Token` header usage on `deviceDats` — assumed consistent with the
  now-corrected login flow, not independently re-tested post-fix.
- Deron's exact inverter devcode/model.
- Whether a device-list discovery endpoint exists (none found/documented
  yet).
