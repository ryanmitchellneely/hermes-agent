#!/usr/bin/env python3
"""Deploy preflight: boot candidate, pass health, only then stop the healthy instance.

Outage lesson #2 from K2 refuse-to-serve: a gate without preflight turns every
config mistake into an outage. This helper is the pattern — call it from deploy
scripts before systemctl stop / launchctl kickstart of the live unit.

Usage:
  python deploy/preflight_bind_check.py --health-url http://127.0.0.1:8642/health
  python deploy/preflight_bind_check.py --check-secrets-only

Exit 0 = safe to cut over. Non-zero = keep old instance serving.
"""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from typing import Optional


def check_secrets(telegram_enabled: bool = True) -> int:
    try:
        from hermes_cli.startup_secrets import (
            assert_gateway_may_bind,
            check_requirements,
            gateway_secret_requirements,
        )
    except ImportError:
        # Allow running from repo root
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from hermes_cli.startup_secrets import (  # type: ignore
            check_requirements,
            gateway_secret_requirements,
        )

    report = check_requirements(
        gateway_secret_requirements(telegram_enabled=telegram_enabled)
    )
    if not report.ok:
        print(report.error_message, file=sys.stderr)
        return 2
    print("preflight secrets: OK")
    return 0


def check_health(url: str, timeout: float = 5.0) -> int:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = getattr(resp, "status", None) or resp.getcode()
            body = resp.read(256)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"preflight health FAIL: {url} ({exc})", file=sys.stderr)
        return 3
    if int(code) >= 400:
        print(f"preflight health FAIL: HTTP {code} from {url}", file=sys.stderr)
        return 3
    print(f"preflight health: OK ({url} → {code})")
    return 0


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--health-url", default="", help="New instance health endpoint")
    p.add_argument(
        "--check-secrets-only",
        action="store_true",
        help="Only run refuse-to-serve secret checks",
    )
    p.add_argument(
        "--no-telegram",
        action="store_true",
        help="Telegram not required for this surface",
    )
    args = p.parse_args(argv)

    rc = check_secrets(telegram_enabled=not args.no_telegram)
    if rc != 0:
        print(
            "KEEP OLD INSTANCE SERVING — new candidate refused secrets gate.",
            file=sys.stderr,
        )
        return rc
    if args.check_secrets_only:
        return 0
    if not args.health_url:
        print("preflight: secrets OK; no --health-url provided (skip live health)")
        return 0
    rc = check_health(args.health_url)
    if rc != 0:
        print(
            "KEEP OLD INSTANCE SERVING — new candidate failed health check.",
            file=sys.stderr,
        )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
