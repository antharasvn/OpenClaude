#!/usr/bin/env bash
# mac-clipboard — macOS clipboard read/write skill
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source project .env (infrastructure skill)
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a; source "$PROJECT_DIR/.env"; set +a
fi

COMMAND="${1:-help}"
shift 2>/dev/null || true

cmd_get() {
    local content
    content=$(pbpaste 2>/dev/null)
    if [[ -z "$content" ]]; then
        echo "(Clipboard is empty)"
    else
        local char_count=${#content}
        echo "=== Clipboard Contents (${char_count} chars) ==="
        echo "$content"
    fi
}

cmd_set() {
    local text="$*"
    if [[ -z "$text" ]]; then
        echo "Error: No text provided. Usage: mac-clipboard set <text>"
        exit 1
    fi
    printf '%s' "$text" | pbcopy
    local char_count=${#text}
    echo "Clipboard set (${char_count} chars)."
}

cmd_help() {
    echo "mac-clipboard — macOS clipboard control"
    echo ""
    echo "Commands:"
    echo "  get          Get current clipboard contents"
    echo "  set <text>   Set clipboard to given text"
    echo "  help         Show this help"
    echo ""
    echo "Examples:"
    echo "  mac-clipboard get"
    echo "  mac-clipboard set \"Hello, world!\""
}

case "$COMMAND" in
    get)    cmd_get ;;
    set)    cmd_set "$@" ;;
    help|*) cmd_help ;;
esac
