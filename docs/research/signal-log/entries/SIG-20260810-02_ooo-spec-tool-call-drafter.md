# SIG-20260810-02 — OoO-Spec: a 0.6B sidecar that speculates *tool calls*, not tokens

```yaml
id: SIG-20260810-02
date: 2026-08-10
title: "OoO-Spec (arXiv 2608.00814) — out-of-order semantic speculation makes tool calling 3.89x faster with a Qwen3-0.6B sidecar"
index_title: "OoO-Spec tool-call drafter — 3.89x claimed on 2xH100/vLLM. Engine-gate framing SUPERSEDED same day (llama.cpp on ryan-spark already has --spec-type); real gate is accept-rate x decode-share -> profile card t_171fbfd2"
steal_rank_note: "S1 superseded; S2 promoted P2 -> P0 and carded"
index_links: [docs]
source_url: "https://x.com/teksedge/status/2086505517640540587"
canonical_repo: ""                       # no code released
canonical_docs: "https://arxiv.org/abs/2608.00814"
bucket: inference
posture: watch
steal_rank: P0
confidence: high                         # post fetched verbatim; paper abstract + HTML read directly
hardware_fit: [spark]                    # llama.cpp 62bf73d on ryan-spark HAS --spec-type; reachable today
stacks_touched: [t1000]
related_plans:
  - "B17"                                # Spark inference experiments — engine phase
  - "t_99c5d345"                         # B17 card
  - "t_716141c4"                         # DSpark NEGATIVE-FINAL on the DS4 server (different binary)
  - "t_227d09b2"                         # 120b engine swap — llama.cpp landed WITH --spec-type; EAGLE3 benched + rejected
  - "t_171fbfd2"                         # S2 carded: profile a real worker card (blocked on Ryan)
  - "SIG-20260810-01"                    # DFlash drafter — Ollama route CLOSED (412); llama.cpp route unexplored
status: carded
status_note: "S2 carded as t_171fbfd2 (blocked on Ryan). §2/§3 CORRECTED 2026-08-10: the 'no engine in the fleet can consume a drafter' claim was wrong — llama.cpp 62bf73d landed on ryan-spark ~1h before this entry was filed and exposes --spec-type draft-eagle3/draft-mtp/draft-dflash/draft-dspark/ngram-*."
distill: none
```

## 1. Claim

[@TeksEdge](https://x.com/teksedge/status/2086505517640540587) (David Hendrickson, 2026-08-09,
187♥ / 29RT) surfacing **OoO-Spec** — a tiny **Qwen3-0.6B sidecar** that predicts the *function
choice* and *argument values* of a tool call **in parallel** while the main model keeps decoding.
Framed as *"speculative decoding is coming for agents."*

The insight is not token-level drafting. It is that a tool call is **structurally predictable from
the request plus the tool schema** — so the semantics can be guessed out of order, then verified.

## 2. What we verified

**Post fetched verbatim** via `api.fxtwitter.com` (see §6 — this route matters).

**Paper — arXiv 2608.00814v1, submitted 2026-08-01.** *"OoO-Spec: Out-of-Order Semantic
Speculation for Fast Tool Calling"*, Zhang / Sun / Xu / Zhang. Abstract read directly.

| Their claim | Value |
|---|---|
| vs. autoregressive tool calling | **2.46–5.34×**, mean **3.89×** |
| vs. ToolSpec baseline | 2.95×; **+34.1%** on Qwen3 4B→32B |
| Mean Accepted Tokens (#MAT) | 6.81 (Qwen2.5-7B / API-Bank) · 8.35 (Qwen3-8B) |
| Hardware | **two H100-80GB**, sidecar served on **vLLM** |
| Benchmarks | API-Bank · ToolAlpaca · BFCL (Java/JS) — 21 target×benchmark combos |
| Drafter | one **LoRA on Qwen3-0.6B**, trained on **Qwen2.5-32B teacher traces**, 9,662 requests |
| Target-specific retraining | **none** — same drafter across Qwen2.5, Qwen3, Llama |
| Code released | **No.** No GitHub URL in the paper |

**Measured by us, today, on the fleet:**

| Fact | Evidence |
|---|---|
| **Ollama exposes no speculative-decoding surface whatsoever** | `ollama run --help`, `ollama serve --help`, full `OLLAMA_*` env list — **zero** draft/spec flags (v0.23.0 local; same CLI surface on 0.31.2/0.32.x) |
| `qwen3:0.6b` **is** in the Ollama library | tags `0.6b`, `-fp16`, `-q4`, `-q8` |
| Family match exists on Spark | `qwen3-coder:30b` (18.6 GB) — same Qwen3 tokenizer family as the 0.6B drafter |
| DS4 lane | custom server; upstream `dspark` is **Metal-only, 0 CUDA** (`t_716141c4` NEGATIVE-FINAL) |

### ⚠️ CORRECTION — 2026-08-10, same day, after the above was written

**The "nothing in the fleet can consume a drafter" conclusion was wrong.** It was true of Ollama
and false of the fleet. `t_227d09b2` completed at **09:59** — this entry was filed at **10:57** —
and it landed **llama.cpp `62bf73d`** on ryan-spark as the batch/window engine. Verified live:

```
$ llama-server --spec-type
none, draft-simple, draft-eagle3, draft-mtp, draft-dflash,
draft-dspark, ngram-simple, ngram-map-k, ngram-map-k4v, ngram-mod, ngram-cache
$ llama-server --version
version: 374 (62bf73d)   aarch64
```

Plus the whole `--spec-draft-*` family (draft KV cache types, draft HF repo, draft threads/affinity).

**So spec-dec is runnable on the fleet today** — on llama.cpp, not Ollama (`:11434` stays the
untouched production teacher lane per Ryan's Option-1 ruling) and not DS4 (custom server;
`t_716141c4` DSpark NEGATIVE-FINAL stands, different binary).

**And it has already been benched and rejected — three times, on three different setups:**

| Run | Card | Accept | Net result |
|---|---|---|---|
| EAGLE3 / gpt-oss-120b / llama.cpp `62bf73d` / ryan-spark ⚠️ **CONFOUNDED — see `SIG-20260810-03`**: ran the **Q8_0** draft head with the **BF16** one unused on disk, and `n_max 16` against mean accept len 2.8–3.2 | `t_227d09b2` | **11.7–14.2%** (165/1408, mean len 2.8–3.2) — vs EAGLE3's published 60–80% | 23.3 tok/s — **2× SLOWER**; **retest pending** |
| DFlash / muse-glimmer-30b-nvfp4 / Ollama 0.32.7 / MBP ⚠️ **RE-MEASURED 2026-08-10 11:41** — Ryan caught wall-clock timing + reasoning eating the token budget | `t_e28b2c0e` | **60–74% on reasoning filler; `drafted=1–7` of ~253 iterations on real code** | baseline **20.7** (not 15.0) vs dflash **14.0** = **~32% SLOWER** — a *structural dual-model tax*, not an acceptance/overhead tradeoff |
| DSpark / DS4 / GB10 | `t_716141c4` | n/a — **Metal-only, 0 CUDA** | no-op; A/B 16.23 vs 16.39 = noise |

~~The middle row is the important one: 60–74% acceptance — squarely in the range the Entrpi fork
claims — and it still lost. So "acceptance is the lever" is not sufficient.~~
**CORRECTED 2026-08-10** — that reading came from a flawed A/B (wall-clock timing; reasoning
burning the whole token budget). Re-measured, the 60–74% was on **reasoning filler**; on real code
the drafter barely fires (`drafted=1–7` of ~253 iterations) and is *still* ~32% slower. The
mechanism is a **structural dual-model tax**, not "healthy acceptance losing to overhead."

**Net effect on the family verdict: it gets weaker, not stronger.** With `SIG-20260810-03`'s
finding that our EAGLE3 run used a **quantized draft head** and `n_max 16` against accept-len ~3,
**all three local losses now have identified, non-fundamental causes** — wrong drafter for the
workload, absent CUDA path, and misconfiguration. We hold **zero** clean datapoints where a
well-matched, well-configured drafter with real acceptance failed to pay here.

Meanwhile the banked 120b win came from the **engine swap alone**: 49–50 vs 35–36 tok/s
(+37–40% raw, +30% on real battery tasks).

The corrected finding is therefore **not** "we lack an engine." It is:

> **We have a spec-dec-capable engine and three local results where speculation made things
> slower — including one at 60–74% acceptance. Nobody has measured what fraction of a worker
> card's wall time speculation could even touch.** That is now `t_171fbfd2`.

`ngram-*` deserves a specific callout: those drafters need **no draft model and no download**,
which makes them the cheapest possible test of the whole family — and they are unbenched.

## 3. Takeaways (5)

1. ~~**Fifth independent signal pointing at the same missing capability — every one needs
   vLLM/SGLang; Ollama is the ceiling.**~~ **CORRECTED, see §2.** Five signals do converge
   (`-20260806-01`, `-20260807-03`, `-20260808-06`, `-20260810-01`, this one), and Ollama *is* a
   ceiling — but the fleet stopped being Ollama-only on **2026-08-10**. llama.cpp `62bf73d` on
   ryan-spark already exposes the full `--spec-type` family, and EAGLE3 was benched on it that
   same day at **12–14% accept** and **rejected for running 2× slower**. The prerequisite is no
   longer *"get an engine."* It is *"is decode a big enough share of worker wall time to be worth
   speculating at all?"* — carded as **`t_171fbfd2`**.
2. **Semantic > token-level, for agents.** Generic spec-dec drafts the next token and hopes.
   OoO-Spec exploits the fact that a schema constrains the answer. Our worker traffic is
   tool-call-shaped, so this is the branch of the spec-dec family aimed at us.
3. **The speedup lands on the wrong segment of our profile.** Our worker latency is dominated by
   **prefill of a ~35.7k prompt**, not tool-call decode — yesterday's KV raise cut prompt phase
   **7.30 s → 2.47 s** and moved decode not at all. A tool call is ~100–200 tokens; at DS4's
   16.8 tok/s that's ~6–12 s, so 3.89× would save perhaps 5–9 s per call. Real, but second-order
   until the engine exists. **Profile before chasing.**
4. **The 3.89× is partly in-distribution.** The LoRA is trained on API-Bank + ToolAlpaca fixed
   splits and evaluated on API-Bank + ToolAlpaca + BFCL. Only BFCL is a genuinely held-out family.
   Treat the mean as an upper bound; the BFCL numbers are the honest ones.
5. **No code, v1 preprint, 2×H100 with split GPU placement.** The paper itself concedes colocation
   *"no longer fits one GPU"* at Qwen3-32B scale, and leaves edge/heterogeneous hardware to future
   work. GB10 unified memory is exactly the case they didn't test.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S2** | **Profile before optimizing the wrong segment** — now the top steal | One real worker card: what % of wall is prefill vs reasoning decode vs tool-call decode? EAGLE3 already failed here at 12–14% accept; the KV raise moved prefill 7.30s→2.47s and decode not at all. Decides whether *any* of this family is worth another window. | **P0** | **CARDED `t_171fbfd2`** (blocked on Ryan) |
| S2b | **`ngram-*` is the free test** | llama.cpp `62bf73d` ships `ngram-simple / ngram-map-k / ngram-map-k4v / ngram-mod / ngram-cache` — **no draft model, no download**. Cheapest possible probe of the whole family, and unbenched. Gated behind S2's answer. | P1 | open — folded into `t_171fbfd2` "what this unblocks" |
| ~~S1~~ | ~~The engine is the gate~~ **SUPERSEDED same day** | The vLLM/SGLang framing was wrong: llama.cpp `62bf73d` landed on ryan-spark 2026-08-10 09:59 with the full `--spec-type` family (`t_227d09b2`). The gate moved from *engine* to *accept rate × decode share*. B17's engine phase is still worth doing for **continuous batching / width**, which llama.cpp does not give us — but it no longer blocks spec-dec. | — | superseded |
| S3 | Target/drafter family pair already on the shelf | `qwen3-coder:30b` + `qwen3:0.6b` is tokenizer-compatible. Now actually consumable via llama.cpp `--spec-draft-hf` / `-md`. **Still don't pull it** until S2 says decode share justifies it. | P2 | open |

## 5. Do NOT

- **Do not `ollama pull qwen3:0.6b` expecting a speedup.** Verified today: no draft-model flag
  exists in Ollama. The pull would be 500 MB of shelf-ware and a fifth "why is this here" model.
  (llama.cpp *can* consume a drafter — but pull nothing until `t_171fbfd2` says decode share
  justifies it, and `ngram-*` needs no weights at all, so it comes first regardless.)
- **Do not bench on ryan-spark without pausing consumers.** Hard rule from `t_227d09b2`
  (2026-08-10 07:57): a bench window thrashed unified memory badly enough that sshd died and Ryan
  power-cycled the box. Stop the ollama *service* / down the tunnel, gate on MemAvailable, kill
  stray reload curls, run from a file (never `pkill -f` matching the script's own text — it
  self-matched, and separately matched Ollama's bundled `llama-server` and killed the warm 120b).
- **Do not quote 3.89× as applicable to us.** Different hardware (2×H100 vs GB10 unified),
  different engine (vLLM vs Ollama/DS4), partly in-distribution training.
- **Do not reopen `t_716141c4`** on the strength of this. Different technique; the CUDA path is
  still absent and DSpark stays NEGATIVE-FINAL.
- No `curl|sh`, no fork installs, nothing on Kevin's box.

## 6. Fetch route — record this

`x.com` was unreachable by every route the log has used before:
`WebFetch` → **404** · `r.jina.ai` → **403** (x.com anonymously blocked until 16:28 UTC, someone
else's abuse) · nitter.privacydev / nitter.poast / xcancel → empty or browser-challenge.

**`https://api.fxtwitter.com/<user>/status/<id>` returned full JSON — text, author, media, metrics.**
`api.vxtwitter.com` works identically and adds `date_epoch` + `mediaURLs`. No auth, no key.

This is now the **first** route in the skill, and it retroactively settled
**`SIG-20260810-01`**, which had been filed with an explicit "we could not fetch the post, the
subject is inferred, this may be the wrong link" warning. Fetched today: the Unsloth post *is*
Muse Glimmer. Inference confirmed, warning removed, confidence medium → high.

## 7. Next action (one)

~~Kanban comment on `t_99c5d345` (B17) recording the engine-gate convergence. No new card.~~
**Superseded 2026-08-10 (Ryan: "add a card for it").**

**`t_171fbfd2`** — *"Profile one real worker card: prefill vs reasoning-decode vs tool-call-decode
share"* — created on `mesh`, **blocked** with the gate *"Ryan picks the target worker card, and
confirms a one-shot manual profile is OK rather than waiting on MESH-TEL-2a."*

Deliberately **not** built as a new instrument: the `MESH-TEL-2` chain
(`t_e1a86e85` done → `t_3a1b8b6b` 2a **blocked** → `t_b3a90086` 2b, `t_d7f24672` 2c,
`t_2545126f` 2d) already owns per-call capture. The card consumes that stream if 2a lands, and
falls back to a one-shot manual profile if it hasn't — the cheaper path is explicitly in scope.

Also cross-referenced onto `t_227d09b2` (the engine/EAGLE3 card whose result corrected §2/§3) and
`t_99c5d345` (B17 — engine phase still justified for **continuous batching / width**, which
llama.cpp does not provide, but no longer as the spec-dec blocker).
