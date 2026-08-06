#!/usr/bin/env python3
"""Emit one reach.receipt.v1 JSON object on stdout."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--peer", required=True)
    p.add_argument("--verb", required=True)
    p.add_argument("--ok", required=True, choices=("true", "false"))
    p.add_argument("--grade", required=True, choices=("live", "stale", "error"))
    p.add_argument("--layer", required=True)
    p.add_argument("--kind", required=True)
    p.add_argument("--rid", required=True)
    p.add_argument("--detail-file", default="")
    p.add_argument("--detail-json", default="")
    p.add_argument("--error-code", default="")
    p.add_argument("--error-message", default="")
    args = p.parse_args()

    detail: dict = {}
    if args.detail_file:
        try:
            with open(args.detail_file, encoding="utf-8") as f:
                raw = f.read().strip()
            if raw:
                loaded = json.loads(raw)
                if isinstance(loaded, dict):
                    detail = loaded
        except (OSError, json.JSONDecodeError):
            detail = {}
    elif args.detail_json:
        try:
            loaded = json.loads(args.detail_json)
            if isinstance(loaded, dict):
                detail = loaded
        except json.JSONDecodeError:
            detail = {}

    out = {
        "schema_version": "reach.receipt.v1",
        "peer": args.peer,
        "verb": args.verb,
        "ok": args.ok == "true",
        "grade": args.grade,
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "layer": args.layer,
        "receipt": {"kind": args.kind, "id": args.rid},
        "detail": detail,
    }
    if args.error_code or args.error_message:
        out["error"] = {"code": args.error_code, "message": args.error_message}

    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
