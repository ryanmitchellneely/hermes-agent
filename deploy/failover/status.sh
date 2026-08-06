#!/usr/bin/env bash
# Show failover status on Mac + VPS.
set -euo pipefail
SSH_HOST="${T1000_FAILOVER_SSH:-k2vps}"

echo "======== MAC ========"
uid="$(id -u)"
echo -n "gateway LaunchAgent: "
if launchctl print "gui/${uid}/ai.hermes.gateway" 2>/dev/null | grep -q 'state = running'; then
  echo RUNNING
else
  echo stopped/missing
fi
echo -n "heartbeat LaunchAgent: "
if launchctl print "gui/${uid}/com.ryan.t1000-failover-heartbeat" 2>/dev/null | grep -q 'state = running\|state = active'; then
  echo loaded
  launchctl print "gui/${uid}/com.ryan.t1000-failover-heartbeat" 2>/dev/null | grep -E 'state =|runs =' | head -5
else
  # launchd interval agents may show differently
  launchctl print "gui/${uid}/com.ryan.t1000-failover-heartbeat" 2>&1 | head -15 || echo "not loaded"
fi
if [[ -f "$HOME/.t1000/logs/failover-heartbeat.log" ]]; then
  echo "last heartbeats:"
  tail -3 "$HOME/.t1000/logs/failover-heartbeat.log"
fi

echo
echo "======== VPS ========"
ssh -o BatchMode=yes -o ConnectTimeout=12 "$SSH_HOST" bash -s <<'REMOTE'
set -euo pipefail
echo -n "t1000-gateway: "
systemctl is-active t1000-gateway.service 2>/dev/null || echo inactive
echo -n "watchdog timer: "
systemctl is-active t1000-failover-watchdog.timer 2>/dev/null || echo inactive
echo "--- heartbeat file ---"
if [[ -f /var/lib/t1000-failover/heartbeat ]]; then
  cat /var/lib/t1000-failover/heartbeat
  raw=$(awk '{print $1}' /var/lib/t1000-failover/heartbeat)
  now=$(date +%s)
  if [[ "$raw" =~ ^[0-9]+$ ]]; then
    echo "age_sec=$(( now - raw ))"
  fi
else
  echo "(missing)"
fi
echo "claimed_by=$(cat /var/lib/t1000-failover/claimed_by 2>/dev/null || echo '?')"
echo "--- watchdog log (tail) ---"
tail -5 /var/lib/t1000-failover/watchdog.log 2>/dev/null || echo "(no log yet)"
echo "--- hermes home ---"
ls -la /opt/t1000/home/.env /opt/t1000/home/config.yaml 2>/dev/null || echo "home incomplete"
REMOTE
