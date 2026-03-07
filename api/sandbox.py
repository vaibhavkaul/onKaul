"""Sandbox API — per-repo Docker containers with live terminal + preview."""

from __future__ import annotations

import asyncio
import fcntl
import json
import os
import pty
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


@router.get("/repos")
async def list_sandbox_repos():
    """List all repos that have hotReloadSupport enabled."""
    return _sandbox_repos()


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
        return _active[slot]

    repo_cfg = REPOSITORIES.get(repo)
    if not repo_cfg or not repo_cfg.get("hotReloadSupport"):
        raise HTTPException(status_code=404, detail="Sandbox not available for this repo")

    try:
        _ensure_image()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Clone/pull the repo on the host (FastAPI has git/gh auth; container does not)
    checkout = ensure_repo(repo)
    if "error" in checkout:
        raise HTTPException(status_code=500, detail=f"Could not check out repo: {checkout['error']}")
    local_repo_path = str(Path(checkout["path"]).resolve())

    sb = repo_cfg["sandbox"]
    preview_port = sb.get("previewPort", 8080)
    container_name = f"onkaul-sb-{user_id[:8]}-{repo}"

    env_args: list[str] = [
        "-e", f"APP_TYPE={sb.get('appType', 'static')}",
        "-e", f"PREVIEW_PORT={preview_port}",
        "-e", f"START_COMMAND={sb.get('startCommand', '')}",
    ]
    if app_config.ANTHROPIC_API_KEY:
        env_args += ["-e", f"ANTHROPIC_API_KEY={app_config.ANTHROPIC_API_KEY}"]

    result = subprocess.run(
        [
            "docker", "run", "-d",
            "--name", container_name,
            "-p", f"0:{preview_port}",
            # Mount the host checkout read-write so Claude Code edits are live,
            # but the container has no git credentials to push/pull
            "-v", f"{local_repo_path}:/workspace/repo",
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


@router.api_route("/{repo}/preview/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
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
                headers={k: v for k, v in request.headers.items() if k.lower() not in ("host", "cookie", "accept-encoding")},
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
    changed = [l for l in status.splitlines() if l]
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
        ["gh", "pr", "create", "--title", pr_title, "--body", "Created from onKaul sandbox", "--head", branch],
        cwd=local_path, capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise HTTPException(status_code=500, detail=f"PR creation failed: {r.stderr.strip()}")

    pr_url = r.stdout.strip()
    return {"branch": branch, "pr_url": pr_url}
