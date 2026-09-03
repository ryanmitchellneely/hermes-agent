# SIG-20260902-04 — SparklingKit: 128GB is specialists, not a faster chatbot. Don't install.

```yaml
id: SIG-20260902-04
date: 2026-09-02
title: "stevibe SparklingKit — Spark as local workbench (ASR+OCR+translate+chat), six specialists in 128GB, file-folder SoT. Author drop. ★11 Apache-2.0. curl|sh install.sh. Steal P2: room ≠ tok/s. Don't docker onto :8889. Don't one-line install. T1000 already is the glue."
index_title: "SparklingKit (stevibe, ★11 Apache) — 128GB specialists not chatbot. Steal P2: room ≠ tok/s. Don't curl|sh. Don't displace Flash."
index_links: [repo]
source_url: "https://x.com/stevibe/status/2095206125583073735"
canonical_repo: "https://github.com/stevibe/SparklingKit"
canonical_docs: "https://sparklingkit.com"
bucket: product
posture: steal
steal_rank: P2
confidence: high          # fxtwitter verbatim + site HTML + GH ★11 Apache-2.0. No install.sh run.
hardware_fit: [spark]
stacks_touched: [t1000]
related_plans:
  - "local-inference-fleet"
  - "SIG-20260825-02"     # leftover 27B is already the specialist lane
  - "ocr-and-documents"
status: open
status_note: "**OPEN — steal P2, no card.** Hardware pre-filter N/A. Author drop, tiny repo, curl|sh. Don't install. Don't load six models on Kevin Flash. Sentence: 128GB is room for specialists."
distill: none
```

## 1. Claim

[@stevibe](https://x.com/stevibe/status/2095206125583073735) (~28k fol; **148 likes / 11 RTs / 183 bookmarks / 12k views** at read; 2026-09-02 17:44 UTC). Fetched verbatim via `api.fxtwitter.com`:

> I spent $4,699 on a DGX Spark and used it as a chatbot for six months… tokens per second was never the point… 128 GB doesn’t force one generalist… six specialists… SparklingKit… one-line install at sparklingkit.com

**Author**, not a clip.

## 2. What we verified

| Check | Result |
|---|---|
| Site | `curl -fsSL https://run.sparklingkit.com/stable/install.sh -o install.sh && bash install.sh` then `localhost:54321`. Apache-2.0, linux amd64+arm64 |
| Repo | `stevibe/SparklingKit` **★11**, created 2026-08-31, TypeScript |
| Hardware pre-filter | **N/A / pass** (GB10 room, not PCIe offload) |
| Duplicate URL | None |

**Hard rule:** no `curl|sh` onto `~/.t1000` or Spark.

We already: Flash `:8889` closer-lane, leftover 27B `:11435`, OCR/docs skills, file-first markdown, never-send.

## 3. Takeaways (max 5)

- **The sentence is real:** 128GB is *room*, not tok/s. 200-agg / 59-agg / 800-prefill slogans this week miss that.
- **Specialists beat one 35B at ASR/OCR.** Don’t ask Flash to transcribe.
- **Don’t install the panel.** T1000 is the glue. SparklingKit is a second SoT (Docker :54321).
- **Don’t load six models on Kevin `:8889`.** Flash stays EXL3-K2.
- **File-folder SoT** we already do. No lock-in pitch is table stakes.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **128GB = keep specialists loaded; generalist only thinks** | Already Flash + leftover 27B. Don’t docker SparklingKit. Don’t evict `:8889` | **P2** | log only |

**Primary steal (one only): S1.** Nothing to install.

## 5. Do not

- **Do not `curl …/install.sh` / Docker on Spark or VPS.**
- **Do not put six models on `:8889`.**
- **Do not upload client audio to a SaaS** (his origin story — we already never-send).
- **Do not open a card.**

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [ ] no STEALS.md (P2)
- [ ] no card

## 7. Chat blurb

`SIG-20260902-04` · `product` · **steal P2** · SparklingKit: **you bought room, not a faster chatbot.** Don’t curl\|sh. Don’t displace Flash. T1000 is already the glue.
