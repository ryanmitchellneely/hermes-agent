#!/usr/bin/env bash
# DS4 liveness watchdog. Writes a heartbeat status file every tick
# REGARDLESS of outcome (register + heartbeat + surface + auto-alert —
# a missing/stale file must mean "watchdog itself is dead", never be
# confused with "service is fine, nothing to report").
#
# 2026-08-10: ds4.service was down 19h with nothing watching it — the
# systemd ExecStartPre gate silently failed every restart attempt after
# the D1 fork cutover. This script exists so that outage pattern can't
# recur unnoticed.
set -uo pipefail

STATUS_DIR="/var/lib/ds4-watchdog"
STATUS_FILE="${STATUS_DIR}/status.json"
STATUS_TMP="${STATUS_FILE}.tmp"
INTERVAL_S="${DS4_WATCHDOG_INTERVAL_S:-600}"

mkdir -p "${STATUS_DIR}"

now_iso="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
now_epoch="$(date +%s)"

svc_active="inactive"
if systemctl is-active --quiet ds4.service; then
  svc_active="active"
fi

http_code="000"
if [[ "${svc_active}" == "active" ]]; then
  http_code="$(curl -s -o /dev/null -m 5 -w '%{http_code}' http://127.0.0.1:8889/v1/models 2>/dev/null || echo 000)"
fi

if [[ "${svc_active}" == "active" && "${http_code}" == "200" ]]; then
  status="ok"
elif [[ "${svc_active}" == "active" ]]; then
  status="degraded"
else
  status="down"
fi

python3 - "$status" "$svc_active" "$http_code" "$now_iso" "$now_epoch" "$INTERVAL_S" "$STATUS_TMP" "$STATUS_FILE" <<'PYEOF'
import json
import sys

status, svc_active, http_code, now_iso, now_epoch, interval_s, tmp_path, final_path = sys.argv[1:9]
doc = {
    "system": "ds4",
    "status": status,
    "service_active": svc_active,
    "http_code": http_code,
    "fired_at": now_iso,
    "fired_at_epoch": int(now_epoch),
    "expected_interval_seconds": int(interval_s),
}
with open(tmp_path, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2)
    f.write("\n")
import os
os.replace(tmp_path, final_path)
PYEOF

if [[ "${status}" != "ok" ]]; then
  echo "ds4-watchdog: status=${status} service_active=${svc_active} http_code=${http_code}" >&2
  exit 1
fi
exit 0
