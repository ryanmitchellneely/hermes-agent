# SIG-20260821-01 — UIUC LLMRouter: learned query-to-model routing library (not a desk install)

```yaml
id: SIG-20260821-01
date: 2026-08-21
title: "Dan Kornas promo of ulab-uiuc/LLMRouter — 16+ learned query-to-model routers (KNN/SVM/MLP/Elo/graph/Router-R1) + xRouteBench; claimed +14.6% vs strongest fixed-model baseline. Academic library, not a T1000 control plane."
index_title: "UIUC LLMRouter (★2443 MIT, pip llmrouter-lib 0.4.0) — 16+ learned query routers + xRouteBench +14.6% vs strongest fixed model. Watch P2. Third axis (query-complexity before the turn) vs our lane standings router and Switchyard stage_router. Do not install; OpenClaw proxy is a second control plane."
source_url: "https://x.com/DanKornas/status/2090628879215948279"
source_url_2: "https://x.com/DanKornas/status/2090628703445189044"
canonical_repo: "https://github.com/ulab-uiuc/LLMRouter"
canonical_docs: "https://arxiv.org/abs/2608.06867"
index_links: [repo, docs]
bucket: router
posture: watch
steal_rank: P2
confidence: high          # parent+reply fetched verbatim via fxtwitter; GitHub API + PyPI + README + arXiv abstract read live; no local install or re-bench
hardware_fit: [none]
stacks_touched: [t1000]
related_plans:
  - "SIG-20260811-06"     # NeMo Switchyard — per-turn stage_router; already carded ST-13
  - "SIG-20260808-02"     # Codex Router — parent-strong / child-cheap
  - "t_95bb6eb2"          # ST-13 observer; do not fold this library into that card
  - "local-inference-fleet"
status: open
status_note: "**OPEN — watch P2, no card.** Hardware pre-filter N/A (not a PCIe-offload win). 14.6% is xRouteBench vs the strongest *fixed* model on academic QA/math/code + 8 xRouteBench sets — ceiling arm exists, traffic does not match ours. Installing the lib or the OpenClaw OpenAI proxy would be a second control plane in front of a router we already own. Taxonomy only: query-complexity ≠ lane ownership ≠ mid-run stage signals."
distill: none
```

## 1. Claim

[@DanKornas](https://x.com/DanKornas/status/2090628703445189044) (Dan Kornas; ~97.6k followers; parent **443 likes / 82 RTs / 532 bookmarks / 17.3k views** at read; 2026-08-21 02:34 UTC; note-tweet + README screenshot). Reply Ryan pasted is the GitHub link card only (15 likes / 781 views). Fetched verbatim via `api.fxtwitter.com`:

> Every LLM query doesn’t need your biggest, most expensive model.
>
> LLMRouter is an open-source library for builders who want to route each query to a suitable LLM instead of sending every task to one default model.
>
> • 16+ routing methods — KNN, SVM, MLP, matrix factorization, Elo, graph-based, …
> • Five categories — single-round, multi-round, multimodal, agentic, personalized
> • Unified CLI — train, infer, Gradio chat
> • Data pipeline — 11 benchmark datasets
> • Extensible plugin workflow
>
> MIT. Link in the reply.

He is a **megaphone**, not an author. Paper/lib is UIUC U Lab (Tao Feng, Fangxu Yu, Haozhen Zhang, et al.), arXiv **2608.06867**, project page `ulab-uiuc.github.io/LLMRouter`.

## 2. What we verified

| Check | Result |
|---|---|
| Post body | **verbatim** via fxtwitter; parent is the claim, reply is the GitHub card + newsletter |
| Repo | `ulab-uiuc/LLMRouter` — **★2,443 / 247 forks / 35 open issues**, **MIT**, created **2025-10-07**, pushed **2026-08-20T08:24Z**, homepage project page. 459 commits on `main`. Not a same-day drop — Dec 2025 release, 1k★ by Jan 2026 |
| PyPI | `llmrouter-lib` **0.4.0**, MIT, `requires-python >=3.10` |
| Paper | arXiv **2608.06867** *LLMRouter: Unified Infrastructure for Developing, Evaluating, and Deploying LLM Routers*. Abstract (verbatim): learned routers beat the strongest fixed-model baseline by **14.6% relatively**; lightweight routers get more competitive under tight cost; user-conditioned routing helps personalization. Formulation = sequential decision with five parts: **context encoders, model encoders, scoring functions, decision rules, learning signals** |
| xRouteBench | HF `ulab-ai/xRouteBench`. README: **17 routers × 8 datasets** (classic NLP, memory, time-series, video, multimodal math, personalized). Eval **replays pre-recorded executions against 18 candidate LLMs** — local-router sweep is zero API cost. Reward `alpha * performance - beta * cost` |
| Train-data pipeline | 11 datasets: Natural QA, Trivia QA, MMLU, GPQA, MBPP, HumanEval, GSM8K, CommonsenseQA, MATH, OpenbookQA, ARC-Challenge (+ Geometry3K / MathVista / Charades-Ego multimodal) |
| Router inventory (README tables) | Single-round: knn / svm / mlp / mf / elo / routerdc / automix / hybrid_llm / graphrouter / causallm_router / smallest_llm / largest_llm. Multi-round: `router_r1` (separate repo, NeurIPS'25). Multimodal: `tsrouter`. Personalized: `gmtrouter`, `personalizedrouter`. Agentic: `knnmultiroundrouter`, `llmmultiroundrouter` |
| Local endpoints | README supports Ollama/vLLM/SGLang via OpenAI `/v1` + empty API key for localhost |
| OpenClaw hook | In-tree `openclaw_router/` — OpenAI-compatible `/v1/chat/completions` proxy, Slack/Discord via OpenClaw gateway, optional `~/.llmrouter/openclaw_memory.jsonl`. **Startup script also starts an OpenClaw gateway** |
| Hardware pre-filter | **N/A / pass.** Win is query→model selection, not removing a PCIe host↔device transfer. No tok/s claim, no batch-size trap. Ceiling arm **exists** (strongest fixed model) — unlike SparDA's void accuracy column |
| Local install / re-bench | **Not run.** Numbers below = **claimed** |
| Duplicate URL | No prior LLMRouter / xRouteBench / ulab-uiuc entry in this tree |

**Our stack already answers two other routing questions.** `~/.t1000/routing/` (SR-1…SR-8) is **lane ownership** from offline standings, applied once at dispatch. SIG-20260811-06 / `t_95bb6eb2` is **mid-run stage signals** over tool-result history (observer, not installed). LLMRouter sells a **third** question: *before the turn, how hard does this query look?* via a trained classifier. That is Switchyard's `llm_classifier` axis, which we already declined as an extra model call — their KNN/Elo variants skip the extra LLM but need labeled query→best-model pairs we do not have.

## 3. Takeaways (max 5)

- **Dan Kornas ≠ the artifact.** UIUC library + paper, public since late 2025, now being clipped. Cite the repo/paper, not the influencer frame.
- **+14.6% is a real ceiling-arm comparison and still the wrong traffic.** Strongest-fixed-model is the right control; xRouteBench / MMLU / GSM8K / HumanEval is not desk / kanban / FILE-fence work. Do not quote 14.6% as a fleet saving.
- **Three routing axes, do not collapse them.** (1) lane ownership — we have. (2) mid-run stage — carded ST-13. (3) query-complexity before the turn — this library. ST-13 must stay tool-result history, not grow a KNN trainer.
- **Replay-of-pre-recorded executions is the good methodology** (xRouteBench local sweep). Same shape as Switchyard RESCUE/LOSS: you cannot score a router without the cheap-model counterfactual. Already owned by `t_95bb6eb2` Phase 2.
- **OpenClaw / `llmrouter serve` is a second control plane** in front of Hermes providers, with a startup script that launches someone else's gateway. Same reject as Switchyard's Rust proxy + OpenRouter quickstart.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Name the three routing axes and keep them separate** — lane ownership (offline standings) ≠ mid-run stage (tool-result history) ≠ query-complexity (trained classifier / Elo / KNN before the turn) | When ST-13 or the standings router is next touched, one sentence in the card/skill: LLMRouter is axis 3 and is **not** in scope. Do not train a KNN on academic benches to pick Grok vs 120b vs Flash | **P2** | watch — no ticket |
| S2 | Pre-recorded multi-model executions as the only honest router bench (xRouteBench replay) | Already the RESCUE/LOSS arm on `t_95bb6eb2` Phase 2. Do not open a parallel xRouteBench install | P2 | fold, not card |
| S3 | Five-component router taxonomy (context encoder / model encoder / scoring / decision / learning signal) | Citation-only if we ever write down our own router. We already have pins + Wilson standings + (planned) stage observer | P2 | log only |

**Primary steal (one only):** S1

## 5. Do not

- Do **not** `pip install llmrouter-lib` onto `~/.t1000`, Spark, or the VPS.
- Do **not** run `llmrouter serve` / `./scripts/start-openclaw.sh` or stand up their OpenAI-compatible proxy in front of Grok / claude-acp / `:8889` / `:11435`.
- Do **not** quote **14.6%** as a T1000 cost or quality win.
- Do **not** open a new steals/mesh card — ST-13 already owns per-turn routing; this is a different axis and a worse install.
- Do **not** curl\|sh anything from the README (ComfyUI linker, OpenClaw startup).
- Do **not** spend API budget generating their 11-dataset training set.

## 6. Next action (mechanical)

- [x] write entry
- [x] regenerate INDEX
- [ ] none — **no STEALS.md row** (not P0/P1), **no card**, **no comment on `t_95bb6eb2`** (would mix axes)

## 7. Chat blurb (paste-ready, ≤6 lines)

**SIG-20260821-01** · router · **watch P2** · high
UIUC LLMRouter (★2443 MIT) — 16+ learned query routers + xRouteBench +14.6% vs strongest fixed model.
**Do not install.** Third axis (query-complexity) vs our lane router and Switchyard stage_router.
OpenClaw proxy = second control plane. 14.6% is academic traffic, not desk.
Entry: `docs/research/signal-log/entries/SIG-20260821-01_uiuc-llmrouter-xroutebench.md`
