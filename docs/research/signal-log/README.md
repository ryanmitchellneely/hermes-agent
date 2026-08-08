# Signal log — mechanical capture

**Purpose:** Every X/blog/repo flex Ryan pastes for “research/review” becomes a **fixed-schema entry**, not a chat novel.  
**SoT:** this directory under T1000 docs.  
**Owner:** Ryan + T1000. **Never** install from a signal without explicit OK.

## One-command flow (agent or Ryan)

When Ryan drops a URL / “review this” / “any cool ideas”:

```text
1. FETCH   primary post + canonical repo/docs (if any)
2. CLASS   bucket + confidence (see enums)
3. WRITE   entries/YYYY-MM-DD_<slug>.md from TEMPLATE.md
4. LEDGER  one new row at TOP of INDEX.md
5. STEALS  only rows with steal_rank ∈ {P0,P1} get “Next action”
6. WIRE    if Next action is backlog → kanban comment or AUTOMATION-ROADMAP ID
7. REPLY   short chat: ID + bucket + top 1–3 steals + path
```

**Do not:** re-litigate full essay in chat if entry exists — link the entry.

## Enums (do not invent new ones casually)

### `bucket`
| Value | Meaning |
|-------|---------|
| `harness` | Agent OS / coding harness / Hermes overlay |
| `inference` | Serve, quant, tok/s, concurrency, engines |
| `models` | Weights, MoE, open checkpoints |
| `router` | Multi-model routing, privacy dial, verbs |
| `ops` | HA, gateway, crons, observability |
| `product` | GTM/packaging ideas for Sovereign/K2 |
| `noise` | Hype only — log and park |

### `posture`
| Value | Meaning |
|-------|---------|
| `watch` | Cite later; no build |
| `steal` | Copy a **pattern** into T1000 (not their install) |
| `spike` | Disposable trial, non-prod only |
| `adopt` | Rare — becomes SoT dependency (needs Ryan + usually Fable) |
| `ignore` | Logged so we don’t re-open |

### `steal_rank`
| Value | Meaning |
|-------|---------|
| `P0` | Do in current quarter / open plan |
| `P1` | Backlog when calm |
| `P2` | Nice; no ticket yet |
| `—` | No steal |

### `confidence`
`high` | `medium` | `low` — how much we trust the claim after fetch (not vibes).

## Files

| Path | Role |
|------|------|
| `INDEX.md` | Newest-first ledger (one line per signal) |
| `TEMPLATE.md` | Copy for every entry |
| `entries/*.md` | Full writeups |
| `STEALS.md` | Rollup of open P0/P1 steals only |
| `../../scripts/signal_log_new.py` | Scaffold entry + INDEX row |

## Chat triggers → this system

| Ryan says | Agent does |
|-----------|------------|
| URL + “research/review” | Full flow 1–7 |
| “ideas from X” / “rip from here” | Flow + emphasize STEALS |
| “log it” | Entry + INDEX only |
| “running ideas doc” | Point at `INDEX.md` + `STEALS.md` |

## Hard rules

1. **Reference required** — X status URL and/or repo; no orphan takes.  
2. **Takeaway ≤ 5 bullets** in entry; steals are separate table.  
3. **No curl\|sh** onto `~/.t1000` from a signal.  
4. **One primary steal recommendation** max per signal (prevents idea obesity).  
5. Duplicate URL → update existing entry, don’t fork.

## Related

- Skills: `agent-harness-compare`, `local-inference-fleet`  
- Plan: `~/.hermes/plans/2026-08-06_222342-spark-inference-experiments.md` (B17)  
- Backlog: AUTOMATION-ROADMAP B17; kanban mesh `t_99c5d345`
