# SIG-20260810-04 — The cluster is aspirational; the prebuilt vLLM sm121 wheel is not

```yaml
id: SIG-20260810-04
date: 2026-08-10
title: "ExoLabs DGX Spark + Mac Studio M3 Ultra cluster (u1tra_instinct) — and the prebuilt vLLM sm121/cp312/aarch64 wheel sitting in exo-spark-assets"
index_title: "Prebuilt vLLM wheel for GB10 EXISTS and matches our Spark triple exactly (sm121/cp312/aarch64) — but this wheel was VETOED by Ryan on supply-chain grounds (10 downloads, third party) and the 'download, not a build' headline is SUPERSEDED by SIG-20260812-03: the OFFICIAL vLLM aarch64 wheel is compiled 12.0-without-PTX, and the SM121 fix (#49904) applies to the SOURCE BUILD. Engine phase is a build. Cluster itself needs hardware we don't have"
index_links: [repo, docs]
source_url: "https://x.com/u1tra_instinct/status/2086773844547711012"
canonical_repo: "https://github.com/exo-explore/exo-spark-assets"
canonical_docs: "https://github.com/exo-explore/exo"
source_url_2: "https://exolabs.net"
bucket: inference
posture: steal
steal_rank: P0
confidence: high          # post fetched verbatim; repo metadata, release assets and exo README read directly; wheel triple checked live against ryan-spark
hardware_fit: [spark, mac]
stacks_touched: [t1000]
related_plans:
  - "t_99c5d345"          # B17 — the engine phase this may collapse from "build project" to "download"
  - "t_171fbfd2"          # profile card — still the gate on whether any of this pays
  - "t_227d09b2"          # llama.cpp engine swap, the current batch/window engine
  - "SIG-20260810-03"     # Arc B70 — vLLM prefill 3.8-8.5x over llama.cpp on a single stream
  - "SIG-20260810-02"     # OoO-Spec — where I wrongly narrowed the engine phase to "width only"
  - "SIG-20260807-03"     # McNab Spark width
status: carded
status_note: "**Primary steal CARDED `t_08e96127` — now in `triage` with Ryan's supply-chain STOP on THIS wheel (10 downloads, third party); the veto held, nothing was fetched.** ⚠️ **Corrected 2026-08-12 by `SIG-20260812-03`:** the official vLLM PyPI aarch64 wheel is built `TORCH_CUDA_ARCH_LIST='…12.0'` with PTX explicitly excluded, and PR #49904's SM121 fix is a *source-build* fix — so the engine phase is a **build**, not a download. Card retargeted; gate is now vLLM issue #51920 (engine crash at startup on sm_121 for MLA models = DS4 Flash)."
distill: none
```

## 1. Claim

[@u1tra_instinct](https://x.com/u1tra_instinct/status/2086773844547711012) (keys, 2.4k followers,
2026-08-10 11:17Z, 90♥ / 4.6k views):

> *"Wired up my DGX Spark cluster to the Mac Studio M3 Ultra for about **896GB of Vram** capacity
> and about **850 GB usable inference memory** with **segregated Prefill and Decode** using
> ExoLab's recommended setup."*

One photo, no benchmark numbers, no config posted. The 896 GB math is self-consistent:
**3 × Spark 128 GB (384) + M3 Ultra 512 GB = 896.**

## 2. What we verified

### The part that is directly ours

**`exo-explore/exo-spark-assets` publishes a prebuilt vLLM wheel for DGX Spark.**

```
v0.2.0  (2026-06-12)
  vllm-0.23.0rc2+g47bd77088.sm121-cp312-cp312-linux_aarch64.whl   147.1 MB   10 downloads
  exo-warm-cache.tar.gz                                            75.4 MB    5 downloads
v0.1.0  (2026-06-12)
  vllm-0.22.1rc1.dev437+ge0871ad22-cp38-abi3-manylinux_2_28_aarch64.whl  266.4 MB
```

**Checked live against `spark` (ryanneely1000@spark-6c82) — the triple matches exactly:**

| Wheel requires | Our Spark |
|---|---|
| `sm121` | `nvidia-smi` → **NVIDIA GB10, compute_cap 12.1** ✅ |
| `cp312` | **Python 3.12.3** ✅ |
| `linux_aarch64` | **aarch64** ✅ |
| — | `import vllm` → **ModuleNotFoundError** (not installed) |
| — | 3.3 TB free ✅ |

`exo-warm-cache.tar.gz` matters too: vLLM's `torch.compile` warmup on a new arch is brutal, and
that tarball is a prebuilt warm cache.

**Why this is a P0 and not a curiosity.** Across five signals we have treated "get vLLM onto the
Spark" as an unbounded source-build project on a new Blackwell ARM part, and used that assumption
to defer B17's engine phase. **Someone published a wheel for our exact triple two months ago.**
The engine phase may be a download plus a venv, not a build campaign.

### The part that is NOT ours

**Disaggregated prefill/decode could not be verified as a named exo feature.** What exo's README
actually documents:

- **Topology-Aware Auto Parallel** — splits by device resources + measured link latency/bandwidth
- **Tensor Parallel RDMA** — benchmarks are all **4 × 512 GB M3 Ultra Mac Studio** (DeepSeek v3.1
  671B 8-bit, Qwen3-235B 8-bit, Kimi-K2-Thinking 4-bit)
- **`exo-bench`** — *"measures model prefill and token generation speed across different
  **placement configurations**"*

"Segregated prefill and decode" is a plausible description of a **placement configuration**, but it
is the poster's phrasing, not an exo feature name I can point at. Treat the architecture as
**claimed, not documented.**

**Also unverified by design: `exo-spark`'s source is not public.** The assets repo says
*"Source: exo-spark"* and no such repo exists in the org. We can see the artifact, not the build.

### The RDMA line that changes a decision we have open

> *"RDMA is a new capability added to macOS 26.2. It works on any Mac with Thunderbolt 5
> (**M4 Pro Mac Mini**, M4 Max Mac Studio, M4 Max MacBook Pro, **M3 Ultra Mac Studio**)."*

Per exo's own enumeration, the **M3 Max MacBook Pro is absent** — so Ryan's MBP cannot be an RDMA
cluster member. The **M4 Pro Mac mini we priced at ~$2,799 can be.**

That is a genuinely new argument in the mini decision. Until now the mini's case was
*"always-on nervous system"* and explicitly **not** *"outruns the M3 Max."* This adds a second,
different case: it is the cheapest RDMA-capable entry into an exo cluster, and the laptop can
never be one.

## 3. Takeaways (5)

1. **The engine gate may be cheaper than we priced it.** Not "build vLLM for Blackwell ARM" —
   `pip install` a 147 MB wheel into a venv. That does not make it *good*, it makes it **testable
   this week instead of next quarter**.
2. **This compounds with `SIG-20260810-03` from an hour ago.** That signal measured vLLM beating
   llama.cpp on **prefill 3.8–8.5× at `max-num-seqs=1`** — a single-stream number, not a batching
   one. **Prefill is our worker bottleneck** (~35.7k-token prompts; the KV raise moved prefill
   7.30 s → 2.47 s and decode not at all). Two independent signals in one morning point the same
   engine at the same bottleneck.
3. **10 downloads is the honest headline.** A release-candidate wheel pinned to a git hash, built
   by a third party, from a repo whose **source is unpublished**, downloaded ten times. That is a
   supply-chain decision, not a package-manager decision — and it is Ryan's to make, not mine.
4. **The cluster story needs hardware we do not have.** It is 3 Sparks + a 512 GB M3 Ultra. We have
   one Spark of our own, one of Kevin's (shared, not ours to cluster), and a 64 GB M3 Max that
   exo's own list rules out of RDMA. **Do not read this as validation of a second Spark** — it is
   validation that *someone else's* four-figure-per-box cluster works.
5. **The real unlock in the photo is memory, and memory is not our problem.** 850 GB usable buys
   Kimi-K2 / DeepSeek-671B class weights. Our constraint has never been "the model doesn't fit" —
   it is prefill latency on a 35.7k prompt. Different bottleneck; don't inherit their goal.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Prebuilt vLLM for GB10 exists — the engine phase is a download** | Bounded spike on **Ryan's Spark only**: fresh venv, `pip install` the `sm121/cp312/aarch64` wheel, extract the warm cache, serve **one** model on a **non-production port**, run the existing repair-battery + prefill measurement against llama.cpp's banked 49–50 tok/s and ~1,070 tok/s prefill. **Never touch `:11434`** (Ollama holds the Juice teacher contract per Ryan's Option-1 ruling) and never touch `:8889` (Kevin's DS4). | **P0** | open — commented onto `t_99c5d345` |
| S2 | Ship warm compile caches beside the wheel | `exo-warm-cache.tar.gz` is the fix for vLLM's cold `torch.compile` on a new arch. If we ever build our own, cache the artifact — that is the difference between a 20-minute and a 3-minute server start. | P1 | note |
| S3 | **RDMA eligibility is a hardware-purchase input** | Fold into the mini decision: M4 Pro mini is on exo's TB5/RDMA list, the M3 Max MBP is not. Second independent argument for the mini beyond always-on. | P1 | open — belongs in the mini brief, not a new card |
| S4 | Measure placement, don't assume it | `exo-bench` measures prefill and decode **per placement configuration**. Same discipline as `t_171fbfd2`: know the segment split before optimizing a segment. | P2 | folded into `t_171fbfd2` |

## 5. Do NOT

- **Do not install the wheel on Kevin's box.** DS4 owns ~105 GiB of unified memory there and the
  admission gate requires ≥105 GiB free. Ryan's Spark only, and only in a venv.
- **Do not install it system-wide or into any path Ollama or llama.cpp resolves from.** Both
  production lanes on that box (`:11434` teacher contract, llama.cpp batch/window engine) stay
  untouched. Fresh venv, non-production port, rollback = delete the venv.
- **Do not treat this as a second-Spark purchase signal.** The cluster is 3 Sparks + a 512 GB
  Studio. Different budget, different goal (fit huge weights), different bottleneck than ours.
- **Do not quote "896 GB / 850 GB usable" as a benchmark.** It is a capacity claim with no tok/s,
  no model, and no config attached.
- **Do not claim exo does PD disaggregation** until it is pointed at in their docs. Their README
  says *placement configurations*; the disaggregation framing is the poster's.
- No `curl | sh`. The wheel install is an explicit, reviewed `pip install <file>` after Ryan's OK —
  not a piped installer.

## 6. Provenance

Post via `api.fxtwitter.com` (skill's first route, worked first try). Repo metadata, org listing
and release assets via the GitHub API. exo README read raw from `raw.githubusercontent.com`;
`exolabs.net` fetched and stripped. **The wheel/host triple was checked live over SSH against
`spark`** — `uname -m`, `python3 --version`, `nvidia-smi --query-gpu=compute_cap` — not inferred
from the filename.

## 7. Next action (one)

Kanban comment on **`t_99c5d345`** (B17 Spark inference experiments) recording that the engine
phase has a prebuilt artifact matching our exact triple, with the supply-chain caveat and the
venv/port isolation constraints stated as preconditions. **No new card** — B17 already owns the
engine phase, the board is at 44 blocked, and the spike needs Ryan's word on installing a
third-party wheel before it becomes work.
