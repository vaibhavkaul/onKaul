"""Sandbox API — per-repo Docker containers with live terminal + preview."""

from __future__ import annotations

import asyncio
import fcntl
import json
import os
import pty
import re
import struct
import subprocess
import termios
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Cookie, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response, StreamingResponse

from api.conversation_store import new_user_id
from config import config as app_config
from repository_config.repositories import REPOSITORIES
from tools.local_code import ensure_repo

router = APIRouter(prefix="/sandbox", tags=["sandbox"])

USER_COOKIE = "onkaul_user_id"
SANDBOX_IMAGE = "onkaul-sandbox:latest"
SANDBOX_DOCKERFILE_DIR = str(Path(__file__).resolve().parents[1] / "sandbox")

# Active sandboxes: (user_id, repo_key) -> {container_name, preview_port}
_active: dict[tuple[str, str], dict] = {}


def _ensure_image() -> None:
    """Build the sandbox Docker image if it doesn't already exist."""
    check = subprocess.run(
        ["docker", "image", "inspect", SANDBOX_IMAGE],
        capture_output=True,
    )
    if check.returncode == 0:
        return  # image already present

    result = subprocess.run(
        ["docker", "build", "-t", SANDBOX_IMAGE, SANDBOX_DOCKERFILE_DIR],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to build sandbox image:\n{result.stderr.strip()}")


def _sandbox_repos() -> list[dict]:
    return [
        {
            "key": key,
            "name": repo["name"],
            "org": repo.get("org", ""),
            "sandbox": repo["sandbox"],
        }
        for key, repo in REPOSITORIES.items()
        if repo.get("hotReloadSupport") and repo.get("sandbox")
    ]


PROJECT_META_FILE = ".onkaul-project.json"
_STATIC_PREVIEW_PORT = 8080


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", name.lower().strip()).strip("-")[:64]


def _user_project_dir(user_id: str, slug: str) -> Path:
    return Path(app_config.WORKSPACE_DIR) / "projects" / user_id / slug


def _load_project_meta(user_id: str, slug: str) -> dict | None:
    meta_file = _user_project_dir(user_id, slug) / PROJECT_META_FILE
    if not meta_file.exists():
        return None
    return json.loads(meta_file.read_text())


def _generate_static_starter(path: Path, name: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "index.html").write_text(
        f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{name}</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <div class="hero">
    <div class="card">
      <div class="icon">⚡</div>
      <h1>{name}</h1>
      <p class="subtitle">Your project is ready.</p>
      <p class="hint">Open the terminal on the right and type <code>claude</code> to start building.</p>
    </div>
  </div>
  <script src="app.js"></script>
</body>
</html>
"""
    )
    (path / "style.css").write_text(
        """*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #0f0f10;
  color: #e8e8e8;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.hero { padding: 2rem; text-align: center; }
.card {
  background: #1a1a1c;
  border: 1px solid #2a2a2e;
  border-radius: 16px;
  padding: 3rem 4rem;
  max-width: 480px;
}
.icon { font-size: 3rem; margin-bottom: 1.5rem; }
h1 { font-size: 2rem; font-weight: 700; margin-bottom: 0.75rem; }
.subtitle { color: #888; margin-bottom: 1.5rem; }
.hint { color: #666; font-size: 0.875rem; line-height: 1.6; }
code {
  background: #2a2a2e;
  color: #7dd3fc;
  padding: 0.1em 0.4em;
  border-radius: 4px;
  font-family: 'SF Mono', 'Fira Code', monospace;
}
"""
    )
    (path / "app.js").write_text("// Your app starts here\nconsole.log('Project ready!');\n")


@router.get("/repos")
async def list_sandbox_repos():
    """List all repos that have hotReloadSupport enabled."""
    return _sandbox_repos()


@router.get("/user-projects")
async def list_user_projects(
    user_id: Optional[str] = Cookie(default=None, alias=USER_COOKIE),
):
    """List all user-created sandbox projects."""
    if not user_id:
        return []
    projects_root = Path(app_config.WORKSPACE_DIR) / "projects" / user_id
    if not projects_root.exists():
        return []
    results = []
    for meta_file in sorted(projects_root.glob(f"*/{PROJECT_META_FILE}")):
        try:
            results.append(json.loads(meta_file.read_text()))
        except Exception:
            pass
    return results


@router.post("/user-projects")
async def create_user_project(
    body: dict[str, Any],
    user_id: Optional[str] = Cookie(default=None, alias=USER_COOKIE),
):
    """Create a new user-owned sandbox project."""
    is_new_user = user_id is None
    if user_id is None:
        user_id = new_user_id()

    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Project name is required")

    project_type = body.get("project_type") or "static"
    repo_url = (body.get("repo_url") or "").strip()
    slug = _slugify(name)
    local_path = _user_project_dir(user_id, slug)

    if local_path.exists():
        raise HTTPException(status_code=409, detail=f"A project named '{slug}' already exists")

    if repo_url:
        r = subprocess.run(
            ["git", "clone", repo_url, str(local_path)],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Clone failed: {r.stderr.strip()}")
    elif project_type == "static":
        _generate_static_starter(local_path, name)
    else:
        local_path.mkdir(parents=True, exist_ok=True)

    meta = {
        "slug": slug,
        "name": name,
        "project_type": project_type,
        "preview_port": _STATIC_PREVIEW_PORT,
        "start_command": body.get("start_command") or "",
        "local_path": str(local_path.resolve()),
        "created_at": datetime.utcnow().isoformat(),
    }
    (local_path / PROJECT_META_FILE).write_text(json.dumps(meta, indent=2))

    response = JSONResponse(content=meta, status_code=201)
    if is_new_user:
        response.set_cookie(USER_COOKIE, user_id, max_age=86400, httponly=False, samesite="lax")
    return response


@router.post("/{repo}/start")
async def start_sandbox(
    repo: str,
    user_id: Optional[str] = Cookie(default=None, alias=USER_COOKIE),
):
    """Start a sandbox container for the given repo."""
    is_new_user = user_id is None
    if user_id is None:
        user_id = new_user_id()

    slot = (user_id, repo)
    if slot in _active:
        # Check the container is still alive; if not, clean up and recreate
        existing = _active[slot]
        alive = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Running}}", existing["container_name"]],
            capture_output=True,
            text=True,
        )
        if alive.returncode == 0 and alive.stdout.strip() == "true":
            return existing
        # Container is dead — remove it and fall through to start a fresh one
        subprocess.run(["docker", "rm", "-f", existing["container_name"]], capture_output=True)
        del _active[slot]

    try:
        _ensure_image()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    repo_cfg = REPOSITORIES.get(repo)
    if repo_cfg and repo_cfg.get("hotReloadSupport"):
        # Configured repo — check it out on the host
        checkout = ensure_repo(repo)
        if "error" in checkout:
            raise HTTPException(
                status_code=500, detail=f"Could not check out repo: {checkout['error']}"
            )
        local_repo_path = str(Path(checkout["path"]).resolve())
        sb = repo_cfg["sandbox"]
    else:
        # User-created project
        meta = _load_project_meta(user_id, repo)
        if meta is None:
            raise HTTPException(status_code=404, detail="Sandbox not available for this key")
        local_repo_path = meta["local_path"]
        sb = {
            "appType": meta["project_type"],
            "previewPort": meta.get("preview_port", _STATIC_PREVIEW_PORT),
            "startCommand": meta.get("start_command", ""),
        }
    preview_port = sb.get("previewPort", 8080)
    container_name = f"onkaul-sb-{user_id[:8]}-{repo}"

    env_args: list[str] = [
        "-e",
        f"APP_TYPE={sb.get('appType', 'static')}",
        "-e",
        f"PREVIEW_PORT={preview_port}",
        "-e",
        f"START_COMMAND={sb.get('startCommand', '')}",
    ]
    if app_config.ANTHROPIC_API_KEY:
        env_args += ["-e", f"ANTHROPIC_API_KEY={app_config.ANTHROPIC_API_KEY}"]

    result = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
            "-p",
            f"0:{preview_port}",
            # Mount the host checkout read-write so Claude Code edits are live,
            # but the container has no git credentials to push/pull
            "-v",
            f"{local_repo_path}:/workspace/repo",
            *env_args,
            SANDBOX_IMAGE,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Container start failed: {result.stderr.strip()}",
        )

    # Discover the mapped host port
    port_out = subprocess.run(
        ["docker", "port", container_name, str(preview_port)],
        capture_output=True,
        text=True,
    )
    assigned = int(port_out.stdout.strip().split(":")[-1])

    info: dict = {
        "container_name": container_name,
        "preview_port": assigned,
        "local_repo_path": local_repo_path,
        "status": "running",
    }
    _active[slot] = info

    # Wait for the preview server inside the container to be ready (up to 15s)
    await _wait_for_preview(assigned)

    response = JSONResponse(content=info)
    if is_new_user:
        response.set_cookie(USER_COOKIE, user_id, max_age=86400, httponly=False, samesite="lax")
    return response


@router.delete("/{repo}/stop")
async def stop_sandbox(
    repo: str,
    user_id: Optional[str] = Cookie(default=None, alias=USER_COOKIE),
):
    """Stop and remove the sandbox container."""
    if not user_id:
        raise HTTPException(status_code=401, detail="No user session")
    slot = (user_id, repo)
    info = _active.pop(slot, None)
    if not info:
        raise HTTPException(status_code=404, detail="No active sandbox")
    subprocess.run(["docker", "rm", "-f", info["container_name"]], capture_output=True)
    return {"status": "stopped"}


@router.get("/{repo}/status")
async def sandbox_status(
    repo: str,
    user_id: Optional[str] = Cookie(default=None, alias=USER_COOKIE),
):
    """Check whether a sandbox is currently running."""
    if not user_id:
        return {"status": "stopped"}
    slot = (user_id, repo)
    info = _active.get(slot)
    if not info:
        return {"status": "stopped"}
    return {"status": "running", **info}


@router.websocket("/{repo}/terminal")
async def terminal_ws(
    websocket: WebSocket,
    repo: str,
    user_id: Optional[str] = Cookie(default=None, alias=USER_COOKIE),
):
    """
    WebSocket terminal relay. Opens a PTY via `docker exec` into the sandbox
    container and relays bytes bidirectionally. Accepts a JSON resize message:

        {"type": "resize", "cols": 120, "rows": 40}
    """
    await websocket.accept()

    if not user_id:
        await websocket.close(code=1008, reason="No user session")
        return

    slot = (user_id, repo)
    info = _active.get(slot)
    if not info:
        await websocket.close(code=1008, reason="No active sandbox")
        return

    container_name = info["container_name"]

    # Open a pseudo-terminal pair
    master_fd, slave_fd = pty.openpty()
    proc = subprocess.Popen(
        ["docker", "exec", "-it", container_name, "bash"],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
    )
    os.close(slave_fd)

    loop = asyncio.get_running_loop()
    output_queue: asyncio.Queue[bytes | None] = asyncio.Queue()

    def _on_readable() -> None:
        try:
            data = os.read(master_fd, 4096)
            loop.call_soon_threadsafe(output_queue.put_nowait, data)
        except OSError:
            loop.call_soon_threadsafe(output_queue.put_nowait, None)

    loop.add_reader(master_fd, _on_readable)

    async def _relay_output() -> None:
        while True:
            chunk = await output_queue.get()
            if chunk is None:
                break
            try:
                await websocket.send_bytes(chunk)
            except Exception:
                break

    async def _relay_input() -> None:
        try:
            while True:
                msg = await websocket.receive()
                if msg.get("type") == "websocket.disconnect":
                    break
                raw: bytes = msg.get("bytes") or (msg.get("text") or "").encode()
                if not raw:
                    continue
                # Check for a resize control message
                try:
                    parsed = json.loads(raw)
                    if parsed.get("type") == "resize":
                        cols = int(parsed.get("cols", 80))
                        rows = int(parsed.get("rows", 24))
                        fcntl.ioctl(
                            master_fd,
                            termios.TIOCSWINSZ,
                            struct.pack("HHHH", rows, cols, 0, 0),
                        )
                        continue
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass
                os.write(master_fd, raw)
        except (WebSocketDisconnect, RuntimeError):
            pass

    try:
        await asyncio.gather(_relay_output(), _relay_input(), return_exceptions=True)
    finally:
        loop.remove_reader(master_fd)
        try:
            os.close(master_fd)
        except OSError:
            pass
        try:
            proc.terminate()
        except Exception:
            pass


def _repo_snapshot(path: str) -> dict[str, float]:
    """Return {filepath: mtime} for all non-.git files under path."""
    snap: dict[str, float] = {}
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d != ".git"]
        for f in files:
            fp = os.path.join(root, f)
            try:
                snap[fp] = os.path.getmtime(fp)
            except OSError:
                pass
    return snap


@router.get("/{repo}/watch")
async def watch_sandbox(
    repo: str,
    user_id: Optional[str] = Cookie(default=None, alias=USER_COOKIE),
):
    """SSE stream — sends 'reload' whenever a file in the repo changes."""
    if not user_id:
        raise HTTPException(status_code=401, detail="No user session")
    slot = (user_id, repo)
    info = _active.get(slot)
    if not info:
        raise HTTPException(status_code=503, detail="Sandbox not running")

    local_path = info["local_repo_path"]

    async def event_stream():
        yield "data: connected\n\n"
        prev = await asyncio.to_thread(_repo_snapshot, local_path)
        while True:
            await asyncio.sleep(1.0)
            # Check slot still active
            if _active.get(slot) is None:
                break
            curr = await asyncio.to_thread(_repo_snapshot, local_path)
            if curr != prev:
                prev = curr
                yield "data: reload\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _wait_for_preview(port: int, timeout: float = 15.0) -> None:
    """Poll until the preview server on the given port accepts connections."""
    deadline = asyncio.get_running_loop().time() + timeout
    async with httpx.AsyncClient() as client:
        while asyncio.get_running_loop().time() < deadline:
            try:
                await client.get(f"http://127.0.0.1:{port}/", timeout=1.0)
                return  # server is up
            except httpx.RequestError:
                await asyncio.sleep(0.5)


@router.api_route(
    "/{repo}/preview/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"]
)
async def preview_proxy(
    request: Request,
    repo: str,
    path: str = "",
    user_id: Optional[str] = Cookie(default=None, alias=USER_COOKIE),
):
    """HTTP proxy to the preview server running inside the sandbox container.
    Handles all methods so browser-sync's socket.io polling works."""
    if not user_id:
        raise HTTPException(status_code=401, detail="No user session")
    slot = (user_id, repo)
    info = _active.get(slot)
    if not info:
        raise HTTPException(status_code=503, detail="Sandbox not running — start it first")

    qs = request.url.query
    url = f"http://127.0.0.1:{info['preview_port']}/{path}"
    if qs:
        url += f"?{qs}"

    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            body = await request.body()
            resp = await client.request(
                method=request.method,
                url=url,
                content=body,
                headers={
                    k: v
                    for k, v in request.headers.items()
                    if k.lower() not in ("host", "cookie", "accept-encoding")
                },
                timeout=10.0,
            )
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                media_type=resp.headers.get("content-type"),
            )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Preview server unreachable: {exc}")


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def _require_sandbox(user_id: Optional[str], repo: str) -> dict:
    if not user_id:
        raise HTTPException(status_code=401, detail="No user session")
    info = _active.get((user_id, repo))
    if not info:
        raise HTTPException(status_code=503, detail="Sandbox not running")
    return info


@router.get("/{repo}/git-info")
async def git_info(
    repo: str,
    user_id: Optional[str] = Cookie(default=None, alias=USER_COOKIE),
):
    info = _require_sandbox(user_id, repo)
    local_path = info["local_repo_path"]
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], local_path).stdout.strip()
    status = _git(["status", "--porcelain"], local_path).stdout.strip()
    changed = [line for line in status.splitlines() if line]
    return {"branch": branch, "has_changes": len(changed) > 0, "changed_count": len(changed)}


@router.post("/{repo}/reset")
async def git_reset(
    repo: str,
    user_id: Optional[str] = Cookie(default=None, alias=USER_COOKIE),
):
    info = _require_sandbox(user_id, repo)
    local_path = info["local_repo_path"]
    _git(["reset", "--hard", "HEAD"], local_path)
    _git(["clean", "-fd"], local_path)
    return {"status": "reset"}


@router.post("/{repo}/push")
async def git_push(
    repo: str,
    body: dict[str, Any],
    user_id: Optional[str] = Cookie(default=None, alias=USER_COOKIE),
):
    info = _require_sandbox(user_id, repo)
    local_path = info["local_repo_path"]

    status = _git(["status", "--porcelain"], local_path).stdout.strip()
    if not status:
        raise HTTPException(status_code=400, detail="No changes to push")

    branch = f"sandbox/{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    commit_msg = body.get("commit_message") or "Changes from sandbox"
    pr_title = body.get("pr_title") or commit_msg

    r = _git(["checkout", "-b", branch], local_path)
    if r.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Could not create branch: {r.stderr.strip()}")

    _git(["add", "-A"], local_path)

    r = _git(["commit", "-m", commit_msg], local_path)
    if r.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Commit failed: {r.stderr.strip()}")

    r = _git(["push", "origin", branch], local_path)
    if r.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Push failed: {r.stderr.strip()}")

    r = subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--title",
            pr_title,
            "--body",
            "Created from onKaul sandbox",
            "--head",
            branch,
        ],
        cwd=local_path,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        raise HTTPException(status_code=500, detail=f"PR creation failed: {r.stderr.strip()}")

    pr_url = r.stdout.strip()
    return {"branch": branch, "pr_url": pr_url}
