# SIG-20260818-01 — Jun Song: Flash-as-verifier for GLM on Spark will “beat Fable.” Paper is real (Jul). Pairing is unmeasured. 4×Spark is not our fleet.

```yaml
id: SIG-20260818-01
date: 2026-08-18
title: "jun_song (1.9k likes) quotes jackyk02: DS4 Flash self-verify Best-of-5 on Terminal-Bench 2.1 is 79%→88% and '11x cheaper than Fable 5.' README table: Pass@1 78.7 / verifier 88.0±0.6 / oracle 96.6. Needs DEEPSEEK_API_KEY — API Flash, not Kevin IQ2. Later same-day tweet (208955) adds GLM+Spark / 4×Spark-beats-Fable. Paper Jul. Don't pip install."
index_title: "LAAV TB2.1 Bo5 79→88 is API Flash self-rank, not Spark. 11x cheaper = author tweet. Jun GLM/4×Spark follow-up still hype. Watch P2. Don't install."
source_url: "https://x.com/jun_song/status/2089521135050535236"
source_url_2: "https://x.com/jackyk02/status/2089421448784023553"
canonical_repo: "https://github.com/llm-as-a-verifier/llm-as-a-verifier"
canonical_docs: "https://llm-as-a-verifier.com"
index_links: [repo, docs]
bucket: harness
posture: watch
steal_rank: P2
confidence: high
hardware_fit: [spark]
stacks_touched: [t1000]
related_plans:
  - "SIG-20260811-06"
  - "t_c5510683"
  - "local-inference-fleet"
status: open
status_note: "**UPDATED 2026-08-18 — Jun hub tweet + README Bo5 table.** 78.7% Pass@1 → **88.0%±0.6** verifier / 96.6 oracle. Scoring needs **DEEPSEEK_API_KEY**. 11× cheaper not in README. Later 208955 GLM+4×Spark still unmeasured. No install. No card."
updated: 2026-08-18
distill: none
```

## 0. Hub tweet (this URL) + later GLM follow-up

[@jun_song](https://x.com/jun_song/status/2089521135050535236) (40.7k fol; **1,979 likes** / 134 RT / 1,692 bookmarks / 188k views) quote-tweeted the actual result. **No new SIG.**

> Stanford is cooking… self-verification… Deepseek-V4-Flash easily outperforms Fable. **11x cheaper** and a much higher Terminal bench score.

[@jackyk02](https://x.com/jackyk02/status/2089421448784023553) (2.1k fol; 1,730 likes / 2,085 bookmarks / 388k views): sample **5** V4 Flash solutions, rank with **the same model** via LAAV → **79% → 88%** on Terminal-Bench 2.1, “11× cheaper than Claude Fable 5.”

Same-day later tweet (already in this entry): GLM-5.3 + Spark Flash / 4×Spark beats Fable offline.

## 1. Claim

[@jun_song](https://x.com/jun_song/status/2089555716671766988) (40.7k fol; 188 likes / 4 RT / 151 bookmarks / 13k views; note tweet):

If LLM-as-a-verifier works, pair a large model with a small one and verify on the cheap. **GLM-5.3 API + DS4 Flash on a DGX Spark** = jump without cost. **4× DGX Spark** could multi-batch both and **beat Fable entirely offline**.

Quote [@jackyk02](https://x.com/jackyk02/status/2089548247564189918) (Jacky Kwok, Stanford): paper used **Gemini 2.5 Flash to verify GPT-5.5** trajectories → SOTA Terminal-Bench 2.0. “Local V4 Flash verifying GLM 5.3 should definitely work.”

## 2. What we verified

| Check | Result |
|---|---|
| Site | [llm-as-a-verifier.com](https://llm-as-a-verifier.com) — Stanford / Berkeley / NVIDIA Research. Fine-grained scores from **scoring-token logits** (granularity × repeats × criteria split). No extra training |
| Claimed benches | TB2 **86.5%** · SWE-Verified **78.2%** · RoboReward **87.4%** · MedAgent **73.3%**. RL: ~1.8× sample-eff on LIBERO (π0+SAC); ~1.1× on MATH (Qwen3-8B GRPO) |
| Repo | `llm-as-a-verifier/llm-as-a-verifier` MIT ★**989** / created 2026-04-09 / pushed 08-14. Also TurboAgent ★51 Apache-2.0 |
| Paper | [arXiv 2607.05391](https://arxiv.org/abs/2607.05391) submitted **2026-07-06** |
| Install | `pip install llm-verifier` + a Claude Code plugin — **not for this desk** |
| Hardware pre-filter | **N/A** (not PCIe-offload) |
| Our fleet | **2** Sparks, separate houses. Kevin = DS4 squat (~105 GiB). **No 4× node.** Dual-load GLM+Flash on 121G is a residency fail |
| README TB2.1 self-verif | Same model generates + verifies. Best-of-3: Pass@1 **79.4** / verifier **86.5±1.1** / oracle 92.1. **Best-of-5: 78.7 / 88.0±0.6 / 96.6**. Trajectories in-repo. Score scripts need **`DEEPSEEK_API_KEY`** |
| “11× cheaper” | **Author tweet only.** Not in README |
| Local vs API | Quickstart = `DEEPSEEK_API_KEY` or Vertex or a logprobs OpenAI server. **Not** our IQ2 `ds4-server` on Kevin |

## 3. Takeaways (max 5)

- The banked row is **API Flash Best-of-5 self-rank** (78.7 → 88.0 on TB2.1). Not “Flash is smarter than Fable at N=1.”
- **11× cheaper** is the tweet, not the README.
- Later GLM+Spark / 4×Spark transfer is still a guess. We have **2** Sparks, not 4.
- Same family as Switchyard / `t_c5510683` fail-open judge. Do **not** promote Flash from 1/13 worker because Bo5 API verify scored well.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Cheap verifier of an expensive trajectory** (not cheap worker) | If we ever add a judge arm: Flash scores a finished 120b/Grok/Claude trajectory. Fail-open. Fold into `t_c5510683` — **no new card** | **P2** | watch |

**Primary steal:** S1 (not P1 — no STEALS row)

## 5. Do not

- `pip install llm-verifier` or the Claude Code plugin onto `~/.t1000`.
- Dual-load GLM 5.3 + DS4 on one Spark.
- Quote “Flash easily outperforms Fable” or **11× cheaper** as a desk fact.
- Run Bo5 self-verify on Kevin IQ2 and call it the paper row (logprobs + API backend).
- Make Flash the desk closer because TB2.1 Bo5 hit 88.

## 6. Next action

- [x] entry + INDEX
- [ ] none — **no STEALS P0/P1 row, no card**

## 7. Chat blurb

**SIG-20260818-01** · harness · **watch P2** · high
Jun hub: Flash self-verify Bo5 **79→88** on TB2.1. That’s **API** (`DEEPSEEK_API_KEY`), not Kevin. 11× cheaper = tweet only.
**Do not install.** Flash-as-Bo5-ranker ≠ Flash-as-worker.
