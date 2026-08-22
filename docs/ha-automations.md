# HA Automations Built on MutaTrack Sensors

Status: **cut over 2026-08-22**. The spoken announcement now uses the
phrasing developed during the trial below. These automations live
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
when that's actually informative (overnight, tight margins).

That was the original intent; in practice the local model (see "Model
capability findings" below) wasn't reliable enough at open-ended
generation to do this live, so the current version (v5) computes the
comfort/risk verdict in Jinja and picks from hand-written phrasing instead
of calling an LLM at all. Treat "LLM-generated" as the aspiration this is
working toward, not the current implementation — see the version history
in `power_comfort_announcement_trial.yaml`'s header comment for exactly
what changed and why at each step.

## Current state (trial)

`power_comfort_announcement_trial.yaml` — created via the HA REST API
2026-08-22 (`automation.mutatrack_power_comfort_announcement_trial`, config
id `1787376439276`). Runs **in parallel** with the original spoken
automation:

- Same trigger and same 10%-crossing conditions as
  `system_power_announcement.yaml` — fires on identical events.
- Action (as of v5) computes SOC% and load% (averaged across
  `l1_phase_output_load_rate` / `loadpercent_l2`, not stated in the output)
  against time-of-day and picks a hand-written phrase at random — no LLM
  call. Earlier versions (v1-v4) called `ai_task.generate_data` (Ollama)
  instead; see the "Model capability findings" section below for why that
  was rolled back for now.
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
live and in `power_comfort_announcement_trial.yaml`.

**Prompt rewritten 2026-08-22, same day:** the first successful trigger
(SOC 39→40) posted a notification, but the model's output was garbled — a
degenerating, self-contradicting repeat of the raw prompt facts instead of
a real sentence. Root cause: `ai_task.ollama_ai_task` runs **Llama 3.2 1B**
(`llama3.2:1b-instruct-q4_K_M`, confirmed via the device registry), a
small quantized model that struggles when asked to both reason about
comfort/risk *and* compose natural phrasing in one step. Iterated directly
against `ai_task.generate_data` (bypassing the automation, via
`POST /api/services/ai_task/generate_data?return_response` — safe, no
state mutation) through a few prompt versions before finding a stable one:
moving the comfort/risk verdict into deterministic Jinja logic (mirroring
the Home view's existing threshold logic on the Sundial dashboard) and
giving the model only the much easier job of phrasing an
already-decided outcome. Confirmed coherent and consistent across
repeated test calls for every branch (fully charged / at-risk overnight /
comfortable overnight / plain percentage). See the automation export for
the exact prompt and the full iteration history/rationale in its header
comment. Still an open question whether this holds up over several days
of real crossings, or whether the model needs swapping for something
larger — that's what the remaining trial period is for.

**Personality attempt, then rollback to static phrasing, 2026-08-22 (v5):**
asked the v4 prompt to sound warmer/less bland. Tested two directions
directly against `ai_task.generate_data` (bypassing the automation each
time, same safe method as above):
- A tone instruction ("warm, friendly, conversational... not a robotic
  readout") — sometimes genuinely better ("but don't worry, it'll easily
  make it to sunrise"), but reintroduced the v1 failure modes in roughly
  a third of runs: duplicated paragraphs restating the same idea, and
  invented details never given in the prompt (e.g. "It's getting pretty
  dark in this area").
- A few-shot example ("match this style: 'Battery's down to 15 percent,
  and it's tight overnight...'") — worse: the model pattern-matched the
  example's structure but sometimes hallucinated a completely wrong SOC
  (output "The battery's 75% charge..." when told 15 percent), or
  produced generic filler ("a moderate load will keep the battery charged
  for a relatively long time").

Conclusion: this model's reliability ceiling sits right around the
"state the fact, add one deterministic-verdict sentence" level (v4) —
asking for more expressiveness costs more in hallucination/repetition
than it gains in tone. **Rolled back to static, hand-written phrasing**
(v5, current): the same four branches as v4, but each maps to a short
list of pre-written variants picked at random via Jinja's `| random` —
no model call at all for this automation. Gets some rotation/personality
without the latency or reliability cost. See "Model capability findings"
below for the full investigation, including why bigger local models
aren't a viable alternative on this hardware, and what to revisit once
better hardware is available.

## Model capability findings (2026-08-22) — revisit with better hardware

This section exists so a future session (once you have a better machine
running Ollama, or move to a hosted LLM) can pick the LLM-generation idea
back up without repeating this investigation from scratch.

**What's actually available on this instance's Ollama add-on** (queried
directly via `GET http://homeassistant.local:11434/api/tags`, which is
reachable from this dev machine over LAN even though the add-on's internal
Docker hostname `76e18fb5-ollama` is not):

| Model | Params | Size on disk |
| --- | --- | --- |
| `llama3.2:1b-instruct-q4_K_M` | 1.2B | 0.81 GB — **currently used by `ai_task.ollama_ai_task`** |
| `tinyllama:latest` | 1B | 0.64 GB |
| `llama3.2:latest` | 3.2B | 2.02 GB |
| `qwen3:4b-instruct` | 4.0B | 2.50 GB |
| `qwen2.5:latest` | 7.6B | 4.68 GB |

All five are already pulled — trying a bigger one needs a config change to
which model backs the `ai_task` entity, not a download.

**Why bigger wasn't tried further:** timed a trivial one-line prompt
(`"Say hello in one sentence."`) directly against `llama3.2:latest` (3.2B,
already pulled) via `POST http://homeassistant.local:11434/api/generate` —
**it took 104 seconds.** The 1B model that's currently in use responds in
roughly a couple of seconds for comparable prompts. This strongly suggests
the host has no GPU acceleration and is CPU-bound enough that anything
above ~1-1.2B params is impractical for a notification that should follow
a real-time state change, not show up a minute or two later. Two calls (one
timed out at 60s, one completed at 104s) were made directly against the
add-on to establish this — outside of any automation, so they didn't touch
MutaTrack or HA config, but they did occupy the Ollama add-on's CPU for
that duration on the live production host. Checked HA core and the Ollama
add-on's lightweight `/api/tags` endpoint immediately afterward — both
responded instantly, so nothing crashed or hung, but there's **no
host-level CPU/RAM telemetry available** (no `systemmonitor` integration
installed on this instance) to say precisely how close to the edge it got.
Worth installing `systemmonitor` before running any further multi-model
experiments like this, or doing them from a lower-priority time window.

**What to revisit once you have better hardware (GPU-accelerated, or a
hosted LLM API):**
1. Re-run the personality prompts documented above (tone instruction,
   few-shot example) against `llama3.2:latest`, `qwen3:4b-instruct`, or
   `qwen2.5:latest` — larger models are generally much more reliable at
   following "don't invent details" / "don't repeat yourself" instructions
   under more expressive asks, so the hallucination/repetition problems
   seen here may simply not recur.
2. If latency is still a concern even on better hardware, consider a
   hosted API (Anthropic/OpenAI/etc.) instead of local Ollama — trades
   local-only/no-cost for reliable low-latency generation. Would need a
   new HA integration/config entry, not just a model swap.
3. Restore the v4-style prompt (deterministic verdict decided in Jinja,
   model only phrases it — see `power_comfort_announcement_trial.yaml`'s
   git history for the exact wording) as the starting point, then layer
   the personality ask back on top once a larger/hosted model is in play.
4. Install `systemmonitor` first so any future multi-model comparison has
   real CPU/RAM numbers to reason from, rather than just "did HA stay
   responsive."

**Retrieving trial output for review:** persistent_notification entities
are queryable over the HA REST API without any config change, so
`scripts/fetch_trial_notifications.py` pulls the full series (filter by
title, e.g. `"Power Comfort"`) for review — no text-file `notify` target
or HA restart needed.

```bash
.venv/bin/python3 scripts/fetch_trial_notifications.py "Power Comfort"
```

## Next steps (not yet done)

- [x] Cut the spoken automation (`system_power_announcement.yaml`) over
      to the v5 static-randomized-phrasing message — done 2026-08-22.
- [ ] Delete `automation.mutatrack_power_comfort_announcement_trial`
      (its job is done — its output is now what the spoken automation
      uses) and `automation.mutatrack_daily_summary_via_ollama`
      (superseded) — neither has been deleted yet, both still live on
      the instance.
- [ ] **Revisit real LLM-generated phrasing once on better hardware** —
      see "Model capability findings" above for exactly what to re-test
      and why it was shelved for now.

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
