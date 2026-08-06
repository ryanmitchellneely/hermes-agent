#!/usr/bin/env bash
# Install Mac heartbeat LaunchAgent (primary claim) — KeepAlive loop.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
DEST_DIR="$HOME/.t1000/failover"
mkdir -p "$DEST_DIR" "$HOME/.t1000/logs" "$HOME/Library/LaunchAgents"

cp "$ROOT/mac/heartbeat.sh" "$DEST_DIR/heartbeat.sh"
cp "$ROOT/mac/heartbeat-loop.sh" "$DEST_DIR/heartbeat-loop.sh"
chmod +x "$DEST_DIR/heartbeat.sh" "$DEST_DIR/heartbeat-loop.sh"

PLIST_DST="$HOME/Library/LaunchAgents/com.ryan.t1000-failover-heartbeat.plist"
cp "$ROOT/mac/com.ryan.t1000-failover-heartbeat.plist" "$PLIST_DST"
# Ensure paths point at home (not Documents — TCC)
/usr/libexec/PlistBuddy -c "Set :ProgramArguments:1 $DEST_DIR/heartbeat-loop.sh" "$PLIST_DST" 2>/dev/null || true

uid="$(id -u)"
launchctl bootout "gui/${uid}/com.ryan.t1000-failover-heartbeat" 2>/dev/null || true
launchctl bootstrap "gui/${uid}" "$PLIST_DST"
launchctl kickstart -k "gui/${uid}/com.ryan.t1000-failover-heartbeat" 2>/dev/null || true

"$DEST_DIR/heartbeat.sh" && echo "heartbeat: ok" || echo "heartbeat: FAILED"
echo "Mac heartbeat loop installed (KeepAlive, every 30s) via $DEST_DIR"
