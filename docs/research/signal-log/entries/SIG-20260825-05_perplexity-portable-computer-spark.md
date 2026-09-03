# SIG-20260825-05 — Perplexity Portable Computer: their full agent runtime local on DGX Spark, benchmarked AGAINST hermes-agent (our upstream). Harness ablation is the gift; adviser-rung escalation is the steal.

```yaml
id: SIG-20260825-05
date: 2026-08-25
title: "Perplexity launches Portable Computer on NVIDIA DGX Spark (433k views): orchestrator LLM, subagent LLM, planner, tool router, scheduler, persistent task queue, local search index, OS-enforced fail-closed sandbox — all local, apt-installable. Local models: PPLX 27B (post-trained on their own harness) or Qwen 3.8 27B; Nemotron 3.5 Lightning soon. Cloud escalation is per-step, user-gated, PII-classified, show-what-leaves, and the frontier model returns TEXT GUIDANCE ONLY. Internal benches put their harness ~8pts above hermes-agent on same-class 27B locals — T1000 is a hermes-agent fork, so they published an ablation of OUR lineage."
index_title: "Perplexity Portable Computer on DGX Spark: their harness 82.6 vs hermes-agent 74.0 (vendor bench, stock 27B) = ~8pts sitting in OUR harness design. Steal = adviser rung (local keeps loop, frontier text-only). Carded ST-16/ST-17."
source_url: "https://x.com/perplexity_ai/status/2092268362386780270"
canonical_repo: ""
canonical_docs: "https://www.perplexity.ai/hub/products/portable-computer"
index_links: [docs]
bucket: harness
posture: steal
steal_rank: P1
confidence: medium
hardware_fit: [spark]
stacks_touched: [t1000, k2, sovereign]
related_plans:
  - "t_610d4184"
  - "t_a133f091"
status: carded
distill: none
```

> **Reconciled 2026-09-03.** This signal was written up twice on 2026-08-25 — a hermes-desk watch/P2 note on the VPS (this id, `-05`) and a carded steal/P1 write-up on the Mac (as `-01`, an id the VPS had already given to the gguf-symlink signal). The Mac body is kept under the canonical VPS id; the superseded desk verdict was: "OPEN — watch P2, no card. Hardware pre-filter N/A. Paid subscribers only. Cloud escalate + inbox connectors. Would displace 120b/Flash. 82.6 vs Hermes 74 is their bench, same 27B — harness claim, not a model win. Do not install."

## 1. Claim

Perplexity Computer's entire runtime — orchestrator LLM, subagent LLM, agent harness — running fully local on NVIDIA DGX Spark, no cloud dependency. Frontier cloud (15+ models) only as a user-gated, PII-flagged, text-guidance-only adviser. Local steps carry no per-token charge.

## 2. What we verified

| Check | Result |
|---|---|
| Product page | [perplexity.ai/hub/products/portable-computer](https://www.perplexity.ai/hub/products/portable-computer) — apt package (`apt-get install perplexity`), Linux/DGX-OS, Pro/Max sub required. Windows Sept; **macOS not roadmapped** |
| Architecture (press) | Harness = planner + tool router + scheduler + persistent task queue + local search index. Skills load/unload on demand; connectors (Gmail/Outlook/Slack/GitHub) are **compact CLI tools, not full MCP defs**; small system prompt. Self-verification hooks. vLLM underneath, BYO endpoint |
| Sandbox | OS-enforced; restricts processes/filesystem/network. **Fail-closed: sandbox unavailable → tools disabled**, never silently downgraded |
| Escalation | Per-step, user-gated. Harness selects minimal context, runs a **PII classifier**, **shows exactly what leaves**. Remote model returns **text guidance only** — no tool/file/conversation access |
| Models | PPLX 27B (post-trained **on their own harness**, 3-bit, 17.4GB, 32GB RAM) · Qwen 3.8 27B (4-bit, 27.6GB, 24GB RAM) · Nemotron 3.5 Lightning 30B-MoE coming (19GB, 36GB RAM) |
| Benches (ALL vendor-internal — **claimed**, not measured by us) | Local Knowledge Work Bench (53 tasks): theirs on stock Qwen 27B **82.6** / PPLX post-train **85.4** / Pi (OSS) 77.6 / **hermes-agent 74.0**. BrowseComp: 66.7 vs Pi 50.2 vs **Hermes 43.9**. Terminal Bench 2.1: local 59.6 @ ~$0 · +adviser **73.0 @ ~$0.415/rollout** · Opus-alone 82.4 @ ~$0.65 |
| Lineage (measured by us) | `~/Documents/T1000` remotes: **origin = NousResearch/hermes-agent** (MIT), fork = ryanmitchellneely/hermes-agent, product = t1000. Their "Hermes" bench row IS our upstream. Teknium reply on the launch thread: "This app looks familiar 🫣" |
| Hardware fit (measured by us) | ryan-spark = GB10, 121GB, Ubuntu 24.04, 3.7TB NVMe (3.2TB free) — **meets spec exactly**. But 104/121GB resident (120b advisory) → models-board serialization rule applies before any install |

## 3. Takeaways (max 5)

- A third party published an ablation of our harness lineage: **~8pts of knowledge-work performance sits in harness design** (context rationing, escalation shape), +2.8 more from harness-specific post-training. Weights are the cherry, harness is the cake.
- **Adviser rung** is the headline steal: local model keeps the loop; frontier answers ONE distilled, gated, PII-screened question as text. ~60% of the frontier gain at well under the cost — and it directly attacks the 2026-08-11 bare-`hermes -z` Opus burn (197k output tokens).
- Small local models need **rationed context**: compact CLI tool defs beat MCP schemas at 27B scale. hermes-agent's broad tool surface is a plausible chunk of the gap on our zero-cost lanes.
- Fail-closed sandboxing + PII-preflight/show-what-leaves are house-doctrine-shaped and absent from upstream; both are PR-able upstream per the monthly-rebase/upstream-generic ruling (2026-08-10) — upgrades Kevin's hermes too.
- Sovereign angle: strongest validation yet of the local-first privacy pitch — and its commoditization (~$4k Spark + subscription = shrink-wrapped sovereign AI). Moat stays integration/agnosticism; managed-deployment rung opens.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | Adviser-rung escalation (local keeps loop; frontier = gated text-only consultant) | Design note → fork or upstream PR — card **t_a133f091** (ST-17) | P1 | carded |
| S2 | Harness teardown vs ours (context rationing, CLI tool defs, skills load/unload, fail-closed sandbox, PII preflight) | Two-phase teardown (read-only, then install-on-spark) — card **t_610d4184** (ST-16) | P1 | carded |
| S3 | Harness-specific post-training | Fold into Student model program via hermes-agent's existing trajectory-generation tooling — no new card until ST-16 findings | P2 | open |
| S4 | Small fixed bench for local lanes (their 53-task pattern) | ~20-task K2/Juice bench to make model-per-lane a measured decision — no card yet | P2 | open |

**Primary steal (one only):** S1

## 5. Do not

- Quote 82.6/74.0/73.0-at-$0.415 as fact — every number is **vendor-internal and unaudited**; hermes-agent is general-purpose/multi-platform vs their knowledge-work appliance.
- Install the deb on ryan-spark while the 120b is resident (104/121GB used) — memory serialization rule, and phase (b) needs a Pro/Max sub Ryan has not approved.
- Confuse their "Hermes" bench row with anything other than NousResearch/hermes-agent — it IS our upstream; do not write "unrelated product" anywhere.
- Rebuild the ladder around adviser-only before the design note settles trigger + preflight + fail-closed behavior.

## 6. Next action (mechanical)

- [x] entry + INDEX
- [x] add STEALS.md rollup row (S1)
- [x] kanban cards `t_610d4184` (ST-16), `t_a133f091` (ST-17) — both sticky-blocked needs_input on Ryan
- [ ] on ST-16 phase (a) findings: update this entry + decide S3/S4 carding

## 7. Chat blurb (paste-ready, ≤6 lines)

**SIG-20260825-05** · harness · **steal P1** · medium
Perplexity shipped its full agent runtime local on DGX Spark — and benchmarked it against hermes-agent, our upstream: their harness 82.6 vs 74.0 on stock 27Bs (vendor bench). ~8pts sit in harness design.
Primary steal: **adviser rung** — local model keeps the loop, frontier returns one gated, PII-screened, text-only answer (~60% of frontier gain, fraction of cost).
Carded: ST-16 teardown (t_610d4184), ST-17 adviser design (t_a133f091) — both blocked on Ryan (sub+memory window; lane pick).
ryan-spark meets the hardware spec exactly.
