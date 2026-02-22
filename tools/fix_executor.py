"""Create PRs by applying patches in ephemeral workspaces."""

import os
import re
import shlex
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


def _run_codex(cmd_str: str, prompt: str, cwd: Path, timeout: int) -> tuple[int, str, str]:
    cmd = shlex.split(cmd_str)
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _extract_pr_url(output: str) -> str | None:
    # Prefer explicit marker
    marker = re.search(r"PR_URL:\s*(\S+)", output)
    if marker:
        return marker.group(1)
    # Fallback: first GitHub PR URL
    match = re.search(r"https://github\.com/\S+/pull/\d+", output)
    return match.group(0) if match else None


def _truncate(text: str, limit: int = 2000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n...[truncated]"


def _prepare_repo(repo: str, base_branch: str) -> tuple[Path, str] | tuple[None, str]:
    work_root = config.FIX_WORKSPACE_DIR.resolve()
    work_root.mkdir(parents=True, exist_ok=True)

    repo_dir = (work_root / repo).resolve()
    effective_base = base_branch

    if not repo_dir.exists():
        print(f"🛠️  Fix workspace: cloning {repo} into {repo_dir}")
        code, out, err = _run(["git", "clone", _repo_url(repo), str(repo_dir)], work_root, timeout=300)
        if code != 0:
            try:
                if repo_dir.exists():
                    shutil.rmtree(repo_dir)
            except Exception:
                pass
            return None, f"git clone failed: {err or out}"
        print("✅ Clone complete")
    else:
        print(f"🛠️  Fix workspace: reusing {repo_dir}")
        code, out, err = _run(["git", "fetch", "--prune", "origin"], repo_dir)
        if code != 0:
            return None, f"git fetch failed: {err or out}"
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
        return None, f"git reset failed: {err or out}"
    code, out, err = _run(["git", "clean", "-fd"], repo_dir)
    if code != 0:
        return None, f"git clean failed: {err or out}"
    print(f"✅ Workspace reset to origin/{effective_base}")

    return repo_dir, effective_base


def _build_plan_prompt(repo: str, context: str) -> str:
    return (
        "You are Codex running headlessly. Create a fix plan for the issue below.\n"
        "Constraints:\n"
        "- Do NOT modify any files.\n"
        "- Output ONLY the plan in Markdown.\n"
        "- Keep it actionable and ordered.\n\n"
        f"Repository: {repo}\n\n"
        "Issue context:\n"
        f"{context.strip()}\n"
    )


def _build_apply_prompt(
    repo: str,
    base_branch: str,
    title: str,
    body: str,
    plan_md: str,
) -> str:
    return (
        "You are Codex running headlessly. Apply the following plan.\n"
        "Requirements:\n"
        "- Implement the changes in the repo working tree.\n"
        "- Run any minimal tests you think are necessary.\n"
        "- Do NOT create branches, commits, or PRs.\n"
        "- After changes, print a short summary and list any tests run.\n\n"
        f"Repository: {repo}\n"
        f"Base branch: {base_branch}\n"
        f"PR title: {title}\n"
        f"PR body:\n{body}\n\n"
        "Plan (Markdown):\n"
        f"{plan_md.strip()}\n"
    )


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
    context: str,
    base_branch: str = "main",
) -> dict:
    """
    Create a PR using headless Codex to generate a plan and apply it.
    """
    work_id = uuid.uuid4().hex[:8]
    plan_dir = (config.FIX_WORKSPACE_DIR / "plans" / repo).resolve()
    plan_dir.mkdir(parents=True, exist_ok=True)
    plan_path = plan_dir / f"plan-{work_id}.md"

    repo_dir: Path | None = None
    effective_base = base_branch
    branch = f"onkaul/fix-{work_id}"

    try:
        prepared, result = _prepare_repo(repo, base_branch)
        if prepared is None:
            return {"error": result}
        repo_dir = prepared
        effective_base = result  # type: ignore[assignment]

        plan_prompt = _build_plan_prompt(repo, context)
        code, out, err = _run_codex(
            config.CODEX_PLAN_CMD,
            plan_prompt,
            repo_dir,
            timeout=config.CODEX_TIMEOUT_SECONDS,
        )
        if code != 0:
            return {"error": f"Codex plan failed: {err or out}"}
        if not out:
            return {"error": "Codex plan produced no output"}
        plan_path.write_text(out + "\n", encoding="utf-8")

        prepared, result = _prepare_repo(repo, effective_base)
        if prepared is None:
            return {"error": result}
        repo_dir = prepared
        effective_base = result  # type: ignore[assignment]

        code, out, err = _run(["git", "checkout", "-B", branch, f"origin/{effective_base}"] , repo_dir)
        if code != 0:
            return {"error": f"git checkout failed: {err or out}", "plan_path": str(plan_path)}

        apply_prompt = _build_apply_prompt(repo, effective_base, title, body, out)
        code, apply_out, err = _run_codex(
            config.CODEX_APPLY_CMD,
            apply_prompt,
            repo_dir,
            timeout=config.CODEX_TIMEOUT_SECONDS,
        )
        if code != 0:
            return {"error": f"Codex apply failed: {err or apply_out}", "plan_path": str(plan_path)}

        code, status_out, err = _run(["git", "status", "--porcelain"], repo_dir)
        if code != 0:
            return {"error": f"git status failed: {err or status_out}", "plan_path": str(plan_path)}
        if not status_out:
            return {"error": "Codex produced no changes", "plan_path": str(plan_path)}

        code, diffstat, _ = _run(["git", "diff", "--stat"], repo_dir)
        diffstat = diffstat if code == 0 else ""

        code, out, err = _run(["git", "add", "-A"], repo_dir)
        if code != 0:
            return {"error": f"git add failed: {err or out}", "plan_path": str(plan_path)}

        commit_message = title.strip() or f"onKaul fix {work_id}"
        code, out, err = _run(["git", "commit", "-m", commit_message], repo_dir)
        if code != 0:
            return {"error": f"git commit failed: {err or out}", "plan_path": str(plan_path)}

        code, out, err = _run(["git", "push", "-u", "origin", branch], repo_dir)
        if code != 0:
            return {"error": f"git push failed: {err or out}", "plan_path": str(plan_path)}

        body_with_meta = body.strip()
        body_with_meta += "\n\n---\n"
        body_with_meta += f"Codex plan path: {plan_path}\n"
        if diffstat:
            body_with_meta += "\nDiff stat:\n" + diffstat + "\n"
        if apply_out:
            body_with_meta += "\nCodex apply output (truncated):\n```\n" + _truncate(apply_out) + "\n```\n"

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
                body_with_meta,
            ],
            repo_dir,
        )
        if code != 0:
            return {"error": f"gh pr create failed: {err or out}", "plan_path": str(plan_path)}

        pr_url = out.strip()
        return {
            "success": True,
            "pr_url": pr_url,
            "plan_path": str(plan_path),
        }

    except Exception as e:
        return {"error": f"Failed to create PR: {str(e)}"}

    finally:
        try:
            if repo_dir and repo_dir.exists():
                _run(["git", "reset", "--hard", f"origin/{effective_base}"], repo_dir)
                _run(["git", "clean", "-fd"], repo_dir)
                print(f"🧹 Fix workspace cleaned: {repo_dir}")
        except Exception as cleanup_error:
            print(f"⚠️  Failed to clean fix workspace: {cleanup_error}")
