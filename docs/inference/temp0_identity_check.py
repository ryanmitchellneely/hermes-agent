#!/usr/bin/env python3
"""Temp-0 token-identity check between speculative arms.

WHY: on 2026-09-03/04 (llama.cpp PR 28243 thread) a Metal report found the MTP
arm greedy-identical to no-spec at n=200 and DIVERGENT at n=400 — the cause is
MUL_MAT batch-invariance, so identity is a threshold on accumulated rounding,
and any claim "n-max N is safe" needs the generation length attached. This
instrument fixes the length at >=400 and hashes the token stream so two arms
(served one after the other on the same endpoint) can be compared.

Usage: run once per arm with --label; it appends {label, sha256, n_tokens,
head} to --ledger. `--compare A B` prints identical/diverged + the first
differing offset (by decoded text, since ids are not exposed over OpenAI chat).
"""
from __future__ import annotations
import argparse, hashlib, json, sys, time, urllib.request
from pathlib import Path

PROMPT = (
    "Write a detailed technical explanation, in plain prose with no code, of how "
    "a speculative decoding draft head is verified against a target model, why "
    "acceptance rate depends on the output's predictability, and what happens to "
    "throughput when the draft is wrong. Keep going until you have covered "
    "rejection sampling, tree drafting, and KV-cache rollback."
)

def gen(base, model, n, timeout):
    payload = {"model": model, "messages": [{"role": "user", "content": PROMPT}],
               "max_tokens": n, "temperature": 0, "top_k": 1, "seed": 7,
               "stream": False, "reasoning_effort": "none"}
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    text = d["choices"][0]["message"]["content"] or ""
    return text, d.get("usage", {}).get("completion_tokens"), time.time() - t

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:11439/v1")
    ap.add_argument("--model", default="qwen3.8-flash-next")
    ap.add_argument("--label")
    ap.add_argument("--n", type=int, default=600)
    ap.add_argument("--timeout", type=float, default=900)
    ap.add_argument("--ledger", default="temp0-identity.jsonl")
    ap.add_argument("--compare", nargs=2, metavar=("A", "B"))
    a = ap.parse_args()
    led = Path(a.ledger)
    if a.compare:
        rows = {}
        for line in led.read_text().splitlines():
            r = json.loads(line); rows[r["label"]] = r
        x, y = rows[a.compare[0]], rows[a.compare[1]]
        if x["sha256"] == y["sha256"]:
            print(f"IDENTICAL  {a.compare[0]} == {a.compare[1]}  n_tokens={x['n_tokens']}")
            return 0
        tx, ty = x["text"], y["text"]
        k = next((i for i in range(min(len(tx), len(ty))) if tx[i] != ty[i]), min(len(tx), len(ty)))
        print(f"DIVERGED   {a.compare[0]} vs {a.compare[1]}  first diff at char {k} of {len(tx)}/{len(ty)}  "
              f"n_tokens={x['n_tokens']}/{y['n_tokens']}")
        print("  A:", repr(tx[max(0,k-40):k+40])); print("  B:", repr(ty[max(0,k-40):k+40]))
        return 2
    if not a.label:
        ap.error("--label required unless --compare")
    text, n_tok, wall = gen(a.base, a.model, a.n, a.timeout)
    if not text or (n_tok or 0) < 400:
        print(f"INVALID: n_tokens={n_tok} (<400) — lengthen the prompt or raise --n", file=sys.stderr)
        return 1
    row = {"label": a.label, "sha256": hashlib.sha256(text.encode()).hexdigest(),
           "n_tokens": n_tok, "wall_s": round(wall, 1), "text": text}
    with led.open("a") as fh:
        fh.write(json.dumps(row) + "\n")
    print(json.dumps({k: row[k] for k in ("label", "sha256", "n_tokens", "wall_s")}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
