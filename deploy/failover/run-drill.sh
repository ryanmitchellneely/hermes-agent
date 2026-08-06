#!/usr/bin/env bash
# Detached failover drill — must NOT run as a child of hermes gateway.
# Logs to ~/.t1000/logs/failover-drill-*.log
set -u
LOG="${HOME}/.t1000/logs/failover-drill-$(date +%Y%m%dT%H%M%S).log"
mkdir -p "$(dirname "$LOG")"
exec >>"$LOG" 2>&1
echo "=== DRILL START $(date -u +%Y-%m-%dT%H:%M:%SZ) pid=$$ ==="
uid=$(id -u)
SSH=(ssh -o BatchMode=yes -o ConnectTimeout=12 -o IdentitiesOnly=yes -i "$HOME/.ssh/id_ed25519" k2vps)

vps() { "${SSH[@]}" "$@"; }

# systemctl is-active prints "inactive" AND exits non-zero — never use
# `$(systemctl … || echo inactive)` or you get "inactive inactive" and shift fields.
vps_state_line() {
  vps 'gw=$(systemctl is-active t1000-gateway.service 2>/dev/null || true); case "$gw" in active|activating|deactivating) :;; *) gw=inactive;; esac; claim=$(cat /var/lib/t1000-failover/claimed_by 2>/dev/null || echo unknown); age=$(( $(date +%s) - $(awk "{print \$1}" /var/lib/t1000-failover/heartbeat 2>/dev/null || echo 0) )); echo "$gw $claim $age"'
}

echo "BASELINE"
mac_gw=$(launchctl print "gui/${uid}/ai.hermes.gateway" 2>&1 | awk -F'= ' '/state =/{print $2; exit}')
echo "mac_gw=$mac_gw"
base=$(vps_state_line || echo "ssh_fail unknown 999")
echo "vps_line=$base"
echo "vps_gw=$(echo "$base" | awk '{print $1}'); claim=$(echo "$base" | awk '{print $2}'); age=$(echo "$base" | awk '{print $3}')"

echo "STEP1 pause heartbeat + stop Mac gateway (exclusive VPS)"
launchctl bootout "gui/${uid}/com.ryan.t1000-failover-heartbeat" 2>/dev/null || true
# Prefer hermes CLI if available outside gateway context
if [[ -x "$HOME/Documents/T1000/venv/bin/hermes" ]]; then
  env HERMES_HOME="$HOME/.t1000" "$HOME/Documents/T1000/venv/bin/hermes" gateway stop 2>/dev/null || true
fi
launchctl bootout "gui/${uid}/ai.hermes.gateway" 2>/dev/null || true
sleep 3
mac_gw=$(launchctl print "gui/${uid}/ai.hermes.gateway" 2>&1 | awk -F'= ' '/state =/{print $2; exit}')
echo "mac_gw_after_stop=${mac_gw:-stopped}"

echo "STEP2 wait promote (max 240s)"
promoted=0
for i in $(seq 1 24); do
  out=$(vps_state_line || echo "ssh_fail unknown 999")
  echo "t+$((i*10))s $out"
  gw=$(echo "$out" | awk '{print $1}')
  if [[ "$gw" == "active" ]]; then promoted=1; echo PROMOTED; break; fi
  sleep 10
done
if [[ "$promoted" != "1" ]]; then
  echo "PROMOTE_TIMEOUT — dump"
  vps 'tail -20 /var/lib/t1000-failover/watchdog.log; systemctl status t1000-gateway --no-pager | head -30'
fi

echo "STEP3 restore Mac gateway + heartbeat; wait demote"
launchctl bootstrap "gui/${uid}" "$HOME/Library/LaunchAgents/ai.hermes.gateway.plist" 2>/dev/null || true
launchctl kickstart -k "gui/${uid}/ai.hermes.gateway" 2>/dev/null || true
if [[ -x "$HOME/Documents/T1000/venv/bin/hermes" ]]; then
  env HERMES_HOME="$HOME/.t1000" "$HOME/Documents/T1000/venv/bin/hermes" gateway start 2>/dev/null || true
fi
launchctl bootstrap "gui/${uid}" "$HOME/Library/LaunchAgents/com.ryan.t1000-failover-heartbeat.plist" 2>/dev/null || true
launchctl kickstart -k "gui/${uid}/com.ryan.t1000-failover-heartbeat" 2>/dev/null || true
sleep 2
/bin/bash "$HOME/.t1000/failover/heartbeat.sh" || true

demoted=0
for i in $(seq 1 18); do
  out=$(vps_state_line || echo "ssh_fail unknown 999")
  echo "recover+$((i*10))s $out"
  gw=$(echo "$out" | awk '{print $1}')
  claim=$(echo "$out" | awk '{print $2}')
  age=$(echo "$out" | awk '{print $3}')
  # gw must be inactive (not active); claim=mac; fresh HB
  if [[ "$gw" != "active" && "$claim" == "mac" && "${age:-999}" -lt 90 ]]; then
    demoted=1
    echo DEMOTED_OK
    break
  fi
  # keep heartbeats fresh during wait
  /bin/bash "$HOME/.t1000/failover/heartbeat.sh" || true
  sleep 10
done

echo "FINAL"
mac_gw=$(launchctl print "gui/${uid}/ai.hermes.gateway" 2>&1 | awk -F'= ' '/state =/{print $2; exit}')
hb=$(launchctl print "gui/${uid}/com.ryan.t1000-failover-heartbeat" 2>&1 | awk -F'= ' '/state =/{print $2; exit}')
echo "mac_gw=$mac_gw hb=$hb"
final=$(vps_state_line || echo "ssh_fail unknown 999")
echo "vps_line=$final"
echo "vps_gw=$(echo "$final" | awk '{print $1}'); claim=$(echo "$final" | awk '{print $2}'); age=$(echo "$final" | awk '{print $3}')"
vps 'tail -12 /var/lib/t1000-failover/watchdog.log'
echo "promoted=$promoted demoted=$demoted"
if [[ "$promoted" == "1" && "$demoted" == "1" ]]; then
  echo "RESULT=PASS"
else
  echo "RESULT=FAIL"
fi
echo "=== DRILL END $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo "$LOG" > "$HOME/.t1000/logs/failover-drill-latest.path"
