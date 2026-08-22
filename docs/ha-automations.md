# HA Automations Built on MutaTrack Sensors

Status: **cut over and cleaned up 2026-08-22**. Only one automation is
live now — `system_power_announcement.yaml` — using the phrasing
developed during the trial documented below. The trial automation and the
old daily-summary automation have both been deleted from the instance.
These automations live in the Home Assistant instance's automation store
(not this repo's `custom_components/mutatrack/` code) — MutaTrack only
supplies the underlying sensors they trigger on and read. This doc exists
so the full environment (HA config + this repo) can be recreated on a
fresh install, and so the trial's rationale/status isn't lost between
sessions.

YAML exports of each automation live in `ha-config/automations/`. They are
reference/recreation copies, not applied automatically — HA's automation
store is the live source of truth. `system_power_announcement.yaml` is
the one currently live; the other two carry a `.deleted` extension —
they're no longer on the instance, kept only as history/recreation
reference. Re-apply any of them by pasting into the HA UI's automation
editor (YAML mode) or via the REST API (see "Recreating on a fresh
install" below).

## Why this exists

Two announcement automations were already running on the live HA instance
(base-ha, `homeassistant.local` / `https://base-ha.vtechs.com.jm` — see
`.env`'s `HA_URL`) before this repo tracked them:

1. **`system_power_announcement.yaml`** ("Announcement: System Power") —
   spoken (TTS) announcement, template-generated, fires each time
   `sensor.mutatrack_<device>_battsoc` crosses a new 10% boundary (e.g.
   79%→80%, not 81%→82%). Three canned branches: full charge, ≤20% low
   battery warning, plain "at N percent" otherwise.
2. **`mutatrack_daily_summary_via_ollama.yaml.deleted`** ("MutaTrack
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
in `power_comfort_announcement_trial.yaml.deleted`'s header comment for
exactly what changed and why at each step.

## Current state (live)

`system_power_announcement.yaml` is now the only automation, having been
cut over 2026-08-22 to the phrasing developed in the trial
(`power_comfort_announcement_trial.yaml.deleted`, formerly
`automation.mutatrack_power_comfort_announcement_trial`, config id
`1787376439276` — deleted from the instance once the cutover landed):

- Same trigger/10%-crossing conditions as before.
- Action computes SOC% and load% (averaged across
  `l1_phase_output_load_rate` / `loadpercent_l2`, not stated in the output)
  against time-of-day and picks a hand-written phrase at random — no LLM
  call. Earlier trial versions (v1-v4) called `ai_task.generate_data`
  (Ollama) instead; see the "Model capability findings" section below for
  why that was rolled back.
- Spoken via `tts.speak` (`tts.piper` → `media_player.vlc_telnet`), same as
  before the cutover — only the message template changed.
- The old daily-summary automation
  (`mutatrack_daily_summary_via_ollama.yaml.deleted`, formerly config id
  `1785417591353`) has also been deleted from the instance — it's fully
  superseded, nothing depends on it.

**Bug found and fixed 2026-08-22:** the first real trigger (SOC 29→30)
errored before posting anything — `ai_task.generate_data`'s `entity_id`
was under a separate `target:` key instead of directly in `data:` (the
pattern the daily-summary automation used successfully). Mixing `target`
with this service caused HA to also inject a list-form `entity_id` into
`data`, which the service schema rejects as needing a plain string. Fixed
live and in the trial export (now `power_comfort_announcement_trial.yaml.deleted`).

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

## Forecast integration (2026-08-22)

The load%-based heuristic (`l1_phase_output_load_rate`/`loadpercent_l2`
averaged, compared against a 25% threshold) used to be the only signal
behind the at-risk/comfortable split. That's an inverter-output-utilization
percentage, not power draw or time — a confusing proxy for "will this last
until sunrise." MutaTrack already has a purpose-built answer:
`forecast.py`'s `BatteryForecastEngine`, exposed as
`sensor.mutatrack_..._battery_time_remaining` (minutes until the
inverter's stop-SOC cutoff, only populated while discharging).

The automation now compares that sensor's value against minutes until
`sun.sun`'s `next_rising` directly — a real time-vs-time answer — and only
falls back to the load% heuristic when the forecast sensor is
`unknown`/`unavailable`. See the `message:` template in
`system_power_announcement.yaml` for the exact logic.

**Status: falls back to the heuristic 100% of the time right now.** The
forecast sensor needs either a configured battery capacity or several
observed charge/discharge cycles to calibrate (`capacity_source` is
`unavailable` on a fresh/uncalibrated instance) — checked live 2026-08-22
and it's still `unknown`. This isn't a bug in the automation; it's
expected until calibration data accumulates (or a capacity is configured
in MutaTrack's options flow).

**A related gap was found and fixed the same day:** `forecast.py` only
ever computed the discharge-side ("time remaining") estimate — while
charging, it had nothing to report, even though the Sundial dashboard's
Maintenance-view card was already named "Time remaining / to full" as if
it covered both directions. Checked the dashboard's actual card
definitions directly (`ha-config/dashboards/dashboard-powertrack.yaml`) to
confirm: every reference, including that card, points at the single
existing `battery_time_remaining` entity — the charging side was never a
separate variable, just an optimistically-named title on a sensor that
didn't do it.

Added a symmetric charging-side calculation (`seconds_to_full`, rolling-
average charge power, targeting the inverter's own configured full-charge
SOC — read from a real API field, `eybond_ctrl_71_read`/`BattFullSOC`,
rather than assuming 100%) as its **own separate sensor entity**,
`sensor.mutatrack_..._battery_time_to_full` — not dual-purposing the
existing one, since a duration sensor silently changing what milestone
it's counting down to (depending on phase) would be confusing to
graph/alert on. See `custom_components/mutatrack/forecast.py` and
`sensor.py`'s git history (commits around 2026-08-22) for the full detail;
verified with standalone script runs (both directions, plus a non-default
full-SOC ceiling) since `forecast.py` has no HA-only imports.

**This code is committed to the repo but not yet deployed to the live HA
instance** — I only have REST/WebSocket API access to that instance, not
filesystem/SSH access to `custom_components/mutatrack/`, so I can't copy
the updated files over myself. Deployment (copy files, reload/restart the
integration) is on the user to do; the automation's fallback logic means
nothing breaks in the meantime, it just keeps using the load% heuristic
until both (a) the code is deployed and (b) the forecast has calibrated.
The new `battery_time_to_full` sensor isn't referenced by any automation
yet — the night/low-SOC comfort branches this automation cares about
should rarely coincide with charging (no PV at night), so it wasn't
critical to wire in immediately, but it's available once useful.

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

**`scripts/fetch_trial_notifications.py`** was written to review the
trial's `persistent_notification` output before the cutover; it's no
longer needed day-to-day now that the trial automation is gone (nothing
posts a `persistent_notification` for this anymore — output is spoken),
but it's left in place since the same technique (querying
`persistent_notification.*` entities over the REST API) is generally
useful for any future trial-via-notification approach.

## Next steps (not yet done)

- [x] Cut the spoken automation (`system_power_announcement.yaml`) over
      to the v5 static-randomized-phrasing message — done 2026-08-22.
- [x] Delete `automation.mutatrack_power_comfort_announcement_trial` and
      `automation.mutatrack_daily_summary_via_ollama` — done 2026-08-22,
      both removed from the instance via the REST API.
- [ ] **Revisit real LLM-generated phrasing once on better hardware** —
      see "Model capability findings" above for exactly what to re-test
      and why it was shelved for now.
- [ ] **Deploy the updated `forecast.py`/`sensor.py` to the live HA
      instance** (copy over `custom_components/mutatrack/`, reload/restart
      the integration) — committed to the repo but not yet live, see
      "Forecast integration" above.
- [ ] Once deployed and calibrated (configured capacity, or a few observed
      charge/discharge cycles), confirm the automation actually takes the
      forecast-comparison branch instead of the load% fallback on a real
      night/low-SOC crossing.

## Dependencies for recreating this on a fresh HA install

None of these are part of `custom_components/mutatrack/` — they must be
separately configured on the HA instance:

- **Piper TTS** (`tts.piper`) — HA's built-in Piper integration.
- **A media player entity** to speak through (this install uses
  `media_player.vlc_telnet` — a VLC instance exposed via the VLC Telnet
  integration). Substitute any media player entity that supports
  `tts.speak`.
- **`sun` integration** — core HA, enabled by default, no setup needed.
  Supplies `sun.sun`'s `next_rising`/`next_setting` attributes.
- MutaTrack's own sensors (`battsoc`, load-rate sensors) — from this
  integration, entity ids are suffixed with a device-id string derived
  from the API's device identifier (e.g. `i30000251520943825`), which
  **will differ per install**. Update the entity ids in the exported YAML
  to match the target install's actual sensor entity ids before
  re-applying.

**Only needed if reviving LLM-generated phrasing** (not required for the
current static-phrasing implementation): an **Ollama `ai_task` entity**
(`ai_task.ollama_ai_task`) — HA's Ollama integration, configured with an
`ai_task` conversation entity pointed at a local Ollama server. See "Model
capability findings" above before investing in this on modest hardware.

## Recreating on a fresh install

1. Set up the dependencies above (Piper, a media player; Ollama `ai_task`
   only if reviving LLM-generated phrasing).
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
