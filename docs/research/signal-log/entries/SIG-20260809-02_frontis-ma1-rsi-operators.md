# SIG-20260809-02 — Frontis-MA1 / OpenRSI: harness +30 vs model +20, in one factorial

```yaml
id: SIG-20260809-02
date: 2026-08-09
title: "Frontis-MA1 (35B) + OpenMLE — RSI via four trained program-evolution operators; harness contributed more than the model"
source_url: "https://x.com/neural_avb/status/2086119647099985975"
posted_at: "2026-08-08T15:57:36Z"
quoted_post: "https://x.com/neural_avb/status/2086073348531110130"   # self-QRT; substance is the linked X article
canonical_repo: "https://github.com/FrontisAI/OpenRSI"
canonical_docs: "https://arxiv.org/abs/2607.28568"
bucket: harness
posture: steal
steal_rank: P1
confidence: medium            # strong design, released weights — but self-evaluated on a self-authored held-out benchmark
hardware_fit: [none]          # weights are NC-licensed; 35B/30B serving is external to the 4090 figure
stacks_touched: [t1000, k2]
related_plans:
  - "SIG-20260809-01"         # repair pass — this is the RL-trained, factorially-controlled version
  - "t_6506193d"              # W3+ repair-pass A/B — this paper supplies the control design it asked for
  - "SIG-20260807-02"         # Prime Agent — AVB's whole point is the contrast with prompt-level RSI
  - "B18"                     # student program — execution-grounded labels vs human labels
status: open
distill: none
```

## 1. Claim

AVB (@neural_avb, 12.6k followers) self-QRTs his own X article on **Frontis-MA1**. His framing is
the interesting part, not the summary:

> "Esp coz they are actually finetuning language models **inside compatible harnesses**, instead of
> just optimizing the code/system prompts. You get to wrap your RL and gradient descent stuff around
> a search and evolution layer."

The underlying work: **arXiv 2607.28568** (2026-07-30, 24 authors, FrontisAI). They post-train
**Frontis-MA1 (35B)** as a *meta-evolution agent* for machine-learning engineering, aligning both
post-training and inference around **four atomic program-evolution operators — Draft, Improve,
Debug, Crossover** — trained by execution-grounded SFT + RL, then composed into long-horizon search.
Full stack released as **OpenMLE** (Gym / RL / Evo).

## 2. What we verified

Fetched arXiv abstract, the OpenRSI README, `OpenMLE-Evo/README.md`, the HF model list, and the
GitHub API. Not read: the ablation tables in the paper body.

| Fact | Value |
|---|---|
| Repo | `FrontisAI/OpenRSI` — **260★**, 22 forks, Python, created 2026-07-30, **pushed today** |
| Weights | 35B + 30B, **plus GGUF derivatives** for both |
| **License** | **CC BY-NC 4.0 — non-commercial**, on every artifact |
| Headline | MLE-Bench Lite Medal Average **39.39% → 60.61%** over base w/ OpenMLE-Evo; **71.21%** w/ Evo-Max |
| Positioning (theirs) | exceeds GPT-5.5 + Codex; approaches GPT-5.6 Sol and the 2.8T Kimi K3 |

### The number that actually matters — a real factorial

On held-out NatureBench Lite they varied **one factor at a time**, which fills three cells of a 2×2:

| model | framework | Match-SOTA |
|---|---|---:|
| base | base | **20%** |
| base | **OpenMLE-Evo** | **50%**  → *harness alone:* **+30** |
| **trained** | OpenMLE-Evo | **70%**  → *model alone, on top of Evo:* **+20** |

### Both released models are MoE — this complicates our dense-vs-MoE prior

Read from the HF `config.json`s:

| model | `model_type` | shape |
|---|---|---|
| Frontis-MA1-35B | `qwen3_5_moe` | `Qwen3_5MoeForConditionalGeneration` |
| Frontis-MA1-30B | `qwen3_moe` | 48 layers, hidden 2048, **128 experts / 8 active**, 262k ctx |

`t_6506193d` carries the hypothesis — from danpacary's chart — that **repair pays out on dense and
not on MoE** (his one MoE model moved +11 vs +36/+47 for dense 27–35B). Frontis-MA1 is **MoE** and
gained **39.39 → 71.21** from operator training + search. That does not refute the card's
hypothesis, because the settings differ in the decisive way: he **prompted** a stock model to retry;
they **RL-trained the Debug operator into the weights**. But it does mean *"MoE doesn't repair"*
cannot be carried as a general law into the experiment design — only as a hypothesis about
**prompted** repair on stock weights.

**The harness contributed more than the model, and it contributed first.** Same direction as
SIG-20260809-01 (danpacary) and as our own G3 result (DS4-Flash 0/3 → 8/8 apply_ok, no model or
hardware change) — but unlike either of those, this one has a proper one-factor-at-a-time design.

## 3. Where the evidence is weak (state it, don't launder it)

1. **The held-out benchmark is theirs.** NatureBench was released by the same team on 2026-06-23 and
   then used as the "held-out transfer benchmark" for their own model. Held-out from *training*,
   not from the authors.
2. **Self-reported frontier comparison.** "Exceeds GPT-5.5 + Codex / approaches Kimi K3" is their
   harness running their baselines. No third-party reproduction yet at 260★ / 10 days old.
3. **Benchmark dedup is a claim.** "Data deduplicated against all evaluation benchmarks" is asserted,
   not independently audited.

## 4. The misreading trap — do not repeat it

> "Frontis-MA1 (35B) … **on one RTX 4090 capped at 12 GB VRAM**"

That 4090 is the **sandbox the agent's generated ML code runs in** — the compute budget for the
*task*, not the host for the *agent*. `OpenMLE-Evo/README.md` lists "**model servers** … are
external," and Evo-Max is explicitly an "asynchronous **multi-GPU** search profile."

A 35B BF16 agent does not serve from 12 GB. Anyone quoting this as "35B beats frontier on a 4090"
— and it will be quoted that way — is wrong, and would size our hardware plan wrong.

## 5. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Factorial harness-vs-model design** (vary one at a time; report both deltas) | Adopt as the report shape for `t_6506193d`; it is the control structure that card already demands | **P1** | **wired — card comment** |
| S2 | **Named operator set: Draft / Improve / Debug / Crossover** as the code-lane vocabulary | We have *Draft* (G3) and *Debug* (repair pass, carded). **Improve** and **Crossover** have no analogue in DevBot | P1 | open |
| S3 | Execution-grounded labels — environment scores the trace, no human in the loop | B18 is stuck at **0 labels / 2 pointers** on human thumbs. Split the scorer: schema-valid / evidence-grounded / refusal-correct are **mechanically checkable today**; intent / urgency / followup are not | P1 | open |

**Primary steal (one only): S1.**

## 6. Do not

- **Do not plan on these weights.** CC BY-NC 4.0 kills them for Sovereign/K2 client work regardless
  of merit. The *patterns* are free; the model is not.
- Do not install OpenMLE on `~/.t1000` or either Spark. This is a 10-day-old research stack.
- Do not read S3 as "we can stop labeling." Urgency and intent have **no execution oracle** — that
  is precisely why Ryan's labels are the irreplaceable part of B18. S3 automates the *checkable*
  dimensions only, so Ryan's minutes go to the judgment ones.
- Do not cite the 4090 figure as an agent-hosting number (§4).

## 7. Next action (mechanical)

- [x] add to `INDEX.md` + `STEALS.md`
- [x] kanban comment `t_6506193d` — hand it the factorial design + the MoE-vs-dense read
- [ ] no new card (board at 46 blocked / 19 todo; S2/S3 stay in the log until something clears)

## 8. Chat blurb

`SIG-20260809-02` · `harness` · **steal P1** · [arXiv 2607.28568](https://arxiv.org/abs/2607.28568) ·
[OpenRSI](https://github.com/FrontisAI/OpenRSI) 260★ · **CC BY-NC — weights unusable commercially**.
Second independent corroboration that harness > model, and the first with a real factorial:
**framework alone +30 pts, model alone +20**, one factor at a time. Trap: the "RTX 4090 12 GB" is the
task sandbox, not the agent host. Wired into `t_6506193d` as its control design.
