# SIG-20260823-03 — MiaAI One-Spark EXL3 recipe is a public Docker of the stack we already serve

```yaml
id: SIG-20260823-03
date: 2026-08-23
title: "MiaAI One-Spark EXL3 Flash recipe — public Docker of the stack we already serve. 47 tok/s @ 384k/util 0.94 is not a win vs our C1 ~56 @ 256k/0.85. Steal P1: try 384k at 0.85 if pool still >=440k; do not copy start.sh."
index_title: "MiaAI One-Spark EXL3 (★173 MIT, 2026-08-20) — public SparkInfer+0xSero recipe of Kevin's live lane. Tweet 47 tok/s is 384k/util 0.94 think-off. Our C1 p50 is 54.8–55.8 @ 256k/0.85 (0.90 = 19.5). Steal P1: 384k at 0.85 if pool ≥440k; do not ./start.sh."
index_links: [repo]
source_url: "https://x.com/MiaAI_lab/status/2090737183099384193"
canonical_repo: "https://github.com/MiaAI-Lab/DeepSeek-v4-Flash-One-DGX-Spark"
canonical_docs: "https://github.com/MiaAI-Lab/DeepSeek-v4-Flash-One-DGX-Spark#measured-results"
bucket: inference
posture: steal
steal_rank: P1
confidence: high          # fxtwitter verbatim; GH API + full README; fleet C1 table already measured 2026-08-16. No pull, no start.sh.
hardware_fit: [spark]
stacks_touched: [t1000, k2]
related_plans:
  - "SIG-20260808-06"     # Entrpi/ds4 IQ2 path — parked
  - "SIG-20260812-04"     # REAP K216 family
  - "flash-256k-util-085"
  - "exl3-k2-spark"
status: open
status_note: "**OPEN — steal P1, no new card.** Hardware pre-filter N/A (not a PCIe-offload win). We already run SparkInfer EXL3-K2 on kevin `:8889` (2026-08-15). Do not `./start.sh`, do not util 0.94. One-variable 384k @ 0.85 only on Ryan OK."
distill: none
```

## 1. Claim

[@MiaAI_lab](https://x.com/MiaAI_lab/status/2090737183099384193) (Mia; ~17k followers; **1,334 likes / 146 RTs / 1,248 bookmarks / 134 replies / 179k views** at read; 2026-08-21 09:46 UTC; note-tweet). Fetched verbatim via `api.fxtwitter.com`:

> A BIG moment for all DGX Spark users
>
> You can now run DeepSeek v4 Flash 0731 without needing a second unit, with quality high enough for reliable code generation, high context, and great speed!
>
> Optimized for single stream session:
> - EXL3 quantization
> - 384k context (conservative) / ~440k kv cache
> - 47 tok/s single stream (structured)
> - 1024 tok/s prefill
> - 370k token needle test passed
>
> Thanks @0xSero … Tuned for SparkInfer + DSpark … same quality of a Q4_K_M / Q5 GGUF!
>
> Get it here: https://github.com/MiaAI-Lab/DeepSeek-v4-Flash-One-DGX-Spark

## 2. What we verified

| Check | Result |
|---|---|
| Post body | **verbatim** via fxtwitter + vxtwitter |
| Repo | `MiaAI-Lab/DeepSeek-v4-Flash-One-DGX-Spark` — **★173 / 19 forks**, **MIT** (glue only), created **2026-08-20**, pushed **2026-08-21T23:22Z**. No GitHub release. Python launcher + bind-mount kernel patches |
| Runtime | `ghcr.io/0xsero/deepseek-v4-flash-0731-spark-sparkinfer` (vLLM 26.02 base). Kernel = `local-inference-lab/b12x` (SparkInfer, formerly b12x). Weights = `0xSero/deepseek-v4-flash-0731-spark` (**EXL3 3.0 bpw, REAP-K216 = 216/256 experts**, ~99.5–107 GiB) |
| Their defaults | `MAX_MODEL_LEN=384000` · `GPU_MEMORY_UTILIZATION=0.94` · `MAX_NUM_SEQS=1` · `KV_RECORD=stock432` · `MODE=dspark` K5 / K64 draft · bind `0.0.0.0:8888` **no auth** · disable earlyoom |
| Their numbers (**claimed**, 2026-08-21) | Decode **44–47 tok/s structured** at 384k; KV pool **439,622**; NIAH 320k + **370,104** exact recall, 0 preemptions; prefill **~1,024 tok/s at start → ~625 effective** on the 370k run (tweet quotes only the start) |
| Hardware pre-filter | **N/A / pass.** One-Spark serve, not a PCIe host↔device win |
| Duplicate URL | None. Sibling of SIG-20260808-06 (Entrpi/ds4 IQ2, parked) — **different engine** |
| **Our live lane** | Kevin `:8889` = **SparkInfer EXL3-K2**, model id `deepseek-v4-flash`, **256k**, `MODE=dspark`, `ds4.service` parked **2026-08-15**. Same family as this recipe |

**The 47 vs 56, named.** Same C1 protocol we already use (stream, 512 forced, thinking off):

| Serve | KV pool | C1 p50 | Source |
|---|---:|---:|---|
| Our 65k / 0.85 | ~189k | **55.8** | `flash-1x-sidedoor-bakeoff` |
| Our 256k / **0.90** | 838k | **19.5** | `flash-256k-util-085` |
| **Our 256k / 0.85 (live)** | **609k** (2.3× a 256k request) | **54.8–55.8** | same |
| Their 384k / **0.94** | 439,622 | **44–47 structured** (not C1) | README 2026-08-21 |

0.94 is the next notch past the util that already **halved** our short-prompt decode. Tweet 47 is think-off structured at deep ctx — not a C1 win, and not “we cannot run Flash on one Spark.” We have been doing that since 08-15.

Prefill: tweet **1024** is the *start* of a request. Their own 370k NIAH is **~625 tok/s effective** / ~10 min for a full 384k prefill.

Quality: README maps EXL3 3.0 → “IQ4_XS / Q4_K_S, often feels Q4–Q5” then the tweet collapses that to **Q4_K_M / Q5**. Weights are also **REAP-K216** (SIG-20260812-04). Two levers, one slogan.

## 3. Takeaways (max 5)

- **MiaAI is packaging our live engine, eight days late.** SparkInfer + 0xSero EXL3 + DSpark on 1× GB10 is Kevin `:8889` today. “No second unit” is not news here.
- **47 tok/s is the deep-ctx / high-util cell.** Our C1 at 256k/0.85 is **54.8–55.8**. Copying `GPU_MEMORY_UTILIZATION=0.94` is the 0.90 trap.
- **We already have the KV headroom for 384k at 0.85.** Live pool **609k** > their 440k need. The lever is `MAX_MODEL_LEN`, not util, not a 107 GB re-pull.
- **Prefill 1024 is the best cell.** Depth decays; a 384k cold prefill is ~10 minutes. Agent turns at 35k–60k are a different number.
- **No auth + `0.0.0.0:8888` + disable earlyoom** is their quickstart. Ours stays tunneled `:8889`.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **384k at util 0.85 if the pool already clears ~440k** — do not copy their 0.94 | One-variable: `MAX_MODEL_LEN` 262144 → 384000 on `exl3-k2-spark`, util **held 0.85**. Recreate compose. Remeasure C1 + a 370k NIAH. Hermes `providers.kevin-spark.context_length` moves with it. Ryan OK first (`:8889` down ~3–4 min) | **P1** | open |
| S2 | `KV_RECORD=stock432` (432-byte NVFP4 vs padded 584) as a pool grow that is *not* util | Citation-only until we confirm which layout the live compose already uses | P2 | log only |
| S3 | Tweet prefill is start-of-request; report start **and** effective-at-depth | Already the bench-contract shape (prefill ≠ decode) | P2 | fold into `t_6e058ca2` if kicked |

**Primary steal (one only):** S1.

## 5. Do not

- **Do not `./start.sh` on kevin-spark.** 107 GB pull, util 0.94, port 8888, no auth, earlyoom off, would displace the live `:8889` lane.
- **Do not raise `GPU_MEMORY_UTILIZATION` past 0.85.** Measured: 0.90 → C1 **19.5**.
- **Do not quote 47 as faster than us, or 1024 as our prefill.** Different instrument, best cell.
- **Do not treat EXL3 3.0 as Q5, or forget it is REAP-K216.** Two quality claims, neither re-benched here.
- **Do not `systemctl restart ds4`.** IQ2 path stays parked.

## 6. Next action (mechanical)

- [x] write entry + regenerate INDEX
- [x] STEALS.md P1 row
- [ ] no new card — one-variable bump waits on Ryan OK; existing Flash lane docs already own the util law
- [ ] on OK: comment the bump onto the live EXL3-K2 serve note (`flash-256k-util-085`), not a new mesh card

## 7. Chat blurb

**SIG-20260823-03** · inference · steal **P1** · high
MiaAI public SparkInfer+EXL3 Docker — we already serve this on Kevin `:8889`. Tweet **47 tok/s @ 384k/0.94** is not a win vs our **C1 54.8–55.8 @ 256k/0.85** (0.90 = 19.5).
**Steal:** raise `MAX_MODEL_LEN` to 384k **at 0.85** if the 609k pool still clears ~440k. Do not `./start.sh`.
Entry: `docs/research/signal-log/entries/SIG-20260823-03_miaai-exl3-one-spark-384k.md`
