#!/usr/bin/env bash
# mac-screenshot — macOS screenshot capture skill
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source project .env (infrastructure skill)
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a; source "$PROJECT_DIR/.env"; set +a
fi

COMMAND="${1:-help}"
shift 2>/dev/null || true

# Determine workspace temp dir
# If WORKSPACE_DIR is set (by bot), use it; otherwise use a default
TEMP_DIR="${WORKSPACE_DIR:-$PROJECT_DIR/temp}"
mkdir -p "$TEMP_DIR"

cmd_screen() {
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local outfile="$TEMP_DIR/screenshot_${timestamp}.png"
    echo "Capturing full screen..."
    screencapture -x "$outfile"
    if [[ -f "$outfile" ]]; then
        local size
        size=$(du -sh "$outfile" | cut -f1)
        echo "Screenshot saved: $outfile (${size})"
        echo "FILE:$outfile"
    else
        echo "Error: Screenshot failed."
        exit 1
    fi
}

cmd_window() {
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local outfile="$TEMP_DIR/screenshot_window_${timestamp}.png"
    echo "Capturing frontmost window..."
    # -l 0 captures the frontmost window; -o excludes shadow
    screencapture -x -o -l "$(osascript -e 'tell application "System Events" to get id of window 1 of (first process whose frontmost is true)' 2>/dev/null || echo 0)" "$outfile" 2>/dev/null || \
    screencapture -x -w "$outfile" 2>/dev/null || \
    screencapture -x "$outfile"
    if [[ -f "$outfile" ]]; then
        local size
        size=$(du -sh "$outfile" | cut -f1)
        echo "Window screenshot saved: $outfile (${size})"
        echo "FILE:$outfile"
    else
        echo "Error: Window screenshot failed."
        exit 1
    fi
}

cmd_help() {
    echo "mac-screenshot — macOS screenshot capture"
    echo ""
    echo "Commands:"
    echo "  screen   Capture the full screen"
    echo "  window   Capture the frontmost window"
    echo "  help     Show this help"
    echo ""
    echo "Screenshots are saved to: $TEMP_DIR"
    echo "Filename format: screenshot_YYYYMMDD_HHMMSS.png"
}

case "$COMMAND" in
    screen) cmd_screen ;;
    window) cmd_window ;;
    help|*) cmd_help ;;
esac
