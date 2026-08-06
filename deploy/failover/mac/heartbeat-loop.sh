#!/usr/bin/env bash
# Long-running heartbeat loop for launchd KeepAlive (StartInterval was only firing once).
#
# This side DECLARES, it does not arbitrate. It reports whether the Mac gateway is up
# (gw=) and whether the Mac wants to serve (want=), and it only ever starts or stops the
# Mac's own gateway. The VPS watchdog alone decides whether the standby runs.
#
# Self-fencing: heartbeat silence is what makes the VPS promote, but silence only means
# "this script cannot reach the VPS" — the Mac gateway may still be happily polling
# Telegram. That combination is the 2026-07-26 split brain: two gateways, both losing
# getUpdates every 22s. So after FENCE_AFTER_SEC of failed heartbeats, stop the Mac
# gateway here, which makes Mac silence actually mean Mac absence.
#
# Failback is a handshake, not a standoff. A fenced Mac keeps reporting want=primary; the
# watchdog stops the VPS in response; only then does the Mac start its gateway. An earlier
# version had the Mac wait for the VPS to go idle while the watchdog waited for the Mac to
# come up — each holding for the other, forever.
set -u
HB="${T1000_HEARTBEAT_SCRIPT:-$HOME/.t1000/failover/heartbeat.sh}"
INTERVAL="${T1000_HEARTBEAT_INTERVAL:-30}"
LOG="${T1000_FAILOVER_LOG:-$HOME/.t1000/logs/failover-heartbeat.log}"
FENCE_AFTER_SEC="${T1000_FENCE_AFTER_SEC:-120}"
SSH_HOST="${T1000_FAILOVER_SSH:-k2vps}"
SSH_KEY="${T1000_FAILOVER_SSH_KEY:-$HOME/.ssh/id_ed25519}"
GW_LABEL="ai.hermes.gateway"
GW_TARGET="gui/$(id -u)/${GW_LABEL}"
GW_PLIST="$HOME/Library/LaunchAgents/${GW_LABEL}.plist"
# One-shot operator request for the baton: `touch` it and the Mac asks for primary on the
# next beat, the watchdog stops the VPS, and only then does the Mac start its gateway.
# That ordering is why this exists — starting the Mac by hand while the VPS still holds
# Telegram is what produced the 22-second conflict loop.
WANT_FILE="${T1000_WANT_PRIMARY_FILE:-$HOME/.t1000/failover/want-primary}"
mkdir -p "$(dirname "$LOG")"

say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >>"$LOG"; }

gw_running() {
  launchctl print "$GW_TARGET" 2>/dev/null | grep -q 'state = running'
}

vps_gateway_active() {
  ssh -o BatchMode=yes -o ConnectTimeout=10 -o IdentitiesOnly=yes -i "$SSH_KEY" \
    "$SSH_HOST" 'systemctl is-active --quiet t1000-gateway.service' 2>/dev/null
}

start_gw() {
  # Two launchd traps, both of which produced a silent no-op start on 2026-07-26:
  #   - bootstrap returns "Input/output error" when the job is already loaded, so the
  #     kickstart must be unconditional rather than an || fallback;
  #   - `kickstart -k` means "kill the running instance first" and does not reliably
  #     start a job that is loaded but stopped — plain kickstart does.
  # Return codes lie here, so verify the job is actually up before reporting success.
  local i
  launchctl bootstrap "gui/$(id -u)" "$GW_PLIST" 2>/dev/null || true
  for i in 1 2 3; do
    launchctl kickstart "$GW_TARGET" 2>/dev/null || true
    sleep 2
    gw_running && return 0
  done
  say "ERROR could not start Mac gateway after 3 attempts"
  return 1
}

say "loop_start interval=${INTERVAL}s fence_after=${FENCE_AFTER_SEC}s script=${HB}"

down_since=0
fenced=0
while true; do
  # A gateway that is down because WE fenced it still wants primary back, as does one an
  # operator explicitly asked for. A gateway simply stopped by hand does not, and must
  # not fight the standby for the Telegram slot.
  want="standby"
  if gw_running || (( fenced == 1 )) || [[ -f "$WANT_FILE" ]]; then
    want="primary"
  fi

  if [[ -x "$HB" ]] && T1000_WANT_ROLE="$want" /bin/bash "$HB" \
       >>"${LOG%.log}.loop.out.log" 2>>"${LOG%.log}.loop.err.log"; then
    down_since=0
    if [[ "$want" == "primary" ]] && ! gw_running; then
      if vps_gateway_active; then
        say "WAIT_HANDOVER want=primary sent — waiting for the VPS to yield the Telegram slot"
      else
        say "TAKE_PRIMARY VPS has yielded — starting Mac gateway"
        start_gw
        fenced=0
        rm -f "$WANT_FILE" 2>/dev/null || true
      fi
    fi
  else
    [[ -x "$HB" ]] || say "FAIL missing $HB"
    now="$(date +%s)"
    (( down_since == 0 )) && down_since="$now"
    down_for=$(( now - down_since ))
    if (( fenced == 0 && down_for >= FENCE_AFTER_SEC )) && gw_running; then
      say "FENCE heartbeat down ${down_for}s >= ${FENCE_AFTER_SEC}s — stopping Mac gateway so the VPS can take over cleanly"
      launchctl bootout "$GW_TARGET" 2>/dev/null || true
      fenced=1
    fi
  fi
  sleep "$INTERVAL"
done
