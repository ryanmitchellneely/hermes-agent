---
id: PB-011
class: dispatch-routing
match:
  - "xAI token refresh failed"
  - "invalid_grant"
  - "no xAI OAuth token found"
  - "model_escalated"
verified: 2026-08-20
sources:
  - "mesh t_60b000b0 runs 997-1000+ (2026-08-20 12:36-12:49Z): sonnet->opus->grok ladder, 6 crashes"
  - "mesh t_18e69cec / t_feca325a same window -> routed to triage"
---

**Symptom:** a card crash-loops in ~90s attempts, two per model, with
`model_escalated` events walking a ladder (e.g. sonnet → opus[1m] → grok-4.5)
and every rung failing the same way at startup. Run logs show an auth error
(`invalid_grant`, `no xAI OAuth token found`) or the PB-007 clean-exit
signature. After the ladder exhausts, the card lands in triage/blocked.

**Mechanism (two compounding parts, both measured live):**

1. **The estimator sidecar overwrites explicit model pins.** A manual
   `set-model` verified on-card was replaced with the estimator's own
   suggestion before first dispatch. Pinning before unblock is NOT
   sufficient when the estimator re-stamps on ready.
2. **The failure ladder escalates by capability, not by health.** It walks
   to "bigger" lanes with zero liveness check, so when the dead thing is a
   provider (missing claude-acp token, dead xAI refresh token) the ladder
   visits every dead lane in turn and never tries a healthy local one.

**Diagnosis:** `hermes auth status <provider>` for each rung of the ladder;
check `task_events` for `model_escalated` entries; run log tail names the
auth failure.

**Fix (interim):** revive the dead provider first (see below), THEN re-arm.
Re-pinning to a live lane mid-loop loses to the estimator re-stamp.

**xAI re-auth on the VPS had a trap — CORRECTED 2026-08-20 ~16:00Z:** the
first diagnosis blamed daemon in-memory flushes; the REAL eraser was the
pre-flip Mac launchd agent `com.ryan.t1000-failover-heartbeat`, whose
`heartbeat.sh` rsynced the frozen Mac `auth.json` + `config.yaml` over
`/opt/t1000/home/` (killed the 2026-08-19 revival overnight and two same-day
fixes; proven by mtime forensics — every reverted file carried the Mac
original's mtime exactly). Both failover plists are retired `.mac-glass`
(same family as the PB-009 watchdog). With the heartbeat dead, re-auth works
with daemons running: `hermes auth add xai-oauth --type oauth --no-browser`
(device flow; an operator can run it via `ssh -tt` in the background and
hand the human just the URL+code), then prune the pool to the fresh entry
and **sync it into every `profiles/*/auth.json`** — workers read their own
profile store, not the root one (a passing root-store test proves nothing
about worker lanes). Test with `hermes -z ... -m grok` from a
t1000-readable cwd.

**Root fix (carded, mesh t_7af7daf9):** health-gate both the estimator's
suggestions and the escalation ladder's targets; neither may override an
explicit human pin.

**Don't:** keep re-pinning and re-unblocking against the estimator — each
round burns the failure budget and pushes the card toward triage.
