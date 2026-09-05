# Qwen3.8-Flash-Next pilot on ryan-spark — what is staged, how to flip, how to roll back

**Status (2026-09-05 23:20Z):** staged and VALIDATED (window 23:12–23:20Z), NOT flipped. Decision + evidence trail: models card `t_37efebbb`.
Bench canon: T1000 repo `docs/inference/BAKEOFF-DS4-VS-QWEN38-FLASH-NEXT.md`.

## What is on this box now

| piece | path | note |
|---|---|---|
| target model | `~/models/flash-next-udq3/Qwen3.8-Flash-Next-UD-Q3_K_XL-*.gguf` | unsloth, 90 GB, byte-verified |
| MTP draft heads | `~/models/flash-next-udq3/mtp-Qwen3.8-Flash-Next-{shared-,}Q8_0.gguf` | shared (2.8 GB) is the one in use |
| **production binary** | `~/llama.cpp-prod/build/bin/llama-server` | branch `flash-prod` @ `0a418d6c` = PR 28243 (MTP) + PR 28136 (direct PLE) merged, CUDA |
| bench binaries | `~/llama.cpp-mtp/` (28243 only), `~/llama.cpp-ple/` (28136 only), `~/llama.cpp/build-qwen4exp` (08-26 pin) | keep for A/B; do not serve from them |
| serve script | `~/models/flash-next/serve-udq3-mtp.sh <mode>` | `prod` = mtp3 + `--lazy-mode on-direct`; env `CTX`, `NP` |
| systemd units | `~/models/flash-next/unit/` | `flash-next.service`, `flash-next-health.{service,timer}`, `install.sh` (needs sudo, Ryan-present) |
| aux tiny models | ollama `qwen3:1.7b`, `qwen3-aux:1.7b` (8k ctx) | pulled, NOT loaded — see "residency" |

## Residency facts that constrain everything (measured 2026-09-05)

- 90 GB target + 2.8 GB head + 49k-ctx KV needs **ollama holding nothing bigger than hermes3**.
  flash-next cannot co-reside with gpt-oss:120b or qwen3.8:27b.
- **ollama on this box keeps at most three residents.** A fourth model of any size (tested 1.8 GB)
  evicts gpt-oss:120b; and loading 120b *last* evicts everything else. Load order: 120b first.
- After the flip the ollama set is: `hermes3:8b-16k` (+ optionally `qwen3-aux:1.7b`) — ~8 GB.

## The flip (runbook — do in this order, devbot lane quiet)

1. **Config first, models second.** On k2vps `/opt/t1000/home/config.yaml` (backup with a timestamp):
   - add provider `spark-flash`: `api: http://127.0.0.1:11439/v1`, `api_key: local`, `models: [qwen3.8-flash-next]`, `context_length: 49152`
     (11439 is the only free port ryan-spark's sparklink key may bind; it is labelled BENCH in
     MODEL-BENCH-LANE.md — re-label it PILOT there, or widen the fence by one port: a human call)
   - every `provider: spark` + `model: gpt-oss:120b` or `qwen3.8:27b` (profiles ~L729-786, moa
     reference_models ~L425-460, kanban default model, `auxiliary.compression`) → `spark-flash` / `qwen3.8-flash-next`
   - `agent.reasoning_overrides: qwen3.8-flash-next: none` for the fast lanes
2. Stop the two big residents and keep them from coming back: `ollama stop gpt-oss:120b; ollama stop qwen3.8:27b`
   (nothing references them any more after step 1, so nothing re-pins them). Verify `ollama ps`.
3. `sudo systemctl enable --now flash-next flash-next-health.timer` (after `install.sh` has run once).
   Wait for `curl -s localhost:8898/health` → `{"status":"ok"}` (~2 min).
4. Reverse tunnel spark → k2vps `:11439 → :8898` as a supervised unit like the `:11435` one
   (`~/.vps-tunnel.lock` flock pattern), NOT the bench script's ad-hoc tunnel.
5. Verify from the VPS: `curl 127.0.0.1:11439/v1/models` lists `qwen3.8-flash-next`; run one kanban
   card; check `health.json` updates every minute.

## Rollback (≤ 5 min, no downloads)

1. Restore the config backup on k2vps. 2. `sudo systemctl disable --now flash-next flash-next-health.timer`.
3. Reload ollama residents **120b first**, then 27b, then hermes3 (`curl :11434/api/generate {"model":…}`).
4. Verify `:11435` answers and `ollama ps` shows three. Everything flash-next stays on disk.

## Numbers the decision rests on (same instruments, this box)

| model / mode | code_c1 | edit | prose | cold prefill 20k tok | TTFT 20k |
|---|---:|---:|---:|---:|---:|
| gpt-oss:120b (ollama, lane today) | 57.1 | 51.6 | **66.0** | n/a | 2.6 s (short prompts) |
| qwen3.8:27b (ollama) | 37.5 | 41.2 | 18.4 | | |
| flash-next PR 28243 mtp3 @16k | 60.2 | 60.2 | 35.5 | 238 tok/s → **83 s** | |
| flash-next PR 28136 on-direct | | | | **594 tok/s → 35 s** | |
| **flash-next flash-prod (mtp3 + on-direct) @49k, 1 slot** | **60.3** | **59.0** | **34.5** | **560 tok/s → 42 s** (23.5k tok) | acceptance 0.657 |

Read: flash-next beats 120b on edit-shaped work (+16 %) and 27b everywhere; 120b is ~1.9× faster on
novel prose; direct PLE reads are what make a 20k-token card wait 35 s instead of 85–90 s.
MTP output is not bit-identical to non-spec output at temp 0 (equivalent quality on our probes).

## Open decisions (Ryan)

- Flip at all, and when (needs a quiet lane and ~15 min).
- Port: re-label 11439 as the pilot endpoint, or widen the sparklink fence by one port.
- `install.sh` needs sudo once (unit + sudoers line for the agent account).
- Kevin's box: DS4 stays; flash-next only ties it on copyable work. Separate call.
