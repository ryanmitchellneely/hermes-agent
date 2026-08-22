"""MESH-INFRA-2: board policy defaults code cards to worktree isolation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_WORKTREE = Path(__file__).resolve().parents[2]
if str(_WORKTREE) not in sys.path:
    sys.path.insert(0, str(_WORKTREE))

from hermes_cli import kanban_db as kb
from hermes_cli import projects_db as pdb


@pytest.fixture
def fresh_home(tmp_path, monkeypatch):
    home = tmp_path / "hermes_home"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    for var in (
        "HERMES_KANBAN_DB",
        "HERMES_KANBAN_WORKSPACES_ROOT",
        "HERMES_KANBAN_HOME",
        "HERMES_KANBAN_BOARD",
    ):
        monkeypatch.delenv(var, raising=False)
    try:
        import hermes_constants

        hermes_constants._cached_default_hermes_root = None  # type: ignore[attr-defined]
    except Exception:
        pass
    kb._INITIALIZED_PATHS.clear()
    return home


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main", str(repo)],
        check=True,
        capture_output=True,
        text=True,
    )
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=t@example.com",
            "-c",
            "commit.gpgsign=false",
            "add",
            "README.md",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=t@example.com",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-m",
            "init",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return repo


def test_git_default_workdir_omitted_kind_is_worktree(fresh_home, tmp_path):
    repo = _make_repo(tmp_path)
    kb.create_board("code", name="Code", default_workdir=str(repo))
    conn = kb.connect(board="code")
    try:
        tid = kb.create_task(conn, title="ship it", board="code")
        task = kb.get_task(conn, tid)
        assert task.workspace_kind == "worktree"
        # Anchored under board default_workdir (repo root) until resolve, or
        # pre-keyed in the sibling container when project_repo pathing runs.
        assert task.workspace_path in {
            str(repo),
            str(repo.parent / (repo.name + ".worktrees") / tid),
        }
    finally:
        conn.close()


def test_explicit_scratch_opts_out(fresh_home, tmp_path):
    repo = _make_repo(tmp_path)
    kb.create_board("code2", name="Code2", default_workdir=str(repo))
    conn = kb.connect(board="code2")
    try:
        tid = kb.create_task(
            conn, title="ops note", board="code2", workspace_kind="scratch"
        )
        assert kb.get_task(conn, tid).workspace_kind == "scratch"
    finally:
        conn.close()


def test_no_default_workdir_stays_scratch(fresh_home):
    kb.create_board("ops", name="Ops")
    conn = kb.connect(board="ops")
    try:
        tid = kb.create_task(conn, title="plain", board="ops")
        assert kb.get_task(conn, tid).workspace_kind == "scratch"
    finally:
        conn.close()


def test_dir_main_repo_rewritten_to_worktree(fresh_home, tmp_path):
    repo = _make_repo(tmp_path)
    kb.create_board("code3", name="Code3", default_workdir=str(repo))
    conn = kb.connect(board="code3")
    try:
        tid = kb.create_task(
            conn,
            title="old habit",
            board="code3",
            workspace_kind="dir",
            workspace_path=str(repo),
        )
        task = kb.get_task(conn, tid)
        assert task.workspace_kind == "worktree"
        assert task.workspace_path == str(
            repo.parent / (repo.name + ".worktrees") / tid
        )
    finally:
        conn.close()


def test_explicit_default_workspace_kind_scratch_wins(fresh_home, tmp_path):
    repo = _make_repo(tmp_path)
    kb.create_board(
        "mixed",
        name="Mixed",
        default_workdir=str(repo),
        default_workspace_kind="scratch",
    )
    conn = kb.connect(board="mixed")
    try:
        tid = kb.create_task(conn, title="stay scratch", board="mixed")
        assert kb.get_task(conn, tid).workspace_kind == "scratch"
    finally:
        conn.close()


def test_board_project_bind_sets_project_id(fresh_home, tmp_path):
    repo = _make_repo(tmp_path)
    kb.create_board("meshx", name="MeshX", default_workdir=str(repo))
    with pdb.connect_closing() as pconn:
        pid = pdb.create_project(
            pconn, name="T1000", primary_path=str(repo), board_slug="meshx"
        )
        proj = pdb.get_project(pconn, pid)
    from hermes_cli.projects_cmd import _sync_board_default_workdir

    _sync_board_default_workdir(proj, "meshx")
    meta = kb.read_board_metadata("meshx")
    assert meta["project_id"] == pid
    assert meta["default_workdir"] == str(repo)

    conn = kb.connect(board="meshx")
    try:
        tid = kb.create_task(conn, title="inherit project", board="meshx")
        task = kb.get_task(conn, tid)
        assert task.project_id == pid
        assert task.workspace_kind == "worktree"
    finally:
        conn.close()


def test_gc_stale_worktrees_only_removes_aged_terminal(fresh_home, tmp_path):
    repo = _make_repo(tmp_path)
    target = repo / ".worktrees" / "t_oldtask1"
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "worktree",
            "add",
            "-b",
            "wt/t_oldtask1",
            str(target),
            "HEAD",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    kb.create_board("gcboard", name="GC", default_workdir=str(repo))
    conn = kb.connect(board="gcboard")
    try:
        tid = kb.create_task(
            conn,
            title="old",
            board="gcboard",
            workspace_kind="worktree",
            workspace_path=str(target),
            branch_name="wt/t_oldtask1",
        )
        # Force id + terminal + aged timestamps so GC eligibility matches path.
        conn.execute(
            "UPDATE tasks SET id = ?, workspace_path = ?, status = 'done', "
            "completed_at = 1, created_at = 1 WHERE id = ?",
            ("t_oldtask1", str(target), tid),
        )
        conn.commit()
        stats = kb.gc_stale_worktrees(conn, older_than_seconds=0, board="gcboard")
        assert stats["removed"] == 1
        assert not target.exists()
    finally:
        conn.close()


def test_resolve_workspace_materializes_sibling_worktree(fresh_home, tmp_path):
    """PB-012 clone-twin cure: new worktrees land OUTSIDE the clone tree."""
    repo = _make_repo(tmp_path)
    kb.create_board("sib", name="Sib", default_workdir=str(repo))
    conn = kb.connect(board="sib")
    try:
        tid = kb.create_task(conn, title="edit a file", board="sib")
        task = kb.get_task(conn, tid)
        resolved = kb.resolve_workspace(task, board="sib")
        expected = repo.parent / (repo.name + ".worktrees") / tid
        assert resolved == expected
        assert resolved.exists()
        # The clone must not be an ancestor of the workspace.
        assert repo.resolve() not in resolved.resolve().parents
        # Still a linked worktree of the repo (same git common dir).
        out = subprocess.run(
            ["git", "-C", str(resolved), "rev-parse", "--git-common-dir"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert Path(out).resolve() == (repo / ".git").resolve()
    finally:
        conn.close()


def test_resolve_workspace_reuses_legacy_in_repo_checkout(fresh_home, tmp_path):
    """Pre-relocation tasks keep their in-repo checkout across re-dispatch."""
    repo = _make_repo(tmp_path)
    kb.create_board("leg", name="Leg", default_workdir=str(repo))
    conn = kb.connect(board="leg")
    try:
        tid = kb.create_task(conn, title="old task", board="leg")
        legacy = repo / ".worktrees" / tid
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "worktree",
                "add",
                "-b",
                f"wt/{tid}",
                str(legacy),
                "HEAD",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        task = kb.get_task(conn, tid)
        resolved = kb.resolve_workspace(task, board="leg")
        assert resolved == legacy
    finally:
        conn.close()


def test_gc_removes_sibling_layout_worktree(fresh_home, tmp_path):
    repo = _make_repo(tmp_path)
    target = repo.parent / (repo.name + ".worktrees") / "t_sibtask1"
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "worktree",
            "add",
            "-b",
            "wt/t_sibtask1",
            str(target),
            "HEAD",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    kb.create_board("gcsib", name="GCSib", default_workdir=str(repo))
    conn = kb.connect(board="gcsib")
    try:
        tid = kb.create_task(
            conn,
            title="old sibling",
            board="gcsib",
            workspace_kind="worktree",
            workspace_path=str(target),
            branch_name="wt/t_sibtask1",
        )
        conn.execute(
            "UPDATE tasks SET id = ?, workspace_path = ?, status = 'done', "
            "completed_at = 1, created_at = 1 WHERE id = ?",
            ("t_sibtask1", str(target), tid),
        )
        conn.commit()
        stats = kb.gc_stale_worktrees(conn, older_than_seconds=0, board="gcsib")
        assert stats["removed"] == 1
        assert not target.exists()
    finally:
        conn.close()
