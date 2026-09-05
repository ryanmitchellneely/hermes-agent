#!/usr/bin/env python3
"""Prefill (prompt-processing) bench on REAL text — the number the lane waits on.

WHY: llama.cpp PR 28136's author measured flash-next prefill at ~300 tok/s on
real-world text vs 700+ on repetitive benchmark text on a DGX Spark, because the
lazy PLE (n-gram) table is read through mmap and real text touches far more of
it. A DevBot card is ~19k tokens of real text, so TTFT is what the lane feels.

DESIGN: one long real-text prompt (built from repo docs, no repetition), sent
with `cache_prompt: false` so every call re-prefills; tiny completion (16 tok)
so the wall is ~all prefill. First call discarded (cold mmap), then N repeats.
Reports prompt tokens, TTFT (= time to first streamed token), and prompt tok/s.
"""
from __future__ import annotations
import argparse, json, statistics, sys, time, urllib.request
from pathlib import Path

def one(base, model, text, timeout):
    payload = {"model": model, "messages": [{"role": "user", "content": text}],
               "max_tokens": 16, "temperature": 0, "stream": True,
               "stream_options": {"include_usage": True}, "cache_prompt": False,
               "reasoning_effort": "none"}
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", "Accept": "text/event-stream"})
    t0 = time.time(); ttft = None; usage = None
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"): continue
            body = line[5:].strip()
            if body == "[DONE]": break
            d = json.loads(body)
            if d.get("usage"): usage = d["usage"]
            ch = d.get("choices") or []
            if ch and ttft is None:
                delta = ch[0].get("delta", {})
                if delta.get("content") or delta.get("reasoning_content") or delta.get("reasoning"):
                    ttft = time.time() - t0
    total = time.time() - t0
    pt = (usage or {}).get("prompt_tokens")
    return {"prompt_tokens": pt, "ttft_s": round(ttft, 2) if ttft else None,
            "total_s": round(total, 2), "prompt_tok_s": round(pt / ttft, 1) if (pt and ttft) else None}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:11439/v1")
    ap.add_argument("--model", default="qwen3.8-flash-next")
    ap.add_argument("--label", required=True)
    ap.add_argument("--corpus", required=True, help="text file, real prose, ~75k chars for ~19k tokens")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--timeout", type=float, default=1200)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    text = Path(a.corpus).read_text(encoding="utf-8", errors="replace")
    text = ("Read the following material carefully and then answer with exactly one word: READY.\n\n" + text)
    rows = []
    cold = one(a.base, a.model, text, a.timeout); print("cold", json.dumps(cold), flush=True)
    for i in range(a.repeats):
        r = one(a.base, a.model, text, a.timeout); rows.append(r); print(f"warm{i+1}", json.dumps(r), flush=True)
    ps = [r["prompt_tok_s"] for r in rows if r["prompt_tok_s"]]
    summary = {"label": a.label, "model": a.model, "base": a.base, "corpus_chars": len(text),
               "prompt_tokens": rows[0]["prompt_tokens"] if rows else None,
               "cold": cold, "warm_prompt_tok_s_p50": statistics.median(ps) if ps else None,
               "warm_ttft_s_p50": statistics.median([r["ttft_s"] for r in rows if r["ttft_s"]]) if rows else None,
               "rows": rows}
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(summary, indent=2) + "\n"); print("wrote", a.out)
    return 0
if __name__ == "__main__": sys.exit(main())
