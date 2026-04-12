#!/usr/bin/env bash
# safe-restart.sh — Test-gated restart with rollback and admin notification.
# Called by ouroboros when the bot is dead. Runs tests before starting,
# rolls back to the last known-good commit if tests or startup fail.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVICE_LABEL="com.claude.telegram-bot"
KNOWN_GOOD_FILE="$PROJECT_DIR/backups/known-good-commit"
ROLLBACK_LOCK="$PROJECT_DIR/backups/rollback-lock"
MAX_RETRIES=3
STARTUP_WAIT=15

# Load .env for TELEGRAM_CHAT_ID / ALLOWED_USERS
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

# Resolve admin chat ID: TELEGRAM_CHAT_ID, or first entry in ALLOWED_USERS
ADMIN_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
if [[ -z "$ADMIN_CHAT_ID" && -n "${ALLOWED_USERS:-}" ]]; then
    ADMIN_CHAT_ID="${ALLOWED_USERS%%,*}"
    ADMIN_CHAT_ID="${ADMIN_CHAT_ID// /}"
fi

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [safe-restart] $*"
}

notify() {
    local msg="$1"
    log "NOTIFY: $msg"
    if [[ -n "$ADMIN_CHAT_ID" ]]; then
        "$SCRIPT_DIR/../skills/telegram-sender/send.sh" \
            --text "$msg" --chat "$ADMIN_CHAT_ID" 2>/dev/null || true
    fi
}

get_short_hash() {
    git -C "$PROJECT_DIR" rev-parse --short HEAD 2>/dev/null || echo "unknown"
}

edit_restart_messages() {
    local text="$1"
    local file="$PROJECT_DIR/.restart-messages.json"
    [[ -f "$file" ]] || return 0

    local token=""
    if [[ -f "$PROJECT_DIR/.env" ]]; then
        token=$(grep -E '^TELEGRAM_BOT_TOKEN=' "$PROJECT_DIR/.env" | cut -d= -f2- | tr -d '"' | tr -d "'")
    fi
    [[ -n "$token" ]] || return 0

    python3 -c "
import json, urllib.request
msgs = json.load(open('$file'))
for m in msgs:
    data = json.dumps({'chat_id': m['chat_id'], 'message_id': m['message_id'], 'text': '$text'}).encode()
    req = urllib.request.Request(
        'https://api.telegram.org/bot$token/editMessageText',
        data=data, headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass
" 2>/dev/null || true

    rm -f "$file"
}

sync_dev() {
    log "Syncing with origin/dev..."
    cd "$PROJECT_DIR"

    if ! git fetch origin 2>/dev/null; then
        log "git fetch failed (offline?), continuing with local state"
        return 0
    fi

    # If we previously rolled back, don't merge until remote moves past the bad commit
    if [[ -f "$ROLLBACK_LOCK" ]]; then
        local bad_commit remote_head
        bad_commit=$(cat "$ROLLBACK_LOCK")
        remote_head=$(git -C "$PROJECT_DIR" rev-parse origin/dev 2>/dev/null || echo "")

        if git -C "$PROJECT_DIR" merge-base --is-ancestor "$bad_commit" "$remote_head" 2>/dev/null; then
            # Remote still contains the bad commit — check if it has moved past it
            if [[ "$remote_head" == "$bad_commit" ]]; then
                log "Rollback lock active — remote still at bad commit ${bad_commit:0:7}, skipping sync"
                return 0
            fi
            # Remote has new commits on top of the bad one — try them (fix may have been pushed)
            log "Rollback lock: remote has new commits past ${bad_commit:0:7}, attempting sync"
        fi

        # Remote moved past the bad commit or diverged — clear the lock and sync
        rm -f "$ROLLBACK_LOCK"
        log "Rollback lock cleared"
    fi

    # Only merge if there's something to merge
    local local_head remote_head
    local_head=$(git rev-parse HEAD 2>/dev/null)
    remote_head=$(git rev-parse origin/dev 2>/dev/null || echo "")

    if [[ -z "$remote_head" || "$local_head" == "$remote_head" ]]; then
        log "Already up to date with origin/dev"
        return 0
    fi

    if ! git merge origin/dev --no-edit 2>/dev/null; then
        git merge --abort 2>/dev/null || true
        notify "[safe-restart] Merge conflict with origin/dev on commit $(get_short_hash). Manual resolution needed."
        return 1
    fi

    log "Merged origin/dev successfully"
    return 0
}

run_tests() {
    log "Running tests..."
    local output
    if output=$(cd "$PROJECT_DIR" && "$PROJECT_DIR/.venv/bin/python" -m pytest tests/ --tb=short -q -x 2>&1); then
        log "Tests passed"
        return 0
    else
        log "Tests FAILED"
        # Store last 20 lines for notification
        TEST_OUTPUT=$(echo "$output" | tail -20)
        return 1
    fi
}

record_good() {
    # Clean up rollback info if present
    rm -f "$PROJECT_DIR/.rollback-info.json"
    mkdir -p "$PROJECT_DIR/backups"
    git -C "$PROJECT_DIR" rev-parse HEAD > "$KNOWN_GOOD_FILE"
    log "Recorded known-good commit: $(get_short_hash)"
}

rollback() {
    if [[ ! -f "$KNOWN_GOOD_FILE" ]]; then
        notify "[safe-restart] No known-good commit found at $KNOWN_GOOD_FILE. Manual intervention needed."
        return 1
    fi

    local good_commit
    good_commit=$(cat "$KNOWN_GOOD_FILE")
    local current_commit
    current_commit=$(git -C "$PROJECT_DIR" rev-parse HEAD 2>/dev/null || echo "unknown")

    if [[ "$current_commit" == "$good_commit" ]]; then
        notify "[safe-restart] Already at known-good commit ($good_commit). Known-good is also failing. Manual intervention needed."
        return 1
    fi

    log "Rolling back from $(get_short_hash) to ${good_commit:0:7}..."
    git -C "$PROJECT_DIR" reset --hard "$good_commit"

    # Write rollback info for bot injection
    local created_ts
    created_ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    local test_output_escaped
    test_output_escaped=$(echo "$TEST_OUTPUT" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null || echo '""')
    cat > "$PROJECT_DIR/.rollback-info.json" <<EOF
{
  "created": "$created_ts",
  "bad_commit": "$current_commit",
  "good_commit": "$good_commit",
  "test_output": $test_output_escaped
}
EOF

    # Lock out sync_dev so ouroboros doesn't re-merge the bad commit
    echo "$current_commit" > "$ROLLBACK_LOCK"
    log "Rollback lock set — blocking sync until remote moves past ${current_commit:0:7}"
    return 0
}

get_service_pid() {
    launchctl list "$SERVICE_LABEL" 2>/dev/null | awk -F'= ' '/"PID"/{gsub(/[;"]/,"",$2); print $2}'
}

is_service_alive() {
    local pid
    pid=$(get_service_pid)
    [[ -n "$pid" && "$pid" != "-" ]] && kill -0 "$pid" 2>/dev/null
}

start_service() {
    log "Starting $SERVICE_LABEL..."
    # kickstart -k stops the running instance (if any) and starts a fresh one.
    # Do NOT use `bootout` — that unloads the plist entirely.
    if ! launchctl kickstart -k "gui/$(id -u)/$SERVICE_LABEL" 2>/dev/null; then
        log "launchctl kickstart failed for $SERVICE_LABEL"
        return 1
    fi

    # Poll for a valid PID (up to 5s)
    local pid_start=""
    for _ in 1 2 3 4 5; do
        pid_start=$(get_service_pid)
        if [[ -n "$pid_start" && "$pid_start" != "-" && "$pid_start" != "0" ]]; then
            break
        fi
        sleep 1
    done

    if [[ -z "$pid_start" || "$pid_start" == "-" || "$pid_start" == "0" ]]; then
        log "$SERVICE_LABEL failed to start (no PID after 5s)"
        return 1
    fi

    # Check that the SAME process stays alive for the full wait period.
    # A crash-looping bot may briefly appear active between launchd restarts,
    # so we verify PID stability, not just liveness.
    local checks=3
    local interval=$(( STARTUP_WAIT / checks ))
    for i in $(seq 1 "$checks"); do
        sleep "$interval"
        local pid_now
        pid_now=$(get_service_pid)
        if [[ -z "$pid_now" || "$pid_now" == "-" || "$pid_now" == "0" ]]; then
            log "$SERVICE_LABEL died during startup check $i/$checks (no PID)"
            return 1
        fi
        if [[ "$pid_now" != "$pid_start" ]]; then
            log "$SERVICE_LABEL PID changed ($pid_start -> $pid_now) during check $i/$checks — crash-looping"
            return 1
        fi
        if ! kill -0 "$pid_now" 2>/dev/null; then
            log "$SERVICE_LABEL process $pid_now is gone during check $i/$checks"
            return 1
        fi
    done

    log "$SERVICE_LABEL started successfully (PID $pid_start, stable for ${STARTUP_WAIT}s)"
    return 0
}

# ── Main flow ────────────────────────────────────────────────────────

TEST_OUTPUT=""

# Step 1: Sync with dev
if ! sync_dev; then
    exit 1
fi

# Step 2: Test + start loop with retries
for attempt in $(seq 1 "$MAX_RETRIES"); do
    log "Attempt $attempt/$MAX_RETRIES"

    if run_tests; then
        if start_service; then
            record_good
            log "Bot is alive and healthy"
            if (( attempt > 1 )); then
                notify "[safe-restart] Recovered after rollback to $(get_short_hash). Bot is running."
            fi
            exit 0
        else
            # Startup failed despite tests passing
            notify "[safe-restart] Tests passed but $SERVICE_LABEL failed to start (attempt $attempt/$MAX_RETRIES). Commit: $(get_short_hash).
Last output:
$TEST_OUTPUT"
        fi
    else
        notify "[safe-restart] Tests FAILED (attempt $attempt/$MAX_RETRIES). Commit: $(get_short_hash).
Test output:
$TEST_OUTPUT"
    fi

    # Roll back and retry
    if ! rollback; then
        # rollback already sent notification
        exit 1
    fi
done

notify "[safe-restart] All $MAX_RETRIES attempts exhausted. Manual intervention needed."
edit_restart_messages "❌ Restart failed"
exit 1
