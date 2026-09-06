# flash-next production window (systemd cutover) — harness t_83348309

Current state (2026-09-06): cron+flock supervision on ryan-spark, per
`docs/inference/PILOT-FLASH-NEXT-RYAN-SPARK.md` §"Supervision". Below is the
switch to systemd. Do this ON ryan-spark, Ryan-present (sudo).

## Install (once)
`sudo bash ~/models/flash-next/unit/install.sh` (mirrored at
`docs/inference/flash-next-unit/install.sh`) installs `flash-next.service` +
`flash-next-health.{service,timer}` to `/etc/systemd/system/`, reloads
systemd, and grants `ryanneely1000` passwordless
`systemctl {start,stop,restart,is-active} flash-next` +
`{start,stop} flash-next-health.timer`. Does not enable/start anything.

## Flip to systemd
```
sudo systemctl enable --now flash-next flash-next-health.timer
crontab -l > ~/models/flash-next/unit/crontab.bak-pre-systemd-$(date +%Y%m%dT%H%M%SZ)
crontab -e   # delete the 3 lines below (also in unit/flash-cron.txt)
```
Lines to delete (server / tunnel / heartbeat, `unit/flash-cron.txt`):
```
*/2 * * * * CTX=65536 NP=2 /usr/bin/flock -n $HOME/.flash-next.lock $HOME/models/flash-next/serve-udq3-mtp.sh prod >> $HOME/models/flash-next/flash-next.service.log 2>&1
*/2 * * * * /usr/bin/flock -n $HOME/.flash-tunnel.lock /usr/bin/ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=accept-new -i $HOME/.ssh/id_ed25519_k2vps -R 127.0.0.1:11439:127.0.0.1:8898 sparklink@177.7.37.126
* * * * * $HOME/models/flash-next/unit/flash-next-health.sh >/dev/null 2>&1
```

## Verify
```
# on ryan-spark
ss -ltn 'sport = :8898'; curl -s localhost:8898/health
systemctl is-active flash-next; systemctl is-active flash-next-health.timer
# from k2vps (tunnel stays cron-supervised, PILOT doc step 4 — not this flip)
curl -s 127.0.0.1:11439/health
curl -s 127.0.0.1:11439/v1/models   # lists qwen3.8-flash-next
```
## Rollback (≤5 min, no downloads)
```
sudo systemctl disable --now flash-next flash-next-health.timer
crontab ~/models/flash-next/unit/flash-cron.txt   # or splice the 3 lines back
```
Reload order (PILOT doc "Rollback"), **120b first** then 27b then hermes3:
```
curl :11434/api/generate -d '{"model":"gpt-oss:120b"}'
curl :11434/api/generate -d '{"model":"qwen3.8:27b"}'
curl :11434/api/generate -d '{"model":"hermes3:8b-16k"}'
ollama ps   # expect three residents
```
Also restore k2vps `config.yaml` + every `profiles/*/config.yaml.bak-pre-flash-flip-*`
(PILOT doc "Profiles have their own provider tables").

## Paging proof (systemd path only, briefly)
```
sudo systemctl stop flash-next
sudo -u t1000 env HERMES_HOME=/opt/t1000/home /opt/t1000/venv/bin/python3 \
  /opt/t1000/home/scripts/t1000_ops_alert_pulse.py
```
Expect `WARN flash-next completion: CHANNEL unreachable via :11439 tunnel`
(`_flashnext_liveness()`), then `sudo systemctl start flash-next` and re-run
the pulse — expect silence or a 🟢 recovery line (`_flash_next_liveness()`).
