#!/usr/bin/env bash
# VPS standby watchdog: promote/demote t1000-gateway from Mac heartbeats.
# Run as root via systemd timer.
#
# Division of authority (the thing that took two outages to get right):
#   The Mac DECLARES  — is it reachable, is its gateway up (gw=), does it want the
#                       baton back (want=). It never starts or stops the VPS.
#   This script DECIDES — whether the VPS gateway runs. It never starts or stops the
#                       Mac's gateway.
# Neither side waits on the other, so there is no split brain and no failback deadlock.
set -euo pipefail

STATE_DIR="${T1000_FAILOVER_DIR:-/var/lib/t1000-failover}"
FAIL_AFTER_SEC="${FAIL_AFTER_SEC:-180}"
RECOVER_AFTER_SEC="${RECOVER_AFTER_SEC:-90}"
PROMOTE_DELAY_SEC="${PROMOTE_DELAY_SEC:-25}"
HANDOVER_GRACE_SEC="${HANDOVER_GRACE_SEC:-120}"
UNIT="${T1000_GATEWAY_UNIT:-t1000-gateway.service}"
LOG="${STATE_DIR}/watchdog.log"
LOCK="${STATE_DIR}/watchdog.lock"

mkdir -p "$STATE_DIR"
exec 9>"$LOCK"
if ! flock -n 9; then
  exit 0
fi

log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a "$LOG" >/dev/null; }

field() { head -1 "$1" | tr ' ' '\n' | sed -n "s/^$2=//p" | head -1; }

hb_file="${STATE_DIR}/heartbeat"
now="$(date +%s)"
age=-1
have_hb=0
hb_gw="unknown"
hb_want="standby"
if [[ -f "$hb_file" ]]; then
  raw="$(head -1 "$hb_file" | awk '{print $1}')"
  g="$(field "$hb_file" gw)";   [[ -n "$g" ]] && hb_gw="$g"
  w="$(field "$hb_file" want)"; [[ -n "$w" ]] && hb_want="$w"
  if [[ "$raw" =~ ^[0-9]+$ ]]; then
    have_hb=1
    age=$(( now - raw ))
    if (( age < 0 )); then age=0; fi
  fi
fi

active=0
if systemctl is-active --quiet "$UNIT" 2>/dev/null; then
  active=1
fi

# Never promote without a prior valid Mac heartbeat (avoids install race).
if (( have_hb == 0 )); then
  log "NO_HEARTBEAT unit=$([[ $active -eq 1 ]] && echo active || echo inactive) — waiting for Mac"
  if (( active == 1 )); then
    log "DEMOTE no valid heartbeat while unit active — stopping $UNIT (safe default: Mac primary)"
    systemctl stop "$UNIT" || log "ERROR stop $UNIT failed"
    systemctl reset-failed "$UNIT" 2>/dev/null || true
    printf 'mac\n' >"${STATE_DIR}/claimed_by"
  fi
  exit 0
fi

# --- Decide whether the Mac is serving -------------------------------------
# A fresh heartbeat only proves the heartbeat script is alive. Only an explicit
# gw=stopped means the Mac is not serving; an absent gw= field (older heartbeat)
# is read as serving, so a half-upgraded Mac can never be raced into a split brain.
mac_fresh=0
(( age <= FAIL_AFTER_SEC )) && mac_fresh=1

mac_serving=0
if (( mac_fresh == 1 )) && [[ "$hb_gw" != "stopped" ]]; then
  mac_serving=1
fi

# The Mac fenced itself and wants the baton back. It cannot take it while the VPS
# still holds Telegram, so the VPS yields first — bounded, because a Mac that asks
# and then never comes up must not leave the standby down forever.
handover_file="${STATE_DIR}/handover_since"
mac_handover=0
if (( mac_fresh == 1 && mac_serving == 0 )) && [[ "$hb_want" == "primary" ]]; then
  if [[ -f "$handover_file" ]]; then
    hsince="$(head -1 "$handover_file" | awk '{print $1}')"
  else
    hsince="$now"
    printf '%s\n' "$now" >"$handover_file"
  fi
  if [[ "$hsince" =~ ^[0-9]+$ ]] && (( now - hsince < HANDOVER_GRACE_SEC )); then
    mac_handover=1
  else
    log "HANDOVER_EXPIRED mac asked for primary but never came up — taking it back"
  fi
else
  rm -f "$handover_file" 2>/dev/null || true
fi

want_vps=1
if (( mac_serving == 1 || mac_handover == 1 )); then
  want_vps=0
fi

# --- Act -------------------------------------------------------------------
if (( want_vps == 1 )); then
  if (( active == 0 )); then
    log "PROMOTE age=${age}s gw=${hb_gw} want=${hb_want} — delay ${PROMOTE_DELAY_SEC}s for Telegram release, then start $UNIT"
    if (( PROMOTE_DELAY_SEC > 0 )); then
      sleep "$PROMOTE_DELAY_SEC"
    fi
    # Re-check: the Mac may have recovered or resumed serving during the delay.
    now2="$(date +%s)"
    raw2="$(head -1 "$hb_file" | awk '{print $1}')"
    gw2="$(field "$hb_file" gw)"
    if [[ "$raw2" =~ ^[0-9]+$ ]] && (( now2 - raw2 <= FAIL_AFTER_SEC )) && [[ "$gw2" != "stopped" ]]; then
      log "ABORT_PROMOTE Mac serving again age=$(( now2 - raw2 ))s gw=${gw2:-unknown}"
      printf 'mac\n' >"${STATE_DIR}/claimed_by"
      exit 0
    fi
    systemctl reset-failed "$UNIT" 2>/dev/null || true
    # Stale locks from a previous hard kill block a clean takeover
    rm -f /opt/t1000/home/gateway.lock /opt/t1000/home/gateway.pid 2>/dev/null || true
    if systemctl start "$UNIT"; then
      log "PROMOTE_OK $UNIT started"
      printf 'vps\n' >"${STATE_DIR}/claimed_by"
      printf '%s\n' "$now2" >"${STATE_DIR}/promoted_at"
    else
      log "ERROR start $UNIT failed"
    fi
  else
    log "HOLD_VPS age=${age}s gw=${hb_gw} unit=active"
  fi
else
  if (( active == 1 )); then
    if (( mac_handover == 1 )); then
      log "HANDOVER age=${age}s want=primary — stopping $UNIT so the Mac can resume"
    else
      log "DEMOTE age=${age}s <= ${RECOVER_AFTER_SEC}s gw=${hb_gw} — stopping $UNIT (Mac primary)"
    fi
    systemctl stop "$UNIT" || log "ERROR stop $UNIT failed"
    systemctl reset-failed "$UNIT" 2>/dev/null || true
    printf 'mac\n' >"${STATE_DIR}/claimed_by"
    printf '%s\n' "$now" >"${STATE_DIR}/demoted_at"
  else
    systemctl reset-failed "$UNIT" 2>/dev/null || true
    printf 'mac\n' >"${STATE_DIR}/claimed_by"
    if (( age > 60 )); then
      log "STANDBY age=${age}s unit=inactive"
    fi
  fi
fi

exit 0
