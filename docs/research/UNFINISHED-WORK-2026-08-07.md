# Unfinished work ledger — 2026-08-07 night

**Purpose:** single file so unfinished work is not only in chat memory.  
**Profile:** `HERMES_HOME=~/.t1000`  
**Companion index (docs):** `~/Documents/T1000/docs/research/AGENT-MODEL-DOC-INDEX.md`  
**Mesh REF:** `t_043bcb33` (doc corpus) · this file: `~/.t1000/kanban/UNFINISHED-WORK-2026-08-07.md`

**How to use:** Top = must not lose. Bottom = park/noise. Update when something lands or dies.

---

## P0 — Active engineering (can lose if abandoned)

| Item | Where | Board | Next action |
|------|--------|-------|-------------|
| **EA one-queue + interrupt budget** | PR [#4348](https://github.com/joinsov/kevin-real-estate-tools/pull/4348) · worktree clean | mesh `t_ced7480f` · `t_4e9cc69a` | **root-tests FAIL** (pytest pass). Fix root-tests → merge → `t_a02c40c1` |
| **DevBot selftest PR** | [#4352](https://github.com/joinsov/kevin-real-estate-tools/pull/4352) checks **green** | mesh `t_d11fa676` | Merge when ready; refresh SPRINT.md (#4350 already merged) |
| **T1000 research corpus** | commit `00674e8c6` **pushed** → `product/ryan/herald-0.20-cutover` | `t_498126c6` done | Done 2026-08-07 |
| **Claude ACP lane** | commits on herald branch (shipped code) | `t_e863f674` done | Keep branch backed up / product remote; Desktop thrash may need picker refresh |
| **Gate-1 package (Mon 08-10)** | ADV client files + desk cards | desk `t_b6db2490` ready · money `t_9f34311a` | Human package freeze; **no invoice on Gate thread** |

### Phase 1 EA PR map (do not re-open Phase 0)

| PR | State |
|----|--------|
| #4346 #4347 #4349 #4350 #4351 | **MERGED** |
| #4348 | **OPEN** — one-queue + interrupt ≤3/day |
| #4352 | **OPEN** — DevBot selftest |

---

## P1 — Real hangers (tracked; not free-fire)

| Item | Board / files | Notes |
|------|----------------|-------|
| Pulp + fleet blueprint rescue + tape append | mesh `t_f4cd0a55` | HUMAN push from juice branches → sov-consulting main |
| Juice tape append child | `t_499a5a85` todo | Depends human rescue |
| LAB-0015 / R5 / registry decision | `t_43bef393` | HUMAN ~2h sit |
| Estate ledger + silence-kills | `t_92726064` todo | After R5 decision |
| CoS engine / fold Pulp role | `t_05ed9141` · `t_72bfb2f6` | Blocked/todo — crucible S3 |
| Spark inference B17 | plan + `t_99c5d345` | Kickoff phrase only |
| Mini student B18 | `student-lab` git + `t_848b57b7` | Golden set 30→100+ blocker |
| Kevin Spark pull | `t_d11fa676` | Ryan Spark ≠ Kevin |
| Desktop shell rebuild 0.20 | `t_33b54172` | After thrash; not tourism |
| Desktop Kanban plugin enable | `t_c7f2534a` | HUMAN Settings→Plugins |
| Signal-log / plans | **files committed** T1000 | Dual-write `docs/research` + `docs/plans` |
| Pulp residuals polish | `t_9bfcbb2f` · `t_fb05b715` review-req | VPS freshness voice may be done pending eyes |
| Pulp auth renew | `t_f18d325e` | Cal hold **Tue 08-18**; cliff **08-28** |
| Herald park | `t_2f43f830` | GB1 fail invoice; Gate1 Mon |
| Invoice SOV-2026-001 | desk `t_9f34311a` | FILL Wells → Ryan send |
| K2 harness INDEX conflict markers | k2 `t_8e1dee0d` | `AGENT-HARNESS-RESEARCH-INDEX.md` |
| Local-model scoreboard migration | `t_d754cc37` todo | Lane polish |
| LAB-0024 LoRA register | `t_1edac8a4` todo | After estate/panel decisions |

---

## P2 — Dirty trees (work exists on disk; risk of loss)

| Repo | State | Risk |
|------|--------|------|
| **T1000** | ahead 1 (docs) after push 0; dirty `package-lock` + `.omc/` ignore | Low if pushed |
| **sovereign-advisory** | main dirty **~70** (SBS tripwires, digests, desk, crucible) | **HIGH** client week — commit packs |
| **sovereign-consulting** | branch clean vs origin; **??** ai-briefs, competitive-intel, desk/, juice tools | Medium — untracked research |
| **investing** | main dirty **34**, **no upstream** | Medium-high private stream |
| **proofmark** | behind 20 + untracked docs | Pull before new work |
| **kevin-real-estate-tools** | behind main 8 on coord branch; **5 stashes** | Stashes can rot |
| **student-lab** | local git only, `?? bin/` | No remote yet |
| **k2-worktrees/two-unit-model** | **dirty ~4378** on main | **Dangerous** — do not commit blind; inspect or reset intentionally |
| EA worktrees (one-queue etc.) | dirty=0 | OK — PR is SoT |
| T1000 stash | `wip after archive snapshot` | Review before drop |

---

## P3 — Open PR backlog (K2 — not lost, but aged)

Active Ryan focus this week should stay **#4348 + #4352 + Gate-1**. Older open PRs still on GitHub (not deleted):

- Arctic/legal pack cluster: #4275–#4281 (many pair with k2 todo cards)
- Phone loop #2872, session-start #3638, mirror #4187, etc.
- Drafts: #3790 Buzz crucible, #3755 briefs
- Claude-authored still open: #4040, #3974

Full list: `gh pr list --repo joinsov/kevin-real-estate-tools --author @me --state open`

---

## Sessions (interrupted — history intact; don’t reopen zombies)

| Session | Unfinished trail | Captured? |
|---------|------------------|-----------|
| @session:default/20260807_211133_27c9df | Crash + hanging audit + docs land | this ledger + mesh |
| @session:default/20260807_153122_6eb7be | EA Phase 1 → #4348 | mesh EA cards |
| @session:default/20260807_153211_3806ee | Claude ACP + DevBot | done ACP · #4352 · Kevin card |
| @session:default/20260807_194859_2cd9dd | Fleet visual / Kanban plugin | `t_c7f2534a` |
| @session:default/20260806_053426_f5024759 | Signal log | files committed |
| `20260807_104356_af0582` | Dead Class A 403 | recovered in EA session |

Prefer **this chat** or fresh tabs; old 403 tabs are zombie lineage.

---

## Explicitly NOT unfinished (don’t reopen)

- Herald engine Path A cutover residual gateway finish — done  
- Distillery P0–P3 native ports — shipped  
- Phase 0 EA spine PRs — merged  
- DevBot #4350 scripts — merged  
- Cron fleet = Mac + grok audit — done `t_566bf5c1`  
- Desktop thrash ops fixes (lock, :9119, reasoning_overrides) — done  

---

## Ryan checklist (minimal)

1. Confirm T1000 docs **pushed** to product remote  
2. **#4348** CI green + merge when ready (EA)  
3. **#4352** DevBot selftest  
4. **sovereign-advisory** commit/pack SBS dirt before Mon Gate  
5. **Gate-1** package freeze (`t_b6db2490`) — no money on thread  
6. Optional: enable Desktop Kanban plugin; ignore two-unit-model dirt until intentional  
7. Optional: set upstream or backup **investing** repo  

---

## File pointers

| File | Role |
|------|------|
| `~/.t1000/kanban/UNFINISHED-WORK-2026-08-07.md` | This ledger |
| `~/.t1000/kanban/AGENT-MODEL-DOC-INDEX.md` | Doc corpus map |
| `~/Documents/T1000/docs/research/AGENT-MODEL-DOC-INDEX.md` | Same in git |
| `~/.t1000/kanban/PORTFOLIO.md` | Board portfolio |
| `~/Documents/sovereign-advisory/desk/AUTOMATION-ROADMAP.md` | B17/B18 |

*Generated 2026-08-07 hanging-work continuity pass.*
