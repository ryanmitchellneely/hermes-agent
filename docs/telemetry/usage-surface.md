# Usage + success surface (MESH-TEL-3)

The read side of the model-call telemetry store. Schema contract:
[`model-calls-schema.md`](model-calls-schema.md). Writer: `agent/call_telemetry.py`.

Answers the questions the store was opened for:

> "are we keeping track of how much money we are saving using local, how many
> runs etc? is there a place it can be live? not just a snapshot in time? I want
> a full overview of where every token is going, how long different systems are
> working or taking, bottlenecks."

## What runs

| piece | path |
|---|---|
| digest generator | `scripts/telemetry_digest.py` |
| launcher (writes surface + heartbeat) | `deploy/telemetry-digest/telemetry-digest.sh` |
| schedule (**not installed**) | `deploy/telemetry-digest/com.ryan.t1000-telemetry-digest.plist` |
| markdown surface | `~/.t1000/telemetry/USAGE-DIGEST-latest.md` |
| heartbeat status file | `~/.t1000/telemetry/telemetry-digest-heartbeat.json` |
| tests | `tests/scripts/test_telemetry_digest.py` |

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

**`custom` is deliberately `unknown`.** It covers both local Ollama and hosted
OpenAI-compatible endpoints (GLM on Volcengine ARK), and schema v1 carries no
`base_url` to tell them apart. Guessing would reproduce the LAB-SCOREBOARD bug
with better intentions. Instead the digest raises a warn flag naming the
provider and its call count.

Resolve it with operator configuration, which is a statement of fact rather
than an inference — `~/.t1000/telemetry/provider_classes.json`:

```json
{ "custom": "local" }
```

Override the path with `--provider-class-map`. Unknown class names in the file
are dropped rather than trusted.

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

## Arming it — human gate, not yet done

Nothing is scheduled. Installing a schedule is a human decision in this repo.
To arm the daily 08:30 run:

```bash
cp /Users/ryan/Documents/T1000/deploy/telemetry-digest/com.ryan.t1000-telemetry-digest.plist \
   ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.ryan.t1000-telemetry-digest.plist
launchctl kickstart -k gui/$(id -u)/com.ryan.t1000-telemetry-digest   # run once now
```

Verify: `cat ~/.t1000/telemetry/telemetry-digest-heartbeat.json`

Disarm: `launchctl bootout gui/$(id -u)/com.ryan.t1000-telemetry-digest`

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
