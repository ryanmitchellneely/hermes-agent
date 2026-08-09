# SPEC: Standings Router

*v1 — drafted 2026-08-09. Every factual claim below was verified on disk or against a live
endpoint on 2026-08-09 unless explicitly marked as an assumption.*

---

## Problem + evidence

**Routing is static config, and the config is allowed to be wrong about reality.**

What routes traffic today, verified:

- `~/.t1000/profiles/worker/config.yaml` and `~/.t1000/profiles/orchestrator/config.yaml` both
  declare `model.provider: spark`, `model.default: gpt-oss:120b`, `ollama_num_ctx: 65536`.
- The `providers:` block declares `context_length` per provider: `spark: 65536`,
  `kevin-spark: 65536`, `mbp-ollama: 32768`.
- Per-card escape hatch: `hermes kanban set-model <task_id> <model> --provider <p>` (verified via
  `--help`), recorded as a `model_override_set` task event.

Nothing in that loop is derived from a measurement. The numbers are asserted by hand, and no
process compares them to what the boxes actually serve.

**The failure this produced, measured, not recalled.** `~/.t1000/kanban/LAB-SCOREBOARD.jsonl`
carries 27 runs with `failure_class: ctx_window_too_small`, spanning
**2026-08-08T18:57:00Z → 2026-08-09T03:37:23Z (~8h40m)**. Every one of them reports the identical
pair:

```
ctx_reported = 32768        ctx_minimum = 64000
```

Split by lane: **21 × `gpt-oss:120b` @ `spark`**, 4 × `opus` @ `claude-acp`,
2 × `deepseek-v4-flash` @ `kevin-spark`. `hermes kanban-lab status` shows
`ctx_window_too_small` as the single largest failure class on the desk
(27 of 63 failures over 7 days — larger than `run_error` 16, `protocol_violation` 13,
`worker_dead` 10, `endpoint_down` 6).

The floor is a hard agent-init gate, not a soft preference:
`~/Documents/T1000/agent/model_metadata.py:390` sets `MINIMUM_CONTEXT_LENGTH = 64_000`, enforced
at `:822` and `:845`. A sub-minimum live probe deliberately **invalidates the cache and refuses to
persist** — startup rejects rather than blessing a 32K window.

**The part that decides this spec's design.** The config *said* `spark: 65536`. The runtime
*served* 32768. A drift-check that only diffs config against config, or config against the
standings table, would have found nothing wrong for nine hours. The default silently pointed at a
lane that could not serve agentic work at all, and the only signal was dispatches dying.
**Drift detection must compare config against a live probe, using the same probe path the agent
itself uses** — anything less reproduces the outage.

**Measurement surfaces already exist. Nothing joins them to routing.**

| Surface | Path | State (verified 2026-08-09) |
|---|---|---|
| Kanban lab scoreboard | `~/.t1000/kanban/LAB-SCOREBOARD.jsonl` (+`.md`), via `~/.t1000/bin/kanban-lab` → `~/.t1000/scripts/kanban_lab_scoreboard.py` | 421 runs/7d, success 188, failed 63, local 89. Per-model `n/ok/fail/wall_p50/link/tok_ok`. **281 of 421 rows have no model recorded at all.** |
| DevBot code scoreboard | `~/.t1000/kanban/FLASH-SCOREBOARD.jsonl` | 17 rows: `apply_ok`, `wall_s`, `prompt/completion_tokens`, `tokens_est`, `is_local`, `saved_usd_vs_frontier`. **Split-brain**: kevin box appends to its own `/home/ryan-lab/.t1000/kanban/FLASH-SCOREBOARD.jsonl`; harvest card `t_700d9953` is open/ready. |
| Golden evals (format lane) | `~/models/eval/{format_golden.py, q4km.json, q4_0.json, caden_hermes3_8b.json}` | Instrument `format_golden v1 (20 cases, format-compliance only)`. Aggregates: `q4km` (hermes3:8b-16k-km @ mbp) pass 0.40 / 0.50s · `q4_0` (hermes3:8b-16k @ spark) pass 0.35 / 1.59s · `caden_hermes3_8b` (@ 4060 :11436) pass 0.25 / 0.81s. All `json_valid_rate 1.0`. |
| D-test protocol | mesh `t_0da022de` (done), harness at `.../workspaces/t_0da022de/d_test_file_fence_goldens.py` | 20/20 FILE-fence goldens, **p50 7.31s vs Flash baseline 24.54s**, free floor ≥19GB, unloaded cleanly, **no alias pivot** — measurement without mutation, exactly the pattern this spec generalizes. |
| MESH-TEL call telemetry | mesh board | `TEL-1 t_ca387cf4` done · `TEL-2 t_e1a86e85` done (decomposition) · `TEL-4 t_08184cd2` done · **`2a t_3a1b8b6b` BLOCKED (sink+schema)** · `2b t_b3a90086` todo (emit) · `2c t_d7f24672` todo (ACP zero-tokens) · `2d t_2545126f` scheduled · `TEL-3 t_02aca524` todo (digest). |

Two findings from MESH-TEL bear directly on ranking and are carried into this design rather than
rediscovered:

1. **`~/.t1000/bin/telemetry-query` exists** (shim → `~/Documents/T1000/scripts/telemetry_query.py`,
   12,387 bytes, written 2026-08-09 07:08) **but `~/.t1000/telemetry/` does not exist.** The reader
   shipped; the emit (2b) has not. There is no call-level stream to rank on today.
2. **`agent/claude_acp_client.py:1103` and `:1237` hardcode `prompt/completion/total_tokens = 0`.**
   Any throughput or cost ranking that ingests claude-acp naively reads it as free and inverts the
   local-vs-subscription picture. Same failure class as the DevBot scoreboard's `tokens_est=true`
   rows.

**The waiting consumer.** Mesh card **`t_d754cc37` "Local-model lane migration via scoreboard
standings()"** (todo, parent `t_05ed9141`, child `t_47f30baf`) is explicitly blocked on this work.
Its body already carries the ratified promotion ladder — **boot (ctx ≥ 64,000) → protocol (N≥3
cards ending `kanban_complete`/`kanban_block`) → quality → throughput (`wall_p50`) → reasoning bump
(`none→low→medium→high`, never prove a local with global `xhigh`)** — plus attachments
`PROMOTION-RUBRIC-t_d754cc37.md` and `AUDIT-2026-08-08-worker-cap-and-lab.md`. Its closing line
names the exact seam this spec fills: *"k2-hub eval/scoreboard.py standings() remains a parallel
instrument for KRT production routing drift; desk kanban lab is the Hermes worker promotion
committee."* This spec builds the desk-side half and reuses the KRT half's hard-won semantics.

**Prior art we must not re-derive.**
`~/Documents/kevin-real-estate-tools/k2-hub/src/k2_hub/eval/scoreboard.py:201` already implements
`standings()` for KRT production routing, and its comments encode failures already paid for:

- Rank **within one instrument only** — a Wilson lower bound (0.4–0.6 for a real win) and a raw
  arena accuracy (~1.0) are not on the same scale; mixing them picks the arena row every time.
- Prefer the **Wilson lower bound** where it exists: *"a 3-case 100% must not outrank a 40-case 67%."*
- `drifted` keeps **three states apart**: nothing-measured is not drift; live-route-unknown is not
  drift; both-known-and-strictly-worse is the only real claim.
- **A tie is not drift.** Two models tied 33/33, recency broke the tie, and the board permanently
  reported production as BEHIND an equal model — *"a board that cries wolf stops being read."*
- `_live_model()` asks the router what routes **right now**, never the table — *"reading the route
  from the same rows would compare a thing to itself."*
- Order by `recorded_at DESC, id DESC` — `recorded_at` has one-second resolution and a sweep writes
  every row in the same second.

**A live drift exists right now, on disk, to test against.** Config alias `spark-format` →
`hermes3:8b-16k` @ spark = the `q4_0` measurement, **pass 0.35**. Measured best on the same
instrument is `q4km` (`hermes3:8b-16k-km` @ mbp-ollama), **pass 0.40**. Production is not on the
best-measured model. It is also `8/20` vs `7/20` on n=20 — well inside noise — so the correct v1
verdict is *"no actionable difference"*, not a flip. The pilot must demonstrate the router has the
spine to say that.

---

## V1 scope

Shippable in 1–2 working sessions. Three artifacts and one pilot.

1. **`capability.py` — live capability probe (read-only).**
   For each provider in a profile, resolve served models and served context length **through the
   same path `agent_init` uses** (`agent/model_metadata.py`), not a hand-rolled GET. Emits
   `~/.t1000/routing/capability.json`: `{provider, endpoint, models[], ctx_served, ctx_declared,
   probe_ok, probed_at}`. This is the component that would have caught 2026-08-08.

2. **`standings.py` — evidence adapters + `standings()`.**
   Read-only adapters normalize existing files into one `Measurement` record —
   `{lane, instrument, model, provider, host, n, metric, metric_lower, wall_p50_s,
   tokens_available, measured_at, source_path}` — from LAB-SCOREBOARD.jsonl,
   FLASH-SCOREBOARD.jsonl, `~/models/eval/*.json`, and D-test result JSON. `standings()` then
   returns one `Standing` per lane with the k2-hub semantics **ported verbatim in behavior**:
   rank within one instrument, prefer the lower bound, tie ≠ drift, unmeasured ≠ drift,
   unknown-live ≠ drift, live route read from config not from the table.

3. **`route_config.py` — the generator.**
   - `--check`: renders what config *would* be, diffs against what config *is* **and** against
     `capability.json`, prints a per-lane report, exits non-zero on drift or capability failure.
     **Never writes.**
   - `--apply --ack <token>`: rewrites only a marker-bounded region of the target profile config.
     Refuses without the ack token. **Writes config; restarts nothing.**
   - `pins.yaml` (`~/.t1000/routing/pins.yaml`): human decisions the generator may never compute
     away. Pins always win; a pin that standings disagrees with renders as `pinned-override`, not
     as drift.

4. **One pilot lane: the format/aux repair lane.**
   Chosen because it is the only lane with a real golden instrument already on disk (three models
   measured on `format_golden v1`), it has a live drift to detect (`spark-format` → 0.35 vs best
   0.40), and it is **non-agentic — it sits entirely below the 64k ctx floor, so a wrong answer
   cannot kill dispatch.** The agentic `worker`/`orchestrator` default is precisely the lane we
   must not pilot on.

**Reporting only, on a schedule:** one `--check` invocation wired report-only, with heartbeat +
surface per the observability principle. No `--apply` on a timer, ever.

---

## Non-goals

- **No auto-promotion.** Nothing flips a lane without Ryan. `--apply` is a human-invoked command
  carrying an ack token; there is no code path from a green measurement to a changed route.
- **No new inference lane, no model pulls, no quant work, no engine changes.** This spec measures
  and generates; it does not provision. 98GB hybrid quant stays NO; engine side-door stays NO.
- **No dependency on the MESH-TEL call stream.** `2a` is blocked and `~/.t1000/telemetry/` does not
  exist. V1 ranks on run-level and golden-level evidence that exists today. The call stream is a
  v2 adapter — additive, and the `Measurement` schema is shaped to accept it.
- **No cross-instrument ranking, no composite score, no "overall best model" leaderboard.** The one
  number that would be most fun to show is the one k2-hub already proved lies.
- **No latency ranking across hosts.** `format_golden.py` states outright that accuracy is
  host-independent but latency is not comparable across hosts. Wall time ranks only within a host.
- **No writes to Sierra, K2, or any product path.** Desk infrastructure only.
- **No change to `max_in_progress_per_profile`, dispatch locking, or the worker cap.** The
  cap=2-vs-running=4 concurrency bug (`AUDIT-2026-08-08-worker-cap-and-lab.md`) is real and
  adjacent and **not this card's problem**.
- **No rewrite of the profile config.** The generator owns a marker-bounded region and nothing else.

---

## Design sketch

### Components and where each runs

| Component | Runs on | Reads | Writes |
|---|---|---|---|
| `capability.py` | MBP (desk), over existing tunnels — no SSH | provider endpoints via `model_metadata` probe path | `~/.t1000/routing/capability.json` |
| `standings.py` | MBP, pure read | LAB + FLASH scoreboards, `~/models/eval/*.json`, D-test JSON | nothing (returns objects; optional `--json`) |
| `route_config.py --check` | MBP, pure read | standings + capability + pins + current configs | nothing (stdout + exit code) |
| `route_config.py --apply` | MBP, human-invoked | same | marker-bounded region of one profile config |
| `pins.yaml` | authored by Ryan | — | — |

Everything is desk-resident and read-only by default. No daemon, no new service, no Mac-resident
runtime dependency introduced into any serving path — the generator's output is a file, and the
boxes are untouched.

### Data sources, and what each is allowed to decide

- **`~/models/eval/*.json`** — the only true *quality* instrument today (`format_golden v1`).
  Drives `best_model` for the pilot lane. Accuracy comparable across hosts; latency is not.
- **`~/.t1000/kanban/LAB-SCOREBOARD.jsonl`** — operational reality: outcomes, `failure_class`,
  `wall_p50`, `tok_s_out`, and the `ctx_reported`/`ctx_minimum` pair. Drives the **boot** and
  **protocol** gates of the ladder. It is *not* a quality instrument and must never render as one —
  the `kanban-lab` docstring's own honesty requirement.
- **`~/.t1000/kanban/FLASH-SCOREBOARD.jsonl`** — `apply_ok` + `wall_s` for the devbot-code lane.
  **Blocked on `t_700d9953`**: the kevin-box copy is not harvested, so this source is knowingly
  partial. Adapter must declare partiality and refuse to rank a lane whose evidence it knows is
  incomplete, rather than rank on the half it can see.
- **D-test JSON** (`t_0da022de` shape: `d_test_pass`, `n`, `apply_ok_pct`, `wall_s_p50/p95`,
  `free_gb_min`, `compared_to_flash_p50`) — the throughput gate's reference format.
- **`capability.json`** — a veto, never a promotion. It can disqualify a model; it can never
  elevate one.

### Lane model

A **lane** is `(profile, task_class)` — e.g. `(worker, agentic)`, `(orchestrator, agentic)`,
`(aux, format)`, `(devbot, code)`. A `Standing` is computed per lane and renders exactly one of
**five** states, never blank:

| State | Meaning |
|---|---|
| `ok` | live model is the best measured, or tied with it |
| `drifted` | a strictly better model, measured on the **same** instrument, exists |
| `unmeasured` | no evidence for this lane at all — the most interesting state, and the one a naive board hides |
| `unknown-live` | the live route could not be resolved; renders as unknown, never as BEHIND |
| `pinned-override` | a human pin governs this lane; standings disagree; the pin wins |

### Config surfaces

The generator owns a bounded region and nothing outside it:

```yaml
# BEGIN standings-router (generated — do not hand-edit; run route_config.py --check)
model:
  provider: spark
  default: gpt-oss:120b
# END standings-router
```

V1's generated region covers **`model.provider`, `model.default`, and `agent.reasoning_overrides`
entries for local models only.** Everything else in the ~2,000-line profile config is out of scope
and must survive `--apply` byte-identical. Hand-edits outside the markers are preserved by
contract and by test.

`pins.yaml` seeds with the standing decisions already made, which the generator must respect as
facts rather than inputs:

- `kevin-spark` / `deepseek-v4-flash` → **per-card only**, not a profile default, until the W4
  dual-ack closes. Verified live: `t_a97cf1e6` is open with Ryan's half-ack lodged 2026-08-09 08:06
  (*"ACK pivot-D, contingent on Kevin's ack"*) and Kevin's ack outstanding. **A model that wins on
  measurements and is pinned per-card must render `pinned-override`, and the generator must emit
  nothing for it.**
- `4060` / CadensPC → **never load-bearing, non-agentic only.** (Probed live: `:11436` up, serving
  `mistral:7b`; scored 0.25 on the format golden. Boot/autostart still pending — `t_47f30baf`.)
- `mbp-ollama` → `context_length: 32768`, **structurally ineligible for any agentic lane.** This one
  is checkable statically, with no probe at all.
- `98GB hybrid quant: NO`, `engine side-door: NO` — standing defaults from the W4 packet.

---

## Gates & risks

### Needs Ryan's ack

1. **Any `--apply`.** The ack token is per-invocation, not a stored setting. No token, no write.
2. **`pins.yaml` initial contents.** Pins encode human decisions; an agent may propose the file and
   must not author the rulings in it.
3. **The pilot lane's first real route change**, if the pilot ever produces an actionable verdict.
   (On today's numbers it should not — 8/20 vs 7/20 is noise.)

### Restart-path

`kanban.dispatch_in_gateway: true` in both profiles — dispatch runs **inside the gateway**.
Changing the `orchestrator` profile's `model.default` therefore does not reliably take effect until
the gateway restarts, and a gateway restart interrupts in-flight dispatch. Two consequences,
both binding:

- **`--apply` writes config and restarts nothing.** Taking the change live is a separate,
  explicitly-scheduled act.
- **No card that restarts a serving lane may be born ready.** The restart card is born blocked and
  carries the dspark precedent (`t_716141c4`) in full: snapshot the pre-change command verbatim,
  record the **baseline before** the change, change **one variable**, gate on it, and document the
  rollback in the summary **even if it was not needed**. Its gate language is the standard —
  *"If apply_ok regresses at all → mandatory rollback (lane unattended)."*

### Blast radius

Measured, not hypothesized: a wrong `model.default` on an agentic profile cost **27 dead runs
across ~8h40m** and produced no alert. That is the worst case this system can cause and the worst
case it exists to prevent. The pilot lane is deliberately chosen so that a v1 bug cannot reach it:
the format lane is non-agentic and below the ctx floor.

### Failure modes, and the mitigation for each

| Failure mode | Why it is real | Mitigation |
|---|---|---|
| **Probe false-negative on Ollama.** `num_ctx` is a per-request parameter; a naive `/v1/models` GET can report a smaller window than the lane would actually get, condemning a healthy model. | The 21 `gpt-oss:120b` failures reported 32768 while config claimed 65536 — the two disagree and only one probe path is authoritative. | Probe through `agent/model_metadata.py`'s own path. If the agent would accept it, the router must accept it, and vice versa. Never a second opinion. |
| **Ranking on partial evidence.** Kevin-box DevBot rows never reach the Mac SoT (`t_700d9953`). | Verified: rows append to `/home/ryan-lab/.t1000/kanban/FLASH-SCOREBOARD.jsonl`, Mac copy has 17 rows. | Adapter declares source completeness. An incomplete source yields `unmeasured`, never a confident ranking. Fail loud, not quietly-wrong. |
| **claude-acp reads as free.** Hardcoded zero tokens at `claude_acp_client.py:1103/:1237`. | Verified in the MESH-TEL-2 handoff. | `tokens_available: false` is a required field; rows carrying it are excluded from throughput/cost ranking and included in quality ranking. |
| **Model attribution gap.** 281 of 421 lab rows have no model recorded — model/effort are only written on explicit override. | `kanban-lab status` `(unset): n=281`. | Unattributed rows count toward *volume* only, never toward a model's score. State it on every report; never silently drop them. |
| **`n` too small.** The pilot's own live drift is 8/20 vs 7/20. | On disk today. | Lower-bound ranking; a difference whose intervals overlap renders `ok`, not `drifted`. This is the primary correctness test. |
| **Generator clobbers hand config.** ~2,000 lines of unrelated settings per profile. | — | Marker-bounded region; byte-identical round-trip test on everything outside it; `--check` verifies config mtime is unchanged after a check run. |
| **Global `reasoning_effort: xhigh`.** Set in *both* profiles today, while the ratified ladder says never prove a local with global `xhigh` and Ollama must never receive it. | Verified in both config files. | The generator emits per-model `reasoning_overrides` as a YAML **dict** and never touches the global value in v1 — flagged in `--check` output as a standing inconsistency for Ryan, not auto-corrected. |
| **A pin gets computed away.** The W4 decision is live and unresolved. | `t_a97cf1e6` open with a half-ack. | Pins are loaded before standings and applied after; a pinned lane emits nothing regardless of score. Regression test: a pinned lane with a winning challenger must render `pinned-override` and produce an empty diff. |

---

## Acceptance criteria

**Capability probe**

1. Replaying the recorded 2026-08-08 evidence, `--check` flags `gpt-oss:120b @ spark` as
   `capability-fail` with `ctx_served=32768 < 64000` and exits non-zero — i.e. the tool reproduces
   the incident from evidence it would have had at the time.
2. `capability.json` reports `ctx_declared` and `ctx_served` as separate fields for every provider,
   and `--check` fails when they disagree, in either direction.
3. `mbp-ollama` is reported structurally ineligible for every agentic lane with no probe required.

**Standings**

4. Every lane renders exactly one of `ok | drifted | unmeasured | unknown-live | pinned-override`.
   Zero lanes render blank or unlabeled.
5. Synthetic-tie test: two models with equal metrics on one instrument render `ok`, not `drifted`.
6. Small-`n` test: 3-case 100% does **not** outrank 40-case 67% on the same instrument.
7. Cross-instrument test: a golden-eval row and a lab-outcome row for the same lane are never
   compared; the report names which instrument each verdict came from.
8. On today's real data the pilot lane renders **`ok` with an explicit "difference not actionable
   (n=20, intervals overlap)" note** — not a flip to `q4km`.
9. Rows with `tokens_available: false` are absent from any throughput or cost ranking, and the
   report says so rather than omitting them silently.

**Generator**

10. `--check` writes nothing: config file mtimes and hashes are identical before and after.
11. `--apply` without a valid ack token exits non-zero and writes nothing.
12. Round-trip: `--apply` then `--check` reports clean.
13. Content outside the `BEGIN/END standings-router` markers is byte-identical after `--apply`,
    verified on a config carrying a deliberate hand-edit.
14. The generator refuses to emit for any lane not in the pilot allowlist, and refuses to emit for a
    pinned lane even when standings favor a challenger.
15. `--apply` restarts no process. Verified: gateway PID and all worker PIDs are unchanged across an
    apply.

**Operational**

16. The scheduled `--check` registers a heartbeat and surfaces its result; a failed run alerts
    rather than failing silently (observability principle — the exact rule LBIS violated).
17. `t_d754cc37` can consume the output: `standings --json` returns the per-lane records that card's
    migration ladder needs, and a comment on that card cites the artifact paths.

---

## Card decomposition

Ordered. Board: **mesh**. Parents refer to card ids in this list unless a `t_` id is given.
Born-status: **ready** = dispatchable now · **todo** = auto-promotes when parents complete ·
**blocked** = human gate, no agent may self-clear.

---

**SR-1 — Capability probe: what each provider actually serves**
> Build `~/.t1000/routing/capability.py`. For every provider in `~/.t1000/profiles/*/config.yaml`,
> resolve served models and served context length **through `~/Documents/T1000/agent/model_metadata.py`'s
> own probe path** — not a hand-rolled GET; if the agent would accept the window, this must too.
> Emit `~/.t1000/routing/capability.json` with `{provider, endpoint, models[], ctx_declared,
> ctx_served, probe_ok, probed_at}`. `ctx_declared` comes from config, `ctx_served` from the probe;
> they are separate fields and disagreement is the headline. Read-only: no config writes, no
> restarts, no model loads. Ryan Spark has global `OLLAMA_KEEP_ALIVE=-1` — if any probe path could
> load a model, pass `keep_alive` ≤ 10m, or an un-TTL'd load pins it forever.
> **Parents:** none · **Born: ready**

**SR-2 — Evidence adapters + `Measurement` schema**
> Define one normalized record — `{lane, instrument, model, provider, host, n, metric,
> metric_lower, wall_p50_s, tokens_available, measured_at, source_path, source_complete}` — and
> write read-only adapters for the four sources that exist today:
> `~/.t1000/kanban/LAB-SCOREBOARD.jsonl` (421 rows; 281 have no model — count them as volume only,
> never as a model's score), `~/.t1000/kanban/FLASH-SCOREBOARD.jsonl` (17 rows; set
> `source_complete: false` — the kevin-box copy is unharvested per `t_700d9953`),
> `~/models/eval/*.json` (`format_golden v1`), and D-test JSON (`t_0da022de` shape).
> `tokens_available` is REQUIRED, not optional: `claude_acp_client.py:1103/:1237` hardcode zero
> tokens, and stored naively that makes claude-acp read as free. Do NOT depend on
> `~/.t1000/telemetry/` — it does not exist and its sink card `t_3a1b8b6b` is blocked.
> **Parents:** none · **Born: ready**

**SR-3 — `standings()`: port the KRT semantics, do not reinvent them**
> Implement `standings()` returning one `Standing` per lane. **Read
> `~/Documents/kevin-real-estate-tools/k2-hub/src/k2_hub/eval/scoreboard.py:201` first and port its
> behavior** — its comments encode outages already paid for: rank within ONE instrument (scales
> differ); prefer the Wilson lower bound (3-case 100% must not beat 40-case 67%); a TIE is not
> drift; nothing-measured is not drift; unknown-live is not drift; read the live route from config,
> never from the evidence table; order by `recorded_at DESC, id DESC` because timestamps have
> one-second resolution. Render exactly five states: `ok | drifted | unmeasured | unknown-live |
> pinned-override`. Ship the tie test, the small-`n` test, and the cross-instrument test with the
> function. Capability (SR-1) is a VETO only — it disqualifies, never promotes.
> **Parents:** SR-1, SR-2 · **Born: todo**

**SR-4 — `pins.yaml` loader + schema (loader only; Ryan authors the contents)**
> Define and load `~/.t1000/routing/pins.yaml`: human decisions the generator may never compute
> away. Schema per pin: `{lane|provider|model, mode: per-card-only|forbidden|forced, reason,
> decided_by, decided_at, review_after}`. Pins load BEFORE standings and apply AFTER: a pinned lane
> emits nothing regardless of score and renders `pinned-override`, not `drifted`. Ship the
> regression test that matters — a pinned lane with a strictly-winning challenger must produce an
> EMPTY diff. Write the loader and a commented example file only; do not author the rulings.
> **Parents:** none · **Born: ready**

**SR-5 — Ryan authors the initial pins**
> Human decision card. Populate `~/.t1000/routing/pins.yaml` with the standing rulings so the
> generator treats them as facts: (1) `kevin-spark`/`deepseek-v4-flash` = **per-card-only**, not a
> profile default, until W4 dual-ack `t_a97cf1e6` closes — Ryan's half-ack is lodged (2026-08-09
> 08:06, *"ACK pivot-D, contingent on Kevin's ack"*), Kevin's is outstanding; (2) CadensPC/4060 =
> never load-bearing, non-agentic only; (3) `mbp-ollama` @ 32768 = ineligible for every agentic
> lane; (4) 98GB hybrid quant NO, engine side-door NO. Each pin needs a `review_after` date so the
> file cannot quietly become permanent. No agent may self-clear this card.
> **Parents:** SR-4 · **Born: blocked**

**SR-6 — Generator `--check`: drift report, writes nothing**
> Build `~/.t1000/routing/route_config.py --check`. Render what the marker-bounded config region
> WOULD be from standings + pins + capability, diff it against the current config, and print one row
> per lane naming the instrument each verdict came from. Exit non-zero on drift or capability
> failure. **Never writes** — assert config mtimes and hashes are unchanged after a run, in a test.
> Also surface, without auto-correcting: `agent.reasoning_effort: xhigh` is set globally in BOTH
> profiles while the ratified ladder forbids proving locals under global `xhigh` and Ollama must
> never receive it. Acceptance: replaying the 2026-08-08 evidence, this flags `gpt-oss:120b @ spark`
> as `capability-fail` (`ctx_served 32768 < 64000`) and exits non-zero.
> **Parents:** SR-3, SR-4 · **Born: todo**

**SR-7 — Ryan reads the first `--check` report**
> Human decision card. Run `route_config.py --check` and read the full output before any `--apply`
> code path is trusted. Confirm three things: (a) no lane renders blank; (b) the pilot format lane
> renders `ok` with "difference not actionable (n=20, intervals overlap)" — 8/20 `q4km` vs 7/20
> `q4_0` is noise, and if the tool calls that a flip, it has no spine and SR-3 goes back; (c) the
> pinned kevin-spark lane renders `pinned-override` with an empty diff. Then approve or bounce.
> No agent may self-clear.
> **Parents:** SR-6 · **Born: blocked**

**SR-8 — Generator `--apply`: ack-gated, marker-bounded, restarts nothing**
> Add `--apply --ack <token>`. Rewrites ONLY the region between
> `# BEGIN standings-router` / `# END standings-router` in one profile config — v1 region is
> `model.provider`, `model.default`, and `agent.reasoning_overrides` entries for local models
> (YAML **dict**, never a string). Refuse without a valid token; refuse for any lane outside the
> pilot allowlist; refuse for any pinned lane. **Restart nothing** — assert gateway and worker PIDs
> are unchanged across an apply, in a test. Ship the byte-identical round-trip test on a config
> carrying a deliberate hand-edit outside the markers. Taking a change LIVE is SR-9, not this card.
> **Parents:** SR-7 · **Born: todo**

**SR-9 — Pilot apply on the format lane, in its own restart window**
> **Born blocked because this is the first card that can change what actually serves.** Follow the
> dspark precedent `t_716141c4` exactly: snapshot the pre-change config/command verbatim for
> rollback; record the BASELINE before touching anything (`format_golden v1` pass_rate + mean_wall,
> per host); change ONE variable; then gate. Gate: format-lane `json_valid_rate` must not regress at
> all and `pass_rate` must be ≥ baseline — **any regression → mandatory rollback**, lane is
> unattended. Latency is NOT comparable across hosts (`format_golden.py` says so) — compare wall
> only within a host. Document the rollback in the summary even if it was not needed. Do not touch
> the agentic `worker`/`orchestrator` default on this card. `kanban_block(needs_input)` rather than
> free-fire if anything is ambiguous.
> **Parents:** SR-8 · **Born: blocked**

**SR-10 — Scheduled `--check`, report-only, with a heartbeat**
> Wire `route_config.py --check` to run on a schedule, report-only. Per the observability principle,
> a scheduled job that cannot be seen does not count: it must register, heartbeat, surface its
> result where Ryan already looks, and **alert on failure rather than failing silently** — a
> drift-detector that dies quietly recreates the exact 8h40m blind spot it exists to close.
> `--apply` on a timer is forbidden; the schedule may only ever report. Include the run in whatever
> desk digest already exists rather than inventing a new surface.
> **Parents:** SR-6 · **Born: todo**

**SR-11 — Hand the artifact to the waiting consumer**
> Comment on mesh card `t_d754cc37` ("Local-model lane migration via scoreboard standings()") with
> absolute artifact paths, the `standings --json` record shape, and how its ratified ladder maps
> onto the implemented gates: boot → SR-1 capability (`ctx ≥ 64_000`); protocol + throughput → SR-2
> lab adapter (`kanban_complete`/`kanban_block` outcomes, `wall_p50`); quality → SR-2 golden
> adapter. Name explicitly what v1 does NOT provide — no auto-promotion, no call-level telemetry
> (`t_3a1b8b6b` blocked, `~/.t1000/telemetry/` absent), FLASH evidence partial until `t_700d9953`
> harvests the kevin-box rows — so the next agent does not assume a gate exists that does not.
> **Parents:** SR-3, SR-6 · **Born: todo**

---

## Open questions

1. Is a lane keyed on `(profile, task_class)` the right grain, or does the desk actually route per
   **alias** (`spark-format`, `spark-code`, `private`, `ds4`), which would make the alias block —
   not `model.default` — the real config surface the generator should own?
2. When a lane's evidence is `source_complete: false` (FLASH until `t_700d9953` lands), should
   `--check` render it `unmeasured` and stay silent, or render a distinct `partial-evidence` state
   that is loud but non-blocking?
3. Should `--apply` refuse outright while any pin's `review_after` date has passed, on the grounds
   that an expired human decision is exactly the stale input that let the orchestrator default rot
   for nine hours?
