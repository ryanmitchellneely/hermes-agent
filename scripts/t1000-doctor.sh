#!/usr/bin/env bash
# Compatibility alias for the canonical Juice doctor.
set -euo pipefail

ROOT="${T1000_ROOT:-$HOME/Documents/T1000}"
exec "$ROOT/scripts/juice-doctor" "$@"
