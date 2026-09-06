# v2 of the infra gate: the stored failure error is generic ("pid not alive", "protocol violation");
# the lane failure (HTTP 404 model not found, invalid_grant...) is only in the task LOG. Sniff its tail.
import shutil,datetime
p="/opt/t1000/home/scripts/kanban_model_escalate.py"; s=open(p).read()
old='''        # Lane failure: the model never ran. Never promote an outage to a paid rung.
        infra_blob = f"{last_err} {fail_run.get('error') or ''} {log_ctx}"
'''
new='''        # Lane failure: the model never ran. Never promote an outage to a paid rung.
        # The stored error is generic (pid not alive / protocol violation); the 404 or
        # invalid_grant is only in the task log, so sniff its tail too (v2, 2026-09-06).
        infra_blob = f"{last_err} {fail_run.get('error') or ''} {log_ctx} {log_tail_text(board, tid)}"
'''
assert s.count(old)==1; s=s.replace(old,new,1)
old2='''def _holds_path():'''
new2='''def log_tail_text(board: str, tid: str, nbytes: int = 12000) -> str:
    """Last nbytes of the task's worker log (empty if none) — where lane errors actually show up."""
    logp = HOME / "kanban" / "boards" / board / "logs" / f"{tid}.log"
    try:
        size = logp.stat().st_size
        with open(logp, "rb") as fh:
            if size > nbytes:
                fh.seek(size - nbytes)
            return fh.read().decode("utf-8", "replace")
    except OSError:
        return ""


def _holds_path():'''
assert s.count(old2)==1; s=s.replace(old2,new2,1)
shutil.copy(p, p+".bak-pre-infra-gate-v2-"+datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ"))
open(p,"w").write(s); print("gate v2 patched")
