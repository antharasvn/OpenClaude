#!/usr/bin/env bash
# mac-apps — macOS application control skill
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source project .env (infrastructure skill)
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a; source "$PROJECT_DIR/.env"; set +a
fi

COMMAND="${1:-help}"
shift 2>/dev/null || true

cmd_open() {
    local app="${1:-}"
    if [[ -z "$app" ]]; then
        echo "Error: app name required. Usage: mac-apps open <AppName>"
        exit 1
    fi
    echo "Opening: $app"
    open -a "$app" 2>/dev/null || {
        echo "Error: Could not open '$app'. Check the app name."
        exit 1
    }
    echo "Opened $app successfully."
}

cmd_quit() {
    local app="${1:-}"
    if [[ -z "$app" ]]; then
        echo "Error: app name required. Usage: mac-apps quit <AppName>"
        exit 1
    fi
    echo "Quitting: $app"
    osascript -e "tell application \"$app\" to quit" 2>/dev/null || {
        echo "Error: Could not quit '$app'. App may not be running or name may be wrong."
        exit 1
    }
    echo "Quit $app successfully."
}

cmd_list() {
    echo "=== Running Applications ==="
    osascript <<'EOF'
set appList to {}
tell application "System Events"
    repeat with proc in (every process whose background only is false)
        set end of appList to name of proc
    end repeat
end tell
set output to ""
repeat with appName in appList
    set output to output & appName & linefeed
end repeat
return output
EOF
}

cmd_frontmost() {
    echo "=== Frontmost Application ==="
    osascript -e 'tell application "System Events" to get name of first process whose frontmost is true' 2>/dev/null || echo "Could not determine frontmost app."
}

cmd_help() {
    echo "mac-apps — macOS application control"
    echo ""
    echo "Commands:"
    echo "  open <app>   Open an application by name"
    echo "  quit <app>   Quit an application by name"
    echo "  list         List all running (visible) applications"
    echo "  frontmost    Show the frontmost application"
    echo "  help         Show this help"
    echo ""
    echo "Examples:"
    echo "  mac-apps open Safari"
    echo "  mac-apps open \"Google Chrome\""
    echo "  mac-apps quit Finder"
}

case "$COMMAND" in
    open)       cmd_open "$@" ;;
    quit)       cmd_quit "$@" ;;
    list)       cmd_list ;;
    frontmost)  cmd_frontmost ;;
    help|*)     cmd_help ;;
esac
