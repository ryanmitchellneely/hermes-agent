# SIG-20260827-01 — Quantized on one Spark ≠ serves on one Spark

```yaml
id: SIG-20260827-01
date: 2026-08-27
title: "ViC305/vcruz305: GLM-5.3-Flash BF16 598.5 GiB → NVFP4 177.15 GiB via ModelOpt PTQ on one GB10. 320B/18B-active. He names the distinction: quantized-on-Spark ≠ serves-on-Spark (177 vs 121 GiB). UMA is one pool (24+48 GPU/CPU still filled swap). Steal P2: don't occupy Kevin for 12h PTQ. Don't pull 177 GiB."
index_title: "vcruz305 GLM-5.3-Flash NVFP4 — PTQ on 1× Spark, pack is 177 GiB (won't serve in 121). UMA GPU+CPU is one pool. Steal P2: don't run the recipe on :8889. Same author as empty-day Flash-Next GGUFs; this pack is real (0 dl still)."
index_links: [repo]
source_url: "https://x.com/ViC305/status/2092999580346396749"
canonical_repo: "https://github.com/vcruz305/glm53-flash-nvfp4-one-spark-quantize"
canonical_docs: "https://huggingface.co/vcruz305/GLM-5.3-Flash-NVFP4"
bucket: inference
posture: steal
steal_rank: P2
confidence: high          # fxtwitter verbatim; GH API ★0 MIT-ish NOASSERTION created today; HF 0 dl, glm5_next, 177 GiB claimed. No clone, no PTQ.
hardware_fit: [spark]     # PTQ host only — pack does not serve
stacks_touched: [t1000]
related_plans:
  - "SIG-20260825-03"     # same author empty-day Flash-Next placeholders
  - "SIG-20260826-06"     # Bakeer mmap — different: that one *does* serve
status: open
status_note: "**OPEN — steal P2, no card.** Hardware pre-filter N/A (disk offload during PTQ, not a PCIe KV-offload win). He already wrote quantized≠serves. Do not 12h-PTQ on Kevin. Do not pull 177 GiB."
distill: none
```

## 1. Claim

[@ViC305](https://x.com/ViC305/status/2092999580346396749) (Cruz / HF `vcruz305`; ~854 followers; **19 likes / 5 RTs / 15 bookmarks / 1.4k views** at read; 2026-08-27 15:36 UTC). Fetched verbatim via `api.fxtwitter.com`.

PTQ of `zai-org/GLM-5.3-Flash-BF16` (~598.5 GiB, **320B total / 18B active**) → `vcruz305/GLM-5.3-Flash-NVFP4` (**177.15 GiB**, 48 shards, 190,218,104,932 bytes) on **one** GB10 via NVIDIA ModelOpt (experts-only NVFP4 W4A4, FP8 KV, layerwise calib). Borrowed Spark via Brev. Does not own one.

He writes the distinction in the tweet:

> Quantized on one Spark ≠ runs on one Spark.

## 2. What we verified

| Check | Result |
|---|---|
| Post | **verbatim** via fxtwitter |
| Recipe repo | `vcruz305/glm53-flash-nvfp4-one-spark-quantize` — **★0**, created **today**, `license: NOASSERTION` |
| Weights | HF `vcruz305/GLM-5.3-Flash-NVFP4` — **0 downloads / 3 likes**, `glm5_next`, ModelOpt, MIT tag, base `zai-org/GLM-5.3-Flash-BF16` |
| Hardware pre-filter | **N/A / pass.** NVMe offload during *quant*, not an inference PCIe-offload paper |
| Local PTQ / pull | **Not run** |
| Same author | Empty-day `vcruz305/Qwen3.8-Flash-Next-GGUF` (SIG-20260825-03). This pack is a real ModelOpt export; still **0 dl** |

UMA lesson (his words): 24 GiB GPU + 48 GiB CPU looked like two pools; **15/15 GiB swap filled**. Working dispatch: GPU **40** / CPU **24** / rest NVMe. We already know this (`Addressing Mode: ATS`, RSS ~1 GB holding 105 GiB). His failed 24+48 is the trap.

Timing (claimed, after debug): load 15–20 min · 45-layer calib 1h24 · resmooth ~1h · stream write 1–1.5h. Debug campaign ~**12 hours**.

## 3. Takeaways (max 5)

- **He named quantized ≠ serves.** 177 GiB vs 121 GiB usable. Do not “try GLM-5.3-Flash on Spark.”
- **UMA is one budget.** Adding GPU-cap + CPU-cap double-counts. Already doctrine.
- **Don't occupy Kevin for a 12h ModelOpt campaign.** `:8889` stays Flash.
- **0-star recipe, 0-dl pack, same-day.** Realer than yesterday's empty GGUF, still not a pull.
- **GLM-5.3-Flash 320B/18B is a different family** than DS4 Flash / Qwen3.8-Flash-Next. Not a replacement lane.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Quantize-on-box ≠ serve-on-box** — name the two sizes | If anyone cites “one Spark GLM-5.3,” the serve size is 177 GiB. No ticket | **P2** | log only |

**Primary steal (one only): S1.**

## 5. Do not

- **Do not pull `vcruz305/GLM-5.3-Flash-NVFP4` (177 GiB).**
- **Do not run the PTQ recipe on either Spark.**
- **Do not treat 24+48 as 72 GiB of headroom.**
- **Do not evict Flash** to “try” a model that doesn't fit.

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [ ] no STEALS.md (P2)
- [ ] no card

## 7. Chat blurb

`SIG-20260827-01` · `inference` · **steal P2** · Cruz PTQ'd GLM-5.3-Flash to NVFP4 **on** one Spark. Pack is **177 GiB** — **won't serve** in 121. UMA is one pool. Don't run it on Kevin.
