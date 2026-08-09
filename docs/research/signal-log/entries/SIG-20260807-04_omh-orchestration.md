# SIG-20260807-04 — Oh-My-Hermes multi-model orchestration layer

```yaml
id: SIG-20260807-04
date: 2026-08-07
title: "Oh-My-Hermes multi-model orchestration layer"
source_url: "https://x.com/rlaope/status/2085581549484073099"
source_url_2: "https://x.com/rlaope/status/2086267378309234801"  # 2026-08-09 re-promo; triggered the v1.0.5 delta below
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

---

## 8. UPDATE 2026-08-09 — v1.0.5 delta (second promo, same project)

Ryan pasted a second rlaope post. **Not forked into a new SIG** — same repo, so the dedupe rule
is update-in-place (cf. SIG-20260808-05, where nothing had moved and nothing was written).
Here the project *did* move materially.

### Measured delta since this entry was written (2026-08-07)

| | 08-07 | 08-09 | |
|---|---|---|---|
| Stars | ~700 | **760** | launch heat, still |
| Release | (none read) | **v1.0.5** 08-08 13:15Z | 5 releases since 06-18 |
| Commits since 08-07 | — | **40** | `pushed_at` 08-09 11:07Z |
| Issues open | — | 2 | vs ~50 issue-branches merged |

**Provenance caveat, and it is the main one:** effectively every commit is a merge of
`rlaope/agent/issue-NNN` (issues ~789–838) landing in a ~2-day window. That is an **autonomous
agent loop shipping into main**, not reviewed human contribution. Feature titles are unusually
well-phrased as user outcomes; **none of them are verified by us.** GitHub code search needs auth,
so `decision_gate/v1` could not be confirmed in-tree — only the commit subject asserts it.
Treat the capability list as *claimed surface*, not working software.

### Why the delta matters here — three titles land on live T1000 problems

1. **"recommend only coding owners that can finish the accepted plan"** — capability-aware owner
   routing. This is precisely the failure we ate: DS4 Flash scored **9/9 on the eval lane and
   1/13 on worker cards the same day**, because the harness floor (`MINIMUM_CONTEXT_LENGTH=64_000`)
   exceeded its then-32768 ctx. A router that refuses owners which structurally cannot finish
   would have caught that before 13 cards failed.
2. **"project only the capabilities a request needs"** — narrow the toolset per request. The
   complement to raising ctx: we fixed the 35.7k worker-prompt floor by **raising the ceiling**
   (W2, 32768→65536); projection **lowers the floor** instead. Both are wanted; only one is done.
3. **"make an approval-gated pause survive a restart with decision_gate/v1"** — durable approval
   gates. We hit exactly this class of bug: `--initial-status blocked` prints "Created (blocked)"
   but `recompute_ready()` promotes parentless cards **straight back to `ready`**, and `t_b02284c0`
   needed a *sticky* block comment specifically to stop `default_assignee=worker` from auto-spawning
   a human-gate card the instant its parent completed.

Also notable, lower priority: *"report whether a native capability is genuinely complete"* —
which is the exact meta-failure the 08-08 audit found (five steals shipped while still marked
`open`) and which recurred within six hours today (see below).

### New steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S5 | **Capability-aware owner routing** | Refuse/redirect a card whose owner can't meet its floor, before dispatch | P1 | open |
| S6 | **Capability projection** (only the tools the request needs) | Shrink worker prompt below the floor instead of only raising ctx | P1 | open |
| S7 | **Restart-durable approval gate** (`decision_gate/v1`) | Gate state that survives dispatcher restart + `recompute_ready()` | P1 | open |
| S8 | Native-completeness check before adopting | "Is this already built here?" as a step, not a habit | P2 | open |
| S9 | Handoff to another owner **without replanning** | Relevant if W4 pivots the code lane B→D | P2 | open |

**Primary new steal: S5.** It is the one that maps to damage we already took.

### Verdict — unchanged
Still **pattern-mine, do not install**. Nothing about v1.0.5 changes the ownership-fight argument;
if anything, 40 auto-merged commits in two days *raises* the cost of tracking someone else's
operating layer on `~/.t1000`. S6 is the interesting one to build natively, not adopt.
