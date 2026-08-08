# K2 DevBot (Local OSS on Kevin Spark) — Implementation Plan

> **Status 2026-08-07:** MBP dogfood **bootstrap landed** in KRT working tree (charter, jobs, scripts, KB pages, `~/.devbot-test`). First job `db-0001` ran propose via **gpt-oss:120b@127.0.0.1:11435**. Chunker fixed; index ~1.3k chunks. Night cron still off. Commit when ready on a clean `ryan/devbot-*` branch (primary tree was dirty — files are new/untracked-friendly).
>
> **For Hermes:** Prefer subagent-driven-development for later phases.

**Goal:** Stand up a **shared K2 DevBot** — overnight/after-hours engineering worker that knows the estate, grounds answers in research + live repo fact, operates Distillery *outputs* and the broken-shit backlog, and only ships work Ryan and Kevin have approved — running as a **local agent on Kevin’s Spark** on **open-source models** (no Codex; no cloud-required path for the grinder core).

**Architecture:** DevBot is a **role + runtime + knowledge plane**, not a third PM desk.  
- **Runtime:** Hermes-class agent (or thin harness) on **Kevin Spark**, model = OSS reasoner (default target: `gpt-oss:120b` or successor on Spark Ollama/vLLM).  
- **Knowledge:** Compiled desk/K2 wiki + research corpus index + live tools (git/rg/read) — **not** fine-tune-first.  
- **Control:** Approved job cards only; two-unit fences (`ryan/*` / `kevin/*` / `shared/*`); propose-PR default; dual human gate for shared/send/cross-lane.  
- **Distillery:** Research/tastemaker **feeds cards**; DevBot does not own ADR product lanes on Claude/K2.

**Tech stack (target):**
- Host **prod:** **Kevin Spark** (overnight grinder SLA)
- Host **dev/test:** **Ryan MBP** (dogfood loop, schema, tools, small-model path) — see §3.0
- Model prod: OSS reasoner (`gpt-oss:120b` or pinned successor on Spark)
- Model test on MBP: whatever is warm/local (e.g. `qwen3-coder:30b`, Hermes 36B, or tunnel to Spark `:11435`) — **not** a second production 120B copy required on MBP
- Embed: `nomic-embed-text` (MBP already has it; fine for test; Spark for yellow prod)
- Agent: Hermes profile `devbot` (same code path both hosts; different `HERMES_HOME` / endpoint)
- Repo SoT: `kevin-real-estate-tools` + allowlisted satellites
- Research SoT: `docs/research/**`, deep-campaign packs, ADRs, Distillery briefs
- Queue: in-repo job cards (preferred) or kanban — Phase 0 pick
- CI/review: KRT gates; `gh` from runner host

---

## 0. Constraints & non-goals (lock these)

### Hard constraints
1. **Codex is gone** — no Buzz `#codex-build` / hermes codey / OpenAI Codex as implementer. Replacement = **local OSS agent on Kevin Spark**.
2. **Two-unit law stays** — no joint PM product; no DevBot owning both humans’ backlogs as babysitter. Shared = **jobs + doctrine + CI**, not shared write identity stomping lanes.
3. **No send / Sierra prod / customer mutation** without explicit human OK (same as desk rules).
4. **Grounding law:** claims about stack, ability, or tradeoffs must cite **research corpus page, ADR, AGENTS/REPO-MAP, or live file path**. If uncited → label `confidence: low` and search before asserting.
5. **Privacy dial:** Spark prod = yellow default. MBP test may use green only for *human-supervised* dogfood, never as silent cloud fallback for the night runner.
6. **Subscription/API keys** — no Anthropic/OpenAI key fallbacks for the grinder path (Ryan cost doctrine). Cloud only if humans explicitly escalate a single hard task.
7. **Host promotion:** MBP proves loop; Kevin Spark is the only **after-hours** runner until both humans OK otherwise. MBP must not silently steal overnight jobs.

### Non-goals (v1)
- Replacing Ryan Hermes desk or Kevin’s interactive Claude unit
- Rebuilding Distillery product / ADR-064 inside T1000
- Full-repo fine-tune of 120B as primary knowledge store
- Unsupervised merge to `main` on shared/send paths
- Lori Teammate EA scope creep

---

## 1. Current context (what exists)

| Asset | Role vs DevBot |
|--------|----------------|
| KRT `AGENTS.md` / lanes / merge doctrine | **Contract** DevBot must obey |
| `docs/research/**` + deep-campaign playbook | **Research corpus** to ground tradeoffs |
| Distillery (briefs + pattern ports) | **Intake**, not runtime |
| Ryan unit Hermes / T1000 | Front door for Ryan; may *file* jobs, not run overnight grinder |
| Kevin unit (Claude interactive) | Peer; ratifies product; reviews |
| Spark + `gpt-oss:120b` | **Prod compute** (Kevin’s box) |
| Ryan MBP Ollama shelf | **Test/dogfood** — nomic embed + coder/36B; optional tunnel to Spark 120B |
| Desk wiki / llm-wiki skill | **To build** knowledge compile |
| nomic-embed | **Wire on MBP first**, mirror index to Spark for prod |
| Prior Codex night lane | **Retired** — patterns (inbox-for-implementer, PR-only) reusable under new runtime |

---

## 2. Target capability model

### 2.1 What DevBot *is*
Overnight / after-hours **engineering worker** that:
1. Pulls next **approved** job card  
2. Grounds plan in research + REPO-MAP + live code  
3. Implements on correct branch fence in isolated worktree  
4. Runs targeted tests  
5. Opens PR (default) or stops at proposal patch  
6. Reports: citations, tradeoff rationale, risk, what it did **not** do  

### 2.2 What it must *know* (knowledge planes)

| Plane | Content | Mechanism |
|-------|---------|-----------|
| **A. Always-on** | AGENTS.md, REPO-MAP, stack table, hard floors, DevBot SOUL | Inject every turn |
| **B. Compiled wiki** | Systems, services, tradeoff pages, “why not Redis”, deploy topology | llm-wiki on Spark-visible path |
| **C. Research corpus** | `docs/research/**`, crucibles, ADRs, Distillery briefs | Index + mandatory retrieve-before-architect |
| **D. Live repo** | Current code, CI, git history | Tools only (rg/read/gh) |
| **E. Jobs / backlog** | Approved cards, broken-shit, Distillery residuals | Queue SoT |
| **F. Optional later** | LoRA house style | Only after A–E work |

### 2.3 Grounding protocol (every non-trivial turn)

```text
1. Retrieve: research + wiki + REPO-MAP hits for the task keywords
2. Quote/cite: path or page id in the working plan
3. Tradeoff block: options considered → chosen → rejected-with-reason
4. If research silent: say so; fall back to live code + AGENTS stack defaults
5. Never invent stack alternatives (AGENTS: flag before writing off-stack)
```

Tool sketch (names illustrative):
- `research_search(q)` → top chunks from `docs/research` + wiki  
- `stack_canon()` → REPO-MAP + AGENTS stack section  
- `repo_search` / `read_file` / `run_tests` / `gh_pr`  

### 2.4 Autonomy levels (card field)

| Level | Allowed | Default |
|-------|---------|---------|
| `propose` | Branch + patch + summary, **no PR** | exploration |
| `pr` | Open PR, never merge | **v1 default** |
| `merge_lane` | Self-merge only if doctrine says lane-scoped + 7 checks green | rare, explicit |
| `hold` | Analysis only | research-only cards |

---

## 3. Runtime hosts

### 3.0 Dual-host strategy (MBP test → Kevin Spark prod)

**Yes — test on your MBP.** That is the right dogfood path. Do not block learning the loop on Kevin box access.

| | **Ryan MBP (test)** | **Kevin Spark (prod)** |
|--|---------------------|-------------------------|
| Role | Build agent loop, cards, retrieve, one-shot jobs under supervision | After-hours dequeue SLA |
| When | Daytime / anytime you are watching | Night window only (Phase 4+) |
| Model | Local coder/36B **or** tunnel `127.0.0.1:11435` → Spark 120B if up | Resident `gpt-oss:120b` |
| Embed | `nomic-embed` local (already on shelf) | Same index copied or rebuilt |
| HERMES_HOME | `~/.devbot-test` or profile `devbot-test` | `~/.devbot` or profile `devbot` |
| Cron overnight | **Off** by default | **On** after Phase 4 exit |
| PR fence | Prefer `ryan/*` or `shared/devbot-test-*` while dogfooding | `shared/devbot-*` / card fence |
| Fail closed | Ollama cold → fail visible, no cloud | Spark down → queue holds, no Cadens |

**Promotion rule:** A feature is “prod-ready” only after the **same job card schema + tools + grounding eval** pass on MBP *and* one supervised run on Kevin Spark. Overnight cron enables **only** on Spark.

**MBP model reality (fleet skill):** Ollama is often a **cold shelf**. For test you either:
1. `ollama run` a mid model (qwen3-coder:30b / 36B) for loop proof, or  
2. Keep Spark tunnel up and point test profile at `:11435` 120B (best fidelity), or  
3. Hybrid: 120B plan via tunnel, local embed + git tools on MBP.

Do **not** download a second 120B onto MBP “for prep.”

### 3.1 Host layout — Kevin Spark (prod)

```text
Kevin Spark
├── Ollama or vLLM: gpt-oss:120b (+ optional hermes3:8b format)
├── embed: nomic-embed-text (or pull index artifact from MBP build)
├── HERMES_HOME=~/.devbot
├── worktrees: ~/k2-worktrees/devbot-<jobid>/
├── git: kevin-real-estate-tools
├── cron: after-hours dequeue + heartbeat
└── egress: git/gh; no Sierra prod; no customer send
```

### 3.1b Host layout — Ryan MBP (test)

```text
Ryan MBP
├── Ollama: nomic-embed + mid coder (or cold until test session)
├── optional: SSH/tunnel to Kevin or Ryan Spark :11435 for 120B
├── HERMES_HOME=~/.devbot-test
├── worktrees: ~/Documents/k2-worktrees/devbot-test-<jobid>/
├── same KRT clone / origin/main discipline
├── cron overnight: DISABLED
└── manual: `devbot run --job <id>` while watching
```

### 3.2 Model routing (local OSS)

| Task class | Model |
|------------|--------|
| Plan / multi-file reason / tradeoff writeup | **120B** |
| Mechanical edit / format / JSON job status | 8B–32B local if available on Spark |
| Embed / retrieve | nomic-embed |
| Hard stuck after N fails | **Stop + human card** (optional later: green escalate — not v1) |

### 3.3 Inference engineering (required, not optional)
- Keep **warm** 120B process across job steps (session pool / long-lived server)  
- Context length truthful for compressor  
- Job-scoped cwd/worktree so path guards match repo  
- Heartbeat + surface failures (observability principle)  
- Idle recycle without killing mid-job  

### 3.4 Network / access
- Tailscale/mesh reachability Ryan ↔ Kevin Spark (existing reach patterns)  
- `gh` auth as **machine identity** agreed by both (bot account or Kevin PAT scoped) — document in charter; never commit tokens  
- Read-only mount or git clone of research already in KRT (corpus is in-repo — good)

---

## 4. Job card schema (SoT)

**Path (proposed):** `docs/agent-coordination/devbot/jobs/YYYY-MM-DD-<slug>.md`  
**Index:** `docs/agent-coordination/devbot/QUEUE.md`

```yaml
---
id: db-2026-08-07-001
status: draft | ready | approved | in_progress | pr_open | needs_human | done | blocked
title: short
repos: [kevin-real-estate-tools]
paths: [k2-hub/src/...]
fence: shared | ryan | kevin   # branch prefix policy
autonomy: propose | pr | merge_lane
approved_by: []                # ryan, kevin — require both if fence=shared or send-adjacent
source: distillery | backlog | ci_flake | inbox-NNNN | human
research_refs: [docs/research/..., docs/decisions/...]
acceptance:
  - "pytest path/to/test passes"
  - "no new send-path without gate"
risk: low | medium | high
deadline: YYYY-MM-DD
---
## Problem
## Constraints
## Out of scope
## Notes for DevBot
```

**State machine:** only `approved` is dequeueable by night runner.

---

## 5. Phased plan

### Phase 0 — Charter + Kevin ratify (no code)

**Objective:** Name DevBot, host=Kevin Spark, OSS-only grinder, grounding law, fences.

**Deliverables:**
1. One-pager charter (this plan §0–2 condensed) → KRT coord path after Ryan+Kevin OK  
2. Explicit “Codex retired; implementer = Spark DevBot”  
3. Choose: Hermes profile vs thin harness  
4. Choose: job SoT = in-repo markdown vs kanban  
5. Bot GitHub identity decision  

**Exit:** Both humans ACK; packet or inbox card closed.

**Fable?** Optional ADV on **gates + autonomy only** if disagreement; not required if charter is accepted as-is.

---

### Phase 1 — Knowledge plane (start on MBP)

**Objective:** DevBot can answer “what’s our stack and why” with citations.

**Where:** **Ryan MBP first** (wiki + corpus live in KRT clone). Spark only needs a sync/copy before Phase 4.

**Tasks:**
1. **Stack canon pack** — single markdown from AGENTS + REPO-MAP + observability + deploy notes  
2. **Tradeoffs index** — SQLite default, lab vs hub, two-unit, merge doctrine, send gate, etc.  
3. **Research corpus inventory** — list `docs/research/**` + INDEX hygiene  
4. **llm-wiki bootstrap** under KRT `docs/devbot-wiki/` (travels with git to Spark)  
5. **Ingest first 15 sources** (canon + cornerstone research + Distillery doctrine)  
6. **Grounding eval set (20 Qs)** — run with MBP agent + tools  

**Exit:** ≥16/20 grounded on MBP dry-run.

---

### Phase 2 — Retrieval (MBP nomic first)

**Objective:** `research_search` / `wiki_search` usable.

**Where:** Build index on **MBP** (`nomic-embed`); commit **chunk manifest + build script** (not necessarily giant binary vectors — or store vectors under `~/.devbot-test/index` gitignored). Spark rebuilds from same script in Phase 3b.

**Tasks:**
1. Chunk wiki + research + decisions  
2. Embed with nomic; local index  
3. Tool top-k + paths  
4. `scripts/devbot_reindex.py` idempotent  
5. Eval retrieval hit-rate on 20 Qs  

**Exit:** Median ≥1 correct source in top-5.

---

### Phase 3 — Agent runtime (MBP dogfood → Spark supervised)

**Objective:** Same loop on both hosts; one manual approved job → PR.

**Phase 3a — MBP (this week path)**  
1. `HERMES_HOME=~/.devbot-test` + model endpoint (local mid **or** Spark tunnel 120B)  
2. SOUL: grounding + AGENTS + charter  
3. Tools: git, rg, read, pytest, gh, research_search  
4. Worktree factory under test prefix  
5. Supervised job (prefer low-risk lab/docs/test path)  
6. Log runbook: what failed on MBP  

**Phase 3b — Kevin Spark (promotion)**  
1. Mirror profile + reindex script  
2. Pin 120B endpoint  
3. Repeat **same** job card (or twin) supervised  
4. Heartbeat path proven on Spark  

**Exit:** One PR from MBP *or* Spark without cloud model; Spark supervised run green before any night cron.

---

### Phase 4 — Coding loop + after-hours grind (**Spark only**)

**Objective:** Queue-driven overnight work on Kevin Spark.

**Tasks:**
1. Job state machine + QUEUE.md  
2. `devbot dequeue` on Spark  
3. Runner plan → implement → test → PR  
4. Cron 22:00–06:00 CT; MBP cron stays off  
5. Morning digest  
6. Human review loop  

**Exit:** 3 nights Spark-only; ≥2 PRs human-disposed.

---

### Phase 5 — Distillery + backlog intake

**Objective:** Research loop and broken-shit feed the queue cleanly.

**Tasks:**
1. Distillery brief → job card template mapper (human still hits `approved`)  
2. CI flake / doctor drift / known-broken list → card drafts (`ready`, not auto-approved)  
3. Inbox “implement” residuals → card drafts (no Codex path)  
4. Reject cards that are ADR/product (route to Kevin/Ryan interactive unit)  

**Exit:** Distillery output never executes without approval; backlog drafts appear weekly without manual retyping.

---

### Phase 6 — Inference harden + optional model train

**Objective:** Fast stable Spark path; LoRA only if needed.

**Tasks:**
1. Warm model server, context truth, job-scoped sessions  
2. Split: 120B plan / smaller apply if quality holds  
3. Optional: LoRA on **style + tool discipline** from graded transcripts — **not** full repo  
4. Re-run grounding eval + 5 coding tasks  

**Exit:** p50 job cycle time target set and met; no regression on grounding eval.

---

## 6. Files / surfaces likely to change (when executing)

| Area | Paths |
|------|--------|
| Charter / jobs | `kevin-real-estate-tools/docs/agent-coordination/devbot/**` |
| Build plan land | `docs/build-plans/2026-08-07-devbot-local-spark.md` (copy of this) |
| Wiki | `docs/devbot-wiki/**` or external wiki synced to Spark |
| Index scripts | `scripts/devbot_reindex.py`, `scripts/devbot_dequeue.py` |
| Spark ops | launchd/cron unit files under deploy or `~/.devbot/` |
| Skills | new `k2-devbot` skill on Hermes profiles that *talk about* DevBot; runtime skills on Spark profile |
| T1000 | optional mesh notes only — **not** product rebuild |
| Config | Spark Ollama model pins; **no** Codex aliases in DevBot profile |

---

## 7. Validation

| Gate | Proof |
|------|--------|
| Local-only grinder | Job completes with model base_url on Spark; no OpenAI/Anthropic key used |
| Grounding | Eval set ≥80% with citations to research/ADR/REPO-MAP/live path |
| Fence | Branches match `approved` fence; no writes to opposite human branches |
| Approval | Night runner skips non-`approved` cards |
| Doctrine | Shared/send/cross-lane never self-merged by DevBot |
| Observability | Heartbeat file/cron proves alive; failures visible morning |
| Distillery | Sample brief → card draft → human approve → PR |
| Two-unit | No joint queue UI; weekly priority + packets unchanged |

---

## 8. Risks & tradeoffs

| Risk | Mitigation |
|------|------------|
| Kevin Spark downtime | Jobs stay queued; no Cadens silent fallback (fleet law) |
| 120B slow / weak on huge refactors | Card sizing; split jobs; escalate to human interactive unit |
| Hallucinated stack choices | Grounding protocol + AGENTS “flag off-stack” |
| Stale research | Reindex cron; prefer live code for API truth |
| Cross-chat / multi-job session bleed | Job-scoped worktree + agent session id |
| Bot gh identity politics | Explicit Phase 0 decision with Kevin |
| Scope creep into Lori/EA/Distillery product | Charter non-goals; card router rejects |
| “Train the model” distraction | Phase 6 last; wiki/RAG first |
| Codex muscle memory in docs | Grep-and-update kickoff docs that still say codey/Codex |

**Tradeoff call (recommended default):**  
Hermes-on-Spark + wiki/RAG + approved jobs **>** custom agent framework **>** fine-tune.  
Shared **markdown job SoT in KRT** **>** new SaaS queue (stays in git, two-unit friendly).

---

## 9. Open questions (resolve in Phase 0)

1. Hermes profile on Spark vs purpose-built thin harness?  
2. Job SoT: in-repo markdown vs T1000 kanban `k2` board?  
3. GitHub identity for PRs (`shared/devbot` bot user vs Kevin machine user)?  
4. Is Kevin Spark the **only** overnight runner? (**Plan default: yes.** MBP = test only.)  
5. Morning surface: Slack `#builds` vs inbox-only vs both?  
6. Max autonomy overnight: `pr` only, or allow `merge_lane` for pure `kevin-lab/`?  
7. MBP test model: local mid-weight vs tunnel to Spark 120B for fidelity?  
8. Which Distillery artifacts are in-bounds for auto-draft cards?

---

## 10. Suggested immediate next actions (human)

1. Ryan: skim this plan; mark Phase 0 answers to open questions.  
2. Kevin: ratify host + gh identity + max autonomy (packet or short call).  
3. Optional Fable: only if autonomy/merge gates contested — prompt = §0 + §2.4 + §8.  
4. On execute signal: start Phase 1 knowledge pack + Phase 0 charter land on KRT (coord doctrine).  
5. **Do not** start fine-tunes or new PM UI first.

---

## 11. One-page mental model

```text
                    ┌──────────────┐
                    │  MBP test    │  dogfood loop, wiki, embed, supervised jobs
                    └──────┬───────┘
                           │ promote same artifacts
Distillery / backlog       ▼
        → approved cards → DevBot on Kevin Spark (OSS 120B, night)
                        ← research + wiki retrieve
                        ← live repo tools
                        → PR → dual human gate → merge/reject
```

**Know the system** = wiki + research retrieve + tools (build on MBP).  
**Grind after hours** = Spark only.  
**Stay shared without chaos** = fences + dual gate + no joint desk.

---

## 12. Relationship to other plans

| Plan | Relationship |
|------|----------------|
| `2026-08-06_222342-spark-inference-experiments.md` | Inference harden feeds Phase 6; don’t block DevBot v1 on it |
| `2026-08-07_074000-mac-mini-student-model.md` | Mini = control plane later; DevBot compute = **Kevin Spark** |
| Claude ACP / T1000 desk work | Orthogonal — Ryan interactive Max lane; not DevBot grinder |
| Teammate EA / Lori | Separate product track |

---

*End of plan. No implementation performed.*
