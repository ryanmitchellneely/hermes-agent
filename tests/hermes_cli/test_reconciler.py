"""Proof tests for the desired-state reconciler (P0 Distillery pattern).

Standing rule: no proof, no bottle. These drills inject drift and show
auto-repair or refuse + surface within one reconciler run.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from hermes_cli.reconciler import (
    Finding,
    FindingKind,
    Reality,
    load_desired_state,
    maybe_alert_unrepaired,
    reconcile,
)


@pytest.fixture
def desired(tmp_path: Path) -> dict:
    src = (
        Path(__file__).resolve().parents[2]
        / "deploy"
        / "reconciler"
        / "desired-state.yaml"
    )
    data = yaml.safe_load(src.read_text(encoding="utf-8"))
    # Point heartbeat/alert into tmp
    data["reconciler"]["heartbeat_path"] = str(tmp_path / "heartbeat.json")
    data["reconciler"]["drift_alert_path"] = str(tmp_path / "last-alert.json")
    data["reconciler"]["unrepaired_alert_after_sec"] = 60
    return data


def test_load_checked_in_desired_state():
    data = load_desired_state()
    assert data["version"] == 1
    assert data["gateway_ha"]["topology"] == "mac-primary-vps-standby"
    assert "dual_gateway_live" in data["gateway_ha"]["refuse_states"]


def test_healthy_mac_primary_is_ok(desired, tmp_path: Path):
    reality = Reality(
        host_role="mac",
        mac_gateway_running=True,
        mac_heartbeat_agent_running=True,
        vps_gateway_active=False,
        vps_claimed_by="mac",
    )
    result = reconcile(
        desired=desired, reality=reality, fix=False, state_dir=tmp_path
    )
    assert result.ok
    assert result.exit_code == 0
    assert result.drifted == 0
    assert result.refused == 0
    assert (tmp_path / "heartbeat.json").is_file()
    hb = json.loads((tmp_path / "heartbeat.json").read_text(encoding="utf-8"))
    assert hb["ok"] is True


def test_disarmed_timer_reports_drift_and_fix_repairs(desired, tmp_path: Path):
    """Inject drift: required VPS timer disarmed → --fix re-arms it."""
    reality = Reality(
        host_role="vps",
        mac_gateway_running=False,
        vps_gateway_active=False,
        vps_watchdog_timer_active=False,
        timers_active={
            "t1000-failover-watchdog.timer": False,
            "juice-doctor-reconcile.timer": False,
        },
    )
    repaired_ids: list[str] = []

    def repair(finding: Finding, _reality: Reality, _desired: dict) -> bool:
        if finding.id.startswith("timer.disarmed:"):
            repaired_ids.append(finding.id)
            return True
        return False

    # Report-only: drift, non-zero exit
    report = reconcile(
        desired=desired, reality=reality, fix=False, state_dir=tmp_path
    )
    assert not report.ok
    assert report.exit_code == 1
    assert report.drifted >= 2
    assert any(f.id.startswith("timer.disarmed:") for f in report.findings)

    # --fix: auto-repair within one run
    fixed = reconcile(
        desired=desired,
        reality=reality,
        fix=True,
        repair_fn=repair,
        state_dir=tmp_path,
    )
    assert fixed.fixed >= 2
    assert fixed.drifted == 0
    assert fixed.ok
    assert fixed.exit_code == 0
    assert "timer.disarmed:t1000-failover-watchdog.timer" in repaired_ids


def test_dual_gateway_is_refused_not_repaired(desired, tmp_path: Path):
    """Standing invariant: dual live writers → REFUSE, never repair-into."""
    reality = Reality(
        host_role="mac",
        mac_gateway_running=True,
        mac_heartbeat_agent_running=True,
        vps_gateway_active=True,  # split brain
    )
    repair_calls = {"n": 0}

    def repair(finding: Finding, *_a) -> bool:
        repair_calls["n"] += 1
        return True

    result = reconcile(
        desired=desired,
        reality=reality,
        fix=True,
        repair_fn=repair,
        state_dir=tmp_path,
    )
    assert result.refused >= 1
    assert result.exit_code == 2
    assert any(f.id == "ha.dual_gateway_live" for f in result.findings)
    # Must not attempt to "fix" a refuse finding
    refuse = next(f for f in result.findings if f.id == "ha.dual_gateway_live")
    assert refuse.kind == FindingKind.REFUSE
    assert refuse.repaired is False
    assert repair_calls["n"] == 0  # no drift repairs either in this pure refuse case


def test_mac_hand_start_while_vps_serving_refused(desired, tmp_path: Path):
    reality = Reality(
        host_role="mac",
        mac_gateway_running=False,
        mac_heartbeat_agent_running=True,
        vps_gateway_active=True,
        mac_hand_start_requested=True,
    )
    result = reconcile(
        desired=desired, reality=reality, fix=True, state_dir=tmp_path
    )
    assert result.refused >= 1
    assert any(
        f.id == "ha.mac_hand_start_while_vps_serving" for f in result.findings
    )
    assert result.exit_code == 2


def test_unrepaired_drift_surfaces_alert_after_grace(desired, tmp_path: Path):
    """Reconciler heartbeats always; unrepaired drift alerts after threshold."""
    desired = dict(desired)
    desired["reconciler"] = dict(desired["reconciler"])
    desired["reconciler"]["unrepaired_alert_after_sec"] = 30

    reality = Reality(
        host_role="vps",
        timers_active={
            "t1000-failover-watchdog.timer": False,
            "juice-doctor-reconcile.timer": True,
        },
    )
    t0 = 1_700_000_000.0
    r1 = reconcile(
        desired=desired,
        reality=reality,
        fix=False,
        state_dir=tmp_path,
        now=t0,
    )
    assert r1.drifted >= 1
    assert r1.alert_written is False  # still in grace
    pending = json.loads((tmp_path / "last-alert.json").read_text(encoding="utf-8"))
    assert pending["status"] == "pending"

    r2 = reconcile(
        desired=desired,
        reality=reality,
        fix=False,
        state_dir=tmp_path,
        now=t0 + 45,
    )
    assert r2.alert_written is True
    alert = json.loads((tmp_path / "last-alert.json").read_text(encoding="utf-8"))
    assert alert["status"] == "alert"
    assert "timer.disarmed:t1000-failover-watchdog.timer" in alert["finding_ids"]


def test_refuse_alerts_immediately(desired, tmp_path: Path):
    reality = Reality(
        host_role="mac",
        mac_gateway_running=True,
        mac_heartbeat_agent_running=True,
        vps_gateway_active=True,
    )
    result = reconcile(
        desired=desired,
        reality=reality,
        fix=False,
        state_dir=tmp_path,
        now=1_700_000_000.0,
    )
    assert result.alert_written is True
    alert = json.loads((tmp_path / "last-alert.json").read_text(encoding="utf-8"))
    assert alert["status"] == "alert"


def test_maybe_alert_clears_when_healthy(tmp_path: Path):
    from hermes_cli.reconciler import ReconcileResult

    alert_path = tmp_path / "last-alert.json"
    alert_path.write_text('{"status":"alert","finding_ids":["x"]}', encoding="utf-8")
    healthy = ReconcileResult(ok=True, findings=[])
    wrote = maybe_alert_unrepaired(
        alert_path, healthy, unrepaired_after_sec=10, now=100.0
    )
    assert wrote is False
    assert not alert_path.exists()


def test_systemctl_enabled_ignores_static(monkeypatch):
    """'static' units are not enabled-at-boot — must not false-positive HA drift."""
    import subprocess
    from hermes_cli import reconciler as rec

    class R:
        returncode = 0
        stdout = "static\n"
        stderr = ""

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: R(),
    )
    assert rec._systemctl_is_enabled("t1000-gateway.service") is False

    class R2:
        returncode = 0
        stdout = "enabled\n"
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: R2())
    assert rec._systemctl_is_enabled("t1000-gateway.service") is True
