from __future__ import annotations

import subprocess

from tools import local_code


def test_repo_url_uses_configured_org(monkeypatch):
    monkeypatch.setattr(local_code.config, "GITHUB_ORG", "acme")

    assert local_code._repo_url("repo-a") == "https://github.com/acme/repo-a.git"


def test_gh_available_handles_missing_command(monkeypatch):
    def _raise(*_args, **_kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(local_code.subprocess, "run", _raise)

    assert local_code._gh_available() is False


def test_clone_repo_uses_gh_when_available(monkeypatch, tmp_path):
    monkeypatch.setattr(local_code.config, "GITHUB_ORG", "acme")
    monkeypatch.setattr(local_code, "_gh_available", lambda: True)
    captured = {"cmd": None}

    def _fake_run(cmd):
        captured["cmd"] = cmd
        return 0, "", ""

    monkeypatch.setattr(local_code, "_run_cmd", _fake_run)

    local_code._clone_repo("repo-a", tmp_path / "repo-a")

    assert captured["cmd"][0:3] == ["gh", "repo", "clone"]


def test_clone_repo_uses_git_when_gh_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(local_code.config, "GITHUB_ORG", "acme")
    monkeypatch.setattr(local_code, "_gh_available", lambda: False)
    captured = {"cmd": None}

    def _fake_run(cmd):
        captured["cmd"] = cmd
        return 0, "", ""

    monkeypatch.setattr(local_code, "_run_cmd", _fake_run)

    local_code._clone_repo("repo-a", tmp_path / "repo-a")

    assert captured["cmd"][0:2] == ["git", "clone"]


def test_ensure_repo_clone_failure_returns_error(monkeypatch, tmp_path):
    monkeypatch.setattr(local_code.config, "WORKSPACE_DIR", tmp_path)
    monkeypatch.setattr(
        local_code, "_clone_repo", lambda *_args, **_kwargs: (1, "", "clone failed")
    )

    out = local_code.ensure_repo("repo-a")

    assert out["error"] == "git clone failed: clone failed"


def test_ensure_repo_clone_success(monkeypatch, tmp_path):
    monkeypatch.setattr(local_code.config, "WORKSPACE_DIR", tmp_path)
    monkeypatch.setattr(local_code, "_clone_repo", lambda *_args, **_kwargs: (0, "", ""))

    out = local_code.ensure_repo("repo-a")

    assert out["cloned"] is True
    assert out["path"].endswith("repo-a")


def test_ensure_repo_pull_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(local_code.config, "WORKSPACE_DIR", tmp_path)
    repo_path = tmp_path / "repo-a"
    repo_path.mkdir(parents=True)

    monkeypatch.setattr(
        local_code.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="fail"
        ),
    )

    out = local_code.ensure_repo("repo-a")

    assert out["error"] == "git pull failed: fail"


def test_search_code_local_rg_success(monkeypatch, tmp_path):
    monkeypatch.setattr(local_code.config, "WORKSPACE_DIR", tmp_path)
    repo_path = tmp_path / "repo-a"
    repo_path.mkdir(parents=True)
    (repo_path / "a.txt").write_text("hello", encoding="utf-8")

    monkeypatch.setattr(
        local_code, "ensure_repo", lambda _repo: {"pulled": True, "path": str(repo_path)}
    )
    monkeypatch.setattr(
        local_code.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=str(repo_path / "a.txt") + "\n",
            stderr="",
        ),
    )

    out = local_code.search_code_local("repo-a", "hello")

    assert out["total_count"] == 1
    assert out["matches"][0]["path"] == "a.txt"


def test_search_code_local_falls_back_to_git_grep(monkeypatch, tmp_path):
    monkeypatch.setattr(local_code.config, "WORKSPACE_DIR", tmp_path)
    repo_path = tmp_path / "repo-a"
    repo_path.mkdir(parents=True)

    monkeypatch.setattr(
        local_code, "ensure_repo", lambda _repo: {"pulled": True, "path": str(repo_path)}
    )

    calls = {"n": 0}

    def _fake_run(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise FileNotFoundError
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="sub/a.txt\n", stderr="")

    monkeypatch.setattr(local_code.subprocess, "run", _fake_run)

    out = local_code.search_code_local("repo-a", "hello")

    assert out["total_count"] == 1
    assert out["matches"][0]["path"] == "sub/a.txt"


def test_read_file_local_handles_missing_and_unicode(monkeypatch, tmp_path):
    monkeypatch.setattr(local_code.config, "WORKSPACE_DIR", tmp_path)
    repo_path = tmp_path / "repo-a"
    repo_path.mkdir(parents=True)
    monkeypatch.setattr(
        local_code, "ensure_repo", lambda _repo: {"pulled": True, "path": str(repo_path)}
    )

    missing = local_code.read_file_local("repo-a", "missing.txt")
    assert missing["error"] == "File not found: missing.txt"

    file_path = repo_path / "bin.txt"
    file_path.write_bytes(b"\xffabc")
    out = local_code.read_file_local("repo-a", "bin.txt")
    assert out["path"] == "bin.txt"
    assert "\ufffd" in out["content"]


def test_list_directory_local_success_and_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(local_code.config, "WORKSPACE_DIR", tmp_path)
    repo_path = tmp_path / "repo-a"
    repo_path.mkdir(parents=True)
    (repo_path / "a.txt").write_text("x", encoding="utf-8")
    (repo_path / "sub").mkdir()

    monkeypatch.setattr(
        local_code, "ensure_repo", lambda _repo: {"pulled": True, "path": str(repo_path)}
    )

    missing = local_code.list_directory_local("repo-a", "nope")
    assert missing["error"] == "Directory not found: nope"

    out = local_code.list_directory_local("repo-a", "")
    names = {item["name"] for item in out["items"]}
    assert {"a.txt", "sub"} <= names
