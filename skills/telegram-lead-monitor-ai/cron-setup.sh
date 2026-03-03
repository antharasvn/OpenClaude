#!/usr/bin/env bash
# cron-setup.sh — Install/uninstall cron job for telegram-lead-monitor-ai
# Usage: ./cron-setup.sh {install|uninstall}

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="${OPENCLAUDE_WORKSPACE_DIR:-/root/OpenClaude/workspaces/c917951142}"
CRON_TAG="# telegram-lead-monitor-ai"
LOGFILE="$WORKSPACE_DIR/logs/lead-monitor-ai-cron.log"

install_cron() {
    # Remove old entry if present
    (crontab -l 2>/dev/null || true) | grep -v "$CRON_TAG" | crontab -

    # Build cron line (every hour at :05)
    local cron_line="5 * * * * OPENCLAUDE_WORKSPACE_DIR=$WORKSPACE_DIR $SCRIPT_DIR/run.sh run-once >> $LOGFILE 2>&1 $CRON_TAG"

    # Add new entry (preserving existing jobs)
    (crontab -l 2>/dev/null || true; echo "$cron_line") | crontab -

    mkdir -p "$(dirname "$LOGFILE")"

    echo "Cron job installed (every hour at :05)"
    echo "Log: $LOGFILE"
    crontab -l | grep "lead-monitor-ai"
}

uninstall_cron() {
    (crontab -l 2>/dev/null || true) | grep -v "$CRON_TAG" | crontab -
    echo "Cron job removed"
}

case "${1:-}" in
    install)   install_cron ;;
    uninstall) uninstall_cron ;;
    *)
        echo "Usage: $0 {install|uninstall}"
        exit 1
        ;;
esac
