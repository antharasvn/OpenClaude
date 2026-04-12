#!/usr/bin/env bash
# mac-finder — macOS Finder operations skill
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source project .env (infrastructure skill)
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a; source "$PROJECT_DIR/.env"; set +a
fi

COMMAND="${1:-help}"
shift 2>/dev/null || true

cmd_reveal() {
    local path="${1:-}"
    if [[ -z "$path" ]]; then
        echo "Error: Path required. Usage: mac-finder reveal <path>"
        exit 1
    fi
    # Resolve to absolute path
    local abs_path
    abs_path="$(cd "$(dirname "$path")" 2>/dev/null && pwd)/$(basename "$path")" || {
        echo "Error: Path does not exist: $path"
        exit 1
    }
    if [[ ! -e "$abs_path" ]]; then
        echo "Error: Path does not exist: $abs_path"
        exit 1
    fi
    echo "Revealing in Finder: $abs_path"
    open -R "$abs_path"
    echo "Done."
}

cmd_trash() {
    local path="${1:-}"
    if [[ -z "$path" ]]; then
        echo "Error: Path required. Usage: mac-finder trash <path>"
        exit 1
    fi
    # Resolve to absolute path
    local abs_path
    abs_path="$(cd "$(dirname "$path")" 2>/dev/null && pwd)/$(basename "$path")" || {
        echo "Error: Path does not exist: $path"
        exit 1
    }
    if [[ ! -e "$abs_path" ]]; then
        echo "Error: Path does not exist: $abs_path"
        exit 1
    fi
    # Prevent accidental deletion of critical paths
    local dangerous_paths=("/" "/Users" "/System" "/Library" "/Applications" "/usr" "/bin" "/sbin" "/etc")
    for danger in "${dangerous_paths[@]}"; do
        if [[ "$abs_path" == "$danger" ]]; then
            echo "Error: Refusing to trash a protected system path: $abs_path"
            exit 1
        fi
    done
    echo "Moving to Trash: $abs_path"
    osascript -e "tell application \"Finder\" to delete POSIX file \"$abs_path\""
    echo "Moved to Trash."
}

cmd_downloads() {
    local downloads_dir="$HOME/Downloads"
    echo "=== Recent Downloads (last 10) ==="
    if [[ ! -d "$downloads_dir" ]]; then
        echo "Downloads folder not found: $downloads_dir"
        exit 1
    fi
    ls -lt "$downloads_dir" | grep -v '^total' | head -10 | awk '{
        size=$5; name="";
        for(i=9; i<=NF; i++) name = name (i==9 ? "" : " ") $i;
        printf "%-10s %s %s %s  %s\n", size, $6, $7, $8, name
    }'
}

cmd_desktop() {
    local desktop_dir="$HOME/Desktop"
    echo "=== Desktop Files ==="
    if [[ ! -d "$desktop_dir" ]]; then
        echo "Desktop folder not found: $desktop_dir"
        exit 1
    fi
    local count=0
    while IFS= read -r -d '' entry; do
        local name
        name=$(basename "$entry")
        if [[ -d "$entry" ]]; then
            echo "[DIR]  $name"
        else
            local size
            size=$(du -sh "$entry" 2>/dev/null | cut -f1)
            echo "[FILE] $name ($size)"
        fi
        ((count++))
    done < <(find "$desktop_dir" -maxdepth 1 ! -name ".*" ! -path "$desktop_dir" -print0 2>/dev/null | sort -z)
    if [[ $count -eq 0 ]]; then
        echo "(Desktop is empty)"
    else
        echo ""
        echo "Total items: $count"
    fi
}

cmd_help() {
    echo "mac-finder — Finder operations"
    echo ""
    echo "Commands:"
    echo "  reveal <path>    Reveal a file or folder in Finder"
    echo "  trash <path>     Move a file or folder to the Trash"
    echo "  downloads        List recent Downloads (last 10 items)"
    echo "  desktop          List all Desktop files and folders"
    echo "  help             Show this help"
    echo ""
    echo "Examples:"
    echo "  mac-finder reveal ~/Documents/report.pdf"
    echo "  mac-finder trash ~/Desktop/old-file.txt"
    echo "  mac-finder downloads"
    echo "  mac-finder desktop"
}

case "$COMMAND" in
    reveal)     cmd_reveal "$@" ;;
    trash)      cmd_trash "$@" ;;
    downloads)  cmd_downloads ;;
    desktop)    cmd_desktop ;;
    help|*)     cmd_help ;;
esac
