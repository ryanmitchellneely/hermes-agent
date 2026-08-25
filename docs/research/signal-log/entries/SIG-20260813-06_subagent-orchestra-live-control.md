# SIG-20260813-06 — Teknium: parent Hermes can SPAWN / LIST / STEER / STOP subagents with live transcripts (“Subagent Orchestra”)

```yaml
id: SIG-20260813-06
date: 2026-08-13
title: "Teknium: 'Your Hermes can now steer, end, and read live transcripts of what your sub-agents are doing' while they work async. Marketing graphic SUBAGENT ORCHESTRA: SPAWN (mothership+drones, dispatch returns ids) · LIST (sa-0/sa-1 RUNNING + race-standings telemetry) · STEER (new course, no pit stop) · STOP/HALT (partial result still returns). Cross-check T1000 tree: tools/delegate_tool.py already has steer_subagent() + live transcript writers + interrupt path — feature is in-engine; steal is making parent-visible controls + LIST telemetry the default agent UX, not fire-and-forget delegate_task."
index_title: "Subagent Orchestra (Teknium): SPAWN/LIST/STEER/STOP + live transcripts. T1000 already has steer_subagent + live transcript plumbing in delegate_tool — gap is parent tool surface + default UX, not greenfield. P1: expose list/steer/stop/transcript to parent; teach orchestrator when to steer vs kill."
source_url: "https://x.com/Teknium/status/2087986084592709814"
canonical_repo: "https://github.com/NousResearch/hermes-agent"
canonical_docs: ""
index_links: [repo]
bucket: harness
posture: steal
steal_rank: P1
confidence: high
hardware_fit: [mbp, spark, vps]
stacks_touched: [t1000]
related_plans:
  - "agent-harness-compare"
  - "SIG-20260813-04"   # coworkers vs nested subagents — complementary
  - "kanban workers"     # durable board ≠ ephemeral subagents
status: open
status_note: "**OPEN — confirm parent-visible tool schema on live desk before carding.** Code already contains steer_subagent + create_live_transcripts; this session's tool list still looks like fire-and-forget delegate_task. Verify which build/gateway exposes LIST/STEER/STOP to the parent model."
distill: none
```

## 1. Claim

[@Teknium](https://x.com/Teknium/status/2087986084592709814) (726 likes / 48 RT / 239 bookmarks / ~38k views):

> New in Hermes Agent: Your Hermes can now **steer, end, and read live transcripts** of what your sub-agents are doing. Let your agent have full control over all of its subagents while they work async!

Graphic: **SUBAGENT ORCHESTRA — live delegation control** (Nous Research).

## 2. What we verified

| Panel | Claim on graphic |
|---|---|
| SPAWN | Mothership + drones; **dispatch returns ids** |
| LIST | `sa-0`/`sa-1` **RUNNING** + elapsed + **race-standings telemetry** |
| STEER | Course change mid-flight — *“new course, no pit stop”* |
| STOP | HALT — *“partial result still returns”* |

**Local tree (T1000 checkout, read live):**
- `tools/delegate_tool.py`: **`steer_subagent(subagent_id, text)`** — queues guidance at next iteration boundary without cutting current tool call; returns bool
- Same module: **live transcripts** (`create_live_transcripts`, per-task append log, finalize markers)
- Interrupt/stop path referenced as mirror of steer (`interrupt_subagent` family in comments)
- Parent session tool surface in *this* Telegram session still presents **`delegate_task`** as the primary API — LIST/STEER/STOP may be newer schema or UI-only in Desktop/TUI

So: **not vapor** relative to our fork; **productization + default exposure** is the news.

## 3. Takeaways (max 5)

- Nested subagents without mid-flight control are how you get silent thrash; Orchestra is the antidote.
- **IDs from spawn** are load-bearing — without stable ids, steer/stop are theater.
- STOP must return **partial** — matches our kanban kill/reclaim doctrine (don’t void work).
- Orthogonal to Bot Mode (profile coworkers): Orchestra = *inside one session*; Bot Mode = *across durable identities*.
- Pair with dual-claimer width control: more live children without LIST is how N≫cap happens.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Parent tools: list / steer / stop / read_transcript** for in-flight children | Verify live tool schema; if missing, wire thin wrappers over existing `steer_subagent` + registry + transcript paths; teach orchestrator skill | **P1** | open |
| S2 | Spawn returns structured ids + status board (race-standings) | `delegate_task` result already has handles — surface running table in parent progress | P2 | fold |
| S3 | Stop → partial result contract | Document in kanban-worker + delegate skill: kill is not discard | P2 | doctrine |

**Primary steal:** S1

## 5. Do not

- Treat this as permission to raise kanban cap.
- Build a second delegation runtime — extend `delegate_tool` / async_delegation.
- Confuse with Bot Mode Agent Inbox (async mail vs live steer).

## 6. Next action

- [x] entry + INDEX + STEALS
- [ ] verify parent tool list on current gateway build (one session probe)
- [ ] no card until probe shows gap

## 7. Chat blurb

**SIG-20260813-06** · harness · steal **P1** · high  
Teknium Subagent Orchestra: SPAWN/LIST/STEER/STOP + live transcripts.  
Engine already has `steer_subagent` + transcripts — **expose to parent**.  
≠ Bot Mode coworkers.
