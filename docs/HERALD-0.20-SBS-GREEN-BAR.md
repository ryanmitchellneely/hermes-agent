# Herald 0.20 — SBS green bar (unpark gate)

**Card:** `mesh` `t_94708cc1`  
**Defined:** 2026-08-05  
**Purpose:** Exactly three objective pass/fail conditions that must ALL pass before Herald 0.20 cutover work may unpark.  
**Not this doc:** technical cutover checklist (`hermes doctor`, HA single-writer, cron tick, DM round-trip) — that runs *after* unpark, per `docs/T1000-KEVIN-AGENT-MESH-PLAN.md`.

**Doctrine:** client week (SBS) > agent week; reach utility > Herald tourism.  
**Separate human gate:** even when all three pass, **Ryan must explicitly unpark** the Herald park card (`t_2f43f830` or successor). Agents never self-unpark.

---

## Green bar (all three required)

### GB1 — Money tripwire not RED (invoice rail)

| | |
|---|---|
| **PASS when** | SOV-2026-001 is **SENT** on the operational send log, **and** the latest SBS tripwire board does **not** mark the invoice row RED. |
| **FAIL when** | SEND artifact still STAGED / payment block has `[FILL]`/`[PLACEHOLDER]`, **or** no SENT-LEDGER row with Status `SENT <date>`, **or** latest tripwires worst/invoice = RED for FILL/unsent. |
| **Check (commands / paths)** | 1. `~/Documents/sovereign-advisory/clients/sbs-david/stage1-invoice-SOV-2026-001-SEND.md` — header not "STAGED — DO NOT SEND"; no `[FILL]` in ACH block. 2. `…/SENT-LEDGER.md` — row for invoice SOV-2026-001 with `SENT YYYY-MM-DD`. 3. Newest `…/TRIPWIRES-YYYY-MM-DD.md` (or HEARTBEATS `system=sbs-tripwires`) — invoice tripwire ≠ RED. |
| **Why** | Portfolio freeze parks Herald until money rail is no longer the open fire. Unambiguous custody: ledger + tripwire, not vibes. |

### GB2 — Gate 1 commercial checkpoint resolved

| | |
|---|---|
| **PASS when** | Gate 1 (contracted Mon **2026-08-10 14:00 CT** or any re-scheduled successor on joinsov calendar) is **past**, **and** a written outcome exists: David pick among held menu lanes (**1a/1b/1c/1d** or named successor) **or** explicit STOP / defer with date. |
| **FAIL when** | Gate 1 still upcoming, RSVP/package still open-YELLOW without outcome, **or** no written pick/stop in case file. |
| **Check (commands / paths)** | 1. Calendar: Gate 1 event end &lt; now (joinsov). 2. Case file one of: newest runsheet / `FACTS.md` / `DELIVERY-RECORD.md` / Gate-1 pack AS-SENT — contains outcome line naming lane or STOP. 3. Latest tripwires: Gate-1 row not "needs package / decision open". |
| **Why** | Herald cutover must not compete with the Stage-1 money/menu decision. Outcome filed = commercial fork known. |

### GB3 — No hard SBS client meeting inside the cutover window

| | |
|---|---|
| **PASS when** | Looking forward **48 hours** from intended unpark/cutover start (America/Chicago): **zero** SBS-hard events with external guests (David / Todd / Ross / vendors) on joinsov calendar — Demo, Gate, working session, design review. |
| **FAIL when** | Any such event starts within the next 48h CT, **or** calendar cannot be read (treat as FAIL-closed). |
| **Check (commands / paths)** | 1. Google Calendar (joinsov) next 48h filter title/guests for SBS / Streamlined / David / Todd / Ross. 2. Cross-check latest `EMAIL-DIGEST-*-morning.md` + tripwires WATCH rows for same-day client holds. 3. Optional: Pulp calendar snapshot if fresh; if missing, use GCal directly — missing Pulp ≠ pass. |
| **Why** | Gateway reload / Herald cutover is mid-ops risk. No client-facing collision window. |

---

## How to score

```text
green_bar = GB1 AND GB2 AND GB3
unpark_allowed = green_bar AND ryan_explicit_unpark
```

- If any GB is FAIL → Herald stays **parked**. Do not start merge/cutover.
- If all GB PASS but no Ryan unpark → still parked (human ceremony).
- Technical green bar (doctor / HA / cron / DM) is a **downstream** checklist on the cutover card, not a substitute for this SBS bar.

## Snapshot at definition (2026-08-05 CT)

| Condition | Status | Evidence sketch |
|-----------|--------|-----------------|
| GB1 Money | **FAIL** | Invoice SEND still STAGED + FILL; tripwires worst=RED invoice +15 biz d; unpaid window open since 07-27 |
| GB2 Gate 1 | **FAIL** | Gate 1 still ahead Mon 2026-08-10 14:00; menu prices held, decision not taken |
| GB3 Quiet 48h | **FAIL** (as of Wed evening) | Demo #3 Fri 2026-08-07 14:00 inside any cutover started before then; Ross+Todd session was same-day |

**Ruling:** Herald 0.20 remains **parked**. Green bar not met.

## Re-score 2026-08-06 ~13:00 CT (hanging-work audit)

| Condition | Status | Evidence sketch |
|-----------|--------|-----------------|
| GB1 Money | **FAIL** | `stage1-invoice-SOV-2026-001-SEND.md` still **STAGED — DO NOT SEND** + ACH `[FILL]`; no SENT-LEDGER row for invoice; `TRIPWIRES-2026-08-06.md` invoice **RED +16 biz d** |
| GB2 Gate 1 | **FAIL** | Gate 1 still **Mon 2026-08-10 14:00 CT** (David+Todd accept / Ross tentative); prices HELD; package YELLOW (B names-only + TODD RULES); **no written 1a/1b/1c/1d or STOP** |
| GB3 Quiet 48h | **FAIL** | **Demo #3 Fri 2026-08-07 14:00 CT** (all four accepted) inside any cutover started now; Gate 1 Mon still in wider client window |

**Ruling:** stays **parked**. Next formal re-score: **Tue 2026-08-11** (day after Gate 1) or earlier if invoice SENT lands. Do **not** unpark during Demo #3 / Gate 1 week unless Ryan overrides doctrine.

## Review cadence (while parked)

| When | What |
|------|------|
| **Tue 2026-08-11** (day after Gate 1) | Re-score GB1–GB3 on mesh card comment; if still FAIL, set next review |
| **Fri REPLAN** each week | One-line green-bar score in mesh weekly triage |
| Early re-score OK | Any day invoice SENT lands (GB1 may flip without waiting for Tuesday) |

## Related

- Park card: mesh `t_2f43f830` (Herald 0.20 PARK)
- Portfolio freeze: `~/.t1000/kanban/seed-bodies/adv-freeze.md` / desk freeze decision card
- Upgrade posture (post-unpark): `docs/T1000-KEVIN-AGENT-MESH-PLAN.md` § Upgrade posture
- Mesh law: `mesh` weekly triage — Herald/Distillery only when SBS green + Ryan unparked
