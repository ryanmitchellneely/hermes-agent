#!/usr/bin/env bash
# receipt helpers for t1000-reach — emit reach.receipt.v1 JSON on stdout.
# shellcheck shell=bash

_REACH_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# emit_receipt peer verb ok grade layer kind id [detail_json] [error_code] [error_message]
emit_receipt() {
  local peer="$1" verb="$2" ok="$3" grade="$4" layer="$5" kind="$6" rid="$7"
  # NOTE: do NOT write ${8:-{}} — bash parses the default `{}` as `{` + stray `}`,
  # which appends an extra } onto real JSON and breaks parsing.
  local detail_json="${8-}"
  [[ -n "$detail_json" ]] || detail_json='{}'
  local err_code="${9-}"
  local err_msg="${10-}"
  local df

  df="$(mktemp)"
  # shellcheck disable=SC2064
  trap "rm -f '$df'" RETURN
  printf '%s' "$detail_json" >"$df"

  local args=(
    python3 "$_REACH_LIB_DIR/emit_receipt.py"
    --peer "$peer"
    --verb "$verb"
    --ok "$ok"
    --grade "$grade"
    --layer "$layer"
    --kind "$kind"
    --rid "$rid"
    --detail-file "$df"
  )
  if [[ -n "$err_code" || -n "$err_msg" ]]; then
    args+=(--error-code "$err_code" --error-message "$err_msg")
  fi
  "${args[@]}"
}

reach_human() {
  printf '%s\n' "$*" >&2
}
