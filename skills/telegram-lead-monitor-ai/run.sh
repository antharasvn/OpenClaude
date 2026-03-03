#!/usr/bin/env bash
# telegram-lead-monitor-ai — Collect messages, notify coordinator for AI analysis
# Usage: ./skills/telegram-lead-monitor-ai/run.sh {install-cron|uninstall-cron|run-once}
# Infrastructure skill — sources project .env for bot token, workspace .env for monitor config

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source project .env (infrastructure skill — needs TELEGRAM_BOT_TOKEN)
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

# Determine workspace directory
WORKSPACE_DIR="${OPENCLAUDE_WORKSPACE_DIR:-/root/OpenClaude/workspaces/c917951142}"

# Source workspace .env (monitor-specific config)
if [[ -f "$WORKSPACE_DIR/.env" ]]; then
    set -a
    source "$WORKSPACE_DIR/.env"
    set +a
fi

LOGDIR="$WORKSPACE_DIR/logs"
LOGFILE="$LOGDIR/lead-monitor-ai.log"
CRON_TAG="# telegram-lead-monitor-ai"
ADMIN_CHAT="${TELEGRAM_ADMIN_CHAT_ID:-917951142}"
SENDER="$PROJECT_DIR/skills/telegram-sender/send.sh"

mkdir -p "$LOGDIR"

usage() {
    echo "Usage: $0 {install-cron|uninstall-cron|run-once|start-daemon|stop-daemon|status-daemon}"
    echo "  install-cron   — Add cron job (every hour)"
    echo "  uninstall-cron — Remove cron job"
    echo "  run-once       — Single execution (for testing)"
    echo "  start-daemon   — Start hourly daemon in background"
    echo "  stop-daemon    — Stop daemon"
    echo "  status-daemon  — Check if daemon is running"
    exit 1
}

check_deps() {
    if ! python3 -c "import telethon" 2>/dev/null; then
        echo "Installing Python dependencies..."
        pip3 install -q -r "$SCRIPT_DIR/requirements.txt"
    fi
}

cmd_install_cron() {
    # Remove old entry if present, then add new one
    local cron_line="*/10 * * * * OPENCLAUDE_WORKSPACE_DIR=$WORKSPACE_DIR TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-} $SCRIPT_DIR/run.sh run-once >> $LOGFILE 2>&1 $CRON_TAG"

    # Remove existing entry
    (crontab -l 2>/dev/null || true) | grep -v "$CRON_TAG" | crontab -

    # Add new entry
    (crontab -l 2>/dev/null || true; echo "$cron_line") | crontab -

    echo "Cron job installed (every hour)"
    echo "Log: $LOGFILE"
    crontab -l | grep "lead-monitor-ai"
}

cmd_uninstall_cron() {
    (crontab -l 2>/dev/null || true) | grep -v "$CRON_TAG" | crontab -
    echo "Cron job removed"
}

cmd_run_once() {
    check_deps

    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] === Collector run starting ==="

    # Step 1: Run the collector
    COLLECTOR_OUTPUT=$(env \
        TG_MONITOR_API_ID="${TG_MONITOR_API_ID:-}" \
        TG_MONITOR_API_HASH="${TG_MONITOR_API_HASH:-}" \
        TG_MONITOR_PHONE="${TG_MONITOR_PHONE:-}" \
        python3 "$SCRIPT_DIR/collect.py" \
        --workspace "$WORKSPACE_DIR" 2>&1) || {
        echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] Collector failed"
        echo "$COLLECTOR_OUTPUT"
        exit 1
    }

    echo "$COLLECTOR_OUTPUT"

    # Step 2: Extract output file path
    OUTPUT_FILE=$(echo "$COLLECTOR_OUTPUT" | grep "^OUTPUT_FILE=" | tail -1 | cut -d= -f2-)

    if [[ -z "$OUTPUT_FILE" || ! -f "$OUTPUT_FILE" ]]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] No messages to analyze — done"
        exit 0
    fi

    # Count messages
    MSG_COUNT=$(python3 -c "import json; print(len(json.load(open('$OUTPUT_FILE'))))" 2>/dev/null || echo "?")

    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Collected $MSG_COUNT messages, notifying coordinator..."

    # Step 3: Send notification to admin chat to trigger coordinator analysis
    NOTIFICATION_TEXT="🤖 Lead analysis requested

File: $OUTPUT_FILE
Messages: $MSG_COUNT

Please analyze these messages for development leads and send notifications for any valid leads found."

    if [[ -x "$SENDER" ]]; then
        "$SENDER" --text "$NOTIFICATION_TEXT" --chat "$ADMIN_CHAT" || {
            echo "$(date '+%Y-%m-%d %H:%M:%S') [WARN] Failed to send notification via telegram-sender"
        }
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') [WARN] telegram-sender not found at $SENDER"
        echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Pending messages saved to: $OUTPUT_FILE"
    fi

    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] === Collector run complete ==="
}

cmd_start_daemon() {
    local pidfile="$WORKSPACE_DIR/lead-monitor-ai-daemon.pid"

    if [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
        echo "Daemon already running (PID $(cat "$pidfile"))"
        exit 0
    fi

    echo "Starting daemon (hourly collection)..."
    nohup "$SCRIPT_DIR/daemon.sh" >> "$WORKSPACE_DIR/logs/lead-monitor-ai-daemon.log" 2>&1 &
    echo "Daemon started (check logs at $WORKSPACE_DIR/logs/lead-monitor-ai-daemon.log)"
}

cmd_stop_daemon() {
    local pidfile="$WORKSPACE_DIR/lead-monitor-ai-daemon.pid"

    if [[ ! -f "$pidfile" ]]; then
        echo "Daemon not running (no PID file)"
        exit 0
    fi

    local pid=$(cat "$pidfile")
    if kill -0 "$pid" 2>/dev/null; then
        echo "Stopping daemon (PID $pid)..."
        kill -TERM "$pid"
        sleep 2
        if kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid"
        fi
        rm -f "$pidfile"
        echo "Daemon stopped"
    else
        echo "Daemon not running (stale PID)"
        rm -f "$pidfile"
    fi
}

cmd_status_daemon() {
    local pidfile="$WORKSPACE_DIR/lead-monitor-ai-daemon.pid"

    if [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
        echo "Daemon is running (PID $(cat "$pidfile"))"
        tail -10 "$WORKSPACE_DIR/logs/lead-monitor-ai-daemon.log"
    else
        echo "Daemon is not running"
        rm -f "$pidfile"
    fi
}

case "${1:-}" in
    install-cron)   cmd_install_cron ;;
    uninstall-cron) cmd_uninstall_cron ;;
    run-once)       cmd_run_once ;;
    start-daemon)   cmd_start_daemon ;;
    stop-daemon)    cmd_stop_daemon ;;
    status-daemon)  cmd_status_daemon ;;
    *)              usage ;;
esac
