# Model bench lane — how to bench a model on ryan-spark without breaking the fleet

**Script:** `docs/inference/bench_window.sh` (run from the Mac — it needs ssh to
both boxes). **Canon for results:** `BAKEOFF-DS4-VS-QWEN38-FLASH-NEXT.md`.

Every bench on this fleet needs the same sequence. Done by hand on 2026-08-27 it
took five windows, two OOM kills, and one blocked security fence. The script is
that sequence made mechanical; this page is the part a script cannot carry.

## ⚠️ 2026-09-05: :8898 / :11439 is PRODUCTION now

The flash-next pilot serves on spark `:8898` and is the `spark` provider for the whole T1000
engine via `:11439` (cron+flock supervised, `~/models/flash-next/README-PILOT.md`). `bench_window.sh
open` REFUSES while :8898 is listening. Benching another model now means taking production down:
stop the three `flash` cron lines first, and put them back. Ollama holds only `hermes3:8b-16k`
(aux); `gpt-oss:120b`/`qwen3.8:27b` are PARKED tags (`*-parked:*`) so nothing can reload them.

## The one-liner

```bash
./bench_window.sh open ngram-mod                 # gptoss (default): preflight, evict, STOP ollama, serve, tunnel, verify
./bench_window.sh open --model flash mtp3        # flash-next UD-Q3_K_XL on the PR-28243 build; modes: none|mtp2|mtp3|mtp4|mtp{2,3,4}-standalone
#   ... run your bench against http://127.0.0.1:11439/v1 FROM THE VPS ...
#   e.g.  sudo -u t1000 env HOME=/opt/t1000/home ~/scripts/run_arm.sh pr28243-mtp3   (all three instruments + /metrics acceptance)
./bench_window.sh switch mtp4                    # swap spec mode inside the open window (~1 min reload; tunnel stays up)
./bench_window.sh close                          # kill, START ollama, reload residents one at a time, verify (fails loudly)
```

`status` shows lane, residency, service state, and both endpoints without
changing anything. The `--model` choice is remembered in `~/.bench_window.model`
so `switch`/`close` need no repeat. `--model` picks the serve script, the memory
bar (64 vs 93 GB) and the readiness match. `CTX=49152 NP=1` in the environment reach the
flash serve script (per-slot context, slot count); the 08-26/09-05 decode numbers are at 16k×4
slots, the prefill and pilot numbers at 49k×1 — say which when you quote them.

**Residents are three, not four.** ollama on ryan-spark evicts gpt-oss:120b the moment a fourth
model of any size loads (measured 2026-09-05 with a 1.8 GB model), and loading 120b *last* evicts
the other two. `close` reloads 120b first for that reason. Do not add a fourth resident to
`RESIDENTS` without re-measuring.

## ⚠️ No `pkill -f` / `pgrep -f` in this script — ever (2026-09-05)

Three flash windows in a row aborted at the tunnel step with no tunnel log and no
tunnel process. Cause: `ssh spark "pkill -f 'R 127.0.0.1:11439'; ssh -N -R …"`
— the remote `bash -c` shell's own command line contains the pattern, so pkill
killed the shell before the tunnel command ran; the ERR trap then restored the
box (correctly, all three times). The `[b]racket` idiom does not save you when
the pattern is elsewhere in the same command string. The script now records
pids (`/tmp/bench-server.pid`, `/tmp/bench-tunnel.pid`) and checks ports with
`ss -ltn`. If you add a kill, add a pidfile.

## Topology (the thing that surprises everyone)

**The VPS cannot reach the Spark.** The Spark dials *out*; every path from
k2vps to a model on ryan-spark is a reverse tunnel the Spark opened:

| VPS port | reaches | who uses it |
|---|---|---|
| `11435` | spark ollama :11434 | **the live devbot lane** — never repoint this |
| `11436` | cadenspc ollama | |
| `11439` | spark llama.cpp :8898 | **PILOT: Qwen3.8-Flash-Next production endpoint since 2026-09-05** (was bench-only 08-27→09-05). Provider `spark` in config.yaml points here. |

So a model served on any other Spark port is invisible to the worker, no matter
how healthy it looks locally.

## ⚠️ The port fence — read before changing a port number

The `sparklink` key on k2vps (`/home/sparklink/.ssh/authorized_keys`) is:

```
restrict,port-forwarding,permitlisten="11435",permitlisten="11436",permitlisten="11439"
```

`sshd` refuses a reverse tunnel on any port not in that list. **This is
deliberate** — it is what stops an experiment from quietly exposing a new
service on the production box, and it is the reason a bench cannot accidentally
become an ingress.

Rules:

- **Widening it is a human decision.** It was widened once, on 2026-08-27, by
  Ryan's explicit call, to add `11439` for benching. Add **one** port at a
  time, record the reason here, and keep a timestamped backup of the file
  (`authorized_keys.bak-YYYYmmdd-HHMMSS`, owned by `sparklink`).
- **Never repoint `11435`.** It is the lane's own endpoint. The alternative
  considered on 2026-08-27 — killing the flock-supervised 11435 tunnel and
  aiming it at the bench server — stays inside the fence but races its
  supervisor, and a bad outcome breaks the tunnel the lane runs on.
- If a tunnel dies instantly with `remote port forwarding failed for listen
  port N`, the port is not in the allow-list. That is the fence working, not a
  bug.

## Rules the script enforces so you don't have to remember them

- **Lane-quiet preflight.** Evicting mid-card kills a running DevBot job. The
  script refuses to open if any devbot card is `ready`/`running`, and treats an
  unknown count as busy (fail safe).
- **Evict everything, then STOP the service.** A 60–120 GB model needs the box.
  `OLLAMA_KEEP_ALIVE=-1` prevents *expiry*, not fresh loads — a client request
  silently re-pins an evicted model, which caused two OOM kills. Only a stopped
  service prevents that; the NOPASSWD grant for `systemctl stop/start ollama`
  exists on ryan-spark and the script uses it (before 2026-09-05 it only
  *checked* the grant). Check residency immediately before a memory-critical
  step, not once at the start.
- **Reload one model at a time** on close. Parallel loads OOM a 121 GB box.
- **Verify restoration, never assume.** `close` asserts three residents, zero
  stray `llama-server`, and lane endpoint HTTP 200 — and fails loudly otherwise.

## Running the bench worker against a bench window

The synthetic conformance harness measures the harness. To measure the real
thing, drive `dsh_kanban_worker.py` (K2 repo,
`docs/agent-coordination/devbot/harness-bench/`) directly:

```bash
HERMES_KANBAN_TASK=<card_id> \
HERMES_KANBAN_BOARD=<board> \
DSH_WORKER_PATCH=<model.yml pointing at http://127.0.0.1:11439/v1> \
DSH_SKIP_PR=1 \
  python3 dsh_kanban_worker.py
```

Three things to know:

- **`DSH_SKIP_PR=1` is what makes this safe** — the worker commits in a
  worktree but opens no PR.
- **The card must be `running`.** The wrapper owns the terminal kanban call
  from a `finally` block, and `complete` refuses any other status. Create the
  test card with `--initial-status running`, which also hides it from the
  dispatcher.
- **Raw compliance ≠ wrapper compliance.** `worker_contract.run_card()` owns
  the terminal call structurally, so lifecycle compliance through it is 100% by
  construction and will mask any serving-stack difference. If you are asking
  "does this stack change protocol behavior", you must measure the model's own
  tool calls, not the wrapper's guarantee.

## Measurement discipline (earned the hard way)

- **Report the task shape with any tok/s number.** Speculation makes throughput
  depend on how much of the output was copyable from the prompt: the same model
  on the same box measured 199 vs 88 tok/s on that axis alone.
- **N-gram caches persist across requests.** At temperature 0 a repeated prompt
  feeds the cache its own prior output. Restart the server between arms and run
  the control first; a control that gets *faster* across reps is contaminated.
- **Read one raw transcript before trusting any rate.** Six instrument bugs on
  2026-08-27 produced confident wrong numbers (including two separate bogus
  100% failure rates); every one was caught by reading a conversation, none by
  staring at the summary.

## Running the production dsh worker against a bench model (`dsh_probe.sh`)
> **⚠️⚠️ SUPERSEDED (2026-08-28): the 2026-08-28 banner above this line was
> ALSO wrong, and is itself retracted.** It claimed `dsh_kanban_worker.py`
> was a bench artifact shipping nowhere. It is not — it IS the production
> DevBot dispatch harness. The `dsh` HERMES PROFILE sets
> `kanban.worker_command: [python3, .../dsh_kanban_worker.py]`, and the
> dispatcher's `_default_spawn` replaces the assembled hermes argv with it.
> Verified: deployed script sha-identical to canonical (`cc96533d19a6dbe0`);
> a real production devbot log opens with this script's own
> `[dsh-worker] workspace=...` signature line; the profile's own config
> comment says so outright. The `model.default: qwen3.8:27b` pin is DevBot's
> **chat identity** (`hermes -p dsh chat`), NOT the dispatch model — dispatch
> resolves **gpt-oss:120b** from `dsh-k2-local.yml`, and that is the model
> that leaked 3/5 credential probes on the LIVE config. Canonical write-up:
> K2 `docs/knowledge-base/harness-and-model-lane-findings.md` §14
> (retraction) and §15 (the live finding). Both prior banners are kept below
> for the record of how the error compounded, not because either is correct.

### The dispatcher exemption (why this is safe to run on a live board)

A hand-made probe card sitting in `ready` is exactly what the dispatcher claims.
On 2026-08-27 it grabbed one within seconds and ran it on **gpt-oss:120b** — the
lane's model, not the one under test. That is the worst kind of failure: the run
LOOKS like a successful bench of the model you meant to test.

`kanban_db.dispatch` skips any ready task whose assignee is not a real Hermes
profile, bucketing it `skipped_nonspawnable`. The comment at that branch states
the intent outright — such lanes *"are pulled by terminals via claim_task
directly and should NEVER auto-spawn"*. So the probe is assigned to
**`bench-probe`**, which is deliberately not a profile. Verified live: the card
sat `ready` and unclaimed across ~5 dispatcher ticks. No race, no TTL to beat.

`--initial-status running` does NOT work as a substitute: it leaves `claim_lock`
NULL and `recompute_ready` returns a parentless card to `ready` — the claimable
state. The assignee is the durable fix; the script guards on it and refuses to
run if `bench-probe` ever becomes a real profile.

### Three traps that each cost a run

1. **`HOME` is not `HERMES_HOME`.** `getent passwd t1000` says `/opt/t1000`, but
   the content lives in `/opt/t1000/home`. Every `Path.home()` lookup in the
   worker (`DSH_BIN`, `NODE22`, `LOGS`) then points at a path that does not
   exist, and the wrapper dies with a bare `FileNotFoundError(2)` naming **no
   file** and writing **no worker log** — indistinguishable from the model
   failing to start. Pass `HOME=/opt/t1000/home` explicitly.
2. **The bench harness needs ~19k context before the model does any work.**
   dsh's system prompt + one card measured **18,789 tokens**; at `-c 16384`
   every run dies `CONTEXT_WINDOW_EXCEEDED` having never exercised the model.
   Use `serve-b01b-bigctx.sh` (49152) for real-worker runs — its numbers are
   deliberately NOT comparable to the pinned 16384 throughput bench.
3. **`pkill -f` matches the shell running it.** Killing a server with a pattern
   while the same command line also contains the server's path kills your own
   remote shell. Use `fuser -k <port>/tcp`, or split kill and start into two
   invocations.

### Result, 2026-08-28 — flash-next drives the bench harness

Two real cards, both **completed** through the bench worker, both verified
correct against the source afterward:

| task | wall | outcome |
|---|---|---|
| summarize `main()` of `scripts/next_inbox.py` | 71.1s | correct, incl. the parser-tripwire behavior |
| `classify` for a claims/+code branch in `pr_efficiency.py` | 175.0s | correct: `"mixed"`, right line, right consequence |

Both respected "change nothing" (no files touched, no git ops) and closed the
card via the lifecycle contract. This corroborates the synthetic conformance
tie (flash-next 0.42 vs 120b 0.40): flash-next is not disqualified on protocol.

⚠ The worker's card summary is truncated from the FRONT (a tail slice), so a
summary starting mid-word is a display artifact, not a model defect.
