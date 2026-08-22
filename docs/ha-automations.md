# HA Automations Built on MutaTrack Sensors

Status: **trial in progress**, started 2026-08-22. These automations live
in the Home Assistant instance's automation store (not this repo's
`custom_components/mutatrack/` code) — MutaTrack only supplies the
underlying sensors they trigger on and read. This doc exists so the full
environment (HA config + this repo) can be recreated on a fresh install,
and so the trial's rationale/status isn't lost between sessions.

YAML exports of each automation live in `ha-config/automations/`. They are
reference/recreation copies, not applied automatically — HA's automation
store is the live source of truth. Re-apply by pasting into the HA UI's
automation editor (YAML mode) or via the REST API (see "Recreating on a
fresh install" below).

## Why this exists

Two announcement automations were already running on the live HA instance
(base-ha, `homeassistant.local` / `https://base-ha.vtechs.com.jm` — see
`.env`'s `HA_URL`) before this repo tracked them:

1. **`system_power_announcement.yaml`** ("Announcement: System Power") —
   spoken (TTS) announcement, template-generated, fires each time
   `sensor.mutatrack_<device>_battsoc` crosses a new 10% boundary (e.g.
   79%→80%, not 81%→82%). Three canned branches: full charge, ≤20% low
   battery warning, plain "at N percent" otherwise.
2. **`mutatrack_daily_summary_via_ollama.yaml.superseded`** ("MutaTrack
   Daily Summary via Ollama") — once-daily (21:00) LLM-generated summary
   of the day's solar/battery numbers via `ai_task.generate_data` against
   a local Ollama `ai_task` entity, posted as a `persistent_notification`.

The decision (2026-08-22): fold the LLM-generation piece from #2 into the
10%-crossing trigger from #1, instead of running a separate daily summary.
The new announcement leads with the battery percentage (always) and adds a
short comfort/risk read — reasoning about load vs. time-to-sunrise — only
when that's actually informative (overnight, tight margins). It does not
state the load number directly; load is an input the model reasons over,
not part of the output. See the automation's `instructions:` template in
`power_comfort_announcement_trial.yaml` for the exact prompt.

## Current state (trial)

`power_comfort_announcement_trial.yaml` — created via the HA REST API
2026-08-22 (`automation.mutatrack_power_comfort_announcement_trial`, config
id `1787376439276`). Runs **in parallel** with the original spoken
automation:

- Same trigger and same 10%-crossing conditions as
  `system_power_announcement.yaml` — fires on identical events.
- Action calls `ai_task.generate_data` (Ollama) with SOC%, load% (averaged
  across `l1_phase_output_load_rate` / `loadpercent_l2`, not stated in the
  output), current time, and `sun.sun`'s `next_rising`/`next_setting`.
- Posts the result as a `persistent_notification` (text), rather than
  speaking it — this is deliberate, so the spoken experience is unchanged
  during review.
- The original spoken automation (`system_power_announcement.yaml`) is
  untouched and still speaking the old templated message.
- The daily summary automation
  (`mutatrack_daily_summary_via_ollama.yaml.superseded`) is **still live**
  on the instance, pending removal — not yet deleted, since the trial
  hasn't been reviewed/cut over yet.

**Bug found and fixed 2026-08-22:** the first real trigger (SOC 29→30)
errored before posting anything — `ai_task.generate_data`'s `entity_id`
was under a separate `target:` key instead of directly in `data:` (the
pattern the daily-summary automation used successfully). Mixing `target`
with this service caused HA to also inject a list-form `entity_id` into
`data`, which the service schema rejects as needing a plain string. Fixed
live and in `power_comfort_announcement_trial.yaml`. Not yet reconfirmed
against a real SOC crossing — waiting on the next one.

**Retrieving trial output for review:** persistent_notification entities
are queryable over the HA REST API without any config change, so
`scripts/fetch_trial_notifications.py` pulls the full series (filter by
title, e.g. `"Power Comfort"`) for review — no text-file `notify` target
or HA restart needed.

```bash
.venv/bin/python3 scripts/fetch_trial_notifications.py "Power Comfort"
```

## Next steps (not yet done)

- [ ] Review a few days of trial notifications (via the fetch script
      above) against the spoken template's output.
- [ ] Decide: cut the spoken automation over to the LLM-generated message
      (swap `tts.speak`'s templated `message:` for the `ai_task` +
      response-variable pattern), keep both, or revert.
- [ ] Once cut over (or if the trial is abandoned), delete
      `automation.mutatrack_power_comfort_announcement_trial` and/or
      `automation.mutatrack_daily_summary_via_ollama` as applicable —
      neither has been deleted yet.

## Dependencies for recreating this on a fresh HA install

None of these are part of `custom_components/mutatrack/` — they must be
separately configured on the HA instance:

- **Piper TTS** (`tts.piper`) — HA's built-in Piper integration.
- **A media player entity** to speak through (this install uses
  `media_player.vlc_telnet` — a VLC instance exposed via the VLC Telnet
  integration). Substitute any media player entity that supports
  `tts.speak`.
- **Ollama `ai_task` entity** (`ai_task.ollama_ai_task`) — HA's Ollama
  integration, configured with an `ai_task` conversation entity pointed at
  a local Ollama server. This is the piece doing the LLM generation; model
  choice/quality directly affects announcement output.
- **`sun` integration** — core HA, enabled by default, no setup needed.
  Supplies `sun.sun`'s `next_rising`/`next_setting` attributes.
- MutaTrack's own sensors (`battsoc`, load-rate sensors) — from this
  integration, entity ids are suffixed with a device-id string derived
  from the API's device identifier (e.g. `i30000251520943825`), which
  **will differ per install**. Update the entity ids in the exported YAML
  to match the target install's actual sensor entity ids before
  re-applying.

## Recreating on a fresh install

1. Set up the dependencies above (Piper, a media player, Ollama `ai_task`).
2. Install/configure MutaTrack itself, confirm the battery SOC and load
   sensors exist with their actual entity ids.
3. Edit the entity ids in the relevant YAML file(s) under
   `ha-config/automations/` to match.
4. Apply via the HA UI (Settings → Automations → three-dot menu → Edit in
   YAML → paste) — this is the simplest path for a one-off recreation.
   Alternatively, POST the JSON-equivalent body to
   `/api/config/automation/config/<new_numeric_id>` with a bearer token
   (see `HA_TOKEN` in `.env`, generated via HA profile → Security tab) —
   this is what was used to create the trial automation in this session,
   useful if scripting the recreation of several automations at once.
