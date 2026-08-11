# SIG-20260810-05 — Liquid AI's finetuning cookbook, and the two training rungs B18 already has the data shape for

```yaml
id: SIG-20260810-05
date: 2026-08-10
title: "Liquid4All/cookbook finetuning notebooks (surfaced by Leonie) — CPT / SFT / DPO / GRPO recipes across TRL and Unsloth"
index_title: "Liquid cookbook: SFT->DPO->GRPO ladder. The real find is ours — B18's outcome-loop labels are already DPO pairs and score_case is already a verifiable GRPO reward. Corpus-blocked; License=None so read-don't-copy"
index_links: [repo]
source_url: "https://x.com/helloiamleonie/status/2086806187572355388"
canonical_repo: "https://github.com/Liquid4All/cookbook/tree/main/finetuning"
canonical_docs: ""
bucket: models
posture: steal
steal_rank: P1
confidence: high          # post fetched verbatim; repo metadata + full finetuning tree read via GitHub API; our own scorer/plan/card read live off disk
hardware_fit: [caden, mbp]   # Unsloth notebooks are CUDA -> caden (8GB cap). MLX path on MBP/mini is ours, not theirs.
stacks_touched: [t1000, student-lab]
related_plans:
  - "B18"                 # Mac mini student model program
  - "t_848b57b7"          # B18 card
  - "t_47f30baf"          # CadensPC role — this gives it a candidate answer
  - "t_1edac8a4"          # LAB-0024 LoRA register
  - "t_d754cc37"          # local-model scoreboard lane (parent of the caden card)
status: carded
status_note: "Primary steal CARDED t_de3a5688 (blocked on Ryan). See card body for the full spec + guardrails."
distill: none
```

## 1. Claim

[@helloiamleonie](https://x.com/helloiamleonie/status/2086806187572355388) (Leonie, 20k followers,
2026-08-10 13:25Z, 197♥ / 14.2k views):

> *"The @liquidai cookbook is such an underrated developer resource: Curious about fine-tuning
> text, vision, audio, or encoder models? Curious about fine-tuning with **CPT, SFT, DPO, or
> GRPO**? Curious about fine-tuning LFMs with **Unsloth or TRL**? It has it all. I just did a
> little cleanup."*

→ `github.com/Liquid4All/cookbook/tree/main/finetuning`

## 2. What we verified

**Repo:** `Liquid4All/cookbook` — **2,209★, 357 forks**, created 2025-10-03,
**pushed 2026-08-10 13:13Z — 12 minutes before the post** (that's her cleanup landing).

**⚠️ `license: None`.** No license file means **all rights reserved by default** — not
permissive. We may read and learn from it; we may **not** lift the code. Pattern-mine only.
(Contrast: every other repo logged today — Arc B70 cookbook, exo, OpenKB — was MIT/Apache.)

**The `finetuning/` tree — 12 files, 9 notebooks, read via the GitHub API:**

| Method | Notebooks |
|---|---|
| **CPT** (continued pretraining) | `cpt_text_completion_with_unsloth` · `cpt_translation_with_unsloth` |
| **SFT** | `sft_with_trl` · `sft_with_unsloth` · `sft_for_vision_language_model` · `sft_for_vision_language_model_with_trl` |
| **DPO** | `dpo_with_trl` |
| **GRPO** | `grpo_with_unsloth` · **`grpo_for_verifiable_tasks`** |

Plus `scripts/unsloth-sft-lfm2.5.py` and two notebook-cleanup utilities.

The post's "text, vision, audio, or encoder" oversells this directory: **audio and encoder
notebooks are not in `finetuning/`** (the repo is 1,187 files; those live elsewhere if at all).
What's here is text + vision.

---

### 🔵 The actual find — it's ours, not theirs

`grpo_for_verifiable_tasks` is the recipe for RL where the reward is a deterministic check.
**We already have that check, and I read it live rather than assuming.**

`sovereign-consulting/tools/juice/evals/scorers.py:218` — `score_case()` returns, per case:

```python
{ "case_id", "passed",
  "schema_valid", "field_exact", "refusal_correct", "evidence_grounded",
  "errors": [...] }
```

Four **deterministic component scores** with partial credit, plus a boolean rollup. That is a
verifiable reward function in everything but name — and we have **100 Ryan-labeled cases**
(`golden_set_research_v2.json`, `RYAN_LABELED_UNSIGNED`).

And the outcome loop's row shape is:

```json
{"classification": {...model's own 6-field output...},
 "label": {"verdict": "wrong", "correction": "intent=complaint urgency=4"}}
```

**Rejected** and **chosen** in one row. That is a DPO preference pair.

So B18 currently plans **one** training rung — SFT/LoRA distillation from the Spark teacher — and
we are already collecting the data for **two more**:

| Rung | Signal source | Data we already have | Ceiling it breaks |
|---|---|---|---|
| **SFT** (planned) | teacher outputs | `capture-index` classifications | can only *approach* the teacher (61/97 on research-v2) |
| **DPO** (unplanned) | Ryan's thumbs + corrections | `label.verdict` + `label.correction` | learns *Ryan's* calibration, not the teacher's |
| **GRPO** (unplanned) | `score_case` | 100 labeled cases w/ exact expectations | needs **no human labels at all** |

**A retroactive validation worth recording:** the plan's Option-B decision (2026-08-07) — store
pointers **plus the classification**, never bodies — was argued on privacy and on saving a ~1.5 h
teacher re-run. It also, by accident, made the corpus **DPO-ready**. Option A (pointers only)
would have stored the correction with nothing to contrast it against. Right call for a reason
nobody wrote down at the time.

## 3. Takeaways (5)

1. **Two of three rungs need no new collection — just a different read of rows we're already writing.**
2. **GRPO decouples "beat the teacher" from the label bottleneck.** The plan's stated thesis is that
   Ryan's corrections are the only path past the teacher's ceiling. A verifiable reward is a second
   path that needs zero labels. Given labels sit at **0** and pointers at **2 of 500**, that
   matters more than it would in a healthy corpus.
3. **⛔ But do not train on the golden set.** It is the **referee**. GRPO against those 100 cases
   burns the only instrument that can tell a good student from a bad one — train/test
   contamination, and we'd never see it because the eval would look great. If GRPO ever runs it
   needs a **separately generated reward set**, and the 100 stay sealed. *This is the trap this
   entry exists to prevent.*
4. **None of this is reachable today, and a cookbook is not progress.** B18 is corpus-blocked:
   **2 trainable pointers vs a floor of 500**, **0 labels**. Same discipline as OpenKB — file it,
   don't let it feel like movement.
5. **Unsloth is CUDA, so these recipes route to Caden, not the Mac lane.** Our plan picked MLX
   (`mlx_lm.lora`) precisely so MBP→mini is a hostname change. The TRL/Unsloth notebooks are a
   different toolchain; the *method* ports, the *code* doesn't.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **SFT → DPO → GRPO as a ladder, not a single shot** | Add a *later-phase* rung table to the B18 plan mapping each rung to the asset we already collect (teacher outputs → SFT; `label.verdict`+`correction` → DPO; `score_case` → GRPO). **Explicitly gated behind the corpus floor** so it can't read as ready work. | **P1** | open — commented onto `t_848b57b7` |
| **S2** | **Never train against the referee** | If GRPO is ever attempted, the reward set must be generated separately from `golden_set_research_v2.json`. The 100 cases stay a sealed instrument. Write it into the plan's hard-rules block next to *"no training run counts unless `baseline_locked: true`"*. | **P1** | open — same comment |
| S3 | Caden's job might be **training**, not inference | `t_47f30baf` asks what should live on CadensPC. Every answer so far has been an inference tier (8B eval/embed, measured 49 tok/s). Unsloth QLoRA is a *CUDA* workload and Caden is our only CUDA box — but **RTX 4060 / 8 GB VRAM / 15.7 GB RAM** caps it at small models, short sequences, QLoRA only. Candidate answer, not a good one. Plan's standing rule holds: *"CadensPC never becomes load-bearing."* | P2 | note — not carded |
| S4 | License hygiene on "steal" sources | `license: None` = all rights reserved. Read, don't copy. Worth a standing field check when a signal points at a repo we'd otherwise crib from. | P2 | note |

## 5. Do NOT

- **Do not copy code from this repo.** No license = all rights reserved. Patterns and method only.
- **Do not treat this as unblocking B18.** The blocker is corpus (2/500 pointers, 0 labels), not
  recipes. Nothing here moves that number.
- **Do not GRPO against `golden_set_research_v2.json`.** See takeaway 3 — it destroys the referee.
- **Do not repoint the student training path from MLX to Unsloth.** The MLX choice buys
  MBP → mini as a hostname change (plan §Phase E); Unsloth would forfeit that for a box the plan
  explicitly forbids from becoming load-bearing.
- **Do not pull LFM models.** We don't run Liquid's family; the notebooks are LFM-flavored and
  `unsloth-sft-lfm2.5.py` is theirs, not a generic script.
- No `curl | sh`, nothing installed, no new deps.

## 6. Provenance

Post via `api.fxtwitter.com` (skill's first route). Repo metadata + full recursive tree via the
GitHub API — **notebook contents not read** (9 `.ipynb` files; the method names are from filenames
and the post, and I did not open them). `score_case`, the B18 plan, and `t_47f30baf` were read
**live off disk / the board**, which is where the DPO-pair and verifiable-reward mappings came
from — those are our observations, not the cookbook's claims.

## 7. Next action (one)

Kanban comment on **`t_848b57b7`** (B18 student model program) recording the three-rung ladder,
the Option-B retroactive validation, and the **don't-train-on-the-referee** rule. **No new card** —
B18 is corpus-blocked and the board is at 44 blocked; adding a training card now would create the
illusion of a live lane.
