# MutaTrack — Implementation Plan

Working plan for building the MutaTrack Home Assistant integration, agreed
2026-07-10. Source product/roadmap doc:
[Confluence — MutaTrack Product Brief, Starter Tech Spec & Roadmap](https://vtechs.atlassian.net/wiki/spaces/VTechEng/pages/59506690/MutaTrack+Product+Brief+Starter+Tech+Spec+Roadmap).

Status legend: `[ ]` not started, `[~]` in progress, `[x]` done.

## Decisions on record

- **Credentials for local API testing:** `.env` file, gitignored, user fills
  in real values. `.env.example` documents required keys.
- **Devcode/inverter model:** unknown up front — Phase 2 must discover it
  live via the API rather than assume the community gist's field map is
  correct as-is.
- **Repo hosting:** new GitHub repo (e.g. `deron/ha-mutatrack`), created and
  pushed by the user once local scaffolding is in a working state — not
  automated by the agent.
- **Write/control (v2):** strictly out of bounds for this build. No code,
  no architecture hooks, no TODOs implying it's imminent.

## Phase 0 — Repo scaffolding & context

- [x] `git init`
- [x] `CLAUDE.md` with source-of-truth hierarchy and links to local docs
- [x] `IMPLEMENTATION_PLAN.md` (this file)
- [ ] `.gitignore` (Python, HA, `.env`, secrets, `__pycache__`, etc.)
- [ ] `docs/` scaffolding: `api-reference.md`, `architecture.md`,
      `dev-setup.md`, `release-process.md`

## Phase 1 — `custom_components/mutatrack/` skeleton

- [ ] `manifest.json`
- [ ] `const.py` — field index map, endpoint URLs, defaults
- [ ] `api.py` — ValueClouds client (login, deviceDats, positional-array
      parsing, defensive/index-tolerant)
- [ ] `config_flow.py` — email/password entry, PN/SN override
- [ ] `coordinator.py` — `DataUpdateCoordinator`, reactive re-auth on
      401/unavailable
- [ ] `sensor.py` — entities from the field map; correct
      `device_class`/`state_class` for Energy Dashboard compatibility on
      cumulative kWh fields
- [ ] `diagnostics.py` — redacted diagnostics export
- [ ] `strings.json` / `translations/en.json`

Scope: v1 read-only monitoring only, per Confluence roadmap.

## Phase 2 — Local API test harness

- [ ] `.env.example` + `.env` (gitignored)
- [ ] Standalone script: login, then discover account's device list /
      confirm PN/SN/devcode live
- [ ] Query `deviceDats` and validate the reverse-engineered field-index map
      against real data; record findings in `docs/api-reference.md`
- [ ] Save one raw sample response as a test fixture for mocked unit tests

## Phase 3 — Repo config for HA install/update support

- [ ] `hacs.json`, HACS-compliant structure
- [ ] README with install instructions + dashboard wiring guidance (native
      Power Sankey / Energy Distribution cards; optional community card
      pointer) — docs only, no new integration code, per Confluence 2.4
- [ ] GitHub Actions: `hassfest` validation + HACS validation workflows
- [ ] Versioning/release process (tags → GitHub Releases, what HACS uses for
      updates)
- [ ] User creates GitHub repo and pushes when ready (not automated)

## Confluence sync

When local docs reflect a change in overall architecture or product
direction (not just implementation detail), propose an update to the
Confluence page's high-level sections to keep it aligned. Confluence is not
expected to track implementation-level detail — that lives in `docs/`.
