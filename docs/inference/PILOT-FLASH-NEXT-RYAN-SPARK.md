# Qwen3.8-Flash-Next pilot on ryan-spark — what is staged, how to flip, how to roll back

**Status (2026-09-05 ~23:45Z):** FLIPPED (Ryan: "go!"). Supervision = cron+flock (no sudo yet); `unit/install.sh` upgrades it to systemd when Ryan runs it. Decision + evidence trail: models card `t_37efebbb`.
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
   - add provider `spark-flash`: `api: http://127.0.0.1:11439/v1`, `api_key: local`, `models: [qwen3.8-flash-next]`, `context_length: 65536` (Hermes refuses main-agent models under 64K)
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

1. Restore the config backup on k2vps AND every `profiles/*/config.yaml.bak-pre-flash-flip-*`. 2. `sudo systemctl disable --now flash-next flash-next-health.timer`.
3. Reload ollama residents **120b first**, then 27b, then hermes3 (`curl :11434/api/generate {"model":…}`).
4. Verify `:11435` answers and `ollama ps` shows three. Everything flash-next stays on disk.

## Numbers the decision rests on (same instruments, this box)

| model / mode | code_c1 | edit | prose | cold prefill 20k tok | TTFT 20k |
|---|---:|---:|---:|---:|---:|
| gpt-oss:120b (ollama, lane today) | 57.1 | 51.6 | **66.0** | n/a | 2.6 s (short prompts) |
| qwen3.8:27b (ollama) | 37.5 | 41.2 | 18.4 | | |
| flash-next PR 28243 mtp3 @16k | 60.2 | 60.2 | 35.5 | 238 tok/s → **83 s** | |
| flash-next PR 28136 on-direct | | | | **594 tok/s → 35 s** | |
| **flash-next flash-prod (mtp3 + on-direct) @65k, 1 slot** | **60.3** | **59.0** | **34.5** | **560 tok/s → 42 s** (23.5k tok) | acceptance 0.657 |

Read: flash-next beats 120b on edit-shaped work (+16 %) and 27b everywhere; 120b is ~1.9× faster on
novel prose; direct PLE reads are what make a 20k-token card wait 35 s instead of 85–90 s.
MTP output is not bit-identical to non-spec output at temp 0 (equivalent quality on our probes).

## Supervision (done 2026-09-06 00:3xZ, Ryan authorized)

- **cron + flock**, three lines in the ryanneely1000 crontab (backup `crontab.bak-*` in this dir):
  server (`*/2`, `CTX=65536 NP=1`, lock `~/.flash-next.lock`), reverse tunnel `:11439` (`*/2`, lock
  `~/.flash-tunnel.lock`), heartbeat (`* * * * *` → `health.json`). A crash or reboot recovers within 2 min.
- **Old ollama names removed** (`gpt-oss:120b`, `qwen3.8:27b`); the blobs live on as
  `gpt-oss-parked:120b` / `qwen38-parked:27b`. Nothing can load 64 GB beside the pilot any more.
- Upgrade path to systemd is still `sudo bash unit/install.sh` (remove the three cron lines afterwards).
- ⚠️ The server MUST be started under the same flock the cron line uses. A bare `nohup` server does
  not hold the lock, so cron launches a second copy that loads 90 GB before it finds the port taken.
  That nearly happened at 00:30Z; the fix is the cron line itself, run by hand.

## Profiles have their own provider tables (learned 2026-09-06 02:00Z)

`/opt/t1000/home/config.yaml` is NOT the only place provider `spark` lives. Every profile under
`/opt/t1000/home/profiles/*/config.yaml` (worker, orchestrator, k2, proof, sov, q38, flash, grok,
sonnet, mac-nail, dsh) carries its own `providers:` block. The kanban worker runs under the
`worker` profile, so the first live card 404'd at ollama `:11435` three times while the root
config already pointed at flash-next. All profiles are now flipped (backups
`config.yaml.bak-pre-flash-flip-*` next to each). **Rollback must restore the profile backups too.**

Second finding from the same card: after the `failure_limit` (2) local crashes the dispatcher
escalated the retry to `claude-acp / sonnet` on its own. A broken local lane therefore spends
frontier budget silently and can report a "success" that never touched the local model. Block
the card when that happens; the rule's home in config has not been located yet.

First real card on flash-next (t_37ce841e, 02:02–02:04Z): 85 s wall, 24.6k prompt tokens, 1.5k
generated, MTP acceptance 0.70, output correct and honest.

## Slots: NP=2, not 1 (measured 2026-09-06 03:00Z)

Under two concurrent worker cards on a single slot, every agent turn re-prefilled its whole
~25k-token context because the one KV cache thrashed between the two conversations: prompt tokens
climbed to 785k while generation stayed ~39k, `requests_deferred` sat at 1–3, and cards that take
1.5–5 min alone took 7–10 min. Two slots (`NP=2`, 65k each) give each conversation its own cache. **`CTX` is per-slot**: the serve
script passes `-c CTX*NP` because llama-server otherwise divides one `-c` across slots (the first NP=2
restart silently gave 2×32k, below the 64K the engine assumes).
Memory is fine: this architecture's KV is small (16k×4 slots and 65k×1 both sat at ~74 GB used).

## Alerting and the escalate gate (built 2026-09-06 04:00Z, gate verified live 04:16Z)

- **Alerting:** `k2vps:/opt/t1000/home/scripts/t1000_ops_alert_pulse.py` (Hermes cron, every 30 min,
  Telegram on change) checks `:11439/health` is ok, `:11439/v1/models` lists `qwen3.8-flash-next`
  (a bench window left on the tunnel would fail this), and `:11435` ollama for the hermes3 aux.
  It says CHANNEL (tunnel/box), SERVER (unhealthy), or WRONG-MODEL, pages once per distinct state,
  and sends a 🟢 recovery line. State: `cache/ops-alert-pulse-state.json` (`flash_next_checked_at`).
  The Spark-side `health.json` remains the local heartbeat; this is the reader it lacked.
- **Escalate gate:** `k2vps:/opt/t1000/home/scripts/kanban_model_escalate.py` (every 3 min) no
  longer promotes a LANE failure to a paid rung. Errors matching `infra_error_substrings`
  (http 404, model not found, connection refused, invalid_grant, token refresh failed, unknown
  provider, api call failed after, ...) HOLD the card where it is, print one HOLD line per task per
  6 h (cron stdout = Telegram), and log to `kanban/model_escalate_holds.json`. The stored failure
  error is generic (pid not alive / protocol violation); the lane error lives only in
  `boards/<b>/logs/<tid>.log`, so the gate sniffs that tail (v2). `unavailable_providers: [xai-oauth]`
  in `kanban/model_escalate.json` drops the grok rung until `hermes model` re-auth; the live ladder is
  sonnet → opus. Selftest 11/11. Verified live: a card pinned to a connection-refused lane crashed
  twice, parked `blocked`, and was HELD with 0 escalations. Both scripts live only under
  `/opt/t1000/home/scripts` (not the T1000 repo); patch scripts are kept in
  `docs/inference/flash-next-unit/` and backups sit beside each script.

## Alias cleanup (done 2026-09-06 04:22Z) and the estimator label (fixed 11:09Z)

All 142 live cards pinned to `gpt-oss:120b@spark` were re-pinned to `qwen3.8-flash-next@spark` via
`hermes kanban set-model` (one audit event each). The estimator's hardcoded
`_LOCAL_MODEL_PREFERENCE["spark"]` in `hermes_cli/kanban_estimate.py` now reads
`("qwen3.8-flash-next", "gpt-oss:120b", "hermes3:8b-16k")` (T1000 commit e51c342f4, gateway restarted,
verified: new cards estimate as `Spark · qwen3.8-flash-next`). The only remaining old-name references
are the chat-profile aliases in `config.yaml` (~L729–786), which resolve to flash-next by design.

## Residency heartbeat (VPS copy paused 2026-09-06 11:11Z)

The `Spark residency heartbeat` Hermes cron on k2vps (`5ad27bc2a170`) runs a Mac-designed tool
whose drift check needs `ssh` to the Spark; the VPS cannot reach the Spark, so it had self-failed
silently since deploy (`cache/spark-residency-state.json` → `boxes: {}`). Paused. ryan-spark
liveness is covered by the ops-pulse flash-next check above. The tool's source of truth is
`sovereign-consulting/tools/spark-residency` on the Mac (Ryan-write-only); its `manifest/ryan-spark.yaml`
still pins `gpt-oss:120b` and needs a rewrite for the pilot: pinned `hermes3:8b-16k` only; flash-next is a
llama.cpp server on `:8898`, not an ollama pin; `gpt-oss-parked:120b` / `qwen38-parked:27b` are
forbidden residents. That checkout also holds an unrelated, uncommitted nemotron-lane change from Aug 13.

## Open decisions and owed items (Ryan)

- Confirm the Telegram HOLD line arrived (~23:16 CDT Sep 5, "HOLD (lane failure, NOT escalated)").
- Re-authenticate xAI on k2vps (`hermes model` as t1000); then remove `xai-oauth` from
  `unavailable_providers` in `kanban/model_escalate.json`.
- Optional: `sudo bash ~/models/flash-next/unit/install.sh` to move supervision from cron to systemd
  (then delete the three cron lines).
- Kevin's box: DS4 stays (flash-next only ties it on copyable work). Say yes and the card closes.
- Rewrite `manifest/ryan-spark.yaml` in sovereign-consulting (see above).
- Unrelated, surfaced by the 03:30Z kernel auto-reboot: `sovereign-mc` crash-looping on missing
  Cloudflare Access env vars, `k2-ci-queue-monitor.service` failed after boot, and whether the
  unattended 03:30Z reboot window is acceptable for production k2-hub.
