# SIG-20260828-03 — Tech2Wild “load at 1M, cap per-agent” is paged-KV, not EXL3

```yaml
id: SIG-20260828-03
date: 2026-08-28
title: "Tech2Wild: load local LLM at MAX ctx (claims 1M on 4× DGX Spark), cap per-agent in the harness; model max is 'just a ceiling' over a shared dynamic KV pool. True of paged-KV (vLLM/SGLang). False of EXL3 (MAX_MODEL_LEN × util preallocates) and of Ollama (num_ctx sizes resident KV). Steal P1: don't 1M :8889. No card."
index_title: "Tech2Wild 1M-on-4×Spark KV-pool tip — paged-KV ceiling, not EXL3 reservation. Steal P1: cap per-agent in Hermes; do not load :8889 at 1M. Don't quote 1M. No card."
index_links: []
source_url: "https://x.com/Tech2Wild/status/2093199833263718579"
canonical_repo: ""
canonical_docs: ""
bucket: inference
posture: steal
steal_rank: P1
confidence: high          # fxtwitter verbatim. Engine split from our own EXL3/Ollama/DS4 measurements. No 4× box, no local run.
hardware_fit: [spark]     # the *pattern* (harness cap vs engine pool). His 1M/4× number does not fit.
stacks_touched: [t1000, k2]
related_plans:
  - "SIG-20260823-03"     # 384k at util 0.85 — the live EXL3 pool law this tweet would invert
  - "SIG-20260810-07"     # TurboQuant 1M is a *different* 1M (TQ3 KV-quant fork, not 'just a ceiling')
  - "SIG-20260807-03"     # McNab width — SUM of concurrent, not one 1M slot
  - "SIG-20260825-03"     # same megaphone; Flash-Next 'fits one Spark' was a guess
status: open
status_note: "**OPEN — steal P1, no card.** Hardware pre-filter N/A (not a PCIe-offload win). 1M is 4× Spark paged-KV. EXL3 max_seq_len reserves. Don't quote 1M. Don't raise :8889 to 1M. Fold onto 384k-at-0.85."
distill: none
```

## 1. Claim

[@Tech2Wild](https://x.com/Tech2Wild/status/2093199833263718579) (~3.3k followers; **48 likes / 5 RTs / 54 bookmarks / 2.4k views** at read; 2026-08-28 04:51 UTC; note-tweet, no media, no repo). Same megaphone as SIG-20260825-03. Fetched verbatim via `api.fxtwitter.com`:

> Load your model at MAX context (mine's 1M on 4x DGX Spark). Then cap context PER-AGENT in your harness, not on the model.
>
> Why it works: all your agents share ONE dynamic KV pool. The model's max context doesn't reserve memory, it's just a ceiling. Each request only uses the blocks it actually fills.
>
> Size the pool for the SUM of what runs at once, cap each agent so no runaway eats it all.

He is a **megaphone**. No engine named. No batch. No tok/s.

## 2. What we verified

| Check | Result |
|---|---|
| Post | **verbatim** via fxtwitter. No quote-tweet, no image, no repo |
| Hardware pre-filter | **N/A / pass.** Not a PCIe host↔device paper. Continue |
| 4× Spark 1M | **Does not transfer.** Fleet is 1× Spark per lane (Kevin Flash `:8889`, Ryan 120b). 121 GB UMA each, ATS, no CPU→GPU hop. Same-room pair is 2× + 200G DAC, not 4× TP |
| “max ctx doesn't reserve” | **Engine-class split, not a universal law** |
| Duplicate URL | None |

**Engine-class split (ours, already measured):**

| Engine | What `max ctx` does | Evidence |
|---|---|---|
| **EXL3-K2 `:8889`** | **Reserves.** `MAX_MODEL_LEN` × `GPU_MEMORY_UTILIZATION` sizes the KV pool at start. Live: 256k @ **0.85**, pool ~**609k**, C1 **54.8–55.8**. **0.90 → C1 19.5** | SIG-20260823-03 |
| **Ollama** | **Reserves per slot.** `ollama ps` size − `list` size = KV, sized by that model's `num_ctx`. `OLLAMA_NUM_PARALLEL` is the SUM cap (Ryan Spark **=2**) | local-inference-fleet residency |
| **DS4 (parked)** | ctx and `--kv-disk-space-mb` are a **pair**. 32k→65k doubled on-disk KV against an 8 GB disk budget → 55 evictions / 10h | SIG-20260810-07 family |
| **vLLM / SGLang paged KV** | His sentence is **true** — `max_model_len` is a ceiling, blocks fill per request | SIG-20260812-01 / 12-03. **Not what `:8889` runs** |

No batch size, no named engine, no ceiling arm → a throughput reading of this tweet is **unreadable**. The 1M is a cluster flex, not a GB10 recipe.

TurboQuant 1M (SIG-20260810-07) is a **different 1M**: TQ3 KV-quant fork + 91 GiB weights, not “raise max_seq_len, it's free.”

## 3. Takeaways (max 5)

- **“Just a ceiling” is paged-KV slang.** Applying it to EXL3 is how you replay the 0.90 trap.
- **Harness per-agent caps are already the desk.** `providers.*.context_length` vs runtime is the 2026-08-08 Flash 100k-claim / 32k-runtime crash. Cap in Hermes **and** size the engine pool. Not instead.
- **Size for the SUM** we already own: `OLLAMA_NUM_PARALLEL`, EXL3 `MAX_NUM_SEQS` (MiaAI shipped **1**), DS4 `--batched-session`. McNab 32-wide is agg tok/s, not 32 × 1M.
- **1M on 4× is not a Spark number.** Don't quote it next to C1 55 or leftover 27B 31.7.
- **Same author guessed Flash-Next “fits one Spark.”** That countdown was empty that day (SIG-25-03). Treat 1M the same way.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Paged-KV ceiling ≠ preallocated reservation** — cap per-agent in the harness; still size the engine pool for the SUM. Do not load EXL3 at 1M because a tweet said max ctx is free | Leave `:8889` at 256k / 0.85. The live lever is still SIG-23-03: `MAX_MODEL_LEN` 262144→384000 **util held 0.85** if pool ≥440k. Hermes `context_length` moves with the engine, never ahead of it | **P1** | fold — no new card |

**Primary steal (one only): S1.**

## 5. Do not

- **Do not quote 1M / 4× Spark.**
- **Do not raise `MAX_MODEL_LEN` to 1M on `:8889`.** That is a reservation, not a ceiling. 384k @ 0.85 is the open experiment; 1M is not.
- **Do not raise `GPU_MEMORY_UTILIZATION` past 0.85.** 0.90 = C1 19.5.
- **Do not treat this as a vLLM/SGLang install cue.** Those engines are the B17 engine-phase cards, not this tweet.
- **Do not open a card.** Fold onto the existing 384k-at-0.85 steal.

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [x] STEALS.md P1 row
- [ ] no card
- [ ] no engine flag change

## 7. Chat blurb

`SIG-20260828-03` · `inference` · **steal P1** · Tech2Wild 1M-on-4× “max ctx is just a ceiling” is **paged-KV**. EXL3 `:8889` **reserves** (`MAX_MODEL_LEN` × util). Cap per-agent in Hermes; do **not** load Flash at 1M. Don't quote 1M.
