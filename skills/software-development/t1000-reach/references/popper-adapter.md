# Popper adapter (A5) — Sovereign Labs, read-only

## Surface

| Piece | Path / fact |
|-------|-------------|
| Unit | `buzz-agent-t1000.service` on **k2vps** (`User=t1000lab`) |
| Labs tree | `/opt/t1000-lab/labs` · experiments `/opt/t1000-lab/labs/experiments` |
| Registry | `/opt/t1000-lab/labs/registry` (ledger; not auto-enforced) |
| Cadens (non-critical) | VPS loopback `http://127.0.0.1:11436` · warm status `/var/lib/juice/cadens_warm_status.json` |
| Spark (fleet critical) | VPS loopback `http://127.0.0.1:11435` — Popper may escalate here; not Popper-only |
| Identity | OS user `t1000lab` only — isolation template for other agents |

## CLI

```bash
reach popper status
reach popper labs
reach popper findings -- --lab lab-0021-tool-selection --limit 5
REACH_POPPER_LAB='lab-0020' reach popper findings
```

**Write verbs are refused:** `enqueue|run|promote|write` → `error.code=write_forbidden`.

## status grading

| Condition | ok | grade |
|-----------|----|-------|
| unit active + user=t1000lab + experiments tree + Cadens up + warm fresh (≤2h) | true | live |
| unit up, Cadens down (Spark may still be up) | true | stale (`cadens_down`) |
| unit up, both Cadens+Spark down | true | stale (`inference_down`) |
| warm status age > 7200s | true | stale (`cadens_warm_stale`) |
| unit user ≠ t1000lab | true | stale (`user_not_isolated`) |
| unit inactive / ssh fail / labs missing | false | error |

`detail.critical_path` is always **false** — Cadens/Popper downtime must not page the desk as fleet-down.

## labs

Lists experiment dirs with flags: `has_result_md`, `has_results_json`, `has_prereg`, `verdict`, `run_status`, `completed`.

## findings

Read-only extract of `RESULT.md` head and/or compact `results.json` summary (overall verdict + per-arm accuracies). Optional `--lab` substring filter.

## What Popper is not

- Not a chat buddy (use Buzz #labs / human for conversation)
- Not on the critical path (watched-not-paged)
- Not allowed to self-promote or touch production
- Not Cadens-the-GPU as a soul — Cadens is compute for cheap lab runs

## Env

- `K2VPS_HOST` (default `k2vps`)
- `POPPER_UNIT`, `POPPER_ROOT`, `POPPER_LABS`, `POPPER_EXPERIMENTS`
- `POPPER_CADENS_URL`, `POPPER_CADENS_WARM_STATUS`
- `REACH_POPPER_LAB`, `REACH_POPPER_FINDINGS_LIMIT`

## Implementation note (adapter authors)

Remote inventory/findings use **`ssh k2vps bash -s -- args <<'REMOTE'`**, not `ssh "python3 - <<'PY'…"`. Nested `"` in remote Python breaks bash parse of the skill script — see `bash-json-pitfalls.md` §5.

## Smoke (2026-08-04)

- `status` → live, user=t1000lab, Cadens+Spark up, **17** labs / **16** completed
- `lab-0021-tool-selection` → prereg+results.json present, `overall_verdict=PARTIAL`, `status=RAN` (scoreboard rung text may still say False — trust live tree)
- `findings --lab lab-0021` → gpt-oss:120b native **PASS** (first_tool 1.0 / full_seq 0.91); hermes3 native **PARTIAL**
- `enqueue` → `write_forbidden`

## Related

- Charter: `/opt/t1000-lab/labs/CHARTER.md`
- Mesh skill: parent `SKILL.md`
- Fleet note: Cadens tunnel deliberately separate from Spark (`:11436` vs `:11435`)
