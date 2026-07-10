# ValueClouds API Reference

Status: unverified — reverse-engineered from a community gist for a
*different* inverter unit. Everything here needs live validation against
Deron's actual account/device (Phase 2 of IMPLEMENTATION_PLAN.md) before it
should be treated as trustworthy in shipped sensor code.

Source: [Ig0rr0/valueclouds](https://github.com/Ig0rr0/valueclouds) gist,
cross-referenced in the [Confluence product doc](https://vtechs.atlassian.net/wiki/spaces/VTechEng/pages/59506690/MutaTrack+Product+Brief+Starter+Tech+Spec+Roadmap).

## Authentication

| Item | Detail |
| --- | --- |
| Login endpoint | `POST https://api.valueclouds.com/ppr/web/login/login` |
| Payload | JSON body with account email + password |
| Response | `data.token` — session token, no documented expiry |
| Token use | `Token` header on subsequent requests |
| Refresh pattern (observed) | Reactive re-login on HA start and on sensor `unavailable`, not a proactive TTL-based refresh |

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

_(Empty until Phase 2 runs the test harness against the real account. Record
confirmed devcode, PN/SN, and any field-index corrections here.)_
