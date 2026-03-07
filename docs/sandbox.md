# Sandbox (Live Preview + Claude Code)

The sandbox feature gives any repository a Docker-backed development environment directly in the onKaul web UI: a live preview iframe on the left and a terminal with Claude Code pre-installed on the right.

## What You Get

- **Live preview** — the running app embedded in the UI, auto-reloads whenever a file changes
- **Terminal** — a full PTY connected to the container; type `claude` to start coding
- **Git controls** — branch display, one-click reset, and push-to-PR from the header bar

## Prerequisites

- Docker Desktop (or Docker Engine) running on the host
- `gh` CLI authenticated (`gh auth login`) — used for private repo checkout and PR creation
- `ANTHROPIC_API_KEY` set in `.env` — forwarded to the container so Claude Code can run

## Enabling a Repo

Add `hotReloadSupport` and a `sandbox` block to any entry in `repo_config.json`:

```json
{
  "repositories": {
    "my-static-site": {
      "name": "my-static-site",
      "org": "acme",
      "hotReloadSupport": true,
      "sandbox": {
        "appType": "static",
        "previewPort": 8080,
        "startCommand": ""
      }
    },
    "my-vite-app": {
      "name": "my-vite-app",
      "org": "acme",
      "hotReloadSupport": true,
      "sandbox": {
        "appType": "dev-server",
        "previewPort": 5173,
        "startCommand": "npm install && npm run dev -- --host 0.0.0.0"
      }
    }
  }
}
```

### Config Fields

| Field | Type | Description |
|---|---|---|
| `hotReloadSupport` | `boolean` | Show repo in the Sandboxes section of the sidebar |
| `sandbox.appType` | `"static"` \| `"dev-server"` | How to serve the app inside the container |
| `sandbox.previewPort` | `number` | Port the app listens on inside the container |
| `sandbox.startCommand` | `string` | Shell command for `dev-server` apps (ignored for `static`) |

## How It Works

### Start

Clicking **Start Sandbox**:

1. Builds `onkaul-sandbox:latest` on first run (auto, ~2 min) and caches it
2. Checks out the repo on the host via `gh` (credentials stay on host — no git inside container)
3. Starts a Docker container with the checkout volume-mounted at `/workspace/repo`
4. For `static`: runs `serve /workspace/repo` on `previewPort`
5. For `dev-server`: runs `startCommand`
6. Waits up to 15 s for the server to be ready before returning

### Hot Reload

The FastAPI host polls the repo directory for `mtime` changes every second. When any file changes, it pushes a Server-Sent Event to the browser, which reloads the preview iframe after a 500 ms debounce (allowing multi-file saves to settle).

### Terminal

A WebSocket opens a PTY via `docker exec` into the running container. Terminal resize events are forwarded automatically.

### Git Controls

All git/gh commands run on the **host** (the container has no credentials):

| Control | Action |
|---|---|
| Branch badge | Shows current branch and count of uncommitted files |
| **Reset** | `git reset --hard HEAD && git clean -fd` — discards all changes (confirmation required) |
| **Push PR** | Creates a `sandbox/YYYYMMDD-HHmmss` branch, commits all changes, pushes, and opens a PR via `gh pr create` |

## Docker Image

The image is defined in `sandbox/Dockerfile`. It is built automatically on first sandbox start.

To force a rebuild after changing the `Dockerfile` or `entrypoint.sh`:

```bash
docker rmi onkaul-sandbox:latest
# Then click Start Sandbox — it will rebuild automatically
```

The image includes:

- Ubuntu 22.04
- Node.js 22 LTS
- `serve` (static file server)
- Claude Code (official native binary installer)

## Security Notes

- Containers have **no git credentials** — they can only read/write the volume-mounted checkout
- `ANTHROPIC_API_KEY` is passed as an environment variable; do not expose sandbox endpoints publicly
- The preview proxy strips `Cookie` and `Accept-Encoding` headers before forwarding to the container
