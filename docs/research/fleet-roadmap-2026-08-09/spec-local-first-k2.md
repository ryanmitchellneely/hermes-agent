# SPEC — Local-first migration of K2's paid LLM lanes (v1)

**Status:** draft for Ryan + Kevin review
**Author:** ryan-claude (spec lane)
**Date:** 2026-08-09
**Pilot lane:** `inbox_thread_classification` → Finn (`spark-b01b`, `gpt-oss:120b`), **shadow only**

---

## Problem + evidence

**The cost thesis does not survive contact with the data. Read this before anything else.**

The brief for this spec assumed K2 is paying meaningful per-token money to
OpenRouter and that local inference would claw it back. Measured live against the
production hub DB (`/opt/k2-hub/k2-hub/k2-hub.db`, `llm_routing_decisions`, 2026-08-09):

```
LIFETIME:  34,233 calls   $58.19   2026-05-26 → 2026-08-09  (~75 days, ~$0.78/day)
30-DAY:    ~25,000 calls  ~$30.2   (~$1.00/day, ~$30/month)
```

Thirty dollars a month. ADR-057 already reached this conclusion independently and
wrote it into the record: *"Cost is explicitly not a justification (K2 lifetime cloud
bill: $28.53)."* That figure has since roughly doubled and is **still** not a
justification. Any version of this spec that leads with savings is selling a number
that cannot pay for the engineering hours to capture it.

So the savings ledger in this spec is **instrumentation, not motivation**. We build it
because it is cheap, because DevBot already proved the schema, and because it is the
only honest way to check the claim later — not because it carries the business case.

**What actually justifies the work**, in priority order:

1. **Data residency (the real one).** PII in LLM prompts was filed as issue #2456.
   Every lane below currently egresses to DeepSeek via OpenRouter. Local inference is
   the only change that makes the residency question *disappear* rather than be
   mitigated — the data never leaves the estate. ADR-037's reasoning is explicitly
   volume-independent: "Four transcripts a day going to DeepSeek is the same
   per-transcript residency problem as fifty."
2. **Deleting a failure class.** OpenRouter credit exhaustion (HTTP 402) once
   silently killed briefs for days. The router now carries a per-provider 402 circuit
   breaker (`llm_router.py`, `_BALANCE_TRIPPED`, keyed per-provider because the balance
   is account-wide) — a real fix, but a *mitigation* of a class that local removes
   outright. **This trade is not free:** it swaps "prepaid balance ran out" for
   "tunnel/box went stale," which is why tunnel-freshness is a first-class gate below
   and not an afterthought.
3. **Latency headroom.** The pilot lane averages **5,050 ms** on DeepSeek. Finn is
   prefill-dominant (≈1.5–2.4k t/s prefill vs 43–59 t/s generation), which is exactly
   the right shape for long-input/short-output verdict work.

### Lane inventory (30 days, live, ordered by volume)

| task_type | calls | $ | avg ms | reaches a customer? | on ADR-057 seat list? |
|---|---|---|---|---|---|
| `call_summary_grounding_judge` | 7,923 | 4.62 | 2,966 | no (internal judge) | no |
| `lead_synthesis` | 5,643 | 0.89 | 2,351 | indirect | no |
| `sms_reply_comprehension` | 2,172 | 0.70 | 2,773 | **send-adjacent** | no |
| `sovereign_credibility_lens` | 1,302 | 5.55 | 2,561 | no (Sovereign lane, not K2) | no |
| `sphere_drift_extraction` | 1,169 | 0.97 | 2,881 | no | no |
| **`inbox_thread_classification`** | **1,142** | **1.67** | **5,050** | **no — internal triage only** | **yes (Decision B v1)** |
| `call_extraction` | 1,055 | 3.47 | 10,418 | no | excluded, cloud model floor |
| `sovereign_gtm_miner` | 982 | 5.08 | 4,462 | no (Sovereign lane) | no |
| `lead_intelligence_brief` | 837 | 1.16 | 6,113 | indirect | excluded (generation-heavy) |
| `comm_comprehension` | 680 | 1.12 | 5,315 | no | **PII lane — gated separately** |
| `hermes_guardrail_check` | 265 | 0.11 | 3,395 | no | yes (Decision B v1) |
| `voice_draft`, `*_narrative` | <100 ea | <0.08 | — | varies | excluded (generation-heavy) |

### Why `inbox_thread_classification` is the pilot

It is the only lane that satisfies all five selection criteria simultaneously:

- **Internal-only blast radius.** Output is `segment / importance / needs_reply /
  summary` JSON feeding Kevin's inbox triage. It touches no send path, no Sierra write,
  no customer-visible surface. A wrong label costs a mis-sorted email.
- **A parity engine already exists.** `k2-hub/src/k2_hub/evals/lane_bakeoff.py`
  carries a full `LaneSpec` for it (`weekly_volume=326`, `build_inbox_thread_classification`,
  `max_tokens=400`, `temperature=0.0`, `context_class="standard"`, a written rubric, and
  `auto_metrics=_JSON_METRICS`). We do not need to build a golden set — we need to point
  an existing harness at a new challenger.
- **Pre-authorized in principle.** It sits on ADR-057 Decision B's non-PII v1 seat list
  **and** in `FINN_SEAT_TASK_TYPES` (`llm_router.py:97`).
- **Ryan's PII condition is already discharged for this lane.** Ryan's sign-off
  (inbox-902, 2026-08-04) was conditional on spot-checking the "PII-redacted" code
  comments into verified behavior. For this lane the behavior is real, not a comment:
  `kevin_inbox/classifier.py` imports and calls both `scrub_pii_for_llm`
  (`hermes_guardrails`) and `redact_prompt` (`prompt_redaction`) on body **and**
  participants before the call (`classifier.py:189`, `:197`, `:202`).
- **Verdict-shaped.** Long thread in (measured peak 3,226 prompt tokens), ≤400 tokens
  out. Prefill-dominant — Finn's strength, not its weakness.

### Topology — verified live, 2026-08-09

- **Finn is UP**, contradicting ADR-057's "offline for three days" premise.
  `tailscale status` from the VPS: `100.125.80.66  finn  tagged-devices  linux  active;
  direct …:41641, tx 860 rx 620`.
- **The endpoint answers and the auth gate holds.** Unauthenticated
  `GET http://100.125.80.66:11435/api/tags` from the VPS returns **401** — the Caddy
  bearer proxy is doing its job.
- **Hub env is already provisioned.** `/etc/k2-hub.env` carries `OLLAMA_REMOTE_URL`
  (`http://100.125.80.66:11435`, matching `spark.py`'s hardcoded `EXPECTED_HOST`/
  `EXPECTED_PORT` exactly), `OLLAMA_REMOTE_TOKEN`, and `K2_LLM_PROVIDER_POLICY=openrouter-only`.
- **Three separate reverse tunnels terminate on VPS loopback**, all owned by `sshd`
  (verified via `ss -tlnp`): `:11435` → serves `qwen3-coder:30b`; `:11436` → serves
  `mistral:7b`; `:11437` → answers `unauthorized` (bearer-proxied, consistent with the
  Kevin-Spark DS4 lane). `:11434` is the VPS's own local ollama (`nomic-embed-text` only).
  **Note the collision hazard:** loopback `:11435` and Finn's tailnet `:11435` are
  different endpoints serving different models. `spark.py` pins the tailnet one by IP and
  rejects anything else, which is what keeps this safe — do not "simplify" that check.
- **The provider client is built and dark.** `llm_providers/spark.py` is complete and
  fail-closed: fixed endpoint, single allowed model (`gpt-oss:120b`), no retries, no
  defaults, no cloud fallback, no router import. Its `llm_complete_with_metadata`
  already returns the shared completion shape (`prompt_tokens`, `completion_tokens`,
  `cost_usd=0.0`, plus `total_duration_ns`/`load_duration_ns`) that router telemetry reads.

**The gap is small and specific.** The box is up, the tunnel is up, the env is set, the
client is written, the eval harness exists, and the seat is on the approved list. What is
missing is: a health record, a policy value that permits a shadow call, one line of model→
provider mapping, a shadow runner, and a savings ledger. That is the whole of v1.

---

## V1 scope

One lane, shadow only, behind a new policy value that cannot weaken the existing one.

1. **Tunnel/endpoint freshness probe** — a recorded, alerting health signal for the
   VPS→Finn path, standing up the parked `k2-spark-node-health` timer. This is the gate
   ADR-057 calls "seven consecutive qualifying green health days," and it is currently
   **not started**.
2. **Extend `K2_LLM_PROVIDER_POLICY` by adding a value** — `openrouter-only+local-shadow`
   — which behaves identically to `openrouter-only` for every *serving* decision and
   additionally permits a non-serving shadow call on an explicitly allowlisted task_type.
3. **Router mapping** so `_provider_for_model` resolves `gpt-oss:120b` to the `spark`
   provider. Shadow path only; `RoutingDecision.select` is untouched.
4. **Shadow runner for `inbox_thread_classification`** — DeepSeek serves (unchanged);
   Finn is called on the same PII-scrubbed prompt; both outputs and the divergence are
   logged; **Finn's output is never returned to any caller.**
5. **Savings + parity ledger** reusing DevBot's exact JSONL schema — `local_api_usd`,
   `frontier_compare`, `frontier_in_per_mtok`, `frontier_out_per_mtok`,
   `frontier_cost_usd`, `saved_usd_vs_frontier`, `is_local`, `tokens_est` — so the two
   estates' numbers are directly comparable.
6. **A parity report** produced by pointing the existing `lane_bakeoff` `LaneSpec` at
   Finn as challenger, with an explicit verdict and the honest cost delta beside it.

---

## Non-goals

- **Cutting over.** V1 changes what is *measured*, never what is *served*. Cutover is a
  separate Ryan+Kevin-gated card.
- **Touching the PII lane.** `comm_comprehension` stays on ADR-037's separate gate
  (shadow parity + Kevin's sign-off + one-way fail-closed ratchet). Nothing here
  accelerates it.
- **Weakening fail-closed behavior.** `openrouter-only` keeps its exact current
  semantics. We add a value; we do not edit one.
- **Any send-path or Sierra-write lane.** `sms_reply_comprehension`,
  `arctic_reactivation_draft_claude`, `voice_draft` are out of scope entirely.
- **Generation-heavy seats.** The `*_narrative` lanes, `conversation_synthesis`,
  `lead_intelligence_brief` — ADR-057 excludes them and this spec does not reopen it.
- **Ryan's `spark-6c82` / DS4 as a K2 serving node.** ADR-057's tenant wall: Ryan's box
  is a different tenant's hardware and may never carry a Kevin-tenant payload. DS4
  (`:11437`) is named here only to explain the topology.
- **Cost optimization as a driver.** Explicitly disclaimed above.

---

## Design sketch

**Policy extension — additive, never subtractive.**

`llm_provider_policy.py` today is a 3-constant module with a frozenset of two values and
a `parse_provider_policy` that raises on anything else. The change adds a third member:

```
PROVIDER_POLICY_OPENROUTER_ONLY_LOCAL_SHADOW = "openrouter-only+local-shadow"
VALID_PROVIDER_POLICIES = frozenset({DUAL, OPENROUTER_ONLY, OPENROUTER_ONLY_LOCAL_SHADOW})
```

The invariants that must be pinned by test, not by prose:
- The new value resolves **serving** exactly as `openrouter-only` does — same provider
  topology, same Anthropic→OpenRouter Claude mapping, same 402 breaker behavior.
- An unknown value still raises. An unset value still defaults to `dual`.
- The shadow call is permitted **only** when the policy is the new value **and** the
  task_type is in an explicit shadow allowlist. Two independent conditions.
- Under plain `openrouter-only`, a shadow call is impossible — the existing live
  configuration keeps its exact current behavior, so this change is a no-op until Ryan
  flips the env deliberately.

**Shadow runner — copy the house pattern, do not invent one.**

`comprehension/call_shadow.py` and `meeting_shadow.py` are the ratified precedent, and
their doctrine is stated in their own docstrings: PII scrub *before* egress, fail-soft
per item, dedup, and "compute + log, never act." The runner inherits all of it:

- Serving call is untouched: DeepSeek returns, caller gets that value, always.
- Shadow call runs on the **already-scrubbed** prompt — reuse the exact string the
  serving call used, so no second redaction path can drift out of sync.
- Any Finn fault (`LLMUnavailableError`, `LLMTimeoutError`, `LLMError`) is **data, not a
  crash** — recorded as an outage row, never surfaced to the caller. `spark.py` raises
  these already; the runner must not add retries or a fallback, both of which `spark.py`
  deliberately omits.
- Both outputs are parsed as JSON and compared field-by-field
  (`segment` / `importance` / `needs_reply` / `summary`), because the lane's
  `auto_metrics=_JSON_METRICS` already scores that shape.

**Savings ledger — DevBot's schema verbatim.**

Per call, append one JSONL row. `local_api_usd = 0.0`; `frontier_cost_usd` computed from
the serving call's real `prompt_tokens`/`completion_tokens` × the DeepSeek rate;
`saved_usd_vs_frontier` = the difference. `tokens_est` flags estimated vs. metered counts
— Finn returns real `prompt_eval_count`/`eval_count`, so this lane can report `false`
where DevBot reports `true`. Roll up daily. **The rollup must print the monthly
extrapolation next to the engineering cost**, so nobody reads a big-looking cumulative
number without its denominator.

**Parity report — reuse, don't rebuild.**

`lane_bakeoff.py`'s runner already resolves a provider per candidate via
`llm_router._provider_for_model(candidate.model_id)` and calls
`provider.llm_complete_with_metadata(...)`. `spark.py` implements exactly that interface.
Once the model→provider mapping exists, Finn becomes a challenger with no harness surgery,
and `lane_bakeoff` records `provider_policy=llm_router.get_provider_policy()` alongside
the result — the report is self-describing about which policy produced it.

**Failure-class swap, stated plainly.** We delete "prepaid balance hit 402 and briefs died
silently" and we buy "the tunnel or the box went stale." The second is only better if it
is *observed*, which is why the health timer is card 1 and not card 5, and why a stale
probe must alert rather than fail quiet — the exact mistake the 402 incident made.

---

## Gates & risks

| # | Gate / risk | Disposition |
|---|---|---|
| G1 | **ADR-057 is `Status: Proposed`, not Accepted.** Ryan signed off 2026-08-04 (inbox-902) conditional on two fixes; kevin-claude confirmed merging the file "did not ratify it." | Decision B is the authority this whole spec rests on. Shadow work may proceed (shadow is not "routing activation"); **cutover may not** until `Status: Accepted`. |
| G2 | **Two ADRs share the number 057** — Ryan's condition (1). | Must be resolved by the ADR owner before ratification. Blocks cutover, not shadow. |
| G3 | **"PII-redacted" comments spot-checked into verified behavior** — Ryan's condition (2). | **Discharged for the pilot lane only** — verified real in `classifier.py:189/197/202`. Not discharged for the other three Decision B seats. |
| G4 | **Seven consecutive green health days not started.** Timer `k2-spark-node-health` is present as unit files but commented out in `deploy/systemd/ENABLED_TIMERS` and has never been installed. | Card 1. Hard gate on cutover. Shadow may run during the observation window and in fact produces the evidence. |
| G5 | **On-box benchmark sanity owed.** ADR-047's one-use authority "was consumed without a result." | Needs re-authorization from Kevin before it can be re-run. Human card. |
| G6 | **Live bearer token was exposed in plaintext during this spec's research** (my redaction failed while reading `/etc/k2-hub.env`). | Rotate `OLLAMA_REMOTE_TOKEN`. Human card, blocked. Value is deliberately not recorded in this document or anywhere in the repo. |
| G7 | Tunnel-freshness becomes the new silent-failure class. | Mitigated by G4's probe + alert. A shadow lane failing silently is low-stakes; the same pattern on a *served* lane is the 402 incident again. |
| G8 | Finn is on flaky WiFi (ethernet run pending per ADR-057), though currently direct and active. | Non-PII seats keep **mandatory** cloud failover per Decision B. This is not optional and must not be "simplified" away at cutover. |
| G9 | Shadow doubles token volume on the lane. | ~1,142 calls/30d; incremental frontier cost is $0 (shadow side is local). Serving cost unchanged. |
| G10 | Tenant wall — Ryan's `spark-6c82` and DS4 may never carry Kevin-tenant payload. | Enforced by `spark.py`'s hardcoded `EXPECTED_HOST`. Any card touching that constant is cross-lane and needs Kevin. |
| G11 | Cross-lane paths: `kevin_inbox/`, `llm_router.py`, `llm_provider_policy.py`, ADR files. | Per CLAUDE.md these need human review. No self-merge. |
| G12 | `spark.py` rejects `response_format` (structured output unsupported). | The lane wants JSON. Shadow must prompt-and-parse, and parse failure is a **parity data point**, not an error to paper over. |

---

## Acceptance criteria

1. `K2_LLM_PROVIDER_POLICY=openrouter-only` produces byte-identical routing behavior
   before and after the change, pinned by a test that fails if the shadow path can be
   reached under that value.
2. An unknown policy value still raises `ValueError`; unset still defaults to `dual`.
3. With the new policy value set, `inbox_thread_classification` serving results are
   unchanged — a test asserts the caller receives the DeepSeek result even when the
   shadow provider raises, returns garbage, or times out.
4. `k2-spark-node-health` is installed, heartbeating, surfacing, and auto-alerting per
   `docs/architecture/observability-principle.md`; a stale probe **alerts** rather than
   failing quiet.
5. Seven consecutive qualifying green health days are recorded and queryable.
6. The savings ledger emits DevBot-schema JSONL rows with real (not estimated) token
   counts, and the daily rollup prints the monthly extrapolation beside the engineering
   cost.
7. A parity report over ≥200 shadow pairs exists, produced by the existing `lane_bakeoff`
   `LaneSpec`, reporting per-field agreement, latency delta, JSON-parse failure rate, and
   Finn outage rate.
8. The report states an explicit verdict in ADR-057's own vocabulary
   (`flip-candidate` / `insufficient` / `errors`) and is filed to both lanes' inboxes.
9. No diff in v1 touches `send_gate.py`, `sierra_client` write lanes, any SMS/SendGrid
   sender, or `RoutingDecision.select` for any served lane.
10. `OLLAMA_REMOTE_TOKEN` is rotated and the exposed value is confirmed dead.

---

## Card decomposition

**Legend — born-status:** `ready` = an agent may start unattended. `blocked` = requires a
named human decision first. Per CLAUDE.md, human cards are born blocked, and nothing
touching K2 send-paths or Sierra may be born ready. No card in v1 touches either.

---

**C1 — Un-park `k2-spark-node-health` and start the green-day clock**
Install the existing-but-commented-out `k2-spark-node-health` timer from
`k2-hub/deploy/systemd/ENABLED_TIMERS` on k2vps. It probes VPS→Finn
(`http://100.125.80.66:11435`) with the fixed synthetic no-PII payload only. Must
heartbeat + surface + auto-alert per `docs/architecture/observability-principle.md`; a
stale probe alerts rather than failing quiet. Record the negative auth test (unauthenticated
`/api/tags` must return 401 — verified live 2026-08-09).
*Parents:* none (root) · *Born:* **ready**

**C2 — Extend the provider-policy enum with `openrouter-only+local-shadow`**
Add a third member to `VALID_PROVIDER_POLICIES` in `k2-hub/src/k2_hub/llm_provider_policy.py`.
It must resolve every *serving* decision identically to `openrouter-only`. Do not edit the
semantics of any existing value. Add tests pinning: unknown still raises, unset still
defaults to `dual`, and the shadow path is unreachable under plain `openrouter-only`.
Cross-lane file — human review required, no self-merge.
*Parents:* none (root) · *Born:* **ready**

**C3 — Map `gpt-oss:120b` → the `spark` provider in `_provider_for_model`**
`llm_router._provider_for_model` cannot currently resolve Finn's model, so nothing can call
it. Add the mapping only. Do not modify `RoutingDecision.select` — no task_type may change
its served provider. This is what lets `lane_bakeoff`'s existing runner treat Finn as a
challenger, since it resolves providers through this same function.
*Parents:* C2 · *Born:* **ready**

**C4 — Shadow runner for `inbox_thread_classification`**
Follow `comprehension/call_shadow.py` doctrine exactly: compute + log, never act. DeepSeek
serves and its result is always what the caller receives. Call Finn on the *same
already-scrubbed* prompt string (never re-redact — a second path can drift). Any Finn fault
is a recorded outage row, never an exception to the caller. Gated on both the new policy
value and a task_type allowlist. Internal-only lane; no send path, no Sierra write.
*Parents:* C2, C3 · *Born:* **ready**

**C5 — Savings + parity ledger in DevBot's schema**
Append one JSONL row per shadow pair using DevBot's exact field names (`local_api_usd`,
`frontier_compare`, `frontier_in_per_mtok`, `frontier_out_per_mtok`, `frontier_cost_usd`,
`saved_usd_vs_frontier`, `is_local`, `tokens_est`) so K2 and T1000 numbers are directly
comparable. Use Finn's real `prompt_eval_count`/`eval_count`, so `tokens_est=false`. The
daily rollup MUST print the monthly extrapolation beside the engineering cost.
*Parents:* C4 · *Born:* **ready**

**C6 — Parity report via the existing `lane_bakeoff` LaneSpec**
Point the existing `inbox_thread_classification` `LaneSpec` (`evals/lane_bakeoff.py`) at
Finn as challenger — no harness surgery, it already resolves providers via
`_provider_for_model` and calls `llm_complete_with_metadata`. Report per-field agreement
(`segment`/`importance`/`needs_reply`/`summary`), latency delta vs the 5,050 ms baseline,
JSON-parse failure rate (`spark.py` rejects `response_format`, so parse failure is a real
data point), and Finn outage rate. Require ≥200 pairs.
*Parents:* C4, C5 · *Born:* **ready**

**C7 — Rotate the exposed `OLLAMA_REMOTE_TOKEN`**
The live bearer token was exposed in plaintext during this spec's research (a redaction
failed while reading `/etc/k2-hub.env` on k2vps). Rotate it on Finn's Caddy proxy and in
`/etc/k2-hub.env`, then confirm the old value is dead. Ryan owns this — it is a
credential operation on Kevin-tenant hardware. The exposed value is deliberately recorded
nowhere in the repo.
*Parents:* none (root) · *Born:* **blocked** (human — Ryan; coordinate with Kevin)

**C8 — Resolve the duplicate ADR-057 number**
Ryan's sign-off condition (1) from inbox-902: two ADRs share the number 057, making every
citation in this spec ambiguous. The ADR owner must renumber one and update citations.
Neither Ryan's lane nor this spec edits `docs/decisions/` unilaterally — Ryan explicitly
declined to. Blocks ADR-057 ratification, which blocks cutover.
*Parents:* none (root) · *Born:* **blocked** (human — kevin-claude / Kevin as Chief Architect)

**C9 — Re-authorize and run the on-box benchmark**
ADR-057 retains "on-box benchmark sanity on the real seat shape" as a conjunctive gate,
but records that ADR-047's one-use authority "was consumed without a result." Running it
again requires fresh authorization. Must run on Finn specifically — ADR-057's tenant wall
bars Ryan's `spark-6c82` numbers from standing in.
*Parents:* C1 · *Born:* **blocked** (human — Kevin)

**C10 — Flip ADR-057 to `Status: Accepted`**
Ryan signed off 2026-08-04 conditional on two fixes; kevin-claude confirmed that merging
PR #3486 "did not ratify it." Once C8 and C9's evidence land, the ADR needs Kevin's
ratification as Chief Architect plus Ryan's confirmation to flip. Nothing downstream of
ADR-057 is decided until this happens.
*Parents:* C8, C9 · *Born:* **blocked** (human — Kevin + Ryan)

**C11 — Cutover decision for `inbox_thread_classification`**
Read C6's parity report, C1's seven green days, and C9's benchmark, then decide whether
Finn serves this lane. Cloud failover is **mandatory** and non-removable per ADR-057
Decision B — Finn unavailable must mean DeepSeek carries it, never a stall. If the verdict
is not a clean `flip-candidate`, the correct outcome is to keep shadowing and say so.
*Parents:* C6, C10 · *Born:* **blocked** (human — Ryan + Kevin)

---

## Open questions

1. **Does the cost framing survive at all, or should this be refiled purely as a
   residency + reliability project?** At ~$30/month, the savings ledger cannot justify
   the hours. I have written it as instrumentation and led with residency — but if Ryan
   wants a *cost* project, the honest answer is that K2 is the wrong estate to look for
   it in, and the Sovereign lanes (`sovereign_credibility_lens` $5.55 +
   `sovereign_gtm_miner` $5.08 = ~35% of 30-day spend across only 2,284 calls) are the
   denser target — but they are Ryan's consulting lane, not K2, and sit outside every
   gate discussed here.

2. **Is a shadow call "workload payload" under ADR-037's amended Gate-0 clarification?**
   ADR-057 permits "non-PII workload payload and provider selection for the Decision B
   seat list" once health + benchmark pass. C4 runs shadow traffic *during* the health
   observation window, before the benchmark. I read shadow-on-an-approved-non-PII-seat as
   permitted since it is neither routing activation nor PII, and it generates the very
   evidence the gates ask for — but this is Kevin's call to confirm, not mine to assume.

3. **Should `hermes_guardrail_check` shadow in parallel?** It is on the same Decision B
   seat list and its ~265 calls/30d would cost nothing extra to shadow alongside. I left
   it out to keep v1 to one lane — but its "PII-scrubbed before egress" claim is still an
   unverified comment (G3 is discharged only for the pilot), so adding it means doing that
   verification too.
