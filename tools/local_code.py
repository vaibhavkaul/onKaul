"""Local workspace code operations (clone, pull, search, read)."""

import os
import subprocess
from pathlib import Path

from config import config


def _repo_path(repo: str) -> Path:
    return config.WORKSPACE_DIR / repo


def _repo_url(repo: str) -> str:
    org = config.GITHUB_ORG
    return f"https://github.com/{org}/{repo}.git"


def _gh_available() -> bool:
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def _clone_repo(repo: str, path: Path) -> tuple[int, str, str]:
    org = config.GITHUB_ORG
    if _gh_available():
        return _run_cmd(["gh", "repo", "clone", f"{org}/{repo}", str(path)])
    return _run_cmd(["git", "clone", _repo_url(repo), str(path)])


def _run_cmd(cmd: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def ensure_repo(repo: str) -> dict:
    """Ensure repo exists locally, auto-clone if missing, auto-pull if present."""
    path = _repo_path(repo)
    if not path.exists():
        print(f"📥 Local code: cloning {repo} into {path}...")
        path.mkdir(parents=True, exist_ok=True)
        code, out, err = _clone_repo(repo, path)
        if code != 0:
            return {"error": f"git clone failed: {(err or out).strip()}"}
        print(f"✅ Local code: cloned {repo}")
        return {"cloned": True, "path": str(path)}

    # Auto-pull (fast-forward only)
    print(f"🔄 Local code: pulling latest for {repo}...")
    result = subprocess.run(
        ["git", "-C", str(path), "pull", "--ff-only"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        return {"error": f"git pull failed: {result.stderr.strip()}"}
    print(f"✅ Local code: pulled {repo}")
    return {"pulled": True, "path": str(path)}


def search_code_local(repo: str, query: str) -> dict:
    """Search code using ripgrep in local repo."""
    ensure = ensure_repo(repo)
    if "error" in ensure:
        return ensure

    path = _repo_path(repo)
    # Prefer rg for speed; fallback to git grep if rg isn't available
    try:
        print(f"🔎 Local code: searching {repo} with rg for '{query}'")
        result = subprocess.run(
            ["rg", "-n", "--files-with-matches", query, str(path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode not in (0, 1):
            return {"error": f"rg failed: {result.stderr.strip()}"}
        files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except FileNotFoundError:
        print(f"🔎 Local code: rg not found, falling back to git grep in {repo}")
        result = subprocess.run(
            ["git", "-C", str(path), "grep", "-l", query],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode not in (0, 1):
            return {"error": f"git grep failed: {result.stderr.strip()}"}
        files = [line.strip() for line in result.stdout.splitlines() if line.strip()]

    matches = []
    for file_path in files[:10]:
        rel = str(Path(file_path).resolve().relative_to(path)) if Path(file_path).is_absolute() else file_path
        matches.append(
            {
                "path": rel,
                "local_path": str(path / rel),
            }
        )

    return {"matches": matches, "total_count": len(files)}


def read_file_local(repo: str, path: str) -> dict:
    """Read file contents from local repo."""
    ensure = ensure_repo(repo)
    if "error" in ensure:
        return ensure

    repo_path = _repo_path(repo)
    file_path = repo_path / path
    if not file_path.exists():
        return {"error": f"File not found: {path}"}

    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = file_path.read_text(encoding="utf-8", errors="replace")

    return {
        "path": path,
        "content": content,
        "local_path": str(file_path),
    }


def list_directory_local(repo: str, path: str = "") -> dict:
    """List directory contents from local repo."""
    ensure = ensure_repo(repo)
    if "error" in ensure:
        return ensure

    repo_path = _repo_path(repo)
    dir_path = repo_path / path
    if not dir_path.exists():
        return {"error": f"Directory not found: {path}"}

    items = []
    for item in dir_path.iterdir():
        items.append(
            {
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
                "path": str(Path(path) / item.name) if path else item.name,
            }
        )

    return {"items": items}
