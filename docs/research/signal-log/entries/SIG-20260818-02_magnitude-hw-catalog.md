# SIG-20260818-02 — Magnitude catalog: profile hardware, estimate tok/s, auto-download + MTP/DFlash. Competing harness, not a desk tool.

```yaml
id: SIG-20260818-02
date: 2026-08-18
title: "tomgreenwald / Magnitude (YC S25): new model catalog profiles hardware, estimates tok/s before download, recommends models, then downloads HF quant, loads built-in engine, configures MTP/DFlash, sets concurrency from RAM. npm i -g @magnitudedev/cli. README: 'Ollama runs models. Hermes is an agent that can use local models. Magnitude combines both.'"
index_title: "Magnitude catalog (★968 Apache). Hardware picker + estimated tok/s. Competing harness vs T1000 — watch. Don't npm i -g. Don't let it squat Spark."
source_url: "https://x.com/tomgreenwald/status/2089475434903953561"
canonical_repo: "https://github.com/magnitudedev/magnitude"
canonical_docs: "https://docs.magnitude.dev"
index_links: [repo, docs]
bucket: harness
posture: watch
steal_rank: P2
confidence: high
hardware_fit: [mbp, spark, cadenspc]
stacks_touched: [t1000]
related_plans:
  - "agent-harness-compare"
  - "local-inference-fleet"
  - "SIG-20260810-01"
status: open
status_note: "**OPEN — no install.** Tweet + README + npm 0.0.6 + repo (Apache-2.0 ★968, pushed today) fetched. Hardware pre-filter N/A. README names Hermes as the thing they collapse into one binary. Do not `npm i -g`."
distill: none
```

## 1. Claim

[@tomgreenwald](https://x.com/tomgreenwald/status/2089475434903953561) (2.9k fol; 643 likes / 46 RT / 829 bookmarks / 52k views; YC S25 / @usemagnitude):

Which models can your machine actually run? Magnitude catalog now: auto-profile hardware, **estimate tok/s before download**, recommend a pick. Then download HF quant, load built-in engine, configure **MTP / DFlash**, set concurrency from memory.

`npm i -g @magnitudedev/cli`

## 2. What we verified

| Check | Result |
|---|---|
| Repo | `magnitudedev/magnitude` Apache-2.0 ★**968** / 91 forks / created 2026-06-12 / pushed **today** / site magnitude.dev |
| npm | `@magnitudedev/cli` **0.0.6**, Apache-2.0, created 2026-03-11 |
| README vs us | “Ollama runs local models. **Hermes is an agent that can use local models.** Magnitude combines both… Nothing else to set up.” |
| Hardware pre-filter | **N/A** (picker, not a PCIe-offload win) |

## 3. Takeaways (max 5)

- This is a **second agent OS**, not a catalog plugin for T1000.
- The only stealable idea is **estimate tok/s + fit before download**. We already have residency budget + the Spark metric card; we do not need their engine.
- Auto MTP/DFlash is the same trap as SIG-10-01 / SIG-16-02: spec-dec without `n_max` / accept% is unreadable.
- `npm i -g` onto this Mac would fight MTPLX `:8000` and Spark Ollama pins.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Fit + estimated tok/s before a download** | Optional one-liner in `local-inference-fleet` residency: refuse a pull that doesn’t name host + verb + estimated resident GB. Already implied. **No card** | **P2** | watch |

**Primary steal:** S1 (not P1)

## 5. Do not

- `npm i -g @magnitudedev/cli` on MBP / Spark / Cadens.
- Let Magnitude download a 27B/120B onto a box that already pins 120b+8b+27b.
- Treat “works on any hardware” as a Spark SLA.
- Dual-drive Magnitude + T1000 as Telegram brains.

## 6. Next action

- [x] entry + INDEX
- [ ] none — **no STEALS P0/P1 row, no card**

## 7. Chat blurb

**SIG-20260818-02** · harness · **watch P2** · high
Magnitude: hardware catalog + estimated tok/s + auto MTP/DFlash. README says they *are* Hermes+Ollama.
**Do not `npm i -g`.** T1000 stays SoT.
