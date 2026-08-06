#!/usr/bin/env bash
# Install repo-vendored t1000-reach into active HERMES_HOME (~/.t1000 by default).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.t1000}"
TARGET="$HERMES_HOME/skills/software-development/t1000-reach"
BIN_DIR="$HERMES_HOME/bin"
mkdir -p "$(dirname "$TARGET")" "$BIN_DIR"

if [[ -e "$TARGET" && ! -L "$TARGET" ]]; then
  stamp="$(date +%Y%m%d-%H%M%S)"
  bak="$TARGET.bak-$stamp"
  echo "Backing up existing non-symlink skill -> $bak"
  mv "$TARGET" "$bak"
fi

ln -sfn "$ROOT" "$TARGET"
ln -sfn "$TARGET/scripts/reach" "$BIN_DIR/reach"
chmod +x "$TARGET/scripts/reach" "$TARGET/scripts/peers"/*.sh "$TARGET/scripts/lib"/* 2>/dev/null || true

echo "Installed:"
echo "  skill: $TARGET -> $ROOT"
echo "  bin:   $BIN_DIR/reach"
"$BIN_DIR/reach" peers | head -40
