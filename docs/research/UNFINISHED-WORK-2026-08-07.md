# Unfinished work ledger — agent / mesh / model (2026-08-07)

**Scope for this file:** T1000 desk, Claude ACP, DevBot, EA shell, inference/student, signal-log, estate-mesh instruments, dirty **agent** trees.  

**Out of scope here (desk owns it — not dropped, just not this continuity pass):** SBS / David / Gate-1 / invoice SOV-2026-001 / sovereign-advisory client dirt. See board **`desk`** + tripwires if you need that lane.

**Profile:** `HERMES_HOME=~/.t1000`  
**Doc corpus map:** `~/Documents/T1000/docs/research/AGENT-MODEL-DOC-INDEX.md`  
**Mesh REFs:** `t_2b02cc37` (this ledger) · `t_043bcb33` (doc index)  
**Home copy:** `~/.t1000/kanban/UNFINISHED-WORK-2026-08-07.md`  
**Git:** `T1000/docs/research/UNFINISHED-WORK-2026-08-07.md` on `product/ryan/herald-0.20-cutover`

---

## P0 — Don’t lose (active agent engineering)

| Item | Where | Board | Next |
|------|--------|-------|------|
| **EA one-queue + interrupt ≤3/day** | [#4348](https://github.com/joinsov/kevin-real-estate-tools/pull/4348) · worktree `teammate-ea-one-queue` clean | `t_ced7480f` · parent `t_4e9cc69a` | **root-tests FAIL** (pytest green) → fix → merge → then nudges `t_a02c40c1` |
| **DevBot selftest** | [#4352](https://github.com/joinsov/kevin-real-estate-tools/pull/4352) checks **green** | pairs `t_d11fa676` | Merge when you want; refresh stale SPRINT.md (#4350 already **merged**) |
| **Claude ACP Max lane** | T1000 `ryan/herald-0.20-cutover` (pushed) | `t_e863f674` **done** | Picker refresh after Desktop thrash; Grok stays default |
| **Research corpus** (signal-log, plans dual-write, indexes) | commits `00674e8c6` + `fe5426300` **pushed** | `t_498126c6` done | Done |

### EA Phase 1 PR map

| PR | State |
|----|--------|
| #4346 #4347 #4349 #4350 #4351 | **MERGED** |
| #4348 | **OPEN** — one-queue + interrupt (root-tests red) |
| #4352 | **OPEN** — DevBot selftest (green) |

---

## P1 — Tracked hangers (agent/mesh; not free-fire)

| Item | Board / files | Notes |
|------|----------------|-------|
| Pulp + fleet blueprint rescue + tape | `t_f4cd0a55` | HUMAN; branches `ryan/juice-buzz-acp-shim` / `juice-wrap-untrusted-p3` still on sov-consulting |
| Juice tape append | `t_499a5a85` todo | Child of rescue |
| LAB-0015 / R5 / registry decision | `t_43bef393` | HUMAN estate sit |
| Estate ledger + silence-kills | `t_92726064` todo | After R5 |
| CoS engine / fold Pulp role | `t_05ed9141` · `t_72bfb2f6` | Crucible S3 |
| Spark inference **B17** | plan + `t_99c5d345` | Kickoff phrase only |
| Mini student **B18** | `~/Documents/student-lab` git + `t_848b57b7` | Golden 30→100+ |
| Kevin Spark model pack | `t_d11fa676` | Ryan `:11435` ≠ Kevin box |
| Desktop shell rebuild vs engine 0.20 | `t_33b54172` | Post-thrash; not Herald tourism |
| Desktop Kanban plugin | `t_c7f2534a` | Settings → Plugins |
| Pulp residuals / freshness | `t_9bfcbb2f` · `t_fb05b715` | Polish; VPS-only |
| Pulp auth renew | `t_f18d325e` | Hold **Tue 08-18**; cliff **08-28** |
| Herald fleet park (doctrine) | `t_2f43f830` | Engine already 0.20; park ≠ rollback |
| K2 harness INDEX conflict markers | k2 `t_8e1dee0d` | `AGENT-HARNESS-RESEARCH-INDEX.md` |
| Local-model scoreboard lane | `t_d754cc37` todo | |
| LAB-0024 LoRA register | `t_1edac8a4` todo | After panel decisions |
| Distillery intake tranche | `t_048f0c5c` | Recon-first; no rebuild |

---

## P2 — Dirty trees that can lose **agent** work

| Repo | State | Risk for *this* scope |
|------|--------|------------------------|
| **T1000** | clean vs product after push; ignore `.omc/` + package-lock | Low |
| **kevin-real-estate-tools** | coord checkout behind main; **5 stashes** | Stashes rot — list before drop |
| **EA worktrees** | dirty=0 | OK — PR is SoT |
| **k2-worktrees/two-unit-model** | ~4378 dirty on main | Dangerous noise — don’t commit blind |
| **sovereign-consulting** | untracked juice tools / ai-briefs / estate already landed PR | Medium (fleet blueprint still on branches) |
| **student-lab** | local git only; `?? bin/` | No remote yet |
| **proofmark** | behind 20 | Low for agent continuity |
| **investing** | dirty + no upstream | Out of agent scope; optional backup |
| ~~sovereign-advisory SBS~~ | dirty ~70 | **Desk lane — ignore in this ledger** |

---

## P3 — Aged open PRs (GitHub keeps them; not this week’s brain)

Focus **#4348 + #4352**. Rest still exist if needed:

- Arctic/legal cluster #4275–#4281 · phone #2872 · drafts #3790/#3755 · etc.  
- `gh pr list --repo joinsov/kevin-real-estate-tools --author @me --state open`

---

## Sessions → captured (agent trails)

| Session | Trail | Captured |
|---------|--------|----------|
| @session:default/20260807_211133_27c9df | Crash + continuity | this ledger + mesh |
| @session:default/20260807_153122_6eb7be | EA → #4348 | EA cards |
| @session:default/20260807_153211_3806ee | Claude ACP + DevBot | ACP done · #4352 · Kevin card |
| @session:default/20260807_194859_2cd9dd | Fleet visual / Kanban UI | `t_c7f2534a` |
| @session:default/20260806_053426_f5024759 | Signal log | files pushed |
| `20260807_104356_af0582` | Dead xAI 403 | yoinked into EA recovery |

Don’t reopen zombie 403 tabs.

---

## Done — don’t reopen

- Herald Path A gateway/HB residual finish  
- Distillery P0–P3 ports  
- EA Phase 0 PRs  
- DevBot #4350  
- Cron host+model audit `t_566bf5c1`  
- Desktop thrash ops (lock, :9119, reasoning_overrides)  
- Signal-log + plan dual-write + doc index **pushed**

---

## Ryan checklist (agent continuity only)

1. **#4348** — fix root-tests → merge EA  
2. **#4352** — merge DevBot selftest when convenient  
3. Optional: Desktop Kanban plugin; Kevin Spark pull when he confirms  
4. Optional: B17/B18 only on explicit kickoff  
5. Ignore SBS/David/Gate/invoice **in this file** — desk board owns that  

---

*Refocused 2026-08-07: Dave/SBS de-scoped from P0 for agent continuity.*
