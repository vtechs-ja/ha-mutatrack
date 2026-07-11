# MutaTrack

A Home Assistant custom integration for Must/Eybond/ValueClouds-ecosystem
hybrid solar inverters (ValueClouds/SmartESS/DessMonitor/SmartValue
white-label backend), starting with the Must PV18-3224 PRO-family inverter
(Eybond WFBLE.DTU.PlugProA-02 datalogger).

**v1 scope: read-only monitoring only.** No write/control features.

## Status

Login and the primary data endpoint are confirmed working live end-to-end
against a real account. Not yet broadly tested across other
devices/firmware versions — see [docs/api-reference.md](docs/api-reference.md)
for known unknowns.

## Installation

### HACS (custom repository)

1. HACS → Integrations → ⋮ menu → **Custom repositories**
2. Add `https://github.com/vtechs-ja/ha-mutatrack`, category **Integration**
3. Install "MutaTrack" from HACS, then restart Home Assistant

### Manual

Copy `custom_components/mutatrack/` into `<your-ha-config>/custom_components/mutatrack/`,
then restart Home Assistant.

## Setup

Settings → Devices & Services → Add Integration → search "MutaTrack".

You'll need:

- Your ValueClouds/SmartValue account email and password
- Your device's PN, SN, and devcode

There is no device-list discovery endpoint, so PN/SN/devcode must be
captured manually via browser DevTools — see
[docs/dev-setup.md](docs/dev-setup.md) for how.

The config flow performs a live login test before saving, so bad
credentials fail immediately in the UI.

## Entities

Sensors are created dynamically from whatever fields the API returns for
your device — names and units come from the API itself, not a hardcoded
list. Core telemetry (power, energy, battery, etc.) is exposed as regular
sensors; everything else (settings/control-read values, machine info) is
exposed as diagnostic-category sensors.

## Dashboard

Energy-related entities are compatible with Home Assistant's native Energy
Dashboard and Power Sankey / Energy Distribution cards — no custom card
required.

## Documentation

- [docs/api-reference.md](docs/api-reference.md) — ValueClouds API details
- [docs/architecture.md](docs/architecture.md) — integration design
- [docs/dev-setup.md](docs/dev-setup.md) — local dev environment
- [docs/release-process.md](docs/release-process.md) — HACS/versioning

## Known unknowns

See [CLAUDE.md](CLAUDE.md#current-known-unknowns-do-not-treat-as-resolved)
for details on unresolved API questions (write/control endpoint existence,
field stability across firmware, etc.) — none are v1 blockers.
