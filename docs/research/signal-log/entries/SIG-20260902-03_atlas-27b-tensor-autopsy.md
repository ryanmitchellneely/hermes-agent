# SIG-20260902-03 — Atlas: measured 27B tensor autopsy. Don't install.

```yaml
id: SIG-20260902-03
date: 2026-09-02
title: "u1tra_instinct wow-bro remix of superalesha Atlas: Qwen3.8-27B Living Model — 1199 tensors, 64-layer signal flow, INT4 layer-swap damage from real weights/runs. Repo alesha-pro/atlas ★51 MIT. Watch P2. Citation if we ever requant leftover 27B. Don't pip/scan Spark. Don't quote 1.1M neurons as a bench."
index_title: "Atlas (alesha-pro, ★51 MIT) — measured INT4/INT8/FP8 error per 27B tensor. Watch P2. Don't install. Don't requant :11435 off this viz."
index_links: [repo]
source_url: "https://x.com/u1tra_instinct/status/2095219224553615556"
source_url_2: "https://x.com/superalesha/status/2094708329092137324"
canonical_repo: "https://github.com/alesha-pro/atlas"
canonical_docs: "https://atlas.alesha.pro"
bucket: models
posture: watch
steal_rank: P2
confidence: high          # fxtwitter quote + GH README. No clone, no GPU scan.
hardware_fit: [none]
stacks_touched: [t1000]
related_plans:
  - "SIG-20260825-02"     # leftover 27B Spark lane
  - "SIG-20260902-01"     # same day's 200-agg AEON slogan — different artifact
status: open
status_note: "**OPEN — watch P2, no card.** Hardware pre-filter N/A. Viz of 27B tensors. Don't run weight_atlas.py on Spark. Leftover stays Ollama Q4_K_M :11435."
distill: none
```

## 1. Claim

[@u1tra_instinct](https://x.com/u1tra_instinct/status/2095219224553615556) (keys; **5 likes / 711 views** at read; 2026-09-02 18:36 UTC):

> wow bro.. this is freaking cool.... it's a big deal full repo in the thread

Quotes [@superalesha](https://x.com/superalesha/status/2094708329092137324) (Alexey Fateev; 4×3090 + 2×Spark bench account):

> Atlas covers Qwen3.8 27B completely: 1,199 tensors… Living Model… English/code/agent traces… 64 layers… damage from swapping each layer to INT4… actual weights or real runs. No placeholder data.

keys is a **megaphone**. Artifact is **alesha-pro/atlas**.

## 2. What we verified

| Check | Result |
|---|---|
| Repo | `alesha-pro/atlas` **★51 MIT**, created 2026-08-30. Static site `atlas.alesha.pro`. 0 runtime deps for the UI |
| Method | Scan shards → SQNR dB for INT8/INT4-g128/FP8 e4m3 per tensor. 116 s / 27B on one GPU. Also GLM-5.3-Flash NVFP4 autopsy |
| Hardware pre-filter | **N/A** (viz, not a PCIe-offload win) |
| Duplicate URL | None. Not SIG-09-02-01 (that was 8-wide tok/s) |

## 3. Takeaways (max 5)

- **Useful as a map, not a runtime.** “Which 27B layers die at INT4” is the only sentence if we ever leave Ollama Q4_K_M.
- **Don’t treat 1.1M neurons / 1199 tensors as a Spark number.**
- **Don’t scan Spark overnight.** Leftover `:11435` stays.
- **Don’t clone into T1000.** ★51 static site.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Quant damage is per-layer, measured SQNR — not a global INT4 slogan** | Citation only. Don’t requant `:11435` off the gallery | **P2** | log only |

**Primary steal (one only): S1.** Nothing to install.

## 5. Do not

- **Do not `pip install torch` / `python3 scripts/weight_atlas.py` on Spark.**
- **Do not quote 1.1M neurons.**
- **Do not evict `:8889` or swap leftover 27B.**
- **Do not open a card.**

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [ ] no STEALS.md (P2)
- [ ] no card

## 7. Chat blurb

`SIG-20260902-03` · `models` · **watch P2** · Atlas = measured 27B tensor autopsy (INT4 layer damage). Don’t install. Don’t requant `:11435`.
