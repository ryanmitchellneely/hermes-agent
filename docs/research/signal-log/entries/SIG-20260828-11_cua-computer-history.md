# SIG-20260828-11 — Pran_Ker: Cua Driver as cowork default. Computer History is an action log.

```yaml
id: SIG-20260828-11
date: 2026-08-28
title: "Pran_Ker (unaffiliated) makes Cua Driver his cowork/CUA default. Quotes trycua 08-18 Computer History: encrypted local record of Cua Driver actions so new sessions recover. Watch P2. Vendor of installed cua-driver 0.19.3. Don't curl|sh. Mac is glass, not runtime."
index_title: "Cua Computer History (trycua 08-18) via Pran_Ker. Encrypted local CUA action log. Watch P2. Don't curl|sh. Don't make Mac a CUA runtime. Related SIG-11-05."
index_links: [repo]
source_url: "https://x.com/Pran_Ker/status/2093140591089701305"
source_url_2: "https://x.com/trycua/status/2089770780053643397"
canonical_repo: "https://github.com/trycua/cua"
canonical_docs: "https://cua.ai"
bucket: harness
posture: watch
steal_rank: P2
confidence: high          # fxtwitter quote-tweet verbatim. GH trycua/cua ★21.9k. No curl|sh run.
hardware_fit: [none]      # Mac is glass; CUA runtime would invert that
stacks_touched: [t1000]
related_plans:
  - "SIG-20260811-05"     # same vendor, Lume Metal shim; cua-driver 0.19.3 already noted
  - "mac-cua-preflight"
status: open
status_note: "**OPEN — watch P2, no card.** Hardware pre-filter N/A. Computer History = encrypted local action log for Cua Driver. Don't curl cua.ai/driver/install.sh. Don't dual-drive Cua as Telegram cowork. Mac never runtime."
distill: none
```

## 1. Claim

[@Pran_Ker](https://x.com/Pran_Ker/status/2093140591089701305) (Prannay Hebbar; CUA/coding post-training; ~1k fol; **235 likes / 14 RTs / 261 bookmarks / 41k views** at read; 2026-08-28 00:56 UTC). Fetched verbatim via `api.fxtwitter.com`:

> I am not affiliated and hadn't heard of them before this. But my god, is this a well-built product. It's become my default for all cowork (computer use).

Quotes [@trycua](https://x.com/trycua/status/2089770780053643397) (18 Aug):

> first open-source Computer History — early preview for Cua Driver on macOS, Windows, and Linux. Encrypted, local record of actions they took through Cua Driver, so new sessions can recover useful context from earlier work.

He is an **endorsement**, not the vendor. Cua's own bio is `curl | sh` install — **hard no**.

## 2. What we verified

| Check | Result |
|---|---|
| Quote | Verbatim. Product = **Computer History** on Cua Driver, not the Lume Metal shim |
| Repo | `trycua/cua` **★21,975 MIT**. Same vendor as SIG-11-05 (cua-driver **0.19.3** already noted on this Mac) |
| Hardware pre-filter | **N/A** |
| Duplicate URL | None. Subject-class = same vendor, **new feature** (action-log), not the 11-05 shim |

Computer History = persist GUI tool traces (click/type/verify) so the *next* CUA session isn't amnesiac. Analog of `session_search`, for the mouse.

## 3. Takeaways (max 5)

- **Endorsement ≠ install.** Pran_Ker does CUA post-training; “default for cowork” is his machine, not ours.
- **`curl \| sh` is in the vendor bio.** Signal-log hard rule. Don't.
- **Mac is glass.** CUA Driver as cowork default would make the laptop a runtime. VPS Hermes stays SoT; `computer-use` already exists.
- **Action-log is the only sentence.** If CUA sessions can't see prior clicks, they re-do them. We already have session transcripts for the desk; GUI traces are a different store.
- **Don't fork 11-05.** Same vendor, different artifact.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | Persist CUA *actions* (not just chat) so the next session can recover | Citation only. Don't stand up Computer History. If we ever need GUI-trace recall, fold into session_search — not a Cua sidecar | **P2** | log only |

**Primary steal (one only): S1.** Nothing to install.

## 5. Do not

- **Do not `curl -fsSL cua.ai/driver/install.sh`.**
- **Do not make Mac the CUA runtime.**
- **Do not dual-drive Cua Driver as Telegram cowork.**
- **Do not open a card.** 11-05 already tracks this vendor.

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [ ] no STEALS.md (P2)
- [ ] no card

## 7. Chat blurb

`SIG-20260828-11` · `harness` · **watch P2** · Pran_Ker defaulted to Cua Driver. Computer History = encrypted local CUA action log. Don't curl\|sh. Don't make Mac a runtime. Same vendor as SIG-11-05.
