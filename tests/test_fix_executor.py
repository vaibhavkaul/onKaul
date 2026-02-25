from __future__ import annotations

from pathlib import Path

from tools import fix_executor


def test_repo_url_uses_configured_org(monkeypatch):
    monkeypatch.setattr(fix_executor.config, "GITHUB_ORG", "acme")

    assert fix_executor._repo_url("repo-x") == "https://github.com/acme/repo-x.git"


def test_extract_pr_url_prefers_marker_then_fallback():
    marked = "logs...\nPR_URL: https://github.com/acme/repo/pull/123\nmore"
    fallback = "see https://github.com/acme/repo/pull/456 for details"
    missing = "no pr url"

    assert fix_executor._extract_pr_url(marked) == "https://github.com/acme/repo/pull/123"
    assert fix_executor._extract_pr_url(fallback) == "https://github.com/acme/repo/pull/456"
    assert fix_executor._extract_pr_url(missing) is None


def test_truncate_keeps_short_and_truncates_long():
    assert fix_executor._truncate("abc", limit=10) == "abc"
    out = fix_executor._truncate("x" * 20, limit=10)
    assert out.endswith("...[truncated]")
    assert out.startswith("x" * 10)


def test_create_pr_from_patch_rejects_invalid_patch_format(tmp_path, monkeypatch):
    monkeypatch.setattr(fix_executor.config, "FIX_WORKSPACE_DIR", tmp_path)

    result = fix_executor.create_pr_from_patch(
        repo="repo-a",
        patch="not-a-unified-diff",
        title="t",
        body="b",
    )

    assert "Invalid patch format" in result["error"]


def test_create_pr_from_patch_rejects_ellipsis_patch(tmp_path, monkeypatch):
    monkeypatch.setattr(fix_executor.config, "FIX_WORKSPACE_DIR", tmp_path)

    bad_patch = "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-...\n+x\n"
    result = fix_executor.create_pr_from_patch(
        repo="repo-a",
        patch=bad_patch,
        title="t",
        body="b",
    )

    assert "Do not truncate or use ellipses" in result["error"]


def test_create_pr_from_patch_clone_failure_returns_error(tmp_path, monkeypatch):
    monkeypatch.setattr(fix_executor.config, "FIX_WORKSPACE_DIR", tmp_path)
    monkeypatch.setattr(
        fix_executor,
        "_clone_repo",
        lambda repo, repo_dir, work_root: (1, "", "clone failed"),
    )

    patch = "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-a\n+b\n"
    result = fix_executor.create_pr_from_patch(
        repo="repo-a",
        patch=patch,
        title="t",
        body="b",
    )

    assert result["error"] == "git clone failed: clone failed"


def test_create_pr_from_patch_happy_path(tmp_path, monkeypatch):
    monkeypatch.setattr(fix_executor.config, "FIX_WORKSPACE_DIR", tmp_path)
    monkeypatch.setattr(fix_executor.config, "GITHUB_ORG", "acme")

    repo = "repo-a"
    repo_dir = tmp_path / repo
    repo_dir.mkdir(parents=True)

    def fake_run(cmd: list[str], cwd: Path, timeout: int = 120):
        if cmd[:3] == ["git", "fetch", "--prune"]:
            return 0, "", ""
        if cmd[:3] == ["git", "rev-parse", "--verify"]:
            return 0, "ok", ""
        if cmd[:3] == ["git", "reset", "--hard"]:
            return 0, "", ""
        if cmd[:2] == ["git", "clean"]:
            return 0, "", ""
        if cmd[:3] == ["git", "checkout", "-B"]:
            return 0, "", ""
        if cmd[:2] == ["git", "apply"]:
            return 0, "", ""
        if cmd[:3] == ["git", "status", "--porcelain"]:
            return 0, " M a.txt", ""
        if cmd[:2] == ["git", "add"]:
            return 0, "", ""
        if cmd[:2] == ["git", "commit"]:
            return 0, "", ""
        if cmd[:4] == ["git", "push", "-u", "origin"]:
            return 0, "", ""
        if cmd[:3] == ["gh", "pr", "create"]:
            return 0, "https://github.com/acme/repo-a/pull/99", ""
        return 0, "", ""

    monkeypatch.setattr(fix_executor, "_run", fake_run)

    patch = "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-a\n+b\n"
    result = fix_executor.create_pr_from_patch(
        repo=repo,
        patch=patch,
        title="Fix",
        body="Body",
    )

    assert result["success"] is True
    assert result["pr_url"] == "https://github.com/acme/repo-a/pull/99"
    assert result["branch"].startswith("onkaul/fix-")


def test_create_pr_from_plan_prepare_repo_failure(monkeypatch):
    monkeypatch.setattr(fix_executor, "_prepare_repo", lambda repo, base: (None, "prep failed"))

    result = fix_executor.create_pr_from_plan(
        repo="repo-a",
        title="Fix",
        body="Body",
        context="ctx",
    )

    assert result["error"] == "prep failed"


def test_create_pr_from_plan_plan_step_failure(tmp_path, monkeypatch):
    repo_dir = tmp_path / "repo-a"
    repo_dir.mkdir(parents=True)
    monkeypatch.setattr(fix_executor.config, "FIX_WORKSPACE_DIR", tmp_path)
    monkeypatch.setattr(fix_executor, "_prepare_repo", lambda repo, base: (repo_dir, "main"))
    monkeypatch.setattr(fix_executor.config, "FIX_EXECUTOR_ENGINE", "codex")
    monkeypatch.setattr(fix_executor.config, "CODEX_PLAN_CMD", "codex exec")
    monkeypatch.setattr(fix_executor.config, "CODEX_TIMEOUT_SECONDS", 1)
    monkeypatch.setattr(
        fix_executor, "_run_headless", lambda *args, **kwargs: (1, "", "plan failed")
    )

    result = fix_executor.create_pr_from_plan(
        repo="repo-a",
        title="Fix",
        body="Body",
        context="ctx",
    )

    assert "Plan step failed: plan failed" in result["error"]


def test_create_pr_from_plan_no_changes_after_apply(tmp_path, monkeypatch):
    repo_dir = tmp_path / "repo-a"
    repo_dir.mkdir(parents=True)
    monkeypatch.setattr(fix_executor.config, "FIX_WORKSPACE_DIR", tmp_path)
    monkeypatch.setattr(fix_executor, "_prepare_repo", lambda repo, base: (repo_dir, "main"))
    monkeypatch.setattr(fix_executor.config, "FIX_EXECUTOR_ENGINE", "codex")
    monkeypatch.setattr(fix_executor.config, "CODEX_PLAN_CMD", "codex plan")
    monkeypatch.setattr(fix_executor.config, "CODEX_APPLY_CMD", "codex apply")
    monkeypatch.setattr(fix_executor.config, "CODEX_TIMEOUT_SECONDS", 1)

    calls = {"n": 0}

    def fake_run_headless(cmd_str: str, prompt: str, cwd: Path, timeout: int):
        calls["n"] += 1
        if calls["n"] == 1:
            return 0, "- step1\n- step2", ""
        return 0, "applied", ""

    def fake_run(cmd: list[str], cwd: Path, timeout: int = 120):
        if cmd[:3] == ["git", "checkout", "-B"]:
            return 0, "", ""
        if cmd[:3] == ["git", "status", "--porcelain"]:
            return 0, "", ""
        if cmd[:3] == ["git", "reset", "--hard"]:
            return 0, "", ""
        if cmd[:2] == ["git", "clean"]:
            return 0, "", ""
        return 0, "", ""

    monkeypatch.setattr(fix_executor, "_run_headless", fake_run_headless)
    monkeypatch.setattr(fix_executor, "_run", fake_run)

    result = fix_executor.create_pr_from_plan(
        repo="repo-a",
        title="Fix",
        body="Body",
        context="ctx",
    )

    assert result["error"] == "Codex produced no changes"
    assert "plan_path" in result
