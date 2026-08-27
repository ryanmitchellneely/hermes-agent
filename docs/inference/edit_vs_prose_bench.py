#!/usr/bin/env python3
"""Edit-shaped vs prose A/B — measure whether a build exploits output copyability.

WHY: SIG-20260826-06 reports Flash-Next at 97.4 tok/s on "reproduce file, one
change" (94.7% ngram accept) but 22.1 tok/s on prose (5.8% accept). Acceptance
tracking copyability is the signature of CONTEXT-COPYING speculation, not a
neural draft head. This measures the same spread on our own hardware.

DESIGN — the two cases are matched so copyability is the only variable:
  - identical file in the prompt (identical prefill)
  - comparable output length (the file is ~the same size as the asked prose)
  - only difference: EDIT's output is ~entirely copyable from context,
    CONTROL's output cannot be copied at all.

Hypothesis: if our build has no context-copy speculation, edit ~= prose tok/s,
and Bakeer's 97 requires a mechanism we do not have. Both outcomes inform.

VALIDITY GUARD: a model that shortcuts the edit case ("unchanged, see above")
would post a fast tok/s for a task it did not do. We assert the edit output
actually contains the file's structure AND the requested change.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FILE_UNDER_EDIT = '''\
import json
from pathlib import Path


DEFAULT_TIMEOUT = 30


class LedgerStore:
    """Append-only JSONL store for run receipts."""

    def __init__(self, path: Path, timeout: int = DEFAULT_TIMEOUT):
        self.path = Path(path)
        self.timeout = timeout
        self._cache: list[dict] = []

    def append(self, row: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as fh:
            fh.write(json.dumps(row) + "\\n")
        self._cache.append(row)

    def load(self) -> list[dict]:
        if not self.path.exists():
            return []
        rows = []
        for line in self.path.read_text().splitlines():
            if line.strip():
                rows.append(json.loads(line))
        self._cache = rows
        return rows

    def latest(self, n: int = 10) -> list[dict]:
        return self.load()[-n:]
'''

EDIT_PROMPT = (
    "Here is a Python file:\n\n```python\n" + FILE_UNDER_EDIT + "```\n\n"
    "Output the ENTIRE file again, unchanged except for one thing: change "
    "DEFAULT_TIMEOUT from 30 to 60. Output the complete file in a single "
    "```python fence. No commentary, no ellipsis, no 'unchanged' shorthand — "
    "every line must be present."
)

CONTROL_PROMPT = (
    "Here is a Python file:\n\n```python\n" + FILE_UNDER_EDIT + "```\n\n"
    # Length is tuned to land near the edit case's ~230 completion tokens:
    # decode rate drifts slightly with KV growth, so a 3x longer control
    # would confound the copyability comparison it exists to isolate.
    "Do NOT reproduce or quote the file. Write a single paragraph of about "
    "160 words of original prose on the design tradeoffs of append-only JSONL "
    "stores versus SQLite for run receipts: durability, concurrent writers, "
    "and schema evolution. Plain prose only, no code, no bullet points, no "
    "quoting of any identifier from the file. Stop at one paragraph."
)


def stream_chat(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    payload = dict(payload)
    payload["stream"] = True
    payload.setdefault("stream_options", {"include_usage": True})
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )
    t0 = time.perf_counter()
    t_first = None
    chunks: list[str] = []
    usage: dict[str, Any] = {}
    finish = None
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        while True:
            line = resp.readline()
            if not line:
                break
            s = line.decode("utf-8", "replace").strip()
            if not s or s.startswith(":"):
                continue
            if s.startswith("data:"):
                s = s[5:].strip()
            if s == "[DONE]":
                break
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                continue
            if obj.get("usage"):
                usage = obj["usage"]
            choices = obj.get("choices") or []
            if not choices:
                continue
            c = (choices[0].get("delta") or {}).get("content")
            if isinstance(c, str) and c:
                if not chunks:
                    t_first = time.perf_counter()
                chunks.append(c)
            finish = choices[0].get("finish_reason") or finish
    total_s = time.perf_counter() - t0
    text = "".join(chunks)
    comp = usage.get("completion_tokens") or 0
    ttft = ((t_first - t0) * 1000.0) if t_first else None
    decode_s = max(total_s - ((ttft or 0) / 1000.0), 1e-6)
    return {
        "ttft_ms": round(ttft, 1) if ttft else None,
        "total_s": round(total_s, 3),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": comp,
        "decode_tok_s": round(comp / decode_s, 2) if comp else None,
        "wall_tok_s": round(comp / total_s, 2) if comp and total_s else None,
        "finish_reason": finish,
        "text": text,
    }


def validate_edit(text: str) -> dict[str, Any]:
    """The edit case is only a valid measurement if the model really did it."""
    # Every key must be True when the task was done right. `removed_old_value`
    # is phrased positively for exactly that reason: an earlier version stored
    # `kept_old_value` (correctly False) and the all()-aggregate then scored a
    # perfect edit as invalid — a grader inverting a correct verdict.
    return {
        "has_change": "DEFAULT_TIMEOUT = 60" in text,
        "removed_old_value": "DEFAULT_TIMEOUT = 30" not in text,
        "has_class": "class LedgerStore" in text,
        "has_all_methods": all(m in text for m in
                               ("def __init__", "def append", "def load", "def latest")),
        "no_ellipsis": "..." not in text and "# unchanged" not in text.lower(),
    }


def validate_control(text: str) -> dict[str, Any]:
    """The control is only valid if the model did NOT copy the file."""
    return {
        "no_code_fence": "```" not in text,
        "no_class_name": "LedgerStore" not in text,
        "no_identifiers": not any(i in text for i in
                                  ("def append", "def latest", "_cache", "mkdir")),
    }


def stat(vals: list[float]) -> dict[str, float] | None:
    if not vals:
        return None
    return {"n": len(vals), "mean": round(statistics.mean(vals), 2),
            "p50": round(statistics.median(vals), 2),
            "min": round(min(vals), 2), "max": round(max(vals), 2)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8899/v1")
    ap.add_argument("--model", default="qwen3.8-flash-next")
    ap.add_argument("--label", required=True)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--timeout", type=float, default=600)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    url = args.base.rstrip("/") + "/chat/completions"
    cases = [("edit_shaped", EDIT_PROMPT, validate_edit),
             ("prose_control", CONTROL_PROMPT, validate_control)]
    rows: list[dict[str, Any]] = []

    for name, prompt, validator in cases:
        for i in range(args.repeats + 1):  # +1 cold, discarded
            phase = "cold" if i == 0 else f"warm{i}"
            payload = {"model": args.model,
                       "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 900, "temperature": 0,
                       "reasoning_effort": "none"}
            try:
                r = stream_chat(url, payload, args.timeout)
            except Exception as e:  # noqa: BLE001
                rows.append({"case": name, "phase": phase, "error": str(e)})
                print(f"{name} {phase} FAILED: {e}", flush=True)
                continue
            text = r.pop("text")
            r.update({"case": name, "phase": phase,
                      "valid": validator(text), "content_chars": len(text)})
            r["valid_all"] = all(r["valid"].values())
            rows.append(r)
            print(json.dumps({k: r[k] for k in
                              ("case", "phase", "decode_tok_s", "wall_tok_s",
                               "ttft_ms", "completion_tokens", "valid_all")}), flush=True)

    summary = {}
    for name, _, _ in cases:
        warm = [r for r in rows if r.get("case") == name
                and r.get("phase") != "cold" and "error" not in r]
        summary[name] = {
            "decode_tok_s": stat([r["decode_tok_s"] for r in warm if r.get("decode_tok_s")]),
            "wall_tok_s": stat([r["wall_tok_s"] for r in warm if r.get("wall_tok_s")]),
            "completion_tokens": stat([float(r["completion_tokens"]) for r in warm if r.get("completion_tokens")]),
            "valid": sum(1 for r in warm if r.get("valid_all")),
            "n": len(warm),
        }

    e = summary["edit_shaped"]["decode_tok_s"]
    p = summary["prose_control"]["decode_tok_s"]
    ratio = round(e["p50"] / p["p50"], 2) if e and p and p["p50"] else None
    summary["copyability_speedup"] = ratio
    summary["reading"] = (
        "ratio ~1.0 = build does NOT exploit output copyability (no context-copy "
        "speculation); ratio >>1.0 = it does, and the headline number is a "
        "copy artifact rather than a decode rate."
    )

    report = {"as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "label": args.label, "base": args.base, "model": args.model,
              "summary": summary, "rows": rows}
    out = args.out or str(Path.home() / "Documents/T1000/docs/inference/experiments"
                          / f"edit-vs-prose-{args.label}.json")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(report, indent=2) + "\n")
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
