"""Create PRs by applying patches in ephemeral workspaces."""

import os
import shutil
import subprocess
import uuid
from pathlib import Path

from config import config


def _repo_url(repo: str) -> str:
    org = config.GITHUB_ORG
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        return f"https://{token}@github.com/{org}/{repo}.git"
    return f"https://github.com/{org}/{repo}.git"


def _run(cmd: list[str], cwd: Path, timeout: int = 120) -> tuple[int, str, str]:
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def create_pr_from_patch(
    repo: str,
    patch: str,
    title: str,
    body: str,
    base_branch: str = "main",
) -> dict:
    """
    Create a PR by applying a unified diff patch in a temporary workspace.

    Args:
        repo: Repository name (e.g., 'appian-server')
        patch: Unified diff patch, paths relative to repo root
        title: PR title
        body: PR body/description
        base_branch: Base branch for PR (default: main)

    Returns:
        Dict with pr_url or error
    """
    work_root = config.FIX_WORKSPACE_DIR.resolve()
    work_root.mkdir(parents=True, exist_ok=True)

    # Use a fixed workspace per repo
    repo_dir = (work_root / repo).resolve()

    work_id = uuid.uuid4().hex[:8]
    effective_base = base_branch

    try:
        if "diff --git " not in patch or "\n--- " not in patch or "\n+++ " not in patch or "\n@@ " not in patch:
            return {"error": "Invalid patch format. Provide a full unified diff with diff --git/---/+++ and @@ headers."}
        if "..." in patch or "…" in patch:
            return {"error": "Invalid patch format. Do not truncate or use ellipses in diffs."}
        if not repo_dir.exists():
            print(f"🛠️  Fix workspace: cloning {repo} into {repo_dir}")
            code, out, err = _run(
                ["git", "clone", _repo_url(repo), str(repo_dir)],
                work_root,
                timeout=300,
            )
            if code != 0:
                try:
                    if repo_dir.exists():
                        shutil.rmtree(repo_dir)
                except Exception:
                    pass
                return {"error": f"git clone failed: {err or out}"}
            print("✅ Clone complete")
        else:
            print(f"🛠️  Fix workspace: reusing {repo_dir}")
            code, out, err = _run(["git", "fetch", "--prune", "origin"], repo_dir)
            if code != 0:
                return {"error": f"git fetch failed: {err or out}"}
            print("✅ Fetch complete")

        # Determine base branch (fallback to origin/HEAD if requested base missing)
        effective_base = base_branch
        code, out, err = _run(["git", "rev-parse", "--verify", f"origin/{base_branch}"], repo_dir)
        if code != 0:
            code, out, err = _run(["git", "symbolic-ref", "refs/remotes/origin/HEAD"], repo_dir)
            if code == 0 and out.startswith("refs/remotes/origin/"):
                effective_base = out.replace("refs/remotes/origin/", "")

        # Reset workspace to a clean state
        code, out, err = _run(["git", "reset", "--hard", f"origin/{effective_base}"], repo_dir)
        if code != 0:
            return {"error": f"git reset failed: {err or out}"}
        code, out, err = _run(["git", "clean", "-fd"], repo_dir)
        if code != 0:
            return {"error": f"git clean failed: {err or out}"}
        print(f"✅ Workspace reset to origin/{effective_base}")

        branch = f"onkaul/fix-{work_id}"
        code, out, err = _run(["git", "checkout", "-B", branch, f"origin/{effective_base}"], repo_dir)
        if code != 0:
            return {"error": f"git checkout failed: {err or out}"}
        print(f"✅ Checked out {branch} from {effective_base}")

        patch_file = repo_dir / ".onkaul.patch"
        patch_file.write_text(patch, encoding="utf-8")

        code, out, err = _run(["git", "apply", "--whitespace=fix", str(patch_file)], repo_dir)
        if code != 0:
            patch_preview = "\n".join(patch.splitlines()[:40])
            print(f"⚠️  Patch preview (first 40 lines):\n{patch_preview}")
            return {"error": f"git apply failed: {err or out}"}
        print("✅ Patch applied")

        # Remove patch file so it doesn't get committed
        try:
            patch_file.unlink(missing_ok=True)
        except Exception:
            pass

        code, out, err = _run(["git", "status", "--porcelain"], repo_dir)
        if code != 0:
            return {"error": f"git status failed: {err or out}"}
        if not out:
            return {"error": "Patch produced no changes"}
        print(f"✅ Changes detected ({len(out.splitlines())} files)")

        code, out, err = _run(["git", "add", "-A"], repo_dir)
        if code != 0:
            return {"error": f"git add failed: {err or out}"}
        print("✅ Staged changes")

        commit_message = title.strip() or f"onKaul fix {work_id}"
        code, out, err = _run(["git", "commit", "-m", commit_message], repo_dir)
        if code != 0:
            return {"error": f"git commit failed: {err or out}"}
        print("✅ Commit created")

        code, out, err = _run(["git", "push", "-u", "origin", branch], repo_dir)
        if code != 0:
            return {"error": f"git push failed: {err or out}"}
        print("✅ Branch pushed")

        code, out, err = _run(
            [
                "gh",
                "pr",
                "create",
                "--repo",
                f"{config.GITHUB_ORG}/{repo}",
                "--base",
                effective_base,
                "--head",
                branch,
                "--title",
                title,
                "--body",
                body,
            ],
            repo_dir,
        )
        if code != 0:
            return {"error": f"gh pr create failed: {err or out}"}
        print("✅ PR created")

        pr_url = out.strip()
        return {"success": True, "pr_url": pr_url, "branch": branch}

    except Exception as e:
        return {"error": f"Failed to create PR: {str(e)}"}

    finally:
        # Keep workspace for reuse; leave clean after job
        try:
            if repo_dir.exists():
                _run(["git", "reset", "--hard", f"origin/{effective_base}"], repo_dir)
                _run(["git", "clean", "-fd"], repo_dir)
                print(f"🧹 Fix workspace cleaned: {repo_dir}")
        except Exception as cleanup_error:
            print(f"⚠️  Failed to clean fix workspace: {cleanup_error}")


def create_pr_from_plan(
    repo: str,
    title: str,
    body: str,
    edits: list[dict],
    base_branch: str = "main",
) -> dict:
    """
    Create a PR by applying line-based edits in a fixed workspace.

    Edits format:
      - {op: "replace", path, start_line, end_line, new_lines: [..]}
      - {op: "insert", path, start_line, new_lines: [..]}
      - {op: "delete", path, start_line, end_line}
    """
    work_root = config.FIX_WORKSPACE_DIR.resolve()
    work_root.mkdir(parents=True, exist_ok=True)

    repo_dir = (work_root / repo).resolve()
    work_id = uuid.uuid4().hex[:8]
    effective_base = base_branch

    try:
        if not repo_dir.exists():
            print(f"🛠️  Fix workspace: cloning {repo} into {repo_dir}")
            code, out, err = _run(
                ["git", "clone", _repo_url(repo), str(repo_dir)],
                work_root,
                timeout=300,
            )
            if code != 0:
                try:
                    if repo_dir.exists():
                        shutil.rmtree(repo_dir)
                except Exception:
                    pass
                return {"error": f"git clone failed: {err or out}"}
            print("✅ Clone complete")
        else:
            print(f"🛠️  Fix workspace: reusing {repo_dir}")
            code, out, err = _run(["git", "fetch", "--prune", "origin"], repo_dir)
            if code != 0:
                return {"error": f"git fetch failed: {err or out}"}
            print("✅ Fetch complete")

        # Determine base branch (fallback to origin/HEAD if requested base missing)
        code, out, err = _run(["git", "rev-parse", "--verify", f"origin/{base_branch}"], repo_dir)
        if code != 0:
            code, out, err = _run(["git", "symbolic-ref", "refs/remotes/origin/HEAD"], repo_dir)
            if code == 0 and out.startswith("refs/remotes/origin/"):
                effective_base = out.replace("refs/remotes/origin/", "")

        # Reset workspace to a clean state
        code, out, err = _run(["git", "reset", "--hard", f"origin/{effective_base}"], repo_dir)
        if code != 0:
            return {"error": f"git reset failed: {err or out}"}
        code, out, err = _run(["git", "clean", "-fd"], repo_dir)
        if code != 0:
            return {"error": f"git clean failed: {err or out}"}
        print(f"✅ Workspace reset to origin/{effective_base}")

        # Apply edits
        for edit in edits:
            op = edit.get("op")
            path = edit.get("path")
            if not op or not path:
                return {"error": "Invalid edit: missing op or path"}
            file_path = repo_dir / path
            if not file_path.exists():
                return {"error": f"File not found: {path}"}

            raw = file_path.read_text(encoding="utf-8", errors="replace")
            lines = raw.splitlines(keepends=True)
            had_trailing_newline = raw.endswith("\n")

            def _norm_new_lines(new_lines: list[str]) -> list[str]:
                joined = "\n".join(new_lines)
                if joined:
                    if had_trailing_newline and not joined.endswith("\n"):
                        joined += "\n"
                return joined.splitlines(keepends=True)

            if op == "replace":
                start = int(edit.get("start_line", 0))
                end = int(edit.get("end_line", 0))
                new_lines = edit.get("new_lines", [])
                if start < 1 or end < start:
                    return {"error": f"Invalid replace range for {path}: {start}-{end}"}
                print(f"✏️  Replace lines {start}-{end} in {path}")
                lines[start - 1 : end] = _norm_new_lines(new_lines)
            elif op == "insert":
                start = int(edit.get("start_line", 0))
                new_lines = edit.get("new_lines", [])
                if start < 1:
                    return {"error": f"Invalid insert line for {path}: {start}"}
                print(f"➕ Insert before line {start} in {path}")
                lines[start - 1 : start - 1] = _norm_new_lines(new_lines)
            elif op == "delete":
                start = int(edit.get("start_line", 0))
                end = int(edit.get("end_line", 0))
                if start < 1 or end < start:
                    return {"error": f"Invalid delete range for {path}: {start}-{end}"}
                print(f"➖ Delete lines {start}-{end} in {path}")
                del lines[start - 1 : end]
            else:
                return {"error": f"Unknown edit op: {op}"}

            file_path.write_text("".join(lines), encoding="utf-8")

        branch = f"onkaul/fix-{work_id}"
        code, out, err = _run(["git", "checkout", "-B", branch, f"origin/{effective_base}"], repo_dir)
        if code != 0:
            return {"error": f"git checkout failed: {err or out}"}
        print(f"✅ Checked out {branch} from {effective_base}")

        code, out, err = _run(["git", "status", "--porcelain"], repo_dir)
        if code != 0:
            return {"error": f"git status failed: {err or out}"}
        if not out:
            return {"error": "Edits produced no changes"}
        print(f"✅ Changes detected ({len(out.splitlines())} files)")

        code, out, err = _run(["git", "add", "-A"], repo_dir)
        if code != 0:
            return {"error": f"git add failed: {err or out}"}
        print("✅ Staged changes")

        commit_message = title.strip() or f"onKaul fix {work_id}"
        code, out, err = _run(["git", "commit", "-m", commit_message], repo_dir)
        if code != 0:
            return {"error": f"git commit failed: {err or out}"}
        print("✅ Commit created")

        code, out, err = _run(["git", "push", "-u", "origin", branch], repo_dir)
        if code != 0:
            return {"error": f"git push failed: {err or out}"}
        print("✅ Branch pushed")

        code, out, err = _run(
            [
                "gh",
                "pr",
                "create",
                "--repo",
                f"{config.GITHUB_ORG}/{repo}",
                "--base",
                effective_base,
                "--head",
                branch,
                "--title",
                title,
                "--body",
                body,
            ],
            repo_dir,
        )
        if code != 0:
            return {"error": f"gh pr create failed: {err or out}"}
        print("✅ PR created")

        pr_url = out.strip()
        return {"success": True, "pr_url": pr_url, "branch": branch}

    except Exception as e:
        return {"error": f"Failed to create PR: {str(e)}"}

    finally:
        try:
            if repo_dir.exists():
                _run(["git", "reset", "--hard", f"origin/{effective_base}"], repo_dir)
                _run(["git", "clean", "-fd"], repo_dir)
                print(f"🧹 Fix workspace cleaned: {repo_dir}")
        except Exception as cleanup_error:
            print(f"⚠️  Failed to clean fix workspace: {cleanup_error}")
