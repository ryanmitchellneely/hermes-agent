# SIG-20260808-05 — Hermes Agent Dock v0.2.1 (per-profile side-channel)

```yaml
id: SIG-20260808-05
date: 2026-08-08
title: "Hermes Agent Dock v0.2.1 — native Desktop dock for direct profile chat"
source_url: "https://x.com/bkashjosi/status/2086016592874234068"
canonical_repo: "https://github.com/BkashJEE/hermes-agent-dock"
canonical_docs: "https://github.com/BkashJEE/hermes-agent-dock/releases/tag/v0.2.1"
bucket: harness
posture: steal
steal_rank: P1
confidence: high
hardware_fit: [mbp]
stacks_touched: [t1000]
related_plans: ["t_c7f2534a Desktop Kanban plugin", "t_33b54172 Desktop shell vs engine 0.20", "SIG-20260808-02 codex-router"]
status: open
distill: none
```

## 1. Claim
Community **Hermes Desktop plugin** (not Nous) adding a floating/docked specialist card: chat **directly with any configured Hermes profile** while the main orchestrator is busy, with concurrent per-profile jobs, cancellation, and **opt-in** Kanban assignment.

## 2. What we verified
- `BkashJEE/hermes-agent-dock` — **MIT**, JavaScript, ~17★, created **2026-08-07**, pushed 2026-08-08. Real releases `v0.2.0` → **`v0.2.1`** (today).
- Install is `git clone` + **`python install.py`** (stdlib-only, no npm/pip/post-install hooks) writing into `$HERMES_HOME/desktop-plugins/` + `$HERMES_HOME/plugins/`, with timestamped backup + SHA-256 manifest and a reversible `uninstall.py`.
- **Verified on Windows 10 only.** README explicitly states macOS/Linux are *not claimed as verified* this release.
- On **Hermes v0.20.0** (Ryan's exact engine) pet-click does nothing — status-bar + Command Palette are the supported launchers. Confirmed as expected behavior, not a bug.
- Discovery uses official `hermes_cli.profiles.list_profiles()`; reads only name/default/gateway/model/description. **No** conversation, memory, skill, or credential crawling.
- Kanban writes target a hardcoded **`executive-organization`** board. **Ryan has no such board** (mesh/desk/k2/arctic/proofmark/career/investing/joinsov).
- Fit check (live): Ryan runs **4 profiles** — `default` opus[1m] running, `orchestrator` deepseek-v4-flash, `worker` gpt-oss:120b, `local-experimental` — i.e. exactly the multi-profile shape this targets. Currently **0 user plugins installed**.
- No streaming (polls background job); one job per profile, up to 4 concurrent; images job-scoped and deleted in `finally`.

## 3. Takeaways
- The real idea is a **side channel**: a busy orchestrator thread should never be the only door to your other agents.
- **Assign task is an explicit toggle** — chat ≠ work item. That is Ryan's no-free-fire doctrine expressed as UI.
- Captured results settle **`blocked / needs_input`** for human verification instead of self-declaring done — same law as HUMAN=Ryan / GREEN-only-on-OK.
- Job identity is idempotent (`request_id` + idempotency key, lost-POST reconciliation, retention caps) — directly addresses orphan/duplicate dispatch pain.
- Quality is unusually disciplined for a 1-day-old community repo (SECURITY.md, third-party notices, published tests, labeled "conceptual artwork" on the hero) — but **macOS is unproven and it wants to write into HERMES_HOME**.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Per-profile side channel while orchestrator busy** | Reach `worker` / `orchestrator` profile without hijacking the default thread; one job per profile, concurrent across profiles | P1 | open |
| S2 | **Explicit assign-task gate** | Conversation never mints a kanban card unless deliberately toggled | P1 | open |
| S3 | **Settle as `blocked / needs_input`, never auto-done** | Agent-captured results land for Ryan verification, not GREEN | P1 | open |
| S4 | Idempotent job identity + lost-response reconciliation | `request_id`/idempotency key so a dropped POST neither orphans nor duplicates; bounded retention | P1 | open |
| S5 | Model picker lists only the profile's authed provider models | Reinforces SIG-20260808-02 S3 — no dead Spark/Ollama aliases | P2 | open |

**Primary steal:** S1 (per-profile side channel)

## 5. Do not
- **Do not run `python install.py` against `~/.t1000`** — prod HERMES_HOME; needs explicit Ryan OK and a non-prod home first (`--home <temp> --copy-only`).
- Do not let it create an `executive-organization` board — would fork the board scheme away from the mesh SoT.
- Do not accept a **second kanban writer** alongside the dispatcher (dual-writer law).
- Do not treat Windows-verified as macOS-verified.
- Do not treat this as official Nous — community project.

## 6. Next action
- [x] entry + INDEX + STEALS
- [x] kanban comment `t_c7f2534a` (Desktop Kanban plugin — same Desktop surface)
- [ ] no install (spike only on a throwaway `--home`, on Ryan OK)

## 7. Chat blurb
Agent Dock v0.2.1 = community Hermes Desktop plugin: talk straight to any profile while the orchestrator is busy, concurrent jobs, opt-in kanban. Steal the **side channel** + **explicit assign gate** + **settle-as-blocked**. Don't install into `~/.t1000` (Windows-verified only, wants an `executive-organization` board you don't have).
