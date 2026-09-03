# SIG-20260823-01 — OpenViking: filesystem context DB; 91% is the OpenClaw cell

```yaml
id: SIG-20260823-01
date: 2026-08-23
title: "Lomash Kumar video of volcengine/OpenViking — ByteDance context DB (viking:// + L0/L1/L2). Headline 91% token drop is OpenClaw vs its native dump (392.6M → 37.4M). Hermes only −34.3%. AGPL-3.0, first-party hermes memory setup openviking. Pattern-mine, do not adopt."
index_title: "OpenViking (★32.3k AGPL-3.0, v0.4.16) — viking:// + L0/L1/L2 context DB. 91% token drop is OpenClaw's native firehose, not Hermes (−34.3%). Steal P1: skill/memory L0 abstracts, not hermes memory setup openviking."
index_links: [repo, docs]
source_url: "https://x.com/LomashKumar52/status/2091396806068609513"
source_url_2: "https://blog.openviking.ai/post/openviking-benchmark-results/"
canonical_repo: "https://github.com/volcengine/OpenViking"
canonical_docs: "https://docs.openviking.ai/en/getting-started/01-introduction"
bucket: harness
posture: steal
steal_rank: P1
confidence: high          # fxtwitter verbatim; GH API + README + Hermes integration md + LoCoMo hermes README + benchmark blog + live `hermes memory status`. No install, no video transcription.
hardware_fit: [vps, spark]  # Ollama path exists; we will not run it
stacks_touched: [t1000]
related_plans:
  - "SIG-20260809-03"     # OpenKB compile-wiki — sibling pattern (raw→compiled), not this
  - "SIG-20260807-04"     # OMH capability projection
  - "t_6c3fd131"          # worker prompt floor; fold L0/L1 skill abstracts here
  - "memory-hygiene"      # we already own hot L0 vs cold L2; missing L1
status: open
status_note: "**OPEN — steal P1, no new card.** Hardware pre-filter N/A (not a PCIe-offload win). 91% is the OpenClaw LoCoMo cell. Do not `hermes memory setup openviking` (AGPL-3.0 + one-provider lock + VolcEngine SaaS). Fold L0/L1 skill abstracts onto `t_6c3fd131` when Ryan kicks that card; comment written 2026-08-23."
distill: none
```

## 1. Claim

[@LomashKumar52](https://x.com/LomashKumar52/status/2091396806068609513) (Lomash Kumar; 205 followers; YouTube [@PandaMakingMoney](https://www.youtube.com/@PandaMakingMoney); **109 likes / 12 RTs / 144 bookmarks / 5.2k views** at read; 2026-08-23 05:27 UTC; note-tweet + **34.6 min** 4K video). Fetched verbatim via `api.fxtwitter.com`:

> An open source tool from @ByteDanceOSS is claiming a 91% drop in AI agent token usage. Here's the full OpenViking breakdown.
>
> @openvikingai is a self-evolving context database built to unify agent memory, knowledge RAG, and skills under one system… filesystem paradigm… viking:// … tiered L0/L1/L2 … directory recursive retrieval … self-iteration … AGPL v3 licensing implications… tools like @openclaw, @NousResearch Hermes, and @claudeai.

He is a **megaphone**, not an author. Artifact is Volcengine / ByteDance `volcengine/OpenViking`. Paper: **VikingMem**, arXiv **2605.29640**, accepted VLDB 2026.

## 2. What we verified

| Check | Result |
|---|---|
| Post body | **verbatim** via fxtwitter + vxtwitter; video 2076.9 s, 3836×2160. Not transcribed — tweet + first-party docs are enough |
| Repo | `volcengine/OpenViking` — **★32,262 / 2,463 forks / 494 open issues**, **AGPL-3.0**, created **2026-01-05**, pushed **2026-08-22T09:44Z**, homepage `openviking.ai`, Python + Rust CLI. Latest tag **v0.4.16** (2026-08-21). 2,068 commits. Not a same-day drop |
| License | Main project **AGPL-3.0** (changed Mar 30 2026, PR #1085). `crates/ov_cli` + `examples` Apache-2.0. Commercial SaaS on **Volcano Engine**; self-managed edition is a license key |
| Docs | Filesystem `viking://{resources,user,agent}` · three types Resource / Memory / Skill · L0 abstract 256 chars · L1 overview 4,000 chars · L2 full · directory-recursive retrieval with a visible trajectory · session commit → async memory extract |
| Hermes hook | First-party: `hermes memory setup openviking` over HTTP (default `127.0.0.1:1933`). Docs: *do not* install OpenViking into the Hermes venv. Listed as a partner project next to deer-flow / NoKV |
| Live desk | `hermes memory status` **2026-08-23**: Provider **(none — built-in only)**. Plugin **installed but inactive**. USER.md **1,361 B** / MEMORY.md **2,204 B** (caps ~1,375 / 2,200) |
| Hardware pre-filter | **N/A / pass.** Win is prompt-token reduction via tiered load, not removing a PCIe host↔device transfer. No tok/s claim, no batch-size trap |
| Local install / re-bench | **Not run.** Numbers below = **claimed** (their LoCoMo / tau2 / HotpotQA blog, May 29 2026). Eval VLM = **Doubao 2.0 Pro**, embed = **Doubao-embedding-vision-251215** — ByteDance's own models |
| Duplicate URL | No prior OpenViking / VikingMem / viking:// entry in this tree |

**The 91% cell, named.** Their own [benchmark blog](https://blog.openviking.ai/post/openviking-benchmark-results/) (not the tweet):

| Integration | Accuracy | Query time | Input tokens | Token Δ |
|---|---|---|---|---|
| OpenClaw native | 24.20% | 95.14 s | **392,559,404** | — |
| OpenClaw + OV | 82.08% | 38.8 s | 37,423,456 | **−91.0%** |
| Hermes native | 33.38% | 82.4 s | 79,228,398 | — |
| Hermes + OV | 82.86% | 27.9 s | 52,026,755 | **−34.3%** |
| Claude Code auto | 57.21% | 49.1 s | 353,306,422 | — |
| Claude Code + OV | 80.32% | 20.4 s | 129,968,899 | −63.2% |

README range "34.3–91.0%" is these three cells. The tweet headlines the **best** one. Hermes — the runtime we actually run — is the *worst* savings cell, because native Hermes memory is already the 2-file always-on budget, not an OpenClaw-style firehose.

Second 91% in the same post: HotpotQA **accuracy** 91.00% at top-20 (12,533 tok / 0.23 s). Different metric. Do not conflate.

tau2-bench (same LLM, memory on vs off): Retail **+6.87 pp**, Airline **+11.87 pp**. Ceiling arm exists (no-memory LLM). Traffic is retail/airline tool tasks, not desk/kanban.

## 3. Takeaways (max 5)

- **Lomash ≠ the artifact.** 32k★ Volcengine repo public since January, first-party Hermes provider already in-tree. Cite the repo/blog, not the YouTube frame.
- **91% is OpenClaw native being terrible (392 M tokens).** Hermes only −34.3%. Quoting 91% as a fleet saving is the SparDA best-cell move.
- **We already own a crude L0/L2 split.** `memory-hygiene`: USER/MEMORY = always-on L0 (char-capped); skills / desk / `session_search` = L2 on demand. What we do **not** have is L1 — a 256-char abstract / 4k overview of a skill or desk file, so a turn can judge relevance before loading the body. `skill_view` today dumps the whole SKILL.md.
- **AGPL-3.0 + one-provider lock + VolcEngine SaaS = do not adopt.** Hermes allows exactly one external memory provider. Turning this on evicts any future Honcho/k2_ledger path and copylefts a network service. K2 already rejected vendor memory on those grounds.
- **OpenKB (SIG-20260809-03) is the compile sibling, not this.** OpenKB = raw docs → wiki. OpenViking = runtime context DB with tiered *load*. Do not merge the cards.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **L0/L1 sidecars on write, load depth on demand** — 256-char abstract + 4k overview per skill/dir, full body only when the turn needs it | When `t_6c3fd131` (capability projection) is kicked: project **skill abstracts**, not full `SKILL.md`. Measure: tokens saved vs cards that fail because the body was projected away. Dispatch-once (cache sacred) — not per-turn | **P1** | fold — comment on `t_6c3fd131` |
| S2 | Retrieval trajectory you can watch (which directory produced the hit) | Citation-only. `session_search` already returns bookends + match window. Do not build a viking:// browser | P2 | log only |
| S3 | Session commit → async extract into typed memories (profile / preferences / entities / events / identity / soul / cases) | We already have this as the `memory` tool + EOD ritual. Their list is a taxonomy, not a missing loop | P2 | log only |

**Primary steal (one only): S1.** It is true whether or not OpenViking is ever installed, and it is the missing middle layer of a split we already run.

## 5. Do not

- **Do not `hermes memory setup openviking`.** One command, first-party, and it would become the only external memory provider on this desk. AGPL-3.0 network copyleft + VolcEngine SaaS upsell.
- **Do not `pip install openviking` into the T1000 / Hermes venv.** Their own Hermes doc forbids combining the envs (`pip check` before you even think about it). Throwaway venv or nothing — and "nothing" is the default.
- **Do not quote 91% as our number.** Hermes cell is −34.3%, on LoCoMo, judged by Doubao, not re-run here.
- **Do not stand up VikingBot / Studio / Helper.** Separate agent framework + desktop console + Feishu/WeChat/Telegram bot. Second control plane.
- **Do not treat this as a reason to grow USER/MEMORY.** The always-on files are already at cap. The lever is *not injecting skill bodies*.

## 6. Next action (mechanical)

- [x] `INDEX.md` regenerated via `signal_log_index.py --write`
- [x] `STEALS.md` rollup row
- [x] kanban comment `t_6c3fd131` (mesh, scheduled) — S1 as a named input for when Ryan kicks projection; no new card
- [ ] no new card — board already deep; this is a fold, not an experiment

## 7. Chat blurb

`SIG-20260823-01` · `harness` · **steal P1** · [OpenViking](https://github.com/volcengine/OpenViking) ★32.3k AGPL-3.0 v0.4.16. Tweet 91% is OpenClaw vs a 392 M-token native dump; Hermes (our runtime) is **−34.3%**. Plugin is already installed here and **off**. Primary steal **S1 — L0/L1 skill abstracts into `t_6c3fd131`**, not `hermes memory setup openviking`.
