# mac-shortcuts

Apple Shortcuts CLI skill for the OpenClaude Telegram bot.

## Commands

| Command | Description |
|---------|-------------|
| `list` | List all shortcuts available in Shortcuts.app |
| `run <name>` | Run a shortcut by name |

## Usage

```bash
./skills/mac-shortcuts/run.sh list
./skills/mac-shortcuts/run.sh run "Morning Routine"
./skills/mac-shortcuts/run.sh run "Toggle Dark Mode"
```

## Tools Used

- `shortcuts` CLI — built into macOS 12 Monterey and later

## Notes

- Requires macOS 12 Monterey or later. Will error with a clear message on older versions.
- Shortcut names are **case-sensitive** and must match exactly as they appear in Shortcuts.app.
- `run` has a **60-second timeout** — shortcuts that require user interaction or take too long will be terminated.
- Shortcuts that display UI dialogs or require user input may hang; prefer automation-ready shortcuts.
- The `shortcuts` CLI may require Automation permission in System Preferences the first time it is used.
