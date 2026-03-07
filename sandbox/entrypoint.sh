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
fi

# Auto-launch Claude in fully unrestricted mode when a bash session opens.
# This works because the container runs as the non-root sandbox-user.
# The user can Ctrl+C back to the shell at any time.
echo 'claude --dangerously-skip-permissions' >> /home/sandbox-user/.bashrc

echo "==> Sandbox ready."
tail -f /dev/null
