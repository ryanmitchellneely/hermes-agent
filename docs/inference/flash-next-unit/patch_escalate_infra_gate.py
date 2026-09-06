# Gate the kanban model-escalate sidecar: (1) never escalate a LANE/INFRA failure (404 model not found,
# connection refused, dead OAuth token...) — hold the card and say so once; (2) skip ladder rungs whose
# provider is declared unavailable (xai-oauth while its refresh token is invalid_grant).
import shutil,datetime,json
p="/opt/t1000/home/scripts/kanban_model_escalate.py"; s=open(p).read()
def rep(old,new):
    global s
    assert s.count(old)==1, old[:60]; s=s.replace(old,new,1)

rep('''\nIMMEDIATE_ERR_SUBS = [''','''\n# LANE / INFRA failures: the model never got to try. Escalating these to a paid rung
# spends frontier budget on an outage (measured 2026-09-06: a profile whose provider
# pointed at a retired ollama tag 404d three times and the ladder promoted the card to
# claude-acp/sonnet). Hold instead, and say so once per task per HOLD_REPEAT_SECS.
INFRA_ERR_SUBS = [
    "http 404",
    "' not found",
    "connection refused",
    "connecterror",
    "connection error",
    "invalid_grant",
    "token refresh failed",
    "re-authenticate",
    "name or service not known",
    "no route to host",
    "errno 111",
    "max retries exceeded",
]
HOLD_REPEAT_SECS = 6 * 3600
HOLDS_PATH = None  # set after HOME is known
HELD: list = []

IMMEDIATE_ERR_SUBS = [''')

rep('''def error_is_immediate(err: str, cfg: dict, model: Optional[str] = None) -> bool:''',
'''def error_is_infra(err: str, cfg: dict) -> Optional[str]:
    """Return the matching infra substring if the error is a lane failure, else None."""
    e = (err or "").lower()
    subs = cfg.get("infra_error_substrings")
    if subs is None:
        subs = INFRA_ERR_SUBS
    for sub in subs or []:
        if sub and str(sub).lower() in e:
            return str(sub)
    return None


def apply_unavailable_providers(cfg: dict) -> None:
    """Drop ladder rungs whose provider is declared unavailable (e.g. xai-oauth with a dead token)."""
    bad = set(cfg.get("unavailable_providers") or [])
    if not bad:
        return
    cfg["ladder"] = [r for r in (cfg.get("ladder") or []) if (r.get("provider") or "") not in bad]


def _holds_path():
    return HOME / "kanban" / "model_escalate_holds.json"


def record_hold(board: str, tid: str, title: str, why: str, err: str) -> None:
    """Remember an infra hold; append a human line only the first time per task per HOLD_REPEAT_SECS."""
    path = _holds_path()
    try:
        holds = json.loads(path.read_text()) if path.is_file() else {}
    except Exception:  # noqa: BLE001
        holds = {}
    now = int(time.time())
    key = f"{board}/{tid}"
    last = int((holds.get(key) or {}).get("ts") or 0)
    holds[key] = {"ts": now, "why": why, "err": (err or "")[:200]}
    try:
        path.write_text(json.dumps(holds, indent=1) + "\\n")
    except Exception:  # noqa: BLE001
        pass
    if now - last >= HOLD_REPEAT_SECS:
        HELD.append(
            f"HOLD (lane failure, NOT escalated): {board}/{tid} {title[:60]!r} — matched {why!r}: "
            f"{(err or '')[:140]}. Fix the lane (provider/endpoint/token); the card stays where it is."
        )


def error_is_immediate(err: str, cfg: dict, model: Optional[str] = None) -> bool:''')

rep('''        if not reason:
            # Local ready with no fail yet — leave alone
            continue
''','''        if not reason:
            # Local ready with no fail yet — leave alone
            continue

        # Lane failure: the model never ran. Never promote an outage to a paid rung.
        infra_blob = f"{last_err} {fail_run.get('error') or ''} {log_ctx}"
        infra_hit = error_is_infra(infra_blob, cfg)
        if infra_hit:
            record_hold(board, tid, title, infra_hit, infra_blob.strip())
            continue
''')

rep('''    all_actions: list[Action] = []
    for board, db in board_dbs(args.board):''','''    apply_unavailable_providers(cfg)  # live boards only; the selftest lab keeps the full ladder
    all_actions: list[Action] = []
    for board, db in board_dbs(args.board):''')

rep('''        text = format_human(all_actions, mode)
        if text:
            sys.stdout.write(text)
    return 0''','''        text = format_human(all_actions, mode)
        if text:
            sys.stdout.write(text)
        if HELD:
            sys.stdout.write("\\n".join(HELD) + "\\n")
    return 0''')

shutil.copy(p, p+".bak-pre-infra-gate-"+datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ"))
open(p,"w").write(s)
# config: declare xai-oauth unavailable + carry the infra list explicitly
cp="/opt/t1000/home/kanban/model_escalate.json"; cfg=json.load(open(cp))
shutil.copy(cp, cp+".bak-pre-infra-gate")
cfg["unavailable_providers"]=["xai-oauth"]
cfg["_unavailable_providers_note"]="xai-oauth: refresh token invalid_grant since <=2026-09-06; remove once `hermes model` re-auth is done"
cfg["infra_error_substrings"]=["http 404","' not found","connection refused","connecterror","connection error","invalid_grant","token refresh failed","re-authenticate","name or service not known","no route to host","errno 111","max retries exceeded"]
json.dump(cfg, open(cp,"w"), indent=2); open(cp,"a").write("\n")
print("escalate script + config patched")
