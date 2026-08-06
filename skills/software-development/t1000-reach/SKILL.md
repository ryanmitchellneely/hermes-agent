---
name: t1000-reach
description: "Use when Ryan asks T1000 to reach Spark, Juice, Pulp, Popper, Kevin/Chamberlain/Carlton, or fleet mesh health. Router CLI `scripts/reach <peer> <verb>` returns reach.receipt.v1 JSON."
version: 1.3.1
author: Ryan / T1000
license: MIT
metadata:
  hermes:
    tags: [t1000, mesh, spark, juice, pulp, popper, chamberlain, reach]
    related_skills: [t1000-spark-tools, t1000-gateway-ha]
---

# T1000 reach mesh

## Overview

Desk **router** from T1000 to fleet peers. Not one protocol — per-peer doors with a shared **receipt**. Spec: `references/SPEC.md`.

**Ryan priority (2026-08-03):** agent↔agent reach (Kevin/Carlton/Chamberlain **and** Spark/Juice/Pulp/Popper) is the north star — more important than Herald feature tourism. Ship L0–L3 doors on 0.17; A2A is later polish.

```bash
REACH="$HOME/.t1000/bin/reach"   # symlink → skill scripts/reach (symlink-safe)
# or: $HOME/.t1000/skills/software-development/t1000-reach/scripts/reach
"$REACH" <peer> <verb> [--json] [-- <peer-args>...]
# JSON receipt on stdout; exit 0 iff ok=true
```

## When to Use

- “Is Spark up?” / tunnel up|down / which models
- “Reach Juice / classify this / juice doctor”
- “Reach Pulp / Popper / Kevin”
- “Mesh health” / fleet status
- Any agent-to-agent handoff that needs a **receipt**

**Don’t use for:** SPARK-gated oneshot tool evals (`comm_comprehension`) — use `t1000-spark-tools`. HA failover — use `t1000-gateway-ha`.

## Peers (v1)

| Peer | Verbs | Status |
|------|-------|--------|
| **spark** (dgx) | status, models, tunnel-up, tunnel-down | **LIVE A1** |
| **juice** (j) | status, doctor, classify, triage | **LIVE A2** |
| **kevin** (chamberlain) | status, notify, inbox | **LIVE A3** |
| **pulp** | status, ask | **LIVE A4** |
| **popper** (labs) | status, labs, findings | **LIVE A5** |
| carlton | inbox | via kevin inbox |
| **all** (mesh) | status | **LIVE B** |

## Agent contract

1. Load this skill.
2. Run `scripts/reach …` (absolute path above).
3. Quote `ok`, `grade`, `receipt.id`, and relevant `detail` to Ryan.
4. **Never claim live without `ok=true` and a fresh `as_of`.**
5. Stubs return `error.code=not_implemented` — say so honestly.
6. Identity rules: do **not** fuse T1000 / Juice / Pulp / Popper / Carlton / Chamberlain credentials.
7. Kevin `notify`: Ryan explicit send OK only; dual gate `REACH_KEVIN_FIRE=1` **and** `--fire`; HA single-writer check; always write inbox on fire.
8. **Never claim Kevin-the-human saw a Telegram message** just because `message_id` returned. See Kevin section below.
9. Pulp `ask`: quote `detail.result.answer`; never post to Buzz; never run `remember:`/`done:` via reach.
10. Popper: read-only (`status|labs|findings`); never claim enqueue/promote; Cadens down = non-critical stale, not fleet page.
11. `reach all status`: quote per-peer grades; mesh may be `ok=true` + `grade=stale` (e.g. Juice R0 proving).
12. When Ryan asks “can you read my texts?” — check `imsg` FDA first; if denied, say so plainly and offer phone copy-paste for Kevin (do not pretend Telegram is his text thread).

## Kevin / Chamberlain (A3) — API reach ≠ human attention

**Canonical CLI:** `reach kevin status|notify|inbox` (alias `chamberlain`).

| Verb | Behavior |
|------|----------|
| `status` | Probe k2vps `/etc/k2-hub.env` (token/chat **presence only**), HA strip, inbox dir |
| `notify` | Default **dry-run**. Live: VPS `sendMessage`/`sendDocument` as 🏛️ Chamberlain via @K2SellsBot |
| `inbox` | Write only `kevin-real-estate-tools/.../inbox-for-kevin-claude/NNN-*.md` |

**Verified rail (2026-08-03/04):** bot `@K2SellsBot` (name Chamberlain) → **private** Telegram user first_name Kevin, last N\*. `message_id` examples: competitive-intel PDF **24326**, mesh smoke **24872**.

### Critical honesty (Ryan correction)

- Kevin’s day-to-day with Ryan is **text/iMessage**, not Telegram.
- Telegram accept + profile name **proves account targeting**, not that Kevin opened the app.
- Report as: **“sent to Kevin’s Chamberlain TG account (message_id=N)”** + inbox path — then **ask Ryan** if human ack is needed on his normal text thread.
- Durable agent path that does not depend on Kevin’s TG habits: **repo inbox** (kevin-claude).
- Open product question remains: Kevin human surface = Buzz / Telegram / SMS / Ryan-relay — do not invent a fourth bot.

### Fire gates

```bash
# dry-run (safe default)
reach kevin notify -- --dry-run --subject "…" --body "…"

# live — BOTH required
REACH_KEVIN_FIRE=1 reach kevin notify -- --fire --subject "…" --body "…"
# optional: --file /path.pdf  --no-inbox
```

Blocks: dual T1000 gateways · missing VPS token/chat · `--fire` without `REACH_KEVIN_FIRE=1`.

Full adapter notes: `references/kevin-adapter.md`.

## Copy-paste

```bash
R="$HOME/.t1000/skills/software-development/t1000-reach/scripts/reach"
"$R" peers
"$R" spark status
"$R" spark models
"$R" spark tunnel-up      # uses juice evals/spark_tunnel.sh
"$R" spark tunnel-down
"$R" juice status         # auth vs model facets; grade may be stale if R0 proving
"$R" juice doctor
REACH_JUICE_TEXT='Tour Saturday 10am?' "$R" juice classify -- --channel email --synthetic
# real comms only with: REACH_JUICE_ALLOW_REAL=1
"$R" kevin status
"$R" kevin notify -- --dry-run --subject "Hi" --body "..."
# live send:
# REACH_KEVIN_FIRE=1 "$R" kevin notify -- --fire --subject "Hi" --body "..."
"$R" pulp status
"$R" pulp ask -- --question "What units are down? Brief."
"$R" popper status
"$R" popper labs
"$R" popper findings -- --lab lab-0021-tool-selection --limit 3
"$R" all status          # mesh health strip
"$R" schema
```

Env overrides: `SPARK_BASE_URL` (default `http://127.0.0.1:11435`), `SPARK_TUNNEL_SCRIPT`, `SPARK_REASON_MODEL`, `SPARK_FORMAT_MODEL`, `SPARK_SSH_HOST`, `SPARK_ENABLED` (default true for juice classify), `REACH_JUICE_TEXT`, `REACH_JUICE_ALLOW_REAL`, `JUICE_ROOT`, `REACH_KEVIN_FIRE`, `REACH_KEVIN_SUBJECT`/`BODY`/`TEXT`/`FILE`, `KEVIN_INBOX_DIR`, `K2VPS_HOST`, `REACH_PULP_QUESTION`, `PULP_BRIDGES`, `PULP_VENV_PY`, `REACH_POPPER_LAB`, `REACH_POPPER_FINDINGS_LIMIT`, `POPPER_UNIT`, `POPPER_EXPERIMENTS`, `POPPER_CADENS_URL`.

## Receipt

`schema_version: reach.receipt.v1` — see `references/receipt.schema.json`.

Grades: `live` | `stale` | `error`. Exit: `0` ok · `1` peer error · `2` usage.

**Important:** `ok=true` + `grade=stale` is a valid healthy-but-not-fully-operational state (e.g. Juice R0 still proving, Spark tunnel up but models incomplete). Do **not** tell Ryan “Juice is down” when `ok=true`.

## Juice grading (A2) — auth ≠ model

See `references/juice-adapter.md`.

| Condition | ok | grade |
|-----------|----|-------|
| status v2 readable + safety boundaries intact + spark up + R0 locked/fresh | true | live |
| status OK + safety OK, but R0 proving (baseline unlocked / eval stale) **or** spark down | true | stale (+ error.code like `r0_proving` / `spark_down`) |
| CLI fail / invalid JSON / boundaries missing classify-only or no-sends | false | error |

Always split in `detail`: `auth.facet` (`live-authorized` \| `synthetic-only`) vs `model.facet` (`up` \| `down`). Never collapse “live-authorized” into “classify works.”

## Common Pitfalls

1. Spark is **compute**, not a chat agent — don’t say “Spark said”.
2. Gateway up ≠ tunnel up — always probe tags URL.
3. Don’t reimplement tunnel logic — wrap `spark_tunnel.sh` (canonical: `sovereign-consulting/tools/juice/evals/spark_tunnel.sh`).
4. `juice` desktop launcher ≠ `sovereign_juice` CLI — A2 calls `python3 -m sovereign_juice` from `JUICE_ROOT`, never boots Electron.
5. Current session may need absolute path / `~/.t1000/bin/reach` until skill cache refresh.
6. **Bash `${var:-{}}` is broken** — appends stray `}` onto real JSON → empty `detail`. Fix: `local x="${8-}"` then default to `'{}'`. See `references/bash-json-pitfalls.md`.
7. **Symlink entrypoint** — resolve `BASH_SOURCE` through `readlink` before `dirname/..` (fixed in `scripts/reach`).
8. **Receipts via env vars are fragile** — use `scripts/lib/emit_receipt.py --detail-file`.
9. **Identity fusion** — no Kevin-tenant MCP / `kermes:write` for T1000; no dual TG gateways; Pulp stays no-send.
10. Stubs stay **honest** only for not-yet-built verbs; spark/juice/kevin/pulp/popper/all are LIVE. Popper enqueue is `write_forbidden`, not a silent no-op.
11. **Juice classify** must export `SPARK_ENABLED=true` (and `SPARK_BASE_URL`) — without it Juice returns exit 0 + `{"success":false,"error":"SPARK_ENABLED is false"}`. Treat `success:false` / missing `intent` as failure even when rc=0.
12. **Real comms seatbelt** — `--real` requires `REACH_JUICE_ALLOW_REAL=1`; default is `--synthetic`.
13. Empty `detail: {}` with `ok: true` is a **receipt bug**, not a green peer — re-run smoke from `references/bash-json-pitfalls.md`.
14. **Kevin TG ≠ Kevin texting Ryan** — never equate `message_id` with human read-receipt; prefer inbox for agents; offer Ryan-relay on his SMS/iMessage thread for human-critical pings.
15. Kevin notify dual gate: `--fire` alone is insufficient without `REACH_KEVIN_FIRE=1` (cron safety).
16. Do not print `TELEGRAM_BOT_TOKEN` or chat IDs — probe presence only (`token_present` / `kevin_chat_present`).
17. **Pulp T1000-lane ≠ Buzz @Pulp** — `reach pulp ask` is SSH oneshot (no channel post). Do not claim “Pulp replied in Buzz.”
18. **Pulp ask blocks** `remember:` / `done:` — memory/commitment writes stay owner-ceremony only.
19. **Pulp confidential** — if gather marks confidential, omit brief content; T1000 has no allowlisted Buzz room (same red-team finding as pulp_confidential).
20. **Pulp ask uses VPS Spark 11435**, not Mac tunnel alone — VPS spark down ⇒ ask fails even if Mac `reach spark status` is live.
21. **Popper Cadens** is non-critical (`critical_path=false`); do not tell Ryan the fleet is down when only :11436 is dark.
22. **Scoreboard vs live tree** — scoreboard.py Popper rungs can lag; prefer `reach popper labs|findings` over dashboard prose. LAB-0021 tool-selection has **run** (results.json, PARTIAL) even when the board still says False.
23. **Remote probe quoting** — never embed multi-line Python with `"` inside `ssh "…"`. Use `ssh host bash -s -- args <<'REMOTE'` (see `references/bash-json-pitfalls.md` §5). Symptom: `unexpected EOF while looking for matching '"'`.
24. **Mesh strip grading (`all status`)** — critical peers = spark/juice/kevin/pulp; optional = popper. Mesh `ok=false` only if a **critical** peer fails; popper/Cadens degrade → `ok=true` + `grade=stale`. Missing peer row = bug (never omit).
25. **imsg FDA** — reading Ryan’s cell Messages requires Full Disk Access on the Hermes host; until granted, cannot text Kevin on the human path — use Chamberlain TG (API only) + inbox + Ryan-relay copy-paste.

## Security / ops controls (from team review)

Full text: `references/team-controls.md`. Load before building A3–A5 or Kevin notify.

## Install (from this repo)

```bash
./skills/software-development/t1000-reach/scripts/install-local.sh
```

Symlinks this tree into `$HERMES_HOME/skills/software-development/t1000-reach` (default `~/.t1000`) and `bin/reach`.

Repo docs: `docs/reach/` · plan: `docs/T1000-KEVIN-AGENT-MESH-PLAN.md`

## Support files

- `references/SPEC.md` — mesh SPEC v1
- `references/receipt.schema.json` — receipt schema
- `references/bash-json-pitfalls.md` — bash `{}` default + symlink + emit path + **ssh bash -s remote probe**
- `references/team-controls.md` — security/ops/DX MUST/MUST-NOT
- `references/juice-adapter.md` — A2 juice verbs, grading, classify recipe
- `references/kevin-adapter.md` — A3 Chamberlain rail, dual gate, human-attention honesty
- `references/pulp-adapter.md` — A4 T1000-lane status/ask (no Buzz post, no memory write)
- `references/popper-adapter.md` — A5 labs status/labs/findings (read-only, no enqueue)
- `scripts/reach` · `scripts/peers/{spark,juice,kevin,pulp,popper,all}.sh` · `scripts/lib/{receipt.sh,emit_receipt.py}`
- bin: `~/.t1000/bin/reach` (symlink-safe)

## Verification Checklist

- [ ] `reach peers` lists spark+juice+kevin+pulp+popper+all as **live**
- [ ] `reach spark status` → non-empty `detail.models` (reason + format present ⇒ live)
- [ ] `reach juice status` → `ok=true`, facets present; grade may be `stale` if R0 proving
- [ ] `reach juice doctor` → structured doctor tail, not raw-only
- [ ] `REACH_JUICE_TEXT='…' reach juice classify -- --channel email --synthetic` → `intent` set
- [ ] `reach kevin status` → rail ready + single_writer_ok
- [ ] `reach kevin notify -- --dry-run …` → composed 🏛️ preview; no send
- [ ] `--fire` without `REACH_KEVIN_FIRE` → `fire_gate` error
- [ ] `reach pulp status` → unit active + authorized + spark facet
- [ ] `reach pulp ask -- --question "What units are down?"` → non-empty `detail.result.answer`
- [ ] `reach pulp ask` with `remember: …` → `mutating_prefix_blocked`
- [ ] `reach popper status` → unit active, user=t1000lab, experiments_summary present
- [ ] `reach popper labs` → count ≥ 1
- [ ] `reach popper findings -- --lab lab-0021` → non-empty findings or honest no_findings
- [ ] `reach popper enqueue` → `write_forbidden`
- [ ] `reach all status` → five peer rows (spark/juice/kevin/pulp/popper); missing peer never omitted
- [ ] `~/.t1000/bin/reach spark status` works via symlink
- [ ] No secrets in receipt JSON
- [ ] Exit codes: 0 ok · 1 peer error · 2 usage

## Related

- Plan: `~/Documents/T1000/docs/T1000-KEVIN-AGENT-MESH-PLAN.md`
- SPEC: `references/SPEC.md` and `~/Documents/T1000/docs/reach/SPEC.md`
- Spark oneshots: skill `t1000-spark-tools` (different from mesh status)
- HA strip: skill `t1000-gateway-ha` (orthogonal — gateway-up ≠ spark-up)
- Chamberlain desk recipe: skill `sovereign-desk` → `references/kevin-chamberlain-delivery.md`
- Next: Kevin one-pager (Buzz surface) · Herald 0.20 calm upgrade · iMessage FDA for human Kevin path
