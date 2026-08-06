#!/usr/bin/env bash
# Install T1000 standby + failover watchdog on k2vps. Gateway stays STOPPED.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SSH_HOST="${T1000_FAILOVER_SSH:-k2vps}"
SRC_LOCAL="${T1000_SRC_LOCAL:-$HOME/Documents/T1000}"
HOME_LOCAL="${HERMES_HOME_LOCAL:-$HOME/.t1000}"

echo "==> [1/6] VPS user + dirs"
ssh "$SSH_HOST" bash -s <<'REMOTE'
set -euo pipefail
if ! id t1000 &>/dev/null; then
  useradd --system --home-dir /opt/t1000 --create-home --shell /usr/sbin/nologin t1000
fi
mkdir -p /opt/t1000/src /opt/t1000/home /opt/t1000/venv /var/lib/t1000-failover /etc/t1000
chown -R t1000:t1000 /opt/t1000 /var/lib/t1000-failover
chmod 755 /opt/t1000 /var/lib/t1000-failover
chmod 750 /etc/t1000
REMOTE

echo "==> [2/6] rsync source (excludes)"
rsync -az --delete \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude 'venv' \
  --exclude 'node_modules' \
  --exclude '__pycache__' \
  --exclude '.pytest_cache' \
  --exclude 'website/node_modules' \
  --exclude 'website/build' \
  --exclude 'apps/' \
  -e ssh \
  "$SRC_LOCAL/" "$SSH_HOST:/opt/t1000/src/"
ssh "$SSH_HOST" 'chown -R t1000:t1000 /opt/t1000/src'

echo "==> [3/6] rsync HERMES_HOME (secrets + config; no huge caches)"
rsync -az \
  --exclude 'logs/' \
  --exclude 'cache/' \
  --exclude 'audio_cache/' \
  --exclude 'image_cache/' \
  --exclude 'archives/' \
  --exclude 'bootstrap-cache/' \
  --exclude '*.lock' \
  --exclude 'gateway.pid' \
  --exclude 'gateway.lock' \
  -e ssh \
  "$HOME_LOCAL/" "$SSH_HOST:/opt/t1000/home/"
ssh "$SSH_HOST" 'chown -R t1000:t1000 /opt/t1000/home && chmod 700 /opt/t1000/home && chmod 600 /opt/t1000/home/.env /opt/t1000/home/auth.json 2>/dev/null || true'

echo "==> [4/6] venv + install hermes-agent"
ssh "$SSH_HOST" bash -s <<'REMOTE'
set -euo pipefail
export UV_PYTHON=3.12
if [[ ! -x /opt/t1000/venv/bin/python ]]; then
  uv venv /opt/t1000/venv --python 3.12
fi
chown -R t1000:t1000 /opt/t1000/venv
# install project into venv
sudo -u t1000 bash -lc 'cd /opt/t1000/src && uv pip install --python /opt/t1000/venv/bin/python -e .'
# smoke
sudo -u t1000 bash -lc 'HERMES_HOME=/opt/t1000/home /opt/t1000/venv/bin/python -c "import hermes_cli; print(\"hermes_cli_ok\", hermes_cli.__file__)"'
REMOTE

echo "==> [5/6] systemd units (gateway NOT enabled)"
scp -q \
  "$ROOT/vps/t1000-gateway.service" \
  "$ROOT/vps/t1000-failover-watchdog.service" \
  "$ROOT/vps/t1000-failover-watchdog.timer" \
  "$SSH_HOST:/etc/systemd/system/"
# watchdog script lives in tree
ssh "$SSH_HOST" bash -s <<'REMOTE'
set -euo pipefail
chmod +x /opt/t1000/src/deploy/failover/vps/watchdog.sh
# ensure gateway is stopped and disabled
systemctl daemon-reload
systemctl stop t1000-gateway.service 2>/dev/null || true
systemctl disable t1000-gateway.service 2>/dev/null || true
systemctl enable --now t1000-failover-watchdog.timer
systemctl start t1000-failover-watchdog.service || true
systemctl is-enabled t1000-failover-watchdog.timer
systemctl is-active t1000-gateway.service || echo "gateway inactive (good)"
# seed empty heartbeat so we don't immediately promote
if [[ ! -f /var/lib/t1000-failover/heartbeat ]]; then
  printf '%s host=install gw=unknown role=seed\n' "$(date +%s)" > /var/lib/t1000-failover/heartbeat
fi
REMOTE

echo "==> [6/6] done"
echo "VPS standby installed. Gateway is OFF until Mac heartbeats go stale."
echo "Next: ./install-mac.sh && ./status.sh"
