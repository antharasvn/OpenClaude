#!/usr/bin/env bash
# daily-brief — launchd entry point (com.claude.daily-brief, 09:00 daily).
#
# Why this exists: the plist used to run ~/.local/bin/claude directly. Since
# 2026-08-26 that path is a zsh shim that `exec`s the Anthropic-signed
# claude-native inside the launchd-managed pid; launchd's lightweight code
# requirement then kills it (SIGKILL, OS_REASON_CODESIGNING) before it runs —
# 2026-08-27 09:00 brief never happened. Spawning claude as a child of this
# script (same shape as skills/heartbeat/run.sh) sidesteps that check.

set -euo pipefail

export PATH="/Users/antharas/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_DIR"

echo "[daily-brief] Starting at $(date -u +%Y-%m-%dT%H:%M:%SZ)"

claude -p "Generate and send a daily brief using the daily-brief skill" \
    --allowedTools Read,Write,Bash,Glob,Grep,Skill
rc=$?

echo "[daily-brief] Completed at $(date -u +%Y-%m-%dT%H:%M:%SZ) rc=$rc"
exit $rc
