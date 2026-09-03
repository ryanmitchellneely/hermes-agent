# SIG-20260828-10 — beamnxw Graphiti 94.8 is a Jan-2025 Zep vendor paper

```yaml
id: SIG-20260828-10
date: 2026-08-28
title: "beamnxw: Zep Graphiti 94.8% retrieval, +18.5% long-horizon, 90% lower latency. Card is Rasmussen et al. Zep AI, arXiv 2501.13956, 20 Jan 2025. DMR 94.8 vs MemGPT 93.4 (+1.4pp). Watch P2. Don't install Graphiti. Don't quote 94.8 (also Scroll's LongMemEval_S cell). Fold invalidate-stale into OpenViking."
index_title: "Zep Graphiti (arXiv 2501.13956, Jan 2025) — DMR 94.8 vs MemGPT 93.4. Watch P2. Don't install. Don't quote 94.8/90%. Fold stale-edge invalidation into OpenViking."
index_links: [repo, docs]
source_url: "https://x.com/beamnxw/status/2093054521056665983"
source_url_2: "https://x.com/i/article/2090062291693666304"
canonical_repo: "https://github.com/getzep/graphiti"
canonical_docs: "https://arxiv.org/abs/2501.13956"
bucket: harness
posture: watch
steal_rank: P2
confidence: high          # fxtwitter + card OCR + GH ★30.4k Apache-2.0. Paper date on PDF: 20 Jan 2025.
hardware_fit: [none]
stacks_touched: [t1000]
related_plans:
  - "SIG-20260823-01"     # OpenViking L0/L1 — this slot already occupied
  - "SIG-20260825-04"     # Scroll 94.8 is a *different* 94.8 (LongMemEval_S / Qwen3.8-Max)
  - "SIG-20260826-04"     # Recuris — mutate skills, not a graph store
status: open
status_note: "**OPEN — watch P2, no card.** Hardware pre-filter N/A. 19-month-old vendor paper. DMR +1.4pp over MemGPT. Don't hermes memory setup graphiti. Don't quote 94.8 (collides with Scroll). Fold: invalidate superseded facts."
distill: none
```

## 1. Claim

[@beamnxw](https://x.com/beamnxw/status/2093054521056665983) (~5.5k fol; telegram CTA; **78 likes / 4 RTs / 59 bookmarks / 3.1k views** at read; 2026-08-27 19:14 UTC). Quotes own 19 Aug X article. Fetched verbatim via `api.fxtwitter.com`:

> Zep's Graphiti engine achieves 94.8% retrieval accuracy while boosting long-horizon reasoning by 18.5% with 90% lower latency… solves state decay in multi-bot setups like my Grok Bot research desk.

He is a **megaphone**.

## 2. What we verified

| Check | Result |
|---|---|
| Card OCR | *Zep: A Temporal Knowledge Graph Architecture for Agent Memory* — Rasmussen / Paliychuk / Beauvais / Ryan / Chalef, **Zep AI**. **arXiv 2501.13956v1 [cs.CL] 20 Jan 2025** |
| Named cells | DMR **94.8% vs MemGPT 93.4%**. LongMemEval: **up to +18.5% accuracy**, **90% lower latency vs baseline** |
| Repo | `getzep/graphiti` **★30,372 Apache-2.0**, created 2024-08-08, still pushed. Real product, old paper |
| Hardware pre-filter | **N/A** |
| Duplicate URL | None. **94.8 is also Scroll's LongMemEval_S / Qwen3.8-Max cell** (SIG-25-04) — different system, same slogan number |

OpenViking (23-01) already owns “don't install a graph memory provider.” Graphiti would be a **second** memory plane (typically Neo4j) in front of USER/MEMORY.

## 3. Takeaways (max 5)

- **19-month-old vendor paper sold as a drop.** Cite Jan 2025 or cite nothing.
- **94.8 vs 93.4 is +1.4pp on DMR.** The tweet drops the comparator. 18.5 / 90 are LongMemEval vs *their* baseline, not Hermes.
- **Don't quote 94.8.** It collides with Scroll's Max-class cell.
- **Bi-temporal invalidation is the only sentence.** `t_valid` vs `t_invalid` on an edge = don't leave superseded USER facts live. We already fail this when a session writes a “lesson” over a dead one.
- **Not a Graphiti install.** OpenViking AGPL was rejected for the same slot.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Invalidate superseded facts** — an edge that is no longer true gets `t_invalid`, it doesn't sit next to the new one as equal | Fold into OpenViking S1 / memory-hygiene: a USER.md replace should *retire* the old line, not append a contradiction | **P2** | fold into SIG-20260823-01 |

**Primary steal (one only): S1.** Nothing to install.

## 5. Do not

- **Do not `pip install graphiti` / `hermes memory setup` Zep.**
- **Do not quote 94.8 / 18.5 / 90%.**
- **Do not stand up Neo4j for agent memory.**
- **Do not open a card.**

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [ ] no STEALS.md (P2)
- [ ] no card

## 7. Chat blurb

`SIG-20260828-10` · `harness` · **watch P2** · Graphiti 94.8 is **Zep AI Jan 2025**, DMR +1.4pp over MemGPT. Don't quote 94.8 (also Scroll). Don't install. Invalidate stale USER facts — that's it.
