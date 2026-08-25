# SIG-20260818-03 — Hermes Desktop in-app browser: user + agent share a pane beside chat. Watch — we already have CUA.

```yaml
id: SIG-20260818-03
date: 2026-08-18
title: "HermesWatcher (unofficial): 'this is where Hermes Desktop starts getting really interesting' — in-app browser the agent can click/type while the conversation stays beside it. Quote imbabybrooklyn (939 likes): 'you have full control of the in-app browser now / Hermes does too' + video, @NousResearch."
index_title: "Desktop in-app browser (user+Hermes). Watch P2 — CUA already exists; visible split-pane is UX, not a new stack. Don't install a second browser."
source_url: "https://x.com/HermesWatcher/status/2089683235844538844"
source_url_2: "https://x.com/imbabybrooklyn/status/2089669386718085430"
canonical_repo: ""
canonical_docs: ""
index_links: []
bucket: product
posture: watch
steal_rank: P2
confidence: high
hardware_fit: [mbp]
stacks_touched: [t1000]
related_plans:
  - "macos-computer-use"
  - "inspecting-hermes-desktop-dom"
  - "SIG-20260813-04"
status: open
status_note: "**OPEN — demo tweet + video, no install.** HermesWatcher unofficial. Brooklyn demo video only (no repo). Hardware N/A. T1000 already has computer_use + cua_browser. Don't add a second browser engine."
distill: none
```

## 1. Claim

[@HermesWatcher](https://x.com/HermesWatcher/status/2089683235844538844) (4.1k fol, unofficial; 534 likes / 25 RT / 435 bookmarks / 43k views):

Give Desktop a browser the agent can actually drive **inside the app**. Watch it click/type while chat stays beside it.

Quote [@imbabybrooklyn](https://x.com/imbabybrooklyn/status/2089669386718085430) (7.9k fol; 939 likes / 353 bookmarks / 85k views): “full control of the in-app browser now / Hermes does too” + video, ping @NousResearch.

## 2. What we verified

| Check | Result |
|---|---|
| Official repo/docs this turn | **None** — community demo, not a tagged release |
| Video | Exists on the Brooklyn tweet (1792×1348). Not transcribed |
| Hardware pre-filter | **N/A** |
| What we already have | `computer_use` + `cua_browser_*` (background, no focus steal). DOM inspect skill is CDP on the **desktop chrome**, not a guest page |

## 3. Takeaways (max 5)

- The new thing is **visible split-pane**, not “Hermes can browse.” We already browse.
- Background CUA is the desk default so we don’t steal Ryan’s cursor. An in-app pane is a *second* surface, not a replacement.
- Unofficial watcher + community video ≠ ship in T1000.app tonight.
- Bot Mode / plugin path stays SIG-13-04.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Agent-driven page visible next to the thread** | If T1000.app already has a Browser tab, dogfood it. If not, wait for a Nous/T1000 release note — don’t bolt a WebView | **P2** | watch |

**Primary steal:** S1 (not P1)

## 5. Do not

- Install a third-party “Hermes browser” plugin into `~/.t1000`.
- Replace background CUA with a focus-stealing in-app WebView.
- Treat HermesWatcher as first-party.

## 6. Next action

- [x] entry + INDEX
- [ ] none — **no STEALS row, no card**

## 7. Chat blurb

**SIG-20260818-03** · product · **watch P2**
Desktop in-app browser (user + Hermes). We already have CUA.
**Don’t install a second browser.**
