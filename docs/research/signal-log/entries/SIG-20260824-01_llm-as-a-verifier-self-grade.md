# SIG-20260824-01 — LLM-as-a-Verifier: same-model rank of 5 Flash trajectories

```yaml
id: SIG-20260824-01
date: 2026-08-24
title: "Shubham Saboo promo of Stanford LLM-as-a-Verifier — 5 mini-swe-agent DS4-Flash trajectories, same model ranks them, Terminal-Bench 2.1 78.7% → 88.0%. Parallel cousin of the sequential repair-pass (SIG-20260809-01). Pattern-mine; do not pip install."
index_title: "LLM-as-a-Verifier (★2759 MIT, pip llm-verifier 0.2.0) — same-model Bo5 rank of DS4 Flash on TB 2.1 78.7→88 (Oracle 96.6). Steal P1: report Pass@1 / picker / Oracle on any retry row. Not a 5×-Flash experiment. Saboo is megaphone."
index_links: [repo, docs]
source_url: "https://x.com/Saboo_Shubham_/status/2091713863368802322"
source_url_2: "https://x.com/jackyk02/status/2089469598240510144"
canonical_repo: "https://github.com/llm-as-a-verifier/llm-as-a-verifier"
canonical_docs: "https://arxiv.org/abs/2607.05391"
bucket: harness
posture: steal
steal_rank: P1
confidence: high          # fxtwitter verbatim + README screenshot; GH API + README table + arXiv 2607.05391 abstract + MIT LICENSE read live. No install, no re-bench.
hardware_fit: [none]      # 5× Flash trajectories is not a one-Spark interactive job; reproduction wants DEEPSEEK_API_KEY
stacks_touched: [t1000]
related_plans:
  - "SIG-20260809-01"     # sequential repair-pass (env tests) — different lever
  - "SIG-20260809-02"     # factorial harness-vs-model report shape
  - "t_6506193d"          # repair A/B/C — done 08-10; this is the parallel cousin, not a reopen
status: open
status_note: "**OPEN — steal P1, no new card.** Hardware pre-filter N/A. 88% is API Flash + mini-swe-agent + same-model logprob rank, not our local 13 t/s rollback. Fold: any best-of-N / retry row must carry Pass@1 · picker · Oracle. Comment on done `t_6506193d` so the family is named; do not reopen."
distill: none
```

## 1. Claim

[@Saboo_Shubham_](https://x.com/Saboo_Shubham_/status/2091713863368802322) (Shubham Saboo; ~119k followers; Google PM / Awesome-LLM-Apps; **271 likes / 49 RTs / 308 bookmarks / 13.8k views** at read; 2026-08-24 02:27 UTC; Typefully + README screenshot). Fetched verbatim via `api.fxtwitter.com`:

> WILD...the model grades its own answers and beats itself.
>
> Stanford's LLM-as-a-Verifier sampled 5 swe-agent trajectories, ranked them with the same model, kept the winner.
>
> deepseek-v4-flash went from 78.7% to 88% on terminal-bench without fine-tuning.
>
> 100% Opensource.

He is a **megaphone**. Artifact is Kwok / Li / Atreya / Liu / Jiang / Finn / Pavone / Stoica / Mirhoseini — Stanford + Berkeley + NVIDIA. Paper arXiv **2607.05391** (Jul 6–7). Author posts landed **2026-08-17** (@jackyk02, @Azaliamirh, @drmapavone). Saboo is a week-late clip.

## 2. What we verified

| Check | Result |
|---|---|
| Post body | **verbatim** via fxtwitter; screenshot is the GitHub README hero (pip `llm-verifier`, three-axis diagram, formula \(R(x,\tau)=\frac{1}{CK}\sum_c\sum_k\sum_g p_\theta(v_g\mid x,c,\tau)\,\phi(v_g)\)) |
| Repo | `llm-as-a-verifier/llm-as-a-verifier` — **★2,759 / 216 forks / 12 open issues**, **MIT**, created **2026-04-09**, pushed **2026-08-20**, docs `llm-as-a-verifier.com/docs/` |
| PyPI | `llm-verifier` **0.2.0**, `requires-python >=3.9`. Changelog: prefix-cache ~3.4× fewer uncached input tokens; TB 2.1 self-ver; `deepseek-v4-flash` backend |
| Paper | *LLM-as-a-Verifier: A General-Purpose Verification Framework*. Not a discrete 1–5 judge: **expectation over scoring-token logits → continuous score**. Scales along granularity, repetition, criteria decomposition |
| Self-ver table (README, first-party) | mini-swe-agent + **same** `deepseek-v4-flash` as verifier. Trajectories shipped in-repo; scoring wants `DEEPSEEK_API_KEY` |

| Config | Pass@1 | LLM-as-a-Verifier | Oracle |
|---|---|---|---|
| Best-of-3 | 79.4% | **86.5% ± 1.1%** | 92.1% |
| Best-of-5 | 78.7% | **88.0% ± 0.6%** | 96.6% |

Tweet 78.7 → 88 is the **Bo5 row**, exact. Ceiling arm **exists** (Oracle = perfect picker among the N samples). Verifier captures **9.3 / 17.9 pp ≈ 52%** of the Bo5 available lift. Other benches in the same README use **Gemini 2.5 Flash** as the *other*-model verifier (TB V2 83.1→86.5, SWE-Verified 76.1→78.2) — smaller lifts, different judge. Do not mix the tables.

| Hardware pre-filter | **N/A / pass.** Win is test-time selection, not a PCIe host↔device transfer. No tok/s claim, no batch-size invert |
| Local install / re-bench | **Not run.** Reproduction is API Flash + key, or a logprobs-capable OpenAI-compatible server. Standing no-provider-keys rule forbids their default path |
| Duplicate URL | No prior LLM-as-a-Verifier / 2607.05391 / `llm-verifier` entry |

**Not the sequential repair-pass.** SIG-20260809-01 / `t_6506193d` (done 08-10) is: run tests → feed failures → one retry. This is: sample **N full trajectories in parallel**, rank with a **same-model logprob judge**, keep one. Env feedback vs LLM rank. Do not reopen the repair card as if this were the missing arm.

## 3. Takeaways (max 5)

- **Saboo ≠ the artifact.** Week-old Stanford/Berkeley/NVIDIA result; cite the repo/paper.
- **88% is API Flash + mini-swe-agent, not our Flash.** Local lane is still the `app/` rollback ~13 t/s. Do not quote 88 as a fleet number.
- **Oracle column is the real instrument.** 88 without 96.6 is a best-cell. Same defect class as a tok/s row without a named ceiling.
- **Same-model self-verify is the surprising cell.** The other README table uses Gemini-as-judge and the lifts shrink. The tweet's "grades its own answers" is the Bo5 Flash-on-Flash row only.
- **5× full agent trajectories is not our regime.** Interactive desk is N=1. The cheap cousin we already named is one sequential repair with a blind-retry control.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Pass@1 / picker / Oracle on every retry or best-of-N row** — Oracle is the ceiling (perfect picker among the samples you already paid for). Without it the picker delta is unreadable | Add the triple to the bench/report contract any time G3, repair, or a worker retries. Do not install `llm-verifier` to get the column | **P1** | fold — STEALS + comment on `t_6506193d` |
| S2 | Continuous score = E[scoring-token logits], not a discrete 1–5 judge | Citation-only unless we already have logprobs on a lane. DS4/`ds4-server` logprobs surface is unverified; do not stand up vLLM to find out | P2 | log only |
| S3 | Same-model judge can beat Pass@1 (self-verify) | Hypothesis for a future repair/G3 picker: rank attempt A vs attempt C with the *same* model instead of always taking the last. Needs the blind-retry control already specified on `t_6506193d` or it is just resampling | P2 | log only |

**Primary steal (one only): S1.** True whether or not their package is ever imported.

## 5. Do not

- **Do not `pip install llm-verifier`.** Default path is `DEEPSEEK_API_KEY` / `VERTEX_API_KEY`. Local path wants a logprobs server we do not run.
- **Do not install the TurboAgent Claude Code plugin** (`pip install git+https://github.com/llm-as-a-verifier/TurboAgent`). Second control plane in front of Max / claude-acp.
- **Do not run 5 parallel Flash agents on one Spark.** 105 GiB class; N=5 is an API-cost story, not a GB10 story.
- **Do not quote 88% or "11× cheaper than Fable 5"** as ours. 11× is the authors' cost claim vs Claude Fable 5, not measured here.
- **Do not reopen `t_6506193d`.** Different lever. Card is done.

## 6. Next action (mechanical)

- [x] `INDEX.md` regenerated via `signal_log_index.py --write`
- [x] `STEALS.md` rollup row
- [x] kanban comment `t_6506193d` (mesh, done) — name the parallel cousin; do not reopen
- [ ] no new card

## 7. Chat blurb

`SIG-20260824-01` · `harness` · **steal P1** · [LLM-as-a-Verifier](https://github.com/llm-as-a-verifier/llm-as-a-verifier) ★2,759 MIT. Saboo clip of Stanford Bo5: API DS4 Flash 78.7 → 88.0 on TB 2.1, Oracle 96.6. Primary steal **S1 — Pass@1 / picker / Oracle on any retry row**, not `pip install llm-verifier` and not five Flash jobs on a Spark.
