# SIG-20260815-03 — MTPLX V2.7: Qwen3.8-27B @ 73 tok/s peak on M5 Max (native MTP, 3 SKUs)

```yaml
id: SIG-20260815-03
date: 2026-08-15
title: "Youssofal_: Qwen 3.8 27B @ 73 TPS (peak) on MacBook Pro M5 Max. MTPLX V2.7 with 3 new models — Bare Speed (short burst / chat), Optimized Speed (higher quality + faster on long coding), Optimized Quality (~30% slower). Native Apple Silicon MTP runtime (no external drafter). Author video. Prior same stack: Qwen3.6-27B 4-bit MLX 28→63 t/s on M5 Max."
index_title: "MTPLX V2.7 Qwen3.8-27B 73 t/s peak on M5 Max (native MTP). Steal = if we ever serve Qwen3.8 on MBP, measure MTPLX not ollama GGUF. 73 is M5 peak not M3 Max. Three SKUs = chat vs long-code vs quality."
source_url: "https://x.com/Youssofal_/status/2088588470117933377"
canonical_repo: "https://github.com/youssofal/MTPLX"
canonical_docs: ""
index_links: [repo]
bucket: inference
posture: steal
steal_rank: P1
confidence: medium
hardware_fit: [mbp]
stacks_touched: [t1000]
related_plans:
  - "SIG-20260815-01"
  - "SIG-20260814-04"
  - "SIG-20260811-01"
  - "local-inference-fleet"
status: open
status_note: "**OPEN — author peak + video; HF ids for the three 3.8 SKUs not fetched this turn.** Hardware pre-filter N/A (Apple native, not PCIe-offload). Ryan box is M3 Max — do not cite 73 as ours. No install."
distill: none
```

## 1. Claim

[@Youssofal_](https://x.com/Youssofal_/status/2088588470117933377) (134 likes / 56 bookmarks / ~6.3k views):

> Qwen 3.8 27B @ **73 TPS (peak)** on a MacBook Pro **M5 Max**.
> **MTPLX V2.7** out now with 3 new models.
> - **Bare Speed** — short burst decode, good for chat
> - **Optimized Speed** — higher quality and faster on long coding
> - **Optimized Quality** — 30% slower but super

## 2. What we verified

| Check | Result |
|---|---|
| Tweet + video | Fetched fxtwitter; amplify video present (not transcribed) |
| Runtime | [youssofal/MTPLX](https://github.com/youssofal/MTPLX) — MLX-native **MTP speculative decode, no external drafter** (prior README crawl) |
| Prior same author | Qwen **3.6** 27B 4-bit MLX **28 → 63 t/s** on M5 Max (temp 0.6) — consistent stack |
| Hardware pre-filter | **N/A** |
| Batch | **Peak / burst** — ceiling, not sustained agent wall |
| This desk | Ryan **M3 Max**, not M5 |

Did **not** re-pull README or HF ids this turn (fetch approval timed out). Three 3.8 SKU repo names unconfirmed.

## 3. Takeaways (max 5)

- Qwen3.8-27B is getting **three engines in one day**: Spark SGLang W4A4 (SIG-15-01), Tech2Wild tool-call #1 (SIG-14-04), now **MLX MTP on Mac**.
- Native MTP (model drafts itself) is the Apple analogue of vLLM/SGLang MTP.
- **SKU split is stealable:** burst-chat vs long-code vs quality — same grammar as Flash vs 120b vs Grok.
- **73 t/s is M5 peak.** Do not score MBP ollama against it.
- Not a Spark default and not a reason to unload q38/MBP doctrine.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **If Qwen3.8 ever runs on MBP, MTPLX is the measure arm** — native MTP, not ollama GGUF; report SKU + peak vs sustained | Watch only until an M3 Max number exists. Do not install the Mac app. | **P1** | watch |
| S2 | Three SKUs (burst / long-code / quality) as explicit serve presets | Name the job, not one “local Qwen” | P2 | doctrine |

**Primary steal:** S1

## 5. Do not

- Quote 73 tok/s as an M3 Max or Spark figure.
- Install MTPLX.app onto the desk.
- Treat “peak” as agent-loop wall-clock.

## 6. Next action

- [x] entry
- [ ] INDEX + STEALS regen (may need a follow-up if write tools stall)
- [ ] none — **no card**

## 7. Chat blurb

**SIG-20260815-03** · inference · steal **P1** · medium
MTPLX V2.7: Qwen3.8-27B **73 t/s peak on M5 Max** (native MTP; 3 SKUs).
**Steal:** MBP measure arm if we ever serve 3.8 locally — not our M3 number. No install.
