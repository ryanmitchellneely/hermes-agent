# Pulp adapter (A4) — T1000-lane

## Surface

| Piece | Path / fact |
|-------|-------------|
| Unit | `buzz-agent-pulp.service` on **k2vps** (User=`pulp`) |
| Auth receipt | `/var/lib/pulp/auth_status.json` (converse-scoped, expiring) |
| Quality | `/var/lib/pulp/quality_status.json` |
| Bridges | `/opt/juice/bridges` · venv `/opt/juice/venv/bin/python` |
| Inference | VPS loopback Spark `http://127.0.0.1:11435` (same tunnel contract as Juice) |
| Buzz body | `buzz-acp` + `buzz_acp_pulp.py` — **not** used for T1000-lane posts |

## CLI

```bash
reach pulp status
reach pulp ask -- --question "What units are down?"
REACH_PULP_QUESTION='…' reach pulp ask
```

## status grading

| Condition | ok | grade |
|-----------|----|-------|
| unit active + authorized unexpired + spark 11435 up | true | live |
| unit up, auth missing/expired | true | stale (`not_authorized`) |
| authorized, spark down | true | stale (`spark_down`) |
| unit inactive / ssh fail | false | error |

## ask contract (T1000-lane)

1. SSH + scp oneshot runner → run with **pulp venv** on VPS.
2. `auth_status()` first — fail closed if not authorized.
3. Import `buzz_acp_pulp._gather_tools` for live read-only context (never raises into crash).
4. `plan()` with **non-owner** sender `t1000-reach` → **no memory recall/write**, no `log_turn`.
5. **Refuse** `remember:` and `done:` prefixes (owner ceremony only).
6. If gather marks **confidential** (commitments/briefs): strip llm_derived; note omission — T1000 has **no** allowlisted Buzz channel.
7. Chat via Spark loopback; optional `_ground_reply` + `flag_stamps`.
8. **Never** post to Buzz / Telegram / mail / Sierra.

## What ask is not

- Not the Buzz @Pulp conversational body (no channel UUID, no `_say` / buzz CLI post).
- Not Carlton/Chamberlain MCP.
- Not a write path into `memory.db`.

## Env

- `K2VPS_HOST` (default `k2vps`)
- `PULP_BRIDGES`, `PULP_VENV_PY`, `PULP_AUTH_REMOTE`
- `REACH_PULP_QUESTION` / `REACH_PULP_TEXT`
- `PULP_CHAT_TIMEOUT` (default 180)

## Smoke (2026-08-04)

- `status` → live, user=pulp, authorized through 2026-08-28, spark up
- `ask "What units are down?"` → `plan_kind=chat`, model `hermes3:8b-16k`, grounded list; grounding retry logged on ungrounded draft figures

## Related

- Charter (docs only): `/opt/buzz/charters/pulp.md`
- Gates: `pulp_core.py` (unit-tested)
- Mesh skill: parent `SKILL.md`
