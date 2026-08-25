# SIG-20260815-01 — MiaAI: Qwen3.8-27B on DGX Spark via SGLang cookbook (NVFP4 W4A4 + MTP) — ~33–35 t/s N=1, ~195–210 t/s N=10

```yaml
id: SIG-20260815-01
date: 2026-08-15
title: "MiaAI_lab: run Qwen3.8-27B on DGX Spark with SGLang (up to 1M ctx, MTP). Claimed ~33–35 tok/s single stream (structural), ~195–210 tok/s at 10 concurrent. Same speed at 256k vs 1M; default 256k to hold 10 concurrent with full KV. Repo MiaAI-Lab/Qwen3.8-27B-SGLang-DGX-Spark (MIT, ★3, day-of). Wraps official SGLang cookbook cell + image lmsysorg/sglang:qwen38-27b. Weights RadixArk/Qwen3.8-27B-NVFP4 (~22 GB). Sister Unsloth/vLLM pack was ~20 t/s N=1 / ~70 at 4. Quotes own prior tweet."
index_title: "MiaAI Qwen3.8 Spark: DSpark 51.5 code / 21–23 chat; MTP wins essays 24.1. 45 tease was short-prompt decode. Chat < our Ollama 31.7. No pull."
source_url: "https://x.com/MiaAI_lab/status/2088579343156924888"
source_url_2: "https://x.com/MiaAI_lab/status/2089806765290565991"
canonical_repo: "https://github.com/MiaAI-Lab/Qwen3.8-27B-SGLang-DGX-Spark"
canonical_docs: "https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3.8-27B"
index_links: [repo, docs]
bucket: inference
posture: steal
steal_rank: P1
confidence: high
hardware_fit: [spark]
stacks_touched: [t1000]
related_plans:
  - "B17"
  - "ST-14 t_13d79be5"
  - "SIG-20260812-02"
  - "SIG-20260813-02"
  - "SIG-20260814-04"
  - "SIG-20260813-01"
status: open
updated: 2026-08-18
status_note: "**UPDATED 2026-08-18 evening — DSpark vs MTP table.** Code LRUCache: DSpark **51.5** / MTP **34.5**. Chat stream ~**21–23** (DSpark slightly faster with thinking on). Essay: MTP **24.1** beats DSpark **18.3**. Repo ★131, `start-dspark.sh` + `RadixArk/Qwen3.8-27B-DSpark` ~2.7 GB. Morning 44.8 tease = short-prompt decode, not chat. **Chat < our Ollama 31.7.** No docker pull."
distill: none
```

## 0. 2026-08-18 follow-up — “Who wants 45 tok/s”

[@MiaAI_lab](https://x.com/MiaAI_lab/status/2089626446486540719) (268 likes / 9 RT / 76 bookmarks / 10k views). **No new SIG.**

Screenshot (decode bench UI):

| Field | Value |
|---|---|
| Model | `RadixArk/Qwen3.8-27B-NVFP4` · port **8888** |
| Job | **2048 tok · 1 conc · 45.8 s** · COMPLETED |
| TTFT | **121 ms** · 1/1 streams |
| Aggregate = stream | **44.8 tok/s** |

Honest N=1. TTFT 121ms ⇒ short prompt. Not a 64k chat row. 2048/45.8 ≈ 44.7.

Vs us: Spark Ollama Q4_K_M **31.7 wall / 42.8 engine**. Vs r0b0tlab matched c1 **25.62**. Do not treat 44.8 as the fleet number.

## 0.1 Evening — DSpark 51.5 code / 21–23 chat (this URL)

[@MiaAI_lab](https://x.com/MiaAI_lab/status/2089806765290565991) (149 likes / 14 RT / 108 bookmarks / 8.4k views). Same repo, now ★**131**. **No new SIG.**

Tweet: optimized DSpark ~**51.5** pure coding vs ~**34.5** MTP. Chat ~**21–23**. MTP still wins long essays.

README + screenshot (stream, post-first-token; same prompts):

| Probe | DSpark (`start-dspark.sh`, block-7) | MTP (`start.sh`, EAGLE 3/1/4) |
|---|---:|---:|
| LRUCache code (ndec n=5) | **51.5** (51.4–51.7, always 518 tok) | **34.5** (always 508) |
| Long essay | 18.3 | **24.1** |
| Chat T=0 think-off | 22.0 | **24.6** |
| Chat T=1 think-off | 21.3 | **23.4** |
| Chat T=1 think-on (UI default) | **23.2** | 21.0 |
| Essay 400 tok | 18.0 | **23.9** |
| LRUCache 400 tok | **47.1** | 33.6 |

DSpark default here. Extra pull: `RadixArk/Qwen3.8-27B-DSpark` ~2.7 GB. No YaRN / >262k on DSpark.

**Chat 21–23 is below our live Spark Ollama 31.7.** 51.5 is an LRUCache code probe (same family as Bakeer edit), not desk chat.

## 1. Claim

[@MiaAI_lab](https://x.com/MiaAI_lab/status/2088579343156924888) (66 likes / 68 bookmarks / ~5k views):

SGLang on Spark for **Qwen3.8-27B**: up to **1M context**, MTP. **~33–35 tok/s** single stream (structural); **~195–210 tok/s** at **10** concurrent. **No speed delta 256k vs 1M.** Default **256k** so 10 concurrent keep full KV.

Sister pack (quoted): Unsloth NVFP4 / vLLM path ~**20 t/s N=1**, ~**70 at 4**.

Repo: https://github.com/MiaAI-Lab/Qwen3.8-27B-SGLang-DGX-Spark

## 2. What we verified

| Check | Result |
|---|---|
| Repo | MIT, Shell, created **2026-08-15**, ★3 — thin wrapper, not a model |
| Recipe | Official **SGLang cookbook** Qwen3.8-27B DGX Spark cell; image **`lmsysorg/sglang:qwen38-27b`** |
| Weights | **`RadixArk/Qwen3.8-27B-NVFP4`** (~22 GB pull); `QUANT=nvfp4\|fp8\|bf16` |
| Engine knobs | **NVFP4 W4A4**, FP8 KV (`fp8_e4m3`), MTP (EAGLE 3 / topk 1 / 4 draft), GDN pool from concurrency, thinking + `qwen3_coder` tools |
| Default serve | 262K native, YaRN off, **10 concurrent**, port 8888 |
| 1M path | `YARN=1` + `CONTEXT_LENGTH=1000000`; ~33 GB / 1M seq; ~2 full 1M in flight regardless of N=10 |
| Hardware pre-filter | **N/A** — Spark GB10 native. Not a CPU-offload paper. |
| Batch | **N=1 and N=10 both reported** — readable (unlike SparDA-class) |

**Claimed tok/s, not fleet-measured.** Sister 20 t/s is the same author’s earlier Unsloth/vLLM row.

## 3. Takeaways (max 5)

- **Qwen3.8-27B is no longer a placeholder-only name** (SIG-12-02) — cookbook image + RadixArk NVFP4 + two Mia packs same week as Tech2Wild #1 tool-call board (SIG-14-04).
- **Engine+quant+N** again: SGLang+MTP ~33–35 N=1 vs their vLLM Unsloth ~20; W4A4 (SIG-13-02) is the recipe to demand, not “NVFP4” as one word.
- Concurrency is the real Spark story (~200 t/s @ 10) — matches SIG-13-01 GB10 ladder thinking; our kanban is still mostly **N=1**.
- 256k vs 1M same decode is plausible if prefill/KV is the bound they sized; 1M is a **capacity** knob, not a speed win. Default 256k+10 is the honest product setting.
- Do not yank DS4 Flash / 120b because a 27B dense pack is faster on a blog bench.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Pin the cookbook recipe** as the Qwen3.8 Spark serve arm: SGLang image + NVFP4 **W4A4** + MTP + report N=1 **and** N=k | Comment onto ST-14 (`t_13d79be5`); when that spike runs, start from this wrapper/cookbook — do not invent flags. Measure N=1 first (our regime). | **P1** | open |
| S2 | Keep W4A4 vs W4A16 + backend on every Qwen3.8 row | Already SIG-13-02 | P1 | fold |

**Primary steal:** S1

## 5. Do not

- `docker run` / pull ~22 GB onto ryan-spark without a named ST-14 kickoff + lane lease.
- Treat 51.5 or 44.8 as desk chat speed. Chat in their own table is **21–23**.
- Quote 51.5 without saying LRUCache code probe.
- Swap desk/kanban defaults to Qwen3.8.
- Use DSpark + YaRN 1M together (README: draft config crash).

## 6. Next action

- [x] entry + INDEX + STEALS
- [x] 2026-08-18: 44.8 N=1 screenshot noted (no new SIG)
- [x] 2026-08-18 evening: DSpark vs MTP table (51.5 / 21–23)
- [ ] comment ST-14 `t_13d79be5` — **no new card**

## 7. Chat blurb

**SIG-20260815-01** upd evening · inference · steal **P1**
DSpark **51.5** code / **21–23** chat. MTP wins essays **24.1**. Morning 45 = short-prompt decode.
**Our Ollama chat 31.7 is faster than their chat.** No pull.
