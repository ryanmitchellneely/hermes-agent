# SIG-20260810-07 — TurboQuant TQ3_4S: 1M context on our exact model, on our exact hardware class. And finding it caught a live half-applied cutover on kevin-spark.

```yaml
id: SIG-20260810-07
date: 2026-08-10
title: "TurboQuant TQ3_4S requant of DeepSeek-V4-Flash-0731 — 91 GiB / 2.73 bpw serving full 1,048,576 context on a single DGX Spark at 18.4 tok/s (22.9 with DSpark drafter), via a third-party llama.cpp fork (coffeecup2020 / YTan2000 / turbo-tan)"
index_title: "TurboQuant TQ3_4S: 1M ctx on DS4-Flash-0731 — OUR model, OUR hardware class (GB10 is listed tested hardware). 16x our ctx at +14% decode. NOT portable to ds4-server (verified: ds4 has NO KV-quant flag), needs the tq3 fork. Finding it caught a LIVE REGRESSION: kevin-spark's unit gate verifies the fork commit but ExecStart launches the upstream rollback binary — we lost the measured 25-26 tok/s win and are running 13.0-13.7"
source_url: "https://x.com/coffeecup2020/status/2086875594390679572"
canonical_repo: "https://github.com/turbo-tan/llama.cpp-tq3"
canonical_docs: "https://huggingface.co/YTan2000/R2-DeepSeek-V4-Flash-0731-TQ3_4S"
index_links: [HF, repo]
bucket: inference
posture: spike
steal_rank: P0
confidence: high          # model card fetched verbatim; fork + author track record read off GitHub/HF APIs; every counter-number and every portability claim measured live on kevin-spark + ryan-spark
hardware_fit: [spark, kevin-spark]
stacks_touched: [t1000, ds4]
related_plans:
  - "B17"                 # Spark inference experiments — this is an engine+quant candidate
  - "t_99c5d345"          # B17 card
  - "t_43e997d2"          # Entrpi fork cutover / drafter provenance — WHERE THE REGRESSION BELONGS
  - "t_d1947f46"          # K5 supervision (regressed per 08-08 audit)
  - "t_01ac807e"          # ctx 32768 -> 65536 (the ceiling this signal dwarfs)
  - "t_e471787f"          # kv-disk 8192 -> 65536
  - "t_6e058ca2"          # bench provenance contract
  - "t_08e96127"          # vLLM sm121 wheel spike (competing engine candidate)
  - "SIG-20260810-06"     # KV disagg — same model, KV-cost adjacency
  - "SIG-20260808-06"     # Entrpi fork (the other DS4 engine candidate)
status: carded
status_note: "Primary steal CARDED (see card in §6). **Two findings outrank the link itself.** (1) VERIFIED LIVE: `ds4-server --help` has NO KV-cache-dtype flag at all — its KV section is disk-checkpoint only. So the 1M trick is NOT portable to our DS4 lane; it requires leaving antirez/ds4 for the tq3 fork. (2) VERIFIED LIVE: kevin-spark's `ds4.service` ExecStartPre greps for the FORK commit `3b792c9a` (and passes — the receipt was updated) but ExecStart launches `/srv/ryan-lab/ds4/app/ds4-server`, which the fork receipt itself names as `rollback=... (upstream b0309611 binary retained, same flags no spec env)`. Half-applied cutover: receipt+gate moved, binary+spec env did not. Journal decode 13.0-13.7 t/s under load vs the fork receipt's banked 25-26. (3) CORRECTED MID-WRITE: my first pass said 'we have never used KV quantization' — FALSE. The ryan-spark Ollama unit sets OLLAMA_KV_CACHE_TYPE=q8_0 + OLLAMA_FLASH_ATTENTION=1 fleet-wide, and our own ~/llama-ab-start.sh:13-14 sets q8_0 too, so the t_227d09b2 120b benches were never f16-KV runs. The untested step is q8_0 -> q4_0 (TurboQuant's own K dtype). Also banked: per-slot ctx already served is 131,072 for gpt-oss:120b and 16,384 for hermes3:8b-16k, and OLLAMA_KEEP_ALIVE=-1 is set globally in the unit — the mechanism behind the 08-09 memory jam."
distill: none
```

## 1. Claim

David Y. Tan (@coffeecup2020) flags YTan2000's `R2-DeepSeek-V4-Flash-0731-TQ3_4S`: a selective-imatrix
requant of **DeepSeek-V4-Flash-0731** (284B MoE / 13B active) at **91 GiB / 2.73 bpw** that serves
**full 1,048,576 context on a single box** — either an RTX 3090 24 GB + 125 GB DDR4 (experts on CPU,
14.3 tok/s) or **a single DGX Spark GB10 (18.4 tok/s, 22.9 with the DSpark drafter)**. Compressed KV
(`-ctk q4_0 -ctv tq3_0`) is what makes 1M context cost only ~14 GB. Credit for the KV cache work goes
to @no_stp_on_snek. Requires the **TurboQuant fork** of llama.cpp — stock builds cannot load the
`TQ3_4S` tensor type.

**This is the first signal in the log whose subject is the exact model we serve in production, on the
exact hardware class we own.**

## 2. What we verified

### The source is real and the author has a track record

| Thing | Measured |
|---|---|
| `turbo-tan/llama.cpp-tq3` | **222★, 16 forks, MIT**, fork of `ggml-org/llama.cpp`, created 2026-03-30, **pushed 2026-08-10 20:11Z** |
| Fork description | *"TQ3_1S/4S **CUDA kernels** — 3.5-bit WHT quantization achieving Q4s quality at 10% smaller size. Based on RaBitQ-inspired Walsh-Hadamard transform."* |
| `turbo-tan/recipes` | 0★, created 08-05, pushed today. Real but brand new. No license file. |
| HF repo | created **2026-08-10 09:26Z**, modified 22:16Z — **hours old. `downloads: 0`, `likes: 3`.** |
| Shards | 9 files, **96.99 GB decimal = ~90.3 GiB** — card's "91 GB" is GiB and checks out |
| `license` | **`other`** — base DeepSeek-V4-Flash license applies. Runtime fork is MIT. |
| Author (`YTan2000`) | **17 models.** Top: `Laguna-XS-2.1` 2,730 dl · `Qwen3.6-27B-TQ3_4S` 1,432 dl / 71 likes · `Qwen3.6-35B-A3B` 952 dl / **83 likes** · `Ornith-1.0` 671 dl |
| Prior DS4-Flash TQ3_4S (110 GB, 512K) | **320 downloads**, created 08-03 — so this is the author's *second* pass at our model |

So `downloads: 0` is "twelve hours old," not "nobody trusts it." This is a prolific, followed quantizer.

### The card's honesty is checkable, and it checks out

Three places the card volunteers something against its own interest — all three verified true:

1. **"Stock `llama.cpp` builds cannot load it."** Confirmed independently on ryan-spark:
   `ggml/include/ggml.h` at `62bf73d` has only `GGML_TYPE_TQ1_0 = 34` and `GGML_TYPE_TQ2_0 = 35`.
   **No TQ3.** `grep -ril "turboquant|TQ3_4|TQ_3"` across the tree → **zero hits.**
2. **"does not contain an MTP draft block, so no `--spec-type draft-mtp` flags apply."** This
   independently corroborates our own finding — `t_716141c4` failed `--mtp-draft` because the 0731
   checkpoint ships no MTP head.
3. **Self-flagged benchmark inconsistency:** *"the 3090 suite run used reasoning budget 81,920
   (garden server) rather than the 256 used for the Spark baselines."* An author who discloses that
   is doing better than most of the log.

### The comparison that makes this P0 — measured on kevin-spark, not inferred

| | **Ours, live now** | **TQ3_4S claim (Spark)** |
|---|---|---|
| Model | `DeepSeek-V4-Flash-IQ2XXS-w2Q2K-AProjQ8-SExpQ8-OutQ8-chat-v2-imatrix-0731.gguf` | `R2_TQ3_4S` (same 0731 base) |
| Size | 86.72 GB = **80.8 GiB** | **91 GiB** (+10 GiB) |
| **Context** | **65,536** | **1,048,576 — 16×** |
| Decode | **16.07 clean / 13.0–13.7 under tool-call load** | **18.4 (22.9 + DSpark)** |
| Engine | `antirez/ds4` `b0309611` | `turbo-tan/llama.cpp-tq3` (build v10413) |
| KV | disk checkpoints, **f16 in memory**, 13.77 KB/tok | **`-ctk q4_0 -ctv tq3_0`, ~14 GB for 1M** |

**16× the context at equal-or-better decode, on the same silicon.** Our ctx 32768→65536 raise
(`t_01ac807e`, this morning) was a 2× move that took a restart and a memory argument; this is 16×
beyond where we landed.

Cross-validation worth noting: their **22.9 tok/s with the DSpark drafter** sits right next to our own
fork receipt's banked **25–26 tok/s with DSpark on CUDA**. Two independent parties, same drafter, same
silicon class, same ballpark. That is mutual corroboration and it further buries the "upstream DSpark
is Metal-only ⇒ DSpark doesn't work on CUDA" reading of `t_716141c4`.

### ⛔ FINDING 1 — the 1M trick is NOT portable to our DS4 lane

`ds4-server --help` (read live on kevin-spark) has **no KV-cache-dtype flag of any kind.** Its entire
`Disk KV Cache` section is checkpointing: `--kv-disk-dir`, `--kv-disk-space-mb`,
`--kv-cache-min-tokens`, `--kv-cache-cold-max-tokens`, `--kv-cache-continued-interval-tokens`,
`--kv-cache-boundary-*`, `--kv-cache-reject-different-quant` (that last one is about *routed-expert*
quant, not KV dtype).

So **there is no `-ctk`/`-ctv` equivalent on `ds4-server`.** The compressed-KV mechanism that makes
1M context affordable cannot be applied to our current engine at all. Reaching 1M context on DS4
Flash means **replacing antirez/ds4 with the tq3 fork** — an engine migration, not a model download.
That is a materially bigger decision than the tweet implies, and it belongs to B17's engine phase
alongside `t_08e96127` (vLLM sm121 wheel), not beside it.

### ⛔ FINDING 2 — LIVE REGRESSION on kevin-spark: half-applied fork cutover

Found while establishing the decode baseline for the comparison above. Read live:

```
ExecStartPre=/usr/bin/grep -Fxq source_commit=3b792c9a5713b871a9f8875fca9d8ea1738b0072 \
                              /srv/ryan-lab/ds4/INSTALL-RECEIPT.txt     <-- FORK commit, and it PASSES
ExecStart=/srv/ryan-lab/ds4/app/ds4-server --cuda --ctx 65536 --kv-disk-space-mb 65536 ...
```

…and the fork's own receipt names that exact path as the rollback:

```
rollback=/srv/ryan-lab/ds4/app/ds4-server (upstream b0309611 binary retained, same flags no spec env)
```

| Evidence | Value |
|---|---|
| `app/ds4-server` | 41,427,752 B, **Aug 8 08:56** → matches upstream receipt (`2026-08-08T09:59:27`) |
| `fork-src/ds4-server` | 36,145,536 B, **Aug 9 22:44** → matches fork receipt (`2026-08-09T22:53:34`) |
| Running proc | PID **4072645**, `app/ds4-server` — **the upstream/rollback binary** |
| Spec env | **absent.** Unit sets only `HOME` + `CUDA_CACHE_PATH`; no `DS4_CONT_MTP_MODE=2`, no `DS4_CONT_DSPARK=1` |
| `NRestarts` | **21**; current start `Mon 2026-08-10 18:49:26 EDT` |
| Journal decode, real tool-call traffic @ ~60k ctx | **13.0–13.7 t/s** (`avg=13.05–13.30`) |
| Fork receipt banked | **25–26 tok/s, accept 72–73%, tok_per_step 2.83–3.00** |

**The receipt and the gate were moved to the fork; the binary and the spec env were not.** The gate
greps a text file, so it passes while launching the rollback path. Every DS4 worker card since 18:49
has run at roughly **half** the fork's measured decode. The 08-08 audit caught the earlier half of
this (fork running unsupervised, unit dead); the unit is now supervised — and supervising the wrong
binary is what makes it durable instead of accidental.

### ⚠️ CORRECTION — my first pass claimed "we have never used KV quantization." That is FALSE.

I wrote that after confirming `llama.cpp 62bf73d` exposes `-ctk`/`-ctv`/`-fa`/`-ncmoe`/`-fit` (plus
draft-specific `-ctkd`/`-ctvd`), and inferred we had never set them. A damage check on ryan-spark
falsified it within minutes — `pgrep -af llama-server` shows **Ollama's own bundled runner already
running with KV quantization on both loaded models**:

```
--cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on -b 1024 -ub 1024 -np 2 --context-shift
```

Root cause, read off the unit environment:

```
OLLAMA_KV_CACHE_TYPE=q8_0     OLLAMA_FLASH_ATTENTION=1
OLLAMA_KEEP_ALIVE=-1          OLLAMA_NUM_PARALLEL=2
```

And our **own** manual A/B script does the same — `~/llama-ab-start.sh:13-14` sets
`--cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on`. So the `t_227d09b2` 120b benches
(49–50 tok/s) were **not** f16-KV runs.

**The corrected steal is narrower but still real.** We are at **q8_0**; TurboQuant's config is
**`-ctk q4_0 -ctv tq3_0`**. The untested step is **q8_0 → q4_0** (another ~2× off KV), and *nobody has
measured its quality cost on our traffic.* That is the actual free experiment.

Two fleet facts banked while establishing this, neither previously written down:

| Fact | Value |
|---|---|
| Per-slot context already served on ryan-spark | `gpt-oss:120b` **131,072** (`-c 262144 -np 2`) · `hermes3:8b-16k` **16,384** (`-c 32768 -np 2`) |
| `OLLAMA_KEEP_ALIVE=-1` is set **globally in the unit** | So *every* model Ollama loads is pinned Forever — this is the mechanism behind the 08-09 memory jam (~6 GB available), not a per-model choice |

## 3. Takeaways (max 5)

- **A published, benchmarked 16×-context path exists for the exact model we serve, on the exact
  silicon we own** — and it is gated on an engine migration, not on hardware.
- **`ds4-server` has no KV-dtype knob.** Compressed KV is unreachable without leaving antirez/ds4.
  This is now a *third* independent reason B17's engine phase is the real gate.
- **We are currently running the rollback binary on kevin-spark** and have silently given back a
  measured ~1.6× decode win. This outranks the signal.
- **KV quantization is already on across the fleet at `q8_0`** (Ollama unit env + our own A/B script).
  The untested step is **q8_0 → q4_0**, which is what buys the context — and its quality cost on our
  traffic is unmeasured. *(My first pass claimed we'd never used KV quant at all; falsified in minutes
  by a damage check. Corrected in §2.)*
- Their DSpark number (22.9) independently corroborates our fork receipt (25–26). Two parties, same
  drafter, same silicon — the CUDA DSpark path is real.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **A same-model, same-silicon 16×-context checkpoint exists — spike it on *Ryan's* box, never Kevin's** | Build `turbo-tan/llama.cpp-tq3` on ryan-spark, pull the 97 GB / 9-shard GGUF, serve at a **stepped** ctx (256k → 512k → 1M), non-prod port. Gate on the repair-battery + a golden set, report decode **and** quality — the card's own numbers show R2 is *worse* on HumanEval than the 110 GB predecessor (90.9 vs 94.5) while better on Hard86 (76 vs 70). Never on kevin-spark: 91 GiB + ~14 GB KV ≈ 105 GiB fully displaces DS4 | **P0** | **carded** |
| **S2** | **The KV step we have NOT taken is `q8_0 → q4_0`** *(corrected — see §2; we are already at q8_0 fleet-wide, not f16)* | On ryan-spark's existing llama.cpp 120b lane: `-ctk q4_0 -ctv q4_0` vs the current `q8_0` baseline, one variable, `-fa on` held constant, golden-gated. Report decode · prefill · peak resident · **max ctx that fits** · pass rate. Free — no fork, no download, no new weights. This is the exact K-cache dtype TurboQuant uses, so it prices the quality half of their 1M claim before anyone spends 97 GB | **P1** | open → folded into the card as **Phase 0** |
| S3 | **A supervisor that verifies a receipt file is not verifying a binary** | `ExecStartPre` should assert the *artifact* (path + sha256 of the running binary), not a grep of a text file the artifact does not have to agree with | **P0** | → comment on `t_43e997d2` / `t_d1947f46` |
| S4 | Selective per-tensor imatrix requant as the size lever (routed experts → IQ2_S carry coding quality; attention/embeddings stay q6_K) | We already do targeted requant (`t_000b7473`). Their published tensor-type file is a reference recipe for any future pass | P1 | open — log only |
| S5 | `--n-cpu-moe` as a deliberate placement knob (experts→CPU, attention→GPU) is what lets a 24 GB 3090 serve 1M | Irrelevant on unified-memory GB10, but it is the mechanism behind the "3090" headline and should not be read as "24 GB is enough on any box" | P2 | open — log only |

**Primary steal (one only):** **S1** — with **S2** as its cheap pre-step, because S2 answers "does the
`q8_0 → q4_0` KV step hold quality on our traffic" for free before anyone spends 97 GB and a fork build.

## 5. Do not

- **Do not run this on kevin-spark.** 91 GiB + ~14 GB KV ≈ 105 GiB, and DS4 already holds 105.1 GiB
  of 121. It is a displacement, not an addition — it would take the production code lane down.
- **Do not `curl | sh` the fork build**, and do not install it into `~/.t1000` or any production path.
  Third-party fork (222★, MIT) built in a scratch dir; rollback = delete the dir.
- **Do not treat 1M context as free.** The card's own quality table shows HumanEval/HumanEval+
  *regressing* vs the larger predecessor. Context and quality moved in opposite directions.
- **Do not read "RTX 3090 24 GB" as "any 24 GB card."** That config needs 125 GB of system RAM and
  `--n-cpu-moe 39`; the GPU holds attention only.
- **Do not quietly `systemctl restart ds4` to "fix" the regression** — that relaunches the same
  rollback binary. The fix is a drop-in pointing `ExecStart` at `fork-src/ds4-server` plus the two
  `DS4_CONT_*` env lines, and that is an engine change on Kevin's box needing Ryan's explicit OK.
- **Do not fold this into `t_08e96127`.** vLLM (width/prefill) and tq3 (context/KV) are different
  levers with different weights; benching them as one confounds both.

## 6. Next action (mechanical)

- [x] add/update STEALS.md rollup
- [x] kanban card — LAB spike, blocked on Ryan (window + supply-chain OK)
- [x] kanban comment `t_43e997d2` + `t_d1947f46` — the half-applied cutover regression
- [ ] AUTOMATION-ROADMAP row — not yet; B17 owns the engine phase
- [ ] patch plan B17 — defer until the engine phase is actually opened

## 7. Chat blurb

`SIG-20260810-07` · `inference` · **spike P0** — TurboQuant `TQ3_4S` serves **1M context** on
**DeepSeek-V4-Flash-0731 (our model)** on **a single DGX Spark (our silicon)** at 18.4 tok/s / 22.9
with DSpark, 91 GiB @ 2.73 bpw. Fork is real: `turbo-tan/llama.cpp-tq3` **222★ MIT, CUDA kernels**;
author has 17 models, top one 2,730 downloads. **Two findings outrank the link.** (1) `ds4-server`
has **no KV-dtype flag** — the 1M trick needs leaving antirez/ds4, so this is an engine migration.
(2) **Live regression:** kevin-spark's unit gate greps the *fork* commit and passes, but `ExecStart`
launches `app/ds4-server` — which the fork receipt itself names as the **upstream rollback binary**,
with no `DS4_CONT_DSPARK` env. Journal decode **13.0–13.7 t/s** vs the fork's banked **25–26**.
Third steal, corrected mid-write: I claimed we'd never used KV quantization — **false**, the Ollama
unit sets `OLLAMA_KV_CACHE_TYPE=q8_0` fleet-wide and our own A/B script sets it too. The untested step
is **`q8_0 → q4_0`**, which is exactly TurboQuant's K-cache dtype — free to bench, and it prices the
quality half of their claim before anyone downloads 97 GB.
