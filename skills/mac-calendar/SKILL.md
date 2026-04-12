# mac-calendar

macOS Calendar and Reminders skill for the OpenClaude Telegram bot.

## Commands

| Command | Description |
|---------|-------------|
| `events [days]` | List upcoming calendar events (default: next 7 days) |
| `reminders` | List all incomplete reminders across all lists |
| `add-event <title> <date> <time>` | Create a new calendar event (1 hour duration) |
| `add-reminder <title>` | Create a new reminder in the default list |

## Usage

```bash
./skills/mac-calendar/run.sh events
./skills/mac-calendar/run.sh events 14
./skills/mac-calendar/run.sh reminders
./skills/mac-calendar/run.sh add-event "Team Standup" 2026-04-15 09:00
./skills/mac-calendar/run.sh add-reminder "Buy groceries"
```

## Argument Formats

- `date` — YYYY-MM-DD (e.g., `2026-04-15`)
- `time` — HH:MM in 24-hour format (e.g., `14:30`)
- `days` — positive integer (e.g., `7`, `30`)

## Tools Used

- `osascript` (AppleScript) — Calendar.app and Reminders.app automation

## Notes

- `add-event` creates a 1-hour event in the **first/default calendar**. To target a specific calendar, modify the AppleScript.
- `add-reminder` creates a reminder in the **first/default list**.
- Requires Full Disk Access or Calendar/Reminders permissions granted to Terminal/the shell.
- Event titles with double quotes are automatically converted to single quotes for AppleScript safety.
