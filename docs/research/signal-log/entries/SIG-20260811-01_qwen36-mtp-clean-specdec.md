# SIG-20260811-01 — A zero-measurement influencer listicle whose one testable line turns out to hand us the clean spec-dec datapoint we've been unable to produce

```yaml
id: SIG-20260811-01
date: 2026-08-11
title: "Alex Finn 'EVERY AI tool you need in August 2026' listicle — the only fleet-relevant line is 'Local model: Qwen 3.6 27b on DGX Spark'. Verifying it surfaced that Qwen3.6 ships a trained MTP head, declares general.architecture=qwen35 (already supported by our llama.cpp build), and that llama.cpp's draft-mtp path is structurally immune to BOTH config bugs that produced our EAGLE3 rejection"
index_title: "Finn listicle = noise (0 measurements, 465k-follower tool roundup). But verifying its one testable line ('Qwen 3.6 27b on DGX Spark') found the clean spec-dec arm: Qwen3.6 GGUF declares arch=qwen35 (LOADS ON OUR EXISTING 62bf73d BUILD, no rebuild), ships a trained MTP head, and llama.cpp auto-resolves the matched sidecar AND auto-clamps n_max — the two exact bugs that killed t_227d09b2's EAGLE3 run. Honest ceiling: nextn_predict_layers=1 means n_max clamps to 1, so <2x, not 2.9x"
source_url: "https://x.com/alexfinn/status/2087025097546809533"
canonical_repo: ""
canonical_docs: "https://huggingface.co/unsloth/Qwen3.6-27B-MTP-GGUF"
index_links: [HF]
bucket: models
posture: steal
steal_rank: P1
confidence: high          # post fetched verbatim via fxtwitter; every model/arch/flag claim measured live off ollama registry, HF API, a GGUF header range-read, and llama.cpp source on ryan-spark
hardware_fit: [spark, mbp]
stacks_touched: [t1000]
related_plans:
  - "t_99c6388b"          # clean spec-dec sweep — where the MTP arm belongs
  - "t_227d09b2"          # EAGLE3 rejection (quantized draft + oversized n_max) — the confound MTP cannot reproduce
  - "t_e28b2c0e"          # DFlash -32% (wrong drafter for the workload)
  - "t_716141c4"          # DSpark Metal-only NEGATIVE-FINAL
  - "t_6e058ca2"          # bench provenance contract
  - "t_bf8fae81"          # fleet model ladder
  - "SIG-20260810-03"     # Arc B70 — draft-head quantization as a failure class
  - "SIG-20260810-01"     # Muse Glimmer / DFlash
status: carded
status_note: "**The link is noise; the verification is the signal.** Finn's post carries zero measurements and no repo — a 465k-follower tool roundup. Its one fleet-relevant line ('Local model: Qwen 3.6 27b on DGX Spark') checks out and leads somewhere useful. VERIFIED, no download: a range-read of the unsloth GGUF header declares `general.architecture=qwen35`, `nextn_predict_layers=1`, `context_length=262144` — so Qwen3.6-27B loads on the llama.cpp `62bf73d` ALREADY on ryan-spark (LLM_ARCH_QWEN35 is in src/llama-model.cpp:307), no rebuild. VERIFIED in source: `--spec-type draft-mtp` auto-downloads the matched MTP sidecar (arg.cpp:393) and auto-clamps `params.n_max = min(n_max, n_mtp_layers)` (speculative.cpp:1353) — the two exact misconfigurations that produced t_227d09b2's 11.7-14.2% acceptance CANNOT be reproduced on this path. HONEST CEILING: `nextn_predict_layers=1` means n_max clamps to 1, so max 2 tokens/step (<2x), not the 2.9-3.1 that multi-head/tree methods claim. **CARDED `t_76235b2a`** (blocked, `needs_input`) 2026-08-11 — Ryan chose a separate card over folding it in as Arm D on `t_99c6388b`, because it changes the target model and so carries a second gate (~10-20 GB download OK) that Arms A/B do not. Phase 0 (resolve the auto-picked sidecar via the HF API) is free and releasable alone."
distill: none
```

## 1. Claim

[@AlexFinn](https://x.com/AlexFinn/status/2087025097546809533) (465,691 followers; 251 likes / 21,101
views at read time) posts *"Here is EVERY AI tool you need to be using in August 2026 … I've personally
used each for 100+"* — a seven-bullet roundup with a video. Verbatim bullets:

| Category | His pick |
|---|---|
| Best planning model | **Fable 5 medium** |
| Best execution model | ChatGPT 5.6 sol medium |
| Best AI tool | ChatGPT Voice |
| Best AI agent harness | ChatGPT Desktop app |
| Best model for UI/UX/games | **Claude Code w/ Claude Opus 5** |
| **Local model** | **Qwen 3.6 27b on DGX Spark — "best speed and intelligence ratio in local AI"** |
| Other must-have | Buzz (Jack Dorsey) |

**No benchmarks, no repo, no configs, no hardware detail.** Six of seven bullets are subscription
recommendations. Exactly one line touches our fleet, and it names our hardware.

## 2. What we verified

All of the following was measured/read live — **nothing downloaded, nothing installed, nothing restarted.**

### The model exists, and there are two of it

Ollama registry manifests (`registry.ollama.ai/v2/library/qwen3.6/manifests/<tag>`):

| tag | size | note |
|---|---|---|
| `qwen3.6:27b` | **17.4 GB** | the one Finn names — dense |
| `qwen3.6:35b` | **23.9 GB** | MoE A3B |
| `qwen3.6:latest` | 23.9 GB | → 35b is the default |

HF downloads (`/api/models?search=Qwen3.6`): `Qwen/Qwen3.6-27B` **6.58M** · `Qwen/Qwen3.6-35B-A3B`
**5.31M** · **`nvidia/Qwen3.6-35B-A3B-NVFP4` 10.59M** (the single most-downloaded of the family, and
NVFP4 is Blackwell-native = GB10).

**Unsloth ships dedicated MTP repos** — `unsloth/Qwen3.6-27B-MTP-GGUF` (1.15M dl) and
`unsloth/Qwen3.6-35B-A3B-MTP-GGUF` (0.48M), 26 GGUF files each, smallest useful quants
**9.6–11.9 GB**, plus `mmproj-*` (so the family is vision-capable).

### The GGUF header — read without downloading the file

HTTP `Range: bytes=0-3000000` against `Qwen3.6-27B-UD-IQ2_XXS.gguf`, parsed the GGUF v3 KV block:

```
general.architecture          qwen35        ← the decisive field
general.name                  Qwen3.6-27B
general.size_label            27B
qwen35.block_count            65
qwen35.context_length         262144
qwen35.nextn_predict_layers   1             ← a single trained MTP head
```

**Qwen3.6 declares itself as `qwen35`.** That matters because:

```
src/llama-model.cpp:307   case LLM_ARCH_QWEN35:      return new llama_model_qwen35(params);
src/llama-model.cpp:309   case LLM_ARCH_QWEN35MOE:   return new llama_model_qwen35moe(params);
```

…are already in **`62bf73d`, the build sitting on `spark` since 2026-08-10 06:13**. No rebuild, no
version bump. There is no `LLM_ARCH_QWEN36` and there does not need to be.

### The MTP path is immune to both bugs that killed our EAGLE3 run

`t_227d09b2` rejected spec-dec on **11.7–14.2% acceptance**, running two known-wrong variables:
a **Q8_0 quantized draft head**, and **`--spec-draft-n-max 16`** against a measured mean accept
length of ~3. From `62bf73d` source on the box:

| Our EAGLE3 bug | What `draft-mtp` does |
|---|---|
| hand-picked draft file, wrong quant | `arg.cpp:393` `opts.download_mtp = spec_type_draft_mtp` → **the matched sidecar is auto-resolved and auto-downloaded from the model repo** (`arg.cpp:568-574`); you cannot pick the wrong one |
| `n_max 16` vs accept ~3 | `speculative.cpp:1353` `params.n_max = std::min(params.n_max, n_mtp_layers)` → **auto-clamped to the number of trained heads** |

And the driver comment names our family explicitly:

```
speculative.cpp:1271   //   neither (qwen35 / qwen35moe): a single trained MTP head.
```

Full runtime surface confirmed present: `--spec-type none,draft-simple,draft-eagle3,draft-mtp,
draft-dflash,draft-dspark,ngram-simple,ngram-map-k,ngram-map-k4v,ngram-mod,ngram-cache`, plus the
whole `--spec-draft-*` family and a download-time `--mtp` flag.

### Headroom and what we already run

`spark` (ryan): **44 GB MemAvailable**, 3.3 TB free, `gpt-oss:120b` + `hermes3:8b-16k` pinned
(`KEEP_ALIVE=-1`). Current shelf: `gpt-oss:120b` 65.4 GB · `qwen2.5-coder:32b` +`-64k` 19.9 GB ea ·
**`qwen3-coder:30b` 18.6 GB (30.5B A3B, measured 86.7 tok/s decode / 3.2 s wall)** · `hermes3:8b(-16k)` ·
`qwen3-embedding`.

## 3. Takeaways (max 5)

1. **The post is noise; the verification is the signal.** Zero measurements, zero repos, six of seven
   bullets are subscription picks. Logged for the one line, and the value came from checking it —
   not from anything Finn wrote. He does not mention MTP at all.
2. **The clean spec-dec arm now has a model.** `t_99c6388b` exists because *"we hold zero clean
   datapoints where a well-matched, well-configured drafter with real acceptance failed to pay."*
   A drafter trained jointly with its target by the model authors, auto-matched and auto-clamped by
   the engine, is as well-matched as this gets — and it runs on the build we already have.
3. **⚠️ Honest ceiling: `nextn_predict_layers=1` caps this at 2 tokens/step.** One head → `n_max`
   clamps to 1 → best case 1 drafted + 1 verified. Expected `1 + a` ≈ **1.7× at 70% accept, before
   drafter cost** — real, but not the 2.9–3.1× that multi-head/tree methods advertise. **Do not sell
   this internally as a 3× lever.**
4. **It changes the target model, which is a different question.** Arms A/B of `t_99c6388b` ask
   "does spec-dec pay on *our current models*" using weights already on disk. An MTP arm asks "does
   spec-dec pay on GB10 *at all*, best case" and needs a ~10–20 GB download of a model we don't run.
   Cleaner mechanism answer; doesn't directly speed up `gpt-oss:120b` or DS4 Flash.
5. **`Qwen3.6-35B-A3B` is a separate, larger question** — same A3B MoE shape as our
   `qwen3-coder:30b` workhorse, one generation newer, with an NVFP4 build that is the family's
   most-downloaded artifact and Blackwell-native. That belongs on the fleet ladder (`t_bf8fae81`),
   not on a spec-dec card.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Model-native MTP is the confound-free spec-dec test** — engine auto-matches the sidecar and auto-clamps `n_max`, so neither of our two known bugs can recur | `-hf unsloth/Qwen3.6-27B-MTP-GGUF --spec-type draft-mtp`, same window/engine/prompt set as `t_99c6388b`. Report accept %, tokens/step, net tok/s, prefill, **and the resolved sidecar path + dtype + effective n_max** per `t_6e058ca2` | **P1** | **CARDED `t_76235b2a`** (blocked) — Ryan chose a separate card over Arm D, 2026-08-11 |
| S2 | Newer A3B generation + NVFP4 as a fleet-model candidate | `Qwen3.6-35B-A3B` (23.9 GB) / `nvidia/…-NVFP4` vs incumbent `qwen3-coder:30b` on the ladder — **not** bundled into the spec-dec window | P2 | open |
| S3 | Read GGUF arch/hparams via an HTTP range request before committing to a download | Reusable: 3 MB fetch answered "will this load on our build" and "how many MTP heads" with **zero** GB transferred. Worth folding into the bench provenance contract | P2 | open |

**Primary steal (one only):** **S1**

## 5. Do not

- **Do not treat this list as evidence of anything.** No measurements. Finn's "Fable 5 medium for
  planning" and "Opus 5 for UI" happen to align with the desk's existing lanes (`Fable b4 router`,
  `opus[1m]` via claude-acp) — that is coincidence, not corroboration, and must not be cited as
  external validation of our routing.
- **Do not expect >2×.** Single MTP head. See takeaway 3.
- **Do not `ollama pull qwen3.6:27b` expecting speculative decoding.** Ollama exposes **zero**
  spec-dec surface at any version we run (re-verified through 0.32.7). The pull gets the weights and
  none of the mechanism. The MTP path is llama.cpp-only.
- **Do not route this to Caden.** RTX 4060 / **8 GB** — the smallest useful quant is 9.6 GB. Same
  clean NO as Muse Glimmer (`SIG-20260810-01`).
- **Do not bundle S1 and S2 into one window.** Changing drafter and target model together is exactly
  the confound `t_99c6388b` was written to eliminate.
- **Do not add a fourth arm without a window.** `t_99c6388b` is already blocked on a consumer-paused
  window on `spark`; two cards competing for one window is how the box wedged on 08-10 07:57.

## 6. Next action (mechanical)

- [x] add/update STEALS.md rollup
- [x] regenerate `INDEX.md`
- [x] kanban comment `t_99c6388b` (Arm D proposal + ceiling + provenance requirement)
- [x] **card created `t_76235b2a`** (blocked, `needs_input`) — Ryan said "add this card", 2026-08-11.
      Carded as a **sibling** of `t_99c6388b` rather than a fourth arm on it, because it changes the
      target model and therefore needs a second gate (download OK) that Arms A/B do not.
      Cross-ref comments landed on `t_99c6388b` and `t_227d09b2`. Seed body:
      `~/.t1000/kanban/seed-bodies/lab-qwen36-mtp-specdec.md`
- [ ] AUTOMATION-ROADMAP row — n/a
- [ ] patch skill — n/a

## 7. Chat blurb

Finn's list is noise — zero measurements, six of seven bullets are subscriptions. But the one line
that names our hardware ("Qwen 3.6 27b on DGX Spark") checks out and leads somewhere: Qwen3.6 ships a
trained MTP head, its GGUF declares `general.architecture=qwen35`, and `LLM_ARCH_QWEN35` is already in
the llama.cpp `62bf73d` on `spark` — it loads with no rebuild. Better: `--spec-type draft-mtp`
auto-resolves the matched sidecar and auto-clamps `n_max` to the head count, so **neither of the two
bugs that produced our 11.7–14.2% EAGLE3 rejection can recur on this path.** Ceiling is honest though —
`nextn_predict_layers=1` caps it at 2 tokens/step (<2×), not 2.9×. Proposed as Arm D on `t_99c6388b`,
same window. Not carded.
