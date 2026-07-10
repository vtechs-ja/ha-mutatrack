# Release & Install Process

Status: planned, not yet implemented (see IMPLEMENTATION_PLAN.md Phase 3).

## HACS structure

- `hacs.json` at repo root
- `custom_components/mutatrack/manifest.json` must satisfy HACS/hassfest
  validation requirements (domain, name, version, codeowners, etc.)
- README with install instructions:
  - HACS custom repository install (pre-default-store)
  - Manual `custom_components/mutatrack` copy as fallback
  - Dashboard wiring guidance: native Power Sankey / Energy Distribution
    cards as the zero-dependency default, optional community power-flow
    card (Sunsynk Power Flow Card / Power Flow Card Plus) as a cosmetic
    upgrade pointer only — no bundled card code, per Confluence 2.4

## CI / validation

- GitHub Actions workflow running `hassfest` validation on push/PR
- GitHub Actions workflow running HACS validation action on push/PR

## Versioning & updates

- Semantic version in `manifest.json`, bumped per release
- Git tags → GitHub Releases — this is the mechanism HACS uses to detect
  and deliver updates to installed users
- Repo hosting: new GitHub repo (e.g. `deron/ha-mutatrack`), created and
  pushed by the user once local scaffolding is in a working state

## Future: HACS default store submission

Not planned until v1.1 per the Confluence roadmap. Requires the repo to
already pass HACS/hassfest validation consistently.
