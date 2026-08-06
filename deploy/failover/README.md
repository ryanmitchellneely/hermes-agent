# T1000 Mac-primary / VPS-standby failover

**Goal:** Telegram gateway + crons prefer the Mac when healthy; VPS takes over only when Mac heartbeats stop.

**Hard rule:** only one host runs `t1000-gateway` at a time.

## Topology

| Host | Role |
|------|------|
| Mac (`ai.hermes.gateway` LaunchAgent) | **Primary** when sending heartbeats |
| VPS `k2vps` (`t1000-gateway.service`) | **Standby** until failover |
| Heartbeat file | `/var/lib/t1000-failover/heartbeat` (unix epoch seconds) |
| Shared secret | `/etc/t1000/failover.env` → `FAILOVER_TOKEN` |

## Thresholds

| Constant | Default | Meaning |
|----------|---------|---------|
| `FAIL_AFTER_SEC` | 180 | No heartbeat → promote VPS |
| `RECOVER_AFTER_SEC` | 90 | Fresh heartbeats while VPS active → demote VPS |
| Heartbeat interval (Mac) | 30s | LaunchAgent `StartInterval` |

## Components

### Mac
- `mac/heartbeat.sh` — SSH to VPS, write heartbeat + gateway state
- `mac/heartbeat-loop.sh` — KeepAlive loop (every 30s); StartInterval alone only fired once on macOS
- LaunchAgent `com.ryan.t1000-failover-heartbeat.plist` → **`~/.t1000/failover/`** (not Documents — TCC blocks Documents)

### VPS
- `vps/watchdog.sh` — read heartbeat age; `systemctl start/stop t1000-gateway`
- `vps/t1000-gateway.service` — Hermes gateway (disabled by default)
- `vps/t1000-failover-watchdog.service` + `.timer` — every 30s
- `HERMES_HOME=/opt/t1000/home`
- Code: `/opt/t1000/src` (rsync from Mac `Documents/T1000`)
- Venv: `/opt/t1000/venv`

## Install (operator)

### One-time VPS
```bash
# from Mac
cd ~/Documents/T1000/deploy/failover
./install-vps.sh          # creates user, dirs, rsync, venv, units (gateway OFF)
```

### One-time Mac
```bash
./install-mac.sh          # installs LaunchAgent heartbeat
```

### Verify
```bash
./status.sh               # both sides
# Simulate failover (careful — will stop Mac gateway ownership):
# stop Mac heartbeat + gateway, wait 3+ min, VPS should start
```

## Failover behavior

1. Mac alive → heartbeat fresh → VPS ensures `t1000-gateway` **stopped**
2. Mac dead/sleep/offline → heartbeat stale > 180s → VPS **starts** gateway
3. Mac returns → heartbeats resume for > 90s → VPS **stops** gateway; Mac LaunchAgent already running primary

## What does NOT fail over
- Buzz Desktop as Ryan (owner identity)
- Chrome Google profiles / GA4 UI
- macOS computer-use

## Secrets
Copy once: `~/.t1000/.env`, `auth.json`, `config.yaml` → `/opt/t1000/home/` (mode 600, user `t1000`).  
Never commit. `install-vps.sh` rsyncs with exclusions for caches.
