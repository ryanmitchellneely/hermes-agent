#!/usr/bin/env bash
# Launch T1000 native desktop (Electron + local Hermes backend).
set -euo pipefail

ROOT="${T1000_ROOT:-$HOME/Documents/T1000}"
export HERMES_HOME="${HERMES_HOME:-$HOME/.t1000}"
export HERMES_DESKTOP_HERMES_ROOT="$ROOT"
export HERMES_DESKTOP_PYTHON="${HERMES_DESKTOP_PYTHON:-$ROOT/venv/bin/python}"
export HERMES_DESKTOP_VARIANT="t1000"
export PATH="$ROOT/venv/bin:$PATH"
unset ELECTRON_RUN_AS_NODE

usage() {
  cat <<'EOF'
Usage: t1000-desktop.sh [--doctor | --install-user-launcher | --help]

  --doctor                 Run the T1000 readiness checks.
  --install-user-launcher  Install ~/.local/bin/t1000-desktop if that path is free.
  --help                   Show this help.
EOF
}

renderer_pid() {
  local pid
  command -v lsof >/dev/null 2>&1 || return 1
  pid=$(lsof -nP -tiTCP:5174 -sTCP:LISTEN 2>/dev/null | sed -n '1p')
  [[ -n "$pid" ]] || return 1
  printf '%s\n' "$pid"
}

renderer_is_owned() {
  local pid="$1"
  local cwd command_line
  cwd=$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | sed -n '1p')
  command_line=$(ps -p "$pid" -o command= 2>/dev/null || true)
  [[ "$cwd" == "$ROOT/apps/desktop" && "$command_line" == *vite* ]]
}

install_user_launcher() {
  local bin_dir="$HOME/.local/bin"
  local link="$bin_dir/t1000-desktop"
  local target="$ROOT/scripts/t1000-desktop.sh"

  if [[ -L "$link" && "$(readlink "$link")" == "$target" ]]; then
    echo "T1000 launcher already installed at $link"
    return 0
  fi
  if [[ -e "$link" || -L "$link" ]]; then
    echo "Refusing to replace existing launcher at $link" >&2
    return 1
  fi
  mkdir -p "$bin_dir"
  ln -s "$target" "$link"
  echo "Installed $link -> $target"
}

case "${1:-}" in
  "") ;;
  --doctor)
    exec "$ROOT/scripts/t1000-doctor.sh"
    ;;
  --install-user-launcher)
    install_user_launcher
    exit 0
    ;;
  --help|-h)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

if [[ ! -d "$ROOT/apps/desktop" ]]; then
  echo "T1000 desktop not found at $ROOT/apps/desktop" >&2
  exit 1
fi

if [[ ! -x "$HERMES_DESKTOP_PYTHON" ]]; then
  echo "T1000 venv missing. From $ROOT run: uv venv --python 3.12 venv && uv pip install -e . --python ./venv/bin/python" >&2
  exit 1
fi

if ! "$HERMES_DESKTOP_PYTHON" -c 'import yaml; import hermes_cli.main' >/dev/null; then
  echo "T1000 venv cannot import yaml and hermes_cli.main." >&2
  echo "Repair it from $ROOT with: uv pip install -e . --python ./venv/bin/python" >&2
  exit 1
fi

if [[ -s "$HOME/.nvm/nvm.sh" ]]; then
  # shellcheck disable=SC1090
  . "$HOME/.nvm/nvm.sh"
  nvm use 22 >/dev/null 2>&1 || true
fi

mkdir -p "$HERMES_HOME"

echo "T1000 desktop"
echo "  code:  $ROOT"
echo "  state: $HERMES_HOME"
echo "  python: $HERMES_DESKTOP_PYTHON"

cd "$ROOT/apps/desktop"
if active_pid=$(renderer_pid); then
  if renderer_is_owned "$active_pid"; then
    echo "T1000 renderer: already running (pid $active_pid); opening or focusing Electron"
    exec npm run dev:electron
  fi
  echo "Port 5174 is owned by another process (pid $active_pid); refusing to collide." >&2
  exit 1
fi

exec npm run dev
