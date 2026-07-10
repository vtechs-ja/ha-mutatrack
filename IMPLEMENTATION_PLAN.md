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

- [x] `manifest.json`
- [x] `const.py` — field index map, endpoint URLs, defaults
- [x] `api.py` — ValueClouds client (login, deviceDats, positional-array
      parsing, defensive/index-tolerant, one reactive re-auth retry on
      401/403)
- [x] `config_flow.py` — email/password + PN/SN/devcode entry, with a login
      test before saving the entry
- [x] `coordinator.py` — `DataUpdateCoordinator`, parses raw array into a
      name-keyed dict tolerant of short/misaligned arrays
- [x] `sensor.py` — entities from the field map; `device_class`/`state_class`
      set for Energy Dashboard compatibility on cumulative kWh fields;
      ambiguous fields (work_state, software_version, last_update_timestamp,
      charger_work_enable) left as plain diagnostic sensors pending Phase 2
      validation
- [x] `diagnostics.py` — redacted diagnostics export (email/password/SN)
- [x] `strings.json` / `translations/en.json`
- [x] `__init__.py` — config entry setup/unload, platform forwarding

Scope: v1 read-only monitoring only, per Confluence roadmap. Syntax and
JSON validated locally; **not yet tested against a running HA instance or
real API data** — PN/SN/devcode are required config-flow fields with no
live device to confirm them against yet (that's Phase 2).

## Phase 2 — Local API test harness

- [x] `.env.example` (`.env` itself gitignored, user-provided)
- [x] `scripts/api_harness.py` — login, and (if PN/SN/devcode provided)
      fetch + map `deviceDats` against `const.FIELD_INDEX`; reuses the
      integration's real `api.py`/`const.py` via `importlib` rather than
      duplicating logic
- [x] Saves raw sample response to `tests/fixtures/sample_device_data.json`
      (credentials scrubbed) for future mocked unit tests
- [x] **Login confirmed live 2026-07-10.** Original doc's login shape was
      wrong (`code 24`, project not found); corrected via real DevTools
      capture to `{account, sha1(password), project: "IOT"}`. Also
      discovered the API returns HTTP 200 on both success and failure —
      `api.py` now checks the body's `success`/`code` fields. Full details
      in `docs/api-reference.md`.
- [ ] **Blocked on user action:** no confirmed device-list discovery
      endpoint exists — PN/SN/devcode must be captured manually via browser
      DevTools (see docs/dev-setup.md) before `deviceDats` can be
      live-validated
- [ ] Run the harness in full device-data mode once PN/SN/devcode are
      captured; record field-index confirmations/corrections in
      `docs/api-reference.md`

`deviceDats`/field-index map is still unverified — only login has been
confirmed against the real account so far.

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
