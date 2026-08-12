# SIG-20260812-01 — SGLang Unified Radix Cache

```yaml
id: SIG-20260812-01
date: 2026-08-12
title: "SGLang Unified Radix Cache: one tree for hybrid prefix caching + session-aware eviction"
source_url: "https://x.com/sgl_project/status/2087258473776210085"
canonical_repo: "https://github.com/sgl-project/sglang"
canonical_docs: "https://www.lmsys.org/blog/2026-08-11-unified-radix-cache"
bucket: inference
posture: spike
steal_rank: P0
confidence: high
hardware_fit: [spark]
stacks_touched: [t1000]
related_plans: ["B17 engine phase / t_99c5d345", "t_08e96127", "t_7cb87a81", "t_e471787f"]
status: carded
distill: none

index_title: "SGLang Unified Radix Cache — the engine-phase candidate that CLEARS Ryan's supply-chain veto (official aarch64+cp312 wheel, sm121 maintained, deepseek_v4 + dspark in-tree)"
index_links: [repo, docs]
status_note: "**CARDED ST-14 `t_13d79be5`** (steals, blocked: window on ryan-spark). Supersedes the vLLM route on provenance — `t_08e96127` was countermanded by Ryan 08-11 on supply-chain grounds"
source_url_2: "https://x.com/lmsysorg/status/2087178463182454788"
```

## 1. Claim

SGLang replaces its per-architecture "cache class matrix" with a **single token-keyed radix tree**
whose per-architecture reuse rules attach as pluggable **components** (FULL path reuse / SWA trailing-window
reuse / MAMBA checkpoint reuse). HiCache tiering (GPU L1 → host L2 → external L3) and **session-aware
eviction** are native to that one tree. Gated behind `SGLANG_ENABLE_UNIFIED_RADIX_TREE=1` plus
`--enable-session-radix-cache`.

## 2. What we verified

**Provenance — all read live, not inferred from the post**

| Fact | Value |
|---|---|
| Repo | `sgl-project/sglang` — **★31,733, Apache-2.0**, pushed 2026-08-12 |
| Latest tag | **v0.5.17**, 2026-08-08 |
| Feature ships in the **tag**, not just main | `python/sglang/srt/mem_cache/unified_radix_cache.py` → HTTP 200 at `v0.5.17` **and** `main` |
| Session eviction flag in tag | `server_args.py:1433 enable_session_radix_cache` |
| PyPI wheel | `sglang-0.5.17-**cp312**-cp312-manylinux_2_34_**aarch64**.whl` (official, first-party) |
| Kernel wheel | `sgl_kernel-0.3.21-cp310-**abi3**-manylinux2014_aarch64.whl` (abi3 ⇒ covers 3.12) |
| GGUF | `load_format="gguf"` + `check_gguf_file()` present in tagged `server_args.py` |
| **DeepSeek-V4 model classes in-tree** | `deepseek_v4.py`, **`deepseek_v4_dspark.py`**, `deepseek_v4_nextn.py` |
| **sm121 status** | Actively maintained, **not** silently unsupported — #32330 *"enable FlashInfer TRT-LLM all-reduce on SM12X"* (closed), #31366 *"skip dsv3_fused_a_gemm test on consumer Blackwell (sm120/sm121)"* (closed), **#19637 "SM120 Performance Optimization Plan" — OPEN** |

**ryan-spark, measured live:** `aarch64` · Python **3.12.3** · GB10 compute_cap **12.1** = sm121 ·
121 GB unified, 33 GB available (120b resident) · **3.3 TB free** · no sglang, no vllm installed.
**Wheel triple-matches the box.**

**Their numbers — claimed, none reproduced by us**

- HiCache tiers, DeepSeek-V4-Flash-FP8, **4×H200 TP4**, 48 clients × 60 rounds: L3 hit rate ~98%,
  TTFT <9 s, **145.5K** effective input tok/s vs **9.4K** (L1) / **14.3K** (L1+L2).
  Inkling-Small **8×H200 TP8**: 96.8%, 1.23 s TTFT, 67.1K vs 15.5K / 21.1K.
- Session-aware eviction on SWE-bench trajectories, TP8: device hit ratio **42%→51%**
  (DSv4-Pro bs128), **~5%→34%** (Qwen3.5-397B-A17B bs32), device+host **58%→67%** (Qwen bs64);
  **TTFT −2.9% to −16.6%**.
- Experimental **Rust** L1-only tree core: TTFT **−38%** over 200 turns, **−42%** over turns 176–200
  (SWA / gpt-oss-20b).

**Our side of the mapping — measured, ours**

- DS4 on `kevin-spark` runs a **single-boundary disk checkpoint** KV scheme. Live now:
  `--ctx 65536 --kv-disk-space-mb 524288` (raised 64G→512G, sovereign-consulting `cc9e606`),
  dir at **155 G / 258 files**, uptime 17h27m.
- Before that raise we measured the exact pathology their session-aware eviction targets:
  **95.4% of evicted entries had `hits=0`**, ~38% hit rate, `reason=disk-cache-full`.
- Our worker workload **is** their benchmark shape: a ~**35.7k-token** system prefix plus
  accumulating tool results, replayed every turn — a growing shared conversational prefix.

## 3. Takeaways (max 5)

1. **This is the first engine candidate that clears the bar Ryan actually set.** `t_08e96127`
   (vLLM sm121 wheel) was countermanded 2026-08-11 — *"dont install something with only 10
   downloads"* — and the card carries a `block_loop_detected` STOP revoking its supply-chain OK.
   SGLang answers that objection directly: first-party PyPI wheel, 31.7k★, Apache-2.0, sm121
   issues closed **today**. Verified nothing was installed on spark from the vLLM attempt.
2. **They shipped the diagnosis of our own KV problem.** *"LRU records which entries were accessed
   recently, but not which prefixes belong to active sessions… it can evict an active session's KV
   while retaining unrelated entries."* That is verbatim our 95.4%-evicted-unused result.
3. **Hybrid attention explains why one boundary is not enough — and DeepSeek-V4 is their worked
   example.** DSv4 composes **FULL + SWA**: full-attention KV reuses the whole matched prefix, SWA
   only a contiguous trailing window. A single-boundary checkpoint scheme (ours) must either discard
   valid reuse or permit invalid reuse. That is a *mechanism-level* account of our poor hit rate,
   not a tuning story.
4. **`deepseek_v4_dspark.py` is in-tree.** DSpark is the drafter we chased through three dead ends
   (upstream Metal-only no-op `t_716141c4`; Entrpi llama.cpp fork at 72–73% accept, unadopted;
   no `dspark-*` GGUF anywhere in a 40-repo HF sweep). One engine would give DS4 Flash + DSpark
   + unified radix + continuous batching together.
5. **Seventh independent signal on the same prerequisite.** Latent Space · McNab width · Entrpi fork
   · DFlash · OoO-Spec · TurboQuant · now this. B17's engine phase is not one experiment among
   many; it is the gate.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Session-aware eviction beats LRU on agentic multi-turn** — attach a stable `session_id`, register the reusable region after each successful turn, and let it **order** eviction rather than pin memory | Bounded SGLang spike on **ryan-spark**, non-prod port, gpt-oss:120b or a small model first: `SGLANG_ENABLE_UNIFIED_RADIX_TREE=1` + `--enable-session-radix-cache`, measure prefix hit rate + TTFT vs llama.cpp's banked ~1,070 tok/s prefill | **P0** | **carded ST-14 `t_13d79be5`** |
| S2 | **One tree, per-architecture reuse components** — separate *prefix identity* from *reuse validity* instead of forking a cache class per model family | Design note for any future T1000 cache work; also the honest explanation to put on the DS4 KV cards for why more disk has diminishing returns | P2 | open |
| S3 | **Report cache hit rate per round, not just aggregate** — their Figure 4 is round-indexed, which is what exposes the capacity cliff | Field for the bench contract `t_6e058ca2`: prefix-hit-rate **by turn**, plus the tier it was served from | P1 | open |

**Primary steal (one only):** **S1**

## 5. Do not

- ⛔ **Do not quote "145.5K vs 9.4K" as a 15× speedup.** It is *effective input-token throughput* as
  defined by their own `bench_multiturn.py` — sum of complete prompt lengths ÷ wall clock — which
  **credits cache-hit prefix tokens**. It measures serving progress under reuse, not prefill compute.
- ⛔ **Do not treat the SWE-bench session-eviction deltas as an isolated ablation.** The blog says so
  explicitly: the comparison changes **both** the cache implementation and the eviction policy.
- ⛔ **Nothing in their benchmark transfers to a single GB10.** 4×/8× H200 with TP4/TP8 and a
  **500 GiB Mooncake Store** L3 tier. We have one 121 GB unified-memory box and no Mooncake.
- ⛔ **sm121 is supported, not tuned.** #19637 (SM120 perf optimization plan) is **open** and at least
  one sgl-kernel test is skipped on consumer Blackwell. Expect correctness before speed, and
  expect GB10 unified memory to differ again from a discrete 5090.
- ⛔ **Never on `kevin-spark`.** DS4 admission requires ≥105 GiB free and DS4 already holds ~105 GiB.
  A second engine there displaces the production code lane.
- ⛔ **Never bind `:11434`** (Juice teacher contract) or `:8889`. Non-production port, fresh venv,
  rollback = delete the venv.
- ⛔ **Do not present this as "SGLang gives us 1M context."** That is `SIG-20260810-07` (TurboQuant),
  a different lever on a different fork. Keep the two spikes separate or both results are confounded.

## 6. Next action (mechanical)

- [x] add/update STEALS.md rollup
- [x] card **ST-14 `t_13d79be5`** on the `steals` board (blocked: consumer-paused window on ryan-spark)
- [ ] none of: AUTOMATION-ROADMAP row, skill patch, plan patch

## 7. Chat blurb

`SIG-20260812-01` · inference · **spike P0** · carded ST-14 `t_13d79be5`.
SGLang v0.5.17 ships Unified Radix Cache + session-aware eviction **in the tag**, with an official
`cp312/aarch64` wheel that triple-matches ryan-spark and `deepseek_v4_dspark.py` in-tree.
It clears the supply-chain veto that killed the vLLM route (`t_08e96127`, countermanded 08-11).
Their session-eviction diagnosis is verbatim our measured 95.4%-evicted-unused KV pathology.
Their H200/Mooncake numbers transfer to us not at all — the spike is the point, not the blog.
