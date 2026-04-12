#!/usr/bin/env bash
# mac-calendar — macOS Calendar and Reminders skill
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source project .env (infrastructure skill)
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a; source "$PROJECT_DIR/.env"; set +a
fi

COMMAND="${1:-help}"
shift 2>/dev/null || true

cmd_events() {
    local days="${1:-7}"
    # Validate days is a positive integer
    if ! [[ "$days" =~ ^[0-9]+$ ]] || [[ "$days" -lt 1 ]]; then
        echo "Error: days must be a positive integer (got: '$days')"
        exit 1
    fi
    echo "=== Upcoming Events (next ${days} days) ==="
    osascript <<EOF
set dayCount to $days
set today to current date
set futureDate to today + (dayCount * days)
set output to ""
tell application "Calendar"
    repeat with cal in calendars
        set evts to (every event of cal whose start date >= today and start date <= futureDate)
        repeat with evt in evts
            set evtDate to start date of evt
            set evtTitle to summary of evt
            set output to output & (evtDate as string) & " | " & evtTitle & linefeed
        end repeat
    end repeat
end tell
if output is "" then
    return "No events in the next " & dayCount & " days."
end if
return output
EOF
}

cmd_reminders() {
    echo "=== Incomplete Reminders ==="
    osascript <<'EOF'
set output to ""
tell application "Reminders"
    repeat with reminderList in lists
        set incomplete to (every reminder of reminderList whose completed is false)
        repeat with r in incomplete
            set rName to name of r
            set listName to name of reminderList
            set output to output & "[" & listName & "] " & rName & linefeed
        end repeat
    end repeat
end tell
if output is "" then
    return "No incomplete reminders."
end if
return output
EOF
}

cmd_add_event() {
    local title="${1:-}"
    local date_str="${2:-}"
    local time_str="${3:-}"

    if [[ -z "$title" || -z "$date_str" || -z "$time_str" ]]; then
        echo "Error: Usage: mac-calendar add-event <title> <date> <time>"
        echo "  date format: YYYY-MM-DD"
        echo "  time format: HH:MM (24h)"
        exit 1
    fi

    # Validate date format
    if ! [[ "$date_str" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        echo "Error: Invalid date format. Use YYYY-MM-DD (e.g., 2026-04-15)"
        exit 1
    fi

    # Validate time format
    if ! [[ "$time_str" =~ ^[0-9]{2}:[0-9]{2}$ ]]; then
        echo "Error: Invalid time format. Use HH:MM in 24h (e.g., 14:30)"
        exit 1
    fi

    # Sanitize title — strip any AppleScript-breaking characters
    title="${title//\"/\'}"

    # Parse date and time components
    local year month day hour minute
    year="${date_str:0:4}"
    month="${date_str:5:2}"
    day="${date_str:8:2}"
    hour="${time_str:0:2}"
    minute="${time_str:3:2}"

    echo "Creating event: \"$title\" on $date_str at $time_str"
    osascript <<EOF
tell application "Calendar"
    set targetCal to first calendar
    set startDate to date "$month/$day/$year $hour:$minute:00"
    set endDate to startDate + (1 * hours)
    set newEvent to make new event in targetCal with properties {summary:"$title", start date:startDate, end date:endDate}
    return "Event created: " & summary of newEvent
end tell
EOF
}

cmd_add_reminder() {
    local title="${1:-}"
    if [[ -z "$title" ]]; then
        echo "Error: Usage: mac-calendar add-reminder <title>"
        exit 1
    fi
    # Sanitize
    title="${title//\"/\'}"
    echo "Creating reminder: \"$title\""
    osascript <<EOF
tell application "Reminders"
    set targetList to first list
    set newReminder to make new reminder in targetList with properties {name:"$title"}
    return "Reminder created: " & name of newReminder
end tell
EOF
}

cmd_help() {
    echo "mac-calendar — Calendar and Reminders control"
    echo ""
    echo "Commands:"
    echo "  events [days]                 Upcoming calendar events (default: 7 days)"
    echo "  reminders                     List incomplete reminders"
    echo "  add-event <title> <date> <time>  Create a calendar event"
    echo "  add-reminder <title>          Create a reminder"
    echo "  help                          Show this help"
    echo ""
    echo "Examples:"
    echo "  mac-calendar events"
    echo "  mac-calendar events 14"
    echo "  mac-calendar add-event \"Team Standup\" 2026-04-15 09:00"
    echo "  mac-calendar add-reminder \"Buy groceries\""
}

case "$COMMAND" in
    events)         cmd_events "$@" ;;
    reminders)      cmd_reminders ;;
    add-event)      cmd_add_event "$@" ;;
    add-reminder)   cmd_add_reminder "$@" ;;
    help|*)         cmd_help ;;
esac
