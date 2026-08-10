# SIG-20260810-01 — Meta Muse Glimmer 30B: a spec-dec drafter you can pull as an Ollama tag

```yaml
id: SIG-20260810-01
date: 2026-08-10
title: "Meta Muse Glimmer 30B (Unsloth) — dense multimodal open model with a shipped DFlash spec-dec drafter"
index_title: "Muse Glimmer 30B + DFlash — spec-dec as a one-command Ollama tag; first local vision candidate; NOT a coder replacement"
index_links: [repo, docs]
source_url: "https://x.com/unslothai/status/2086761998268928157"
canonical_repo: "https://huggingface.co/unsloth/Muse-Glimmer-30B-GGUF"
canonical_docs: "https://unsloth.ai/docs/models/muse-glimmer"
bucket: models
posture: spike
steal_rank: P0
confidence: high              # post RETRIEVED 2026-08-10 via api.fxtwitter.com; subject confirmed (see SIG-20260810-02 §6)
hardware_fit: [spark, mbp]    # NOT caden — smallest quant 10.7 GB vs 8 GB VRAM
stacks_touched: [t1000]
related_plans:
  - "t_716141c4"              # DSpark NEGATIVE-FINAL — this is a second, independent spec-dec route
  - "t_47f30baf"              # CadensPC role — this signal answers it NEGATIVE
  - "B17"                     # Spark inference experiments (Phase C spec-dec)
status: done
distill: none
updated: 2026-08-10
status_note: "CLOSED 2026-08-10 — see §6/§7. ryan-spark (0.31.2): NEGATIVE-FINAL, HTTP 412 manifest-phase gate, whole-model-family, 'may be in pre-release,' zero bytes transferred, box/120b unaffected — revisit when Ollama lifts the gate. Ryan's MBP (upgraded 0.23.0→0.32.7): pulls/loads clean, real dflash speculation confirmed via native Ollama telemetry (60-74% acceptance) but MEASURED NET SLOWER (~10-28%) than plain decode — dflash tag removed. Vision smoke test PASSED (first working local vision model on the fleet). Plain nvfp4 tag (19GB) kept on the MBP for vision only, not throughput (12-18 tok/s, far below both Mac-tier leaders) — Ryan's call if he wants it gone."
```

## 1. Claim

Unsloth shipped GGUF + Ollama builds of **Meta Muse Glimmer 30B** — per Unsloth's changelog,
*"the first open model from Meta Superintelligence Labs"*, a **dense 30B** Apache-2.0 model for
**local agentic and coding workflows**, with **vision**, controllable reasoning effort, and a
**DFlash speculative-decoding drafter** shipped alongside the weights.

## 2. What we verified

> ✅ **RESOLVED 2026-08-10 (see `SIG-20260810-02` §6).** This entry was originally filed with the
> warning that the X post could not be fetched by any route and the subject was **inferred** from
> Unsloth's changelog — i.e. possibly filed against the wrong link. A working route was found later
> the same day (`api.fxtwitter.com`) and the post was retrieved verbatim. **The inference was
> correct.** UnslothAI, 2026-08-10 10:30 UTC, 1,849♥ / 218RT:
>
> > *"Meta releases Muse Glimmer, a new 30B open model that runs on 18GB RAM. Muse Glimmer is
> > Apache 2.0 licensed, supports vision and is the strongest agentic model for its size. Run and
> > train the model via Unsloth."* — links to the HF GGUF repo and the Unsloth guide.
>
> Confidence raised **medium → high**. One precision note: **the post itself never mentions
> DFlash.** The drafter facts below come from the HF card + Ollama library tags, which are
> independent primary sources — but do not attribute the drafter claim to Unsloth's post.

Everything below **was** read directly from Unsloth docs, the HF model card, and the Ollama library.

| Fact | Value | Source |
|---|---|---|
| Params / arch | **~29.6B, dense** causal transformer + **~1.8B ViT-G/14** perception encoder | HF card |
| Modality | **Text + vision** (`--mmproj mmproj-BF16.gguf`) | Unsloth docs |
| Context | **131,072**, extendable to **262,144**; 2,048 sliding window on local-attn layers | HF card + docs |
| License | **Apache 2.0** | HF card |
| Reasoning effort | controllable: **low / medium / high / xhigh** | Unsloth docs |
| Sampling | Meta defaults `temp 1.0 · top_p 0.95 · top_k 64` | Unsloth docs |
| Quant claim | Unsloth Dynamic 2.0, **"0.2% degradation"** vs full precision | HF card — **claimed** |
| **DFlash drafter** | **3.1× on RTX 5090 · 1.5× M4 Max · 1.8× M5 Max** | HF card — **claimed** |
| Agentic | card claims support for *"OpenClaw, **Hermes Agent**, and other agentic orchestration patterns"* | HF card |

**Unsloth's own sizing table names our hardware.** 4-bit `UD-Q4_K_XL` ≈ **17 GB → "Mac 32GB"**;
8-bit `UD-Q8_K_XL` ≈ **34 GB → "Mac 128GB, DGX Spark"**.

### The part that makes this actionable — it's already an Ollama tag

`ollama.com/library/muse-glimmer` is live, and **the drafter ships as its own tag suffix**:

| Tag | Size | Paired `-dflash` | Size | Δ |
|---|---|---|---|---|
| `30b-nvfp4` | 19 GB | **`30b-nvfp4-dflash`** | **21 GB** | +2 GB |
| `30b-q8_0` | 31 GB | **`30b-q8_0-dflash`** | **33 GB** | +2 GB |
| `30b-mxfp8` | 33 GB | `30b-mxfp8-dflash` | 35 GB | +2 GB |
| `30b-bf16` | 57 GB | `30b-bf16-dflash` | 59 GB | +2 GB |
| `30b-mlx` (Apple) | 21 GB | `30b-mlx-bf16-dflash` | 65 GB | — |
| `30b-q4_…` | 18 / 20 GB | **none** | — | — |

Two things fall out: the drafter costs **+2 GB**, and **there is no `q4` dflash** — speculation is
only offered at ≥ nvfp4/q8 precision.

## 3. Why this matters to us specifically

**a) It is a second, independent spec-dec route — and the only one we can measure without asking anyone.**
`t_716141c4` closed **NEGATIVE-FINAL** yesterday: upstream DS4 `dspark` is **Metal-only** (159
metal-tagged lines, 0 cuda), A/B 16.23 vs 16.39 = noise. We concluded the Entrpi fork was *the only
spec-dec route on GB10* — true **for DS4**, but it left the general question unanswered: *does
speculative decoding help at all on GB10?* `30b-nvfp4` vs `30b-nvfp4-dflash` is that experiment,
one variable, on **Ryan's own box**, no fork, no Kevin, no restart, no service change.

**NVFP4 is Blackwell-native and GB10 is Blackwell** — so the 19 GB nvfp4 pair is the natural Spark
candidate. Unverified: whether **Ollama 0.31.2** on Ryan-Spark can consume `nvfp4`/`dflash` tags at
all. That's the first thing the spike finds out, and it's a `pull` away.

**b) First plausible local vision model on the fleet.** Verified live just now — Ryan-Spark, Kevin,
and the MBP hold **zero** vision-capable models between them (`nomic-embed-text` is text embedding).
Every screenshot Ryan drops in chat routes to a non-local aux model. Q4 at ~17 GB fits the MBP and
Spark with room to spare.

**c) It is NOT a coder-lane replacement — and I want that on the record before anyone benches it.**
`qwen3-coder:30b` is **A3B — ~3B active params per token**. Muse Glimmer is **dense ~29.6B**, so
roughly **10× the FLOPs per token**. Expect materially slower decode at equal quant. Our measured
coder baseline is **86.7 tok/s decode / 3.2 s wall** on a 256-token smoke; a dense 30B will not
approach that. *This is an architectural inference from the model card, not a measurement.* The
DFlash 3.1× is the counterweight, and measuring exactly that tension is the point of the spike.

**d) Caden's PC: this is a clean NO.** Smallest quant on offer is **UD-IQ2_XXS at 10.7 GB** against
an **RTX 4060 / 8 GB**. Even 2-bit doesn't fit in VRAM. `t_47f30baf` ("what should live on Cadens")
gets a negative data point, not a candidate.

**e) `xhigh` walks straight into a bug we already logged.** Muse Glimmer exposes `xhigh` reasoning
effort; our own note reads *"Ollama xhigh: CustomProfile omit/clamp (t1000#40)"*. If we pull this
into Ollama and drive it at `xhigh`, that's the known path. Use `medium` for the A/B and hold effort
constant anyway — one variable.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Spec-dec shipped as a pull-able tag, not a build flag** — `model:quant-dflash` beside `model:quant` | Run the one-variable A/B on Ryan-Spark: `30b-nvfp4` vs `30b-nvfp4-dflash`, identical prompt, report **tok/s + tokens/step + accept %** | **P0** | open |
| S2 | **Drafter co-shipped with weights** beats "find a compatible drafter" | When evaluating any future local model, check for a first-party drafter before assuming spec-dec is unavailable | P1 | open |
| S3 | **Vendor sizing tables that name real boxes** ("Mac 32GB", "DGX Spark") | Steal the format for our own model-desk doc — quant → RAM → *which of our four boxes* | P2 | open |

**Primary steal (one only): S1.**

## 5. Do not

- **Do not** let this near the coder lane on vibes. `qwen3-coder:30b` is measured (20/20 goldens,
  p50 7.31 s); dense-30B is a different tradeoff and has to earn it on the same goldens.
- **Do not** pull `bf16`/`mlx-bf16-dflash` (57–65 GB) — Ryan-Spark currently has ~63 GB free and
  `gpt-oss:120b` is already cold; a 65 GB pull evicts the fleet again.
- **Do not** pull anything onto **Kevin's box** — DS4 holds ~105 GiB in CUDA unified memory and the
  admission gate requires an **empty Ollama**. An Ollama pull there is a service-outage risk.
- **Do not** re-open `t_716141c4`. Upstream DSpark stays NEGATIVE-FINAL; this is a *different model*
  and does not unblock DS4.
- **Do not** read the 3.1× as a GB10 number. It is **RTX 5090** — same Blackwell generation, but
  different silicon, different memory system, unmeasured here.
- **Do not** assume the MBP can run these tags — it is on **Ollama 0.23.0**, ~9 minors behind.

## 6. Next action (mechanical)

- [x] add/update STEALS.md rollup (S1 as P0)
- [x] kanban comment `t_716141c4` — second spec-dec route exists and is measurable without Kevin
- [x] card the A/B — **`t_e28b2c0e`** (mesh, created by ryan-desk-fable 2026-08-10 10:35); Ryan gave the word the same day ("card it", ryan-claude K2 session) — go signal recorded as a comment on the card

## 7. Result (2026-08-10)

**ryan-spark (0.31.2): NEGATIVE-FINAL, per spec.** `ollama pull muse-glimmer:30b-nvfp4` and
`:30b-q8_0` both hit HTTP 412 at the manifest phase — zero bytes transferred, whole-model-family
gate (not nvfp4-specific), error text: *"requires a newer version of Ollama that may be in
pre-release."* Did not upgrade spark's Ollama to force it through — that box serves the production
120b judge lane, and an engine-version bump deserves the same battery+rollback discipline the DS4
and 120b engine swaps got, not a side effect of a spike. Box verified untouched: 120b resident
65GB/100% GPU/Forever, 51GB available, no stray blobs.

**Ryan's MBP (upgraded 0.23.0 → 0.32.7 via brew): full A/B ran.** Both tags pulled and loaded
clean. A/B (temp 0, `reasoning_effort=medium`, 256 tok, ISO-dates bench prompt, 3 runs each):

| Arm | Run 1 | Run 2 | Run 3 | Avg |
|---|---|---|---|---|
| baseline (no drafter) | 18.1 | 14.7 | 12.3 | **15.0 tok/s** |
| dflash (drafter on) | 7.9 | 11.9 | 12.5 | **10.8 tok/s** |

The drafter genuinely engaged — native Ollama `speculate_stats` logged real acceptance (60–74%,
avg_draft 1.0–1.7, max_draft up to 4, comparable to DSpark's 72–73% on DS4) — but decode came out
**~28% slower** overall, and still **~10% slower** even excluding run 1's likely cold-start/draft-load
cost (runs 2–3 only: 13.5 vs 12.2). **Verdict: dflash REJECTED on this pairing/hardware.** Same shape
as the 120b/EAGLE3 finding — decent acceptance does not guarantee a net win once draft+verify
overhead is counted, this time on Apple Silicon unified memory rather than CUDA. Removed the tag.

**Vision smoke test: PASS.** A synthetic test image (blue rectangle + red circle) was captioned
correctly and specifically: *"a solid blue rectangular shape on the left and a solid red
oval/circular shape on the right."* This is the fleet's first working local vision model.

**Text/code throughput, for the record: 12–18 tok/s** — well below both Mac-tier leaders
(qwen3.6 quality-king 31.2, qwen3-coder speed-king 71.1), confirming §3(c)'s architectural
prediction. **Not** proposed for the coder lane — per §5's own "do not," that would need to earn
the coder goldens on its own merits, out of scope here.

**Disposition:** dflash tag removed (unambiguous). Plain `nvfp4` (19GB) **kept** on the MBP —
not for throughput, but as the only local vision option on the fleet; 19GB is cheap on a
438GB-free Mac and there's no confirmed near-term vision use case yet, so this is a soft call,
Ryan's to reverse.

**Unrelated finding, surfaced while restoring the server for testing:** the MBP's brew-services
`homebrew.mxcl.ollama` launchd agent reports "started" but does not actually bind the port — this
predates this session's work. Worked around with a manually-launched server (same binary/flags
brew's own caveat recommends); the launchd agent itself still needs a real fix.

## 8. Chat blurb

`SIG-20260810-01` · `models` · **spike P0** — Meta Muse Glimmer 30B (Apache-2.0, dense ~29.6B +
vision, 131k ctx). **The X post was not fetchable** (402 / x.com abuse-block / dead mirrors);
subject inferred from Unsloth's 08-10 changelog. Real find: **DFlash spec-dec ships as an Ollama tag**
(`30b-nvfp4-dflash`, +2 GB) — a one-variable A/B on Ryan's Spark that answers "does spec-dec work on
GB10 at all", which DSpark's Metal-only dead end left open. Also the fleet's **first local vision
candidate** (zero today). **Not** a `qwen3-coder:30b` replacement — dense ≈10× FLOPs/token vs A3B.
**No** for Caden (10.7 GB min vs 8 GB VRAM).
