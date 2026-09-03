# SIG-20260825-01 — witcheer: one symlink so Hermes never sees the GGUF swap

```yaml
id: SIG-20260825-01
date: 2026-08-25
title: "witcheer (Nous community) EP 8 — llama-server --model ~/models/current.gguf --alias current.gguf; swap is ln -sf + restart. Friction he names is not on this desk (we key on Ollama/provider names). Real lesson is alias ≠ receipt."
index_title: "witcheer current.gguf + --alias — swap GGUF without touching Hermes. Already owned via Ollama tags / provider model strings. Steal P2: alias is not a receipt (same class as ds4 ExecStartPre). No card."
index_links: []
source_url: "https://x.com/witcheer/status/2091993598149439975"
source_url_2: "https://x.com/witcheer/status/2089402243262947340"
canonical_repo: ""
canonical_docs: ""
bucket: ops
posture: steal
steal_rank: P2
confidence: high          # fxtwitter verbatim + card image; live ~/.t1000/config.yaml model names read (no secrets). No install.
hardware_fit: [spark, mbp]  # only the llama.cpp bench lane still points --model at a file
stacks_touched: [t1000]
related_plans:
  - "SIG-20260810-07"     # ExecStartPre grepped a receipt, launched the rollback binary
  - "SIG-20260810-03"     # llama-server loaded Q8_0 draft while BF16 sat unused
  - "local-inference-fleet"
status: open
status_note: "**OPEN — steal P2, no card.** Hardware pre-filter N/A. Desk already keys on gpt-oss:120b / deepseek-v4-flash / qwen3-coder:30b, never a GGUF path. Do not add current.gguf in front of a production unit without logging readlink -f + sha256 — that is how the 10-07 fork/rollback split hid."
distill: none
```

## 1. Claim

[@witcheer](https://x.com/witcheer/status/2091993598149439975) (Nous Research community; ~16.1k followers; **88 likes / 3 RTs / 98 bookmarks / 5.1k views** at read; 2026-08-24 20:58 UTC; note-tweet + card; quotes his 08-17 "server choice is not a commitment" post). Fetched verbatim via `api.fxtwitter.com`:

> if you are running Hermes Agent on a local model, you end up swapping GGUFs a lot… your server points `--model` straight at the model file, so every swap means editing your agent config…
>
> point the server at a symlink you control instead.
>
> `--model` reads `~/models/current.gguf`, and `--alias` pins the name the API reports. from then on a swap is one line, `ln -sf` the new file onto `current.gguf`, then restart the server.
>
> the agent config never changes, because the name it keys against never changed.

Card (EP 8, *Running Hermes Agent fully local*):

```text
--model ~/models/current.gguf --alias current.gguf
ln -sf ~/models/the-new-one.gguf ~/models/current.gguf
# then restart the server. that is the whole swap.
```

## 2. What we verified

| Check | Result |
|---|---|
| Post body | **verbatim** via fxtwitter + vxtwitter; quote is the 08-17 "Hermes only sees a local URL" card |
| Repo / package | **none** — ops tip, not a product |
| Live desk config | `~/.t1000/config.yaml` (read 2026-08-25): default `grok-4.6` / `xai-oauth`. Local aliases are **API names** — `gpt-oss:120b`, `deepseek-v4-flash`, `qwen3-coder:30b`, `hermes3:8b-16k`, `mtplx-qwen38-27b-optimized-speed`. **Zero GGUF paths** in the model/alias map |
| Production serve | Ollama **tags** (Spark `:11435`) and **systemd units** (Kevin EXL3 `:8889` / ds4). Name stability is already the tag / unit, not a filename |
| llama.cpp bench lane | Still launches `llama-server -m $FILE` (SIG-20260810-03 / 10-01). That is the only place his command is literally true |
| Hardware pre-filter | **N/A / pass.** Not a PCIe-offload win |
| Duplicate URL | No prior witcheer / `current.gguf` entry |

**The friction he names is not on this desk.** Hermes never keys against a GGUF basename. Swapping a Spark Ollama quant is a tag pull; swapping Flash is a unit/path change behind `:8889`, not a `model:` edit.

**The trap if we copied him blindly.** A stable `--alias` with a moving symlink is the same shape as `ds4.service` grepping a fork *receipt* while `ExecStart` launched the upstream **rollback** binary (SIG-20260810-07). Scoreboard would say `current.gguf` for every quant. We already loaded the **wrong** draft file once (`eagle3-…-Q8_0.gguf` while BF16 sat unused — SIG-20260810-03) *because* the row did not record the resolved path.

## 3. Takeaways (max 5)

- **Witcheer is ops hygiene, not a product.** EP 8 of a Nous-local series. Cite the pattern, not a repo.
- **We already own the stable-name layer.** Ollama tags + provider model strings. Do not add a `current.gguf` in front of Spark/Kevin production.
- **Alias is not a receipt.** If llama.cpp bench ever uses `--alias`, the row must carry `readlink -f` + sha256 of the target. Same contract as `ExecStartPre` asserting the binary it launches.
- **Quote-tweet is already doctrine.** "Hermes only sees a local URL" = our provider map. No steal there.
- **Restart is not free on a KEEP_ALIVE=-1 box.** His "then restart the server" is a cold load. On ryan-spark that evicts 120b. Bench llama-server is a **separate PID**; never `pkill -f llama-server`.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Stable API name + logged resolved artifact** — `--alias` / tag / unit name for the agent; `readlink -f` + sha256 on the receipt / bench row | When the next llama.cpp A/B is written, add `--alias` if you want Hermes untouched **and** write the resolved GGUF into the metric card. Do not invent `~/models/current.gguf` on a production unit | **P2** | log only |
| S2 | Curl the model first, then bring the agent (quote-tweet) | Already the local-worker smoke rule. No new action | P2 | already owned |

**Primary steal (one only): S1.** The tip is right for a single llama.cpp + Hermes laptop. On this fleet the missing half is the receipt.

## 5. Do not

- **Do not put `current.gguf` in front of `exl3-k2-spark` / `ds4.service` / Ollama.** Those already have a stable name. A symlink there hides the next rollback.
- **Do not treat `--alias` as provenance.** Bench contract still wants `draft_file` / resolved path.
- **Do not `pkill -f llama-server` after a "swap."** Matches Ollama's bundled runner.
- **Do not edit `~/.t1000/config.yaml` model strings to GGUF filenames** to "try" this.

## 6. Next action (mechanical)

- [x] `INDEX.md` regenerated via `signal_log_index.py --write`
- [ ] no STEALS.md row (P2)
- [ ] no card

## 7. Chat blurb

`SIG-20260825-01` · `ops` · **steal P2** · witcheer EP 8: `ln -sf` onto `current.gguf` + `--alias` so Hermes never sees the swap. **We already do this** via Ollama tags / provider names. Primary steal **S1 — alias is not a receipt** (same class as the ds4 fork/rollback split). No card.
