#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec uv run python "$SCRIPT_DIR/scripts/setup_repos.py" "$@"
