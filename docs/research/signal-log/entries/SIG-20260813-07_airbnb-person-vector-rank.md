# SIG-20260813-07 — Airbnb search personalization pattern: dual history → overnight person vector → rank (and reuse vector in email)

```yaml
id: SIG-20260813-07
date: 2026-08-13
title: "undefinedKi summary of Airbnb search personalization: every guest has long history (7y bookings/reviews/cancellations) + short window (21d looks; views=97.8% of actions so own window). Model compresses both → one person vector; computed overnight not at query time. NDCG +3.78%, bookings +0.55% (their bar: 0.3% is significant after a decade). Same vector reused in marketing email → clicks +5.04% with no change. Thesis: model the person, not the listing — ports to any catalogue/feed/marketplace."
index_title: "Airbnb dual-history → overnight person-vector rank (+3.78% NDCG, +0.55% book; email reuse +5.04% clicks). Steal for Sovereign/K2: person embedding offline, not listing hero; short view window separate from long booking history. Watch/P1 product — not inference install."
source_url: "https://x.com/undefinedKi/status/2087994882828685539"
source_url_2: "https://x.com/undefinedKi/status/2084279627204235703"
canonical_repo: ""
canonical_docs: ""
bucket: product
posture: steal
steal_rank: P1
confidence: medium
hardware_fit: [none, cloud]
stacks_touched: [sovereign, k2]
related_plans:
  - "joinsov public surface"
  - "arctic"
  - "B18"   # student labels / person modeling adjacent
status: open
status_note: "**OPEN — pattern only.** Secondary source (undefinedKi); no Airbnb paper URL in post. Quote tweet is their evals stack (programmatic → LLM judge → human calibrate). Use as product doctrine, not a dataset to scrape."
distill: none
```

## 1. Claim

[@undefinedKi](https://x.com/undefinedKi/status/2087994882828685539) (~13k followers; 26 likes / 19 bookmarks):

Airbnb personalizes search via **two guest histories** → **one person vector** → rank listings. Vector built **overnight**. Gains: NDCG **+3.78%**, bookings **+0.55%**; email reuse **+5.04%** clicks. *“Modelled the person, not the listing.”*

Prior post (quoted): Airbnb internal evals — programmatic checks → LLM judge → humans only to calibrate; golden 50–100 incl. failures; Cohen's kappa high 80s–90s; 5% live traffic daily.

## 2. What we verified

- Post fetched via fxtwitter; **no primary Airbnb eng blog URL** in the tweet body — confidence **medium** until primary linked.
- Architecture as stated is standard two-tower / user-tower offline inference; the steal is the **product cut** (long vs short, views-dominated short window, cross-surface vector reuse), not a new model class.
- Hardware pre-filter: N/A.

## 3. Takeaways (max 5)

- **Person vector offline** keeps search/email fast — matches our “don’t pay prefill tax at click time.”
- **Views ≠ bookings** — give look-history its own window (21d) or it drowns in 7y booking signal.
- **Cross-surface reuse** (search vector → email) is the multiplier; one representation, many rankers.
- Tiny booking lift can still be real after a decade of tuning — don’t dismiss 0.5% without their baseline discipline.
- Eval cousin: layered judges + small goldens with failures (pairs with our repair-battery / golden doctrine).

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Dual-horizon person model** — long conversion history + short attention/view window → single offline embedding for rank | For joinsov/Arctic/catalogue work: define long vs short event sets before any model; never rank on listing text alone | **P1** | open |
| S2 | Overnight batch person vectors; online only retrieves | Prefer batch job over per-request LLM personalize | P2 | architecture |
| S3 | Same vector powers search + CRM email | One identity representation across Sovereign surfaces | P2 | watch |

**Primary steal:** S1

## 5. Do not

- Scrape Airbnb or invent their paper citation without URL.
- Train on production PII without policy.
- Treat 0.55% as transferable to our traffic without our own golden.

## 6. Next action

- [x] entry + INDEX + STEALS
- [ ] if product work opens: one design note under joinsov/Arctic — no card yet

## 7. Chat blurb

**SIG-20260813-07** · product · steal **P1** · medium  
Airbnb: long+short guest history → overnight person vector → rank (+ email reuse).  
**Steal:** model the person offline; separate view window from conversion history.
