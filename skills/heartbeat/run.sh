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
CYCLE_START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[heartbeat] Starting heartbeat at $CYCLE_START"

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

# A dead cycle exits in seconds, writes no daily log, sends nothing, and still
# stamps last_run — so nothing outside this file ever notices. Count them here.
#
# Detection is STRUCTURAL only: non-zero exit + ≤400 B of output. Healthy cycles
# exit 0 with ~3 KB transcripts, so quoting a failure phrase never false-positives
# on structure. The phrase must NOT gate detection: a 529-Overloaded cycle
# (2026-08-18 16:46Z) carried no quota phrase, was stamped last_success under the
# old phrase-gated rule, and a 529 storm would never have alerted. The output text
# is kept only to LABEL the cause in the alert.
CLAUDE_BYTES=$(wc -c < "$CLAUDE_OUT" | tr -d ' ')
REFUSED=0
REASON=""
if [[ $CLAUDE_RC -ne 0 && $CLAUDE_BYTES -le 400 ]]; then
    REFUSED=1
    REASON="$(head -c 200 "$CLAUDE_OUT" | tr -d '\n')"
    # gtimeout cap (124) in -p mode leaves stdout empty — synthesize a label.
    [[ -z "$REASON" ]] && REASON="exit $CLAUDE_RC with empty output"
    # ...but on the 124 branch `≤400 B` is satisfied BY CONSTRUCTION: `claude -p`
    # emits its result only at the end, so a cap-kill has 0 B of stdout however
    # much work landed. 2026-08-20T18:57:33Z ran the full cycle, wrote its daily
    # log, patched HEARTBEAT.md and pushed 19e56f1 at 19:07:10Z — 24 s before the
    # kill — and was still booked a refusal. Two of those in a row would alert the
    # user that a working fleet is down. Ask the artifact, not the transcript:
    # a commit inside this cycle's window means the work shipped and only the
    # SUMMARY was truncated. Same principle as the structural rule above (never
    # key on text the subject writes) applied to a branch where the structural
    # signal it chose has no power.
    if [[ $CLAUDE_RC -eq 124 ]] \
       && [[ -n "$(git -C "$PROJECT_DIR" log --since="$CYCLE_START" --grep="^heartbeat " --format=%h 2>/dev/null)" ]]; then
        REFUSED=0
        REASON=""
        echo "[heartbeat] exit 124 but commits landed in-window — truncated success, not a refusal"
    fi
fi
rm -f "$CLAUDE_OUT"

# Update state file with new timestamp + refusal accounting
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
ALERT=$(python3 - "$STATE_FILE" "$NOW" "$REFUSED" "$REASON" <<'PYEOF'
import json, sys

state_file, now, refused = sys.argv[1], sys.argv[2], sys.argv[3] == "1"
reason = sys.argv[4]
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
    data["last_refusal_reason"] = reason
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
        ALERT_MSG="⚠️ Heartbeat fleet is dark — $ALERT_N consecutive cycles (~$((ALERT_N * 15)) min) exited without running. Latest error: ${REASON:-unknown}. Cron alerts are unaffected (different CLI, different quota), so logs/infra.log will look healthy. See /tmp/claude-heartbeat.log."
    else
        ALERT_MSG="✅ Heartbeat fleet is running again after $ALERT_N refused cycles (~$((ALERT_N * 15)) min dark)."
    fi
    "$PROJECT_DIR/skills/telegram-sender/send.sh" --text "$ALERT_MSG" >/dev/null 2>&1 \
        || echo "[heartbeat] backpressure alert send FAILED"
fi

echo "[heartbeat] Completed at $NOW"
