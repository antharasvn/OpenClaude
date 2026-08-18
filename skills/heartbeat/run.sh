#!/usr/bin/env bash
# heartbeat — Periodic proactive check-in
# Reviews pending tasks, checks memory for reminders, sends updates if notable.

set -euo pipefail

export PATH="/Users/antharas/.local/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source .env
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

STATE_FILE="$PROJECT_DIR/heartbeat-state.json"

# Initialize state file if it doesn't exist
if [[ ! -f "$STATE_FILE" ]]; then
    printf '{"last_run": null, "last_message_sent": null}\n' > "$STATE_FILE"
fi

# Read last run timestamp
LAST_RUN=$(python3 -c "
import json, sys
try:
    with open('$STATE_FILE') as f:
        data = json.load(f)
    print(data.get('last_run') or 'never')
except Exception:
    print('never')
")

echo "[heartbeat] Last run: $LAST_RUN"
echo "[heartbeat] Starting heartbeat at $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Run Claude with heartbeat prompt
cd "$PROJECT_DIR"

# Tee the invocation so the refusal detector below can read it. The log itself is
# unchanged — launchd still captures stdout to /tmp/claude-heartbeat.log.
CLAUDE_OUT="$(mktemp -t heartbeat-out.XXXXXX)"

set +e
/opt/homebrew/bin/gtimeout 600 claude -p "Run heartbeat: YOUR FIRST TOOL CALL, before any other command, must be: ps -eo pid,lstart,etime,command | grep '[g]timeout 600 claude' -- that lstart is your cycle start and your kill is lstart + 600 s. Do NOT use 'date' or 'ps -o lstart= -p \$\$' to establish it; both timestamp your first tool call instead of the cycle, read 10-92 s late, and manufacture budget you do not have. Then read HEARTBEAT.md for the checklist, then work through each item. Review pending tasks, check memory for reminders or things you wanted to follow up on. Last heartbeat ran at: $LAST_RUN. If anything notable, send a brief update via the telegram-sender skill. If nothing to report, just say 'Heartbeat: nothing to report' and do not send a Telegram message." \
    --allowedTools "Read,Write,Edit,Bash,Glob,Grep,WebFetch,WebSearch,Skill" | tee "$CLAUDE_OUT"
CLAUDE_RC=${PIPESTATUS[0]}
set -e
if [[ $CLAUDE_RC -ne 0 ]]; then
    echo "[heartbeat] Timed out or failed (exit $CLAUDE_RC)"
fi

# A quota refusal exits in seconds, writes no daily log, sends nothing, and still
# stamps last_run — so nothing outside this file ever notices. Count them here.
#
# The phrase alone is NOT sufficient: this fleet reports on its own outages, so a
# perfectly healthy cycle quoting "You've hit your weekly limit" in its summary
# matches it (measured against the live log, 2026-08-18). A real refusal is all
# three of: non-zero exit, a single short line of output, and the phrase.
CLAUDE_BYTES=$(wc -c < "$CLAUDE_OUT" | tr -d ' ')
REFUSED=0
if [[ $CLAUDE_RC -ne 0 && $CLAUDE_BYTES -le 400 ]] \
   && grep -qiE "hit your (weekly|session|usage|5-hour) limit|usage limit reached" "$CLAUDE_OUT"; then
    REFUSED=1
fi
rm -f "$CLAUDE_OUT"

# Update state file with new timestamp + refusal accounting
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
ALERT=$(python3 - "$STATE_FILE" "$NOW" "$REFUSED" <<'PYEOF'
import json, sys

state_file, now, refused = sys.argv[1], sys.argv[2], sys.argv[3] == "1"
try:
    with open(state_file) as f:
        data = json.load(f)
except Exception:
    data = {}

prev = int(data.get("consecutive_refusals") or 0)
alert = ""
if refused:
    n = prev + 1
    # Alert on the 2nd consecutive refusal (one-offs are noise), then re-alert
    # once per ~24 h of cycles so a multi-day outage keeps reminding.
    if n == 2 or (n > 2 and (n - 2) % 96 == 0):
        alert = "REFUSED %d" % n
    data["consecutive_refusals"] = n
    data["last_refusal"] = now
else:
    if prev >= 2:
        alert = "RECOVERED %d" % prev
    data["consecutive_refusals"] = 0
    data["last_success"] = now
data["last_run"] = now

with open(state_file, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
print(alert)
PYEOF
)

if [[ -n "$ALERT" ]]; then
    ALERT_KIND="${ALERT%% *}"
    ALERT_N="${ALERT##* }"
    if [[ "$ALERT_KIND" == "REFUSED" ]]; then
        ALERT_MSG="⚠️ Heartbeat fleet is being refused — $ALERT_N consecutive cycles (~$((ALERT_N * 15)) min) exited without running. Cron alerts are unaffected (different CLI, different quota), so logs/infra.log will look healthy. Usual cause is a usage limit; see /tmp/claude-heartbeat.log."
    else
        ALERT_MSG="✅ Heartbeat fleet is running again after $ALERT_N refused cycles (~$((ALERT_N * 15)) min dark)."
    fi
    "$PROJECT_DIR/skills/telegram-sender/send.sh" --text "$ALERT_MSG" >/dev/null 2>&1 \
        || echo "[heartbeat] backpressure alert send FAILED"
fi

echo "[heartbeat] Completed at $NOW"
