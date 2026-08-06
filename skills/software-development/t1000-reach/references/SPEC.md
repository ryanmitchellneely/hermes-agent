---
title: T1000 reach mesh — SPEC v1
date: 2026-08-03
status: A0-A5+B live (2026-08-04)
team: security + ops + DX (parallel review 2026-08-03)
---

# SPEC — `reach` mesh (T1000 → peers)

## 1. Problem

T1000 is an excellent desk agent but has **no first-class doors** to Ryan-side fleet peers (Spark, Juice, Pulp, Popper) or Kevin-lane (Chamberlain / inbox). Operators improvise SSH and one-offs; no receipts; easy to fuse identities.

## 2. Goal

One router:

```text
reach <peer> <verb> [--json]
```

- Always returns a **receipt JSON** (stdout)
- Exit `0` iff `ok=true`
- Per-peer adapters; **no shared soul/token**
- A0+A1 ship on **0.17** without Herald

## 3. Non-goals (v1)

- A2A protocol (L4) — post Herald + design
- Importing Pulp into T1000 process
- Kevin-tenant MCP bearer for T1000
- Dual Telegram gateways
- Auto-enqueue Popper labs without human OK
- Replacing repo inbox for code/PR handoffs

## 4. Peers and verbs

| Peer | Aliases | v1 verbs | Layer | Implement |
|------|---------|----------|-------|-----------|
| spark | dgx | status, tunnel-up, tunnel-down, models | L0 | **A1** |
| juice | j | status, doctor, classify, triage | L0 | **A2 LIVE** |
| pulp | — | status, ask | L1 | **A4 LIVE** |
| popper | labs | status, labs, findings | L0/L1 | **A5 LIVE** |
| kevin | chamberlain | status, notify, inbox | L2/L3 | **A3 LIVE** |
| carlton | — | inbox | L3 | stub |
| all | mesh | status | — | **B LIVE** |

## 5. Receipt schema (`reach.receipt.v1`)

Required fields:

| Field | Type | Notes |
|-------|------|-------|
| schema_version | const | `reach.receipt.v1` |
| peer | enum | canonical name |
| verb | string | |
| ok | bool | |
| grade | enum | `live` \| `stale` \| `error` |
| as_of | ISO-8601 | UTC |
| layer | enum | L0–L4 |
| receipt | object | `{kind, id}` |
| detail | object | peer-private |
| error | object? | `{code, message}` if not ok |

`receipt.kind`: `local` \| `http` \| `ssh` \| `path` \| `message_id` \| `none`

### Spark `detail`

```json
{
  "tunnel": {"state": "up|down", "local_url": "http://127.0.0.1:11435", "pid": null, "ssh_host": "spark"},
  "models": {"reason": "gpt-oss:120b|missing", "format": "hermes3:8b-16k|missing", "all": []},
  "tags_ok": true
}
```

**Spark status grading:**

| Condition | ok | grade |
|-----------|----|-------|
| Port up + reason + format models present | true | live |
| Port up, missing expected models | false | stale |
| Port down / curl fail | false | error |

## 6. Team controls (merged)

### Security MUST

1. Receipt on every call — no silent success  
2. Per-peer credentials/adapters only  
3. Fail-closed Kevin notify if dual TG writers possible  
4. Pulp: auth-gated, no send/Sierra/mail — no pulp_core import into gateway  
5. Spark is compute-only  

### Security MUST-NOT

6. No Kevin-tenant MCP / kermes:write for T1000  
7. No identity fusion across peers  
8. No second Telegram bot/gateway  
9. No A2A write verbs without Kevin-ratified map  
10. No unceremonied Popper lab writes  

### Ops

11. Split Juice **auth** vs **model/tunnel** facets  
12. HA strip orthogonal: Mac gateway + HB age + VPS inactive  
13. Gateway-up ≠ Spark-up  
14. Missing peer in `all status` = error row, not omit  
15. VPS promote ≠ full mesh green (Mac-only deps)  

### DX

16. Skill: `~/.t1000/skills/software-development/t1000-reach/`  
17. CLI: `scripts/reach` — JSON stdout, optional human stderr  
18. Unknown peer/verb → structured error, exit 2  
19. Wrap existing tunnel/juice scripts — don't fork logic  
20. Natural language maps to same CLI  

## 7. Layout

```text
~/.t1000/skills/software-development/t1000-reach/
  SKILL.md
  references/SPEC.md          # copy or link to this doc
  references/receipt.schema.json
  scripts/reach               # entrypoint
  scripts/lib/receipt.sh
  scripts/peers/{spark,juice,kevin,pulp,popper,all}.sh
  scripts/peers/_stub.sh
```

Also mirror SPEC into repo: `~/Documents/T1000/docs/reach/SPEC.md`

## 8. A0 / A1 acceptance

- [x] `reach peers` lists all peers
- [x] `reach spark status --json` returns valid receipt (live smoke 2026-08-03)
- [x] `reach juice status` returns `not_implemented` stub (honest)
- [x] Exit codes: 0 ok, 1 peer error, 2 usage
- [x] No secrets in receipts
- [ ] Skill loads via skill_view after new session (document)

**Shipped path:** `~/.t1000/skills/software-development/t1000-reach/` · bin link `~/.t1000/bin/reach`

## 9. Build sequence

A0 skeleton → A1 spark → smoke → A2 juice → A3 kevin → A4 pulp → A5 popper → B all status

## 10. Open questions (not blocking A0/A1)

- Canonical spark_tunnel.sh path (juice evals vs worktree) — resolve at runtime  
- Popper SSH host alias if not `spark` / Cadens  
- Whether `reach pulp ask` uses Buzz CLI or direct ACP  

---

*Ratified for build by three-agent review (security, ops, DX) 2026-08-03. Implement A0+A1 now.*

## 11. A5 / B acceptance (2026-08-04)

- [x] `reach popper status` → live (or honest stale if Cadens down)
- [x] `reach popper labs` → experiment inventory from `/opt/t1000-lab/labs/experiments`
- [x] `reach popper findings` → RESULT.md / results.json summaries
- [x] Popper write verbs fail closed (`write_forbidden`)
- [x] `reach all status` includes every peer row (spark/juice/kevin/pulp/popper)
- [x] Mesh `ok=true` + `grade=stale` valid when Juice R0 proving / optional peer degraded
- [x] Popper marked non-critical in mesh strip
