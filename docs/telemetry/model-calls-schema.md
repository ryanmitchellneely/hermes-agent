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

`agent/claude_acp_client.py` (non-streaming and streaming) and
`agent/copilot_acp_client.py` used to build

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
  normalized usage object is all zeros. A caller that knows better can pass
  `tokens_available=True` explicitly — which is what MESH-TEL-2c now does.
* When it is `false`, **every** token field is written as `null`, never `0`, so
  a naive `SUM` cannot silently undercount.
* Consumers report those rows as their own count — "N calls with no token
  data" — rather than folding them into a total. `scripts/telemetry_query.py`
  does exactly this (`calls_with_tokens` / `calls_without_tokens`).

### MESH-TEL-2c: claude-acp is no longer tokenless

The counts were on the wire the whole time. ACP's `session/prompt` response
carries `PromptResponse.usage` (optional, still marked **UNSTABLE** in the ACP
schema) and both shims discarded the result. Probed live against
`claude-agent-acp` 0.62.0, a one-word prompt answers:

```json
{"stopReason": "end_turn",
 "usage": {"inputTokens": 2, "outputTokens": 4, "cachedReadTokens": 19467,
           "cachedWriteTokens": 16113, "totalTokens": 35586}}
```

`agent/usage_pricing.py:acp_usage_namespace` projects that into the
chat-completions shape the shims expose (ACP's `inputTokens` **excludes**
cache; `prompt_tokens` includes it) and tags the result with a
`tokens_available` attribute. The emit sites forward that attribute into
`record_model_call(tokens_available=...)`, because auto-detection would
otherwise apply the `TOKENLESS_PROVIDERS` default and null the very counts 2c
recovered. Providers outside the ACP lanes never set the attribute, so they
keep pure auto-detection.

`usage` is absent on some settle paths (and the Copilot CLI's support is
**unverified** — no `copilot` binary was available to probe). Absent usage
still yields `tokens_available=false` with `null` tokens; the shims read the
result either way, so a Copilot CLI that does report usage is picked up
without a further change.

Note the side effect this makes real: the ACP lanes now feed genuine prompt
totals to session accounting and to `context_compressor.update_from_response`,
which previously saw zeros. No dollar cost appears —
`resolve_billing_route("claude-acp"/"copilot-acp")` returns `unknown`, so
`estimate_usage_cost` yields `amount_usd=None` and nothing is added to session
spend.

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

### Where it is actually called from (MESH-TEL-2b)

Two chokepoints, not one per provider adapter — a per-adapter wiring leaves a
lane silently unattributed the moment a new adapter lands. Each has a success
site and a failure site, because a lane that only records the calls that came
back reports a 100% success rate by construction (t_4123e041).

| site | covers | notes |
|---|---|---|
| `agent/auxiliary_client.py::_validate_llm_response` | every non-streaming aux call that returned (vision, compression, title, web_extract, judges, …) | the same chokepoint `record_aux_usage` uses |
| `agent/auxiliary_client.py::_record_aux_call_failure` | the aux failure counterpart | fires from the `_relay_auxiliary_call` decorator, so it is once per LOGICAL call no matter how many attempts the fallback chain burned; `KeyboardInterrupt`/`CancelledError` are deliberately not recorded as model failures |
| `agent/conversation_loop.py`, at the success `break` | every accepted main-loop response | reached exactly once per accepted call, after all retry/fallback branches have looped or bailed |
| `run_agent.py::_invoke_api_request_error_hook` | the main-loop failure counterpart | the single funnel for all three main-loop failure surfaces (invalid response, `content_filter` refusal, raised exception); the emit sits **above** the `has_hook()` early-return so telemetry does not depend on a user having configured a lifecycle hook |

`wall_ms` on an aux row spans the whole **logical** call, measured from
`time.monotonic()` stamped by the relay decorator — so a route that only
succeeded on its third fallback reads as the slow call it actually was, and an
NTP step cannot produce a negative duration. Every emit site stamps `wall_ms`
into a local **before** any other work in the emit runs, so the emit's own cost
(notably the identity lookup's first-miss config read) never lands in the field
whose job is timing.

### `provider` records the lane, not the routing decision

`provider` is passed through `call_telemetry.resolve_provider_identity` at all
three sites. Two labels are routing decisions rather than identities and are
upgraded to `custom:<name>` via `runtime_provider.canonical_custom_identity`
(reverse-lookup by `base_url`, then by model):

- **`auto`** — what every aux task carries on a stock desk
  (`auxiliary.<task>.provider: auto`, 13 of 13 tasks here). Recorded raw, every
  aux row in the fleet says `provider: "auto"`.
- **bare `custom`** — the shared billing class of every named `providers:`
  entry, so Flash-on-`:8889` and Ollama-on-`:11434` collapse into one bucket,
  and a worker launched `--provider kevin-spark` records as `custom`.

Real identities (`openrouter`, `claude-acp`, `nous`, …) pass through untouched,
and a sentinel that cannot be recovered keeps its original label rather than
having a lane invented for it. The lookup is memoized per `(base_url, model)`;
the first miss costs ~85 ms of config parsing, every hit ~0.0002 ms.

`reason`/`error_type` map onto the closed outcome set:
`content_policy_blocked → refusal`, `timeout → timeout`, everything else
`→ error`.

Known gaps, all verified rather than assumed:

- **`ttft_ms` is always `null` today.** Neither chokepoint sits on a streaming
  first-token boundary, so nothing observes the timestamp. The field is in the
  schema and the writer honours it; no caller populates it yet.
- A main-loop call retried *inside* the provider SDK is one row, not N.
- The streaming aux path returns a raw iterator instead of passing through
  `_validate_llm_response`, so it is not counted.
- On ACP lanes one "call" is a whole agent turn, so `wall_ms` and
  `output_tokens` are turn-scoped and much larger than a single HTTP request.

`tests/conftest.py` pins `T1000_TELEMETRY_DIR` to a per-test tempdir so the
suite cannot append fake rows to the real store.

`tests/conftest.py` pins `T1000_TELEMETRY_DIR` to a per-test tempdir so the
suite cannot append fake rows to the real store.

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
