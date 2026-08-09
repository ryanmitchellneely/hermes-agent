# Open steals rollup (P0 / P1 only)

Mechanical extract from `entries/*` where `steal_rank` is P0 or P1 and status ≠ done/wont.
Refresh when adding signals: edit this table + entry Status.

> **Reconciled against the live boards 2026-08-08** (audit: every steal checked for a real card
> across all 9 kanban boards, 320 cards). Prior wire statuses were stale in **both** directions —
> five steals were already shipped or carded while still marked `open`, and four had never reached
> a board at all. Wire status below is card-verified, not asserted.

| Steal | From | Rank | T1000-shaped action | Wire status |
|-------|------|------|---------------------|-------------|
| **Execution-feedback repair pass** (run tests → feed failures back → one retry) — claimed to beat 6× memory | SIG-20260809-01 danpacary | **P0** | Extend the G3 runner with a test-exec step + **3 arms incl. blind-retry control**; measure before spending the fork lever | **carded 2026-08-09** `t_6506193d` (blocked: Ryan window on his Spark) |
| **Factorial harness-vs-model design** (vary ONE factor at a time, report both deltas) — their result: **framework alone +30 pts, model alone +20** | SIG-20260809-02 Frontis-MA1 / OpenRSI | **P1** | Adopt as the report shape for the repair-pass A/B — it *is* the control structure that card already demands | **wired 2026-08-09** — commented onto `t_6506193d`; no new card |
| **Compile the index, don't hand-maintain it** — generate `INDEX.md` + doc-index §7 from `entries/` frontmatter | SIG-20260809-03 OpenKB | **P1** | ~30 lines in `scripts/signal_log_new.py`, no new dependency. Kills the drift class that put **5 of 12** entries in the cold-start map on 08-09 | **open — no card** (offered to Ryan; board at 44 blocked) |
| **Raw → compiled is a real layer; session logs are not it** | SIG-20260809-03 OpenKB | P1 | KRT `.omc/wiki` is **581 session-logs / 22 curated of 604**; `llm-wiki` skill exists but `WIKI_PATH` unset and never run; `docs/research/` (195 md) has no wiki. Add a compile pass before more auto-capture | open — log only |
| Named operator set **Draft / Improve / Debug / Crossover** as code-lane vocabulary | SIG-20260809-02 Frontis-MA1 | P1 | We have Draft (G3) + Debug (repair, carded). **Improve** and **Crossover** have no DevBot analogue | open — log only, board at 46 blocked |
| Execution-grounded labels — environment scores the trace, no human thumb | SIG-20260809-02 Frontis-MA1 | P1 | B18 is at **0 labels / 2 pointers**. Split the scorer: schema-valid / evidence-grounded / refusal-correct are **checkable today**; intent / urgency / followup have **no oracle** and stay Ryan's | open — do NOT read as "stop labeling" |
| **DS4 gap is DECODE-ONLY — 16.07 vs 28.6 tok/s; prefill already at parity** | SIG-20260808-06 DwarfStar/Entrpi | **P0** | Propose Entrpi fork cutover **to Kevin** (his box, no install) | **carded** `t_43e997d2` — **upstream-DSpark precondition now SATISFIED (negative)**; blocked on Kevin OK only. W2 measured our prefill at **~1,070 tok/s, matching the fork's claim**, so the fork lever is decode, not prefill |
| DS4 speculation + continuous batching as the decode/width lever | SIG-20260808-06 DwarfStar/Entrpi | P1 | Enable `--dspark/--mtp`; width ladders both boxes | ✅ **ANSWERED — negative** `t_716141c4` done 08-09: upstream DSpark is **Metal-only** (159 metal-tagged lines, 0 cuda), A/B 16.23 vs 16.39 = 1.01× noise, rolled back. **Fork is the only spec-dec route on GB10 — do not re-run upstream.** Width: `t_9c7208c2` (Ryan N) · `t_89c72b32` (Kevin N, ack-gated); R12 says `KEEP_ALIVE=-1` eviction, not width, is the Ryan-box bottleneck |
| Concurrency bench N={1,8,16,32}, agg tok/s, width vs 120B depth | SIG-20260807-03 McNab | P0 | B17 **Phase C2** | **wired** plan + `t_fd210e86` decomposed into the two ladders above |
| Spec-dec + TTFT≠decode + prefix/KV sacred | SIG-20260806-01 LS masterclass | P0 | B17 Phases C/D; cache discipline | ✅ **wired + executed** `t_01ac807e` done 08-09: ctx 32768→65536, all 3 configs lockstepped, 58,357-tok prompt → 200. **MLA compresses KV hard — +0.67 GiB for +32k, ~21 KiB/token all-in**, not the doubling I predicted. Residual: `kv-disk-space-mb` still 8192 with `disk-cache-full` evictions in journal — own restart, cheap win |
| **Parent strong / subagents cheap-fast** | SIG-20260808-02 codex-router | P1 | Child model ≠ parent by default | ✅ **SHIPPED** — B22: `orchestrator`→Flash@kevin-spark, `worker`→120b@spark; per-card `model_override`/`provider_override` |
| Picker only lists authed/live routes | SIG-20260808-02 codex-router | P1 | Don't surface dead Spark/Ollama aliases | ✅ **SHIPPED** `t_cf82f21c` (phantom ds4-pro aliases deleted) · residual `t_3084469d` (strip from skill doc) |
| Code-lane turn/token/time budgets + test gate | SIG-20260807-02 Prime | P1 | Coding agent autonomous limits | ✅ **likely already shipped** — `max_runtime_seconds`, `max_retries`, `consecutive_failures` live in the tasks schema. **Verify before building.** |
| Idempotent job identity + lost-response reconciliation | SIG-20260808-05 Agent Dock | P1 | No orphan or duplicate dispatch | ✅ **likely already shipped** — `idempotency_key`, `current_run_id`, `last_heartbeat_at` in schema. **Verify before building.** |
| **Spark serve metric card** (util, mem, tok/s, TTFT p95, KV%) | SIG-20260808-04 sparkDash | P1 | Results template + ops | 🟡 **partial** — `FLASH-SCOREBOARD.md/.jsonl` live, `t_cf7fd6cd` done; gap open in `t_d0277c0b` (tok/s never populated, M2) |
| Capability→workflow→model verb map | SIG-20260807-04 OMH | P1 | Router aliases (`default/private/code/format`) | 🟡 **partial** — `t_d754cc37` lane migration via scoreboard standings (todo); alias hygiene shipped |
| **Capability-aware owner routing** — refuse an owner that can't meet the card's floor | SIG-20260807-04 OMH **v1.0.5** | P1 | Pre-dispatch check vs `MINIMUM_CONTEXT_LENGTH`; would have caught Flash 9/9-eval-vs-1/13-worker | **open — no card** (adjacent, now closed: `t_59505920` diagnosed it by hand) |
| **Capability projection** — send only the tools a request needs | SIG-20260807-04 OMH **v1.0.5** | P1 | Lower the 35.7k worker-prompt floor (complement to W2's ceiling raise, `t_01ac807e` done) | **open — no card** |
| **Restart-durable approval gate** (`decision_gate/v1`) | SIG-20260807-04 OMH **v1.0.5** | P1 | Gate survives dispatcher restart + `recompute_ready()` promotion; today needs a sticky-block comment as a workaround | **open — no card** (workaround live on `t_b02284c0`) |
| Swarm isolation: worktree/lease per worker | SIG-20260807-03 McNab | P1 | Policy before multi-agent coding | 🟡 **partial** — B17 C2.4 + `workspace_kind`/`claim_lock`/`branch_name` in schema |
| **Sticky model mid-thread** (avoid model-hop prefill tax) | SIG-20260808-03 NVIDIA KV transfer | P1 | Don't bounce models mid-session unless worth it | **carded 2026-08-08** `t_c9399728` (blocked: Ryan unblock) |
| **Per-profile side channel while orchestrator busy** | SIG-20260808-05 Agent Dock | P1 | Reach `worker`/`orchestrator` without hijacking default thread | **carded 2026-08-08** `t_647eb43e` (blocked: spike vs native vs drop) |
| Explicit assign-task gate (chat ≠ kanban card) | SIG-20260808-05 Agent Dock | P1 | No card minted unless deliberately toggled | **carded** with `t_647eb43e` |
| Settle captured work as `blocked / needs_input`, never auto-done | SIG-20260808-05 Agent Dock | P1 | Matches HUMAN=Ryan / GREEN-only-on-OK | **carded** with `t_647eb43e` |
| `/refine`-style trajectory→skill patch + diff/accept | SIG-20260807-02 Prime | P1 | skill_manage propose with rollback | **carded 2026-08-08** `t_b6d1a13d` (blocked: Ryan decides) |
| Align C2 fields with multi-concurrency decode bench style | SIG-20260808-04 sparkDash | P1 | bench_concurrency metrics parity | **open — no card** (fold into C2 when the ladders report) |
| Evidence gates / clarify-before-build | SIG-20260807-04 OMH | P1 | "what happened / didn't" in workflows | **open — no card** (adjacent: `t_8b3c9a73` intake-row rule) |
| Same-family cascade skip-reprefill (when engines support) | SIG-20260808-03 NVIDIA KV transfer | P1 | Watch vLLM/SGLang; not DIY maps | watch — no card wanted |

## Backfill debt

The log starts **2026-08-06**. Six research links pasted before that were never captured;
three of them were *actioned anyway* (Herald cutover, Cerebras→operator-surface crucible,
Adamation/TotalAgent→competitive intel + Kevin inbox 168) and read as gaps only because the log
did not exist yet. One is live-relevant: **@miaai_lab 2026-08-05 claims DS4 Flash ~82 tok/s on 2×
Spark**, a third number against our 16.07 measured and Entrpi's 28.6 claimed.
Card: **`t_b5c30927`** (blocked on one scope question — does the log cover competitive intel, or
agent/infra only?).

## Parked (not in rollup)
- kimi-k3-in-c product path — watch only (SIG-20260807-01)
- OMH full install / model-pool sprawl — do not adopt
- Prime curl\|sh as desk primary — spike only if ever
- Cloudflare Computer prod dependency — watch/preview only (SIG-20260808-01)
- codex-router curl install / API-key farm — pattern only (SIG-20260808-02)
- Entrpi one-command installer on Kevin's `spark-b01b` — **Kevin's OK required** (third-party inference engine on a box carrying tunnels + 3 GitHub runners; provenance review + INSTALL-RECEIPT/`ExecStartPre` re-pin before any build). ~~`ds4.service` fails admission~~ **stale — corrected 2026-08-09:** the K5 cutover made the unit the real supervisor (`active`, `NRestarts=0`); the admission failure was the pre-cutover state (SIG-20260808-06)
- danpacary's actual numbers (n=2 repair arm, temp 1.0, no blind-retry control) and his unpublished `evalx` — **steal the method, not the measurements** (SIG-20260809-01)
- OpenKB `pip install` into the T1000 venv — throwaway venv only; pulls `litellm`/`markitdown`/`pymupdf`. Never set `PAGEINDEX_API_KEY` (no-keys rule); Workbench `:7566` ships **auth off by default** — loopback or `OPENKB_API_TOKEN`. Skill Factory stays parked until `agent-skills-estate` audits the ~100 existing skills (SIG-20260809-03)
- Agent Dock `install.py` into `~/.t1000` — Windows-verified only + wants an `executive-organization` board; spike on throwaway `--home` only, on Ryan OK (SIG-20260808-05)
