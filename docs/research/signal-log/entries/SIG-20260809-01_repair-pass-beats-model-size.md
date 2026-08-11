# SIG-20260809-01 — One repair pass closes a 6× memory gap (danpacary)

```yaml
id: SIG-20260809-01
date: 2026-08-09
title: "One retry closes a six-times memory gap — harness beats model size on a coding exam"
index_title: "One repair pass closes a 6× memory gap — harness beats model size"
source_url: "https://x.com/danpacary/status/2085794035197960418"
posted_at: "2026-08-07T18:23:44Z"
canonical_repo: ""            # none published — "evalx", gsha 1877a3f777b7, not public
canonical_docs: ""
bucket: harness
posture: steal
steal_rank: P0
confidence: medium            # direction corroborated by our own G3; effect size is n=2
hardware_fit: [mbp, spark]
stacks_touched: [t1000, k2]
related_plans:
  - "B17"
  - "t_43e997d2"              # fork cutover — this reframes it
  - "t_716141c4"              # upstream DSpark = 1.01x
  - "SIG-20260808-06"
  - "~/Documents/T1000/docs/inference/FLASH-G3-WORTH-IT-2026-08-08.md"
status: carded          # t_6506193d — was only ever recorded in INDEX.md until 2026-08-09
distill: none
```

## 1. Claim

@danpacary (2,968 followers; bio: *"sometimes I design systems for constrained compute | local ai"*),
M4 Max 128 GB, same coding exam across five local models. **Same prompts, same seeds — only the
harness differs.** Arm A = one shot. Arm B = **one repair pass** (model retries once *after seeing
its own test failures*).

> "the 93 GB model was never smarter. it tolerated a worse harness"
> "one retry moved scores further than 6× the memory did"

## 2. What we verified

**Read off his chart** (more precise than the tweet text — the text rounds and omits the method):

Task = *three python files graded by executing **19 hidden tests***. `evalx`, gsha `1877a3f777b7`,
**temperature 1.0**, **n=5 single, n=2 repair**.

| Model | Size | one shot | one repair | Δ |
|---|---:|---:|---:|---:|
| Qwen3.6 27B · 4bit | 16.3 GB | 52.6 | **100** | **+47** |
| Ornith 1.0 35B · 4bit | 20.2 GB | 55.8 | **92.1** | **+36** |
| Qwen3.6 35B **A3B MoE** · 4bit DWQ | 21.4 GB | 47.4 | 57.9 | **+11** |
| Laguna XS 2.1 | 22.1 GB | 63.2 | 73.7 | +11 |
| Laguna S 2.1 · oQ6e | 93.2 GB | 95.8 | **100** | +4 |

He excludes one model himself for a version confound (*"laguna-s-optiq2 … shape and engine version
confounded"*) — a good-faith signal. His own footnote: *"repair is not free for every model."*

**Corroborated independently by us, one day later, without knowing this post existed.** Our G3 work
on 2026-08-08 changed **no model and no hardware** and moved DS4-Flash from **0/3 → 8/8 apply_ok**
(`flash-g3-eval.json`, n=8, rate 1.0). Pure harness: `###FILE` fence protocol + `reasoning_effort=none`.
Our n is larger than his and our result is cleaner. **The direction is real on our own stack.**

## 3. Where his evidence is weak (do not repeat these)

1. **The repair arm is n=2.** A +47 built on two runs over 19 tests is a wide interval. 52.6% ≈ 10/19;
   100% = 19/19. Two samples cannot separate +47 from +20.
2. **Temperature 1.0 with no blind-retry control.** At temp 1.0 a one-shot failure is often a sampling
   accident. He has no *"retry without showing it the failures"* arm — so the chart **cannot distinguish
   "learned from test output" from "rolled the dice twice."** This is the single biggest hole, and it is
   the one thing we must fix when we run our own.
3. **Ceiling compression.** Two models hit exactly 100 — the instrument saturates, so the top of the
   range is unmeasurable (same saturation problem as our signed golden-30).
4. Models unidentifiable/unreleasable (`Ornith`, `Laguna`) and `evalx` is not public — **not reproducible**.

## 4. The read that matters for our stack

**The one class where repair barely helped was MoE** (`Qwen3.6 35B A3B`, +11) — and **our default code
lane is MoE**:

| Our lane | Model | Class | Chart's prediction for repair |
|---|---|---|---|
| **DEFAULT code** | DS4 DeepSeek-V4-Flash | **MoE** | weak gain |
| Fallback code | qwen2.5-coder:32b | **dense** | **strongest gain** |
| Propose | gpt-oss:120b | **MoE** | weak gain |
| Format/repair | hermes3:8b | dense | — |

If that holds, our repair loop pays out most on the **fallback**, not the default — which would be an
argument for dense-coder-first on repair-heavy work. **This is a hypothesis off one n=2 datapoint, not
a finding.** It is cheap to test on our own boxes and it is the reason to test rather than adopt.

## 5. Steals

**PRIMARY (P0) — execution-feedback repair pass in the code lane.** We already have *format* repair
(G3 step 4: reparse → hermes3 fences). We do **not** have *test-failure* repair: run the tests, feed
the failure text back, allow exactly one retry, then escalate. Different lever, larger claimed payoff.
Must ship with a **blind-retry control arm** (retry at same temp, failures withheld) or we learn nothing
he didn't already fail to learn.

**Secondary (P1) — reprioritize the fork decision.** `t_43e997d2` is blocked on Kevin's OK plus a
provenance review to install a third-party inference engine on a box carrying tunnels and 3 GitHub
runners, for **1.8× decode**. A repair pass costs **zero** risk and zero of Kevin's attention. Measure
the harness lever *before* spending the heavyweight one.

**Do not steal:** his numbers (n=2, temp 1.0, no control) · `evalx` (unpublished) · the framing
"big models are pointless" (his own 93 GB model still won one-shot, 95.8 vs 52.6).

## 6. Wired

- Card **`t_6506193d`** — repair-pass A/B/C with blind-retry control (blocked, needs Ryan window)
- Comment on **`t_43e997d2`** — reframes the fork cutover as second in line behind the free lever

## 7. Verdict

**Steal the method, not the numbers.** The claim's direction is the same thing our own G3 measured
with better n — harness moved more than any model swap available to us. The specific effect size is
unreliable and the MoE caveat may invert which of our lanes benefits. Test it with the control arm he
skipped.
