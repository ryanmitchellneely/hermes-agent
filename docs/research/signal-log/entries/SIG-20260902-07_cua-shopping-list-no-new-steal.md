# SIG-20260902-07 — CUA shopping list. Browser-use + Cua already filed. No new steal.

```yaml
id: SIG-20260902-07
date: 2026-09-02
title: "Screenshot: 'The repos I'd pay attention to' — browser-use, Stagehand, Agent S, Cua, BrowserGym, UI-TARS Desktop, Agent Sandbox, Agent Computer. Alpha check: browser_exec already live (11-02); Cua already watch (11-05/28-11). Rest = second harness. Watch P2. Don't install any."
index_title: "CUA shopping list (8 repos). browser-use + Cua already logged. No new steal. Don't Stagehand/Agent-S/UI-TARS. Mac never runtime."
source_url: ""
canonical_repo: ""
canonical_docs: ""
bucket: harness
posture: watch
steal_rank: P2
confidence: high          # screenshot OCR + GH API stars + existing SIGs 11-02/11-05/28-11. No install.
hardware_fit: [none]
stacks_touched: [t1000]
related_plans:
  - "SIG-20260811-02"     # browser_exec already default
  - "SIG-20260828-11"     # Cua Computer History
  - "SIG-20260823-04"     # prior top-N listicle
status: open
status_note: "**OPEN — watch P2, no card.** Hardware pre-filter N/A. Ryan asked for alpha on a CUA listicle. None new. Don't install. Mac is glass."
distill: none
```

## 1. Claim

Ryan dropped a screenshot: “The repos I’d pay attention to” — eight CUA/browser names. Asked for **alpha**, not an install.

## 2. What we verified

| Named | Live GH | T1000 |
|---|---|---|
| **browser-use** | `browser-use/browser-use` ★112k MIT | **Already live.** `browser_exec` is Hermes default (SIG-11-02). Don’t re-enable |
| **Stagehand** | `browserbase/stagehand` ★24k MIT | Second browser SDK (Playwright/a11y). `browser_exec` covers web. Don’t dual-drive |
| **Agent S** | `simular-ai/Agent-S` ★12k Apache | Full CUA harness. Second SoT. Mac never runtime |
| **Cua** | `trycua/cua` ★22k MIT | **Already watch.** cua-driver 0.19.3 noted. Don’t curl\|sh (11-05 / 28-11) |
| **BrowserGym** | `ServiceNow/BrowserGym` ★1.3k | Eval gym. Citation-only if we ever dogfood web agents. Not a runtime |
| **UI-TARS Desktop** | `bytedance/UI-TARS-desktop` ★39k Apache | Desktop agent stack. Second SoT. Don’t install |
| **Agent Sandbox** | E2B-class (many forks) | We already run as the user on VPS. Don’t add a sandbox product |
| **Agent Computer** | ambiguous (★2–14k lookalikes) | Local workspace for coding agents. Cursor + Hermes already. Don’t dual-drive |

Hardware pre-filter: **N/A**. Duplicate class: SIG-23-04 top-N listicle (different 13). This one is CUA-only.

## 3. Takeaways (max 5)

- **No new P1.** The two that matter are already on the log.
- **Web vs GUI:** web → `browser_exec`. Mac GUI → CuaDriver + doctor, not Agent S / UI-TARS.
- **Don’t add Stagehand in front of browser_exec.** Second control plane for the same tab.
- **Persist CUA *actions*** was already the 28-11 sentence. Not a new repo.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | Keep one web tool (`browser_exec`) and one GUI driver (Cua + TCC). Don’t collect frameworks | None. Don’t install | **P2** | log only |

**Primary steal (one only): S1.** Nothing to install.

## 5. Do not

- **Do not `pip install` Stagehand / Agent-S / UI-TARS / BrowserGym.**
- **Do not curl Cua install.sh.**
- **Do not make Mac a CUA runtime.**
- **Do not open a card.**

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [ ] no STEALS.md (P2)
- [ ] no card

## 7. Chat blurb

`SIG-20260902-07` · `harness` · **watch P2** · CUA shopping list. **browser-use + Cua already filed.** No new steal. Don’t install the other six.
