# SIG-20260902-02 — llama.cpp #28136: Spark Flash-Next prefill is mmap, not decode

```yaml
id: SIG-20260902-02
date: 2026-09-02
title: "TeksEdge remix of llama.cpp PR #28136 (coder543, OPEN): Qwen3.8-Flash-Next PLE/n-gram on SSD. mmap 4KB faults vs ~90B needed; parallel pread() → Spark prefill ~300 → ~750–800 tok/s (2–3×) without pinning PLE in RAM. Steal P2 fold Bakeer. Don't quote 800 as decode. Don't merge 28136/27742. Don't evict :8889."
index_title: "llama.cpp #28136 OPEN — Flash-Next PLE mmap→pread, Spark prefill 300→750. Fold Bakeer. Don't quote 800. Don't merge. :8889 stays."
index_links: [repo]
source_url: "https://x.com/TeksEdge/status/2095179948499890200"
canonical_repo: "https://github.com/ggml-org/llama.cpp/pull/28136"
canonical_docs: ""
bucket: inference
posture: steal
steal_rank: P2
confidence: high          # fxtwitter + GH PR body (open, not merged). No checkout, no merge.
hardware_fit: [spark]
stacks_touched: [t1000]
related_plans:
  - "SIG-20260826-06"     # Bakeer NVMe mmap n-gram — this PR is the mmap-fault fix for that path
  - "SIG-20260828-13"     # jaita 3-lane whole-in-RAM (no NVMe pin) — opposite trade
  - "SIG-20260828-01"     # filicroval ngram-mod
status: open
status_note: "**OPEN — steal P2, no card.** Hardware pre-filter N/A (GB10 SSD page faults, not PCIe KV offload). Prefill only. PR unmerged. Don't quote 800. Don't evict EXL3 :8889. Fold Bakeer."
distill: none
```

## 1. Claim

[@TeksEdge](https://x.com/TeksEdge/status/2095179948499890200) (David Hendrickson; ~10.5k fol; **27 likes / 1.5k views** at read; 2026-09-02 16:00 UTC). Fetched verbatim via `api.fxtwitter.com`:

> llama.cpp tweak made Qwen3.8-Flash-Next 2–3× faster at **prompt processing** on a DGX Spark… optimize SSD reading… HUGE PLE/n-gram table on SSD… mmap thousands of 4KB faults when the model may only need ~90 bytes… PR **#28136** parallel `pread()` … Before ~300 tok/s prefill → After ~750–800 … **OPEN, not merged**.

Megaphone. Artifact is **coder543**’s PR.

## 2. What we verified

| Check | Result |
|---|---|
| PR | [ggml-org/llama.cpp#28136](https://github.com/ggml-org/llama.cpp/pull/28136) **state=open, merged=false**, created 2026-09-01. Title: `qwen4exp: direct reads for the lazy PLE table (>2x prefill … on GB10)` |
| Author note | Repeated-token bench hid the fault (700+ tok/s); **diverse real text** dropped to ~300. `pread` workers → ~750–800 **without pinning PLE in RAM**. AI-written (GLM-5.3 / GPT-5.6 Sol), tested on his Spark |
| Hardware pre-filter | **N/A / pass** — SSD page-fault path on GB10, not a PCIe host↔device KV offload win |
| Duplicate URL | None. Same *engine family* as Bakeer mmap (26-06) + qwen4exp #27742 (still don’t merge) |

Kevin `:8889` is **EXL3-K2**, not llama.cpp mmap. This PR does not apply to Flash C1.

## 3. Takeaways (max 5)

- **Prefill, not decode.** 300→750 is prompt processing with PLE on SSD. Don’t quote 800 next to C1 54.8.
- **mmap is the villain they named.** Bakeer already mmap’d the 51B n-gram from NVMe. This is the *fault* tax on that design. jaita’s 3-lane recipe **pinned the whole model in RAM** to dodge it.
- **PR is open.** Same disposition as #27742: don’t merge onto the fleet.
- **Don’t evict `:8889`.** EXL3 doesn’t take this path.
- **TeksEdge is a remix account.** Cite the PR.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **If n-gram/PLE lives on NVMe, mmap 4KB faults can dominate prefill** | Fold Bakeer: don’t llama.cpp Flash-Next on Spark until 28136 is merged *and* we decide to leave EXL3. No overnight pull | **P2** | fold into SIG-20260826-06 |

**Primary steal (one only): S1.**

## 5. Do not

- **Do not quote 750–800 / 2–3× as decode or C1.**
- **Do not merge #28136 or #27742.**
- **Do not evict Kevin `:8889`.**
- **Do not `huggingface-cli download` Flash-Next GGUF to test this.**
- **Do not open a card.**

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [ ] no STEALS.md (P2)
- [ ] no card

## 7. Chat blurb

`SIG-20260902-02` · `inference` · **steal P2** · llama.cpp **#28136 OPEN**: Flash-Next PLE mmap→`pread`, Spark **prefill** 300→750. Don’t quote 800. Don’t merge. `:8889` stays.
