#!/bin/bash
set +e

# Pre-configure Claude Code to use ANTHROPIC_API_KEY without the auth prompt.
# customApiKeyResponses.approved tells Claude Code the user has already approved
# using the key in env — skipping the "choose login method" setup screen.
mkdir -p /root/.claude
cat > /root/.claude.json << EOF
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

echo "==> Sandbox ready. Type 'claude' to start coding."
tail -f /dev/null
