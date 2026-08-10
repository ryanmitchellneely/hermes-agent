# Model-call telemetry — store + schema (MESH-TEL-2a)

The contract that `agent/call_telemetry.py`, the emit sites (MESH-TEL-2b), the
claude-acp token recovery (MESH-TEL-2c) and the digest (MESH-TEL-3) all bind to.
Change it here first.

## Where it lives

```
~/.t1000/telemetry/model_calls-YYYY-MM-DD.jsonl      # local date, daily rotation
```

Override with `T1000_TELEMETRY_DIR` (tests, dry runs). The root is **not**
derived from `HERMES_HOME` — that points at a per-profile directory
(`~/.t1000/profiles/worker`) and this store is cross-profile as well as
cross-board. It is deliberately outside every per-board `kanban.db`: "how much
deepseek vs 120b" is a fleet-wide question.

## Why JSONL and not SQLite

The fleet runs many worker processes at once. One `os.write()` of a single
newline-terminated buffer into a file opened `O_APPEND` is atomic against other
appenders on macOS and Linux, so concurrent writers cannot tear or interleave
each other's lines — no locking, no WAL, no writer starvation, and a crashed
writer costs at most its own partial last line (readers skip unparseable lines).
`tests/agent/test_call_telemetry.py::test_eight_concurrent_processes_write_200_intact_lines`
proves it with 8 real processes released from a common barrier.

A SQLite mirror can be added later as a derived index. It must not become the
source of truth without first demonstrating concurrent-writer safety under WAL.

## One line = one model CALL

Not one run. A single kanban run makes many model calls; run counts are a floor.

| field | type | notes |
|---|---|---|
| `schema_version` | int | currently `1`. Additive fields do not bump it. |
| `ts` | str | ISO8601 with UTC offset, millisecond precision, local tz |
| `ts_epoch_ms` | int | same instant, epoch milliseconds |
| `board` | str \| null | defaults from `HERMES_KANBAN_BOARD` |
| `task_id` | str \| null | defaults from `HERMES_KANBAN_TASK` |
| `run_id` | str \| null | defaults from `HERMES_KANBAN_RUN_ID`; string, cast when joining `task_runs.id` |
| `session_id` | str \| null | defaults from `HERMES_SESSION_ID` |
| `lane` | str \| null | profile — defaults from `HERMES_PROFILE` |
| `task` | str | aux task name (`vision`, `compression`, …) or `main_loop` |
| `provider` | str | `spark`, `kevin-spark`, `claude-acp`, `xai-oauth`, `mbp-ollama`, … |
| `model` | str | the slug that ACTUALLY ran, incl. after fallback — never read from config |
| `effort` | str \| null | reasoning effort |
| `api_mode` | str \| null | passed through to `normalize_usage` |
| **`tokens_available`** | **bool, required** | see below |
| `input_tokens` | int \| null | cache tokens already subtracted out |
| `output_tokens` | int \| null | |
| `cache_read_tokens` | int \| null | |
| `cache_write_tokens` | int \| null | |
| `reasoning_tokens` | int \| null | |
| `prompt_tokens` | int \| null | `input + cache_read + cache_write` |
| `total_tokens` | int \| null | `prompt + output` |
| `wall_ms` | int \| null | |
| `ttft_ms` | int \| null | null where the transport cannot measure it |
| `outcome` | str | `ok` \| `error` \| `timeout` \| `refusal` |
| `outcome_raw` | str | present only when an unknown outcome was coerced to `error` |
| `error_class` | str \| null | truncated to 200 chars |
| `pid`, `host` | int, str | which process wrote the row |

## The `tokens_available` contract

`agent/claude_acp_client.py:1103` (non-streaming) and `:1237` (streaming), and
`agent/copilot_acp_client.py:481`, all build

```python
usage = SimpleNamespace(prompt_tokens=0, completion_tokens=0, total_tokens=0,
                        prompt_tokens_details=SimpleNamespace(cached_tokens=0))
```

That is a **real zero, not a missing value**. Stored as `0`, every rollup reads
the subscription lanes as free and the local-vs-subscription split comes out
inverted — the same failure class as the DevBot scoreboard's 16/16
`tokens_est=true` rows.

So:

* `tokens_available` is required and never null.
* It is auto-detected as `false` when there is no usage object, when the
  provider is in `TOKENLESS_PROVIDERS` (`claude-acp`, `copilot-acp`), or when a
  normalized usage object is all zeros. A caller that knows better (2c, once it
  recovers real ACP counts) can pass `tokens_available=True` explicitly.
* When it is `false`, **every** token field is written as `null`, never `0`, so
  a naive `SUM` cannot silently undercount.
* Consumers report those rows as their own count — "N calls with no token
  data" — rather than folding them into a total. `scripts/telemetry_query.py`
  does exactly this (`calls_with_tokens` / `calls_without_tokens`).

Model attribution is still complete on those rows: provider, model, effort,
outcome and wall time are all captured. The `>=95% attribution` bar is about
model attribution, not token coverage.

## Token normalization

Always through `agent/usage_pricing.py:normalize_usage(raw, provider=, api_mode=)`,
which already handles the Anthropic / Codex-Responses / Chat-Completions shapes
plus bedrock cache accounting and DeepSeek `prompt_cache_hit_tokens`. Tokens are
never estimated from character counts. An already-normalized `CanonicalUsage` is
passed straight through (re-normalizing one would misread its derived
`prompt_tokens` property and drop `output_tokens`).

## Writing

```python
from agent.call_telemetry import record_model_call

record_model_call(
    provider=provider, model=model, effort=effort, usage=response.usage,
    wall_ms=wall_ms, ttft_ms=ttft_ms, outcome="ok", error_class=None,
    task="main_loop",            # or the aux task name
)
```

Keyword-only; everything except `provider` and `model` is optional.
`board` / `task_id` / `run_id` / `session_id` / `lane` fall back to the
dispatcher environment so call sites need not thread them through. The function
**never raises and never blocks on a lock** — the whole body is wrapped in
`try/except`, mirroring `agent/aux_accounting.py:record_aux_usage`.

## Reading

```
~/.t1000/bin/telemetry-query                 # everything in the store
~/.t1000/bin/telemetry-query --since 24h
~/.t1000/bin/telemetry-query --board mesh --lane worker
~/.t1000/bin/telemetry-query --json          # for the MESH-TEL-3 digest
```

Source: `scripts/telemetry_query.py` (stdlib-only, so it runs under a bare
system `python3`). Against an empty or non-existent store it prints
`no data yet` and exits 0 — never a traceback.
