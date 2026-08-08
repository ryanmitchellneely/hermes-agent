# SIG-20260807-02 — Prime Agent self-improving RLM harness

```yaml
id: SIG-20260807-02
date: 2026-08-07
title: "Prime Agent self-improving RLM harness"
source_url: "https://x.com/milesdeutscher/status/2085399864259858487"
canonical_repo: "https://github.com/PrimeIntellect-ai/prime-agent"
canonical_docs: "https://www.primeintellect.ai/blog/prime-agent"
bucket: harness
posture: steal
steal_rank: P1
confidence: high
hardware_fit: [cloud, mbp, spark]
stacks_touched: [t1000]
related_plans: ["agent-harness-compare skill"]
status: open
```

## 1. Claim
Prime Agent = open **self-improving coding harness**: RLM (context-as-variable, subagents as code in persistent IPython) + Continual Harness (`/refine` mid-task CRUD on prompts/skills/memory/subagent specs). Miles: “Hermes on steroids.”

## 2. What we verified
- MIT, TS monorepo, ~5k★ launch; built on `pi`; non-sandbox (user perms)
- `/refine` doesn’t rewrite base system prompt; snapshots/rollback
- Retained subagents + A2A messaging; daemon detach/reattach
- ARC-AGI-3 ~95.5% w/ **Opus 5** = frontier+harness, not free open IQ
- Coding marathon tool — not life gateway/Pulp/HA

## 3. Takeaways
- Same genus as Hermes; different species (REPL-native coding vs desk OS)
- Mid-task harness mutation + rollback is the interesting product idea
- Context-as-variable aligns with prompt-cache sacredness
- Autonomous budgets + quality gates good for code lane
- Not a T1000 replacement

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | Trajectory → propose skill/memory patch + diff/accept | skill_manage UX / optional mid-task | P1 | open |
| S2 | Turn/token/time budgets + test gate | Code-lane autonomous limits | P1 | open |
| S3 | Context-as-variable (query big blobs) | Avoid cache-busting dumps | P1 | open |
| S4 | Retained A2A | Only on mesh/kanban paths | P2 | open |

**Primary steal:** S1 (refine-with-rollback)

## 5. Do not
- curl|sh as Telegram primary / touch `~/.t1000`
- Dual daily drivers with Hermes gateway
- Let launch week derail router + B17

## 6. Next action
- [x] agent-harness-compare skill created (auto)
- [ ] optional kanban stub for S1+S2 when calm
- [ ] spike only on throwaway worktree if Ryan says go

## 7. Chat blurb
Prime = coding RLM harness with `/refine`. Steal refine+rollback and code budgets; keep Hermes SoT. Spike disposable only.
