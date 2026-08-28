#!/bin/bash
# Bench server on spark-b01b, LARGE CONTEXT variant — for the REAL dsh worker.
#
# WHY THIS EXISTS SEPARATELY from serve-b01b.sh: that script pins -c 16384 to
# match the ryan-spark runs exactly, and its comment says changing any flag makes
# the numbers incomparable. That pin is correct for the throughput bench and
# WRONG for the real harness: dsh sends ~18.8k tokens of system prompt + card
# before the model does any work, so at 16384 every real-worker run dies with
# CONTEXT_WINDOW_EXCEEDED before the model is even exercised.
#
# Numbers produced here are therefore NOT comparable to 65.3/90.1 (none) or
# 199/88.4 (ngram). This lane answers "can it run the harness at all", not
# "how fast".
MODEL=${1:-flashnext}
SPEC=${2:-none}
CTX=${3:-49152}
BIN=~/llama.cpp/build-qwen4exp/bin/llama-server
case "$MODEL" in
  120b)      M=~/models/gptoss120b/gpt-oss-120b-MXFP4.gguf; ALIAS=gpt-oss-120b ;;
  flashnext) M=~/models/flash-next-udq3/Qwen3.8-Flash-Next-UD-Q3_K_XL-00001-of-00003.gguf; ALIAS=qwen3.8-flash-next ;;
  *) echo "unknown model $MODEL" >&2; exit 2 ;;
esac
exec "$BIN" -m "$M" --host 0.0.0.0 --port 8898 -ngl 999 -c "$CTX" \
  --jinja -a "$ALIAS" --spec-type "$SPEC"
