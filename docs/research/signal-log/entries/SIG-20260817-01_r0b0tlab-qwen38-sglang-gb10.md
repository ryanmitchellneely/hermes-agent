# SIG-20260817-01 — mr_r0b0t: click-run SGLang container for Qwen3.8-27B NVFP4 on 1×GB10 (123.90 is C8 EAGLE, not N=1)

```yaml
id: SIG-20260817-01
date: 2026-08-17
title: "mr_r0b0t: ready-to-run SGLang container for Qwen3.8-27B NVFP4 on one GB10. Poster: 123.90 tok/s C8 aggregate EAGLE think-off; Quality-200 38.1 mean / 66.8 peak; HumanEval 39/40 @ 58.9 mean; NIAH 8/8 @ 262K. Quant r0b0tlab/Qwen3.8-27B-NVFP4-MTP-sm121. Container r0b0tlab/qwen38-27b-nvfp4-sm121-sglang. README: dedicated c1 is 25.62 EAGLE / 20.97 DSpark — 123.90 is width. Official image pin by sha256. Do not use Unsloth NVFP4 (SGLang #34895)."
index_title: "r0b0tlab Qwen3.8 NVFP4 SGLang 1×GB10. 123.90 = C8 EAGLE not N=1 (c1 25.62). Quality-200 + NIAH 8/8. Steal = this digest-pinned arm vs MiaAI 15-01. No pull."
source_url: "https://x.com/mr_r0b0t/status/2089242896134221872"
canonical_repo: "https://github.com/r0b0tlab/qwen38-27b-nvfp4-sm121-sglang"
canonical_docs: "https://huggingface.co/r0b0tlab/Qwen3.8-27B-NVFP4-MTP-sm121"
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
  - "SIG-20260815-01"
  - "SIG-20260815-04"
  - "SIG-20260816-02"
  - "SIG-20260812-03"
status: open
status_note: "**OPEN — recipe + matched evals, no install.** Tweet + poster + MIT repo (★1, created today) + HF (3 likes / 388 dl, Apache-2.0, 4-of-4 shards) verified. Image is official lmsysorg/sglang digest-pin, not a rebuild. Hardware pre-filter N/A (GB10 native). Do not docker-pull tonight."
distill: none
```

## 1. Claim

[@mr_r0b0t](https://x.com/mr_r0b0t/status/2089242896134221872) (9.7k fol; 37 likes / 7 RT / 31 bookmarks / 2.4k views):

Ready-to-run `@sgl_project` container for **Qwen3.8 27B NVFP4 on one GB10**. **123.90 tok/s C8 aggregate.** Quality-200: 38.1 mean / 66.8 peak. HumanEval **39/40** at 58.9 mean. **262K**, NIAH **8/8**.

Quant: https://huggingface.co/r0b0tlab/Qwen3.8-27B-NVFP4-MTP-sm121
Container: https://github.com/r0b0tlab/qwen38-27b-nvfp4-sm121-sglang

## 2. What we verified

| Check | Result |
|---|---|
| Tweet + poster | fxtwitter 200. Graphic: C8 aggregate **EAGLE · think-off**. Quality-200 / HumanEval / Agentic 18/20 / NIAH 8/8 / GSM8K numeric 92.5% |
| Repo | `r0b0tlab/qwen38-27b-nvfp4-sm121-sglang` MIT ★**1** / created **2026-08-17 05:48Z** / pushed 12:01Z |
| Image | `lmsysorg/sglang@sha256:3c0abdf41ef22de9d7a859dc16ed71eae69452e36c91f071a25e60c85a6d1fc6` — **FROM-pin, not a rebuild**. Nightly forbidden |
| Weights | `r0b0tlab/Qwen3.8-27B-NVFP4-MTP-sm121` Apache-2.0, 4 shards, likes **3** / dl **388**, created 08-16. Draft: official **`RadixArk/Qwen3.8-27B-DSpark`** (not Doopeworld 0-dl) |
| Protocol | Same as his vLLM sibling: dedicated c1 512→2048 ×5 median; ladder 1024→256 c1/2/4/8 ×3; ignore-eos; temp 0; seed 0; think-off |
| Throughput (think-off, author) | **EAGLE c1 25.62** · c8 **123.90**. **DSpark c1 20.97** · c8 82.53. vLLM MTP K3 c1 27.83 / c8 82.89; vLLM DSpark K7 c1 28.46 / c8 61.53 |
| Quality-200 | His 200-prompt set (`artifacts/quality-200.jsonl`). DSpark: GSM8K flex 82.5 / numeric 92.5 · HE **39/40** · IF 37/40 · agentic **18/20** · hard not auto-graded. All-200 mean **38.1** / peak **66.8** (one HE item). Token-weighted 32.7 |
| NIAH | 8/8 both EAGLE and DSpark at 262k (vLLM shape, code `QWEN38-NIAH-9X4K`) |
| Canary | `19 × 23 → 437`. **`417` = FP8-KV flag defect** |
| Do-not (README) | No vLLM `Qwen3DSparkModel` adapter on this path. **No `unsloth/Qwen3.8-27B-NVFP4`** (SGLang #34895) |
| Hardware pre-filter | **N/A** (GB10 native). Batch ladder **present**. Quality has a ceiling arm (HE 39/40) |

## 3. Takeaways (max 5)

- **123.90 is C8 EAGLE aggregate, think-off.** N=1 on the same protocol is **25.62**. Do not quote the poster number as single-stream.
- MiaAI SIG-15-01 claimed **~33–35 N=1 / ~200 N=10**. His matched c1 is lower. Treat 15-01 as optimistic until we run a row.
- DSpark is his **production candidate** (quality); EAGLE wins width. Pick by job, don’t mix the two numbers.
- Supply chain is better than Bakeer same-day ★2: **official image digest + RadixArk draft + sha256 shards**. Still ★1 wrapper — no silent pull.
- Quality-200 is **his suite**, not our H1–H12 / FILE-fence. 39/40 HumanEval ≠ worker card.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Digest-pinned SGLang + official DSpark + canary + N=1 and C8 on one protocol** | Next Spark Qwen3.8 serve: this flag set is the SGLang column vs MiaAI 15-01 / Bakeer 16-02 / Arena 15-04. Report dedicated c1 **and** C8. Canary `19×23=437` before any tok/s. No new card | **P1** | open |
| S2 | Unsloth NVFP4 is a known SGLang reject (#34895) | Do not use the 15-04 Unsloth pack on an SGLang arm | P2 | fold |

**Primary steal:** S1

## 5. Do not

- Docker-pull tonight (★1 same-day wrapper). Official digest is fine **after** Ryan OK + a consumer-paused window.
- Quote **123.90** as N=1 or as “faster than MiaAI 33.”
- Dual-load 27B beside 120b / Nemotron on 121G.
- Use Unsloth NVFP4 or the vLLM DSpark adapter on this SGLang path.
- Treat Quality-200 / HE 39/40 as a worker-card pass.

## 6. Next action

- [x] entry + INDEX + STEALS
- [x] pointer on SIG-15-01
- [ ] fold S1 into next Spark Qwen3.8 serve note — **no card**

## 7. Chat blurb

**SIG-20260817-01** · inference · steal **P1** · high
r0b0tlab Qwen3.8 NVFP4 SGLang on 1×GB10. **123.90 = C8 EAGLE.** Dedicated c1 is **25.62**. Quality-200 + NIAH 8/8.
**Steal:** digest-pin + RadixArk DSpark + canary as the SGLang arm. **Do not pull.**
