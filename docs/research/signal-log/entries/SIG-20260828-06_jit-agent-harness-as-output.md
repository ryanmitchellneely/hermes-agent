# SIG-20260828-06 — JIT-Agent: harness-as-model-output. Don't replace Hermes.

```yaml
id: SIG-20260828-06
date: 2026-08-28
title: "elvis (omarsar0) JIT-Agent — a model whose output is an agent harness (4-module protocol: memory/planning/action/tools). DS-V4-Flash > GPT-5.6 DeepSearchQA +9.1 / Odyssey +4.3; GLM-5.2 +20.2. Competitive with OpenCode / Claude Code. Watch P2. Generating a new harness is anti-SoT. Don't quote Flash>GPT-5.6 as Spark."
index_title: "JIT-Agent (arXiv 2608.25593) — harness-as-output. Flash>+9.1 vs GPT-5.6 is API DeepSearchQA, not C1. Watch P2. Don't replace Hermes. No install."
index_links: [docs]
source_url: "https://x.com/omarsar0/status/2093056965568332236"
canonical_repo: "https://github.com/bingreeky/JIT"
canonical_docs: "https://arxiv.org/abs/2608.25593"
bucket: harness
posture: watch
steal_rank: P2
confidence: high          # fxtwitter verbatim + arXiv abs 26 Aug 2026. GH ★39, no clone.
hardware_fit: [none]
stacks_touched: [t1000]
related_plans:
  - "agent-harness-compare"
  - "SIG-20260826-04"     # Recuris = evolve skills, freeze weights
  - "SIG-20260826-05"     # same megaphone, different paper (handoff tax)
status: open
status_note: "**OPEN — watch P2, no card.** Hardware pre-filter N/A. elvis is megaphone; artifact is Zhang et al. ★39 unofficial-looking repo. Generating a harness on the fly is anti-T1000 SoT. Do not quote +9.1 as Flash C1."
distill: none
```

## 1. Claim

[@omarsar0](https://x.com/omarsar0/status/2093056965568332236) (elvis / DAIR.AI; **~315k followers**; **290 likes / 37 RTs / 457 bookmarks / 17k views** at read; 2026-08-27 19:24 UTC). Fetched verbatim via `api.fxtwitter.com`:

> JIT-Agent is a model whose output is an agent harness… DeepSeek-V4-Flash surpasses GPT-5.6 on DeepSearchQA (+9.1) and OdysseyBench (+4.3). GLM-5.2 gains up to +20.2… competitive with OpenCode and Claude Code.

He is a **megaphone**. Same account as AWS Handoff Tax (SIG-26-05).

## 2. What we verified

| Check | Result |
|---|---|
| arXiv | **2608.25593** v1 26 Aug 2026. Zhang / Lu / Xie / … / Yan. *Scaling Harness Intelligence via Just-in-Time Harness Evolution* |
| Protocol | Four modules: memory · planning · action protocol · tool/skill orchestration. Synthesize, **repair mid-execution**, self-evolve from an archive of prior configs |
| Repo | `bingreeky/JIT` **★39**, created 17 Aug, license Other/NOASSERTION. **Not cloned** |
| Hardware pre-filter | **N/A** |
| Duplicate URL | None |

Numbers are **API Flash vs GPT-5.6** on DeepSearchQA / OdysseyBench. No batch, no GB10, no C1. Ceiling arm is named (OpenCode / Claude Code) — still not our runtime.

## 3. Takeaways (max 5)

- **Harness can dominate the model.** True and old. That is why T1000 stays SoT (`agent-harness-compare`).
- **Synthesizing a new harness per task is the opposite of this desk.** Skills + USER/MEMORY + never-send are the harness. Don't JIT-replace them.
- **+9.1 is not Kevin `:8889`.** API Flash, search/QA benches.
- **Repair-from-archive** is Recuris/Warp's cousin, not a reason to install ★39.
- **elvis bookmark bait.** Cite the arXiv if cited at all.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | Harness is a versioned artifact; don't let the worker rewrite it mid-turn | Already skills + Recuris no-self-vote. Citation only | **P2** | log only |

**Primary steal (one only): S1.** Nothing to install.

## 5. Do not

- **Do not quote Flash > GPT-5.6.**
- **Do not `git clone` bingreeky/JIT into `~/.t1000`.**
- **Do not open a card.**

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [ ] no STEALS.md (P2)
- [ ] no card

## 7. Chat blurb

`SIG-20260828-06` · `harness` · **watch P2** · JIT-Agent writes a harness on the fly. We *are* the harness. +9.1 is API Flash vs GPT-5.6, not C1. Don't install.
