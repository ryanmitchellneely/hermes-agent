# SIG-20260826-05 — AWS Handoff Tax: don't escalate with the cheap model's diary

```yaml
id: SIG-20260826-05
date: 2026-08-26
title: "elvis clip of AWS AI Labs 'Handoff Tax' (arXiv 2608.24358). Full-trajectory escalate recovers <half the LC→HC quality gap and costs extra. Cutting the weak trajectory improves escalate; keeping the strong trajectory helps downshift. Steal P1: closer gets repo+goal, not the cheap model's chain-of-thought. No install."
index_title: "AWS Handoff Tax (arXiv 2608.24358) — full-traj escalate recovers <½ LC–HC gap. Cut cheap trajectory on the way UP; keep strong trajectory on the way DOWN. Steal P1 for 120b/Grok/Max closers. Claude+GPT pairs, not our Flash. No code."
index_links: [docs]
source_url: "https://x.com/omarsar0/status/2092633423617953811"
canonical_repo: ""
canonical_docs: "https://arxiv.org/abs/2608.24358"
bucket: harness
posture: steal
steal_rank: P1
confidence: high          # fxtwitter verbatim + first-page OCR; arXiv abs matches. No PDF full-read, no re-bench.
hardware_fit: [none]
stacks_touched: [t1000, k2]
related_plans:
  - "SIG-20260808-02"     # parent-strong / child-cheap
  - "SIG-20260811-06"     # Switchyard escalate-after-judging-the-turn
  - "SIG-20260807-02"     # B22
  - "t_6c3fd131"          # capability projection — what you hand the closer
status: open
status_note: "**OPEN — steal P1, no card.** Hardware pre-filter N/A. elvis is megaphone; artifact is AWS Agentic AI (Ganz / Nacson / Kalyanpur / Litman). Claude+GPT pairs, repo state preserved. Fold: escalate = compact+repo, not full cheap transcript."
distill: none
```

## 1. Claim

[@omarsar0](https://x.com/omarsar0/status/2092633423617953811) (elvis / DAIR; ~315k followers; **53 likes / 5 RTs / 52 bookmarks / 4.3k views** at read; 2026-08-26 15:21 UTC). Fetched verbatim via `api.fxtwitter.com`:

> … Escalating to a stronger model mid-run is usually the resort when a cheap agent stalls. …
> Across pairs of Claude and GPT models, full-trajectory escalation recovers less than half the quality gap between the weak and strong model while adding a substantial cost premium. The authors call that penalty the handoff tax. Downshifting lands at a much better cost-quality point.
> Cutting the weak model's trajectory information improves escalation quality, while removing the strong model's trajectory hurts downshift quality.

Paper: **The Handoff Tax: Continuing Non-Native Trajectories in LLM Agents** — Roy Ganz, Mor Shpigel Nacson, Adi Kalyanpur, Ron Litman. **AWS, Agentic AI.** arXiv **2608.24358**, 25 Aug 2026.

He is a **megaphone**.

## 2. What we verified

| Check | Result |
|---|---|
| Post + first page | **verbatim** + OCR matches the arXiv abstract word-for-word on the tax definition |
| Method | LC/HC pairs inside Claude family and inside GPT family. Vary **direction** (escalate vs downshift), **timing**, **interface**: full-trajectory / compaction / **trajectory removal**, **repo state kept** |
| Headline | Full-traj escalate recovers **< half** of the LC→HC gap + cost premium = **handoff tax**. Downshift is the better cost–quality point |
| Interface flip | **Escalate:** less LC trajectory → *better*. **Downshift:** drop HC trajectory → *worse* |
| Hardware pre-filter | **N/A / pass** |
| Code / re-bench | **None in this pass.** Claude+GPT coding agents, not Flash/120b/Grok |
| Duplicate URL | None. Complements Switchyard (judge the cheap *turn* before latching) — this is what you *pass* after you decide to switch |

## 3. Takeaways (max 5)

- **This is our closer protocol, measured.** Mesh worker (Flash/27B/Nemotron) → 120b/Grok/Max. Today the closer often inherits the cheap model's diary. AWS says that is the expensive half-recovery.
- **Escalate with repo + goal, not CoT.** The receiving model continues a *non-native* trajectory. Their best escalate interface is **cut the weak trace, keep the files**.
- **Downshift is the opposite.** If Grok/Opus did the hard part, the cheap finisher needs that trajectory.
- **Not a reason to stop using cheap workers.** The tax is on the *switch payload*, not on starting cheap.
- **Claude/GPT pairs, not our lanes.** Direction is high-confidence; the ½ figure is theirs. Don't quote it as a Spark number.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Escalate = compact + repo; downshift = keep the strong trace** | When a worker is handed to a closer (120b / Grok / claude-acp): pass card goal + git state / file list, **not** the cheap model's reasoning dump. Inverse if we ever downshift Max→Flash | **P1** | fold — dispatch/closer contract; no new card |
| S2 | Handoff tax = (quality recovered / LC–HC gap) < 0.5 + extra $ | Name it on any “just escalate to Opus” row. Don't install anything | P2 | log only |

**Primary steal (one only): S1.** True whether or not we re-run their Claude pairs.

## 5. Do not

- **Do not dump a Flash/Nemotron/27B transcript into Max “so it has context.”** That is the taxed interface.
- **Do not treat <½ as our measured number.** Claude/GPT, their harness.
- **Do not stop B22 cheap-first.** Start cheap; switch *payload* is the lever.
- **Do not open a card** to re-bench this on Spark.

## 6. Next action (mechanical)

- [x] INDEX regenerated
- [x] STEALS.md row
- [ ] no card
- [ ] no install

## 7. Chat blurb

`SIG-20260826-05` · `harness` · **steal P1** · AWS **handoff tax**: full-traj escalate recovers **< half** the quality gap. Cut the cheap model's diary on the way up; keep the strong trace on the way down. Closer gets **repo + goal**, not the worker CoT.
