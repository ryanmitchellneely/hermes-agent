# Usage + success surface (MESH-TEL-3)

The read side of the model-call telemetry store. Schema contract:
[`model-calls-schema.md`](model-calls-schema.md). Writer: `agent/call_telemetry.py`.

Answers the questions the store was opened for:

> "are we keeping track of how much money we are saving using local, how many
> runs etc? is there a place it can be live? not just a snapshot in time? I want
> a full overview of where every token is going, how long different systems are
> working or taking, bottlenecks."

## What runs

| piece | path | tracked in git? |
|---|---|---|
| digest generator | `scripts/telemetry_digest.py` | yes (T1000) |
| launcher (writes surface + heartbeat) | `deploy/telemetry-digest/telemetry-digest.sh` | yes (T1000) |
| **delivery** schedule (**not armed**) | `deploy/telemetry-digest/arm-hermes-cron.sh` | yes (T1000) |
| cron wrapper (source of truth) | `deploy/telemetry-digest/telemetry_digest_cron.sh` | yes (T1000) |
| cron wrapper (installed copy) | `$HERMES_HOME/scripts/telemetry_digest_cron.sh` | yes (home repo, once armed) |
| pull-only schedule (**not armed**) | `deploy/telemetry-digest/com.ryan.t1000-telemetry-digest.plist` | yes (T1000) |
| markdown rollup | `~/.t1000/telemetry/USAGE-DIGEST-latest.md` | **yes (home repo)** |
| dated rollup snapshots | `~/.t1000/telemetry/digests/USAGE-DIGEST-<date>.md` | **yes (home repo)** |
| heartbeat status file | `~/.t1000/telemetry/telemetry-digest-heartbeat.json` | no — regenerated every run |
| raw call store | `~/.t1000/telemetry/model_calls-*.jsonl` | no — rotates; never committed |
| tests | `tests/scripts/test_telemetry_digest.py` | yes (T1000) |

Ad-hoc use needs no schedule:

```
python3 scripts/telemetry_digest.py --since 24h
python3 scripts/telemetry_digest.py --since 7d --lane worker
python3 scripts/telemetry_digest.py --since 7d --json
```

It is stdlib-only in the degraded case: `agent.usage_pricing` is a soft import,
so a broken venv costs you the dollar columns, not the surface.

### Why a second module next to `telemetry_query.py`

`scripts/telemetry_query.py` (MESH-TEL-2a) is an ad-hoc filter tool. Its
store-reading primitives — `telemetry_dir`, `parse_when`, `iter_records` — are
imported here rather than reimplemented. Its `rollup()` is not: those buckets
keep running sums only, and p50/p95 needs retained samples, the decision flags
need to compare groups against each other, and the cost split needs a per-row
classification. Bolting that onto the query CLI would make one file serve both
an interactive contract and a scheduled-job contract.

## The three rules this surface enforces

### 1. `tokens_available=false` never enters a sum, and never disappears

Rows flagged `tokens_available=false` are excluded from every token and cost
total and reported as their own count ("N calls with no token data"). They still
appear in call counts and outcome counts — excluded from a sum is not the same
as dropped, and dropping them would hide the call and its failure.

A group where nothing reported tokens prints `no data`, never `0`. That zero is
the whole failure mode: it makes a subscription lane read as free and inverts
any local-vs-hosted comparison.

Pinned by `TestTokensAvailableContract`, including
`test_tokenless_row_carrying_literal_zeros_is_still_excluded` — which passes a
row with `tokens_available=false` *and* literal zeros present, so the exclusion
must come from the flag rather than from the writer happening to null the
fields. Verified by mutation: folding tokenless rows into the sums fails 3
tests.

### 2. Local-vs-hosted comes from provider identity, never from a boolean

`~/.t1000/kanban/LAB-SCOREBOARD.jsonl`, measured 2026-08-10:

- 529 rows; **22 tag a hosted model `is_local=true`** — 11 × `sonnet`,
  8 × `grok-4.5`, 2 × `opus[1m]`, 1 × `opus`.
- **313 of 529 rows (59.2%) carry no model attribution at all.**

The decisive detail: on all 22 mislabeled rows the `provider` column was
**correct** (`claude-acp`, `xai-oauth`) while `is_local` was wrong. The identity
was right in exactly the rows where the derived boolean was wrong. So this
surface derives the cost class from `provider` and never reads a caller-set
locality flag.

Four classes, and the fourth is load-bearing:

| class | meaning |
|---|---|
| `local` | inference on fleet hardware; marginal token cost genuinely $0 |
| `subscription` | flat-fee seat (claude-acp, copilot-acp, codex). $0 marginal, **but the seat is not free** — never read as savings |
| `metered` | pay-per-token API; real dollars leave the account |
| `unknown` | the provider slug does not identify the hosting |

**Bare `custom` is deliberately `unknown`.** It covers both local Ollama and
hosted OpenAI-compatible endpoints (GLM on Volcengine ARK), and schema v1
carries no `base_url` to tell them apart. Guessing would reproduce the
LAB-SCOREBOARD bug with better intentions. Instead the digest raises a warn
flag naming the provider and its call count.

**Qualified `custom:<name>` resolves to `<name>`.** This is not the guess above.
`custom:<name>` is the codebase's canonical qualified provider form — config
keys an endpoint by bare name while the runtime reports the qualified slug (see
`agent/image_routing.py`, `agent/credential_pool.py`) — and the store holds the
same endpoint recorded both ways: `mbp-ollama` (44 calls) and
`custom:mbp-ollama` (120 calls) are one host. Reading the name back out is
parsing a slug the transport wrote, not inferring where inference ran. Names the
tables don't recognise still fall through to `unknown`, so `custom:glm` stays
unattributed.

Without this, the qualified slugs — which became the dominant form on
2026-08-10 — left **84% of calls (3,306 of 3,934) unattributable**, and the
local-vs-subscription split is the whole cost lever. With it, `unknown` is 1.3%.

Resolve what's left with operator configuration, which is a statement of fact
rather than an inference — `~/.t1000/telemetry/provider_classes.json`:

```json
{ "custom": "local", "auto": "local", "mbp-mlx": "local" }
```

A full slug (`"custom:glm"`) outranks a bare name (`"glm"`), so you can pin one
endpoint without reclassifying every sibling. Override the path with
`--provider-class-map`. Unknown class names in the file are dropped rather than
trusted.

`mbp-mlx` is listed here rather than added to `LOCAL_PROVIDERS` on purpose: the
naming convention and MLX being an on-device framework both point local, but
that is an inference about an endpoint, and this file is where inferences get
turned into stated facts by someone who knows.

The durable fix is upstream: emit enough on the row to decide it. See
"Follow-ups" below.

### 3. Failures are as visible as successes

`~/.t1000/kanban/FLASH-SCOREBOARD.jsonl`, measured 2026-08-10: **25 rows,
`apply_ok=true` on 25 of 25.** A scoreboard that has never once recorded a
failure is not reporting 100% reliability, it is reporting that it cannot see
failures. So:

- The `## Failures` section renders whether or not there are any.
- Any group under 10 calls is stamped `⚠thin`, and a window under 10 calls
  raises a `thin_data` flag — a 100% built from 6 calls cannot be read as
  reliability.
- A clean window at or above that floor raises `no_failures_observed`, which
  points at the failure emit site (`run_agent.py::_invoke_api_request_error_hook`)
  and asks you to confirm it is firing before believing the number.

## Trend, not a snapshot

Every render rolls up the equal-length window immediately before `--since` and
prints the deltas (calls, success rate, failures, tokens, wall p50/p95). A
window with no prior data prints `—`, never a fabricated −100%: absent data is
not zero. `--no-compare` switches the section off.

## Decision flags

The point is a decision, not a display.

| flag | fires when | floor |
|---|---|---|
| `success_below_lane` | a model scores ≥10pp below its lane's average | 5 calls |
| `effort_not_earning` | a higher reasoning effort scores no better than a lower one on the same model | 5 calls per arm |
| `tokens_missing` | any row lacks token data | — |
| `cost_class_unknown` | a provider could not be placed | — |
| `thin_data` / `no_failures_observed` | see rule 3 | — |

Eviction candidates (models with no calls in 7 days, for the residency
manifest) are computed over the **whole** store, not the digest window: "no
calls in 7 days" is only meaningful about models that were once called at all.

## Bottlenecks — what this can and cannot say

**Can:** wall-time distribution (p50 / p95 / max) per model, provider, lane and
effort, and each model's share of total observed wall clock. Percentiles are
nearest-rank, so every number printed is a latency some call actually took —
an interpolated p95 invents a duration nothing experienced.

**Cannot:** split wall time into queue/startup wait vs generation. That needs
`ttft_ms`, which is `null` on every row currently in the store — the ACP and
chat-completions transports do not measure first-token latency. The digest
prints this as a caveat rather than inventing a bottleneck metric the schema
does not support.

Also disclosed in every render: one row is one *call*, not one run (so counts
are a floor on runs); untimed calls are excluded from percentiles rather than
counted as zero latency; and the known MESH-TEL-2b emit gaps (SDK-internal
retries, the streaming aux path) are not counted at all.

## Money saved by running local is not asserted

There is no honest measurement of it. It requires a counterfactual — "what
would this have cost on model X" — which is an estimate about a run that never
happened. Asserting one is how a scoreboard ends up reporting a circular
number.

So it is opt-in and labelled:

```
python3 scripts/telemetry_digest.py --since 7d --counterfactual 'claude-opus-4-5@anthropic'
```

which reprices only the zero-marginal-cost classes (`local`, `subscription`)
against the named model and prints the reference model plus the assumption it
rests on. Metered calls are never repriced — that would double-count.

The reference takes `model` or `model@provider`. Prefer the `@provider` form:
the pricing tables key on `(provider, model)`, so a bare model name usually
resolves to no route and cannot be priced. When it cannot be priced the section
still renders and says why — a requested counterfactual that silently vanished
would read as "nothing to report" rather than "this failed".

## Observability contract

Per `docs/architecture/observability-principle.md`, and matching the status
file shape of `deploy/kevin-spark/ds4-watchdog.sh` so one consumer can read
every heartbeat in the fleet:

```json
{
  "system": "telemetry-digest",
  "status": "ok",
  "fired_at": "2026-08-11T13:30:00Z",
  "fired_at_epoch": 1786829400,
  "expected_interval_seconds": 86400,
  "calls_in_window": 8,
  "failures": 0,
  "warn_flags": 1,
  "surface": "/Users/ryan/.t1000/telemetry/USAGE-DIGEST-latest.md",
  "window": "24h"
}
```

- **Registers** — surface + heartbeat at known paths.
- **Heartbeats** — the status file is written on **every** run including the
  failure path, so a missing or stale file means "the digest is dead", never
  "ran fine, nothing to report".
- **Surfaces** — markdown is written *before* stdout delivery, so the last good
  digest stays readable when delivery breaks.
- **Alerts** — exit codes: `0` rendered with calls, `1` **no calls in window**
  (the emit sites may have stopped — a silent telemetry digest manufactures
  false confidence, so this is deliberately loud; `--no-alert-on-empty` to
  opt out), `2` the digest itself failed, with the reason in the heartbeat.

`status` is `ok`, `degraded` (warn flags raised), `empty`, or `error`.

## Delivery — how the digest reaches a human

The card asks for "one Telegram/digest message". **launchd does not deliver.**
Its `StandardOutPath` is a log file, so a launchd-only install refreshes the
surface on disk and nobody ever sees the decision flags — which is the failure
mode this whole surface exists to prevent. The two schedules are therefore not
interchangeable:

| schedule | what it does | delivers to a human? |
|---|---|---|
| `arm-hermes-cron.sh` → Hermes no-agent cron | runs the launcher, sends its **stdout verbatim** to the configured target | **yes** |
| `com.ryan.t1000-telemetry-digest.plist` → launchd | runs the launcher, stdout to a log file | no — pull-only refresh |

`no_agent=True` means the script *is* the job: no LLM, no tokens, no agent
loop. Two constraints make that path work, and both fail at **fire** time
rather than at creation time — i.e. the job is created happily and then never
delivers, which is precisely the silent-telemetry failure this surface exists
to refuse.

#### The script must live inside `$HERMES_HOME/scripts`

`cron/scheduler.py:_run_job_script` resolves `--script` and then requires the
result to sit inside the scripts dir:

```python
if raw.is_absolute(): path = raw.resolve()
else:                 path = (scripts_dir / raw).resolve()
path.relative_to(scripts_dir_resolved)   # else -> "Blocked: ..."
```

An absolute path into this repo is **not** exempt — it is resolved and then
rejected. A **symlink is rejected too**, because `.resolve()` follows it back
out of the scripts dir. Verified against the live guard:

```
BLOCKED : ~/Documents/T1000/deploy/telemetry-digest/telemetry-digest.sh
BLOCKED : <scripts>/link.sh -> (repo)
ALLOWED : telemetry_digest_cron.sh          # real file copy, bare name
```

Hence `deploy/telemetry-digest/telemetry_digest_cron.sh`: `arm-hermes-cron.sh`
installs it as a real copy under `$HERMES_HOME/scripts/` and passes the **bare
filename**. Cron is per-profile (the scheduler resolves `HERMES_HOME` at call
time), so arm it from the same profile whose gateway runs cron — the dry run
prints the target dir and warns when it is not `~/.t1000/scripts`, where the
existing no-agent jobs live.

#### The delivered body must fit the channel

Telegram rejects a `sendMessage` payload over **4096** characters outright.
The full surface measures **~7.6k** on the live store, so delivering it
unmodified is a guaranteed failure, and the decision flags are what would fall
off the end. The wrapper therefore passes `--compact`, which shortens **only
stdout** — headline, cost split, decision flags, and a pointer to the full
surface (~800 chars on the live store). The file on disk is still written in
full. When there are more flags than fit, the body says how many it dropped;
it never trims them silently.

### Arm the delivering schedule — human gate, not yet done

Dry run by default, because arming starts a recurring outbound message:

```bash
deploy/telemetry-digest/arm-hermes-cron.sh          # prints what it would install + create
HERMES_HOME=~/.t1000 deploy/telemetry-digest/arm-hermes-cron.sh --yes
```

Defaults: `30 8 * * *`, `--deliver telegram`, `--no-agent`. Override with
`TELEMETRY_DIGEST_SCHEDULE`, `TELEMETRY_DIGEST_DELIVER` (use `local` to save
runs without sending anything). The installed wrapper sets
`TELEMETRY_DIGEST_COMMIT=1` so the scheduled run keeps the rollup's history;
set it to `0` in the wrapper to render without committing. It never pushes.

Verify: `hermes cron list` · Disarm: `hermes cron remove <job_id>`

### Arm the pull-only schedule (optional, independent)

```bash
cp /Users/ryan/Documents/T1000/deploy/telemetry-digest/com.ryan.t1000-telemetry-digest.plist \
   ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.ryan.t1000-telemetry-digest.plist
launchctl kickstart -k gui/$(id -u)/com.ryan.t1000-telemetry-digest   # run once now
```

Verify: `cat ~/.t1000/telemetry/telemetry-digest-heartbeat.json`

Disarm: `launchctl bootout gui/$(id -u)/com.ryan.t1000-telemetry-digest`

Running both is fine and mildly useful (a midday surface refresh plus one
morning message); the surface write is idempotent.

## The committed rollup

The rendered markdown is committed, and the raw store is not. That split is
deliberate: **the trend cannot survive on the store alone.** Week-over-week
deltas are recomputed from `model_calls-*.jsonl` on every run, so the moment
those rows rotate or get pruned, every past window is unrecoverable. Keeping
the *rendered* digest in git is what gives the surface a memory.

- `USAGE-DIGEST-latest.md` — always the newest render.
- `digests/USAGE-DIGEST-<YYYY-MM-DD>.md` — dated copy, written by
  `--snapshot-dir` (the launcher passes it; ad-hoc runs do not archive). Local
  date, matching the morning run a human actually saw.

Both live under the home repo's curated `.t1000` allowlist
(`~/.gitignore`), added the same way commit `3f5a4e3` added
`kanban/bench-snapshots/`. **Markdown only** — the `.jsonl` call rows, the
heartbeat, and `provider_classes.json` stay ignored.

Committing is opt-in, since a scheduled job that commits unasked is a surprise:

```bash
TELEMETRY_DIGEST_COMMIT=1 deploy/telemetry-digest/telemetry-digest.sh
```

It stages only those two paths and commits with a pathspec, so nothing else
dirty in the home repo can ride along. If a path is still git-ignored it says
so on stderr and skips, rather than reporting a commit that did not happen.
The paths it commits are read back out of the heartbeat the run just wrote, so
a caller that redirected `--dir` / `--out` is followed rather than guessed at.

> **Footgun, pinned by a test.** The store root is `$T1000_TELEMETRY_DIR`, else
> `$HERMES_REAL_HOME/.t1000/telemetry`, else `~/.t1000/telemetry` — the rule in
> `telemetry_dir()`. It is **not** under `$HERMES_HOME`: inside a Hermes worker
> session `HERMES_HOME` is the *profile* dir (`~/.t1000/profiles/<name>`), so
> deriving paths from it archives history where the digest never reads and the
> commit step then correctly refuses to commit it — the rollup quietly stops
> accumulating while every run still reports success.

## Why two scoreboards still exist (MESH-TEL-3 ↔ t_d0277c0b)

They measure different grains and should not be merged:

- **This store is call-grained.** One row = one model call. A single kanban run
  makes many.
- **FLASH-SCOREBOARD / LAB-SCOREBOARD are job-grained.** One row = one job, and
  they carry job-level outcomes (`apply_ok`, `human_fix_min`, `route_again`)
  that have no call-level equivalent.

What should converge is the *overlapping* columns, and the direction is one-way.
The scoreboards' `is_local`, `prompt_tokens` / `completion_tokens`,
`estimated_cost_usd` and `saved_usd_vs_frontier` are re-derived per-writer, and
the evidence above shows those derivations are wrong in the field (22 mislabeled
rows, 59.2% missing model attribution, 25/25 apply_ok). Those columns should be
sourced from this store by joining on `run_id` rather than recomputed. The
job-level outcome columns stay where they are.

Not done here — this card is the read side. Filed as a follow-up.

## Follow-ups

1. **Emit hosting identity on the row.** Adding `base_url_host` (or the
   resolved `billing_mode`) at write time would retire the `unknown` class for
   `custom` without any operator configuration. Additive, so no schema bump.
2. **`ttft_ms` on transports that can measure it** — without it, "why is this
   slow" stays unanswerable.
3. **Join the scoreboards' token/cost/locality columns to this store on
   `run_id`** instead of re-deriving them per writer.
