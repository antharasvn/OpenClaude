#!/usr/bin/env bash
# telegram-lead-monitor — Start/stop/status for the Telegram lead monitoring daemon
# Usage: ./skills/telegram-lead-monitor/run.sh {start|stop|status}
# Infrastructure skill — sources project .env for bot tokens

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source project .env (infrastructure skill — needs bot token for telegram-sender)
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

# Source workspace .env if PWD differs from project dir
if [[ -f "$PWD/.env" && "$PWD" != "$PROJECT_DIR" ]]; then
    set -a
    source "$PWD/.env"
    set +a
fi

# Determine workspace directory for session/logs/db storage
# Default to project dir if no workspace context
WORKSPACE_DIR="${OPENCLAUDE_WORKSPACE_DIR:-$PROJECT_DIR}"
PIDFILE="$WORKSPACE_DIR/lead-monitor.pid"
LOGDIR="$WORKSPACE_DIR/logs"
LOGFILE="$LOGDIR/lead-monitor.log"

mkdir -p "$LOGDIR"

usage() {
    echo "Usage: $0 {start|stop|status|auth}"
    echo "  start  — Start the lead monitor daemon"
    echo "  stop   — Stop the daemon"
    echo "  status — Check if daemon is running"
    echo "  auth   — Run interactive auth (for first-time setup / 2FA)"
    exit 1
}

check_deps() {
    if ! python3 -c "import telethon" 2>/dev/null; then
        echo "Installing Python dependencies..."
        pip3 install -q -r "$SCRIPT_DIR/requirements.txt"
    fi
}

cmd_start() {
    check_deps

    # Check if already running
    if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "Lead monitor is already running (PID $(cat "$PIDFILE"))"
        exit 0
    fi

    # Validate required env vars
    for var in TG_MONITOR_API_ID TG_MONITOR_API_HASH TG_MONITOR_PHONE TG_MONITOR_ADMIN_CHAT_ID; do
        if [[ -z "${!var:-}" ]]; then
            echo "ERROR: Required env var $var is not set"
            exit 1
        fi
    done

    echo "Starting lead monitor..."
    nohup env \
        TG_MONITOR_API_ID="$TG_MONITOR_API_ID" \
        TG_MONITOR_API_HASH="$TG_MONITOR_API_HASH" \
        TG_MONITOR_PHONE="$TG_MONITOR_PHONE" \
        TG_MONITOR_ADMIN_CHAT_ID="$TG_MONITOR_ADMIN_CHAT_ID" \
        TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}" \
        python3 -u "$SCRIPT_DIR/monitor.py" \
        --workspace "$WORKSPACE_DIR" \
        >> "$LOGFILE" 2>&1 &

    echo $! > "$PIDFILE"
    echo "Lead monitor started (PID $!), logging to $LOGFILE"
}

cmd_stop() {
    if [[ ! -f "$PIDFILE" ]]; then
        echo "Lead monitor is not running (no PID file)"
        exit 0
    fi

    local pid
    pid=$(cat "$PIDFILE")

    if kill -0 "$pid" 2>/dev/null; then
        echo "Stopping lead monitor (PID $pid)..."
        kill -TERM "$pid"
        # Wait up to 10 seconds for graceful shutdown
        for i in $(seq 1 10); do
            if ! kill -0 "$pid" 2>/dev/null; then
                break
            fi
            sleep 1
        done
        # Force kill if still alive
        if kill -0 "$pid" 2>/dev/null; then
            echo "Force killing..."
            kill -9 "$pid" 2>/dev/null || true
        fi
        echo "Lead monitor stopped."
    else
        echo "Lead monitor was not running (stale PID file)."
    fi

    rm -f "$PIDFILE"
}

cmd_status() {
    if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "Lead monitor is running (PID $(cat "$PIDFILE"))"
        echo "Log: $LOGFILE"
        # Show last 5 log lines
        if [[ -f "$LOGFILE" ]]; then
            echo "--- Last 5 log lines ---"
            tail -5 "$LOGFILE"
        fi
    else
        echo "Lead monitor is not running"
        rm -f "$PIDFILE"
    fi
}

cmd_auth() {
    check_deps
    echo "Running interactive authentication..."
    python3 "$SCRIPT_DIR/monitor.py" --auth-only --workspace "$WORKSPACE_DIR"
}

case "${1:-}" in
    start)  cmd_start ;;
    stop)   cmd_stop ;;
    status) cmd_status ;;
    auth)   cmd_auth ;;
    *)      usage ;;
esac
