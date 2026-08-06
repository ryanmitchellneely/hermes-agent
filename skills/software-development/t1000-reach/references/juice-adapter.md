# Juice peer adapter (A2) — live 2026-08-03

Wraps **`sovereign_juice`** at `~/Documents/sovereign-consulting/tools/juice` — **not** the Electron cockpit launched by bare `juice`.

## Verbs

| Verb | What | Needs Spark? |
|------|------|----------------|
| `status` | `python3 -m sovereign_juice status` (v2 JSON) | No (but grade reflects tunnel) |
| `doctor` | `scripts/juice-doctor` text → structured fields | No |
| `classify` | stdin / `REACH_JUICE_TEXT` + `--channel` + mode | **Yes** |
| `triage` | batch; default `--synthetic` | **Yes** |

```bash
~/.t1000/bin/reach juice status
~/.t1000/bin/reach juice doctor
REACH_JUICE_TEXT='Tour Saturday 10am at 14 Birchwood?' \
  ~/.t1000/bin/reach juice classify -- --channel email --synthetic
```

Channels: `email` | `sms` | `call_transcript`.  
Real path: `REACH_JUICE_ALLOW_REAL=1` + `--real` (also needs prior `juice live authorize`).

## Env the adapter sets

Inside `run_sovereign_juice`:

- `SPARK_ENABLED=true` (default) — **required** for classify/triage
- `SPARK_BASE_URL=http://127.0.0.1:11435`
- `PYTHONPATH=.:sovereign_juice` from `JUICE_ROOT`

Without `SPARK_ENABLED`, Juice often exits **0** with:

```json
{"success": false, "error": "SPARK_ENABLED is false"}
```

Adapter must treat that as **failure** (check `intent` present or `success is not false`).

## Grading rules (ops)

Split facets — never one boolean:

- `detail.auth.facet` = `live-authorized` | `synthetic-only` | …
- `detail.model.facet` = `up` | `down` (curl Spark tags/version on 11435)

| Safety + schema | Spark | R0 ladder | ok | grade | typical error.code |
|-----------------|-------|-----------|----|-------|---------------------|
| broken | * | * | false | error | `safety_or_schema` |
| OK | down | * | true | stale | `spark_down` |
| OK | up | proving (baseline unlocked / eval stale / threshold unset) | true | stale | `r0_proving` |
| OK | up | locked + fresh | true | live | — |

Doctor mirrors: `OPERATIONAL: no` + classify UP ⇒ `ok=true` `grade=stale` `not_fully_operational`.

## Safety contract strings

Boundaries must include classify-only + no drafts + no sends (wording may be `live-authorized (real comms, read-only)` instead of `synthetic-only`).

## Implementation map

| Path | Role |
|------|------|
| `scripts/peers/juice.sh` | adapter |
| `JUICE_ROOT/sovereign_juice/` | CLI package |
| `T1000/scripts/juice-doctor` | doctor text |
| `juice/evals/spark_tunnel.sh` | tunnel (shared with spark peer) |

## Smoke (A2)

```bash
R=~/.t1000/bin/reach
"$R" juice status | python3 -c 'import sys,json;d=json.load(sys.stdin);assert d["ok"];assert "auth" in d["detail"] and "model" in d["detail"]'
REACH_JUICE_TEXT='Can we schedule a tour Saturday 10am?' \
  "$R" juice classify -- --channel email --synthetic \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);assert d["ok"];assert d["detail"]["result"].get("intent")'
```

Known good classify shape: `intent` (e.g. `schedule_request`), `urgency`, `entities`, `followup_needed`, `confidence`, `evidence`.
