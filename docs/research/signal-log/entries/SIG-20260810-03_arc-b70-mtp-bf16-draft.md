# SIG-20260810-03 — Keep the draft head unquantized: the Arc B70 cookbook, and the confound in our own EAGLE3 result

```yaml
id: SIG-20260810-03
date: 2026-08-10
title: "Intel Arc Pro B70 inference cookbook (SergeB) — vLLM XPU MTP spec-dec unlocked by building the draft head WITHOUT the target's quant_config"
index_title: "Draft head must stay unquantized — and OUR EAGLE3 bench ran the Q8_0 draft while the BF16 one sat unused on disk. 12-14% accept is likely an artifact; free retest available"
index_links: [repo, docs]
source_url: "https://x.com/sergiiiobs/status/2086768088553263191"
canonical_repo: "https://github.com/SergiioB/intel-arc-pro-b70-inference-cookbook"
canonical_docs: "https://localmaxxing.com/es/models/Qwen/Qwen3.6-27B"
bucket: inference
posture: steal
steal_rank: P0
confidence: high          # post fetched verbatim; repo tree, patch source, launch script and results md read directly; our own bench config read live off spark
hardware_fit: [spark]     # the STEAL is portable; their tok/s numbers are Intel Arc / SYCL and do NOT transfer
stacks_touched: [t1000]
related_plans:
  - "t_227d09b2"          # 120b engine swap + EAGLE3 REJECTED at 11.7-14.2% accept  <- the result this signal casts doubt on
  - "t_171fbfd2"          # profile card: does spec-dec pay here at all
  - "t_e28b2c0e"          # DFlash/muse-glimmer A/B: 60-74% accept, still net slower
  - "t_716141c4"          # DSpark NEGATIVE-FINAL
  - "t_99c5d345"          # B17 engine phase
  - "SIG-20260810-02"     # OoO-Spec — the "three rejections" tally this entry qualifies
status: carded
status_note: "Primary steal CARDED t_99c6388b (blocked on Ryan). See card body for the full spec + guardrails."
distill: none
```

## 1. Claim

[@SergiiioBS](https://x.com/sergiiiobs/status/2086768088553263191) (SergeB, 117 followers,
2026-08-10 10:54Z, 38♥ / 3.9k views) publishing an **open recipe** for LLM inference on an
**Intel Arc Pro B70 32 GB**. Headline for the dense 27B run:

- decode **21–29 → 69.3 tok/s** (~2.4–3× llama.cpp)
- prefill **936 → 1,750+ tok/s** (~2×)
- exact-128K with MTP4: **47.6 tok/s**
- `w4a8` **discarded on quality** — KL divergence and stacking errors

Three named causes, and the first is the one that matters to us:

> *"MTP speculative decoding is actually running — **the checkpoint's BF16 draft head stays
> intact instead of inheriting the quant config**"*
> *"fp8 KV cache: dense fp16 KV needs 9.5 GiB at 128K and doesn't fit; fp8 halves it to ~4.75 GiB"*
> *"Native INT4 w4a16 kernel (`XPUwNa16LinearKernel`) instead of a BF16 dequant fallback"*

## 2. What we verified

**Repo is real and current:** `SergiioB/intel-arc-pro-b70-inference-cookbook` — **MIT**, 17★,
created 2026-08-06, **pushed 10:52Z, two minutes before the post**. 88 files: 4 engine patches,
11 benchmark harnesses, a campaign log, raw result JSON, and LocalMaxxing submissions. Not a
thread with screenshots — a working repo.

**The mechanism, read from `patches/patch_mtp_bf16_draft.py` (verbatim docstring):**

> *Native-MTP-Preserved GPTQ keeps `mtp.*` as BF16 fused tensors (gate_up_proj / down_proj).
> **Draft inherits target GPTQ quant_config → expert params become GPTQ-shaped (`w2_qweight`)
> → KeyError on `w2_weight` during fused load.***

The fix is four lines — rebuild the draft head with the quant config stripped:

```python
_qname = quant_config.get_name() if quant_config is not None else None
if _qname is not None:
    print(f"[B70] MTP MultiTokenPredictor: forcing unquantized draft (was {_qname})")
    vllm_config = dataclasses.replace(vllm_config, quant_config=None)
    quant_config = None
```

It also ships a **debug dump** that prints every expert param on the draft head and warns
`"no w2_weight in MTP draft — still quantized or missing MoE"`. That warning is the shape of a
diagnostic we don't have.

**Their engine numbers** (`results/engine-comparison-full-20260806.md`, single-stream,
`max-num-seqs=1`, temperature-controlled, MoE 35B-A3B):

| | vLLM XPU MTP | llama.cpp SYCL | win |
|---|---|---|---|
| decode | 105–130 t/s | 58–74 t/s | **1.5–2.1×** |
| prefill | 563–7,526 t/s | 104–1,728 t/s | **3.8–8.5×** |

MTP alone was **1.69× over their own no-spec baseline**.

---

### 🔴 The finding — read live off `spark`, and it changes one of our own conclusions

Our EAGLE3 bench (`~/bench-eagle3-hardened.sh` on ryan-spark) ran:

```bash
M=~/models/gpt-oss-120b/gpt-oss-120b-MXFP4.gguf
D=~/models/gpt-oss-120b/eagle3-gpt-oss-120b-Q8_0.gguf      # <-- QUANTIZED draft head
llama-server -m "$M" -md "$D" --spec-type draft-eagle3 \
  --gpu-layers-draft 999 --spec-draft-n-max 16 ...
```

And in the same directory, **unused**:

```
/home/ryanneely1000/models/gpt-oss-120b/eagle3-gpt-oss-120b-BF16.gguf   ← never benched
/home/ryanneely1000/models/gpt-oss-120b/eagle3-gpt-oss-120b-Q8_0.gguf   ← what we ran
```

**We benched the quantized draft head and rejected speculative decoding on the result.** The BF16
draft was already on disk.

Two independent config confounds in that one run:

| Confound | What we ran | Why it inflates the loss |
|---|---|---|
| **Quantized draft** | `eagle3-…-Q8_0` | EAGLE3 predicts in the target's hidden-state space; the head is tiny, so quant error lands straight on acceptance. This signal is a documented case of exactly this class silently degrading a draft. |
| **Oversized draft length** | `--spec-draft-n-max 16` | Measured mean accept length was **2.8–3.2** — so ~13 of every 16 drafted tokens were verified and thrown away, every step. `t_227d09b2`'s own comment flagged this ("mean accept ~3 says 16 wastes 13") and it was parked, not retested. |

For scale: our measured acceptance was **11.7–14.2%**. Published EAGLE3 acceptance is typically
**60–80%**. A 5× shortfall against the technique's own literature is much more consistent with a
misconfigured drafter than with "GB10 can't do this."

**What this does and does not overturn.** It does **not** prove spec-dec works here — it removes
`t_227d09b2`'s EAGLE3 row from the evidence pile until it's re-run clean.

> ### ⚠️ UPDATED same day — the DFlash comparison in this section was superseded within the hour
>
> I originally wrote that `t_e28b2c0e` (DFlash) was *"the strongest argument that draft+verify
> overhead eats the win, because that one had healthy acceptance."* **Ryan caught a methodology
> bug in that A/B and it was redone properly** (card comment 11:41). Two flaws: wall-clock timing
> around the whole HTTP call instead of Ollama's native `eval_count`/`eval_duration`, and
> `reasoning_effort=medium` letting the model burn the entire 256-token budget on invisible
> chain-of-thought.
>
> **Corrected run** (native decode-only timing, `think:false`, temp 0, warm, 3 runs each):
>
> | | tok/s | drafter activity |
> |---|---|---|
> | baseline | **20.7** (20.9 / 20.8 / 20.4) — *was wrongly reported as 15.0* | — |
> | dflash | **14.0 — ~32% slower** | `drafted=7,1,1` out of `iterations=251–255` |
> | *(earlier, reasoning-heavy)* | — | `drafted=147–218`, acceptance 60–74% |
>
> **The 60–74% acceptance was on reasoning filler, not on code.** With real code output the
> drafter essentially opts out — and decode is *still* ~32% slower. So the mechanism is **not**
> "good acceptance, overhead still loses." It is **a structural dual-model throughput tax that is
> paid whether or not the drafter does anything useful.** Verdict unchanged (dflash rejected,
> tag removed); reasoning corrected.

**Which means the tally is now weaker than I stated, not stronger.** All three local "losses" have
an identified, non-fundamental cause:

| Run | Why it lost | Fundamental? |
|---|---|---|
| DFlash | drafter domain-mismatched (reasoning, not code) + dual-model residency tax | **no** — wrong drafter for the workload |
| DSpark | Metal-only, 0 CUDA | **no** — absent code path |
| EAGLE3 | quantized draft head + `n_max` 16 vs accept-len ~3 | **no** — misconfiguration (this entry) |

**We do not have a single clean datapoint where a well-matched, well-configured drafter with real
acceptance failed to pay on our hardware.** That is a materially different position from
*"spec-dec has lost three times,"* which is what I told Ryan this morning — and it raises, not
lowers, the value of the BF16 EAGLE3 retest.

## 3. Takeaways (5)

1. **A drafter can be silently degraded rather than broken.** vLLM's failure mode here was a loud
   `KeyError`; ours was quiet — a number that looked like a verdict. Any spec-dec bench needs a
   **draft-provenance line in the log** (dtype/quant of the draft actually loaded), not just an
   acceptance percentage.
2. **We had the right weights and used the wrong ones.** The BF16 draft was downloaded and never
   benched. This is a bench-hygiene failure, not a hardware finding.
3. **Their tok/s multipliers do NOT transfer.** Intel Arc / SYCL is llama.cpp's *weak* backend;
   ours is CUDA on GB10, where llama.cpp is far more competitive. **Quoting "vLLM is 2.4–3×
   llama.cpp" as if it applied to Spark would be the exact error this log exists to prevent.**
4. **But the *structural* claim does transfer, and it corrects me.** Their entire single-stream win
   (`max-num-seqs=1`) came from a native INT4 kernel replacing a dequant fallback, plus working
   spec-dec — **neither is a batching/width lever.** This morning I narrowed B17's engine phase to
   "width/batching only." That was too tight: prefill is their largest multiplier (3.8–8.5×) and
   **prefill is precisely our worker bottleneck** (~35.7k-token prompts; the KV raise moved prefill
   7.30 s → 2.47 s and decode not at all).
5. **fp8 KV is a lever we haven't touched.** They halved KV (9.5 → 4.75 GiB at 128K). Our DS4
   entries cost **883 MiB at ctx 65536** (~13.8 KiB/token, `t_e471787f`). Not urgent — we just went
   8 → 64 GB of budget and evictions are at zero — but it's the knob if ctx rises again.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Never bench a quantized draft head, and log which one loaded** | Re-run the EAGLE3 A/B on ryan-spark with `eagle3-…-BF16.gguf` (already on disk) and `--spec-draft-n-max 4` instead of 16. Two variables, both known-wrong, both free. Report accept % + tokens/step + net tok/s vs the 49–50 engine-only baseline. **If it stays ≲20%, the rejection is real and we close it for good with evidence instead of a confound.** | **P0** | open — wired to `t_171fbfd2` |
| S2 | **Draft provenance in the bench contract** | Every spec-dec bench row records the draft file, its dtype/quant, and `n_max` alongside acceptance. Their patch literally prints a `WARNING: still quantized` line; ours printed nothing. Fold into the bench-scoreboard schema. | P1 | open |
| S3 | Engine phase is a **prefill** lever, not only a width lever | Correct B17's scope: their biggest multiplier is prefill on a single stream, which is our dominant worker cost. Doesn't change the ordering (still gated on `t_171fbfd2`) but changes the *reason*. | P1 | open — commented onto `t_99c5d345` |
| S4 | fp8 KV cache | Halves KV footprint; parked until ctx rises past what the 64 GB budget covers. | P2 | open |
| S5 | Ship the bench-visual skill *inside* the research repo | `.agentic/skills/b70-benchmark-visuals/` — SKILL.md + render script co-located with the data it renders. Mirrors what `t_5183cf91` (nightly bench loop) will need. | P2 | note only |

## 5. Do NOT

- **Do not quote their tok/s as applicable to us.** Intel Arc B70 / SYCL / GPTQ-Int4 / vLLM XPU.
  Different silicon, different backend maturity, different quant. The *mechanism* ports; the
  numbers do not.
- **Do not apply their patches.** They rewrite files inside `/opt/vllm/` in a vendor Docker image
  we don't run. Read them; don't run them.
- **Do not treat this as reopening `t_716141c4`.** DSpark on DS4 is Metal-only, 0 CUDA — an absent
  code path, not a misconfiguration. That NEGATIVE-FINAL stands.
- **Do not re-run the EAGLE3 window without pausing consumers.** Hard rule from `t_227d09b2`
  (2026-08-10 07:57): a bench window thrashed unified memory until sshd died and Ryan
  power-cycled the box. Stop the ollama *service* / down the tunnel, gate on MemAvailable, run
  from a file, never `pkill -f` (it self-matched, and separately matched Ollama's bundled
  `llama-server` and killed the warm 120b).
- No `curl | sh`. Nothing on Kevin's box.

## 6. Provenance note

Fetched with `api.fxtwitter.com` per the skill's first route — worked first try, no auth.
Repo metadata via the GitHub API; patch source, launch script and `results/*.md` read raw from
`raw.githubusercontent.com`. Our own bench config and the unused BF16 draft were read **live off
`spark`**, not inferred from the card text — which is why the confound surfaced at all.

## 7. Next action (one)

Kanban comment on **`t_171fbfd2`** (the live card asking whether spec-dec pays here) recording the
draft-quantization confound and the free retest. **No new card** — the retest belongs inside that
card's decision, and the board is at 44 blocked.
