# MutaTrack

A Home Assistant custom integration for Must/Eybond/ValueClouds-ecosystem hybrid
solar inverters. Status: core API (login + primary data endpoint) confirmed
working live against the real account as of 2026-07-10; not yet tested
inside an actual Home Assistant instance.

## Source of truth hierarchy

1. **Confluence (product/roadmap, high-level):** [MutaTrack — Product Brief, Starter Tech Spec & Roadmap](https://vtechs.atlassian.net/wiki/spaces/VTechEng/pages/59506690/MutaTrack+Product+Brief+Starter+Tech+Spec+Roadmap)
   Treat this as the starting reference for product intent, non-goals, and
   roadmap phasing. It is updated periodically with a high-level abstraction
   when architecture direction changes — it will lag the local docs on
   implementation detail by design. If local docs and Confluence conflict on
   a technical detail, the local docs are more current; if they conflict on
   product direction/scope, flag it to the user rather than assuming either
   is right.
2. **Local docs (this repo, detailed/fast-moving):** the `docs/` directory
   below. This is where implementation-level technical detail lives and gets
   updated as work happens — Confluence is not updated at this granularity.
3. **Code and tests** are always authoritative over both docs when they
   disagree — docs may be stale; verify against code before trusting a
   detail that matters.

## What this project is

Home Assistant users on the Eybond/DessMonitor OEM white-label backend
(ValueClouds, SmartESS, DessMonitor, SmartValue, etc.) have no packaged HA
integration — only scattered YAML gists. MutaTrack is a config-flow-driven
HACS integration, starting with read-only monitoring for a Must PV18-3224
PRO-family inverter (Eybond WFBLE.DTU.PlugProA-02 datalogger) on the
ValueClouds API.

**v1 scope: read-only monitoring only.** No write/control code or hooks for
it — that's a separate, research-gated future effort (see Confluence
roadmap v2). Do not add `select`/`number` platforms or settings-write API
calls without explicit direction.

## Local technical docs

- [docs/api-reference.md](docs/api-reference.md) — ValueClouds API endpoints,
  auth flow, confirmed data endpoint (`queryDeviceOneDataxxx`), and a
  catalogue of other discovered-but-unused endpoints for future work
- [docs/architecture.md](docs/architecture.md) — integration file layout,
  coordinator/config-flow design decisions, entity model
- [docs/dev-setup.md](docs/dev-setup.md) — local dev environment, running the
  API test harness, `.env` setup, testing against a real HA instance
- [docs/release-process.md](docs/release-process.md) — HACS structure,
  validation workflows, versioning/release/update mechanics
- [docs/ha-automations.md](docs/ha-automations.md) — HA automations built
  on top of MutaTrack's sensors (announcements, LLM-generated summaries),
  with YAML exports under `ha-config/automations/`, so the live HA
  instance's config isn't only known to whichever session set it up.
- [docs/ha-dashboards.md](docs/ha-dashboards.md) — HA dashboards built on
  top of MutaTrack's sensors (the "Sundial" dashboard), with an export
  under `ha-config/dashboards/`.

Both of the above are HA-side config, not integration code — they live
outside `custom_components/mutatrack/` but are tracked here so the whole
environment (integration + HA automations/dashboards) can be recreated on
a fresh install. **Keep these docs and their exports in sync whenever an
automation or dashboard that consumes MutaTrack sensors is added, changed,
or removed on the live HA instance** — don't let it silently drift the way
Confluence is allowed to for product-level docs. When in doubt whether the
live HA instance has drifted from what's documented here (as happened
2026-08-22, where a live dashboard and a template helper were already
built but still marked not-done in `IMPLEMENTATION_PLAN.md`), check the
instance directly (REST API for states/automations, WebSocket API's
`lovelace/dashboards/list` + `lovelace/config` for dashboards — see
`.env`'s `HA_URL`/`HA_TOKEN`) rather than trusting the docs alone.

Update these as implementation progresses. When a change here represents a
shift in product direction or overall architecture (not just an implementation
detail), also propose a corresponding high-level update to the Confluence
page rather than letting it silently drift out of sync.

## Current known-unknowns (do not treat as resolved)

- Whether ValueClouds exposes a write/settings endpoint — the field ids
  seen (`eybond_ctrl_*_read`) strongly suggest one exists, but it has
  **deliberately not been probed or investigated**; out of scope until v2.
  Do not attempt to find or call it without explicit direction.
- `alm/api/auth/web/device/warnings` returns an auth error (`code 306`)
  even with a valid token — unresolved, not blocking v1.
- Purpose of the `secret` field returned at login — unused, unconfirmed.
- Whether other Eybond white-label tenants share this API shape — out of
  scope until v3.
- Whether the field set returned by `queryDeviceOneDataxxx` is stable
  across firmware versions — untested, only one snapshot observed so far.

## Repo/build status

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the phased build
plan and current progress. Repo is not yet pushed to GitHub — local
scaffolding only until Phase 3.

**Verified live 2026-07-10:** login and the primary data endpoint
(`queryDeviceOneDataxxx`) both confirmed working end-to-end against
Deron's real account via `scripts/api_harness.py`, including catching and
fixing a real bug (the originally-documented login shape was wrong). Not
yet tested inside an actual running Home Assistant instance.

**Handling `.env`/credentials in this repo:** never `cat`/`grep` `.env`
raw when checking its state — that echoes plaintext into tool output/logs.
Use a masked check, e.g.
`awk -F= '/^VALUECLOUDS_/{print $1"="($2==""?"<empty>":"<set>")}' .env`.
See docs/dev-setup.md.
