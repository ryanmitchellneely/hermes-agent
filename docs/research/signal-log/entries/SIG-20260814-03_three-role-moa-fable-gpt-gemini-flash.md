# SIG-20260814-03 — Three-tier cloud MoA: Fable 5 advisor · GPT-5.6 orchestrator · Gemini 3.7 Flash worker (OpenRouter promo)

```yaml
id: SIG-20260814-03
date: 2026-08-14
title: "Saboo: 'Fable 5 as advisor, GPT-5.6 as orchestrator, and Gemini 3.7 Flash is the worker. Gemini 3.7 Flash completely changes the cost/capability equation.' Quotes OpenRouter: Gemini 3.7 Flash extra 50% off on OpenRouter through Aug 27; competitive for multimodal + agentic at that price. Live OpenRouter id google/gemini-3.7-flash (list price ~$0.375/M in · ~$1.875/M out before promo math). Same three-role shape as our MoA dual-preset work (refs vs aggregator) and kanban orch/worker split — not a new product install."
index_title: "Cloud MoA triad: Fable5 advisor · GPT-5.6 orchestrator · Gemini 3.7 Flash worker (+ OR 50% off thru 8/27). Steal = lock three roles (advise/route/act) not two; Flash-class worker is the cost unlock. Maps to MoA mesh cards + desk lanes."
source_url: "https://x.com/Saboo_Shubham_/status/2087971050722390469"
source_url_2: "https://x.com/OpenRouter/status/2087952866409656733"
canonical_repo: ""
canonical_docs: "https://openrouter.ai/google/gemini-3.7-flash"
index_links: [docs]
bucket: router
posture: steal
steal_rank: P1
confidence: high
hardware_fit: [cloud, mbp, spark]
stacks_touched: [t1000]
related_plans:
  - "t1000-model-desk"
  - "MoA dual presets"
  - "t_a9d1fec7"
  - "SIG-20260813-08"   # Fable + local Flash fleet
  - "SIG-20260813-04"   # Bot Mode coworkers ≠ this
status: open
status_note: "**OPEN — routing pattern.** Tweet + OpenRouter quote + live model id verified. Screenshot banked. No OR key / no adopt as desk default. Promo window ends 2026-08-27."
distill: none
```

## 1. Claim

[@Saboo_Shubham_](https://x.com/Saboo_Shubham_/status/2087971050722390469) (~119k followers; 86 likes / 66 bookmarks / ~9.6k views):

> Fable 5 as **advisor**, GPT-5.6 as **orchestrator**, Gemini 3.7 Flash as the **worker**.  
> Gemini 3.7 Flash completely changes the **cost/capability** equation.

Quotes [@OpenRouter](https://x.com/OpenRouter/status/2087952866409656733): Gemini 3.7 Flash **extra 50% off** exclusively on OpenRouter through **Aug 27**; competitive for **multimodal + agentic** at that price (~124k views on the promo).

## 2. What we verified

| Check | Result |
|---|---|
| Tweet + quote | Fetched fxtwitter; media present |
| OpenRouter catalog | Live id **`google/gemini-3.7-flash`** (and `:batch`) |
| List pricing (API, per-token) | prompt **3.75e-7** ≈ **$0.375 / M in**; completion **1.875e-6** ≈ **$1.875 / M out** (before the temporary 50% off) |
| Sibling | `google/gemini-3.6-flash` still listed higher; 3.7 is the new cheap tier |
| Hardware pre-filter | N/A (router/product) |

We did **not** re-bench quality; Saboo’s “insane” is qualitative.

Screenshot diagram title: **“Meta LOOP with Fable 5, GPT-5.6 and Gemini 3.7 Flash”**
- **Chief Operator / Orchestrator = GPT 5.6** — main hot path: Plan → Delegate → Verify → Synthesize; also Escalate
- **Board Advisor = Fable 5** — *on-demand consulted critic – **not in hot path***; strategy, decomposition critique, risk spotting, taste; feedback for MC
- **Labor layer = N× Gemini 3.7 Flash workers** (A–D) — parallel cheap execution subtasks; results back for verification

## 3. Takeaways (max 5)

- The interesting structure is **three roles**, not two: **taste (advisor)** ≠ **route/orchestrate** ≠ **act (worker)**. Classic MoA often collapses advise+act; Saboo separates Fable taste from GPT control from Flash grind.
- Critical detail: **advisor is off the hot path** (consulted, not every turn). That is cheaper and cleaner than Hermes MoA `fanout: user_turn` which always pays refs.
- **N parallel Flash workers** under one orchestrator — same grammar as kanban cap / delegate_task fan-out; worker price is the unlock (OR promo thru 8/27).
- Matches our doctrine: strong chair / cheap hands (SIG-08 Fable+local Flash; MoA mesh cards; kanban orch=Flash worker=120b).
- Do not confuse with Bot Mode coworkers (durable profiles) or Nemotron local Flash — same *role grammar*, different runtime.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Three-role MoA grammar** — Advisor (taste/critique) · Orchestrator (plan/tools/route) · Worker (bulk act) | Fold into MoA dual-preset card `t_a9d1fec7` / doctrine card: optional third slot or explicit naming so Local/Review presets stop overloading aggregator | **P1** | open |
| S2 | Watch **Gemini 3.7 Flash** as cloud worker candidate only if we ever open paid OR lane | No key, no default; note promo end 2026-08-27 | P2 | watch |

**Primary steal:** S1

## 5. Do not

- Add OpenRouter API keys (Ryan cost law: subscriptions first, no BYOK surprise).
- Replace Grok desk default with GPT-5.6 orchestrator on vibes.
- Treat promo pricing as permanent scoreboard.

## 6. Next action

- [x] entry + INDEX + STEALS
- [ ] comment S1 onto mesh MoA card `t_a9d1fec7` when next touched — **no new card**

## 7. Chat blurb

**SIG-20260814-03** · router · steal **P1** · high  
Fable5 advisor · GPT-5.6 orch · Gemini 3.7 Flash worker (+ OR 50% off thru 8/27).  
**Steal:** three-role MoA grammar (advise/route/act). No OR keys.
