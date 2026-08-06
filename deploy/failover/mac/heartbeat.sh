#!/usr/bin/env bash
# Mac primary heartbeat → VPS. Safe to run every 30s via LaunchAgent.
# Lives under ~/.t1000/failover so launchd is less likely to hit TCC on Documents/.
set -euo pipefail

SSH_HOST="${T1000_FAILOVER_SSH:-k2vps}"
REMOTE_DIR="${T1000_FAILOVER_DIR:-/var/lib/t1000-failover}"
LOG="${T1000_FAILOVER_LOG:-$HOME/.t1000/logs/failover-heartbeat.log}"
SSH_KEY="${T1000_FAILOVER_SSH_KEY:-$HOME/.ssh/id_ed25519}"
mkdir -p "$(dirname "$LOG")"

ts="$(date +%s)"
host="$(hostname -s 2>/dev/null || hostname)"
gw_state="unknown"
if launchctl print "gui/$(id -u)/ai.hermes.gateway" 2>/dev/null | grep -q 'state = running'; then
  gw_state="running"
else
  gw_state="stopped"
fi

# want= is INTENT, distinct from gw= which is current state. A Mac that fenced itself
# still wants the baton back (want=primary); a Mac an operator stopped does not
# (want=standby). The watchdog needs both to tell those apart.
want="${T1000_WANT_ROLE:-primary}"

payload="${ts} host=${host} gw=${gw_state} want=${want} role=mac-primary"

ssh_opts=(
  -o BatchMode=yes
  -o ConnectTimeout=10
  -o ServerAliveInterval=5
  -o IdentitiesOnly=yes
  -i "$SSH_KEY"
)


# Keep VPS standby auth/config fresh so failover can refresh xAI OAuth.
# Without this, promote succeeds but chat dies with invalid_grant (2026-08-06).
# IMPORTANT: do NOT sync on every auth.json mtime bump — gateway/PKCE rewrites
# auth often; that used to rsync every ~30s heartbeat (SSH hammer, 2026-08-06).
AUTH_STAMP="${T1000_AUTH_SYNC_STAMP:-$HOME/.t1000/failover/last-auth-sync}"
AUTH_INTERVAL_SEC="${T1000_AUTH_SYNC_INTERVAL_SEC:-900}"   # full refresh cadence
AUTH_MIN_GAP_SEC="${T1000_AUTH_SYNC_MIN_GAP_SEC:-300}"     # floor between syncs
sync_auth_if_due() {
  local now auth_m stamp_m age due=0
  now="$(date +%s)"
  auth_m=0
  [[ -f "$HOME/.t1000/auth.json" ]] && auth_m="$(stat -f %m "$HOME/.t1000/auth.json" 2>/dev/null || stat -c %Y "$HOME/.t1000/auth.json" 2>/dev/null || echo 0)"
  stamp_m=0
  [[ -f "$AUTH_STAMP" ]] && stamp_m="$(stat -f %m "$AUTH_STAMP" 2>/dev/null || stat -c %Y "$AUTH_STAMP" 2>/dev/null || echo 0)"
  if [[ ! -f "$AUTH_STAMP" ]]; then
    due=1
  else
    age=$(( now - stamp_m ))
    if (( age >= AUTH_INTERVAL_SEC )); then
      due=1
    elif (( auth_m > stamp_m && age >= AUTH_MIN_GAP_SEC )); then
      # auth changed since last sync, but respect min gap
      due=1
    fi
  fi
  if (( due )); then
    if rsync -az -e "ssh ${ssh_opts[*]}" \
      "$HOME/.t1000/auth.json" "$HOME/.t1000/config.yaml" \
      "${SSH_HOST}:/opt/t1000/home/" 2>>"$LOG"; then
      ssh "${ssh_opts[@]}" "$SSH_HOST" \
        'chown t1000:t1000 /opt/t1000/home/auth.json /opt/t1000/home/config.yaml
         chmod 600 /opt/t1000/home/auth.json /opt/t1000/home/config.yaml' 2>>"$LOG" || true
      mkdir -p "$(dirname "$AUTH_STAMP")"
      touch "$AUTH_STAMP"
      echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) auth_sync ok age=${age:-0}s" >>"$LOG"
    else
      echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) auth_sync FAIL" >>"$LOG"
    fi
  fi
}


if ssh "${ssh_opts[@]}" \
  "$SSH_HOST" \
  "umask 077; mkdir -p '$REMOTE_DIR' && printf '%s\n' '$payload' > '$REMOTE_DIR/heartbeat'"; then
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) ok $payload" >>"$LOG"
  sync_auth_if_due || true
  exit 0
fi

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) FAIL ssh $SSH_HOST" >>"$LOG"
exit 1
