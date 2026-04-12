#!/usr/bin/env bash
# daily-brief — Generate and send a morning briefing via Telegram
# Reads memory files, summarizes recent activity, and delivers via telegram-sender.

set -euo pipefail

export PATH="/Users/antharas/.local/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source .env
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

echo "[daily-brief] Starting daily brief at $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Run Claude with daily brief prompt
cd "$PROJECT_DIR"

/opt/homebrew/bin/gtimeout 180 claude -p "Generate a morning briefing. Read memory files to recall context. Check calendar events for today and any coming up in the next 24 hours. Check weather if possible. Summarize: what happened yesterday, what's planned today, any pending items or reminders from memory. Send the brief via telegram-sender skill." \
    --allowedTools "Read,Write,Edit,Bash,Glob,Grep,WebFetch,WebSearch,Skill" || echo "[daily-brief] Timed out or failed (exit $?)"

echo "[daily-brief] Completed at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
