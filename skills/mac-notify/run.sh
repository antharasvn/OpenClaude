#!/usr/bin/env bash
# mac-notify — macOS notification skill
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source project .env (infrastructure skill)
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a; source "$PROJECT_DIR/.env"; set +a
fi

COMMAND="${1:-help}"
shift 2>/dev/null || true

cmd_send() {
    local title="${1:-}"
    local message="${2:-}"

    if [[ -z "$title" || -z "$message" ]]; then
        echo "Error: Both title and message are required."
        echo "Usage: mac-notify send <title> <message>"
        exit 1
    fi

    # Sanitize for AppleScript: escape backslashes and double quotes
    local safe_title safe_message
    safe_title="${title//\\/\\\\}"
    safe_title="${safe_title//\"/\\\"}"
    safe_message="${message//\\/\\\\}"
    safe_message="${safe_message//\"/\\\"}"

    echo "Sending notification: \"$title\""
    osascript -e "display notification \"$safe_message\" with title \"$safe_title\""
    echo "Notification sent."
}

cmd_help() {
    echo "mac-notify — macOS notification sender"
    echo ""
    echo "Commands:"
    echo "  send <title> <message>   Show a macOS notification"
    echo "  help                     Show this help"
    echo ""
    echo "Examples:"
    echo "  mac-notify send \"Build Done\" \"Your project compiled successfully.\""
    echo "  mac-notify send \"Reminder\" \"Time for a break!\""
}

case "$COMMAND" in
    send)   cmd_send "$@" ;;
    help|*) cmd_help ;;
esac
