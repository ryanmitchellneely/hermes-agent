# Spark Inference Experiments Plan

> **For Hermes:** Plan only until Ryan says go. No execution, no Spark load, no default-route changes while live desk depends on current Ollama path.
> When executing: use subagent-driven-development task-by-task; never flip production routes until Phase gates pass.

**Goal:** Run a bounded set of inference-engineering experiments on Ryan’s DGX Spark so local 120B-class serve is measured, then improved (server, cache, speculative decoding, structured tools) without breaking T1000/Pulp.

**Architecture:** Keep today’s **Ollama-on-Spark** path as production baseline. Stand up a **side-door** OpenAI-compatible endpoint (vLLM or SGLang) on a non-default port. Benchmark → compare → optional canary → promote. Experiments ordered by ROI from Latent Space / Baseten inference masterclass + current fleet (MBP M3 Max 64GB, 1× Spark, Kevin’s 2× Sparks later, k2vps Pulp).

**Tech stack:** DGX Spark (GB10, 128GB) · Ollama (baseline) · vLLM and/or SGLang · models `gpt-oss:120b` (MXFP4), `hermes3:8b` / `hermes3:8b-16k`, `qwen2.5-coder:32b` (or current coder tag) · Mac tunnel `127.0.0.1:11435` · `reach spark` · results under `~/Documents/T1000/docs/inference/` (or `~/.t1000/docs/inference/` if preferred)

**Status:** DEFERRED — do not start until Ryan explicitly kicks off.

**Triggers to start (any one):**
- Quiet evening / weekend with Spark free ≥2h
- Ryan says “run spark bench” / “start inference plan”
- After Mac mini migration (optional; not a blocker)

**Hard rules:**
- No production default flip without written gate pass
- No dual-writer gateway nonsense; this plan is **Spark serve only**
- No client/SBS confidential prompts in benches
- Pulp/T1000 stay on current routes until canary
- Cloud escalate remains available; local is not required to beat Claude latency

---

## Current context / assumptions

| Item | Assumption |
|---|---|
| Spark role | Heavy local IQ; Ollama tags include reason `gpt-oss:120b`, format `hermes3:8b*` |
| Tunnel | `ssh` host `spark` → local `11435` via existing tunnel scripts |
| Reach | `reach spark status` expects reason + format models |
| Baseline tok/s | Planning band ~25–45 tg Ollama 120B; optimized single-node target ~50–60 tg |
| Width signal (2026-08) | Public DGX Spark demo: 32 concurrent Hermes coding agents × Flash-class model → ~62.5 **aggregate** tok/s, 0 fails, ~73% draft accept ([McNab](https://x.com/jasonmcnab/status/2085593096243331193)). Proves Spark as **agent width** box — not a promise that 120B does 32-wide at that rate |
| Masterclass levers | Prefill≠decode, KV/prefix cache, spec dec, quant fidelity, structured outs, concurrency/batch, sticky multi-node later |
| Out of scope now | Full PD disaggregation multi-GPU datacenter style, video/diffusion, Kevin TP until Phase G; cloning McNab’s exact Flash model unless already on box |

---

## Success criteria (whole program)

1. **Baseline card** exists: TTFT + decode tok/s for 8B / 32B / 120B @ 2k and 8k ctx (n≥3).
2. **Side-door server** serves 120B without taking down Ollama (or with a documented brief Ollama stop window).
3. **Decision memo:** keep Ollama vs promote vLLM/SGLang for reason path (numbers + tool golden).
4. **Spec-dec pilot** reports accept rate + tg delta vs baseline (promote only if accept ≥ threshold).
5. **Concurrency card** exists: N={1,8,16,32} parallel streams — **aggregate tok/s**, per-stream p50 tg, fail rate, optional draft accept under load (see Phase C2).
6. **No regression** on format/tool JSON path (golden set green).
7. Results logged in one markdown + optional CSV; HEARTBEAT optional one-liner on advisory desk if Ryan wants.

---

## Phased experiment map

```text
Phase 0  Prep + safety                 (~30–45 min)   [no load]
Phase A  Baseline bench card           (~45–60 min)   [Spark load]
Phase B  Side-door server bake-off     (~2–3 h)       [Spark load]
Phase C  Speculative decoding pilot    (~1–2 h)       [Spark load]
Phase C2 Concurrency / width bench     (~45–90 min)   [Spark load]
Phase D  Prefix/KV + agent realism     (~1 h)         [light]
Phase E  Structured tools golden       (~45 min)      [light]
Phase F  Decision + canary/promote     (~30 min)      [careful]
Phase G  (Later) Kevin mesh / sticky   (deferred)
```

Do **not** start B until A is written. Do **not** start C2 until B is healthy (side-door or documented Ollama-only width baseline). Do **not** start F until B+C+E gates clear; **C2 informs F** (promote needs width story, not only single-stream tg).

---

### Task 0.1: Create results home + template

**Objective:** One place for all numbers so future-you doesn’t hunt Telegram.

**Files:**
- Create: `~/Documents/T1000/docs/inference/README.md`
- Create: `~/Documents/T1000/docs/inference/TEMPLATE-bench-card.md`
- Create: `~/Documents/T1000/docs/inference/experiments/YYYY-MM-DD-baseline.md` (on run day)

**Step 1:** mkdir and README stating purpose, phases, “production still Ollama until promote”.

**Step 2:** Template sections: hardware, software SHAs/versions, models, commands, table (model × ctx × pp × tg × TTFT), notes, decision.

**Verify:** paths exist; template has empty tables.

**Do not:** change Spark config.

---

### Task 0.2: Inventory live Spark stack (read-only)

**Objective:** Know exact model tags, server, CUDA/driver, free RAM before touching anything.

**Commands (when live):**
```bash
reach spark status
# or tunnel up then:
curl -sS http://127.0.0.1:11435/api/tags | jq .
ssh spark 'nvidia-smi; free -h; which ollama; ollama --version; docker ps 2>/dev/null | head'
ssh spark 'ls -la ~/ 2>/dev/null; systemctl --user status ollama 2>/dev/null | head -20'
```

**Record:** model names/sizes/quants, Ollama version, GPU util idle, any existing vLLM containers.

**Gate:** If Spark unreachable, stop — fix tunnel first (not this plan’s scope beyond “bring tunnel up”).

---

### Task 0.3: Freeze production contract

**Objective:** Write what must not break.

**Checklist to paste into results doc:**
- [ ] Reason model tag for desk: `gpt-oss:120b` (confirm)
- [ ] Format model: `hermes3:8b` / `hermes3:8b-16k` (confirm)
- [ ] Tunnel port `11435` remains Ollama **or** documented dual-port map
- [ ] Pulp / SPARK-gated tools still work post-change
- [ ] Rollback: restart Ollama only, tear down side-door container

**Files:**
- Create: `~/Documents/T1000/docs/inference/PRODUCTION-CONTRACT.md`

---

### Task 0.4: Build a tiny golden set (quality, not speed)

**Objective:** Catch “faster but broken tools/JSON”.

**Files:**
- Create: `~/Documents/T1000/docs/inference/golden/prompts.jsonl`
- Create: `~/Documents/T1000/docs/inference/golden/README.md`

**Contents (8–12 cases, no secrets):**
1. Short chat (control)
2. Long-ish agent-style system prefix + user ask (prefix stability)
3. Tool-call shaped JSON (name + args)
4. Multi-tool plan JSON
5. Code edit request (coder path)
6. Refuse/safe boundary smoke (optional)
7. Format-only with hermes3 (strict JSON schema)
8. 8k-ctx synthetic pad + short question (ctx stress)

**Each line:** `id`, `model_role` (reason|format|coder), `messages`, `expect` (substring / json_schema / tool_name).

**Verify:** file validates as JSONL; no client names/credentials.

---

## Phase A — Baseline bench card (Ollama as-is)

### Task A.1: Standardize bench harness

**Objective:** One script or documented command block so A/B/C are comparable.

**Preferred approach (pick one when executing):**
1. `llama-bench` / ollama native bench if available on Spark
2. Small Python client: warm-up + n runs, record TTFT and tok/s from streaming timestamps
3. Server-side metrics if vLLM exposes them later

**Files:**
- Create: `~/Documents/T1000/scripts/inference/bench_openai_compat.py` (works against any OpenAI-compat base_url)
- Create: `~/Documents/T1000/scripts/inference/run_baseline.sh`

**Metrics (required columns):**
| field | meaning |
|---|---|
| `ttft_ms` | time to first token |
| `decode_tps` | tokens after first / time after first |
| `total_tps` | optional crude |
| `prompt_tokens` | |
| `completion_tokens` | |
| `ctx_target` | 2k / 8k |
| `model` | |
| `backend` | ollama \| vllm \| sglang |
| `n` | run index |

**Settings:** temperature 0, max_tokens 128 (decode) and separate prefill-heavy prompt; seed if supported; n=3 discard first warm-up if cold start separate.

---

### Task A.2: Run baseline matrix on Ollama

**Objective:** Numbers for current production path.

**Matrix:**

| model | ctx pad | max_out | notes |
|---|---|---|---|
| hermes3:8b (or 8b-16k) | 2k, 8k | 128 | format path |
| qwen2.5-coder:32b (or current) | 2k, 8k | 128 | coder |
| gpt-oss:120b | 2k, 8k | 128 | reason — **primary** |

**Protocol:**
1. Tunnel up; `reach spark status` green
2. Load one model at a time when possible (note if multi-load)
3. Warm-up 1 request discarded or marked cold
4. 3 timed runs each cell
5. Capture `nvidia-smi` once mid 120B run (power, mem, util, temp)

**Do not:** change quants or server yet.

**Output:** fill `experiments/YYYY-MM-DD-baseline.md` + CSV optional.

**Gate A:** Card complete. If 120B @2k decode &lt; 15 tg, flag thermal/power/quant issue before Phase B.

---

### Task A.3: Baseline golden quality

**Objective:** Quality floor for later compare.

Run golden set against Ollama; record pass/fail.

**Gate:** Format JSON cases must pass on hermes3 path before any promote.

---

## Phase B — Side-door server bake-off

### Task B.1: Choose engine order

**Default order:**
1. **vLLM** first (broader ops muscle memory, OpenAI API)
2. **SGLang** if vLLM awkward on GB10 / MoE / MXFP4

**Decision rule:** whichever gets 120B healthy first with stable streaming wins the bake-off; don’t boil ocean supporting both in prod.

---

### Task B.2: Install side-door without killing Ollama (preferred)

**Objective:** Second port e.g. `11436` or `8000` on Spark, tunnel extra local port if needed.

**Sketch:**
```bash
# ON SPARK — example only; pin versions at execute time
# docker run ... vllm serve <model> --port 8000
# keep Ollama on 11434
```

**Mac tunnel:** add local forward `11436 → spark:8000` **or** temporary SSH:
```bash
ssh -N -L 11436:127.0.0.1:8000 spark
```

**Files to update when executing (not now):**
- Tunnel helper scripts under `~/.t1000` / T1000 spark tunnel docs
- `reach` only after promote (don’t change expected ports early)

**Rollback:** stop container; Ollama untouched.

---

### Task B.3: Model bring-up on side-door

**Objective:** 120B generates tokens; then 8B draft candidate.

**Steps:**
1. Resolve HF / local path for gpt-oss 120b quant that Spark already uses (prefer same bits as Ollama MXFP4 if engine supports)
2. Start server with conservative max_model_len (e.g. 16k or 32k — not 128k day one)
3. Smoke: `curl` chat completions 16 tokens
4. Note load time + VRAM/unified mem

**If load fails:** document error; try alternate quant/engine; do not thrash production Ollama &gt;15 min.

---

### Task B.4: Repeat bench matrix on side-door

Same matrix as A.2; backend column = vllm|sglang.

**Compare table:**

| model@ctx | ollama tg | side tg | ollama TTFT | side TTFT | winner |
|---|---|---|---|---|---|

**Gate B (speed):** side-door 120B@2k decode ≥ **1.2×** Ollama **or** TTFT clearly better with tg within 10%, else side-door is optional not promote.

**Gate B (stability):** 20 sequential requests no crash; no empty streams.

---

### Task B.5: Golden on side-door

Same golden set; tool/JSON must not regress vs A.3.

**Gate:** zero new fails on format role; reason role qualitative OK.

---

## Phase C — Speculative decoding pilot

### Task C.1: Draft pair selection

**Primary pair:**
- Target: `gpt-oss:120b`
- Draft: `hermes3:8b` (already in fleet; traffic-shaped to desk)

**Secondary (only if primary accept rate &lt; 0.5):**
- Draft: small coder or dedicated tiny draft if available

**Record:** engine flags for spec dec (vLLM `speculative_model` / SGLang equivalent — pin docs at execute time).

---

### Task C.2: Measure acceptance + speed

**Metrics:**
- mean draft accept rate (if exposed)
- decode_tps vs Phase B without spec
- TTFT (often similar or slightly worse — OK if tg wins)

**Traffic mix (3 buckets, 10 req each):**
1. Ops/chat (desk-like)
2. Code
3. Random summary (expect lower accept — Harry Potter lesson from masterclass)

**Gate C:**  
- Overall accept ≥ **0.55** on ops+code mix **and** decode_tps ≥ **1.25×** Phase B → keep spec on canary  
- Accept &lt; 0.4 or slower → disable spec; document

---

### Task C.3: Optional traffic-specific draft (park if timeboxed)

Only if C.2 promising but code accept low: tiny LoRA draft on anonymized agent traces. **Park by default** (YAGNI until sticky product need).

---

## Phase C2 — Concurrency / width bench (McNab-shaped)

> **Signal:** Jason McNab (2026-08) — 32 concurrent Hermes coding agents on **one DGX Spark**, DeepSeek V4 Flash, **~62.5 aggregate tok/s**, 32/32 ok, **~72.7% draft accept**, ~110 tokens/agent mean. Flex = **swarm width + batched serve**, not “each agent feels like Claude.”  
> **Our job:** Measure *our* stack the same way — **N parallel streams** — without copying his model or dashboard.

### Task C2.0: Guardrails

**Objective:** Don’t thrash production desk or corrupt a shared git tree.

| Rule | Detail |
|---|---|
| Isolation | Concurrent **HTTP completions only** day one — **no** 32 agents writing one worktree |
| Secrets | Synthetic coding prompts only (no SBS/client) |
| Prod Ollama | Prefer **side-door** from Phase B; if Ollama-only, document and keep N modest first (1→8) |
| Model classes | Run **two lanes** if time: (1) **width lane** = fastest reasonable on-box coder/Flash-class or 8B/32B; (2) **depth lane** = `gpt-oss:120b` at **lower N** (1,2,4,8) |
| Don’t claim | “We matched McNab” unless model + prompt + N match; compare **method**, not ego |

---

### Task C2.1: Harness — parallel OpenAI-compat load

**Objective:** One script fires N concurrent chat/completions, records per-stream and aggregate metrics.

**Files:**
- Create: `~/Documents/T1000/scripts/inference/bench_concurrency.py`
- Create: `~/Documents/T1000/docs/inference/experiments/YYYY-MM-DD-concurrency.md`

**Required metrics:**

| Field | Meaning |
|---|---|
| `N` | concurrent streams |
| `model` / `backend` | |
| `agg_tok_s` | total completion tokens / wall time |
| `per_stream_tg_p50` / `p95` | decode-ish per stream if measurable; else tokens/stream_time |
| `ttft_p50_ms` | time to first token across streams |
| `fail_rate` | errors / N |
| `draft_accept` | if spec-dec on (from C) |
| `peak_mem` / `gpu_util` | one `nvidia-smi` snapshot mid-run |
| `tokens_per_stream_mean` | catch “toy 110-token” vs real work |

**Prompt set (fixed):**
1. **Short code** — “Write a Python circuit-breaker class with tests stubs” · `max_tokens=128` or 256  
2. **Optional medium** — same @ 512 (only if N≤8 and mem OK)

**N ladder:** `{1, 8, 16, 32}` for width lane; `{1, 2, 4, 8}` for 120B depth lane. Stop ladder on OOM, >5% fails, or Ryan abort.

**Step 1:** Implement script: asyncio or thread pool, shared wall clock, JSONL per stream + summary row.

**Step 2:** Dry run N=2 against side-door.

**Verify:** summary prints agg_tok_s and fail_rate; no hang >120s without progress log.

---

### Task C2.2: Width-lane run (throughput model)

**Objective:** Find how wide Spark goes on a **fast** on-box model (8B format, 30B coder, or Flash-class **if already present** — do not pull multi-hundred-GB mid-bench without Ryan OK).

**Protocol:**
1. Load width model only (unload 120B if mem fights)
2. Spec-dec **on** if C promoted it for this model pair; else off and note
3. Run N ladder; write table:

| N | agg tok/s | p50 tg/stream | fail% | draft accept | notes |
|---|---:|---:|---:|---:|---|

**Gate C2-width (informational, not promote-blocking alone):**
- N=8 fail_rate **0** and stable streams  
- N=16/32: record cliff (where fails or tg collapses) — **cliff is a finding**, not a failure of the plan

**Compare note:** McNab ~62 agg @ N=32 on Flash — our number may be lower; document model delta.

---

### Task C2.3: Depth-lane run (120B, low N)

**Objective:** Honest concurrency ceiling for **reason** model.

**Protocol:**
1. Resident `gpt-oss:120b` (+ draft 8B if spec-dec on)
2. N = 1,2,4,(8 if mem allows)
3. Same short-code prompt, `max_tokens=128`
4. Table as above

**Gate C2-depth:**
- N=1 matches Phase B single-stream ballpark (±15%)
- N=2+ : document **agg tok/s** vs N=1 (batching win?) and per-stream degradation
- If N=2 already OOM/fails → depth lane max_concurrency = 1 for prod router recommendation

---

### Task C2.4: Isolation footnote (agents later)

**Objective:** Capture policy so future “32 Hermes agents” don’t corrupt repos.

**Write into concurrency experiment md:**
```text
HTTP width bench ≠ multi-agent coding on one tree.
When promoting swarm agents: one worktree (or lease) per worker;
single-writer for shared paths; kanban swarm graph preferred over free-for-all.
```

**No code change required** in C2 — policy only. Optional later: kanban link to mesh swarm tasks.

---

### Task C2.5: Router / decision inputs from C2

**Feed Phase F memo with:**
| Lane | max_N recommended | Why |
|---|---:|---|
| `swarm` / width | (from C2.2 cliff−1) | Flash/coder/8B |
| `private` / 120B | (from C2.3) | usually 1–2 |
| Spec-dec under load | keep/kill | accept rate @ N=8 vs N=1 |

**Success for C2:** concurrency md filled; F can say “promote side-door because single-stream **and** width” or “width only on Ollama 8B, 120B stay N=1.”

---

## Phase D — Prefix / KV realism (agent-shaped)

### Task D.1: Stable prefix experiment

**Objective:** Quantify prefill savings from reused system prefix (masterclass cache-aware lesson).

**Method:**
1. Fixed ~2–4k system+tools prefix (synthetic skills list)
2. Run 10 turns appending user/assistant with **identical** prefix
3. Compare TTFT turn1 vs turn2+ on side-door (prefix caching on)
4. Repeat with **shuffled tool order** each turn (anti-pattern) — expect worse TTFT

**Pickup for Hermes config later:** document “do not reshuffle tools/system mid-session” (likely already true — verify).

**Files:**
- Notes in `experiments/YYYY-MM-DD-prefix-kv.md`
- If Hermes bug found: issue/todo only — fix is separate plan

---

### Task D.2: Context policy recommendation

From D.1 + A/B numbers, write default recommendations:
- Interactive agent ctx default (e.g. 8–16k)
- When to escalate long ctx
- Format model stays short ctx

---

## Phase E — Structured tools golden hardening

### Task E.1: Constrained decoding smoke

**Objective:** Where engine supports JSON schema / grammar, run format+tool cases constrained.

**Compare:** unconstrained vs constrained — validity rate, tg cost.

**Gate E:** constrained validity ≥ unconstrained with no severe tg collapse (&lt;30% hit OK if validity → 100%).

---

### Task E.2: Wire recommendation only

Document: format path should prefer schema-constrained; reason path free text.  
**No Hermes code change in this plan** unless Ryan expands scope.

---

## Phase F — Decision, canary, promote

### Task F.1: Write decision memo

**File:** `~/Documents/T1000/docs/inference/DECISION-YYYY-MM-DD.md`

**Must include:**
- Baseline vs side-door vs spec numbers (table)
- **Concurrency card** (width lane + 120B depth max_N) from Phase C2
- Golden pass/fail
- Thermal/power notes
- Recommendation: **stay Ollama** | **canary side-door** | **promote side-door for reason only** | **promote width lane separately**
- Suggested router caps: `swarm` max_N vs `private` max_N
- Rollback steps (copy-paste)
- What not to do next

---

### Task F.2: Canary (only if gates passed)

**Canary shape:**
- Optional env / config on **one** non-critical client (e.g. manual curl, or single SPARK tool with override base_url)
- 24–48h Ryan dogfood
- Watch: crashes, empty responses, tool parse fails, tunnel flaps

**Promote criteria:**
- Canary painless
- ≥1.2× tg or major TTFT win
- Golden green
- Rollback tested once

**Promote actions (separate small change set):**
- Document ports; update tunnel
- Point reason model URL at side-door
- Leave format on fast 8B (Ollama or same engine)
- Update `reach spark status` expectations if ports/models change
- Skill touch: `t1000-spark-tools` only if URLs change

---

### Task F.3: Explicit non-goals after first cycle

Stop after one cycle unless Ryan opens Phase G. Avoid endless engine churn.

---

## Phase G — Later (Kevin mesh) — plan stub only

**When:** Kevin’s 2 Sparks online + your baseline solid.

| Experiment | Idea |
|---|---|
| G1 | Sticky session routing (same chat → same node with KV) |
| G2 | Role split: node A reason 120B, node B draft 8B / coder 32B |
| G3 | Naive TP dual-node 120B — only if G2 insufficient |
| G4 | Quotas so K2 batch can’t starve desk |

**Do not start G during first weekend.**

---

## Suggested calendar (when Ryan is ready)

| Block | Duration | Phases |
|---|---|---|
| Session 1 | 1.5–2 h | 0 + A |
| Session 2 | 2–3 h | B |
| Session 3 | 1.5–2 h | C + **C2** |
| Session 4 | 1–1.5 h | D + E + F memo; canary optional |

Total focused: **~7–10 hours** wall time across days. Not one marathon if Spark is house-shared.

---

## Files likely to change (only when executing)

| Path | When |
|---|---|
| `~/Documents/T1000/docs/inference/**` | All phases (results) |
| `~/Documents/T1000/scripts/inference/**` | A–C harness + **C2 `bench_concurrency.py`** |
| Spark host: docker/systemd side-door | B–C2 |
| Tunnel scripts under `~/.t1000` or T1000 | B / F if extra port |
| `reach` / `t1000-spark-tools` skill | F promote only |
| Hermes `config.yaml` model base URLs | F promote only |

**Not in scope:** Mac mini purchase, 2nd Spark buy, Pulp VPS inference move, gateway HA (already separate).

---

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Ollama downtime during experiments | Prefer dual-port; schedule window; rollback script ready |
| Unified mem thrash loading two stacks | Load one heavy at a time; stop side-door after session |
| MXFP4 unsupported in engine X | Fall back other engine/quant; keep Ollama |
| Spec dec slows bad traffic | Disable on low accept; traffic-route later |
| Width bench OOMs desk | Prefer side-door; start N=8; unload 120B for width lane |
| “32 agents” misread as multi-writer git | C2 is HTTP-only; isolation footnote before any swarm product |
| “Faster” breaks tools | Golden gate blocks promote |
| Scope creep to multi-node | Phase G locked |
| Thermal throttle confuses benches | Log nvidia-smi; re-run if temp spike |
| Ego-compare to McNab Flash @ 62 agg | Different model; log method parity only |

---

## Open questions (resolve at kickoff, not now)

1. Prefer results under `Documents/T1000/docs/inference` vs `~/.t1000/docs/inference`?
2. Is brief Ollama stop OK if dual-port impossible on GB10?
3. Any model tag renames since last `reach` expect (`gpt-oss:120b`, `hermes3:8b-16k`)?
4. Should canary include Pulp path or desk-only first? (Recommend **desk/manual first**)

---

## Validation summary (definition of done)

- [ ] Baseline card published
- [ ] Side-door numbered compare published
- [ ] Spec-dec accept + tg published (or explicitly skipped with reason)
- [ ] **Concurrency card** published (width N ladder + 120B depth max_N)
- [ ] Golden set green on chosen path
- [ ] Decision memo with rollback + swarm vs private caps
- [ ] Production still safe (either unchanged or promoted with canary history)
- [ ] This plan marked complete / superseded in README

---

## Kickoff command (for future session)

When Ryan says go, agent should:

1. Re-read **this plan**
2. Confirm Spark tunnel + quiet window
3. Start **Task 0.1** only — no server installs until Phase 0 complete
4. Stop after Phase A unless Ryan says continue

```text
Ryan kickoff phrase ideas:
- "start spark inference plan"
- "run phase A only"
- "continue inference plan from phase B"
- "run phase C2 only"   # after B healthy
```

---

## References

- Latent Space: Inference Engineering Masterclass (Kiely/Taha, Baseten) — cache-aware routing, PD split, spec dec, quant error cancellation, structured outputs
- Prior desk targets: ~50 tg north star on 120B single Spark; Ollama often 25–45 until tuned
- Fleet: MBP UI · Spark muscle · k2vps Pulp · Kevin Sparks later
- **Width bench signal:** [Jason McNab — 32 Hermes agents / DeepSeek V4 Flash / 1× DGX Spark ~62.5 agg tok/s](https://x.com/jasonmcnab/status/2085593096243331193) (2026-08); method template for Phase C2 — not a score to chase with 120B
- Related: kimi-k3-in-c disk-stream MoE (RSS toy) — out of scope for this plan; opposite objective (min RAM vs max interactive/width tok/s)
---

**Plan complete. No experiments run. No infrastructure changed.**
