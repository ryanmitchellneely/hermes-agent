#!/usr/bin/env bash
# Offline behavioral test for watchdog.sh promote/demote/handover decisions.
# Stubs systemctl + flock (Linux-only) so nothing real is touched and it runs on the Mac.
#
# The two bugs these lock down both cost real outages on 2026-07-26:
#   - a fresh heartbeat with a stopped Mac gateway used to DEMOTE the standby, leaving
#     no gateway running anywhere;
#   - a fenced Mac and a holding watchdog each waited for the other, forever.
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
WD="$ROOT/vps/watchdog.sh"
TMP="$(mktemp -d)"
BIN="$TMP/bin"; mkdir -p "$BIN"

cat >"$BIN/systemctl" <<'STUB'
#!/usr/bin/env bash
case "$1" in
  is-active) [[ "${FAKE_ACTIVE:-0}" == "1" ]] && exit 0 || exit 3 ;;
  is-failed) [[ "${FAKE_FAILED:-0}" == "1" ]] && exit 0 || exit 1 ;;
  start|stop) echo "SYSTEMCTL_$1" >>"$FAKE_ACTIONS"; exit 0 ;;
  *) exit 0 ;;
esac
STUB
cat >"$BIN/flock" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
chmod +x "$BIN/systemctl" "$BIN/flock"

pass=0; fail=0
# run_case <name> <heartbeat line> <unit_active> <want|-> <must_not_contain|-> [prep]
run_case() {
  local name="$1" hb="$2" active="$3" want="$4" forbid="$5" prep="${6:-}"
  local dir="$TMP/c$RANDOM$RANDOM"; mkdir -p "$dir"
  printf '%s\n' "$hb" >"$dir/heartbeat"
  [[ -n "$prep" ]] && eval "$prep"
  export FAKE_ACTIONS="$dir/actions"; : >"$FAKE_ACTIONS"
  local out rc
  out="$(PATH="$BIN:$PATH" T1000_FAILOVER_DIR="$dir" FAKE_ACTIVE="$active" \
        PROMOTE_DELAY_SEC=0 bash "$WD" 2>&1)"; rc=$?
  local blob="$out$(cat "$dir/watchdog.log" 2>/dev/null)|$(tr '\n' ',' <"$FAKE_ACTIONS")"
  local ok=1
  (( rc == 0 )) || { ok=0; blob="$blob [EXIT=$rc]"; }
  [[ "$blob" == *"command not found"* ]] && ok=0
  [[ "$want"   != "-" && "$blob" != *"$want"*   ]] && ok=0
  [[ "$forbid" != "-" && "$blob" == *"$forbid"* ]] && ok=0
  if (( ok == 1 )); then
    echo "  PASS  $name"; pass=$((pass+1))
  else
    echo "  FAIL  $name"; echo "        want=[$want] forbid=[$forbid]"; echo "        got=$blob"
    fail=$((fail+1))
  fi
}

now=$(date +%s)
S=$((now-9999))   # stale
F=$now            # fresh

echo "== Mac unreachable =="
run_case "stale hb, standby down -> PROMOTE" "$S host=mac gw=running want=primary role=mac-primary" 0 "PROMOTE" -
run_case "stale hb, standby up   -> HOLD"    "$S host=mac gw=running want=primary role=mac-primary" 1 "HOLD_VPS" "SYSTEMCTL_start"

echo "== Mac serving =="
run_case "fresh gw=running, standby down -> quiet"  "$F host=mac gw=running want=primary role=mac-primary" 0 - "SYSTEMCTL_start"
run_case "fresh gw=running, standby up   -> DEMOTE" "$F host=mac gw=running want=primary role=mac-primary" 1 "DEMOTE" -

echo "== BUG 1: Mac not serving must never leave zero gateways =="
run_case "gw=stopped want=standby, standby down -> PROMOTE" \
  "$F host=mac gw=stopped want=standby role=mac-primary" 0 "PROMOTE" -
run_case "gw=stopped want=standby, standby up -> HOLD, never stop the only gateway" \
  "$F host=mac gw=stopped want=standby role=mac-primary" 1 "HOLD_VPS" "SYSTEMCTL_stop"

echo "== BUG 2: failback handshake must not deadlock =="
run_case "fenced Mac want=primary, standby up -> HANDOVER (VPS yields)" \
  "$F host=mac gw=stopped want=primary role=mac-primary" 1 "HANDOVER" -
run_case "fenced Mac want=primary, standby down -> quiet, let the Mac come up" \
  "$F host=mac gw=stopped want=primary role=mac-primary" 0 - "SYSTEMCTL_start"
run_case "handover grace expired -> take it back" \
  "$F host=mac gw=stopped want=primary role=mac-primary" 0 "PROMOTE" - \
  'printf "%s\n" "$((now-999))" >"$dir/handover_since"'

echo "== backward compatibility: a half-upgraded Mac must not be raced =="
run_case "no gw= field, standby up -> DEMOTE not PROMOTE" \
  "$F host=mac role=mac-primary" 1 "DEMOTE" "SYSTEMCTL_start"
run_case "no gw= field, standby down -> quiet" \
  "$F host=mac role=mac-primary" 0 - "SYSTEMCTL_start"

echo "== install race =="
run_case "no valid heartbeat -> never promote" "garbage line" 0 "NO_HEARTBEAT" "SYSTEMCTL_start"

echo "== promote aborts if the Mac resumes during the delay =="
d="$TMP/abort"; mkdir -p "$d"
printf '%s\n' "$S host=mac gw=running want=primary role=mac-primary" >"$d/heartbeat"
export FAKE_ACTIONS="$d/actions"; : >"$FAKE_ACTIONS"
( sleep 1; printf '%s\n' "$(date +%s) host=mac gw=running want=primary role=mac-primary" >"$d/heartbeat" ) &
out="$(PATH="$BIN:$PATH" T1000_FAILOVER_DIR="$d" FAKE_ACTIVE=0 PROMOTE_DELAY_SEC=3 bash "$WD" 2>&1; cat "$d/watchdog.log")"
wait
if [[ "$out" == *"ABORT_PROMOTE"* && "$(cat "$FAKE_ACTIONS")" != *"SYSTEMCTL_start"* ]]; then
  echo "  PASS  heartbeat resumes mid-delay -> ABORT_PROMOTE, no start"; pass=$((pass+1))
else
  echo "  FAIL  heartbeat resumes mid-delay -> ABORT_PROMOTE, no start"; echo "        got=$out"; fail=$((fail+1))
fi

echo "== handover state clears once the Mac is serving again =="
d2="$TMP/clear"; mkdir -p "$d2"
printf '%s\n' "$((now-50))" >"$d2/handover_since"
printf '%s\n' "$F host=mac gw=running want=primary role=mac-primary" >"$d2/heartbeat"
export FAKE_ACTIONS="$d2/actions"; : >"$FAKE_ACTIONS"
PATH="$BIN:$PATH" T1000_FAILOVER_DIR="$d2" FAKE_ACTIVE=0 PROMOTE_DELAY_SEC=0 bash "$WD" >/dev/null 2>&1
if [[ -f "$d2/handover_since" ]]; then
  echo "  FAIL  handover_since cleared when Mac serves"; fail=$((fail+1))
else
  echo "  PASS  handover_since cleared when Mac serves"; pass=$((pass+1))
fi

echo
echo "passed=$pass failed=$fail"
rm -rf "$TMP"
exit $(( fail > 0 ))
