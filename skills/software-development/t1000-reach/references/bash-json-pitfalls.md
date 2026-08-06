# Bash + JSON pitfalls (reach mesh)

Hard-won 2026-08-03 while shipping A0/A1.

## 1. `${var:-{}}` appends a stray `}`

```bash
# BROKEN — bash ends the expansion at the first `}` inside the default
local detail_json="${8:-{}}"
# When $8 is set to '{"a":1}', result becomes '{"a":1}' + '}'  → invalid JSON
# When $8 is unset, you luckily get '{}' ( { + } ), which hides the bug
```

**Fix:**

```bash
local detail_json="${8-}"
[[ -n "$detail_json" ]] || detail_json='{}'
```

Same class of bug: any `${name:-{...}}` default that itself contains `}`.

## 2. Don’t put receipt JSON only in environment variables

Large or quote-heavy JSON in `ENV=... python -` can silently degrade. Prefer:

```bash
df="$(mktemp)"
printf '%s' "$detail_json" >"$df"
python3 "$REACH_LIB/emit_receipt.py" --detail-file "$df" ...
rm -f "$df"
```

Canonical helper: `scripts/lib/emit_receipt.py` + `scripts/lib/receipt.sh::emit_receipt`.

## 3. Symlink-safe `REACH_ROOT`

```bash
_REACH_SRC="${BASH_SOURCE[0]}"
while [[ -L "$_REACH_SRC" ]]; do
  _link="$(readlink "$_REACH_SRC")"
  if [[ "$_link" == /* ]]; then _REACH_SRC="$_link"
  else _REACH_SRC="$(cd "$(dirname "$_REACH_SRC")" && pwd)/$_link"; fi
done
REACH_ROOT="$(cd "$(dirname "$_REACH_SRC")/.." && pwd)"
```

Without this, `~/.t1000/bin/reach` → `~/.t1000/scripts/lib/receipt.sh` (missing).

## 4. Smoke that would have caught #1

```bash
~/.t1000/bin/reach spark status | python3 -c \
  'import sys,json;d=json.load(sys.stdin);assert d.get("detail");assert d["detail"].get("models")'
```

Empty `detail: {}` with `ok: true` is a **parser bug**, not a healthy peer.

## 5. Never put remote Python inside `ssh "…"` when the script has `"`

Hard-won 2026-08-04 shipping A5 Popper.

```bash
# BROKEN at *parse* time — bash treats the outer "…" as one double-quoted
# string; every " inside the Python body ends/reopens it →
#   unexpected EOF while looking for matching `"'
ssh "$HOST" "python3 - <<'PY'
print({\"ok\": True})   # the \" here kills the outer quote
PY"
```

Single-quoted heredoc (`<<'PY'`) does **not** save you if the heredoc is nested inside an outer `ssh "…"`.

**Canonical fix (use for any VPS peer with non-trivial remote Python):**

```bash
ssh -o BatchMode=yes -o ConnectTimeout=15 "$HOST" bash -s \
  -- "$ARG1" "$ARG2" <<'REMOTE' 2>/dev/null || echo '{"error":"ssh_failed"}'
set -euo pipefail
export FOO="$1"
export BAR="$2"
python3 - <<'PY'
import json, os
print(json.dumps({"foo": os.environ["FOO"], "ok": True}))
PY
REMOTE
```

- Local shell owns the outer heredoc → quote-safe.
- Remote `bash -s` gets script on stdin; args after `--` become `$1..$n`.
- Prefer this over pulp-era `ssh "… python3 - <<'PY' … PY\""` once the remote body needs double quotes.

**When building a new peer adapter:** default to `bash -s <<'REMOTE'`. Only use inline `ssh "short command"` for one-liners with no nested `"`.
