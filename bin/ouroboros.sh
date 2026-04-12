#!/usr/bin/env bash
# Ouroboros — watchdog that ensures the telegram bot stays alive.
# If the bot service is stopped or dead, it restarts it after a short delay.
set -euo pipefail

SERVICE_LABEL="com.claude.telegram-bot"
CHECK_INTERVAL="${OUROBOROS_INTERVAL:-30}"

# Resolve project root (parent of bin/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CLEANUP_MARKER="$PROJECT_DIR/.last-log-cleanup"
CLEANUP_INTERVAL=3600  # 1 hour in seconds

is_service_alive() {
    local pid
    pid=$(launchctl list "$SERVICE_LABEL" 2>/dev/null | awk -F'= ' '/"PID"/{gsub(/[;"]/,"",$2); print $2}')
    [[ -n "$pid" && "$pid" != "-" ]] && kill -0 "$pid" 2>/dev/null
}

echo "Ouroboros watching $SERVICE_LABEL (every ${CHECK_INTERVAL}s)"

while true; do
    if ! is_service_alive; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') [ouroboros] $SERVICE_LABEL is dead — reviving..."

        # Notify users who had active generations when the bot crashed
        "$SCRIPT_DIR/notify-interrupted.sh" "$PROJECT_DIR/.active-streams.json" \
            "Something went wrong — restarting..." 2>/dev/null || true

        if "$SCRIPT_DIR/safe-restart.sh"; then
            echo "$(date '+%Y-%m-%d %H:%M:%S') [ouroboros] $SERVICE_LABEL revived successfully"
        else
            echo "$(date '+%Y-%m-%d %H:%M:%S') [ouroboros] safe-restart.sh failed!" >&2
        fi
    fi

    # Hourly log cleanup — gated by marker file mtime
    _do_cleanup=false
    if [[ ! -f "$CLEANUP_MARKER" ]]; then
        _do_cleanup=true
    else
        _marker_age=$(( $(date +%s) - $(stat -f %m "$CLEANUP_MARKER" 2>/dev/null || echo 0) ))
        if (( _marker_age >= CLEANUP_INTERVAL )); then
            _do_cleanup=true
        fi
    fi

    if $_do_cleanup; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') [ouroboros] Running log cleanup..."
        "$SCRIPT_DIR/log-cleanup.sh"
        touch "$CLEANUP_MARKER"
        echo "$(date '+%Y-%m-%d %H:%M:%S') [ouroboros] Log cleanup complete"
    fi

    sleep "$CHECK_INTERVAL"
done
