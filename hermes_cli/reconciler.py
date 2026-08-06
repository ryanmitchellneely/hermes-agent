"""Desired-state reconciler for T1000/Juice (Distillery/openclaw pattern port).

Config declares desired state. One repairer converges reality:

  juice-doctor           → report drift, exit non-zero on drift
  juice-doctor --fix    → converge what is safe; REFUSE unsafe HA states

Standing invariant (encoded in desired-state.yaml, not prose):
  Mac-primary / VPS-standby, single Telegram writer. Never hand-start the Mac
  gateway while the VPS is serving. The reconciler refuses that state rather
  than "repairing into" dual-serve.

Probes are injectable so proof tests can inject drift without real launchd/
systemd. Production probes shell out to launchctl/systemctl/SSH as needed.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


class FindingKind(str, Enum):
    DRIFT = "drift"  # repairable
    REFUSE = "refuse"  # standing invariant — do not auto-repair into this
    OK = "ok"
    ALERT = "alert"  # unrepaired / cannot-fix surface


class Severity(str, Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Finding:
    id: str
    kind: FindingKind
    severity: Severity
    message: str
    repairable: bool = False
    repaired: bool = False
    refuse_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        d["severity"] = self.severity.value
        return d


@dataclass
class Reality:
    """Observable world state the reconciler compares to desired state."""

    host_role: str = "mac"  # mac | vps
    mac_gateway_running: bool = False
    mac_heartbeat_agent_running: bool = False
    vps_gateway_active: bool = False
    vps_gateway_enabled_at_boot: bool = False
    vps_watchdog_timer_active: bool = False
    vps_claimed_by: str = ""  # mac | vps | ""
    heartbeat_age_sec: Optional[int] = None
    # Timers that are armed (name → active bool)
    timers_active: Dict[str, bool] = field(default_factory=dict)
    # Explicit operator request to hand-start Mac while VPS serves (danger)
    mac_hand_start_requested: bool = False


@dataclass
class ReconcileResult:
    ok: bool
    findings: List[Finding] = field(default_factory=list)
    fixed: int = 0
    refused: int = 0
    drifted: int = 0
    heartbeat_written: bool = False
    alert_written: bool = False

    @property
    def exit_code(self) -> int:
        if self.refused > 0:
            return 2
        if not self.ok or self.drifted > 0:
            return 1
        return 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "fixed": self.fixed,
            "refused": self.refused,
            "drifted": self.drifted,
            "heartbeat_written": self.heartbeat_written,
            "alert_written": self.alert_written,
            "exit_code": self.exit_code,
            "findings": [f.to_dict() for f in self.findings],
        }


DEFAULT_DESIRED_STATE_PATH = (
    Path(__file__).resolve().parent.parent / "deploy" / "reconciler" / "desired-state.yaml"
)


def _expand(path: str) -> Path:
    return Path(os.path.expanduser(path)).resolve()


def load_desired_state(path: Optional[Path | str] = None) -> Dict[str, Any]:
    """Load declarative desired-state YAML."""
    p = Path(path) if path else DEFAULT_DESIRED_STATE_PATH
    if yaml is None:
        raise RuntimeError("PyYAML required to load desired-state.yaml")
    with open(p, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError(f"desired-state must be version: 1 mapping, got {type(data)}")
    return data


def evaluate_ha_invariant(reality: Reality, desired: Dict[str, Any]) -> List[Finding]:
    """Encode Mac-primary/VPS-standby single-writer rules as findings.

    REFUSE (never auto-repair into):
      - dual_gateway_live
      - mac_hand_start_while_vps_serving
    """
    findings: List[Finding] = []
    ha = desired.get("gateway_ha") or {}
    if ha.get("topology") != "mac-primary-vps-standby":
        findings.append(
            Finding(
                id="ha.topology_unknown",
                kind=FindingKind.REFUSE,
                severity=Severity.CRITICAL,
                message=f"unsupported gateway_ha.topology={ha.get('topology')!r}",
                refuse_reason="unknown_topology",
            )
        )
        return findings

    dual = reality.mac_gateway_running and reality.vps_gateway_active
    if dual:
        findings.append(
            Finding(
                id="ha.dual_gateway_live",
                kind=FindingKind.REFUSE,
                severity=Severity.CRITICAL,
                message=(
                    "REFUSE: dual gateway live (Mac + VPS both serving). "
                    "Stop one writer manually — reconciler will not pick a side."
                ),
                refuse_reason="dual_gateway_live",
            )
        )

    if reality.mac_hand_start_requested and reality.vps_gateway_active:
        findings.append(
            Finding(
                id="ha.mac_hand_start_while_vps_serving",
                kind=FindingKind.REFUSE,
                severity=Severity.CRITICAL,
                message=(
                    "REFUSE: Mac gateway hand-start while VPS is serving. "
                    "Demote VPS first (watchdog / systemctl stop t1000-gateway)."
                ),
                refuse_reason="mac_hand_start_while_vps_serving",
            )
        )

    # Soft drift: claimed_by should be mac when Mac is healthy primary.
    want_claimed = (ha.get("vps") or {}).get("claimed_by_when_healthy", "mac")
    if (
        reality.host_role == "vps"
        and reality.mac_gateway_running
        and not reality.vps_gateway_active
        and reality.vps_claimed_by
        and reality.vps_claimed_by != want_claimed
    ):
        findings.append(
            Finding(
                id="ha.claimed_by_drift",
                kind=FindingKind.DRIFT,
                severity=Severity.WARN,
                message=f"claimed_by={reality.vps_claimed_by!r} want={want_claimed!r}",
                repairable=True,
            )
        )

    # VPS gateway must not be enabled-at-boot (watchdog owns start/stop).
    if reality.host_role == "vps" and reality.vps_gateway_enabled_at_boot:
        findings.append(
            Finding(
                id="ha.vps_gateway_enabled_at_boot",
                kind=FindingKind.DRIFT,
                severity=Severity.ERROR,
                message="t1000-gateway.service is enabled-at-boot; watchdog must own lifecycle",
                repairable=True,
            )
        )

    return findings


def evaluate_timers(reality: Reality, desired: Dict[str, Any]) -> List[Finding]:
    findings: List[Finding] = []
    if reality.host_role != "vps":
        # Mac does not own VPS timers; skip.
        return findings
    for entry in desired.get("vps_timers") or []:
        name = entry.get("name")
        if not name:
            continue
        required = bool(entry.get("required", True))
        active = bool(reality.timers_active.get(name, False))
        if required and not active:
            findings.append(
                Finding(
                    id=f"timer.disarmed:{name}",
                    kind=FindingKind.DRIFT,
                    severity=Severity.ERROR,
                    message=f"required timer disarmed: {name}",
                    repairable=True,
                )
            )
        elif active:
            findings.append(
                Finding(
                    id=f"timer.ok:{name}",
                    kind=FindingKind.OK,
                    severity=Severity.INFO,
                    message=f"timer armed: {name}",
                )
            )
    return findings


def evaluate_mac_agents(reality: Reality, desired: Dict[str, Any]) -> List[Finding]:
    findings: List[Finding] = []
    if reality.host_role != "mac":
        return findings
    ha = desired.get("gateway_ha") or {}
    mac = ha.get("mac") or {}
    if not reality.mac_heartbeat_agent_running:
        findings.append(
            Finding(
                id="mac.heartbeat_agent_disarmed",
                kind=FindingKind.DRIFT,
                severity=Severity.ERROR,
                message=(
                    f"Mac heartbeat LaunchAgent disarmed "
                    f"({mac.get('heartbeat_launch_agent', 'com.ryan.t1000-failover-heartbeat')})"
                ),
                repairable=True,
            )
        )
    else:
        findings.append(
            Finding(
                id="mac.heartbeat_agent_ok",
                kind=FindingKind.OK,
                severity=Severity.INFO,
                message="Mac failover heartbeat agent running",
            )
        )
    return findings


RepairFn = Callable[[Finding, Reality, Dict[str, Any]], bool]


def default_repair(finding: Finding, reality: Reality, desired: Dict[str, Any]) -> bool:
    """Apply a safe repair. Returns True if repaired.

    Real side-effects are performed only when HERMES_RECONCILER_LIVE=1.
    Tests inject their own repair_fn. Live mode shells out carefully.
    """
    if finding.kind != FindingKind.DRIFT or not finding.repairable:
        return False
    live = os.environ.get("HERMES_RECONCILER_LIVE", "").strip() in {"1", "true", "yes"}
    if not live:
        # Dry repair bookkeeping for unit tests / report-only --fix simulation
        # when callers override; production juice-doctor --fix sets LIVE=1.
        return False

    if finding.id.startswith("timer.disarmed:"):
        unit = finding.id.split(":", 1)[1]
        return _systemctl(["enable", "--now", unit]) == 0

    if finding.id == "ha.vps_gateway_enabled_at_boot":
        unit = ((desired.get("gateway_ha") or {}).get("vps") or {}).get(
            "gateway_unit", "t1000-gateway.service"
        )
        return _systemctl(["disable", unit]) == 0

    if finding.id == "ha.claimed_by_drift":
        state_dir = ((desired.get("gateway_ha") or {}).get("vps") or {}).get(
            "state_dir", "/var/lib/t1000-failover"
        )
        want = ((desired.get("gateway_ha") or {}).get("vps") or {}).get(
            "claimed_by_when_healthy", "mac"
        )
        try:
            path = Path(state_dir) / "claimed_by"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(want + "\n", encoding="utf-8")
            return True
        except OSError:
            return False

    if finding.id == "mac.heartbeat_agent_disarmed":
        label = ((desired.get("gateway_ha") or {}).get("mac") or {}).get(
            "heartbeat_launch_agent", "com.ryan.t1000-failover-heartbeat"
        )
        uid = os.getuid() if hasattr(os, "getuid") else 0  # windows-footgun: ok
        return _run(["launchctl", "kickstart", "-k", f"gui/{uid}/{label}"]) == 0

    return False


def _systemctl(args: Sequence[str]) -> int:
    return _run(["systemctl", *args])


def _run(cmd: Sequence[str]) -> int:
    import subprocess

    try:
        return subprocess.run(
            list(cmd),
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        ).returncode
    except (OSError, subprocess.TimeoutExpired):
        return 127


def write_heartbeat(path: Path, result: ReconcileResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts": time.time(),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ok": result.ok,
        "exit_code": result.exit_code,
        "fixed": result.fixed,
        "refused": result.refused,
        "drifted": result.drifted,
        "finding_ids": [f.id for f in result.findings if f.kind != FindingKind.OK],
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def maybe_alert_unrepaired(
    path: Path,
    result: ReconcileResult,
    *,
    unrepaired_after_sec: int,
    previous_alert: Optional[Dict[str, Any]] = None,
    now: Optional[float] = None,
) -> bool:
    """Write an alert file when drift/refuse cannot be cleared.

    Returns True if an alert was written (or refreshed).
    """
    now = time.time() if now is None else now
    blocking = [
        f
        for f in result.findings
        if f.kind in {FindingKind.DRIFT, FindingKind.REFUSE, FindingKind.ALERT}
        and not f.repaired
        and f.kind != FindingKind.OK
    ]
    # Only non-OK non-repaired
    blocking = [f for f in result.findings if f.kind in {FindingKind.DRIFT, FindingKind.REFUSE} and not f.repaired]
    if not blocking:
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass
        return False

    first_seen = now
    if previous_alert and isinstance(previous_alert.get("first_seen"), (int, float)):
        # Same set of ids → keep first_seen
        prev_ids = set(previous_alert.get("finding_ids") or [])
        cur_ids = {f.id for f in blocking}
        if prev_ids == cur_ids:
            first_seen = float(previous_alert["first_seen"])

    age = now - first_seen
    if age < unrepaired_after_sec and result.refused == 0:
        # Still within grace for plain drift; always alert immediately on REFUSE.
        # Persist first_seen so next run can age it.
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "status": "pending",
                    "first_seen": first_seen,
                    "age_sec": age,
                    "finding_ids": [f.id for f in blocking],
                    "message": "drift open; alert pending until unrepaired_after_sec",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "alert",
        "ts": now,
        "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "first_seen": first_seen,
        "age_sec": age,
        "finding_ids": [f.id for f in blocking],
        "findings": [f.to_dict() for f in blocking],
        "message": "T1000 reconciler: unrepaired drift or refused HA state — operator action required",
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return True


def reconcile(
    *,
    desired: Optional[Dict[str, Any]] = None,
    reality: Optional[Reality] = None,
    fix: bool = False,
    repair_fn: Optional[RepairFn] = None,
    state_dir: Optional[Path] = None,
    now: Optional[float] = None,
) -> ReconcileResult:
    """Compare reality to desired state; optionally repair; always heartbeat."""
    desired = desired if desired is not None else load_desired_state()
    if reality is None:
        raise ValueError("reality probe required (pass Reality(...) or use probe_local_reality())")

    findings: List[Finding] = []
    findings.extend(evaluate_ha_invariant(reality, desired))
    findings.extend(evaluate_timers(reality, desired))
    findings.extend(evaluate_mac_agents(reality, desired))

    repair = repair_fn or default_repair
    fixed = 0
    if fix:
        for f in findings:
            if f.kind == FindingKind.DRIFT and f.repairable:
                if repair(f, reality, desired):
                    f.repaired = True
                    fixed += 1

    refused = sum(1 for f in findings if f.kind == FindingKind.REFUSE)
    drifted = sum(
        1
        for f in findings
        if f.kind == FindingKind.DRIFT and not f.repaired
    )
    ok = refused == 0 and drifted == 0

    result = ReconcileResult(
        ok=ok,
        findings=findings,
        fixed=fixed,
        refused=refused,
        drifted=drifted,
    )

    # Heartbeat + alert paths from desired state (overridable via state_dir for tests).
    # Prefer HERMES_HOME so root-run VPS units don't write under /root/.
    rec = desired.get("reconciler") or {}
    if state_dir is not None:
        hb_path = state_dir / "heartbeat.json"
        alert_path = state_dir / "last-alert.json"
    else:
        hermes_home = Path(
            os.path.expanduser(os.environ.get("HERMES_HOME") or "~/.t1000")
        )
        default_hb = str(hermes_home / "reconciler" / "heartbeat.json")
        default_alert = str(hermes_home / "reconciler" / "last-alert.json")
        hb_raw = rec.get("heartbeat_path") or default_hb
        alert_raw = rec.get("drift_alert_path") or default_alert
        # Rewrite bare ~/.t1000/... to HERMES_HOME when set
        hb_path = _expand(hb_raw)
        alert_path = _expand(alert_raw)
        if os.environ.get("HERMES_HOME"):
            hh = str(hermes_home.resolve())
            # If path still points at another user's .t1000, force under HERMES_HOME
            if "/.t1000/" in str(hb_path) and not str(hb_path).startswith(hh):
                hb_path = hermes_home / "reconciler" / "heartbeat.json"
            if "/.t1000/" in str(alert_path) and not str(alert_path).startswith(hh):
                alert_path = hermes_home / "reconciler" / "last-alert.json"

    write_heartbeat(hb_path, result)
    result.heartbeat_written = True

    prev = None
    if alert_path.exists():
        try:
            prev = json.loads(alert_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            prev = None

    unrepaired_after = int(rec.get("unrepaired_alert_after_sec", 900))
    result.alert_written = maybe_alert_unrepaired(
        alert_path,
        result,
        unrepaired_after_sec=unrepaired_after,
        previous_alert=prev,
        now=now,
    )
    return result


def probe_local_reality() -> Reality:
    """Best-effort live probe on the current host (Mac or VPS)."""
    role = os.environ.get("T1000_HOST_ROLE", "").strip().lower()
    if not role:
        # Heuristic: Linux + /var/lib/t1000-failover → vps
        if Path("/var/lib/t1000-failover").is_dir() and os.uname().sysname == "Linux":
            role = "vps"
        else:
            role = "mac"

    reality = Reality(host_role=role)
    if role == "mac":
        reality.mac_gateway_running = _launchctl_running("ai.hermes.gateway")
        reality.mac_heartbeat_agent_running = _launchctl_running(
            "com.ryan.t1000-failover-heartbeat"
        )
        # Optionally read VPS side via status file if present
        local_claim = Path(os.path.expanduser("~/.t1000/failover/last-status.json"))
        if local_claim.exists():
            try:
                data = json.loads(local_claim.read_text(encoding="utf-8"))
                reality.vps_gateway_active = bool(data.get("vps_gateway_active"))
                reality.vps_claimed_by = str(data.get("claimed_by") or "")
            except (OSError, json.JSONDecodeError):
                pass
    else:
        reality.vps_gateway_active = _systemctl_is_active("t1000-gateway.service")
        reality.vps_gateway_enabled_at_boot = _systemctl_is_enabled("t1000-gateway.service")
        reality.vps_watchdog_timer_active = _systemctl_is_active(
            "t1000-failover-watchdog.timer"
        )
        claimed = Path("/var/lib/t1000-failover/claimed_by")
        if claimed.exists():
            try:
                reality.vps_claimed_by = claimed.read_text(encoding="utf-8").strip()
            except OSError:
                pass
        hb = Path("/var/lib/t1000-failover/heartbeat")
        if hb.exists():
            try:
                raw = hb.read_text(encoding="utf-8").split()[0]
                reality.heartbeat_age_sec = max(0, int(time.time()) - int(raw))
            except (OSError, ValueError, IndexError):
                pass
        # Timer map
        for name in (
            "t1000-failover-watchdog.timer",
            "juice-doctor-reconcile.timer",
        ):
            reality.timers_active[name] = _systemctl_is_active(name)

    return reality


def _launchctl_running(label: str) -> bool:
    import subprocess

    try:
        proc = subprocess.run(
            [
                "launchctl",
                "print",
                f"gui/{(os.getuid() if hasattr(os, 'getuid') else 0)}/{label}",  # windows-footgun: ok
            ],
            check=False,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode != 0:
            return False
        out = proc.stdout or ""
        # "state = running" is the reliable signal
        return "state = running" in out or "pid =" in out
    except (OSError, subprocess.TimeoutExpired):
        return False


def _systemctl_is_active(unit: str) -> bool:
    import subprocess

    try:
        proc = subprocess.run(
            ["systemctl", "is-active", "--quiet", unit],
            check=False,
            stdin=subprocess.DEVNULL,
            timeout=10,
        )
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _systemctl_is_enabled(unit: str) -> bool:
    """True only when unit is explicitly enabled-at-boot (not static/alias/generated)."""
    import subprocess

    try:
        proc = subprocess.run(
            ["systemctl", "is-enabled", unit],
            check=False,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=10,
        )
        # 'enabled' / 'enabled-runtime' are the bad HA states.
        # 'static', 'disabled', 'indirect', 'alias', 'generated' are fine.
        state = (proc.stdout or "").strip().splitlines()
        state = state[0] if state else ""
        return state in {"enabled", "enabled-runtime"}
    except (OSError, subprocess.TimeoutExpired):
        return False


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="t1000-reconciler")
    parser.add_argument("--fix", action="store_true", help="Converge repairable drift")
    parser.add_argument(
        "--desired-state",
        type=Path,
        default=None,
        help="Path to desired-state.yaml",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON result")
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=None,
        help="Override heartbeat/alert directory (tests)",
    )
    parser.add_argument(
        "--role",
        choices=["mac", "vps"],
        default=None,
        help="Override host role for probe",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    desired = load_desired_state(args.desired_state)
    if args.role:
        os.environ["T1000_HOST_ROLE"] = args.role
    reality = probe_local_reality()
    if args.fix:
        os.environ.setdefault("HERMES_RECONCILER_LIVE", "1")
    result = reconcile(
        desired=desired,
        reality=reality,
        fix=args.fix,
        state_dir=args.state_dir,
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        status = "OK" if result.ok else ("REFUSED" if result.refused else "DRIFT")
        print(f"reconciler: {status} fixed={result.fixed} drifted={result.drifted} refused={result.refused}")
        for f in result.findings:
            if f.kind == FindingKind.OK:
                continue
            tag = f.kind.value.upper()
            rep = " [repaired]" if f.repaired else ""
            print(f"  [{tag}] {f.id}: {f.message}{rep}")
        if result.alert_written:
            print("  ALERT: unrepaired drift surfaced (see reconciler last-alert.json)")
    return result.exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
