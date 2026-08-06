#!/usr/bin/env bash
# Controlled Mac↔VPS failover drill for T1000 gateway.
# Usage: ./drill.sh [--fast]
#   --fast  FAIL_AFTER=90 RECOVER=45 (default production 180/90)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SSH_HOST="${T1000_FAILOVER_SSH:-k2vps}"
SSH_KEY="${T1000_FAILOVER_SSH_KEY:-$HOME/.ssh/id_ed25519}"
UID_NUM="$(id -u)"
GW_LABEL="gui/${UID_NUM}/ai.hermes.gateway"
HB_LABEL="gui/${UID_NUM}/com.ryan.t1000-failover-heartbeat"
REPORT="$HOME/.t1000/logs/failover-drill-$(date -u +%Y%m%dT%H%M%SZ).log"
mkdir -p "$(dirname "$REPORT")"

FAIL_AFTER=180
RECOVER=90
PROMOTE_DELAY=25
if [[ "${1:-}" == "--fast" ]]; then
  FAIL_AFTER=90
  RECOVER=45
  PROMOTE_DELAY=20
fi

ssh_c() {
  ssh -o BatchMode=yes -o ConnectTimeout=15 -o IdentitiesOnly=yes -i "$SSH_KEY" "$SSH_HOST" "$@"
}

log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a "$REPORT"; }

mac_state() {
  if launchctl print "$GW_LABEL" 2>/dev/null | grep -q 'state = running'; then echo running; else echo stopped; fi
}
hb_state() {
  if launchctl print "$HB_LABEL" 2>/dev/null | grep -q 'state = running'; then echo running; else echo stopped; fi
}

vps_snapshot() {
  ssh_c 'gw=$(systemctl is-active t1000-gateway.service 2>/dev/null || true)
    [[ "$gw" != "active" ]] && gw=inactive
    timer=$(systemctl is-active t1000-failover-watchdog.timer 2>/dev/null || echo inactive)
    claim=$(cat /var/lib/t1000-failover/claimed_by 2>/dev/null || echo missing)
    raw=$(awk "{print \$1}" /var/lib/t1000-failover/heartbeat 2>/dev/null || echo 0)
    now=$(date +%s); age=99999
    [[ "$raw" =~ ^[0-9]+$ ]] && age=$((now-raw))
    echo "gw=$gw timer=$timer claim=$claim age=$age"
  '
}

stop_mac_hb() {
  launchctl bootout "$HB_LABEL" 2>/dev/null || true
}
start_mac_hb() {
  # `kickstart -k` kills-then-restarts and does NOT reliably start a loaded-but-stopped
  # job; plain kickstart does. Both verbs return 0 either way, so retry until it is up.
  local plist="$HOME/Library/LaunchAgents/com.ryan.t1000-failover-heartbeat.plist" i
  launchctl bootstrap "gui/${UID_NUM}" "$plist" 2>/dev/null || true
  for i in 1 2 3; do
    launchctl kickstart "$HB_LABEL" 2>/dev/null || true
    sleep 2
    [[ "$(hb_state)" == running ]] && return 0
  done
  return 1
}
stop_mac_gw() {
  launchctl bootout "$GW_LABEL" 2>/dev/null || true
  # also try hermes stop if lock remains
  sleep 2
}
start_mac_gw() {
  local plist="$HOME/Library/LaunchAgents/ai.hermes.gateway.plist" i
  launchctl bootstrap "gui/${UID_NUM}" "$plist" 2>/dev/null || true
  for i in 1 2 3; do
    launchctl kickstart "$GW_LABEL" 2>/dev/null || true
    sleep 2
    [[ "$(mac_state)" == running ]] && return 0
  done
  return 1
}

set_thresholds() {
  local fa="$1" rc="$2" pd="$3"
  ssh_c "mkdir -p /etc/systemd/system/t1000-failover-watchdog.service.d
cat > /etc/systemd/system/t1000-failover-watchdog.service.d/thresholds.conf <<EOF
[Service]
Environment=FAIL_AFTER_SEC=${fa}
Environment=RECOVER_AFTER_SEC=${rc}
Environment=PROMOTE_DELAY_SEC=${pd}
EOF
systemctl daemon-reload
systemctl restart t1000-failover-watchdog.timer
"
}

restore_thresholds() {
  ssh_c 'rm -f /etc/systemd/system/t1000-failover-watchdog.service.d/thresholds.conf
    rmdir /etc/systemd/system/t1000-failover-watchdog.service.d 2>/dev/null || true
    systemctl daemon-reload
    systemctl restart t1000-failover-watchdog.timer
  ' || true
}

pass=0
fail=0
assert() {
  local name="$1" cond="$2"
  if eval "$cond"; then
    log "PASS $name"
    pass=$((pass+1))
  else
    log "FAIL $name"
    fail=$((fail+1))
  fi
}

cleanup() {
  log "CLEANUP restore thresholds + ensure Mac primary"
  restore_thresholds || true
  # ensure VPS down
  ssh_c 'systemctl stop t1000-gateway.service 2>/dev/null || true; systemctl reset-failed t1000-gateway.service 2>/dev/null || true; printf mac > /var/lib/t1000-failover/claimed_by' || true

  # Restore must be VERIFIED, not merely attempted. On 2026-07-26 a drill timed out in
  # phase 2, ran this trap, and left the Mac down for an hour — because kickstart can
  # return 0 while the job is still not running a few seconds later. Retry, then say so
  # unmistakably if the Mac never came back, since this trap also runs on the failure
  # path where nobody is watching the assertions.
  local i
  for i in 1 2 3 4 5 6; do
    [[ "$(mac_state)" == running ]] || start_mac_gw || true
    [[ "$(hb_state)"  == running ]] || start_mac_hb || true
    sleep 5
    if [[ "$(mac_state)" == running && "$(hb_state)" == running ]]; then
      break
    fi
    log "CLEANUP retry $i: mac_gw=$(mac_state) mac_hb=$(hb_state)"
  done
  "$HOME/.t1000/failover/heartbeat.sh" 2>/dev/null || true

  if [[ "$(mac_state)" == running && "$(hb_state)" == running ]]; then
    log "CLEANUP_OK mac_gw=running mac_hb=running"
  else
    log "CLEANUP_FAILED mac_gw=$(mac_state) mac_hb=$(hb_state) — THE MAC IS NOT PRIMARY."
    log "CLEANUP_FAILED fix by hand: launchctl kickstart -k $GW_LABEL && launchctl kickstart -k $HB_LABEL"
  fi
}
trap cleanup EXIT

log "=== T1000 failover drill start fail_after=${FAIL_AFTER} recover=${RECOVER} ==="
log "BASELINE mac_gw=$(mac_state) hb=$(hb_state) $(vps_snapshot)"

# 0) sync secrets
log "SYNC auth/env/config → VPS"
rsync -az -e "ssh -o BatchMode=yes -i $SSH_KEY" \
  "$HOME/.t1000/.env" "$HOME/.t1000/auth.json" "$HOME/.t1000/config.yaml" \
  "${SSH_HOST}:/opt/t1000/home/"
ssh_c 'chown t1000:t1000 /opt/t1000/home/.env /opt/t1000/home/auth.json /opt/t1000/home/config.yaml
  chmod 600 /opt/t1000/home/.env /opt/t1000/home/auth.json /opt/t1000/home/config.yaml'

# deploy latest unit/watchdog
log "DEPLOY unit+watchdog"
scp -q -i "$SSH_KEY" \
  "$ROOT/vps/t1000-gateway.service" \
  "$ROOT/vps/watchdog.sh" \
  "$ROOT/vps/t1000-failover-watchdog.service" \
  "$ROOT/vps/t1000-failover-watchdog.timer" \
  "${SSH_HOST}:/tmp/"
ssh_c 'cp /tmp/t1000-gateway.service /etc/systemd/system/
  cp /tmp/t1000-failover-watchdog.service /etc/systemd/system/
  cp /tmp/t1000-failover-watchdog.timer /etc/systemd/system/
  cp /tmp/watchdog.sh /opt/t1000/src/deploy/failover/vps/watchdog.sh
  chmod +x /opt/t1000/src/deploy/failover/vps/watchdog.sh
  systemctl daemon-reload
  systemctl enable --now t1000-failover-watchdog.timer
  systemctl stop t1000-gateway.service 2>/dev/null || true
  systemctl reset-failed t1000-gateway.service 2>/dev/null || true
'

set_thresholds "$FAIL_AFTER" "$RECOVER" "$PROMOTE_DELAY"
log "THRESHOLDS fail=${FAIL_AFTER} recover=${RECOVER} promote_delay=${PROMOTE_DELAY}"

# 1) Mac down
log "STEP1 stop Mac heartbeat + gateway (avoid dual poll)"
stop_mac_hb
stop_mac_gw
sleep 3
assert "mac_gw_stopped" "[[ \"\$(mac_state)\" == stopped ]]"
assert "mac_hb_stopped" "[[ \"\$(hb_state)\" == stopped ]]"

# Force stale heartbeat immediately so we don't wait wall-clock only on age of last beat
# (last beat may be fresh seconds ago — advance clock by writing old ts)
log "STEP2 stale heartbeat age>${FAIL_AFTER}"
ssh_c "old=\$(( \$(date +%s) - ${FAIL_AFTER} - 10 )); printf '%s host=drill gw=stopped role=stale\\n' \"\$old\" > /var/lib/t1000-failover/heartbeat"

# 2) wait promote
log "STEP3 wait for VPS promote (max $((FAIL_AFTER + PROMOTE_DELAY + 120))s)"
deadline=$(( $(date +%s) + FAIL_AFTER + PROMOTE_DELAY + 120 ))
promoted=0
while (( $(date +%s) < deadline )); do
  snap=$(vps_snapshot)
  log "  poll $snap"
  if [[ "$snap" == *"gw=active"* ]]; then
    promoted=1
    break
  fi
  sleep 10
done
assert "vps_promoted" "[[ $promoted -eq 1 ]]"
claim=$(ssh_c 'cat /var/lib/t1000-failover/claimed_by')
assert "claim_vps" "[[ \"$claim\" == vps ]]"

# health: process up 20s, journal not immediate crash
sleep 25
snap=$(vps_snapshot)
log "POST_PROMOTE $snap"
assert "vps_still_active" "[[ \"$snap\" == *gw=active* ]]"
# Telegram: look for conflict storms vs connected
tg=$(ssh_c 'journalctl -u t1000-gateway.service -n 40 --no-pager 2>/dev/null | tail -20')
log "VPS_JOURNAL_TAIL:"
echo "$tg" | tee -a "$REPORT" >/dev/null
if echo "$tg" | grep -qi 'Gateway Starting\|connected\|Telegram'; then
  log "PASS vps_journal_alive"
  pass=$((pass+1))
else
  log "FAIL vps_journal_alive"
  fail=$((fail+1))
fi

# 3) Mac back — through the production handshake, not by grabbing the slot. Starting the
# Mac gateway while the VPS still holds Telegram is a deliberate dual-poll window, and
# that window IS the outage this design exists to prevent. Ask for primary, let the
# watchdog yield, and the heartbeat loop starts the gateway once the slot is free. A
# drill that restores differently from production has not rehearsed production.
log "STEP4 restore Mac via the want-primary handshake"
start_mac_hb || true
sleep 2
assert "mac_hb_running" "[[ \"\$(hb_state)\" == running ]]"
touch "$HOME/.t1000/failover/want-primary"
log "  requested primary — waiting for the VPS to yield and the Mac to take over"
deadline=$(( $(date +%s) + RECOVER + 150 ))
took=0
while (( $(date +%s) < deadline )); do
  if [[ "$(mac_state)" == running ]] && [[ "$(vps_snapshot)" == *"gw=inactive"* ]]; then
    took=1
    break
  fi
  sleep 5
done
assert "mac_took_primary" "[[ $took -eq 1 ]]"
assert "mac_gw_running" "[[ \"\$(mac_state)\" == running ]]"

log "STEP5 wait for VPS demote (max $((RECOVER + 120))s)"
deadline=$(( $(date +%s) + RECOVER + 120 ))
demoted=0
while (( $(date +%s) < deadline )); do
  snap=$(vps_snapshot)
  log "  poll $snap"
  if [[ "$snap" == *"gw=inactive"* && "$snap" == *"claim=mac"* ]]; then
    demoted=1
    break
  fi
  # keep heartbeats fresh
  "$HOME/.t1000/failover/heartbeat.sh" 2>/dev/null || true
  sleep 8
done
assert "vps_demoted" "[[ $demoted -eq 1 ]]"

sleep 5
final=$(vps_snapshot)
log "FINAL mac_gw=$(mac_state) hb=$(hb_state) $final"
assert "final_mac_gw" "[[ \"\$(mac_state)\" == running ]]"
assert "final_vps_inactive" "[[ \"$final\" == *gw=inactive* ]]"
assert "final_claim_mac" "[[ \"$final\" == *claim=mac* ]]"
age_n=$(echo "$final" | sed -n 's/.*age=\([0-9]*\).*/\1/p')
assert "final_age_fresh" "[[ \"${age_n:-999}\" -lt 90 ]]"

log "=== RESULT pass=$pass fail=$fail report=$REPORT ==="
if (( fail > 0 )); then
  exit 1
fi
exit 0
