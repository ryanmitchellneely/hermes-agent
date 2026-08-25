# SIG-20260815-06 — Tony Simons: content half-life / hub-and-spoke (Bot Mode review as the hub)

```yaml
id: SIG-20260815-06
date: 2026-08-15
title: "Tony Simons (@tonysimons_) — 'Most creators don’t have a content problem. They have a content half-life problem.' System: one hub treated as source material (not a funeral) → multiple standalone spokes on different useful angles → repeated paths back to the big idea. Quote-tweet of his Aug 14 Hermes Bot Mode review (tonyreviewsthings.com)."
index_title: "Tony hub-and-spoke half-life (Bot Mode review = hub). Product steal P2 — joinsov factory already exists; don't fork Bot Mode SIG."
source_url: "https://x.com/tonysimons_/status/2088630792461426708"
source_url_2: "https://x.com/tonysimons_/status/2088135760880730502"
canonical_repo: ""
canonical_docs: "https://www.tonyreviewsthings.com/hermes-bot-mode-review/"
index_links: [docs]
bucket: product
posture: steal
steal_rank: P2
confidence: high
hardware_fit: [none]
stacks_touched: [sovereign, t1000]
related_plans:
  - "SIG-20260813-04"
  - "sovereign-content-factory"
  - "sovereign-public-surface"
status: open
status_note: "**OPEN — tweet + hub article fetched. Pattern only. No STEALS row, no card.** Hardware pre-filter N/A. Bot Mode product itself stays on SIG-20260813-04."
distill: none
```

## 1. Claim

[@tonysimons_](https://x.com/tonysimons_/status/2088630792461426708) (note-tweet, 2026-08-15 14:16 UTC; 19 likes / 15 bookmarks / 3 replies / 1 quote / 1,948 views at fetch):

> Most creators don’t have a content problem. They have a **content half-life problem**. You publish one strong piece. It gets a few hours of oxygen. Then the timeline buries it. My new system starts with **one hub** and treats it like **source material, not a funeral**. One hub. Multiple standalone spokes. Different useful angles. Repeated paths back to the big idea.

Quote of his Aug 14 Bot Mode review (124 likes / 80 bookmarks / 8,490 views): long-form of Nous Hermes-Bot-Mode.

## 2. What we verified

| Field | Value |
|---|---|
| Author | Tony Simons — “I help people get @NousResearch Hermes Agent working.” ~9.1k followers, Iowa, tonyreviewsthings.com |
| Primary | fxtwitter + vxtwitter 200; text as quoted; **no media** on the half-life note |
| Quote | Aug 14 review + photo `HPqMIdWXIAA_LF5.jpg` (1672×941) |
| Hub article | [Hermes Bot Mode Review](https://www.tonyreviewsthings.com/hermes-bot-mode-review/) — Aug 14 2026, 8 min, **4.5/5**, public-beta caveats match SIG-20260813-04 (desktop-only plugin, CLI delete, async Agent Inbox, stock `~/.hermes/desktop-plugins` install) |
| Repo / playbook | **None** — “my new system” is a tweet thesis, not a shipped kit |
| Hardware pre-filter | **N/A** (content ops, not PCIe/KV) |

Already on disk: Bot Mode architecture / T1000 install-path footgun = **SIG-20260813-04**. This entry is the **syndication pattern**, not a second Bot Mode writeup.

## 3. Takeaways (max 5)

- Half-life, not volume: a strong piece dies on the timeline unless you **re-cut it into standalone spokes** that still work alone.
- Hub = source material, not a funeral. Tony is demonstrating it: Bot Mode review is the hub; this note is a spoke (distribution/ops angle, not another feature tour).
- Spokes need **different useful angles** + **explicit paths back** — not the same recap pasted six times.
- Joinsov already has a factory (`sovereign-content-factory`: one patent-paper film, site IA, VO, archive). Gap is **post-ship spokes**, not another master.
- Do **not** reopen Bot Mode as a new harness SIG because Tony quoted the review.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Hub + standalone spokes + back-links** after one ship, to beat timeline half-life | When a joinsov / T1000 public piece ships, emit 2–4 spokes (each a different angle, each pointing home). Do not treat the master as done. Factory already owns the hub; this is the syndication step after `archive_version.py`. | **P2** | open |

**Primary:** S1 (P2 — no STEALS.md row, no card)

## 5. Do not

- Do not file another Bot Mode harness SIG from Tony’s review URL.
- Do not `git clone` Bot Mode from this tweet (wrong claim; wrong home if you did).
- Do not start a new joinsov film / content-ops repo for “Tony’s system.”
- Do not post/syndicate anything without Ryan’s explicit OK on that send.

## 6. Next action

- [x] entry + INDEX
- [x] pointer on SIG-20260813-04 §0 (Tony review = long-form, not a fork)
- [ ] none — **no STEALS P0/P1 row, no card**

## 7. Chat blurb

**SIG-20260815-06** · product · **steal P2** · high
Tony: half-life, not volume. One hub → standalone spokes → paths back. Hub = his Bot Mode review.
**Steal:** post-ship spokes for joinsov/T1000 public pieces. Factory already owns the hub.
No card. Bot Mode stays **SIG-20260813-04**.
