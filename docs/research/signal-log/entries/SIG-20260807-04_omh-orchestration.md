# SIG-20260807-04 — Oh-My-Hermes multi-model orchestration layer

```yaml
id: SIG-20260807-04
date: 2026-08-07
title: "Oh-My-Hermes multi-model orchestration layer"
source_url: "https://x.com/rlaope/status/2085581549484073099"
canonical_repo: "https://github.com/rlaope/oh-my-hermes"
canonical_docs: "https://rlaope.github.io/oh-my-hermes/"
bucket: router
posture: steal
steal_rank: P1
confidence: medium
hardware_fit: [cloud, spark, mbp]
stacks_touched: [t1000]
related_plans: ["local-inference-fleet", "Fable model-stack review"]
status: open
```

## 1. Claim
OMH is a **Hermes-native operating layer**: workflows, evidence boundaries, multi-model routing — orchestration over single-model isolation. Keep Hermes; add pro packaging (`omh setup` or skills tap).

## 2. What we verified
- Repo MIT, Python 3.11+, ~700★ (launch heat); README: “stronger operating layer,” not replace Hermes
- Install: curl|sh **or** `hermes skills tap add rlaope/oh-my-hermes`
- Marketing pool: many frontier vendors (cost tension with Ryan discipline)
- Fits T1000 more than Prime (same genus as custom ops pack)

## 3. Takeaways
- **Orchestration > isolation** is the right religion for hybrid cloud/Spark/MBP
- Public kits sell **router + gates + workflows**; we already half-built this privately
- Skill-tap > curl for any trial
- Giant model walls fight cost + prompt-cache discipline
- Dual operating layers (T1000 customs + OMH) = ownership fight

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | Capability → workflow → **evidence gate** | Runs must state what did/didn’t happen (align never-auto-send) | P1 | open |
| S2 | **Clarify before build** | Gateway/coding: force ambiguity resolve before scaffold | P1 | open |
| S3 | **Verb→model map as product** | Ship thin aliases: default/private/code/format/embed | P1 | open |
| S4 | Sanity checks without verify loops | Bound retries on tool/JSON repair | P2 | open |

**Primary steal:** S3 (router verbs) — unlocks S1/S2 without installing OMH.

## 5. Do not
- `curl|sh` / `omh setup` on production `~/.t1000`
- Import full skill tree / multi-vendor key sprawl
- Let OMH own HA, Pulp, or send policy

## 6. Next action
- [x] entry + INDEX + STEALS
- [ ] Fable review → implement router (existing prompt)
- [ ] optional later: non-prod skills-tap spike of **one** workflow only

## 7. Chat blurb
OMH = Hermes ops pack (route + evidence + workflows). Steal **router verbs + evidence gates**, not the install. Primary: thin `default/private/code/format` map post-Fable. No prod overlay.
