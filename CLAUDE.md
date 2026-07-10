# MutaTrack

A Home Assistant custom integration for Must/Eybond/ValueClouds-ecosystem hybrid
solar inverters. Status: pre-build / scaffolding.

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
  auth flow, field-index map, and findings from live validation against the
  actual account/inverter (devcode, PN/SN, confirmed vs. hypothesized fields)
- [docs/architecture.md](docs/architecture.md) — integration file layout,
  coordinator/config-flow design decisions, entity model
- [docs/dev-setup.md](docs/dev-setup.md) — local dev environment, running the
  API test harness, `.env` setup, testing against a real HA instance
- [docs/release-process.md](docs/release-process.md) — HACS structure,
  validation workflows, versioning/release/update mechanics

Update these as implementation progresses. When a change here represents a
shift in product direction or overall architecture (not just an implementation
detail), also propose a corresponding high-level update to the Confluence
page rather than letting it silently drift out of sync.

## Current known-unknowns (do not treat as resolved)

- Exact devcode/model for this specific inverter — unconfirmed, to be
  discovered live via the API test harness (see docs/dev-setup.md)
- Field-index map (45 positional fields) is reverse-engineered from a
  different inverter's community gist, unverified against this account's
  live data
- Whether ValueClouds exposes any write/settings endpoints — unresearched,
  out of scope until v2
- Whether other Eybond white-label tenants share this API shape — out of
  scope until v3

## Repo/build status

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the phased build
plan and current progress. Repo is not yet pushed to GitHub — local
scaffolding only until Phase 3.
