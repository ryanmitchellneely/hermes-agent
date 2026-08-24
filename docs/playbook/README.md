# Failure playbook — retrieval-enforced known-error memory

**Origin:** Ryan's directive, 2026-08-18 ("for things that break, it should keep a
playbook that it learns from and can solve repetitive problems over and over").
Design ruled via mesh card `t_c3a4b01d`. Proof case: on 2026-08-17/18 two worker
runs and a false completion re-diagnosed and re-fixed a cap-enforcement bug that
`652ec52669` had already fixed — with tests — five days earlier. One lookup would
have prevented all of it.

## The gap is retrieval, not writing

The fleet already *writes* findings down (mesh card comments, K2 KB pages, lane
docs, session memory). Nothing forces an agent or a human hitting a failure to
*check* before re-solving. So the design puts the lookup into the failure path
itself, where it cannot be skipped by forgetting.

## Shape

- **Entries** live here, one file per failure class: `PB-NNN-slug.md` with
  frontmatter (`id`, `match` — grep-able patterns over failure text, `class`,
  `verified` date, `sources` — commits/PRs/cards). Body: **Symptom → Diagnosis →
  Fix → Don't**. Canonical in the T1000 repo (git is the history mechanism);
  the running gateway reads its own checkout.
- **Retrieval hook (v0):** a sweep (`scripts/playbook_sweep.py`, stdlib-only)
  runs on the ops pulse, scans recent `blocked`/`crashed` kanban runs across
  boards, greps their failure summaries against every entry's `match` patterns,
  and **comments the hit on the card**: `PLAYBOOK HIT PB-NNN: <diagnosis> →
  <fix>`. The next reader — worker, session, or human — sees the known answer
  on the failure itself, within minutes. No dispatcher-core changes; the sweep
  is an ordinary observable organ (heartbeat + surface per the K2 observability
  principle).
- **Write discipline:** any failure a session resolves that had no hit becomes a
  new entry in the same change that fixes it. A `repair:` instruction is code
  that runs somewhere specific: write it for the EXECUTING runtime (k2vps as
  `t1000` since the 2026-08-19 flip -- absolute Linux paths, never `~` or Mac
  paths/commands) and **execute every command in that runtime once before
  arming it**. All five armed entries carried dead Mac paths until 2026-08-24
  (`a0a56d8db`) because the signed PB-002 template was never re-run post-flip. The sweep also surfaces
  no-hit-blocked cards as entry candidates, so the corpus grows from real
  misses, not speculation.
- **Staleness:** entries carry `verified` + `sources`. v0: the sweep warns on
  entries >90 days unverified (K2's wiki-staleness pattern, date-based).
  Re-verify or retire; a wrong entry is worse than none.
- **Success test** (from the card): the next recurrence of a seeded class gets
  resolved by lookup — measured as the sweep commenting the right entry on a
  failing card before a human or session re-derives it.

## What v0 deliberately is not

Not an LLM-retrieval system, not cross-repo unification with K2's KB (separate
decision — touches Kevin's lane), not a dispatcher hook (core changes need the
upstream-generic bar). Grep over ~dozens of entries is exact, free, and
debuggable; escalate only if the corpus outgrows it.
