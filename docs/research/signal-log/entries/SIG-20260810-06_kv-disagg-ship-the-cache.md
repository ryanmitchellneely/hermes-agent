# SIG-20260810-06 — Ship the prefilled cache: Spark prefills, Mac decodes. We measured his central number on our own box and it is 3.2× cheaper.

```yaml
id: SIG-20260810-06
date: 2026-08-10
title: "Heterogeneous inference / KV disaggregation — DGX Spark prefills, M4 Max decodes, ship the KV cache file between them (danpacary)"
index_title: "KV disagg: Spark prefills, Mac decodes, ship the .kv file. He projects 44 KB/tok for DS4 Flash; we MEASURED 13.77 KB/tok on the same model = 3.2x cheaper, 500k ships in ~6s not 20s. Not reproducible on our fleet: MBP is 64GB, GGUF is 86.7GB"
index_links: [img]
source_url: "https://x.com/danpacary/status/2086851964261003615"
canonical_repo: ""
canonical_docs: ""
bucket: inference
posture: steal
steal_rank: P1
confidence: high          # post + attached graphic fetched verbatim via api.fxtwitter.com; every counter-number measured live on kevin-spark from ds4 journal + kv dir
hardware_fit: [kevin-spark, mbp]
stacks_touched: [t1000, ds4]
related_plans:
  - "B17"                 # Spark inference experiments
  - "t_99c5d345"          # B17 card
  - "t_e471787f"          # kv-disk 8192->65536 (source of our KV/token measurement)
  - "t_01ac807e"          # ctx 32768->65536
  - "t_6e058ca2"          # bench provenance contract
  - "SIG-20260808-03"     # cross-model KV transfer (adjacent: cross-MODEL vs cross-BOX)
  - "SIG-20260808-06"     # Entrpi fork
status: open
status_note: "Not carded. Primary steal is a MEASUREMENT we already own (13.77 KB/tok), not a build. The experiment itself is NOT reproducible on our fleet — MBP is 64GB, ds4flash.gguf is 86.7GB, byte-identical-weights-on-both-boxes fails. Revisit if a small-GGUF lane appears."
distill: none
```

## 1. Claim

[@danpacary](https://x.com/danpacary/status/2086851964261003615) (Daniel Isaac, 2,997 followers,
2026-08-10 16:27Z, 19♥ / 1,098 views). Same author as `SIG-20260809-01` (repair-pass), different
project.

> *"new experiment: heterogeneous inference — macbook pro + DGX Spark. the spark does prefill, the
> m4 max does decode. leveraging each box for what it is actually good at … why this split: the
> spark prefills DeepSeek at 1.5-2.3k tok/s and the mac's wall at long context is exactly prefill.
> and **DeepSeek's cache is 86 KB per token** = the one cache small enough to ship. qwen is 112,
> laguna is 160 … same GGUF byte-identical on both boxes · spark prefills → writes the kv cache to
> disk (ds4 already does this, content-addressed files) · ship the file → mac decodes a context it
> never read"*

**His projected shipping table** (explicitly "nothing wired is tested yet · these are projections"):

| context | cache | wifi (~0.75 Gbit/s) | 10GbE (~1.1 GB/s) |
|---|---|---|---|
| 128k | 5.8 GB | 62 s | 5 s |
| 500k | 22.5 GB | 4 min | 20 s |
| 1M | 46.2 GB | 8 min | 42 s |

Rig: **M4 Max 128 GB + DGX Spark GB10**. Graphic footnotes: *"kv geometry from model configs · q8
cache"*, *"vLLM-NVFP4 to MLX-4bit is impossible · GGUF is the bridge"*.

His pre-registered gate, which is the best part of the post:

> *"a handed-off cache must produce **99% token-identical output** vs prefilling locally.
> correctness first, then the speed."*

## 2. He is modelling the exact model we run — so we measured it

His headline bar is **DeepSeek V4 Flash**, labelled `MQA · 1 kv head → 86 KB/tok`. That is
`ds4flash.gguf` on `kevin-spark`. The artifact he proposes shipping — content-addressed `.kv`
files — **already exists on our disk**, so his projection is directly measurable rather than
arguable.

**Live on `kevin-spark` (read-only):**

```
--kv-disk-dir /srv/ryan-lab/ds4/kv   →  15 GB, 48 content-addressed *.kv files
largest entry                        →  926,290,736 B (883.4 MiB)
```

The `ds4-server` journal logs every write as `kv cache stored tokens=N … size=M MiB`. **17 paired
(tokens, size) datapoints** spanning 563 → 65,282 tokens, fitted:

```
size_MiB = 22.85 + 0.013131 × tokens          (max residual 0.04 MiB across all 17 points)

  marginal :  13,768 B/token  =  13.45 KiB/tok  =  13.77 KB/tok
  fixed    :  22.9 MiB per entry
```

That fit is essentially exact — this is a measurement, not an estimate.

### His table recomputed at our measured rate

| context | his cache | **ours (measured)** | ratio | wifi | 10GbE |
|---|---|---|---|---|---|
| 128k | 5.8 GB | **1.83 GB** | 3.2× | 62 s → **~20 s** | 5 s → **~1.7 s** |
| 500k | 22.5 GB | **7.07 GB** | 3.2× | 4 min → **~75 s** | 20 s → **~6.4 s** |
| 1M | 46.2 GB | **14.5 GB** | 3.2× | 8 min → **~2.6 min** | 42 s → **~13 s** |

**His headline — *"at 500k the cache is 22 GB: 4 minutes on wifi, 20 seconds on wire"* — measures,
on the same model, as ~7 GB: ~75 s on wifi, ~6 s on wire.**

His thesis ("the wire decides the regime") survives and gets *stronger*: at 3.2× cheaper, **wifi
becomes viable at 128k** (~20 s), which in his framing was a wired-only regime.

## 3. Where his number comes from, and the internal inconsistency

His bar says **86 KB/tok**. His own shipping table implies **~44 KB/tok** (5.8 GB ÷ 131,072 =
44.3; 22.5 GB ÷ 512,000 = 43.9; 46.2 GB ÷ 1,048,576 = 44.1 — consistent to 1%). That is exactly
half of 86, and the graphic footnote says **"q8 cache"** — so the bar is fp16 geometry and the
table applies a q8 halving. Explainable, but **the two charts in one graphic are quoted in
different units and neither is labelled**. Anyone reading the bar and doing their own arithmetic
lands 2× off.

Three reasons ours is a further 3.2× below even his q8 figure:

1. **Config-derived geometry over-estimates the artifact.** He states his source: *"kv geometry
   from model configs."* That is a static calculation of K/V tensor width. What DS4 actually
   writes to disk is a **compressed latent**, and the journal tags it `quant=2` — more aggressive
   than his assumed q8.
2. **MLA ≠ MQA.** He labels DeepSeek V4 Flash "MQA · 1 kv head". DeepSeek's attention is **MLA**
   (multi-head *latent* attention), which stores a low-rank latent rather than a 1-head K/V pair.
   "1 kv head" is a fair approximation of the *effective* width, but not of the *stored* object.
   We saw this once already: `t_01ac807e` measured **+0.67 GiB** for a +32k ctx raise against a
   predicted doubling. **MLA compresses harder than config math predicts — twice now.**
3. The rate is a **tunable, not a constant.** If his q8 is a deliberate fidelity choice, our
   smaller number may cost accuracy — which is precisely what his 99%-token-exact gate would
   catch. Nobody should quote a KV/token figure without the quant level attached.

**Second-order finding, ours alone:** the **22.9 MiB fixed header** means short contexts are
pathological to ship — a 563-token entry costs **56.3 KB/token effective**, a 1,046-token entry
36.7, and only at 65k does it approach the 14.1 marginal. **Shipping only pays at long context**,
independently reinforcing his "the interesting regime is 500k+".

## 4. Why we cannot run his experiment

His precondition is *"same GGUF byte-identical on both boxes."*

```
ds4flash.gguf                        86,720,111,488 B  = 86.7 GB
Ryan MBP (M3 Max)  hw.memsize        68,719,476,736 B  = 64.0 GB
```

**The model does not fit on the decode box.** His rig is an **M4 Max 128 GB**; ours is an **M3 Max
64 GB**. This is not a tuning gap, it is 22 GB of missing RAM. No amount of cache shipping helps
when the decoder cannot hold the weights.

Corollaries:
- **Not reproducible on our fleet as specified.** No card. If a small-GGUF lane ever appears
  (a quant that fits 64 GB, or the Phase-D mini at 128 GB), this becomes live — and the
  measurement in §2 is already banked for it.
- His own footnote *"vLLM-NVFP4 to MLX-4bit is impossible · GGUF is the bridge"* is the same
  constraint `SIG-20260808-03` hit from the other side: cross-**model** KV transfer needs identical
  head layout; cross-**box** transfer needs identical weights *and* engine. Both are same-format
  problems.

## 5. What is worth taking

| # | Steal | Rank | State |
|---|---|---|---|
| **S1** | **Our own 13.77 KB/tok + 22.9 MiB/entry**, banked as fleet fact. It sizes cache budgets, shipping, and any future disagg — and it is 3.2× off the number the internet will quote. | **P1** | **measured, this entry** |
| S2 | **Never quote KV/token without the quant level and the measurement method.** Config-derived geometry over-estimated the real artifact by 3.2× here and by ~2× in `t_01ac807e`. | P1 | → `t_6e058ca2` (bench contract) |
| S3 | **Pre-register the correctness gate before the speed claim** — his "99% token-identical vs local prefill" is the right shape, and it is the same discipline `t_6e058ca2` encodes for spec-dec. Adopt the phrasing. | P1 | → `t_6e058ca2` |
| S4 | Prefill-vs-decode asymmetry as a *routing* idea, not a shipping idea: our fleet already splits work across boxes by strength; his framing names why. | P2 | watch |

**Do not:** build cache shipping (precondition fails) · quote his 86 KB/tok or 44 KB/tok for our
DS4 · assume MLA cache scales like config geometry · treat 13.77 KB/tok as quant-independent.

## 6. Provenance caveat on our own number

The 17 journal datapoints are from **PID 3384230, the upstream `antirez/ds4` b0309611 build**,
covering 2026-08-09 09:52 → 22:50. `kevin-spark` was cut over to the **Entrpi fork v0.5.6.1** at
22:53 that night (see the separate finding on `t_43e997d2` / `t_d1947f46`). The fork has written
essentially nothing to the journal since, because it runs **outside the systemd unit** and its
stdout is not journaled under `ds4`.

So: **13.77 KB/tok is an upstream-build measurement.** The fork changed the engine, and nobody has
re-measured KV geometry on it. Re-derive before quoting it as current — same rule this entry just
argued for.

---

*Filed 2026-08-10. Post + graphic fetched verbatim via `api.fxtwitter.com`. Every counter-number
measured live and read-only on `kevin-spark`; nothing changed on that box.*
