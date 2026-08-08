# Agent + model documentation index (T1000 estate)

**Purpose:** one cold-start map for the “zillion docs” of agent/harness/model work so chat sessions don’t become the SoT.  
**Owner profile:** `HERMES_HOME=~/.t1000`  
**Written:** 2026-08-07 ~21:40 CT (hanging-work audit pickup)  
**Board home:** mesh card `t_043bcb33` (filled after create) — title **REF: Agent+model doc corpus index**

**Doctrine:** docs live in **repo homes**; kanban tracks **outcomes**; skills hold **procedures**; `~/.hermes/plans` holds **deferred experiment plans**. Do not duplicate full essays onto cards.

---
**Dual-write:** also `~/.t1000/kanban/AGENT-MODEL-DOC-INDEX.md` (kanban cold-start). Prefer this repo path once committed.


## 0. How to use this

| You need… | Open first |
|-----------|------------|
| “What model lanes exist on my desk?” | skill **`t1000-model-desk`** + `docs/CLAUDE-ACP-LANE.md` |
| “What’s the local/Spark/MBP fleet story?” | skill **`local-inference-fleet`** |
| “Spark tok/s / side-door / spec-dec plan?” | plan B17 + mesh `t_99c5d345` |
| “Student model / mini distill?” | plan B18 + `~/Documents/student-lab/docs/` + `t_848b57b7` |
| “DevBot / Kevin Spark?” | `kevin-real-estate-tools/docs/agent-coordination/devbot/` + `t_d11fa676` |
| “X/repo flex → steals?” | `T1000/docs/research/signal-log/` + skill **`signal-log`** |
| “Compare other harnesses (Prime/OMH)?” | skill **`agent-harness-compare`** + K2 `AGENT-HARNESS-RESEARCH-INDEX.md` (Distillery lab owns deep studies) |
| “Teammate EA / Lori?” | K2 `docs/build-plans/2026-08-07-teammate-ea*.md` + mesh `t_4e9cc69a` |
| “Estate / frames / CoS philosophy?” | `sovereign-consulting/.../2026-08-07-estate-crucible/` |
| “Whole portfolio boards?” | `~/.t1000/kanban/PORTFOLIO.md` |

---

## 1. Skills (procedural memory — load these, don’t re-research)

| Skill | Path under `~/.t1000/skills/` | Owns |
|-------|------------------------------|------|
| `t1000-model-desk` | `software-development/t1000-model-desk/` | Grok default, Claude ACP Path C, locals, aliases, picker |
| `local-inference-fleet` | `software-development/local-inference-fleet/` | MBP/Spark/DevBot roles, session deltas 08-07, router notes |
| `t1000-spark-tools` | `software-development/t1000-spark-tools/` | Spark reach + inference engineering refs |
| `agent-harness-compare` | `software-development/agent-harness-compare/` | Prime/etc pattern compare (not install) |
| `signal-log` | `research/signal-log/` | Mechanical URL→entry→STEALS flow |
| `k2-devbot` | `software-development/k2-devbot/` | DevBot grind loop ops |
| `k2-handlers-pr-ship` | `software-development/k2-handlers-pr-ship/` | EA/handler PR ship gates |
| `t1000-hermes-ops` | `software-development/t1000-hermes-ops/` | Desk ops umbrella (kanban view, Herald, Pulp eyes) |
| `t1000-gateway-ha` | `software-development/t1000-gateway-ha/` | HA / outside reload |

Key skill refs (already on disk):

- `t1000-model-desk/references/claude-acp-lane.md`
- `t1000-model-desk/references/multi-lane-model-desk.md`
- `local-inference-fleet/references/devbot-router-2026-08-07.md`
- `local-inference-fleet/references/fleet-session-deltas-2026-08-07.md`
- `local-inference-fleet/references/shipped-hermes-lanes.md`
- `local-inference-fleet/references/research-watch-inference-2026-08.md`
- `agent-harness-compare/references/prime-agent-2026-08.md`

---

## 2. Deferred experiment plans (`~/.hermes/plans/`)

| Plan file | Roadmap | Mesh | Status |
|-----------|---------|------|--------|
| `2026-08-06_222342-spark-inference-experiments.md` | **B17** | `t_99c5d345` **blocked** (kickoff phrase only) | Plan live; C2 concurrency from McNab signal wired |
| `2026-08-07_074000-mac-mini-student-model.md` | **B18** | `t_848b57b7` **blocked** | Phase 0 done; golden set saturation blocker |
| `2026-08-07_182701-k2-devbot-local-spark.md` | DevBot | `t_d11fa676` **blocked** HUMAN Kevin | MBP dogfood green; Kevin Spark not proven |

Also T1000 tree plans (repo):

- `~/Documents/T1000/docs/plans/2026-08-06-calendar-write-lane.md`
- `~/Documents/T1000/docs/plans/2026-07-13-codey-to-t1000-migration.md`

Roadmap SoT rows: `~/Documents/sovereign-advisory/desk/AUTOMATION-ROADMAP.md` (B17/B18).

---

## 3. T1000 repo docs (engine / desk)

| Path | Git | Role |
|------|-----|------|
| `docs/CLAUDE-ACP-LANE.md` | **committed** on `ryan/herald-0.20-cutover` | Operator SoT for Max ACP lane |
| `docs/T1000-KEVIN-AGENT-MESH-PLAN.md` | committed | Mesh plan with Kevin |
| `docs/HERALD-0.20-SBS-GREEN-BAR.md` | committed | GB1–3 matrix |
| `docs/research/signal-log/**` | **UNCOMMITTED** | Signal intake SoT (README, INDEX, STEALS, entries SIG-*) |
| `scripts/signal_log_new.py` | **UNCOMMITTED** | Scaffold |
| `~/.t1000/kanban/HERALD-CUTOVER-2026-08-06.md` | home only | Cutover day notes |
| `~/.t1000/cache/t1000-distillery-port-brief.md` | cache | Claude Distillery port brief copy |

**Mesh for uncommitted signal-log:** `t_498126c6` (blocked — Ryan OK to commit).

**Mesh for ACP ship:** `t_e863f674` **done**.

---

## 4. Student lab (NOT T1000 tree — contested)

Home: `~/Documents/student-lab/docs/`

| File | Role |
|------|------|
| `README.md` / `RUNBOOK.md` / `STATUS.md` | Ops |
| `GOLDEN-CANDIDATES.md` / `CALIBRATION.md` / `PROMPT-CONFLICTS.md` | Eval design |
| `golden_set_research_v2.json` | Golden set artifact |
| `eval-history/` | Runs |

Tied to B18 / `t_848b57b7`. Crons: student capture/watch/eval under `~/.t1000/cron`.

---

## 5. K2 / Kevin lane (product + EA + DevBot)

### DevBot (on main)
`~/Documents/kevin-real-estate-tools/docs/agent-coordination/devbot/`

CHARTER · MODEL-PACK · KEVIN-SPARK-SETUP · SPRINT · QUEUE · CODEBOOK · EVAL · RUNBOOK-MBP · SPARK-CODER-NOTE · STATUS · TROUBLESHOOT · DEVBOT-SMOKE · `jobs/`

KB: `docs/knowledge-base/devbot-stack-canon.md`, `devbot-runtime.md`  
Inbox: `2067-devbot-spark-model-pack.md`

### Teammate EA
| Path | Role |
|------|------|
| `docs/build-plans/2026-08-07-teammate-ea.md` | Full build plan |
| `docs/build-plans/2026-08-07-teammate-ea-phase0-recon.md` | Phase 0 recon |
| `docs/build-plans/2026-08-07-teammate-ea-hermes-delta-gate.md` | Delta freeze |
| inbox 2058 / 2061 / 174 | Ratify + monitor |
| claims 2062–2067 | PR claims |

**Mesh:** Phase 0 `t_5940b0e2` done · Phase 1 shell `t_4e9cc69a` todo · one-queue `t_ced7480f` blocked on **PR #4348**.

### Harness research (K2 Distillery lab — Claude/Kevin owns product Distillery)
- `docs/research/AGENT-HARNESS-RESEARCH-INDEX.md` ← **has merge conflict markers HEAD/=======** (hygiene!)
- `docs/research/agent-harness-lab/*` (Prime, OpenClaw, LangGraph, Shepherd, bb, …)

**Do not rebuild Distillery product in T1000.** T1000 only ports proven patterns (`distillery-native-ports` skill ref). Mesh: `t_ecf2e67f` done intake; `t_048f0c5c` blocked for next tranche.

---

## 6. Estate crucible (philosophy + EA grounded design)

`~/Documents/sovereign-consulting/docs/research/2026-08-07-estate-crucible/`

| Doc | Role |
|-----|------|
| `CRUCIBLE-2026-08-07-agent-estate-and-frames.md` | Estate frames |
| `CRUCIBLE-ADDENDUM-the-user-agent-and-the-CoS.md` | User/agent/CoS |
| `DESIGN-k2-teammate-ea-grounded.md` | EA design grounded |
| `ROADMAP-2026-08-07-estate-program.md` | Program roadmap |
| `recon/01-fleet.md` … `04-models.md` + harness recon | Recon pack |

**Landed:** mesh `t_8692acc7` done (PR #73).  
**Still HUMAN:** `t_f4cd0a55` rescue Pulp+fleet blueprint branches → main + tape append.

Related mesh todos from crucible sprint: `t_92726064` estate ledger · `t_43bef393` LAB-0015/R5 decision · `t_05ed9141` CoS engine · `t_72bfb2f6` fold Pulp role · `t_1edac8a4` LAB-0024.

---

## 7. Signal log entries (research → steals)

Under `T1000/docs/research/signal-log/entries/` (uncommitted):

| ID | Title | Rank | Wire |
|----|-------|------|------|
| SIG-20260806-01 | Latent Space inference eng | P0 | B17 plan |
| SIG-20260807-01 | kimi-k3-in-c | watch | none |
| SIG-20260807-02 | Prime Agent | P1 | skill agent-harness-compare |
| SIG-20260807-03 | McNab 32× Spark | P0 | B17 Phase C2 |
| SIG-20260807-04 | Oh-My-Hermes | P1 | router verbs open |

Rollup: `STEALS.md` · process: `README.md`.

---

## 8. AI tastemaker briefs (consulting)

`~/Documents/sovereign-consulting/docs/research/ai-briefs/` (many untracked on branch)  
Index there; Sun/Wed cron path. Not mesh free-fire.

---

## 9. Hygiene / known dirt on the doc pile

| Item | Action |
|------|--------|
| `T1000/docs/research/signal-log/**` uncommitted | `t_498126c6` — commit when Ryan OK |
| `AGENT-HARNESS-RESEARCH-INDEX.md` **merge conflict markers** | File on **k2** board (not mesh product) — fix before trust |
| `PORTFOLIO.md` priority table stale vs board | refreshed same night as this index |
| sovereign-consulting estate branch dirty extras | `t_f4cd0a55` human push |
| student-lab outside T1000 git | intentional (B18) |
| `~/.hermes/plans` not in T1000 git | intentional; dual-note AUTOMATION-ROADMAP |
| K2 Distillery lab sprawl | Claude Desktop lane — do not mirror into T1000 |

---

## 10. Mesh cards that *are* the doc program (don’t recreate)

| Id | Status | Doc program |
|----|--------|-------------|
| `t_8692acc7` | done | Estate crucible land |
| `t_e863f674` | done | Claude ACP docs+code |
| `t_ecf2e67f` | done | Distillery port brief intake |
| `t_5bc3916b` | done | Hermes Delta pass |
| `t_566bf5c1` | done | Cron model audit writeup |
| `t_99c5d345` | blocked | B17 inference plan |
| `t_848b57b7` | blocked | B18 student/mini |
| `t_d11fa676` | blocked | Kevin Spark + DevBot residual |
| `t_498126c6` | blocked | Commit signal-log |
| `t_4e9cc69a` | todo | EA Phase 1 (points at build-plans) |
| `t_048f0c5c` | blocked | Next Distillery intake tranche |
| `t_f4cd0a55` | blocked | Pulp/fleet blueprint rescue |
| `t_05ed9141` | blocked | CoS engine (crucible S3) |
| `t_92726064` | todo | Estate ledger instrument |

---

## 11. What this index is *not*

- Not a substitute for reading the linked SoT files  
- Not permission to free-fire B17/B18/Distillery rebuild  
- Not the K2 product Distillery running doc (that’s `agent-harness-lab` under kevin-real-estate-tools)  
- Not SBS client docs (desk board / sovereign-advisory clients)

---

*End index. Update this file when a new plan/skill/major research pack lands; add one mesh comment on the REF card.*
