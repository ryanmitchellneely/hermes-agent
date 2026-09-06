# Add flash-next (ryan-spark llama.cpp via :11439) liveness to the 30m ops alert pulse — same fp-dedup pattern as DS4.
import shutil,datetime
p="/opt/t1000/home/scripts/t1000_ops_alert_pulse.py"; s=open(p).read()
def rep(old,new):
    global s
    assert s.count(old)==1, old[:60]; s=s.replace(old,new,1)

rep('''DS4_LIVENESS_TOKEN_KEY = "K2_LOCAL_API_KEY"''','''DS4_LIVENESS_TOKEN_KEY = "K2_LOCAL_API_KEY"
# flash-next pilot (t_37efebbb, 2026-09-06): Qwen3.8-Flash-Next served by llama.cpp on
# ryan-spark :8898, reached from k2vps ONLY through the sparklink reverse tunnel :11439.
# It is provider `spark` for the whole T1000 engine, so if this is down every local
# kanban card is down. :11435 is the small-model ollama (hermes3 aux) on the same box.
FLASH_HEALTH_URL = os.environ.get("FLASH_HEALTH_URL", "http://127.0.0.1:11439/health")
FLASH_METRICS_URL = os.environ.get("FLASH_METRICS_URL", "http://127.0.0.1:11439/metrics")
FLASH_MODELS_URL = os.environ.get("FLASH_MODELS_URL", "http://127.0.0.1:11439/v1/models")
SPARK_OLLAMA_URL = os.environ.get("SPARK_OLLAMA_URL", "http://127.0.0.1:11435/api/version")
FLASH_TIMEOUT_S = float(os.environ.get("FLASH_TIMEOUT_S", "10"))''')

rep('''def _dsh_verdict_waste() -> list[str]:''','''def _http_get(url: str, timeout: float) -> tuple[int, str]:
    import urllib.request
    req = urllib.request.Request(url, headers={"Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return resp.status, resp.read().decode("utf-8", "replace")


def _flash_next_liveness() -> list[str]:
    """flash-next pilot liveness through the :11439 tunnel. Silent when healthy.
    Tells CHANNEL (tunnel/box unreachable) apart from SERVER (answers but not ok)
    apart from MODEL (health ok but the served model list is wrong)."""
    warns: list[str] = []
    try:
        code, body = _http_get(FLASH_HEALTH_URL, FLASH_TIMEOUT_S)
    except Exception as exc:  # noqa: BLE001
        warns.append(
            "WARN flash-next (provider spark, ALL local kanban cards): CHANNEL unreachable at "
            f"{FLASH_HEALTH_URL} ({type(exc).__name__}) — sparklink tunnel :11439 down, ryan-spark "
            "down, or llama-server not listening on :8898. Spark cron relaunches both within 2 min; "
            "if this persists, look at ~/models/flash-next/flash-next.service.log on the Spark."
        )
    else:
        if code != 200 or '"ok"' not in body:
            warns.append(f"WARN flash-next: /health answered HTTP {code} {body[:120]!r} — server up but not healthy")
        else:
            try:
                _, models = _http_get(FLASH_MODELS_URL, FLASH_TIMEOUT_S)
                if "qwen3.8-flash-next" not in models:
                    warns.append(
                        f"WARN flash-next: :11439 healthy but serves {models[:120]!r}, not qwen3.8-flash-next — "
                        "the tunnel points at the wrong server (bench window left open?)"
                    )
            except Exception as exc:  # noqa: BLE001
                warns.append(f"WARN flash-next: /health ok but /v1/models failed ({type(exc).__name__})")
    try:
        code, _ = _http_get(SPARK_OLLAMA_URL, FLASH_TIMEOUT_S)
        if code != 200:
            warns.append(f"WARN spark ollama (:11435, hermes3 aux): HTTP {code}")
    except Exception as exc:  # noqa: BLE001
        warns.append(
            f"WARN spark ollama (:11435, hermes3 aux for kanban estimator/titles): unreachable ({type(exc).__name__})"
        )
    return warns


def _dsh_verdict_waste() -> list[str]:''')

rep('''    for kind, path in ALERTS:
        fp = _fp(path)''','''    # flash-next pilot liveness (t_37efebbb, 2026-09-06): provider `spark` for the whole
    # engine now lives behind :11439. Same fp dedup; plus an explicit recovery line,
    # because "it came back" is the one message the DS4 pattern never sends.
    fn_warns = _flash_next_liveness()
    fn_blob = "\\n".join(fn_warns).strip()
    fn_fp = hashlib.sha256(fn_blob.encode()).hexdigest()[:16] if fn_blob else None
    new_state["fps"]["flash_next"] = fn_fp
    new_state["flash_next_checked_at"] = _iso()
    old_fn_fp = (prev.get("fps") or {}).get("flash_next")
    if fn_fp and fn_fp != old_fn_fp:
        lines.append(fn_blob)
    elif not fn_fp and old_fn_fp:
        lines.append("🟢 flash-next: :11439 healthy again (provider spark restored)")
    for kind, path in ALERTS:
        fp = _fp(path)''')

shutil.copy(p, p+".bak-pre-flash-liveness-"+datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ"))
open(p,"w").write(s); print("pulse patched")
