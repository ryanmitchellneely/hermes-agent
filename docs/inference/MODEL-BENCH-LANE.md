# Model bench lane — how to bench a model on ryan-spark without breaking the fleet

**Script:** `docs/inference/bench_window.sh` (run from the Mac — it needs ssh to
both boxes). **Canon for results:** `BAKEOFF-DS4-VS-QWEN38-FLASH-NEXT.md`.

Every bench on this fleet needs the same sequence. Done by hand on 2026-08-27 it
took five windows, two OOM kills, and one blocked security fence. The script is
that sequence made mechanical; this page is the part a script cannot carry.

## The one-liner

```bash
./bench_window.sh open ngram-mod   # preflight, evict, serve, tunnel, verify
#   ... run your bench against http://127.0.0.1:11439/v1 FROM THE VPS ...
./bench_window.sh close            # restore + verify (fails loudly if not clean)
```

`status` shows lane, residency, and both endpoints without changing anything.

## Topology (the thing that surprises everyone)

**The VPS cannot reach the Spark.** The Spark dials *out*; every path from
k2vps to a model on ryan-spark is a reverse tunnel the Spark opened:

| VPS port | reaches | who uses it |
|---|---|---|
| `11435` | spark ollama :11434 | **the live devbot lane** — never repoint this |
| `11436` | cadenspc ollama | |
| `11439` | spark llama.cpp :8898 | **bench only** (added 2026-08-27) |

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
- **Evict everything.** A 60–120 GB model needs the box. `OLLAMA_KEEP_ALIVE=-1`
  prevents *expiry*, not fresh loads — a client request silently re-pins an
  evicted model, which caused two OOM kills. Check residency immediately before
  a memory-critical step, not once at the start.
- **Reload one model at a time** on close. Parallel loads OOM a 121 GB box.
- **Verify restoration, never assume.** `close` asserts three residents, zero
  stray `llama-server`, and lane endpoint HTTP 200 — and fails loudly otherwise.

## Running the real worker against a bench window

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
