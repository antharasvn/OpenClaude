#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BOT_SERVICE="claude-telegram-bot"

echo "Restarting bot..."

# Snapshot active streams before the bot's finally blocks can empty them
cp "$PROJECT_DIR/.active-streams.json" "$PROJECT_DIR/.restart-state.json" 2>/dev/null || true

# Notify users with active generations
"$SCRIPT_DIR/notify-interrupted.sh" "$PROJECT_DIR/.restart-state.json" \
    "Restarting — back in a moment..." 2>/dev/null || true

if command -v systemctl &>/dev/null && systemctl --user is-active "$BOT_SERVICE" &>/dev/null 2>&1; then
    # --no-block: return immediately so that if restart.sh was invoked from
    # inside an SDK subprocess (Claude tool use), it doesn't deadlock —
    # systemctl would otherwise block waiting for the bot to stop, while the
    # bot is waiting for the SDK subprocess (which is waiting for restart.sh).
    systemctl --user --no-block restart "$BOT_SERVICE"
    echo "Bot restarted (systemd). Ouroboros still watching."
else
    # Fallback: full stop/start cycle
    "$SCRIPT_DIR/stop.sh"
    sleep 2
    "$SCRIPT_DIR/start.sh"
fi
