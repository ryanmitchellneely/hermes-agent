# SIG-20260816-02 — 0xBakeer: Qwen3.8-27B on 1×Spark — spec-dec ≫ quant; prefix cache silent-off; W4A4 void on SM121

```yaml
id: SIG-20260816-02
date: 2026-08-16
title: "0xBakeer weekend writeup + two MIT recipes: Qwen3.8-27B on one DGX Spark (vLLM 0.27.1-aarch64). Stock FP8 7.88 tok/s → DSpark k=14 edit-heavy 58.5 (FP8) / 75 (Unsloth NVFP4). Spec-dec is most of the 9.5×; 4-bit +27% at c1 and +0.2% at c16. vLLM prefix cache default-off because is_hybrid=True (14–22× prefill). DSpark drafts 3.3× cheaper than MTP. k=14 wins latency, loses 43% aggregate at c8 on FP8. Author LIMITATIONS: baseline was shared-GPU 0.44 GMU; edit-heavy synthetic; speed-only."
index_title: "Bakeer Qwen3.8-27B 1×Spark: spec-dec 6× on FP8; 4-bit dies at c16; --enable-prefix-caching required (hybrid default-off). 75 ≠ M5 73. No pull."
source_url: "https://x.com/0xBakeer/status/2089092964404601310"
source_url_2: "https://x.com/0xBakeer/status/2089090318905774558"
canonical_repo: "https://github.com/0xBakeer/Qwen3.8-27B-FP8-on-a-single-DGX-Spark"
canonical_docs: "https://github.com/0xBakeer/Qwen3.8-27B-4-bit-on-a-single-DGX-Spark"
index_links: [repo, docs]
bucket: inference
posture: steal
steal_rank: P1
confidence: high
hardware_fit: [spark]
stacks_touched: [t1000]
related_plans:
  - "B17"
  - "SIG-20260815-01"
  - "SIG-20260815-02"
  - "SIG-20260815-03"
  - "SIG-20260815-04"
  - "t_6e058ca2"
  - "ST-14 t_13d79be5"
status: open
status_note: "**OPEN — recipe + method, no install.** Tweet + both MIT repos (★2 / ★4, created today) + RESULTS/LIMITATIONS/NOTES/serve.sh fetched. Drafter `Doopeworld/Qwen3.8-27B-DSpark-vLLM` is HF-only, 2 likes / 0 dl, same day. Hardware pre-filter N/A (GB10 native). Do not docker-pull. Do not quote 75 as M5 73."
distill: none
```

## 1. Claim

[@0xBakeer](https://x.com/0xBakeer/status/2089092964404601310) (164 fol; 78 likes / 9 RT / 117 bookmarks / 12k views; note tweet + X article):

Qwen3.8-27B, one DGX Spark: **7.88 → 75 tok/s solo, 256 aggregate.** Quantize-for-speed was the smallest part. Spec-dec on unchanged FP8 → 58.5. DSpark cheaper than MTP. Acceptance rate is a trap. Prefix cache was silently off (`is_hybrid=True`). 4-bit = +27% at 1 req, **+0.2% at 16**.

Recipes: [FP8](https://github.com/0xBakeer/Qwen3.8-27B-FP8-on-a-single-DGX-Spark) · [4-bit](https://github.com/0xBakeer/Qwen3.8-27B-4-bit-on-a-single-DGX-Spark)

## 2. What we verified

| Check | Result |
|---|---|
| Tweet | fxtwitter 200; note + self-quote of X article `2089076470865854466` |
| Repos | Both MIT, created **2026-08-16**, ★**2** / ★**4**. README + RESULTS + LIMITATIONS + NOTES + `serve.sh` fetched |
| Engine | Official `vllm/vllm-openai:v0.27.1-aarch64`. Target `Qwen/Qwen3.8-27B-FP8` 28.5 GiB **dense hybrid** (48 GatedDeltaNet + 16 full-attn) |
| Drafter | `Doopeworld/Qwen3.8-27B-DSpark-vLLM` — **HF exists**, likes **2**, dl **0**, created today, **no GitHub repo**, license None. (RadixArk DSpark pack is the downloaded one — 26k dl — Bakeer did not use it) |
| Spec-dec (author, dedicated GPU, think off, temp 0) | Stock shared-GPU **7.88**. DSpark `k=7` edit **46.8** / fresh **20.05**. DSpark `k=14` edit **58.5** (accept **67.6%**, mean **10.46** tok/pass). MTP `k=15` edit 39.0 / fresh **13.39** (worse than `k=3`) |
| Prefix cache | vLLM `default_prefix_caching = supported and not is_hybrid`. Qwen3.8 `is_hybrid=True` → **off unless `--enable-prefix-caching`**. Prefill warm/cold: 19K **14.2×**, 53K **22.0×**. Nothing in startup log |
| Quant vs batch (k=7) | c1 +27% · c4 +20% · c8 +10% · **c16 +0.2%** (256.08 vs 256.47). 4-bit prefill **−7–9%** at 32–100K (Marlin dequant) |
| SM121 4-bit claims (author) | **No native FP4.** Prefer **W4A16** not W4A4. CUTLASS FP4 “silent garbage.” `VLLM_MARLIN_USE_ATOMIC_ADD=1` required or race looks like “bad quant” |
| Hardware pre-filter | **N/A** — GB10 native, not PCIe offload. Batch ladder **c1–c16 present** (readable) |
| Author LIMITATIONS (load-bearing) | 7.88 baseline = **shared GPU, GMU 0.44**; 58.5/75 = **sole occupant, 0.85**. Edit-heavy is synthetic 45 dataclasses (optimistic accept). Cost-per-draft **derived**, not instrumented. Speed only — no quality eval |
| vs our numbers | **75 Spark NVFP4+DSpark k=14 edit ≠ 73 M5 MTPLX** (SIG-15-03). MiaAI SGLang W4A4+MTP ~33–35 N=1 (SIG-15-01) is a different engine |

## 3. Takeaways (max 5)

- **Most of the 9.5× is output-preserving decode strategy on FP8** (author: 6.0× at DSpark k=7). Quant is the last 1.6× and the only step that changes what the model knows.
- **`--enable-prefix-caching` is not the default** on this hybrid. Our ~35.7k worker prompt is exactly the 19–53K shared-prefix regime (14–22× TTFT).
- **Acceptance % is a trap.** `k=14` dropped accept 98.6→67.6 and got faster. Predictor = **mean tokens / forward pass** (already on `t_6e058ca2`).
- **k=14 vs k=7 is latency vs fleet** — 58.5 vs 208.7 agg at c8. Complements SIG-15-02 adaptive verify. A `k` tuned on one quant **does not transfer**.
- **W4A4-on-Spark (15-01) is now contested.** Author: SM121 has no FP4 tensor path; W4A4 pays accuracy for no compute. Not re-measured by us.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Hybrid prefix cache is opt-in** — vLLM turns it off when `is_hybrid=True`; startup is silent | Next Qwen3.8 / hybrid vLLM serve on Spark: pass `--enable-prefix-caching` and log whether it was already on. Fold into ST-14 / any 15-01/15-04 arm. No new card | **P1** | open |
| S2 | Quant-vs-N ladder + W4A16-not-W4A4 on SM121 | Any 4-bit Spark row must show **c1 and c8/c16**. Do not promote W4A4 as a GB10 compute win until we measure it | P1 | fold |
| S3 | Mean tok/pass > accept% | Already required on `t_6e058ca2` — Bakeer is the field example | P2 | fold |

**Primary steal:** S1

## 5. Do not

- Docker-pull `vllm/vllm-openai:v0.27.1-aarch64` or Bakeer’s `serve.sh` onto ryan-spark tonight (2–4★ same-day; v0.27.x still carries SM121 baggage).
- Pull `Doopeworld/…-DSpark-vLLM` (0 downloads) as the default drafter — RadixArk is the downloaded pack if we ever spike.
- Quote **75 tok/s** as “we can hit M5 numbers on Spark” or as a ceiling. Edit-heavy synthetic + config change vs 7.88.
- Dual-load 27B beside 120b / Nemotron on 121G.
- Treat W4A4 (15-01) as settled compute on SM121.
- Enable `--enforce-eager` (author: ~55% hit on SM121).

## 6. Next action

- [x] entry + INDEX + STEALS
- [x] pointer on SIG-15-01
- [ ] fold S1 into the next Spark vLLM/Qwen3.8 serve note — **no card**

## 7. Chat blurb

**SIG-20260816-02** · inference · steal **P1** · high
Bakeer: Qwen3.8-27B on 1×Spark. Spec-dec is the 6×; 4-bit dies at c16; **`--enable-prefix-caching` is off by default** on this hybrid.
**75 ≠ M5 73.** Do not pull.
