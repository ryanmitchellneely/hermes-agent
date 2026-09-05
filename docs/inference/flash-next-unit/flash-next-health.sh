#!/bin/bash
# Heartbeat for the flash-next pilot (observability principle: register + heartbeat + surface + alert).
# Writes ~/models/flash-next/health.json every run; a stale or "down" file is the alert signal
# that the T1000 monitor / pulse reads (wire-up = t_37efebbb follow-up). Exit 1 on failure so the
# timer's failure state is visible in `systemctl list-timers` / journal too.
OUT=/home/ryanneely1000/models/flash-next/health.json
T=$(date -u +%FT%TZ)
if h=$(curl -s -m 8 http://127.0.0.1:8898/health) && echo "$h" | grep -q '"status":"ok"'; then
  m=$(curl -s -m 8 http://127.0.0.1:8898/metrics)
  acc=$(echo "$m" | awk '/^llamacpp:spec_decode_num_accepted_tokens_total/{a=$2} /^llamacpp:spec_decode_num_draft_tokens_total/{d=$2} END{if(d>0) printf "%.3f", a/d; else print "null"}')
  pred=$(echo "$m" | awk '/^llamacpp:tokens_predicted_total/{print $2}')
  printf '{"ts":"%s","status":"ok","port":8898,"tokens_predicted_total":%s,"mtp_acceptance_cumulative":%s}\n' "$T" "${pred:-0}" "${acc:-null}" > "$OUT"
  exit 0
else
  printf '{"ts":"%s","status":"down","port":8898}\n' "$T" > "$OUT"
  exit 1
fi
