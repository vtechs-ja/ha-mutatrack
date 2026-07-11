# Integration Architecture

Status: Phase 1 implemented and revised after live API validation
(2026-07-10) — login and the primary data endpoint are both confirmed
working against a real account via `scripts/api_harness.py`. Not yet run
inside an actual Home Assistant instance (config flow UI, entity
registration, Energy Dashboard wiring are all still unverified in that
context).

## Layout

```
custom_components/mutatrack/
├── __init__.py          # Setup, config entry, coordinator wiring
├── manifest.json         # Integration metadata, HACS-compatible structure
├── config_flow.py        # UI form: email, password, PN/SN/devcode entry
├── coordinator.py        # DataUpdateCoordinator: login, token cache, poll, re-auth on auth failure
├── api.py                 # Thin ValueClouds API client (login, queryDeviceOneDataxxx)
├── sensor.py               # Dynamically builds entities from whatever fields the API returns
├── forecast.py              # v1.5 battery runtime forecast engine (naive + rolling-average tiers, empirical capacity self-correction)
├── const.py                 # Endpoint URLs, defaults, PRIMARY_TELEMETRY_IDS/ENERGY_FIELD_IDS
├── diagnostics.py            # Redacted diagnostics download
└── strings.json / translations/en.json
```

## Key design decisions

| Decision | Rationale |
| --- | --- |
| One `DataUpdateCoordinator` per device, single API call per poll cycle | Avoids redundant polling; matches HA integration best practice |
| Config flow captures email/password + manual PN/SN/devcode, with a live login test before saving | No confirmed device-list discovery endpoint exists (see docs/api-reference.md), so manual DevTools capture is still required; login validation at least catches bad credentials immediately |
| **Data source: `queryDeviceOneDataxxx`, not the originally-documented `deviceDats`** | `deviceDats` returns an undocumented positional array requiring index-guessing with no way to verify correctness. `queryDeviceOneDataxxx` returns self-describing `{id, title, unit, val}` fields — confirmed live 2026-07-10. This eliminates the field-mapping risk the original Confluence doc flagged as a top concern. |
| **Entities built dynamically from the API response, not a static hardcoded list** | Since fields are now self-describing, `sensor.py` builds one entity per field id present in `coordinator.data` at setup time, using the API's own `title`/`unit` rather than a hand-maintained table. A unit→device_class lookup (`sensor.UNIT_TO_DEVICE_CLASS`) handles the common cases (V/A/W/Hz/°C/kWh); unmapped units still get a working sensor, just without device_class coercion. |
| `const.PRIMARY_TELEMETRY_IDS` (48 ids) marks core sensors vs. diagnostic | Confirmed live to be a strict subset of `queryDeviceOneDataxxx`'s 115 ids — matching ids become regular sensors, the rest (settings/control-read values, machine info) become `EntityCategory.DIAGNOSTIC` sensors. One API call serves both purposes. |
| Entity availability reflects auth/API failure distinctly from "device offline" | Lets downstream automations distinguish "cloud unreachable" from "inverter actually off" |
| API layer checks the response body's `success`/`code`, not just HTTP status | Confirmed live: this API returns HTTP 200 on both success and failure |

## v1 boundary

Read-only monitoring only. No `select`/`number` platforms, no
settings-write API calls — even though `queryDeviceOneDataxxx` surfaces
current settings values (exposed as read-only diagnostics), no write
endpoint has been probed or will be without explicit direction. See
docs/api-reference.md's "Write endpoint" note.

## v1.5 — battery runtime forecasting

`forecast.py` implements `BatteryForecastEngine`, fed by `coordinator.py` on
every poll (no new API calls). Design writeup: Confluence "Feature Roadmap
& Open Questions" v1.5 section.

- **Capacity is not present anywhere in the API response** (SOC is
  percentage-only), so it's resolved as: user-configured value (options
  flow, optional) if set, else an empirically-derived estimate from
  observed charge/discharge cycles (energy delta ÷ SOC delta, folded into
  an EMA), else unavailable.
- **Deviation detection**: if both a configured and an empirical capacity
  exist and disagree by more than 20%, an HA repair issue is raised
  (`battery_capacity_deviation`) — doubles as a degradation signal over the
  battery's life.
- Implemented tiers: naive instantaneous rate, rolling 30-minute average
  discharge rate. **Not implemented**: the time-of-day recorder-history
  pattern tier — tracked as a follow-up, not this first cut.
- Exposed as `sensor.mutatrack_battery_time_remaining` (device_class
  `duration`, minutes), with `rate_method`/`capacity_source`/`capacity_kwh`/
  `calibration_confidence`/`observed_cycles` as attributes for
  transparency.
- **In-memory only**: calibration state (empirical capacity EMA, cycle
  count) resets on integration reload/HA restart. Acceptable for this first
  cut; revisit if reconvergence time proves annoying in practice.
- Options flow (`config_flow.py::MutaTrackOptionsFlow`) lets capacity/type
  be set or changed post-setup; changing either reloads the config entry.

## Open technical risks

- **Firmware/field-set drift**: entities are built once at setup from
  whatever fields were present on the first poll. If a firmware update
  adds/removes/renames fields, that only gets picked up on integration
  reload, not live. Acceptable for v1 given this vendor's field set is
  unlikely to change often, but worth revisiting if it becomes an issue.
- API stability — undocumented cloud API, no versioning guarantee (the
  sibling DessMonitor integration has already broken once from an
  unannounced API change). The original doc's `deviceDats`/login shapes
  being wrong is a live example of how little can be assumed here.
- Rate limiting / ToS — unknown, worth a light review before any public
  HACS submission.
- Multi-tenant white-label question — unconfirmed whether other Eybond
  tenants share this API shape (v3 scope, not now).
- `device/warnings` endpoint auth requirement unresolved — not blocking v1.
