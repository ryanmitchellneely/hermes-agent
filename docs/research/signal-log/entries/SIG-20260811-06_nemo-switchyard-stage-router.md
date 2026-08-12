# SIG-20260811-06 — NVIDIA NeMo Switchyard

```yaml
id: SIG-20260811-06
date: 2026-08-11
title: "NVIDIA NeMo Switchyard — signal-driven per-turn model router (Rust, pre-alpha)"
source_url: "https://x.com/teksedge/status/2087333241888076000"
canonical_repo: "https://github.com/NVIDIA-NeMo/Switchyard"
canonical_docs: "https://developer.nvidia.com/blog/route-ai-agent-workloads-across-models-with-nvidia-nemo-switchyard/"
bucket: router
posture: steal
steal_rank: P0
confidence: high
hardware_fit: [spark, mbp, none]
stacks_touched: [t1000]
related_plans: [t_95bb6eb2, t_06fde05b, t_c5510683, t_6c3fd131]
status: carded
distill: none

index_title: "NeMo Switchyard — per-turn stage-router signals (tool-result history, zero extra LLM call). Orthogonal to our standings router. Pre-alpha, do NOT adopt as runtime"
index_links: [repo, docs]
status_note: "carded ST-13 `t_95bb6eb2` (steals, blocked) — pattern-mine the signal set + RESCUE/LOSS calibration; runtime adoption REJECTED (pre-alpha, second control plane, OpenRouter-key quickstart in front of Max/claude-acp)"
```

## 1. Claim

NVIDIA "open-sourced NeMo Switchyard, a model router designed for AI agents" — route each request to the model best suited for it, locally, against Ollama / vLLM / NIM / any OpenAI-compatible endpoint. Routing can consider latency, cost, capability, load, errors, agent state. Headline experiment: an escalation setup with **Nemotron 3.5 Lightning + Claude Opus 4.8** sent only **7% of calls** to the frontier model for a **74% cost reduction** at **~6 points** of accuracy.

## 2. What we verified

**Repo is real, and older than the post implies.** `NVIDIA-NeMo/Switchyard` — **★485, Apache-2.0**, **created 2026-05-19**, 62 forks, 79 open issues, 282 files, pushed 2026-08-12T01:42Z (minutes before this fetch). Releases: `v0.0.1` + `v0.1.0` **2026-06-30**, `v0.2.0` **2026-08-10**.

**⚠️ "NVIDIA open-sourced" is the announcement, not the release.** The repo has been public ~3 months and shipped its first tag ~6 weeks ago. What landed 2026-08-11 is the coordinated NVIDIA blog + LangChain benchmark, bundled with the Nemotron 3.5 Lightning launch. Do not cite this as a same-day drop.

**It is Rust, not Python** — a proxy (`switchyard-server`, `cargo install`), a library (`switchyard-libsy`), a protocol crate, and a translation crate. The Python surface is only the `nemo-switchyard[cli]` launcher.

**⛔ The vendor's own maturity statement:** *"Switchyard is pre-alpha software that is evolving rapidly. The API and algorithms are expected to change significantly before we reach v1.0."* + a `[!WARNING] Experimental software. Not for production use.`

**The headline numbers are sourced, and they are not the repo's.** 7% / 74% / ~6 points comes from a **LangChain** benchmark over **145 multi-turn agentic tasks** (customer-support dialogue, incident investigation, workflow automation), using the **escalation** router with Nemotron 3.5 Lightning as weak and Claude Opus 4.8 as strong. The repo's own `benchmark/` directory runs something else entirely — **Harbor Terminal-Bench Lite**, with checked-in configs naming `opus-4-7`, `gpt-5-5`, kimi and gemini. Neither number set was reproduced by us.

**Four routing strategies, and only one of them is novel to us:**

| Strategy | Decides on | Extra model call? |
|---|---|---|
| `llm_classifier` | predicted difficulty of the request, **before** running it | yes, per turn |
| **`stage_router`** | **signals already in the conversation — tool-result history** | **no** (at threshold `0.0`) |
| `llm_classifier` + `mode="escalation"` | a judge reading the **completed** weak turn | yes, until latched |
| `random` | fixed split for A/B | no |

**`stage_router`'s signal set, verbatim from their docs** — this is the part worth stealing:

- **WRONG → capable tier:** `severity` (windowed error severity), `spinning` (deep churn with no reads or writes), `exploring` (reading or planning without producing).
- **PROGRESS → efficient tier:** `recent_production_intensity` (writes and edits landing over the recent window).
- Axes are **corroborative**: signed score `tanh`-squashed into `[0,1]`, so **one full signal scores ~0.46** — just under the recommended `0.5` — and a second corroborating signal is what pushes it over. **A critical-error severity is a hard override that escalates on its own.**
- `confidence_threshold = 0.0` is explicitly *"Cost/latency-sensitive. Every signal-based verdict is accepted; **no per-turn LLM call**. Critical-error signals still escalate to capable."*
- The recommended `0.5` is *"Derived from SWE-Bench Pro Python-75 calibration"* — a Python SWE task mix, not agentic desk work.
- **`capable_first` is unbenchmarked.** Their warning: *"Every published threshold and routing result comes from `efficient_first` runs… no calibrated thresholds for it and no measured accuracy or cost figures."* Quality-first is exactly the picker our instincts would reach for, and it is the one with no numbers.

**The escalation router's failure design is good and worth copying:** it calls weak, **buffers** the reply, then judges the completed turn (*"the judge therefore rates work the weak model actually did, not a prediction about work it might do"*), increments a streak on escalate, resets on decline, and only latches to strong at `confirmations` (default 2). And: *"A judge that times out, errors, or returns an unparseable verdict **fails open**: the turn serves the buffered weak reply and the existing streak is **held rather than cleared**. A judge failure never creates a strong-tier latch."*

**Their threshold-calibration recipe is a complete, cheap methodology** — `~40–75` pure-capable tasks + `~20` pure-efficient probes stratified across four quadrant candidates (easy+clean, easy+tricky, hard+structural, hard+localized), then:

```
RESCUE = capable-fail ∩ efficient-pass   → escalation pays here
LOSS   = capable-pass ∩ efficient-fail   → do NOT escalate here
SAFE   = both pass
HARD   = both fail
```

…choose the lowest threshold that rescues RESCUE without over-escalating LOSS. They also note the honest caveat that in stage-router the efficient model inherits partial context, so RESCUE measured from pure-efficient runs is a **conservative lower bound**.

**Key-free local deployment IS supported** — the quickstart's `OPENROUTER_API_KEY` is a default, not a requirement. Their overview §"Self-hosted targets": *"Any target can point at an OpenAI-compatible model server you operate… The client needs no `api_key_env` when the server does not require a credential."* So a pure Ollama/vLLM/DS4 deployment takes zero keys.

**Our router is a different axis, and the gap is real.** `~/.t1000/routing/` is **5,075 LOC across 6 modules + 6 test files** (SR-1…SR-8 of the standings-router spec): `capability.py` probes what each provider actually serves, `evidence.py` normalizes scoreboard rows into `Measurement`, `standings.py` ranks within one instrument on Wilson lower bounds, `pins.py` holds lane pins, `route_config.py --check` reports drift. Every one of those answers **"which model should own lane X"** from accumulated offline evidence, decided once and applied at dispatch. **We have zero per-turn routing** — a card is pinned to a model for its whole run. Switchyard's `stage_router` answers a question our stack does not ask.

## 3. Takeaways

- **The stage-router signal set is computable from telemetry we already emit, with no extra model call.** Kanban `task_events` already carry errors, retries and `consecutive_failures`; workers already produce tool results. `spinning` (churn with no reads/writes) and `recent_production_intensity` (edits landing) are arithmetic over data on disk.
- **We have a live pathology this shape would have caught:** `t_d68e505a` burned its circuit breaker twice on *"iteration budget exhausted 90/90"* — textbook `spinning`, with no escalation and no tier change, and it stalled three downstream cards as the sole parent.
- **RESCUE/LOSS is the instrument `standings.py` is missing.** Wilson lower bounds rank models *within* an instrument; nothing in our stack measures where escalation **pays**. We have never run the counterfactual arm — LAB-SCOREBOARD has 421 rows of "what the live model did" and 0 rows of "what the cheaper model would have done on the same task."
- **"Judge the completed turn, not the predicted difficulty"** is a cheaper, more honest gate than a-priori capability scoring, and it degrades safely (fail-open, hold the streak, never latch on a judge failure).
- **Adopting the runtime would be a second control plane** in front of a tested router we already own — the same verdict as OMH (`SIG-20260807-04`), for the same reason, with "pre-alpha / not for production" added on top.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Per-turn tier signals from tool-result history, zero extra LLM call** — severity / spinning / exploring → capable; production-intensity → efficient; corroborative `tanh` score; critical-error hard override | Port the *signal set and scoring shape* into our dispatch layer as a read-only **observer first**: compute the score per turn from existing `task_events` + tool results, log the verdict it *would* have made, change no routing. Then compare its verdicts against real card outcomes before it gets a vote | **P0** | carded ST-13 |
| S2 | **RESCUE / LOSS / SAFE / HARD quadrant calibration** with a stratified ~20-task efficient probe | The counterfactual arm our scoreboards have never had. Build it on an existing instrument (golden / repair-battery), not a new one. Feeds `standings.py` an escalation-payoff number instead of a within-instrument rank | P1 | open — folds into ST-13 phase 2 |
| S3 | **Judge the completed turn + fail-open streak** — buffer the weak reply, judge what was actually produced, latch only after N consecutive confirmations, never latch on judge failure | Adopt as the **design contract** for any escalation gate we build (including the approval gate on `t_c5510683`): a broken judge must degrade to "serve the cheap answer, hold the streak", never to "escalate" and never to "reset" | P1 | open — log only |

**Primary steal (one only):** **S1**

## 5. Do not

- ⛔ **Do not put our Claude lane behind it.** `switchyard launch claude --model switchyard` with `OPENROUTER_API_KEY` is per-token billing stacked on top of a Max subscription that already runs via **claude-acp (Path C)**. That is the exact failure the desk cost rule forbids — *"Never add provider API keys… fail loudly rather than key-fallback."* A proxy in front of Claude Code is a billing-model change wearing a routing-upgrade costume.
- ⛔ **Do not install it as a runtime.** Pre-alpha by the vendor's own label, Rust/cargo build, and it would sit in front of `~/.t1000/routing/` (5,075 LOC, 6 test modules) as a **second router with its own config format**. Pattern-mine only.
- ⛔ **Do not trust its accounting yet.** Known issue 0.2.0 #2: *"Routing-tier attribution is missing from `/v1/stats` and `/metrics` for LLM-classifier judge failures that route to the default target, **escalation decisions**, and **`stage_router` fallback decisions.**"* A router that cannot tell you which tier served a request is unauditable — the same class of failure as the DS4 `ExecStartPre` that verifies a receipt instead of a binary.
- ⛔ Known issue 0.2.0 #1: *"Buffered upstream work continues after the client disconnects, so a cancelled request can still incur provider cost."* For a router whose whole mechanism is buffering a weak reply, that is a live cost leak.
- **Do not reach for `capable_first`** without your own calibration — it is the picker with zero published thresholds or measured figures.
- **Do not carry `0.5` over as our threshold.** It is calibrated on SWE-Bench Pro Python-75. Our task mix is kanban worker cards and format lanes.
- **Do not conflate this with `SIG-20260811-04`.** That is Nemotron 3.5 Lightning (the model); this is Switchyard (the router). Same launch, different artifacts, different repos.

## 6. Next action (mechanical)

- [x] add/update STEALS.md rollup
- [x] kanban card `steals` ST-13 (blocked)
- [ ] AUTOMATION-ROADMAP row
- [ ] patch skill

## 7. Chat blurb

NVIDIA NeMo Switchyard: real repo (★485, Apache-2.0) but public since **May**, and the vendor labels it **pre-alpha / not for production**. The 7%/74%/6pt numbers are **LangChain's**, 145 multi-turn tasks, escalation router — not in the repo's own benchmarks. Steal: the **stage_router signal set** (severity/spinning/exploring vs production-intensity, corroborative score, **zero extra LLM call** at threshold 0.0) — it answers "which tier for THIS turn," a question our standings router doesn't ask, from telemetry we already emit. Plus their **RESCUE/LOSS** calibration, the counterfactual arm our scoreboards have never run. Runtime adoption rejected: second control plane, and the quickstart path bills OpenRouter tokens in front of a Max subscription.
