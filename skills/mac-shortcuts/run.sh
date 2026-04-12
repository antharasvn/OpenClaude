#!/usr/bin/env bash
# mac-shortcuts — Apple Shortcuts CLI skill
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source project .env (infrastructure skill)
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a; source "$PROJECT_DIR/.env"; set +a
fi

COMMAND="${1:-help}"
shift 2>/dev/null || true

# Verify shortcuts CLI is available
if ! command -v shortcuts &>/dev/null; then
    echo "Error: 'shortcuts' CLI not found. Requires macOS 12 Monterey or later."
    exit 1
fi

cmd_list() {
    echo "=== Available Shortcuts ==="
    shortcuts list 2>/dev/null || {
        echo "No shortcuts found or Shortcuts.app not accessible."
        exit 1
    }
}

cmd_run() {
    local name="${1:-}"
    if [[ -z "$name" ]]; then
        echo "Error: Shortcut name required. Usage: mac-shortcuts run <name>"
        exit 1
    fi
    echo "Running shortcut: \"$name\""
    # Run with a 60-second timeout to avoid hanging
    if timeout 60 shortcuts run "$name" 2>&1; then
        echo "Shortcut completed: \"$name\""
    else
        local exit_code=$?
        if [[ $exit_code -eq 124 ]]; then
            echo "Error: Shortcut timed out after 60 seconds."
        else
            echo "Error: Shortcut failed or not found (exit $exit_code). Check the shortcut name."
        fi
        exit 1
    fi
}

cmd_help() {
    echo "mac-shortcuts — Apple Shortcuts control"
    echo ""
    echo "Commands:"
    echo "  list         List all available shortcuts"
    echo "  run <name>   Run a shortcut by name"
    echo "  help         Show this help"
    echo ""
    echo "Examples:"
    echo "  mac-shortcuts list"
    echo "  mac-shortcuts run \"Morning Routine\""
    echo "  mac-shortcuts run \"Toggle Dark Mode\""
    echo ""
    echo "Note: Shortcut names are case-sensitive."
}

case "$COMMAND" in
    list)   cmd_list ;;
    run)    cmd_run "$@" ;;
    help|*) cmd_help ;;
esac
