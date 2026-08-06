#!/usr/bin/env bash
# Honest not_implemented stub for peers not yet wired (A2+).
# shellcheck shell=bash
set -euo pipefail

REACH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../lib/receipt.sh
source "$REACH_ROOT/scripts/lib/receipt.sh"

stub_peer() {
  local peer="$1" verb="$2" layer="${3:-L0}" phase="${4:-pending}"
  local detail
  detail=$(PEER="$peer" VERB="$verb" PHASE="$phase" python3 - <<'PY'
import json, os
print(json.dumps({
    "implemented": False,
    "phase": os.environ["PHASE"],
    "hint": f"Peer '{os.environ['PEER']}' verb '{os.environ['VERB']}' not built yet — see references/SPEC.md",
}))
PY
)
  emit_receipt "$peer" "$verb" false error "$layer" none "-" "$detail" \
    not_implemented "Peer adapter not implemented yet ($phase)"
  return 1
}
