#!/usr/bin/env bash
# moodle — Fetch Innopolis Moodle deadlines via SSO
# Usage: ./skills/moodle/run.sh [deadlines|courses]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source workspace .env only (user credentials, never project root .env)
if [[ -f "$PWD/.env" ]]; then
    set -a
    source "$PWD/.env"
    set +a
fi

# Validate required credentials
: "${MOODLE_USERNAME:?MOODLE_USERNAME not set in .env}"
: "${MOODLE_PASSWORD:?MOODLE_PASSWORD not set in .env}"

CMD="${1:-deadlines}"

# Validate command
case "$CMD" in
    deadlines|courses) ;;
    *)
        echo "Usage: $0 [deadlines|courses]"
        echo "  deadlines — upcoming assignment deadlines (default)"
        echo "  courses   — list current semester courses"
        exit 1
        ;;
esac

# Start Chrome if not already running
if ! curl -s http://localhost:9222/json/version --max-time 3 > /dev/null 2>&1; then
    echo "Starting Chrome..." >&2
    /opt/google/chrome/chrome \
        --no-sandbox \
        --headless=new \
        --disable-gpu \
        --remote-debugging-port=9222 \
        --disable-dev-shm-usage \
        > /tmp/chrome-moodle.log 2>&1 &
    sleep 4
fi

# Run the Python script
exec python3 "$SCRIPT_DIR/moodle.py" "$CMD"
