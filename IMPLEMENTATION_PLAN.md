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
- **Repo hosting:** [vtechs-ja/ha-mutatrack](https://github.com/vtechs-ja/ha-mutatrack),
  created and pushed 2026-07-11.
- **Write/control (v2):** strictly out of bounds for this build. No code,
  no architecture hooks, no TODOs implying it's imminent.

## Phase 0 — Repo scaffolding & context

- [x] `git init`
- [x] `CLAUDE.md` with source-of-truth hierarchy and links to local docs
- [x] `IMPLEMENTATION_PLAN.md` (this file)
- [x] `.gitignore` (Python, HA, `.env`, secrets, `__pycache__`, etc.)
- [x] `docs/` scaffolding: `api-reference.md`, `architecture.md`,
      `dev-setup.md`, `release-process.md`

## Phase 1 — `custom_components/mutatrack/` skeleton

- [x] `manifest.json`
- [x] `const.py` — endpoint URLs, defaults, `PRIMARY_TELEMETRY_IDS`/
      `ENERGY_FIELD_IDS` (rewritten after Phase 2 findings — see below)
- [x] `api.py` — ValueClouds client (login, `queryDeviceOneDataxxx`,
      confirmed live; one reactive re-auth retry on auth failure)
- [x] `config_flow.py` — email/password + PN/SN/devcode entry, with a login
      test before saving the entry
- [x] `coordinator.py` — `DataUpdateCoordinator`, parses the named field
      list into an id-keyed dict
- [x] `sensor.py` — entities built **dynamically** from whatever fields the
      API actually returns, using the API's own `title`/`unit`; ids in
      `PRIMARY_TELEMETRY_IDS` are regular sensors, everything else
      (settings/control-read values, machine info) is a diagnostic-category
      sensor
- [x] `diagnostics.py` — redacted diagnostics export (email/password/SN)
- [x] `strings.json` / `translations/en.json` (static `entity.sensor` block
      removed — names now come from the API dynamically)
- [x] `__init__.py` — config entry setup/unload, platform forwarding

Scope: v1 read-only monitoring only, per Confluence roadmap. **Rewritten
2026-07-10** after Phase 2 live validation showed the original
`deviceDats`-based design was built on an unverified, ultimately-replaced
data source — see Phase 2 below. Login and device-data fetch confirmed
live end-to-end via `scripts/api_harness.py`. **Still not tested inside an
actual running Home Assistant instance** (config flow UI, entity
registration, Energy Dashboard behavior all unverified in that context).

## Phase 2 — Local API test harness & live validation

- [x] `.env.example` (`.env` itself gitignored, user-provided)
- [x] `scripts/api_harness.py` — reuses the integration's real
      `api.py`/`const.py` via `importlib` rather than duplicating logic
- [x] **Login confirmed live 2026-07-10.** Original doc's login shape was
      wrong (`code 24`, project not found); corrected via real DevTools
      capture to `{account, sha1(password), project: "IOT"}`. Also
      discovered the API returns HTTP 200 on both success and failure.
- [x] **PN/SN/devcode captured** via browser DevTools (`pn`, `sn`,
      `devcode=6409`, `devaddr=255` — the last two both differ from the
      original doc's guesses).
- [x] **Data endpoint pivoted, confirmed live.** Collaboratively discovered
      4 additional endpoints beyond the originally-documented `deviceDats`.
      `queryDeviceOneDataxxx` returns 115 self-describing named fields
      (confirmed a superset of the leaner `querySPDeviceLastData`'s 48) —
      adopted as the sole v1 data source, replacing the blind
      positional-array approach entirely. Full rewrite of
      `const.py`/`api.py`/`coordinator.py`/`sensor.py` to match.
- [x] Full pipeline (login → fetch → parse) verified live end-to-end.
- [x] Raw sample saved to `tests/fixtures/sample_device_data.json`,
      `queryDeviceOneDataxxx_sample.json`, `querySPDeviceLastData_sample.json`
- [x] Other discovered endpoints documented in `docs/api-reference.md` for
      future reference (`queryDeviceEnergyFlow` confirmed working;
      `device/warnings` blocked on an unresolved auth requirement).
      **Deliberately not investigated:** any write/control endpoint,
      despite `eybond_ctrl_*_read` field ids suggesting one exists.

Phase 2 core goals are met. Remaining open items are tracked as
known-unknowns in `docs/api-reference.md`, not blockers for Phase 3.

## Phase 3 — Repo config for HA install/update support

- [x] `hacs.json`, HACS-compliant structure
- [x] README with install instructions + dashboard wiring guidance (native
      Power Sankey / Energy Distribution cards; optional community card
      pointer) — docs only, no new integration code, per Confluence 2.4
- [ ] GitHub Actions: `hassfest` validation + HACS validation workflows
- [x] Versioning/release process (tags → GitHub Releases, what HACS uses for
      updates) — first tag `v0.1.0` cut 2026-07-11
- [x] User creates GitHub repo and pushes when ready (not automated) —
      done 2026-07-11: [vtechs-ja/ha-mutatrack](https://github.com/vtechs-ja/ha-mutatrack)

## Confluence sync

When local docs reflect a change in overall architecture or product
direction (not just implementation detail), propose an update to the
Confluence page's high-level sections to keep it aligned. Confluence is not
expected to track implementation-level detail — that lives in `docs/`.
