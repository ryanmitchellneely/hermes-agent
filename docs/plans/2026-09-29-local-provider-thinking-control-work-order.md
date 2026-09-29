# Work order: thinking control for local OpenAI-compatible providers

- Date: 2026-09-29. Steer: ryan-claude. Cards: mesh `t_d698d173` (bug), models `t_43fdb841` (fleet architecture; Ryan's go for this order), models `t_cfa038b9` (Flash-Next move to TensorFold; this is its effort gate).
- Branch: `ryan/local-thinking-control`, cut from `fork/main` @ `31cedb4830`. This order is committed before any code.
- Crew loop (Ryan lane): ryan-claude steers; an UNFENCED `grok --oauth` build seat builds in this worktree (commit-only, never push, never opens the PR); the `crew-reviewer` agent reviews adversarially and mutation-verifies; ryan-claude pushes and opens the PR. The build seat can execute, so builder-executed bars are allowed (see the lane note in kevin-real-estate-tools CLAUDE.md, "Ryan's Grok may BUILD").

## 1. Measured problem

1. For a provider override of `none`, `parse_reasoning_effort()` (`hermes_constants.py:947-966`) yields `{"enabled": False}`. For a provider with no registered profile (a raw `providers:` entry such as `spark`), `agent/auxiliary_client.py` sets `extra_body["reasoning"] = {"enabled": False}` (fork/main `:8064`; `:8067` for effort). The OpenAI SDK sends it as a top-level `"reasoning"` key.
2. vLLM (finn, container `vllm-fn-tp1`) maps ONLY the top-level `reasoning_effort` field into the template (`vllm/entrypoints/openai/chat_completion/protocol.py:587-588`); its request model uses `extra="allow"`, so `"reasoning"` is dropped silently. TensorFold's CUDA server reads ONLY `chat_template_kwargs` (TensorFold `cuda/server.py:184-198` at `1911880`) and also ignores top-level `reasoning_effort`.
3. The main-agent path (`agent/transports/chat_completions.py:549-560`) emits `extra_body.reasoning` only when `supports_reasoning` is set, and then always with `enabled: True`. A custom provider such as `spark` therefore sends nothing, and the model's template default applies (Qwen3.8-Flash-Next: thinking ON).
4. Effect, measured: finn served 1,889 requests in 24 h and 83% ended `finish_reason=length`. On one small coding prompt direct to vLLM, default thinking spent 3,000 tokens and produced no answer in 103 s; `reasoning_effort=low` took 1,228 tokens (24 s); `enable_thinking=false` took 887 tokens (22 s) (session 29, 2026-09-29).
5. The templates differ. Qwen3.8-Flash-Next reads `enable_thinking` and `reasoning_effort` in {`xhigh` (default), `medium`, `low`}, and RAISES on any other value (`chat_template.jinja`: "Supported types are xhigh (default), medium, and low"). DeepSeek-V4-Flash-0731 reads `thinking` (bool) and `reasoning_effort` in {`high`, `max`} (bake-off `harness/models.json`, entry `ds4`). T1000's own default effort is `high`, which is invalid for Qwen, so a naive pass-through of the effort string breaks Qwen requests.

## 2. Stage A: config mitigation (thinking OFF for `spark`), proven before deploy

Goal: stop Flash-Next from thinking on T1000 calls today, with no code change, if and only if the per-provider `extra_body` actually reaches the wire on every path.

Spec:
- A probe script, `scripts/probe_provider_wire_body.py`, starts a local stub OpenAI-compatible server on 127.0.0.1 (stdlib `http.server`) that records each request body verbatim to a JSONL file and answers with a minimal valid chat completion. The script writes a temporary `HERMES_HOME` whose `config.yaml` declares provider `stub` pointing at the stub, with `extra_body: {chat_template_kwargs: {enable_thinking: false}}`, and drives three real call paths against it:
  (a) one auxiliary call through the real public entry `agent.auxiliary_client.call_llm(...)` (task `title_generation` routed to `stub`);
  (b) one main-agent turn through the real agent entry that uses `agent/transports/chat_completions.py` (a single-turn `AIAgent`/`run_agent` invocation with `model.provider: stub`);
  (c) one MoA reference call through `agent/moa_loop.py`'s public entry with `stub` as a reference model and `max_tokens: 4096`. MoA builds its requests via `call_llm` (`agent/moa_loop.py:20`, `:477`), so (c) must also go through that function, not around it.
  The probe must NOT construct any request body itself. Config reaches the code only through the temporary `HERMES_HOME` the real loader reads (env var `HERMES_HOME`), and the only thing the probe inspects is what the stub server received on the socket.
- It prints one line per path, `PATH <aux|main-stream|main-nonstream|moa> PASS|FAIL <reason>`, then, per path, the captured body's top-level keys, `chat_template_kwargs`, `reasoning`, `reasoning_effort` and `max_tokens`, and exits non-zero unless all three captured bodies carry `chat_template_kwargs.enable_thinking == false`.
- It never touches `/opt/t1000/home` and never uses the network beyond 127.0.0.1.

Bars:
- A1 (builder-executed): the probe runs green on this branch and the three captured bodies are committed as a fixture (`tests/fixtures/provider_wire_body/*.json`). Fixtures are compared as parsed JSON (key order and whitespace ignored); only B5 uses byte comparison.
- A2 (builder-executed, negative): the ONLY change is deleting the `extra_body` block from the temp `config.yaml`. The probe must then exit non-zero and name every path whose captured body lacks the key. Proves both that the probe can fail and that the key in A1 came from config, not from the probe.
- A3 (reviewer-executed): crew-reviewer reruns A1 and A2 in its own detached worktree at the PR head and confirms the same exit codes.
- A4 (human-gated deploy, NOT part of the build): only if A1-A3 pass, ryan-claude proposes to Ryan the live change `providers.spark.extra_body.chat_template_kwargs.enable_thinking: false` in `/opt/t1000/home/config.yaml` (edited as `sudo -u t1000`, never as root), with finn's vLLM counters (`request_success_total` by `finished_reason`, plus request count) snapshotted immediately before and 24 h after. Success = the `length` share over the 24 h window is at most HALF of the pre-change share (measured today at 83% over 24 h), reported with both absolute shares and request counts so a traffic-mix change is visible. If any path in A1 lacked the key, Stage A is dead and only Stage B ships.

## 3. Stage B: engine-proof reasoning mapping for local providers (code)

Goal: T1000's per-model reasoning setting (`none` / `low` / `medium` / `high` / `xhigh` / `max`) takes effect on vLLM AND TensorFold for local providers, with per-family vocabulary, on all three paths.

Spec:
- A provider entry may declare an explicit, opt-in block (no auto-detection by URL):
  ```yaml
  providers:
    spark:
      thinking_control:
        kind: chat_template_kwargs
        switch_key: enable_thinking        # DS4 uses: thinking
        effort_key: reasoning_effort       # omit to never send effort
        effort_map: {low: low, medium: medium, high: xhigh, xhigh: xhigh, max: xhigh}
  ```
- When a request targets a provider with `thinking_control.kind == chat_template_kwargs` and a `reasoning_config` is resolved:
  - `enabled: False` → `extra_body.chat_template_kwargs[switch_key] = False`; no effort key.
  - `enabled: True` with effort E → `chat_template_kwargs[switch_key] = True` and, if `effort_key` is set, `chat_template_kwargs[effort_key] = effort_map[E]`. An E not in `effort_map` is dropped (no effort key sent) and logged once at WARNING. It is never passed through raw.
  - Top-level `reasoning_effort` is never set for these providers. Both engines accept `chat_template_kwargs`, and one form is enough (no `top_level_effort` option; not built).
  - The legacy `extra_body.reasoning` object is NOT sent for such providers.
  - Caller- or config-supplied `chat_template_kwargs` keys win over generated ones: merge, don't overwrite.
- One shared helper, `agent/thinking_control.py::apply_thinking_control(extra_body, reasoning_config, provider_entry) -> dict`, holds all of the mapping logic. It is called DIRECTLY inside the bodies of exactly two request builders (not from a shared intermediate helper): `agent/auxiliary_client.py::_build_call_kwargs` (auxiliary tasks AND MoA reference/aggregator calls, which reach it via `call_llm`: `agent/moa_loop.py:20`, `:477`) and `agent/transports/chat_completions.py` (main agent). No mapping logic lives in either builder.
- Providers without `thinking_control` behave exactly as today (byte-identical request bodies; bar B5).
- At config load, a `thinking_control` block whose `effort_key` is set but whose `effort_map` does not cover every non-`none` effort `parse_reasoning_effort()` can return is logged once at WARNING, naming the provider and each missing effort (an unmapped effort at request time falls back to the template's default, which for Qwen is `xhigh`, the most expensive).

Bars:
- B1 (builder-executed): unit tests over the three builders × {`none`, `low`, `high`, `max`, an unknown effort} × {Qwen-style map, DS4-style map (`switch_key: thinking`, `effort_map: {high: high, xhigh: max, max: max}`)}: assert the exact `chat_template_kwargs` by equality (so `switch_key` is `false` for `none` and `true` for every other effort, and the mapped effort value is exact) and the ABSENCE of `reasoning` / `reasoning_effort` (seeded fixture: every case has a known expected body, so absence is asserted against a case that would carry the key if the guard were missing).
- B1a (builder-executed, no effort key configured): a `thinking_control` block WITHOUT `effort_key` and an override of `low` / `high` must produce `chat_template_kwargs: {enable_thinking: true}` and NO `reasoning_effort` anywhere in the body (neither inside `chat_template_kwargs` nor top level).
- B1b (builder-executed, merge precedence): a config/caller-supplied `chat_template_kwargs: {enable_thinking: true}` plus an override of `none` must produce `enable_thinking: true` on the wire (caller wins); and a caller-supplied `chat_template_kwargs: {foo: 1}` plus override `low` must produce `{foo: 1, enable_thinking: true, reasoning_effort: low}` (merge, not replace).
- B2 (builder-executed): the Stage A probe extended to Stage B, with the main-agent path exercised BOTH streaming and non-streaming (every request-building branch in `chat_completions.py` the probe can reach): stub provider with the Qwen-style `thinking_control`, override `none` → captured body has `enable_thinking: false`; override `low` → `enable_thinking: true, reasoning_effort: low`; T1000 default `high` → `reasoning_effort: xhigh`, never `high`.
- B3 (builder-executed): unmapped effort (e.g. `minimal`) → no effort key in the captured body, and a WARNING naming the dropped value is logged for that call (asserted with a log capture scoped to the single call).
- B4 (reviewer-executed): mutation proofs, each failing at an assertion (rc=1, not a collection error): (i) delete the `effort_map` lookup so raw E passes through → B1/B2 fail; (ii) re-enable the legacy `reasoning` object → B1 fails; (iii) swap the merge order so generated keys overwrite caller keys → B1b fails; (iv) remove the helper call from `chat_completions.py` only → the main-agent case of B2 fails because the captured main-agent body lacks `chat_template_kwargs.enable_thinking`, while the auxiliary and MoA cases in the same run still pass (the reviewer reports both outcomes; a run where everything fails, or where the failure is a crash, does not count as this proof).
- B5 (reviewer-executed): for a provider WITHOUT `thinking_control`, the request body is byte-identical to fork/main's for the same inputs (golden captured on fork/main by the probe, committed as a fixture).
- B7 (builder-executed): a config with `effort_map: {low: low}` produces the load-time WARNING naming the missing efforts; the full Qwen and DS4 maps in this order produce none.
- B6 (reviewer-executed): the repo's own test runner, `scripts/run_tests.sh` on the touched test files plus `tests/agent/test_auxiliary_client.py`, is green, and nothing previously passing now fails.

### Forge notes (rejected findings, kept so they are not re-raised)
- Round 4 asked for an assertion on the builder's intermediate `extra_body` in addition to the wire body. Rejected: every probe assertion is on the bytes the stub received on its socket, the one seam no layer can route around; a transport that strips or rebuilds `extra_body` makes the captured body lack the key and B2 fails. An intermediate assertion would be weaker, not stronger.

## 4. DO-NOTs

- Do not change any request body for providers that do not declare `thinking_control` (B5 is the guard).
- Do not auto-detect vLLM/TensorFold by URL, port or model name.
- Do not send an effort string a template has not been told it accepts.
- Do not edit `/opt/t1000/home/**`, restart any service, or run `hermes` against the live home. Deploy is a separate, human-gated step (A4 and the port to the running branch).
- Do not push, open a PR, or touch other branches. Commit only.
- Do not add a `.env` knob.

## 5. Deploy notes (steer, after review; human-gated)

The live VPS runs `/opt/t1000/src` on branch `ryan/herald-0.20-cutover` (local HEAD `aba713606`, with uncommitted edits), not `fork/main`. Stage B therefore lands in two steps: a PR to `fork/main`, then a cherry-pick onto the running branch in an announced window, as `sudo -u t1000`. Ordering: (0) cherry-pick onto a local copy of the running branch first, resolve any conflicts there, and run the Stage A/B probes plus B6's tests on that result before the window; (1) before the live cherry-pick, verify the RUNNING code ignores an unknown provider key by loading a copy of the live config with a `thinking_control` block through the running branch's config loader in a throwaway `HERMES_HOME` (no error, no behavior change); (2) cherry-pick and restart; (3) confirm the running code reports the new helper active; (4) only then add `thinking_control` for `spark` (Qwen map) and the DS4 provider (DS4 map). Rollback = remove the config block first, then revert the commit. Measure finn's `finished_reason` split before and 24 h after, same rule as A4.
