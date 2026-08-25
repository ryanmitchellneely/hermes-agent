# SIG-20260815-04 — Spark Arena: Unsloth Qwen3.8-27B-NVFP4 on one DGX Spark via vLLM (reproducible recipe)

```yaml
id: SIG-20260815-04
date: 2026-08-15
title: "spark_arena: Saiyam Pathak ran unsloth/Qwen3.8-27B-NVFP4 on a single NVIDIA DGX Spark with vLLM. Public bench page + full recipe YAML (container ghcr.io/spark-arena/dgx-vllm-eugr-nightly, TP=1, max_model_len 131072, kv-cache-dtype fp8, load-format instanttensor, flashinfer, prefix cache, qwen3_coder + qwen3 reasoning). Chart is concurrency vs throughput (SPA — numeric series not scraped this turn)."
index_title: "Spark Arena Unsloth Qwen3.8-27B-NVFP4 vLLM on 1×Spark. Steal = this recipe is the vLLM arm vs MiaAI SGLang (15-01). Demand W4A4 vs W4A16 + N. No docker pull."
source_url: "https://x.com/spark_arena/status/2088446524581630293"
canonical_repo: "https://huggingface.co/unsloth/Qwen3.8-27B-NVFP4"
canonical_docs: "https://spark-arena.com/benchmark/1b9f2bc6-5946-4167-95fc-a4d0557d7abe"
index_links: [docs]
bucket: inference
posture: steal
steal_rank: P1
confidence: high
hardware_fit: [spark]
stacks_touched: [t1000]
related_plans:
  - "SIG-20260815-01"
  - "SIG-20260813-02"
  - "SIG-20260814-04"
  - "ST-14 t_13d79be5"
  - "B17"
status: open
status_note: "**OPEN — first-party Spark Arena page + recipe YAML verified. Numeric concurrency curve not extracted (client-rendered).** Hardware pre-filter N/A. No install."
distill: none
```

## 1. Claim

[@spark_arena](https://x.com/spark_arena/status/2088446524581630293) (18 likes / 13 bookmarks / ~2k views):

> Check @SaiyamPathak’s **unsloth/Qwen3.8-27B-NVFP4** on a **single** NVIDIA DGX Spark with **vLLM**.  
> https://spark-arena.com/benchmark/1b9f2bc6-5946-4167-95fc-a4d0557d7abe

## 2. What we verified

Live page (title `unsloth/Qwen3.8-27B-NVFP4 - Spark Arena Benchmark`):

| Field | Value |
|---|---|
| Model | `unsloth/Qwen3.8-27B-NVFP4` |
| Runtime | vLLM · **TP=1 · 1 node** |
| Author | Saiyam Pathak |
| Container | `ghcr.io/spark-arena/dgx-vllm-eugr-nightly:latest` |
| Ctx / batch | `max_model_len=131072` · `max_num_batched_tokens=32768` · `gpu_memory_utilization=0.8` |
| Knobs | `--kv-cache-dtype fp8` · `--load-format instanttensor` · `--attention-backend flashinfer` · `--enable-prefix-caching` · `--tool-call-parser qwen3_coder` · `--reasoning-parser qwen3` · `VLLM_MARLIN_USE_ATOMIC_ADD=1` |

Chart copy: **X = concurrency, Y = faster**; more concurrent = more throughput, slower per request. **Numeric series not scraped** (SPA).

Hardware pre-filter: **N/A** (GB10 native).

## 3. Takeaways (max 5)

- Third Qwen3.8 Spark pack today: **SGLang cookbook** (15-01) · **vLLM Unsloth Arena** (this) · Mac MTPLX (15-03). Compare engines, don’t pick a brand.
- Recipe is the value — **instanttensor + flashinfer + fp8 KV + 131k** is a concrete vLLM arm for ST-14 / B17.
- **“NVFP4” still not one recipe** (SIG-13-02): Unsloth pack vs NVIDIA pack vs W4A4 vs W4A16. Arena row is Unsloth weights + nightly container.
- Concurrency axis is honest (matches SIG-13-01 / 15-02). Our kanban is still mostly **N=1**.
- Nightly GHCR image = **not** a supply-chain-clear default (same class as the 10-download veto). Cookbook-pinned `lmsysorg/sglang:qwen38-27b` is cleaner provenance for a first spike.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Spark Arena recipe as the vLLM comparison arm** vs MiaAI SGLang for Qwen3.8-27B on one Spark | When ST-14 or a Qwen3.8 serve is kicked: run **this flag set** as the vLLM column (N=1 and N=k). Prefer first-party image over `dgx-vllm-eugr-nightly` unless Ryan OK’s the GHCR. | **P1** | open |

**Primary steal:** S1

## 5. Do not

- `docker pull` the nightly or the Unsloth weights without a named kickoff + lane lease.
- Quote a tok/s from the tweet — there isn’t one.
- Collapse Unsloth NVFP4 with RadixArk NVFP4 / W4A16 NVIDIA packs.

## 6. Next action

- [x] entry
- [ ] INDEX + STEALS
- [ ] none — **no card** (cousin of ST-14 / 15-01)

## 7. Chat blurb

**SIG-20260815-04** · inference · steal **P1** · high  
Spark Arena: Unsloth Qwen3.8-27B-NVFP4 **vLLM on 1×Spark** — full recipe (instanttensor / flashinfer / fp8 KV / 131k).  
**Steal:** vLLM column vs SGLang 15-01. No pull. Curve not scraped.
