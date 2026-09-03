# SIG-20260826-02 — WSJ $3T off-balance-sheet AI commitments (ZH teaser)

```yaml
id: SIG-20260826-02
date: 2026-08-26
title: "ZeroHedge teaser of WSJ: nine tech names ~$3.1T off-balance-sheet AI commitments, +$1.3T in ~3 months vs ZH's prior $1.8T. SoT is WSJ footnotes (uncommenced leases ~$1.2T + purchase commitments ~$1.9T), not the ZH premium wall. Watch P2. Not a T1000 install. NVDA stays roth_1 / propose-only."
index_title: "WSJ ~$3T off-BS AI commitments (ZH teaser) — $1.2T unstarted leases + $1.9T purchase orders vs ~$600B TTM capex. Watch P2. Cite WSJ footnotes, not ZH. No trade."
index_links: [docs]
source_url: "https://www.zerohedge.com/markets/balance-sheet-time-bomb-inside-ai-hits-31-trillion-13tn-three-months"
canonical_repo: ""
canonical_docs: "https://www.wsj.com/tech/ai/why-big-techs-ai-spending-is-3-trillion-higher-than-it-seems-e1067bb2"
bucket: product
posture: watch
steal_rank: P2
confidence: medium        # ZH live HTML is a premium teaser only. Numbers below from WSJ + same-week secondaries that quote the WSJ table. No 10-K re-read in this pass.
hardware_fit: [none]
stacks_touched: [investing]
related_plans:
  - "investing-dashboard"  # propose-only; NVDA = roth_1 only
status: open
status_note: "**OPEN — watch P2, no card.** Hardware pre-filter N/A. ZH is paywalled reprint energy; SoT is WSJ 2026-08-17 footnote analysis. Not a harness steal. Do not trade off this entry."
distill: none
```

## 1. Claim

ZeroHedge (Tyler Durden; title *The Off-Balance Sheet Time Bomb Inside AI Hits $3.1 Trillion: Up $1.3TN In Three Months*). Live fetch **2026-08-26** is a **premium teaser**: they point at their own earlier “$1.8T off-BS time bomb” and stop at “Sign Up For ZH Premium.” Full body **not recovered** (Wayback/archive.today miss; recover_page.py failed).

The underlying story is the **WSJ** (2026-08-17): *Why Big Tech’s AI Spending Is $3 Trillion Higher Than It Seems.*

## 2. What we verified

| Check | Result |
|---|---|
| ZH page | HTTP 200, **paywall/teaser**. Prior ZH figure they cite: **~$1.8T** off-BS (purchase ~$1tn + leases >$800bn) |
| SoT | WSJ analysis of **footnotes** in latest filings for nine names: Alphabet, Amazon, Meta, Microsoft, Oracle, Nvidia, Broadcom, AMD, SpaceX |
| Split (WSJ, via same-week writeups that quote it) | **~$1.2T** uncommenced leases + **~$1.9T** purchase commitments ≈ **~$3.0–3.1T** |
| Comparables | TTM capex **~$600B**; on-BS leases + long-term debt **~$1T** (≈3×) |
| Named cells | Alphabet purchase/other contractual **$811B as of June 30**, vs **$332B** three months earlier (TipRanks quoting WSJ). Meta unstarted leases **$347B** |
| Hardware pre-filter | **N/A** |
| 10-K/10-Q re-read | **Not done this pass** — numbers are **claimed by WSJ**, not re-summed from filings here |
| Duplicate URL | None |

ZH “+$1.3TN in three months” is their **$1.8T → $3.1T** delta, not a WSJ headline. Do not treat ZH as the measurement.

These are **contractual commitments**, not “hidden debt” in the CDS sense until delivery/commencement. Accounting keeps them off-BS until the lease starts or the chips arrive. If demand slips they still have to pay or take a charge. That is the risk, not fraud-by-default.

## 3. Takeaways (max 5)

- **Capex is the cash that already went out. Footnotes are the cash they’ve promised.** Quote both or neither.
- **ZH is a teaser.** Cite WSJ (or the 10-Q footnote) if this number is reused.
- **NVDA is in the nine.** Desk rule unchanged: **NVDA = roth_1 only, propose-only.** This entry is not a trade.
- **Not a T1000/harness steal.** No install, no card, no dashboard change.
- **Alphabet’s $811B vs $332B in one quarter** is the cell that would need a filing re-read before anyone treats it as SoT.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Headline capex ≠ committed spend** — uncommenced leases + purchase obligations live in footnotes | If an investing brief cites “AI spend,” require the footnote split. Do not change the book from this paste | **P2** | watch — no ticket |

**Primary steal (one only): S1.**

## 5. Do not

- **Do not treat ZH as the source.** Premium wall; WSJ is SoT.
- **Do not trade / rebalance / add NVDA** off this.
- **Do not equate “off-balance-sheet” with “fraud.”** It is GAAP timing until commencement/delivery.
- **Do not open a kanban card.**

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [ ] no STEALS.md (P2)
- [ ] no card
- [ ] no investing-dashboard write

## 7. Chat blurb

`SIG-20260826-02` · `product` · **watch P2** · ZH is a paywall teaser of the WSJ footnote story: nine names **~$3T** off-BS AI commitments ($1.2T unstarted leases + $1.9T POs) vs **~$600B** TTM capex. Cite WSJ, not ZH. No trade.
