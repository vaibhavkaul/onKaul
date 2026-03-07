from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest
from fastapi import HTTPException

import api.sandbox as sandbox_module
from api.sandbox import _git, _repo_snapshot, _require_sandbox, _sandbox_repos


# ---------------------------------------------------------------------------
# _sandbox_repos
# ---------------------------------------------------------------------------

def test_sandbox_repos_returns_only_hot_reload_repos(monkeypatch):
    fake = {
        "static-site": {
            "name": "static-site",
            "org": "acme",
            "hotReloadSupport": True,
            "sandbox": {"appType": "static", "previewPort": 8080},
        },
        "api-service": {
            "name": "api-service",
            "org": "acme",
            "hotReloadSupport": False,
            "sandbox": {"appType": "dev-server", "previewPort": 3000},
        },
        "docs-site": {
            "name": "docs-site",
            "org": "acme",
            # no hotReloadSupport
        },
    }
    monkeypatch.setattr(sandbox_module, "REPOSITORIES", fake)
    result = _sandbox_repos()
    assert len(result) == 1
    r = result[0]
    assert r["key"] == "static-site"
    assert r["name"] == "static-site"
    assert r["org"] == "acme"
    assert r["sandbox"]["appType"] == "static"


def test_sandbox_repos_requires_sandbox_config(monkeypatch):
    fake = {
        "no-sandbox": {
            "name": "no-sandbox",
            "org": "acme",
            "hotReloadSupport": True,
            # sandbox key absent
        },
    }
    monkeypatch.setattr(sandbox_module, "REPOSITORIES", fake)
    assert _sandbox_repos() == []


def test_sandbox_repos_empty_when_no_repos(monkeypatch):
    monkeypatch.setattr(sandbox_module, "REPOSITORIES", {})
    assert _sandbox_repos() == []


# ---------------------------------------------------------------------------
# _repo_snapshot
# ---------------------------------------------------------------------------

def test_repo_snapshot_returns_mtimes(tmp_path):
    (tmp_path / "index.html").write_text("<h1>Hello</h1>")
    (tmp_path / "style.css").write_text("body {}")
    snap = _repo_snapshot(str(tmp_path))
    assert len(snap) == 2
    for v in snap.values():
        assert isinstance(v, float)


def test_repo_snapshot_excludes_git_dir(tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main")
    (tmp_path / "index.html").write_text("<h1>Hello</h1>")
    snap = _repo_snapshot(str(tmp_path))
    assert len(snap) == 1
    assert not any(".git" in k for k in snap)


def test_repo_snapshot_detects_new_file(tmp_path):
    (tmp_path / "index.html").write_text("<h1>v1</h1>")
    snap1 = _repo_snapshot(str(tmp_path))
    (tmp_path / "about.html").write_text("<h1>About</h1>")
    snap2 = _repo_snapshot(str(tmp_path))
    assert snap1 != snap2


def test_repo_snapshot_detects_mtime_change(tmp_path):
    f = tmp_path / "index.html"
    f.write_text("<h1>v1</h1>")
    snap1 = _repo_snapshot(str(tmp_path))
    # Explicitly bump mtime by +1 s so the test is never flaky
    new_mtime = os.path.getmtime(str(f)) + 1.0
    os.utime(str(f), (new_mtime, new_mtime))
    snap2 = _repo_snapshot(str(tmp_path))
    assert snap1 != snap2


def test_repo_snapshot_returns_empty_for_empty_dir(tmp_path):
    assert _repo_snapshot(str(tmp_path)) == {}


def test_repo_snapshot_recurses_subdirectories(tmp_path):
    sub = tmp_path / "css"
    sub.mkdir()
    (sub / "main.css").write_text("body {}")
    (tmp_path / "index.html").write_text("<html/>")
    snap = _repo_snapshot(str(tmp_path))
    assert len(snap) == 2


# ---------------------------------------------------------------------------
# _require_sandbox
# ---------------------------------------------------------------------------

def test_require_sandbox_raises_401_without_user(monkeypatch):
    monkeypatch.setattr(sandbox_module, "_active", {})
    with pytest.raises(HTTPException) as exc:
        _require_sandbox(None, "my-repo")
    assert exc.value.status_code == 401


def test_require_sandbox_raises_503_when_not_active(monkeypatch):
    monkeypatch.setattr(sandbox_module, "_active", {})
    with pytest.raises(HTTPException) as exc:
        _require_sandbox("user-abc", "my-repo")
    assert exc.value.status_code == 503


def test_require_sandbox_returns_info_when_active(monkeypatch):
    info = {"container_name": "c1", "preview_port": 8080, "local_repo_path": "/tmp/r"}
    monkeypatch.setattr(sandbox_module, "_active", {("user-abc", "my-repo"): info})
    result = _require_sandbox("user-abc", "my-repo")
    assert result is info


def test_require_sandbox_matches_exact_slot(monkeypatch):
    info = {"container_name": "c1", "preview_port": 8080, "local_repo_path": "/tmp/r"}
    monkeypatch.setattr(sandbox_module, "_active", {("user-abc", "repo-a"): info})
    # Different repo — should 503
    with pytest.raises(HTTPException) as exc:
        _require_sandbox("user-abc", "repo-b")
    assert exc.value.status_code == 503


# ---------------------------------------------------------------------------
# _git
# ---------------------------------------------------------------------------

def test_git_returns_completed_process(tmp_path):
    result = _git(["--version"], str(tmp_path))
    assert isinstance(result, subprocess.CompletedProcess)
    assert "git" in result.stdout.lower()


def test_git_fails_on_non_repo(tmp_path):
    result = _git(["log"], str(tmp_path))
    assert result.returncode != 0


def test_git_rev_parse_returns_branch(tmp_path):
    """Full round-trip: init, commit, check branch name."""
    subprocess.run(["git", "init", tmp_path], capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t.com"], capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "T"], capture_output=True)
    (tmp_path / "f.txt").write_text("hi")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "init"], capture_output=True)
    result = _git(["rev-parse", "--abbrev-ref", "HEAD"], str(tmp_path))
    assert result.returncode == 0
    assert result.stdout.strip() in ("main", "master")


def test_git_status_porcelain_shows_changes(tmp_path):
    subprocess.run(["git", "init", tmp_path], capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t.com"], capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "T"], capture_output=True)
    f = tmp_path / "f.txt"
    f.write_text("original")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "init"], capture_output=True)
    f.write_text("modified")
    result = _git(["status", "--porcelain"], str(tmp_path))
    assert result.returncode == 0
    assert result.stdout.strip() != ""
