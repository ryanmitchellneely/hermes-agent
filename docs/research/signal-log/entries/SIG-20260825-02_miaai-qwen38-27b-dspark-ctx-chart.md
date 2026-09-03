# SIG-20260825-02 — MiaAI Qwen3.8-27B Spark: 67.5→58.8 chart is not a C1 row

```yaml
id: SIG-20260825-02
date: 2026-08-25
title: "MiaAI decode-vs-ctx chart for Qwen3.8-27B DSpark on GB10 — 67.5 @ 4k → 58.8 @ 256k. New BF16 lm_head NVFP4 weights (RadixArk). Chart numbers are not in the repo table (code 51.5 / essay 18.3 / chat ~23). Our live Spark 27B is Ollama Q4_K_M 31.7 wall. Do not start.sh."
index_title: "MiaAI Qwen3.8-27B DSpark chart 67.5→58.8 @ 4k–256k — not in README; their named rows are code 51.5 / essay 18.3. Steal P2: don't quote the chart. Live leftover 27b stays Ollama :11435. No card."
index_links: [repo]
source_url: "https://x.com/MiaAI_lab/status/2092138272675737935"
source_url_2: "https://x.com/MiaAI_lab/status/2092017038319386782"
canonical_repo: "https://github.com/MiaAI-Lab/Qwen3.8-27B-SGLang-DGX-Spark"
canonical_docs: "https://huggingface.co/RadixArk/Qwen3.8-27B-NVFP4-BF16-LMHead"
bucket: inference
posture: steal
steal_rank: P2
confidence: high          # fxtwitter verbatim + chart OCR; GH API + README measured table read live. No docker, no pull.
hardware_fit: [spark]
stacks_touched: [t1000]
related_plans:
  - "SIG-20260823-03"     # MiaAI Flash EXL3 recipe — different model/engine
  - "SIG-20260812-01"     # SGLang engine-phase — Flash, not 27B
  - "SIG-20260812-02"     # Qwen3.8 flagship HARD NO; 27B now shipped
  - "spark-27b-n1-scoreboard"
  - "SIG-20260828-14"     # filicroval stock NVFP4 + DFlash2 whole-request 12.34→57.11. Same family, different clock
status: open
status_note: "**OPEN — steal P2, no card.** Hardware pre-filter N/A. 67.5 is an unlabeled think-off-looking ctx sweep, not our C1. Leftover 27b = Spark Ollama :11435; q38 = Mac MTPLX :8000. Do not ./start-dspark.sh."
distill: none
```

## 1. Claim

[@MiaAI_lab](https://x.com/MiaAI_lab/status/2092138272675737935) (Mia; ~18k followers; **202 likes / 12 RTs / 129 bookmarks / 22.6k views** at read; 2026-08-25 06:33 UTC). Fetched verbatim via `api.fxtwitter.com`:

> This is the expected decode tok/s with the new Qwen3.8-27B weights for the DGX Spark

Quotes her 08-24 post: update to the **BF16 `lm_head`** from @sgl_project for accuracy; Spark repo `MiaAI-Lab/Qwen3.8-27B-SGLang-DGX-Spark`.

Chart (title *Qwen3.8-27B DSpark Decode tok/s vs Context Length*; y = Decode tok/s, x = Context Length):

| Context | Decode tok/s |
|---|---:|
| 4k | **67.5** |
| 16k | 66.8 |
| 32k | 66.4 |
| 64k | 65.6 |
| 128k | 63.4 |
| 256k | **58.8** |

Nearly flat: **−13%** from 4k to 256k.

## 2. What we verified

| Check | Result |
|---|---|
| Post body | **verbatim** via fxtwitter; chart OCR'd |
| Repo | `MiaAI-Lab/Qwen3.8-27B-SGLang-DGX-Spark` — **★319 / 30 forks / 7 issues**, **MIT**, created **2026-08-15**, pushed **2026-08-24T22:07Z**. Docker + `start-dspark.sh` / `start.sh` (MTP) / `start-dflash.sh` |
| Default weights | `RadixArk/Qwen3.8-27B-NVFP4-BF16-LMHead` — NVFP4 W4A4 body + **dense BF16 `lm_head`** (~24 GB + ~2.7 GB DSpark draft). Packed-FP4-head twin still optional |
| Bind | `127.0.0.1:8888` / host network, mem-fraction **0.90**, native **262k**, **10 concurrent**, thinking **ON** by default (`--reasoning-parser qwen3`) |
| Hardware pre-filter | **N/A / pass.** Decode-vs-ctx on one GB10, not a PCIe-offload win |
| Local install | **Not run** |
| Duplicate URL | New tweet. Sibling of SIG-20260823-03 (Flash EXL3) — **different model**. Scoreboard already cited an older MiaAI 27B claim (~33–35) as `SIG-20260815-01` — that file is **not in this tree** |

**The chart is not in the README.** Their own *Measured on this box* table (2026-08-18, **packed-FP4 head**, not the new BF16-head default):

| Probe | DSpark | MTP | DFlash2 |
|---|---:|---:|---:|
| Code (LRUCache + test, n=5) | **51.5** | 34.5 | 50.9 |
| Long essay | **18.3** | 24.1 | 25.4 |
| Default chat (README quickstart) | **~23** | ~21 | ~29–67 streamed |

67.5 / 58.8 appear **nowhere** in the README. No probe, no `n`, no think on/off, no engine-vs-wall. Default serve is **thinking on**. A think-off ctx sweep is a different mode than the container you get from `./start-dspark.sh`.

**Our live 27B (not this stack):**

| Box | Stack | Number |
|---|---|---|
| ryan-spark `:11435` leftover | Ollama 0.32.12 · Q4_K_M · 65k · MTP draft=4 · co-resident 120b+8b | **31.7 wall / 42.8 engine** (A 9/10) |
| Mac `:8000` q38 | MTPLX Optimized-Speed | different box; fair chat ~18 |

27B is **not** the worker. 120b stays the closer.

## 3. Takeaways (max 5)

- **67.5 is a best-cell with no protocol.** README's named DSpark rows are 51.5 code / 18.3 essay / ~23 chat. Quote those, or nothing.
- **New thing is the BF16 `lm_head`**, not a new model. SGLang claims accuracy; we did not re-bench. Body is still NVFP4.
- **Flat 4k→256k (−13%) is the only interesting shape** if the chart is real. Unusable until the probe is named.
- **Do not stand up their Docker on either Spark.** `:8888`, mem 0.90, 10-wide, thinking on, ~27 GB extra next to 120b. Leftover 27b stays Ollama `:11435`.
- **Not the Flash EXL3 recipe.** SIG-20260823-03 is Kevin `:8889`. Do not merge.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **A ctx-vs-decode chart without probe / think / n / engine-vs-wall is not a result** | If the 27B scoreboard is touched, add a "do not quote 67.5" line. Do not A/B SGLang to chase the chart | **P2** | log only |
| S2 | Dense BF16 `lm_head` on an NVFP4 body (accuracy lever, ~+3 GB) | Watch only. Our Ollama Q4_K_M is a different quant family. No pull | P2 | watch |

**Primary steal (one only): S1.**

## 5. Do not

- **Do not `./start-dspark.sh` / `./start.sh` / `./start-dflash.sh`.** Docker + `lmsysorg/sglang:qwen38-27b` + 24 GB pull + `:8888`. DFlash2 first boot **builds an image** and has a hard-reboot history on this class of box.
- **Do not quote 67.5 or 58.8 as fleet numbers.**
- **Do not evict 120b** to "try" 27B-SGLang. Leftover lane is already filled.
- **Do not fold this onto `t_13d79be5` (SGLang Flash).** Wrong model.
- **Do not treat 10-wide 227 agg tok/s (DFlash2 C16) as N=1 chat.**

## 6. Next action (mechanical)

- [x] `INDEX.md` regenerated via `signal_log_index.py --write`
- [ ] no STEALS.md row (P2)
- [ ] no card

## 7. Chat blurb

`SIG-20260825-02` · `inference` · **steal P2** · MiaAI 27B DSpark chart 67.5→58.8 is unlabeled. Their README says DSpark **code 51.5 / essay 18.3**. Our Spark leftover is Ollama **31.7 wall**. Do not `./start-dspark.sh`.
