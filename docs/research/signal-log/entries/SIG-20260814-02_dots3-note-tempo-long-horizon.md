# SIG-20260814-02 — dots3-note Preview: open 280B/16B-active multimodal + TEMPO (long-horizon RL when rollouts take tens of hours)

```yaml
id: SIG-20260814-02
date: 2026-08-14
title: "Chao Qiao / dots-studio ship dots3-note Preview: open-source 280B / 16B-active multimodal model for complex reasoning + long-horizon agents. Also TEMPO — Test-time-scaled Value Estimation with Macro-step Policy Optimization — RL when a single rollout takes tens of hours, using intermediate self-critique as learning signal before task complete. Open-source VibeSearchBench + VibeLifeBench. Page: studio.dots.ai. HF preview weights: dots-studio/dots3-note-prev (+ fp8)."
index_title: "dots3-note = Xiaohongshu (RED) first-party, not a DS4 Flash FT. 280B/16B + TEMPO. Steal = mid-rollout critique. Not a Spark default."
source_url: "https://x.com/ChaoQiao42/status/2088004290556436991"
source_url_2: "https://x.com/jun_song/status/2088248817460400241"
canonical_repo: "https://github.com/studio-dots-ai/dots3-note-prev"
canonical_docs: "https://studio.dots.ai/dots/dots3-en.html"
index_links: [repo, docs]
updated: 2026-08-15
bucket: models
posture: steal
steal_rank: P1
confidence: high
hardware_fit: [cloud, none]
stacks_touched: [t1000, k2]
related_plans:
  - "long-horizon agents"
  - "B18"
  - "kanban multi-hour cards"
status: open
status_note: "**OPEN — 2026-08-15 Jun Song update.** First-party README + LICENSE: **Copyright (c) 2026 Xiaohongshu**, developed by dots studio, Apache-2.0, contact `dots-model-feedback@xiaohongshu.com`. Jun’s “fine-tuned DeepSeek Flash” is **his guess — official materials never say DeepSeek**. 280B not a Spark default. No pull."
distill: none
```

## 1. Claim

[@ChaoQiao42](https://x.com/ChaoQiao42/status/2088004290556436991) (1.0k likes / 104 RT / 440 bookmarks / ~72k views):

> WE SHIPPED IT — **dots3-note Preview**: open-source **280B / 16B-active** multimodal model for complex reasoning and long-horizon agents.  
> **TEMPO** (Test-time-scaled Value Estimation with Macro-step Policy Optimization) — how to RL-train agents when **one rollout takes tens of hours**, by turning **intermediate self-critiquing** into learning signals **before** the task completes.  
> Also open-sourcing **VibeSearchBench** & **VibeLifeBench**.

Landing: https://studio.dots.ai/dots/dots3-en.html

## 0. 2026-08-15 follow-up (no new SIG)

[@jun_song](https://x.com/jun_song/status/2088248817460400241) (40k followers; 711 likes / 41 RT / 333 bookmarks / 70.7k views; quote of @dotsstudioai): thought it was “another random startup releasing a **fine-tuned DeepSeek Flash**.” Then: **Xiaohongshu**, “Chinese Facebook with 350M users,” “data moat… insane,” every Chinese giant rolling their own LLM.

Screenshot on that tweet is the repo LICENSE/Contact footer (not a bench chart). **Duplicate-subject rule:** update this entry, do not open SIG-15-07.

## 2. What we verified

| Check | Result |
|---|---|
| Launch tweet | Fetched fxtwitter; media present (3 images) |
| Jun Song tweet | Fetched fxtwitter + vxtwitter 200; screenshot = LICENSE footer |
| Parent | **Xiaohongshu / RED / 小红书** — first-party: README License + Contact (`Copyright (c) 2026 Xiaohongshu` · `dots-model-feedback@xiaohongshu.com`). RedNote badge + SGLang cookbook path `…/RedNote/Dots3-Note.mdx`. Studio HTML is an XHS shell (`cdn.xiaohongshu.com`, og:title 小红书). |
| DeepSeek Flash FT? | **Not claimed by the vendor.** Own arch in README (DSA+SWA, own MoE ViT, own audio encoder). Jun invented the Flash-FT frame. |
| 350M users | **Jun’s figure**, not in LICENSE/README. Do not bank as measured MAU. |
| HF | `dots-studio/dots3-note-prev` Apache-2.0, likes **160**, dl **240** (2026-08-15); also `-fp8` |
| GitHub | `studio-dots-ai/dots3-note-prev` ★**58** Apache-2.0, created 2026-08-12, pushed 08-14 |
| Arch (README, claimed) | 280B total / **16B active** · 1 dense + 45 MoE · 256 routed + 1 shared, **top-8** · attn 13 DSA + 33 SWA · ctx **512K** · MTP 1 shared / 1.13B · ViT MoE 7B/1.2B act · audio 800M · in: text/image/video/audio · out: text · BF16 + FP8 |
| Serve (README) | **FP8 on one 8-GPU node** (SGLang or vLLM). BF16 needs more. Transformers #47844 + SGLang #33829 *under review* at read; vLLM recipe on `main`. |
| TEMPO | Named in launch tweet; **full report “coming soon”** — still no paper URL |
| Hardware pre-filter | N/A (not a PCIe-offload win). **8-GPU FP8 recommended ≠ one Spark.** |

## 3. Takeaways (max 5)

- Parent is **Xiaohongshu**, first-party — not a random startup and **not a DeepSeek Flash fine-tune**.
- Jun’s “data moat → insane model” is **hype**. 350M MAU (his number) does not score TEMPO or Vibe*.
- Long-horizon RL’s real blocker is **wall-clock of one trajectory** — TEMPO names that; paper still unbanked.
- **Intermediate critique as dense signal** is still the steal, independent of their 280B weights.
- 280B / 16B-active + “FP8 on one 8-GPU node” is **cloud**, not MBP/Spark default.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **TEMPO-class mid-trajectory credit** — don’t wait for terminal success on multi-hour agent runs; score intermediate self-critique / stage gates | For long kanban/worker cards: define stage checkpoints + critique rubric that can train or route *before* done; observer first (log would-have-signal) | **P1** | open |
| S2 | Open long-horizon **life/search** benches as instruments | When we next refresh eval shelf, skim Vibe* once URLs land | P2 | watch |

**Primary steal:** S1

## 5. Do not

- Pull 280B (or the FP8 8-GPU recipe) onto ryan-spark as a “try it” residency.
- Treat NVFP4 third-party HF forks as first-party.
- Call this a DeepSeek-V4-Flash fine-tune — vendor never said that.
- Confuse TEMPO with ordinary process-reward models without reading their paper (not yet banked).
- Quote 350M users as a verified MAU.

## 6. Next action

- [x] entry + INDEX + STEALS (08-14)
- [x] 08-15: Xiaohongshu parent + GitHub README banked; Jun Song as `source_url_2`
- [ ] paper + Vibe* repos when “full report” lands — no new card

## 7. Chat blurb

**SIG-20260814-02** · models · steal **P1** · high  
dots3-note = **Xiaohongshu** first-party (not a DS4 Flash FT). 280B/16B + TEMPO.  
**Steal:** mid-rollout critique for multi-hour agents. Not a Spark default. No pull.
