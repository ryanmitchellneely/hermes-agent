# SIG-20260811-03 — Unsloth Desktop ships an open-source local run+train app **and a first-party `unsloth start hermes` integration for our own runtime**; the real find is that their DGX Spark training path fits Ryan's box and B18's plan never considered it

```yaml
id: SIG-20260811-03
date: 2026-08-11
title: "Unsloth announces Unsloth Desktop (beta) — free, open-source, Mac/Windows/Linux app to run AND train models locally (MLX, GGUF, diffusion, audio), connect Claude Code and Codex to local LLMs, claimed 50% more accurate self-healing tool calls, 2x faster training with 70% less VRAM. Verified: Desktop ships inside the EXISTING unslothai/unsloth repo (69,950 stars, Apache-2.0) and their docs carry a first-party 'How to Run Local AI Models with Hermes Agent' integration page with an `unsloth start hermes` launcher"
index_title: "Unsloth Desktop (beta): open-source local run+train app, Apache-2.0, ships INSIDE unslothai/unsloth (69,950 stars) — no separate repo. Two things land on us and neither is the app itself. (1) First-party HERMES AGENT integration page + `unsloth start hermes` launcher that 'mints an API key, writes the config' — and our shell exports HERMES_HOME=/Users/ryan/.t1000, so their 'separate managed home, your existing setup unchanged' claim is UNVERIFIED against an ambient HERMES_HOME; any spike must run `env -u HERMES_HOME` or it can write a provider + minted key into the desk control plane. (2) Their DGX Spark Docker training path trains up to 200B / gpt-oss-120b at ~68GB unified — Ryan's spark has Docker 29.2.1 installed and 121GB total (43 free NOW with gpt-oss:120b resident; ~108 after unload), so it FITS. B18's plan routes training to MBP/MLX with 'optional CUDA/unsloth on CadensPC' (RTX 4060, 8GB) and never evaluated the Spark, which is the strongest training box on the fleet. Does NOT unblock B18 — still corpus-blocked at 2 trainable pointers vs 500"
source_url: "https://x.com/unslothai/status/2087177146662072546"
canonical_repo: "https://github.com/unslothai/unsloth"
canonical_docs: "https://unsloth.ai/docs/desktop"
index_links: [repo, docs]
bucket: harness
posture: spike
steal_rank: P1
confidence: high          # post fetched verbatim via fxtwitter; repo/release metadata from the GitHub API; every doc quote from unsloth.ai .md sources; every fleet number measured live on this Mac and over ssh
hardware_fit: [spark, mbp, cadenspc]
stacks_touched: [t1000, student-lab]
related_plans:
  - "B18"                 # Mac mini student model — the plan this actually touches
  - "SIG-20260810-01"     # Muse Glimmer / DFlash — same vendor, same week, the nvfp4 export lane
  - "SIG-20260810-05"     # Liquid cookbook — the other fine-tuning-recipe signal; same B18 gap
  - "SIG-20260811-02"     # Hermes Browser Use mode — the other first-party-touches-our-runtime signal
status: carded
status_note: "**CARDED `steals` / `t_b03a04ab` (ST-12, blocked: Ryan's word) for S1; S2 commented onto `t_848b57b7` (mesh/B18) as a plan amendment, deliberately not carded.** **Two steals, neither is 'install the app'.** (1) `unsloth start hermes` is a first-party launcher for OUR runtime — docs claim it runs from 'a separate managed home' leaving the existing setup unchanged, but it also 'mints an API key, writes the config', and this desk EXPORTS `HERMES_HOME=/Users/ryan/.t1000` (both in the live env and in `~/.local/bin/hermes`). Whether their managed home overrides an ambient HERMES_HOME is **not verifiable without installing** — so the mitigation is mandatory, not optional: `env -u HERMES_HOME unsloth start hermes` and never `--persist` on a first run. (2) The **DGX Spark training path is the real find**: their Docker image (`nvcr.io/nvidia/pytorch:25.09-py3`, triton+xformers from source, `TORCH_CUDA_ARCH_LIST=12.1`) trains up to 200B on 128GB unified, gpt-oss-120b at ~68GB. Measured on ryan's spark: **Docker 29.2.1 present**, 121GB total, **43GB available right now** with `gpt-oss:120b` (65.1GB) resident — unload it and ~108GB is free, which clears the 68GB bar. B18's plan (`~/.hermes/plans/2026-08-07_074000-mac-mini-student-model.md`) routes Phase C training to **MBP/MLX** and names only 'optional CUDA/unsloth on CadensPC' (RTX 4060, **8GB**) as the accelerator — it never evaluated the Spark, which is by far the strongest training box on the fleet. That is a genuine plan gap, NOT a free win: MLX was chosen deliberately so MBP -> mini is a hostname change (train and serve in one framework); training on Spark/CUDA breaks that property and adds an export/convert step. **Does not unblock B18** — that program is corpus-blocked at 2 trainable pointers vs 500 and 0 labels; a better trainer changes nothing about that. Also found: the in-tree skill `optional-skills/mlops/training/unsloth/SKILL.md` (v1.0.0, Orchestra Research) is generic LoRA/QLoRA, is **not activated** in `~/.t1000/skills`, and predates Desktop / Studio / the Hermes integration entirely."
distill: none
```

## 1. Claim

[@UnslothAI](https://x.com/UnslothAI/status/2087177146662072546), 2026-08-11 13:59 UTC
(1,066 likes / 36,335 views at read time), fetched verbatim via `api.fxtwitter.com`:

> **Introducing Unsloth Desktop 🦥**
> The first desktop app to run and train models locally.
>
> • Open-source. Runs on Mac, Windows and Linux
> • Supports MLX, diffusion image/video, audio, GGUF
> • Connect Claude Code and Codex to local LLMs
> • 50% more accurate, self-healing tool calls + sandboxed code exec
> • Works for CPU + multiGPU setups - NVIDIA, AMD, Intel, Mac
> • Train models 2× faster with 70% less VRAM
> • Private web search, deep research, RAG, MCP and exports (NVFP4, GGUF)
> • Use Unsloth's OpenAI-compatible API and cloud models
> • Securely deploy LLMs remotely and access anywhere

First-party announcement, so the framing is theirs. **Do not repeat "the first desktop app to run
and train models locally" uncritically** — LM Studio, Jan, GPT4All and Ollama's own app have run
models locally for years. *Training* in a desktop GUI is the defensible half of that claim; "first
to run" is not, and none of it is measured in the post.

## 2. Verified — what is actually there

| Check | Result |
|---|---|
| Repo | **`unslothai/unsloth`** — **69,950 stars, Apache-2.0**, created 2023-11-29, pushed 2026-08-11 15:10 UTC |
| Separate desktop repo? | **No.** `unslothai/unsloth-desktop`, `/desktop`, `/unsloth-app` all **HTTP 404** — Desktop ships inside the existing library repo |
| Repo description (now) | *"Local UI to run and train LLMs and diffusion models, including Kimi K3, MiniMax-H3, Gemma 4, Qwen3.6, DeepSeek-V4, FLUX and more."* — the repo has been **repositioned from a training library to a local UI** |
| Latest releases | `v0.1.62-beta` (2026-08-11), `v0.1.61-beta` / `v0.1.60-beta` "Meta Muse Glimmer" (08-10), `v0.1.526-beta` "DSpark + DeepSeek-V4 Flash 0731" (08-04) |
| Open issues | 1,026 |
| Docs page | `https://unsloth.ai/docs/desktop` — HTTP 200, "Unsloth Desktop (Beta) is a free, open-source app… macOS, Windows, and Linux" |

Their release history is worth noting on its own: **`v0.1.526-beta` is literally titled "DSpark +
DeepSeek-V4 Flash 0731"** — the exact drafter and the exact checkpoint from `SIG-20260810-06` /
`t_716141c4`. Same vendor, same week, same model family we are already benching.

## 3. The part that touches our runtime — `unsloth start hermes`

Their docs carry a first-party integration page: **"How to Run Local AI Models with Hermes Agent"**
(`https://unsloth.ai/docs/integrations/hermes-agent`), alongside sibling pages for OpenClaw,
OpenCode, VS Code, Claude Code and Codex. Verbatim:

> Hermes Agent by Nous Research is an open-source autonomous AI agent that connects to a model
> endpoint… Hermes acts as the agent client, while Unsloth loads and serves models via the local
> API entirely offline.
>
> **Connect Hermes.** Run `unsloth start hermes`. It **mints an API key, writes the config**, and
> launches Hermes against your loaded model.
>
> Unsloth launches Hermes from a **separate managed home** with the Unsloth provider, model, and
> context settings already configured. **Your existing Hermes setup is left unchanged.**

Two launch shapes:

```bash
unsloth start hermes --model unsloth/gemma-4-E2B-it-GGUF:UD-Q4_K_XL --context-length 32768
unsloth start hermes --persist          # keeps sessions/state instead of a temp home
unsloth start hermes --persist --continue
```

Manual path is a plain OpenAI-compatible provider — `API base URL: http://localhost:8888/v1`,
Hermes auto-detects via `GET /v1/models`.

### ⛔ The risk, and why the mitigation is mandatory

Their doc assumes the stock layout: it names **`~/.hermes/config.yaml`** as the config path. **This
desk does not use that path.** Measured live:

```text
env                      HERMES_HOME=/Users/ryan/.t1000
~/.local/bin/hermes      export HERMES_HOME="${HERMES_HOME:-$HOME/.t1000}"
```

`HERMES_HOME` is **exported in the live shell** and re-exported by the wrapper. Their "separate
managed home / existing setup unchanged" guarantee is a claim about *their* default, and it is
**unverified against an ambient `HERMES_HOME`**. If their launcher resolves the home the same way
Hermes itself does, then a command documented as "mints an API key, writes the config" points at
**`~/.t1000/config.yaml` — the desk control plane**, and `--persist` makes it durable.

Cannot be settled without installing, so it is a hard precondition on any spike, not a caveat:

- run **`env -u HERMES_HOME unsloth start hermes`**
- **never `--persist` on a first run**
- snapshot `~/.t1000/config.yaml` + `auth.json` before, diff after

### What it would actually buy us — probably little

We already have three OpenAI-compatible local endpoints live, measured this session:

```text
:11434  MBP ollama      0.32.7
:11435  ryan-spark      0.31.2      (tunnel up)
:11436  cadenspc        0.32.5
:8889   DS4 Flash       context_length 65536
```

**Connectivity is not our problem.** The only marginal value on offer is model *management* (browse,
download, swap without touching Ollama tags) and the **"50% more accurate, self-healing tool calls"**
claim — which is unquantified, has no published methodology, and no baseline. That claim is
nonetheless the interesting one for us specifically, because we have eaten the same failure class
**three times** (DS4 Flash empty `content` with everything in `reasoning_content`; gpt-oss on a small
`num_predict`; gpt-oss ignoring OpenKB's JSON contract and writing prose to disk). If "self-healing"
means retry-on-unparseable, that is exactly the guard our own compile step needed. **Unverified.**

## 4. The real find — the DGX Spark training path fits Ryan's box

Their blog `fine-tuning-llms-with-nvidia-dgx-spark-and-unsloth` documents a working Docker path:

> Unsloth enables local fine-tuning of LLMs with up to **200B parameters** on the NVIDIA DGX™ Spark.
> With 128 GB of unified memory, you can train massive models such as **gpt-oss-120b**… gpt-oss-120b
> will use around **68GB** of unified memory.

Dockerfile from `unslothai/notebooks/Dockerfile_DGX_Spark`: `nvcr.io/nvidia/pytorch:25.09-py3`,
CUDA 13.0, **triton built from source at `c5d671f` for Blackwell**, **xformers from source with
`TORCH_CUDA_ARCH_LIST="12.1"`**, then `unsloth unsloth_zoo bitsandbytes==0.48.0 transformers==4.56.2
trl==0.22.2`. Launch is `--gpus=all --net=host --ipc=host --ulimit memlock=-1` with the HF cache
bind-mounted.

Measured on **ryan's spark** just now:

```text
Docker      29.2.1, build a5c7197            <- already installed
Mem         121 total · 78 used · 43 available
Resident    gpt-oss:120b  65.1 GB
```

**43 GB available is below the 68 GB bar — but only because the 120b is pinned.** Unload it and
~108 GB frees, which clears it comfortably. So the box is capable *today*, with no purchase and no
new hardware; the cost is that training and the 120b propose lane **cannot co-reside**.

### Why this is a genuine gap in B18's plan

`~/.hermes/plans/2026-08-07_074000-mac-mini-student-model.md` sets the training stack as:

> **Tech stack:** MLX (`mlx_lm.lora` train + `mlx_lm.server` serve — same framework MBP → mini) ·
> Ollama retained for embeddings only · … · **optional CUDA/unsloth on CadensPC** for larger runs
> (`~/Documents/T1000/optional-skills/mlops/training/unsloth/`)
>
> Phase C  Student bake-off + LoRA  (weeks 8-10)  **[MBP, MLX]**
> CadensPC never becomes load-bearing. Optional accelerator only.

So the plan already anticipated Unsloth — and pointed it at **CadensPC (RTX 4060, 8 GB)**, the
weakest box on the fleet, while **never evaluating the Spark**, which has ~15× the memory and a
vendor-published Docker image for this exact silicon.

**But this is a trade-off, not a free win, and the plan's reasoning was sound:**

> **Why MLX over Ollama here:** LoRA trains natively on the M3 Max (`mlx_lm.lora`), serves via the
> same framework, and the **MBP → mini migration becomes a hostname change**. Ollama keeps embeddings.

Training on Spark/CUDA **breaks that property**. You would train with unsloth, export GGUF/NVFP4, and
still need a conversion step to serve on an Apple-silicon mini via MLX. The MLX choice buys migration
simplicity; the Spark buys headroom. Which wins depends on student size — and the plan's own
selection rule caps the student at **8–14B**, a size MLX on a 64 GB M3 Max handles without help.

**Honest read: the Spark matters only if the student grows past what MLX/MBP can train, or if a
teacher-scale run (gpt-oss-120b class) is ever wanted. Neither is true today.**

### And it changes nothing about B18's actual blocker

B18 is **corpus-blocked**: 2 trainable pointers against a 500 floor, 0 human labels. A faster,
larger-capacity trainer does not move either number. Filing a better trainer as B18 progress would be
the same category error the program has already been warned about — the bottleneck is data, not
compute.

## 5. Fleet notes banked while verifying

- **In-tree unsloth skill is stale and dormant.** `optional-skills/mlops/training/unsloth/SKILL.md`
  — v1.0.0, author "Orchestra Research", generic *"2-5x faster LoRA/QLoRA fine-tuning, less VRAM"*.
  It is **not activated** in `~/.t1000/skills`, and its references predate Desktop, Studio,
  `unsloth start`, and the DGX Spark Docker path entirely. If any of this is ever pursued, that skill
  is the natural home and it needs a refresh first.
- **`ssh cadenspc` fails with `Host key verification failed`** — while the tunnel on `:11436` answers
  fine (ollama 0.32.5). Direct shell access to the box that the B18 plan names as its CUDA
  accelerator is currently broken. Unrelated to this signal; worth its own look if Caden's box ever
  becomes real work (`t_47f30baf`).
- Unsloth's docs index also carries **Claude Code** and **OpenAI Codex** local-model pages. Ryan's
  Claude path is **claude-acp against Max** (per USER doctrine: acp only, never HTTP, never Copilot).
  Pointing the Claude Code *harness* at a local model is a different lane from the desk's Claude
  lane — potentially zero-token, but it is not a substitute for Max and must not be conflated.

## 6. Steals

**S1 — P1 — spike `unsloth start hermes` behind `env -u HERMES_HOME`.**
Question answered: does a first-party model-manager + tool-call healer beat our Ollama/DS4 endpoints
for the local lanes? Precondition is the HERMES_HOME guard plus a config/auth snapshot-and-diff.
Cheap, reversible, and the only way to test the "50% more accurate tool calls" claim.

**S2 — P1 — evaluate the Spark as B18's training box, as a plan amendment, not a build.**
The plan names CadensPC (8 GB) and never considered the 121 GB Spark that already has Docker and a
vendor image. Amendment should record the trade-off honestly (MLX single-framework migration vs CUDA
headroom + export step) and the co-residency cost (training evicts the 120b propose lane). **Not to
be run while B18 is corpus-blocked.**

**S3 — P2 — refresh the in-tree unsloth skill** if S1 or S2 lands: add Desktop/Studio, the
`unsloth start` reference, the DGX Spark Dockerfile, and the HERMES_HOME warning.

**Do not:**

- Install Desktop expecting it to replace or improve the T1000 desk — the desk's problem has never
  been model connectivity.
- Let any unsloth command write to `~/.t1000` — snapshot and `env -u HERMES_HOME` or don't run it.
- Quote "50% more accurate self-healing tool calls" or "2× faster / 70% less VRAM" as measured — no
  methodology, no baseline, first-party marketing.
- Repeat "first desktop app to run and train models locally" — the *run* half is plainly not first.
- Treat a better trainer as B18 progress. B18 needs corpus and labels.
