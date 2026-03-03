#!/usr/bin/env bash
# daemon.sh — Runs the collector every hour in an infinite loop
# Usage: nohup ./daemon.sh &

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="${OPENCLAUDE_WORKSPACE_DIR:-/root/OpenClaude/workspaces/c917951142}"
PIDFILE="$WORKSPACE_DIR/lead-monitor-ai-daemon.pid"
LOGFILE="$WORKSPACE_DIR/logs/lead-monitor-ai-daemon.log"

# Write PID
echo $$ > "$PIDFILE"

echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Daemon started (PID $$)" | tee -a "$LOGFILE"

# Infinite loop: run every hour
while true; do
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Running collection cycle..." | tee -a "$LOGFILE"

    OPENCLAUDE_WORKSPACE_DIR="$WORKSPACE_DIR" "$SCRIPT_DIR/run.sh" run-once 2>&1 | tee -a "$LOGFILE"

    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Collection complete. Sleeping for 1 hour..." | tee -a "$LOGFILE"

    sleep 3600  # 1 hour
done
