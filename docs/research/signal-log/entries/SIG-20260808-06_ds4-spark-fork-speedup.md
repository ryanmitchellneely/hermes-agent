# SIG-20260808-06 — DS4-Flash +27% on one Spark (Entrpi fork v0.5.6)

```yaml
id: SIG-20260808-06
date: 2026-08-08
title: "DeepSeek-V4-Flash 27% faster on one DGX Spark — DwarfStar/Entrpi fork v0.5.6"
source_url: "https://x.com/jmurillocode/status/2086139608442515884"
canonical_repo: "https://github.com/Entrpi/ds4-on-spark"
canonical_docs: "https://github.com/Entrpi/ds4/blob/v0.5.6/CHANGELOG.md"
bucket: inference
posture: steal
steal_rank: P0
confidence: high
hardware_fit: [spark]
stacks_touched: [t1000, k2]
related_plans:
  - "B17"
  - "~/.hermes/plans/2026-08-06_222342-spark-inference-experiments.md"
  - "~/.hermes/plans/2026-08-07_182701-k2-devbot-local-spark.md"
  - "t_d11fa676"
  - "SIG-20260807-03"
status: open
distill: none
```

## 1. Claim

@jmurillocode: DeepSeek-V4-Flash on **one DGX Spark** went **22.5 → 28.6 tok/s decode** (+27%),
prefill steady ~**1,060 tok/s**, because **DwarfStar v0.5.6** added Spark-specific fast paths and
**speculative decoding now engages during the thinking phase** — previously stuck at **1.0
tokens/step**, now **2.9 at 74% draft acceptance**. 284B params, no cloud.
Credits: DwarfStar engine · antirez ds4-on-spark · Entrpi wrapper · MiaAI_lab.

## 2. What we verified

**The fork is real (fetched):** `Entrpi/ds4-on-spark` — MIT, Shell, **★276**, pushed 2026-08-07.
Self-described: *"Blackwell CUDA perf fork of antirez/ds4 on NVIDIA DGX Spark: one-command
install, ~3x upstream prefill, ~1.5x decode, DSpark, and full continuous batch support."*
README **claimed** numbers: **2.4–3.3× prefill** (2.43× @2k, 3.30× @64k), **1.33–1.47× decode**
across 2k–128k, **59 tok/s aggregate at 12 concurrent**, 515K-token admit at 776 tok/s.

**Key compatibility fact from their README:** the **0731 checkpoint has no MTP head**, so
**DSpark is the only speculation path** — the installer ships a re-extracted drafter. Speculation
is armed at every depth since v0.4.0 (no kv-depth gate).

**Measured by us on Kevin's Spark (`spark-b01b`, 2026-08-08, live):**

| Fact | Value | Source |
|---|---|---|
| Install | `antirez/ds4` @ `b0309611` — **upstream, NOT the Entrpi fork** | `/srv/ryan-lab/ds4/INSTALL-RECEIPT.txt` |
| Upstream freshness | `b0309611` **is** upstream HEAD (2026-08-05); repo has **no tags** | GitHub API |
| Model | `DeepSeek-V4-Flash-IQ2XXS…chat-v2-imatrix-**0731**.gguf`, 86.7 GB | receipt |
| Launch flags | `--cuda --ctx 32768 --kv-disk-dir … --port 8889` — **no `--mtp*`, no speculation, no `--batched-session`** | `ps` |
| **Decode (ours)** | **16.07 tok/s** end-to-end, 169 completion tokens, 10.5 s, `finish=stop` | live `/v1/chat/completions` |
| Earlier log line | prefill 8.64 t/s · generation 11.88 t/s | prior session probe |

**So: ~16 tok/s (us, upstream, unspeculated) vs 28.6 tok/s (them, fork v0.5.6) ≈ 1.8× gap on the
same class of box and the same 0731 weights.**

Upstream `ds4-server --help all` does expose `--mtp / --mtp-draft (default **1**) / --mtp-margin /
--glm-mtp`. **Default `--mtp-draft 1` is literally the tweet's "stuck at 1.0 tokens/step" before-state** —
but the 0731 checkpoint has no MTP head, so upstream MTP flags alone are **not** the fix; DSpark
(fork-side) is.

## 3. Takeaways

- Our DS4 lane is running the **slow configuration**, and we can now name why: upstream engine, no drafter, no batching.
- The gap is **config + fork**, not hardware — same GB10, same weights, same context.
- `--batched-session` (upstream) and the fork's continuous batching are the **multi-agent width** lever, tying straight into B17 **C2** (McNab-style N={1,8,16,32}).
- Prefill is the bigger multiple (2.4–3.3×) — matters most for long-context agent turns, not chat.
- Any change here is **Kevin's box, Kevin's call**: DS4 is serving now and the systemd unit already fails admission (`<105 GiB available`) while the manual server holds memory.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Bench before believing a lane is "fast enough"** | Record DS4 decode/prefill as a B17-style card; ours is 16 tok/s, target ≥28 | P0 | open |
| S2 | Spark-specific fork + drafter (DSpark) as the decode lever | **Propose** fork cutover to Kevin — do not install | P1 | open |
| S3 | Continuous batching / `--batched-session` = agent width | Fold into B17 **C2** as a DS4 concurrency row alongside Ollama | P1 | open |
| S4 | Report speculation health as a metric, not a vibe | Add **tokens/step + draft-accept %** to the B17 metric card (pairs with SIG-…-04) | P1 | open |
| S5 | Reasoning-phase speculation is where Flash spends its tokens | Any Flash caller must budget ≥256 max_tokens (reasoning_content burns first) | P2 | noted |

**Primary steal:** **S1** — the measured 16 vs 28.6 number is the asset; it turns "DS4 feels slow" into a tracked gap with a named cause.

## 5. Do not

- **Do not run the fork's one-command installer on Kevin's Spark.** His box, his hardware, currently serving; needs his explicit OK.
- Do not `sudo systemctl start ds4.service` — the unit is `failed` on memory admission *because* the manual server already owns the RAM. DS4 is up.
- Do not start Ollama on `spark-b01b` while DS4 holds ~80 GiB — that OOMs one of them.
- Do not chase upstream `--mtp*` flags on the 0731 weights (no MTP head) and call it speculation.
- Do not treat 28.6 tok/s as our number until we measure it ourselves.

## 6. Next action

- [x] signal-log entry + INDEX + STEALS
- [ ] B17: add DS4 row to the Phase A/C2 bench card (decode, prefill, tokens/step, accept %)
- [ ] kanban comment `t_d11fa676` (Kevin Spark lane) with the measured gap
- [ ] **Ryan → Kevin:** ask whether he wants the Entrpi fork cutover on `spark-b01b` (draft only; no send)
- [ ] no install, no service changes on Kevin's box

## 7. Chat blurb

DS4 on Kevin's Spark is running **upstream antirez/ds4, no speculation, no batching** — we measured
**16.07 tok/s**. The tweet's **28.6 tok/s** comes from **Entrpi/ds4-on-spark v0.5.6** (★276, MIT):
Spark fast paths + **DSpark drafter** (0731 weights have no MTP head) + continuous batching.
~1.8× on the table, config not hardware. Fork cutover is **Kevin's call** — proposed, not installed.
