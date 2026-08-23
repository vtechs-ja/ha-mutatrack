# HA Dashboard Built on MutaTrack Sensors ("Sundial")

Status: **already live** on the instance as of 2026-08-22 — discovered via
the HA WebSocket API while checking whether the repo's docs matched
reality. `IMPLEMENTATION_PLAN.md`'s Phase 5 entry for this ("not yet
converted from the design mockup into real Lovelace YAML or installed")
was stale; corrected there.

Like the automations in [docs/ha-automations.md](ha-automations.md), this
dashboard lives in HA's Lovelace storage, not this repo — MutaTrack only
supplies the underlying sensors. An export lives at
`ha-config/dashboards/dashboard-powertrack.yaml` for recreation/review; the
live dashboard (storage mode) is the actual source of truth.

## What's there

Dashboard id `dashboard_powertrack`, title "Sundial", url path
`dashboard-powertrack`, sidebar-visible. Two views, matching the
"Home/Maintenance split" from the approved design:

- **Home** (`home`) — day-to-day glance view:
  - A `mushroom-template-card` giving a plain-language "is now a good time
    to run big loads" verdict, computed from PV output minus current load
    vs. a 900W excess threshold, or SOC thresholds (>85% or <22%+low PV).
  - A `mushroom-chips-card` row of raw numbers (PV power, load, SOC,
    charge status).
  - A `power-flow-card-plus` animated power-flow diagram (battery/solar/
    grid/home), wired to MutaTrack's `total_pv_power`/`outsumw`/`battsoc`
    plus the external `sensor.grid_power_estimate` template sensor (not
    MutaTrack — see below).
  - A "Today's harvest" card converting `pvgeneratenergytoday` into a kWh
    figure plus a whimsical "≈N phone charges" conversion.
- **Maintenance** (`maintenance`) — health/diagnostic view:
  - A conditional alert card that only shows when the battery-forecast
    sensor's `deviation_warning` attribute is true, pointing at
    Settings → Repairs.
  - `button-card` health tiles (using a shared `health_tile` template
    defined in the dashboard) for battery capacity trend and time
    remaining/to-full.
  - Gauge cards for round-trip efficiency, PV string balance (both
    MutaTrack sensors), and PV performance ratio (external, see below).
  - An entities card exposing the forecast sensor's `capacity_source`,
    `calibration_confidence`, and `observed_cycles` attributes for
    debugging the forecast engine.

## External dependencies (not MutaTrack, not this repo)

- **Frontend custom cards** (HACS frontend resources, must be installed
  separately from MutaTrack itself): `mushroom` (template-card,
  chips-card), `button-card`, `power-flow-card-plus`.
- **`sensor.grid_power_estimate`** and **`sensor.pv_performance_ratio`** —
  HA UI-configured "Template" helper config entries (config entry domain
  `template`, entry ids `01KXH5KVTWKBHE0SKYYP8V59Z5` and
  `01KXH2DK7QFJW2JYY6PJTGA25N` respectively). These are deliberately kept
  outside MutaTrack per `IMPLEMENTATION_PLAN.md`'s Phase 5 note, to avoid a
  hard dependency on Forecast.Solar or grid-estimation logic living inside
  this integration. Configured via the UI (Settings → Devices & Services →
  Helpers), not YAML, so their template formulas aren't captured in this
  repo — if recreating this dashboard elsewhere, these two helpers need to
  be rebuilt by hand in the target instance first (PV performance ratio:
  actual generation ÷ Forecast.Solar-expected; grid power estimate: your
  own grid-draw estimation logic).

**Bug found and fixed 2026-08-23:** `grid_power_estimate`'s "state"
field (the Jinja template it evaluates) was misconfigured — it literally
contained the entire `template:\n  - sensor:\n      - name: ...` YAML
wrapper text instead of just the bare Jinja expression that field is
supposed to hold. Since most of that text isn't valid Jinja syntax, it
rendered through as literal text with the actual computed number tacked
onto the end, which HA's numeric-sensor validator correctly rejected —
298+ recurring errors, sensor stuck at `unknown`, breaking the Sundial
Home view's power-flow card (its `grid` entity). Confirmed via the
config entry's options flow (`POST /api/config/config_entries/options/flow`
with the entry id, which pre-fills the current stored value) — that's
how the malformed value was actually visible. Fixed by resubmitting just
the bare expression:
```jinja
{{ (states('sensor.mutatrack_..._outsumw')|float(0)) - (states('sensor.mutatrack_..._total_pv_power')|float(0)) - (states('sensor.mutatrack_..._total_battery_power')|float(0)) }}
```
Verified clean afterward: sensor producing real values, no further
errors in the system log.

## Follow-up: Maintenance view didn't actually show time-to-full (2026-08-22)

After adding `battery_time_to_full` as its own sensor (see
[docs/ha-automations.md](ha-automations.md)'s "Forecast integration"
section), the user configured a battery capacity and asked why the
Maintenance view's "Time remaining / to full" card still showed
`unknown`. Two separate causes:

1. At that exact moment the battery was `idle` (neither charging nor
   discharging) — both forecast sensors correctly show `unknown` then,
   regardless of capacity being configured; there's no rate to project
   from. Not a bug.
2. The real gap: that card was — as found earlier — only ever wired to
   the discharge-only `battery_time_remaining` entity, never updated to
   also reference the new `battery_time_to_full` sensor. So even once
   charging resumed, the card still wouldn't have shown anything.

Fixed by splitting it into two adjacent cards, "Time remaining" and
"Time to full", each pointed at its own entity — pushed live via
`lovelace/config/save` over the WebSocket API, and re-exported to
`ha-config/dashboards/dashboard-powertrack.yaml`.

## Follow-up: showing configured vs. estimated capacity together (2026-08-22)

After setting a configured capacity (12 kWh), asked to see both the
configured and empirically-derived values together — active one as the
main line, the alternate bracketed, with an indication of which is
active. `forecast.py`'s `ForecastResult` only exposed the already-resolved
`capacity_kwh`/`capacity_source` (the active value), not the two raw
inputs behind it, so `configured_capacity_kwh`/`empirical_capacity_kwh`
were added alongside them and exposed as attributes on
`sensor.mutatrack_..._battery_capacity_estimate`.

The Maintenance view's "Battery capacity trend" card (previously a plain
`button-card` showing just the active value) is now a
`mushroom-template-card`:
- Primary: `"{{ active }} kWh (configured|estimated)"`
- Secondary: the alternate value bracketed, e.g. `"(estimated: 11.4 kWh)"`
  or `"(configured: 12.0 kWh)"` — or a hint that no estimate/configured
  value exists yet if either side is missing.

Verified both template strings render correctly against live state via
`POST /api/template` before pushing to the dashboard.

## Follow-up: both forecast cards just said "unknown" while idle (2026-08-22)

With capacity configured, both "Time remaining" and "Time to full" still
showed `unknown` — because the battery was genuinely idle (97% SOC,
~5W net power, well inside the ±20W deadband forecast.py treats as
noise) — neither card had anything to project from, correctly, but
seeing two blank-looking cards side by side wasn't a great experience.

Collapsed both into a single card that reads the shared `phase`
attribute (present on both entities, since they come from the same
`ForecastResult`) and shows whichever value is actually relevant:
"N min remaining" while discharging, "N min to full" while charging, or
an explicit "Battery idle" / "No active charge or discharge right now"
otherwise. Still backed by the same two separate entities underneath —
this is purely a smarter display choice on the dashboard side, not a
reversion to dual-purposing one sensor's state (which was deliberately
avoided at the entity level — see `docs/ha-automations.md`'s "Forecast
integration" section for that reasoning). Verified all four template
strings (primary/secondary/icon/icon_color) against live idle state
before pushing.

## Recreating on a fresh install

1. Install the frontend custom cards above via HACS (frontend, not
   integrations).
2. Recreate the two template helpers (`grid_power_estimate`,
   `pv_performance_ratio`) if you want the Home-view power-flow card and
   Maintenance-view performance-ratio gauge to work; otherwise the
   conditional cards referencing them will just show unavailable/hidden.
3. Update entity ids in `ha-config/dashboards/dashboard-powertrack.yaml`
   from this install's `i30000251520943825` suffix to the target
   install's actual MutaTrack entity ids (see the same note in
   `docs/ha-automations.md`).
4. Create a new dashboard (Settings → Dashboards → Add Dashboard →
   "New dashboard from scratch"), then paste the YAML in edit-in-YAML
   mode — or push it via the WebSocket API's `lovelace/config/save`
   command (same pattern used to read it, see
   `scripts/fetch_trial_notifications.py` for the auth/connect
   boilerplate to adapt).
