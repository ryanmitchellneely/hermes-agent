# SIG-20260810-01 — Meta Muse Glimmer 30B: a spec-dec drafter you can pull as an Ollama tag

```yaml
id: SIG-20260810-01
date: 2026-08-10
title: "Meta Muse Glimmer 30B (Unsloth) — dense multimodal open model with a shipped DFlash spec-dec drafter"
index_title: "Muse Glimmer 30B + DFlash — spec-dec as a one-command Ollama tag; first local vision candidate; NOT a coder replacement"
index_links: [repo, docs]
source_url: "https://x.com/unslothai/status/2086761998268928157"
source_url_2: "https://x.com/analogalok/status/2086834522461806748"   # RTX 4090 llama.cpp bench — contradicts our result, see §9
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
status: open
distill: none
updated: 2026-08-10
reopened: 2026-08-10   # see §9 — an independent bench gets +50% decode from the SAME drafter on a config we can now run
status_note: "REOPENED 2026-08-10 (§9): an independent RTX 4090 bench (analogalok) gets 50->75 tok/s decode (+50%) from the SAME DFlash drafter, via llama.cpp `--spec-type draft-dflash --spec-draft-n-max 3` — the opposite sign to our -32%. Our arm ran Ollama/Metal on the MBP with NO ability to set n_max (Ollama exposes no spec knobs); his ran CUDA llama.cpp with n_max=3. VERIFIED LIVE: ryan-spark already has ~/llama.cpp built with CUDA at commit 62bf73d = 'model: Muse Glimmer Support (#26841)', and its llama-server advertises draft-dflash + draft-dspark + 4 ngram-* types, n_max default 3. The experiment is reproducible on our own box, bypassing the HTTP 412 manifest gate entirely — needs only the GGUF download. Prior text preserved below and still true FOR ITS CONFIGURATION. // CLOSED 2026-08-10 — see §6/§7. ryan-spark (0.31.2): NEGATIVE-FINAL, HTTP 412 manifest-phase gate, whole-model-family, 'may be in pre-release,' zero bytes transferred, box/120b unaffected — revisit when Ollama lifts the gate. Ryan's MBP (upgraded 0.23.0→0.32.7): pulls/loads clean. First A/B pass had a real methodology bug (wall-clock timing + reasoning silently eating the token budget) that Ryan caught by cross-checking against published community numbers — CORRECTED via native eval_count/eval_duration + think:false: baseline 20.7 tok/s (not 15.0), dflash 14.0 tok/s post-warmup (not 10.8), still net negative but the drafter barely fires for code at all (near-zero draft attempts vs 60-74% acceptance in the reasoning-heavy run) — the slowdown is a structural dual-model tax, not overhead-vs-benefit. Vision smoke test PASSED. Plain nvfp4 tag kept on the MBP for vision only — Ryan's call if he wants it gone."
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

**Ryan's MBP (upgraded 0.23.0 → 0.32.7 via brew): full A/B ran, then corrected.** Both tags
pulled and loaded clean. First pass used wall-clock timing around the OpenAI-compat endpoint with
`reasoning_effort=medium` — **Ryan flagged the numbers looked low against published community
figures, and he was right.** Two real methodology flaws: (1) wall-clock around the whole HTTP call
instead of Ollama's native `eval_count`/`eval_duration` (decode-only — the convention every other
bench this session used); (2) `reasoning_effort=medium` let the model burn the *entire* 256-token
budget on invisible chain-of-thought in some runs (confirmed directly: an unscoped call returned
`response=""` with all 256 tokens consumed by thinking, nothing visible produced).

**Redone properly**: native `/api/generate`, `eval_count`/`eval_duration`, `think:false` (forces
real code output), temp 0, 3 runs each, model already warm (`load_duration` ~0.04s, ruling out a
cold-start artifact):

| Arm | Run 1 | Run 2 | Run 3 | Avg |
|---|---|---|---|---|
| baseline (no drafter) | 20.9 | 20.8 | 20.4 | **20.7 tok/s** |
| dflash (drafter on) | 13.0* | 13.7 | 14.3 | **14.0 tok/s** (runs 2–3) |

\* run 1 folds in the model-swap cost (6.4s `load_duration` reported, but first-call decode is
still visibly slower than runs 2–3 — some load spillover into the decode timer itself).

**The corrected numbers changed the *mechanism*, not the verdict.** With `think:false`, the
drafter barely fires for code at all: `speculate_stats` shows run 1 `iterations=251 drafted=7
accepted=5`, runs 2–3 `iterations=255 drafted=1 accepted=1` — essentially opting out. Compare the
original reasoning-heavy run: `iterations=126–157 drafted=147–218`, 60–74% acceptance, hundreds of
real draft attempts. **The drafter is evidently tuned for predictable reasoning/filler tokens, not
code** — for actual code generation it does almost nothing. And yet decode is *still* ~32% slower
than baseline (14.0 vs 20.7) with next-to-zero real speculation happening. This is not "decent
acceptance, overhead still loses" (true only for the reasoning workload) — it's **a structural
throughput tax the dflash tag carries on code content regardless of whether the drafter does
anything useful.** Verdict unchanged: dflash rejected, tag removed. But 20.7 tok/s — not 15.0 —
is the honest baseline number for what this model does on the MBP with real code output.

**Vision smoke test: PASS.** A synthetic test image (blue rectangle + red circle) was captioned
correctly and specifically: *"a solid blue rectangular shape on the left and a solid red
oval/circular shape on the right."* This is the fleet's first working local vision model.

**Text/code throughput, corrected: ~20.7 tok/s** — still below both Mac-tier leaders (qwen3.6
quality-king 31.2, qwen3-coder speed-king 71.1), confirming §3(c)'s architectural prediction, but
meaningfully better than the original flawed reading. **Not** proposed for the coder lane — per
§5's own "do not," that would need to earn the coder goldens on its own merits, out of scope here.
Open question this correction surfaces but does not answer: whether 20.7 tok/s is close to this
model's real ceiling on Apple Silicon, or whether Ollama/GGUF's Metal backend is itself leaving
throughput on the table against a native path (MLX ships its own `30b-mlx` tag at the same 21GB —
untested here, a candidate follow-up if the vision capability sees real use).

**MLX follow-up, same day (per Ryan's ask, and a live worked example of the new
`model-bench-preflight.md` doctrine catching a wrong read before it shipped):**

Ollama's `muse-glimmer:30b-mlx` tag is **not real MLX** — verified same model ID (`ef32a55b4976`)
as `30b-nvfp4-dflash`, an alias to the identical GGUF blob. Real MLX execution needs Apple's own
toolchain, entirely separate from Ollama. Found genuine weights at
`mlx-community/Muse-Glimmer-30B-4bit` (ungated, real safetensors, verified before downloading).

`mlx_lm` rejected it (`model_type muse_glimmer not supported`) — wrong tool, this is a
vision-language model; the repo's own README named `mlx-vlm` as correct. `mlx-vlm` rejected it too,
on a more precise error: `No module named mlx_vlm.speculative.drafters.muse_glimmer` — fired even
with no `--draft-model` flag passed, meaning Muse Glimmer's config self-declares its paired drafter
and `mlx-vlm`'s model registry needs that submodule to exist just to recognize the base
architecture at all. Checked for a version gate before concluding incompatible: PyPI-stable
`mlx-vlm` is **0.6.10** (confirmed current PyPI latest); the mlx-community conversion README says
it used **0.6.12**. Installed straight from GitHub main — landed on **0.6.11**, still one point
short. **Genuine, precisely-diagnosed software lag** (model launched today; the tooling hasn't
caught up across *two separate ecosystems* now — Ollama on ryan-spark, `mlx-vlm` on the Mac), not
a hardware or model-quality finding. Did not attempt to patch/stub the missing module — that's
writing code for someone else's library, out of scope for a bench spike. Cleaned up the 21GB
download. **Revisit trigger: check again once `mlx-vlm` ships ≥0.6.12 publicly.** Until then the
corrected GGUF/Ollama number (20.7 tok/s, decode-only, real code output) stands as the best
measured figure on this hardware.

**RESOLVED same day (Fable, on Ryan's "take a look and fix this"):** the missing 0.6.12 was
findable — **mlx-vlm PR #1838 "Add Muse Glimmer model support"**, open/unmerged, authored by the
repo owner himself (purely additive, 9 files, +1337; due-diligence checked before installing).
`pip install git+...@refs/pull/1838/head` → 0.6.12, model loads and generates under real MLX.

**MLX measured (python API, native `generation_tps`, temp 0, 256 tok, 3 runs, single load):
12.3 / 12.8 / 13.1 → avg 12.7 tok/s** (prompt ~80 tps). **Real MLX is ~40% *slower* than
Ollama/GGUF-Metal (20.7) for this model today** — the "native path must be faster on Apple
Silicon" prior fails for a launch-day model riding an hours-old support PR. Condition caveat: this
conversion's chat template **hard-pins "Reasoning strength: high"** (`thinking_mode=disabled`,
`reasoning_effort=none`, and plain all render identically), so MLX ran reasoning-mode — but 12.7
also loses to Ollama's reasoning-mode figures (~15–18), so the verdict is robust to the mismatch.
Output verified code-like in all runs despite the reasoning channel.

**Standing:** Ollama `nvfp4` (20.7 tok/s + working vision) is the serving path for this model on
the MBP. MLX weights removed (reproducible); `mlx-vlm` left at the PR build. **Revisit after
PR #1838 + #1839 merge and a re-converted repo** (the current conversion may predate #1839's
embed_norm quant fix; launch-day MLX conversions typically improve). This full arc — alias-tag
catch → wrong-toolkit catch → version-gate catch → PR-source fix → honest negative — is the worked
example `model-bench-preflight.md` exists for.

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

---

## 9. Contradiction: an independent bench gets **+50%** from the same drafter (2026-08-10)

[@analogalok](https://x.com/analogalok/status/2086834522461806748) (Alok, 2026-08-10 15:18Z,
70♥ / 5RT / 8,140 views, video attached) benched Muse Glimmer on a **single RTX 4090** using
**llama.cpp built from source (Ubuntu 22, CUDA 13)** — not Ollama. Verbatim commands and results:

```bash
# arm A — no speculation
./build/bin/llama-server -m Muse-Glimmer-30B-UD-Q4_K_XL.gguf \
  -c 130000 -b 4096 -ub 4096 -ngl 99 --port 8080
#   prefill 3134.95 t/s · decode 50.00 t/s · VRAM 19.34 GB

# arm B — DFlash drafter
./build/bin/llama-server -m Muse-Glimmer-30B-UD-Q4_K_XL.gguf \
  -md dflash-kquant.gguf --spec-type draft-dflash --spec-draft-n-max 3 \
  -c 80000 -b 4096 -ub 4096 -ngl 99 --port 8080
#   prefill 1293.69 t/s · decode 75.00 t/s · VRAM 23.93 GB  (dflash gguf +1.6 GB)
```

**Decode 50 → 75 tok/s = +50%.** Ours was **20.7 → 14.0 = −32%.** Same model, same drafter,
opposite sign. One of the two is a configuration artifact, and the asymmetry says which is more
likely:

| | ours (§7) | his |
|---|---|---|
| Engine | **Ollama 0.32.7** (GGUF/Metal) | **llama.cpp from source**, CUDA 13 |
| Silicon | M3 Max, unified memory | RTX 4090, 24 GB VRAM |
| Quant | `nvfp4` (19 GB tag) | `UD-Q4_K_XL` |
| Drafter wiring | opaque `-dflash` **tag** | explicit `-md dflash-kquant.gguf --spec-type draft-dflash` |
| **`n_max`** | **not settable — Ollama exposes no spec knobs** | **3** |
| Batch | engine default | `-b 4096 -ub 4096` |
| Content | code (`think:false`) | unstated; his decode figure is whole-run |

He also pays the expected spec-dec tax on the other axis — **prefill halves, 3135 → 1294 t/s** —
which is a coherent, textbook tradeoff signature and mild evidence the drafter is genuinely
engaging on his stack. Our run showed the drafter *opting out* (`drafted=1` of 255 iterations) yet
still losing 32%, which we called a "structural dual-model tax."

> ⚠️ **Do not over-read the engine as the cause.** The tempting conclusion — *"the tax is an
> Ollama artifact; llama.cpp's explicit wiring fixes it"* — **is not supported**, because
> **llama.cpp lost too.** `t_227d09b2` ran `--spec-type draft-eagle3` on **this exact build**
> (`62bf73d`, CUDA, ryan-spark) and got **11.7–14.2% acceptance → 23.3 tok/s vs 49.8–50.3 plain =
> 2× SLOWER**. Different model (gpt-oss-120b) and different drafter (EAGLE3), so it is not a
> direct refutation — but it kills "the engine was the problem" as a clean story. **Six variables
> differ between our arm and his; the engine is one candidate, not the identified cause.**
>
> The variable with the strongest prior is **`n_max`**, because it is the one we *know* we set
> wrong: the EAGLE3 run used **16** against a measured mean accept length of **2.8–3.2**, and
> `t_227d09b2`'s own parked-revisit note says so verbatim (*"mean accept ~3 says 16 wastes 13"*).
> **llama.cpp's default is 3. analogalok used 3. We used 16.** That is the cheapest hypothesis on
> the table and it is exactly what `t_99c6388b` was already created to test.

### The part that makes this actionable — the rig is already on ryan-spark

Verified live, read-only:

```
~/llama.cpp   62bf73d  2026-08-10  "model: Muse Glimmer Support (#26841)"
              version 374, built with GNU 13.3.0 for Linux aarch64
build/bin/llama-server   built 2026-08-10 06:13
libggml-cuda.so.0.19.0   built 2026-08-10 06:13     <- CUDA backend compiled
src/models/muse-glimmer.cpp                          <- model support in-tree
```

`llama-server --help` advertises, authoritatively:

```
--spec-type   none, draft-simple, draft-eagle3, draft-mtp, draft-dflash,
              draft-dspark, ngram-simple, ngram-map-k, ngram-map-k4v,
              ngram-mod, ngram-cache
--spec-draft-n-max N     (default: 3)
--spec-draft-n-min N     (default: 0)
```

Three consequences:

1. **`draft-dflash` is directly runnable on GB10 today.** The `t_e28b2c0e` blocker was Ollama's
   **HTTP 412 manifest gate** on ryan-spark — that gate is an *Ollama registry* problem and
   llama.cpp does not touch it. Only the GGUF download stands between us and his exact arm B.
   Box has **44 GB available, 3.3 TB free disk**; `UD-Q4_K_XL` ≈ 17 GB + dflash 1.6 GB.
   **It also fits the already-ratified architecture** — Ryan confirmed **Option 1** on
   `t_227d09b2` at 09:59: Ollama keeps `:11434` residency and the Juice/teacher contract, while
   **llama.cpp+MXFP4 is the window/batch engine for `/v1` consumers**. A Muse Glimmer bench is
   exactly that surface, so it needs no production-lane change and no re-litigation of the split.

   **Any window inherits `t_227d09b2`'s hard rules, non-negotiable** — they were written after an
   EAGLE3 bench *wedged ryan-spark badly enough that sshd died and Ryan had to power-cycle it*:
   pause **consumers**, not just the model (stop the Ollama service or down the tunnel — parking
   the model does not stop a VPS request re-triggering a 65 GB reload mid-load); memory admission
   gate before serve; hard abort if `MemAvailable` dips below the serve requirement mid-load; and
   **never `pkill -f llama-server`** — it matches Ollama's own bundled runner at
   `/usr/local/lib/ollama/llama-server` and will kill the warm 120b.
2. **`n_max` default is 3** — exactly his value, and 5× below the **16** we used for the EAGLE3
   run. That is independent corroboration of `t_99c6388b`'s thesis that our EAGLE3 rejection was
   a misconfiguration, from a completely unrelated source.
3. **`draft-dspark` exists in a CUDA-built binary.** `t_716141c4` closed DSpark NEGATIVE-FINAL on
   the evidence that it is Metal-only with 0 CUDA lines — that was measured in **antirez/ds4**,
   a different codebase. Upstream llama.cpp ships a CUDA-capable `draft-dspark`. **Do not reopen
   `t_716141c4`** (its finding about DS4 stands), but the general claim "dspark is Metal-only"
   must not be carried over to llama.cpp.

### Other claims from the post, unverified by us

- **19.34 GB VRAM at 130k ctx with unquantized f16 KV**, attributed to **16:1 GQA**. He contrasts
  Gemma 4 31B, which he says needs Q4 KV quant to reach 140k and only ~40k with f16 on 24 GB.
  Plausible and consistent with the HF card's 131k claim, but a vendor-adjacent enthusiast number.
- **76% SWE-Bench Verified.** Not in Unsloth's post; treat as unsourced until the model card or
  Meta says it.
- Quoted tweet frames it as *"distilled from Muse Spark"*, with Muse Spark 1.2 weights "gearing
  up." Roadmap chatter, not a fact.

**Caden verdict is unchanged and if anything firmer** — his whole framing is "dominate 24 GB
consumer cards." Caden's RTX 4060 has **8 GB**. Still a clean NO.

### Revised steal

| # | Steal | Rank | State |
|---|---|---|---|
| **S1′** | **Re-run the DFlash A/B on ryan-spark under llama.cpp** (`--spec-type draft-dflash --spec-draft-n-max 3`), not Ollama. One variable vs his published pair. This converts our −32% from a verdict into a *configuration* datapoint. | **P0** | → folded into `t_99c6388b` |
| **S2′** | **Never bench spec-dec through an engine that hides `n_max`.** Ollama's `-dflash` tag is a black box; the two published wins on this drafter both set `n_max` explicitly. Add to the bench contract. | **P1** | → `t_6e058ca2` |
| ~~S3′~~ | ~~llama.cpp is a third engine path~~ — **already known, not my find.** `t_227d09b2` landed llama.cpp `62bf73d` on ryan-spark at **09:59**, and `SIG-20260810-02` was corrected at **11:30** by an earlier session, which marked its own vLLM-is-the-prerequisite claim superseded. Recorded here only so this entry does not re-assert the stale framing. | — | already corrected elsewhere |

**Do not:** quote his 50/75 as a GB10 number (RTX 4090, different memory system) · pull
muse-glimmer through Ollama on ryan-spark (still 412-gated; llama.cpp is the route) · load
anything on ryan-spark without checking the 120b's residency first · treat +50% as replicated
until we run it.

*Filed 2026-08-10. Post fetched verbatim via `api.fxtwitter.com`. All llama.cpp facts read
read-only off `spark`; nothing built, downloaded, or changed on that box.*
