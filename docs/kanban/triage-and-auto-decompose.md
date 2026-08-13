# Triage and auto-decompose

Triage is an **intake** state: a rough idea that is not yet actionable. A task in
triage cannot be claimed by a worker. It leaves triage through one of two
deliberate edges, both of which call an auxiliary LLM to turn the rough card into
a real spec:

| command | what it does |
|---|---|
| `hermes kanban specify <id>` | tightens the title, writes a goal/approach/acceptance body, flips `triage -> todo` (`kanban_db.specify_triage_task`) |
| `hermes kanban decompose <id>` | fans the card into a graph of child tasks and promotes the root to `todo` (`kanban_db.decompose_triage_task`) |

`recompute_ready` then moves it `todo -> ready` on the next dispatcher tick, or
immediately if it has no open parents.

## Triage is not a dead end — but every other verb says it is

`promote` (including `--force`), `block`, `unblock`, `schedule` and `complete`
all refuse on a triage task, and none of their refusal messages mention `specify`
or `decompose`. Five refusals in a row read as proof that the card is stuck, and
on 2026-08-12 that produced a confident, wrong diagnosis of a severe state-machine
defect — filed as a p55 card, plus three unnecessary card reissues — before an
existing test named `test_specify_promotes_triage_to_todo` revealed the mistake.

Worse, `hermes kanban assign <triage-id> <profile>` **succeeds** and prints
`Assigned ... to <profile>` while leaving the status at `triage`. It reads as
progress and changes nothing about claimability.

If you are looking at a triage card that "won't move": you want `specify`.

## Auto-decompose is deliberately OFF on this box

The gateway has an auto-decompose watcher (`gateway/kanban_watchers.py`) that
drains triage automatically. Its default is **on**. On this machine it is
explicitly **off**:

```yaml
kanban:
  auto_decompose: false
  auto_decompose_per_tick: 0
```

**Why it was turned off (2026-08-08, DS4 residency work).** It did not move
alone. Four settings changed together in the same edit, and all four reduce
background load on the Mac:

| setting | before | after |
|---|---|---|
| `dispatch_interval_seconds` | 60 | 90 |
| `max_in_progress_per_profile` | null (unlimited) | 2 |
| `auto_decompose` | true | false |
| `auto_decompose_per_tick` | 3 | 0 |

This was a coordinated throttle, **not** a judgment that decomposition works
badly. The decomposer runs on `auxiliary.kanban_decomposer`
(`mbp-ollama` / `hermes3:8b`), so leaving it on meant up to three unattended
local LLM calls per 60-second tick competing with DS4 model residency — and the
DS4 wedge is load-triggered.

Reconstructed from `config.yaml.bak-*` backups plus a terminal log, because
`~/.t1000/config.yaml` is **not tracked by git**: the live agent runtime config
has no history, so "who changed this and why" is only ever recoverable by
accident. The flip is bounded to 2026-08-07 21:46 (last seen `true`) →
2026-08-08 11:54 (earliest `false`, in a backup named `ds4-lane`).

### `auto_decompose_per_tick: 0` does nothing

The resolver clamps `per_tick` to `>= 1`:

```python
if per_tick < 1:
    per_tick = 1
```

So a zero there is inert — **the boolean is the only thing holding this off.**
Do not read the `0` as a second layer of protection.

### The toggle is live and fails safe

`_resolve_auto_decompose_settings` re-reads config on **every** dispatcher tick
(#49638), so flipping the flag takes effect on the next tick without a gateway
restart — it is a panic switch for runaway fan-out. On a config-read exception it
returns `(False, 3)`: a transient read error can never re-enable a feature you
turned off.

## Before re-enabling: it cannot be scoped yet

`list_triage_ids()` accepts exactly one filter — `tenant`. There is no predicate
on body length, author, or origin, and the gateway watcher passes no tenant. So
the tick drains **every** triage card on **every** board.

That is the blocker. Turning it on today means an 8B model rewrites the title and
body of every triage card indiscriminately, including cards that carry an
authored human ruling. `specify` replaces the body **wholesale** with generated
JSON — verified live on 2026-08-12 against a throwaway card. A Ryan-gated policy
card sitting in triage would have its ruling overwritten.

`tenant` is the one seam that already exists: `create --tenant` and
`list_triage_ids(tenant=...)` are both plumbed. Scoping the watcher to a tenant
(so machine-generated intake auto-decomposes and authored cards do not) is a
small code change, not a config flip.

**Do not re-enable until at least one of these is true:**

1. The watcher can be scoped — by tenant, by `created_by`, or by a
   "rough intake only" marker — so authored cards are never rewritten; and
2. The local-model load reason has lapsed (DS4 residency no longer contends for
   the Mac), or the decomposer is pointed at a non-local provider.

Until then, `hermes kanban specify <id>` by hand is the intended path — and note
that a card which is already fully written does not want specifying at all, since
that would only degrade it.
