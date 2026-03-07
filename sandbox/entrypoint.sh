#!/bin/bash
set +e

# Pre-configure Claude Code to use ANTHROPIC_API_KEY without the auth prompt.
# customApiKeyResponses.approved tells Claude Code the user has already approved
# using the key in env — skipping the "choose login method" setup screen.
mkdir -p /home/sandbox-user/.claude
cat > /home/sandbox-user/.claude.json << EOF
{
  "hasCompletedOnboarding": true,
  "customApiKeyResponses": {
    "approved": ["sandbox-session"],
    "rejected": []
  }
}
EOF

cd /workspace/repo

echo "==> Starting preview server (type=${APP_TYPE}) on port ${PREVIEW_PORT:-8080} ..."
if [ "$APP_TYPE" = "static" ]; then
    serve /workspace/repo -l "tcp://0.0.0.0:${PREVIEW_PORT:-8080}" &
elif [ "$APP_TYPE" = "dev-server" ] && [ -n "$START_COMMAND" ]; then
    eval "$START_COMMAND" &
elif [ "$APP_TYPE" = "fullstack-python-vite" ]; then
    echo "==> Starting backend (FastAPI) ..."
    eval "$BACKEND_START_COMMAND" &
    echo "==> Starting frontend (Vite) on port ${PREVIEW_PORT} ..."
    eval "$FRONTEND_START_COMMAND" &
fi

# Auto-launch Claude in fully unrestricted mode for interactive bash sessions only.
# [[ $- == *i* ]] checks that the shell is interactive, preventing this from
# running in non-interactive exec calls (e.g. docker exec container bash -c '...').
echo '[[ $- == *i* ]] && claude --dangerously-skip-permissions' >> /home/sandbox-user/.bashrc

echo "==> Sandbox ready."
tail -f /dev/null
