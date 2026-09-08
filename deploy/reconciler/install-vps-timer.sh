#!/usr/bin/env bash
# Install juice-doctor-reconcile timer on the VPS (k2vps).
# Safe to re-run. Does NOT start t1000-gateway.
set -euo pipefail

ROOT="${T1000_ROOT:-$HOME/Documents/T1000}"
HOST="${T1000_VPS_HOST:-k2vps}"
REMOTE_SRC="${T1000_VPS_SRC:-/opt/t1000/src}"

echo "Syncing reconciler units + module to ${HOST}:${REMOTE_SRC} ..."
ssh -o BatchMode=yes "$HOST" "mkdir -p '${REMOTE_SRC}/deploy/reconciler' '${REMOTE_SRC}/hermes_cli' '${REMOTE_SRC}/scripts'"
rsync -az \
  "$ROOT/deploy/reconciler/" \
  "${HOST}:${REMOTE_SRC}/deploy/reconciler/"
rsync -az \
  "$ROOT/hermes_cli/reconciler.py" \
  "${HOST}:${REMOTE_SRC}/hermes_cli/reconciler.py"
rsync -az \
  "$ROOT/scripts/juice-doctor" \
  "${HOST}:${REMOTE_SRC}/scripts/juice-doctor"

echo "Installing systemd units ..."
ssh -o BatchMode=yes "$HOST" bash -s <<EOF
set -euo pipefail
SRC="${REMOTE_SRC}"
ls -la "\$SRC/deploy/reconciler/"
cp "\$SRC/deploy/reconciler/juice-doctor-reconcile.service" /etc/systemd/system/
cp "\$SRC/deploy/reconciler/juice-doctor-reconcile.timer" /etc/systemd/system/
# K2SharedKanban CLI: keep the safe (sudo -u t1000) form the only form on PATH.
if [ -f "\$SRC/deploy/k2kanban/k2kanban" ]; then
  install -m 0755 "\$SRC/deploy/k2kanban/k2kanban" /usr/local/bin/k2kanban
fi
mkdir -p /opt/t1000/home/reconciler
chown -R t1000:t1000 /opt/t1000/home/reconciler 2>/dev/null || true
chown -R t1000:t1000 "\$SRC/deploy/reconciler" "\$SRC/hermes_cli/reconciler.py" "\$SRC/scripts/juice-doctor" 2>/dev/null || true
chmod 644 "\$SRC/hermes_cli/reconciler.py" "\$SRC/deploy/reconciler/"*.yaml "\$SRC/deploy/reconciler/"*.service "\$SRC/deploy/reconciler/"*.timer "\$SRC/deploy/reconciler/"*.md 2>/dev/null || true
chmod 755 "\$SRC/scripts/juice-doctor" "\$SRC/deploy/reconciler/install-vps-timer.sh" 2>/dev/null || true
systemctl daemon-reload
systemctl enable --now juice-doctor-reconcile.timer
# Optional one-time HA hygiene: gateway must not be enabled-at-boot (watchdog owns lifecycle).
if systemctl is-enabled --quiet t1000-gateway.service 2>/dev/null; then
  echo "NOTE: disabling t1000-gateway at-boot (watchdog-owned lifecycle)"
  systemctl disable t1000-gateway.service || true
fi
systemctl start juice-doctor-reconcile.service || true
systemctl is-active juice-doctor-reconcile.timer
systemctl list-timers juice-doctor-reconcile.timer --no-pager || true
echo "--- reconciler one-shot ---"
env HERMES_HOME=/opt/t1000/home T1000_ROOT=/opt/t1000/src T1000_HOST_ROLE=vps \
  PYTHONPATH=/opt/t1000/src HERMES_RECONCILER_LIVE=1 \
  /opt/t1000/venv/bin/python -m hermes_cli.reconciler --fix --role vps 2>&1 | head -40 || true
echo
echo "OK: juice-doctor-reconcile.timer armed"
EOF
