# Fleet roadmap — 1-by-1 refresh + PM deep dive (2026-08-09)

Four read-only recon lanes + six product specs, all live-verified same day.
Full reports + specs: `~/Documents/T1000/docs/research/fleet-roadmap-2026-08-09/`.
Companion: `ROADMAP-DUAL-BOX-2026-08-09.md` (boxes/W-waves — unchanged, extended by this).

## The 1-by-1 (verdict · status · the one thing that matters)

| Build | Verdict | Status | The one thing |
|---|---|---|---|
| **Chamberlain** (K2) | INVEST | LIVE, all probes green | Most-shipped build in the fleet; Kevin's 2 decision cards aging 34h+ |
| **Mesh (kanban factory)** | INVEST | LIVE, 15.5% failure tax | t_3323c114's finished patch kills 58% of crashes — unreviewed |
| **DevBot** | INVEST | LIVE supervised; night armed | Queue EMPTY — job generation is the whole gap (spec ready) |
| **Teammate EA / Lori** | INVEST | DARK runtime, 80% merged | One stuck PR #4348 (rebase + root-tests) + uninstalled tick timer |
| **Distillery intake** | MAINTAIN→INVEST | LIVE faucet, zero drain | 161 drafts, 0 filed; review-agent spec ready; mass-stale 08-14 |
| **Juice** | MAINTAIN | LIVE | triage-digest FAILED today (1500s timeout on new --profile flag) |
| **Pulp** | MAINTAIN | LIVE, self-healing | Auth TTY ceremony by 08-28 (hold 08-18); panel counters 4d stale |
| **Herald** | MAINTAIN engine / PARK program | Engine serving | nemo_relay msg-loss fix stuck upstream (#81858); 19 dirty files on prod branch |
| **Student model** | MAINTAIN | LIVE, data-starved | Corpus 2/500 pointers; SECOND auth cliff 08-23 (live-capture) |
| **Popper / Labs** | MAINTAIN, cadence PARK-ish | Infra LIVE, research 6d dry | LAB-0024 crashed 2x; retry on repointed 120b = third-strike rule |
| **Buzz fleet** | MAINTAIN | LIVE, presence green | Roster env-driven; no per-agent "answered a real mention" probe |
| **Fleet cockpit** | MAINTAIN (fix-now flag) | LIVE, surfacing real alerts | Unversioned/off-repo; deploy_truth heartbeat never instrumented |
| **Content-lab council** | MAINTAIN | LIVE | One-judge "council"; passed veto deadline on t_d4ae1f59 unhandled |
| **Advisory intel** | MAINTAIN | LIVE, cleanest reviewed | Zero kanban visibility — only build with no board presence |

## Hard dates (one view — the thing nothing else cross-linked)
- **2026-08-14** — ~141 Distillery drafts flip stale in one batch (cosmetic by design; review agent + optional bootstrap batch address it)
- **2026-08-18** — calendar hold for Pulp auth TTY ceremony (Ryan)
- **2026-08-23** — student-model live-capture auth expires (Ryan, distinct from Pulp)
- **2026-08-28** — Pulp auth expires (hard cliff if 08-18 hold missed)

## New product specs (committed alongside this doc)
1. **Standings Router** — measurement-driven routing; capability probe = the instrument that would have caught the 08-08 ctx-floor rot. Pilot: non-agentic format lane.
2. **Distillery Review Agent** — clusters + pre-judged verdicts, 8/day batches, apply-on-approve only, cron born paused.
3. **DevBot Job Generation** — mechanical admission filter, draft-only output, runner's approved-only gate = safety spine.
4. **Local-First K2 migration** — shadow pilot on inbox_thread_classification via the existing ADR-057/Finn apparatus; policy enum extended, never weakened. ⚠️ surfaced live token exposure → rotation card (Ryan).
5. **Worker Reliability Layer** — two mechanical fixes ≈ whole 15.5% crash class + digest reliability section.
6. **Chip-ified Human Gates** — mesh HUMAN cards → Buzz decision chips (Chamberlain machinery), react-to-ack; Kevin proposal first.

## Sequencing recommendation (this week)
1. **Worker reliability WR-1/WR-2** (unblocks everything; fixes are sitting there)
2. **Distillery review agent** (beats the queue's usefulness decay; C1 decision is small)
3. **DevBot job-gen** (feeds the armed night cron; 2 rulings then mechanical)
4. **Standings Router SR-1/SR-2** (read-only components; no routing changes yet)
5. **Local-first C1/C2 + token rotation** (K2 lane, PR discipline; token rotation FIRST)
6. **Chip gates** (after Kevin sees digest #1 — the proposal rides the same channel)

Fix-now singletons regardless of the above: juice-triage-digest timeout, kanban-status-health
cron registration, Teammate EA PR #4348 rebase, LAB-0024 third-strike retry, advisory-intel
board visibility.
