# Integration Architecture

Status: planned, not yet implemented (see IMPLEMENTATION_PLAN.md Phase 1).

## Layout

```
custom_components/mutatrack/
├── __init__.py          # Setup, config entry, coordinator wiring
├── manifest.json         # Integration metadata, HACS-compatible structure
├── config_flow.py        # UI form: email, password, optional PN/SN override
├── coordinator.py        # DataUpdateCoordinator: login, token cache, poll, re-auth on 401/unavailable
├── api.py                 # Thin ValueClouds API client (login, deviceDats, field parsing)
├── sensor.py               # Maps parsed fields to HA sensor entities
├── forecast.py              # Battery runtime projection (v1.5, not v1)
├── const.py                 # Field index map, endpoint URLs, defaults
├── diagnostics.py            # Redacted diagnostics download
└── strings.json / translations/en.json
```

## Key design decisions

| Decision | Rationale |
| --- | --- |
| One `DataUpdateCoordinator` per device, single API call per poll cycle | Avoids redundant polling; matches HA integration best practice |
| Config flow captures email/password, not a pre-extracted token | Removes the DevTools token-hunting step from the current YAML gist workflow |
| PN/SN auto-discovered where possible, with manual override field | Reference gist requires manually finding these in DevTools; auto-discovery should be investigated in Phase 2 |
| Sensors keyed by researched field index, defensively parsed (index-out-of-range tolerant) | Field mapping is unverified; a firmware/model variance could shift indices without warning |
| Entity availability reflects auth/API failure distinctly from "device offline" | Lets downstream automations distinguish "cloud unreachable" from "inverter actually off" |

## v1 boundary

Read-only monitoring only. No `select`/`number` platforms, no
settings-write API calls. Write support (v2) is research-gated and out of
scope for this build — see IMPLEMENTATION_PLAN.md.

## Open technical risks

- Field mapping confidence — built for a different Must PV18-3224 PRO unit;
  Deron's exact model is unconfirmed.
- API stability — undocumented reverse-engineered cloud API, no versioning
  guarantee (the sibling DessMonitor integration has already broken once
  from an unannounced API change).
- Rate limiting / ToS — unknown, worth a light review before any public
  HACS submission.
- Multi-tenant white-label question — unconfirmed whether other Eybond
  tenants share this API shape (v3 scope, not now).
