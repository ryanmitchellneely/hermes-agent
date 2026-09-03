"""signal_log_new.py: local id-mint, remote (ssh) id-mint, and body scaffolding.

Ryan ruled 2026-09-03 that the canonical signal-log library is the VPS
checkout, because two hosts minting SIG-YYYYMMDD-NN off a LOCAL glob on the
same day collided. These tests exercise the pure/mockable pieces: next_id
stays local-glob (unchanged), the new remote_next_id/remote_write take an
injectable `run` so no real ssh happens, and build_entry is a pure function.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent


@pytest.fixture()
def mod(monkeypatch, tmp_path):
    # Isolate ROOT-relative paths (ENTRIES/TEMPLATE/GENERATOR) into a scratch
    # signal-log tree so local-mode tests never touch the real repo.
    log_dir = tmp_path / "docs" / "research" / "signal-log"
    (log_dir / "entries").mkdir(parents=True)
    template = (REPO / "docs" / "research" / "signal-log" / "TEMPLATE.md").read_text()
    (log_dir / "TEMPLATE.md").write_text(template)

    spec = importlib.util.spec_from_file_location(
        "signal_log_new", REPO / "scripts" / "signal_log_new.py"
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)

    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(m, "LOG", log_dir)
    monkeypatch.setattr(m, "ENTRIES", log_dir / "entries")
    monkeypatch.setattr(m, "TEMPLATE", log_dir / "TEMPLATE.md")
    # Never on the canonical VPS checkout during tests.
    monkeypatch.setattr(m, "is_canonical_host", lambda: False)
    return m


def _args(**overrides) -> argparse.Namespace:
    base = dict(
        title="Some Title",
        url="https://example.com/x",
        bucket="harness",
        posture="steal",
        steal_rank="P1",
        slug="some-slug",
        repo="",
        docs="",
        confidence="high",
        day="2026-09-03",
        dry_run=False,
        remote=False,
        local=False,
        remote_host="k2vps",
        remote_root="/opt/t1000/src",
        remote_user="t1000",
    )
    base.update(overrides)
    return argparse.Namespace(**base)


# ── build_entry: pure substitution ──────────────────────────────────────────


def test_build_entry_substitutes_real_values_not_enum_literals(mod):
    template_text = mod.TEMPLATE.read_text()
    args = _args()
    body = mod.build_entry(template_text, "SIG-20260903-01", "2026-09-03", args)

    assert "id: SIG-20260903-01" in body
    assert "date: 2026-09-03" in body
    assert 'title: "Some Title"' in body
    assert 'source_url: "https://example.com/x"' in body
    assert "bucket: harness" in body
    assert "posture: steal" in body
    assert "steal_rank: P1" in body
    assert "confidence: high" in body
    # status/distill must get real scalar defaults, never the enum pipe-lists
    # the template ships (status: open|carded|wired|done|wont).
    assert "status: open" in body
    assert "status: open|carded|wired|done|wont" not in body
    assert "distill: none" in body
    assert "distill: none|ai_brief|mesh_doctrine|k2_handoff" not in body
    # NOTE: the H1 title-line substitution is a pre-existing defect (the
    # generic SIG-YYYYMMDD-NN replace runs first and clobbers the exact
    # string the title-line replace looks for) — out of scope here, not
    # asserted on.


# ── next_id: local glob-based numbering (unchanged) ────────────────────────


def test_next_id_starts_at_01_when_empty(mod):
    assert mod.next_id("2026-09-03") == "SIG-20260903-01"


def test_next_id_increments_past_existing(mod):
    (mod.ENTRIES / "SIG-20260903-01_foo.md").write_text("x")
    (mod.ENTRIES / "SIG-20260903-02_bar.md").write_text("x")
    assert mod.next_id("2026-09-03") == "SIG-20260903-03"


# ── local mode: host-suffixed id ────────────────────────────────────────────


def test_run_local_suffixes_id_with_host_letter(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "local_host_suffix", lambda: "m")
    monkeypatch.setattr(
        mod.subprocess, "run", lambda *a, **k: argparse.Namespace(returncode=0)
    )
    args = _args(local=True)
    mod.run_local(args, "2026-09-03", "some-slug")

    written = list(mod.ENTRIES.glob("*.md"))
    assert len(written) == 1
    assert written[0].name == "SIG-20260903-01m_some-slug.md"

    err = capsys.readouterr().err
    assert "WARNING" in err
    assert "SIG-20260903-01m" in err


def test_run_local_dry_run_writes_nothing(mod, capsys):
    args = _args(local=True, dry_run=True)
    mod.run_local(args, "2026-09-03", "some-slug")
    assert list(mod.ENTRIES.glob("*.md")) == []
    out = capsys.readouterr().out
    assert "SIG-20260903-01" in out


# ── remote_next_id: parses `ls` output from a fake ssh run ─────────────────


class FakeResult:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_remote_next_id_parses_existing_entries(mod):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return FakeResult(
            returncode=0,
            stdout="SIG-20260903-01_foo.md\nSIG-20260903-02_bar.md\nSIG-20260901-01_other.md\n",
        )

    sig = mod.remote_next_id("2026-09-03", "k2vps", "/opt/t1000/src", "t1000", run=fake_run)
    assert sig == "SIG-20260903-03"
    # Exactly one ssh call.
    assert len(calls) == 1
    cmd = calls[0]
    assert cmd[0] == "ssh"
    assert cmd[1] == "k2vps"
    assert "sudo -u t1000" in cmd[2]
    assert "ls" in cmd[2]
    assert "docs/research/signal-log/entries" in cmd[2]


def test_remote_next_id_empty_dir_starts_at_01(mod):
    sig = mod.remote_next_id(
        "2026-09-03", "k2vps", "/opt/t1000/src", "t1000",
        run=lambda *a, **k: FakeResult(returncode=0, stdout=""),
    )
    assert sig == "SIG-20260903-01"


def test_remote_next_id_ssh_failure_falls_back_to_01(mod):
    sig = mod.remote_next_id(
        "2026-09-03", "k2vps", "/opt/t1000/src", "t1000",
        run=lambda *a, **k: FakeResult(returncode=255, stdout="", stderr="conn refused"),
    )
    assert sig == "SIG-20260903-01"


# ── remote_write: refuses an existing remote file ───────────────────────────


def test_remote_write_refuses_existing_file(mod):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        # First call is `test -e`; returncode 0 means the file exists.
        return FakeResult(returncode=0)

    with pytest.raises(SystemExit) as exc:
        mod.remote_write(
            "docs/research/signal-log/entries/SIG-20260903-01_x.md",
            "body text",
            "k2vps", "/opt/t1000/src", "t1000",
            run=fake_run,
        )
    assert str(exc.value).startswith("exists:")
    # Refused before any write/index call.
    assert len(calls) == 1


def test_remote_write_succeeds_and_regenerates_index(mod):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        if len(calls) == 1:
            return FakeResult(returncode=1)  # test -e: does not exist
        return FakeResult(returncode=0)

    mod.remote_write(
        "docs/research/signal-log/entries/SIG-20260903-01_x.md",
        "body text",
        "k2vps", "/opt/t1000/src", "t1000",
        run=fake_run,
    )
    assert len(calls) == 3
    # tee call carried the body on stdin.
    tee_cmd, tee_kwargs = calls[1]
    assert "tee" in tee_cmd[2]
    assert tee_kwargs.get("input") == "body text"
    # index regen call.
    index_cmd, _ = calls[2]
    assert "signal_log_index.py --write" in index_cmd[2]


def test_remote_write_index_regen_failure_is_a_note_not_fatal(mod, capsys):
    def fake_run(cmd, **kwargs):
        if "test -e" in cmd[2]:
            return FakeResult(returncode=1)
        if "tee" in cmd[2]:
            return FakeResult(returncode=0)
        return FakeResult(returncode=1, stderr="index broke")

    # Must not raise.
    mod.remote_write(
        "docs/research/signal-log/entries/SIG-20260903-01_x.md",
        "body text",
        "k2vps", "/opt/t1000/src", "t1000",
        run=fake_run,
    )
    err = capsys.readouterr().err
    assert "NOTE" in err


# ── run_remote: dry-run performs no ssh ─────────────────────────────────────


def test_run_remote_dry_run_performs_no_ssh(mod, monkeypatch, capsys):
    def boom(*a, **k):
        raise AssertionError("ssh must not run under --dry-run")

    monkeypatch.setattr(mod, "remote_next_id", boom)
    monkeypatch.setattr(mod, "remote_write", boom)

    args = _args(remote=True, dry_run=True)
    mod.run_remote(args, "2026-09-03", "some-slug")

    out = capsys.readouterr().out.strip()
    assert out == (
        "k2vps:/opt/t1000/src/docs/research/signal-log/entries/"
        "SIG-20260903-NN_some-slug.md"
    )
