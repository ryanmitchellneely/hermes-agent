# SIG-20260814-01 — Gigatoken: CPU tokenizer at GB/s (MIT Rust); M4 Max Qwen ~994× vs HF; not a decode win

```yaml
id: SIG-20260814-01
date: 2026-08-14
title: "TeksEdge: Gigatoken (marcelroed/gigatoken, MIT Rust) takes Qwen tokenization 6.3 MB/s → 6.31 GB/s on Apple M4 Max (~994× vs HF). Dual-EPYC published: GPT-2 24.5, Qwen3 22.2, DeepSeek 19.7 GB/s. Author correctly caveats: does NOT make the LLM generate 1k× faster — pretok only. Wins for huge RAG, agent tool-output ingest, dataset prep, giant ctx prefill prep. Native API >> HF/tiktoken drop-in compat (compat still much faster than stock HF)."
index_title: "Gigatoken (MIT Rust) pretok GB/s — M4 Max Qwen ~994× vs HF. Steal for agent/RAG ingest + dataset prep, not decode. Prefer native API over HF-compat path."
source_url: "https://x.com/TeksEdge/status/2088068092656238718"
canonical_repo: "https://github.com/marcelroed/gigatoken"
canonical_docs: "https://github.com/marcelroed/gigatoken/blob/main/README.md"
index_links: [repo]
bucket: inference
posture: steal
steal_rank: P1
confidence: high
hardware_fit: [mbp, spark, mini, caden, cloud]
stacks_touched: [t1000, k2, sovereign]
related_plans:
  - "B17"
  - "agent ingest"
  - "distillery"
status: open
status_note: "**OPEN — pretok library, not engine.** Verified first-party repo MIT · Rust · ★~3.9k · pip `gigatoken`. README tables match the tweet ballpark (M4 Max Qwen3.5/3.6 6.31 GB/s vs HF 6.3 MB/s). Hardware pre-filter N/A (CPU SIMD path). No install onto desk default path without a named consumer."
distill: none
```

## 1. Claim

[@TeksEdge](https://x.com/TeksEdge/status/2088068092656238718) (98 likes / 85 bookmarks / ~5.8k views):

Gigatoken turns HF-class tokenization into **GB/s** on CPU. Headline: **Qwen 3.5/3.6 on M4 Max 6.31 GB/s vs 6.3 MB/s (~994×)**. Dual EPYC 9565: GPT-2 **24.5**, DeepSeek **19.7**, Qwen3 **22.2** GB/s. Explicit: **does not** speed generation; speeds **text → tokens** before the model.

## 2. What we verified

| Check | Result |
|---|---|
| Repo | `marcelroed/gigatoken` — **MIT**, language **Rust**, ★ **~3,984**, forks ~210, created 2025-11, pushed 2026-08-06 |
| Install | `pip install gigatoken` |
| API | Native `gt.Tokenizer` + file sources; **HF / tiktoken compat** via `.as_hf()` / `.as_tiktoken()` (README: exact match costs throughput) |
| README M4 Max | Qwen 3.5/3.6 **6.31 GB/s** vs HF **6.3 MB/s** (994×); DeepSeek **5.68** vs 7.2 MB/s; GPT-2 **8.79** vs 6.9 MB/s |
| README dual EPYC | GPT-2 **24.53**, Qwen3 **22.16**, DeepSeek **19.69** GB/s — matches tweet |
| Mechanism (claimed) | SIMD pretok, caching, parallelism, less Python/thread overhead |
| Hardware pre-filter | N/A — not a PCIe-offload paper |

**Claimed numbers, not fleet-measured.** Our M3 Max / Spark boxes should land in the same *order of magnitude* if we ever bench.

## 3. Takeaways (max 5)

- Pretok is invisible in short chat and **visible** when agents chew tool dumps / RAG / cut-book / Distillery corpus.
- **Native API vs drop-in** is the real product choice — tweet + README both warn compat mode is slower.
- Pipeline optimization > model-only tok/s fetish (pairs with our segment-split steals).
- Supports the vocab we actually serve (Qwen, DeepSeek, Nemotron, Llama, GPT-OSS on README tables).
- Not a substitute for engine phase (vLLM/SGLang) — orthogonal.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Pretok as first-class agent/RAG stage** — measure wall share of tokenize vs prefill vs decode on a heavy tool-ingest card | One microbench: HF vs gigatoken native on a real agent transcript dump + a cut-book/RAG file; report GB/s + wall ms | **P1** | open |
| S2 | Prefer **native** encode path when batching; keep HF-compat only for exact-match CI | If we adopt, never only wire `.as_hf()` for prod bulk | P2 | fold |

**Primary steal:** S1

## 5. Do not

- Cite 994× as model speed.
- `pip install` into the default Hermes venv without a named consumer + rollback.
- Expect chat TTFT to collapse on short prompts.

## 6. Next action

- [x] entry + INDEX + STEALS
- [ ] optional microbench when a heavy ingest path is already open — **no card**

## 7. Chat blurb

**SIG-20260814-01** · inference · steal **P1** · high  
Gigatoken MIT Rust: pretok GB/s (M4 Max Qwen ~994× vs HF).  
**Steal:** measure pretok share on agent/RAG ingest; native API > HF-compat. Not decode.
