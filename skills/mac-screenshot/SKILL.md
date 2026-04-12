# mac-screenshot

macOS screenshot capture skill for the OpenClaude Telegram bot.

## Commands

| Command | Description |
|---------|-------------|
| `screen` | Capture the entire screen |
| `window` | Capture the frontmost window |

## Usage

```bash
./skills/mac-screenshot/run.sh screen
./skills/mac-screenshot/run.sh window
```

## Output

Screenshots are saved to the workspace `temp/` directory with timestamp filenames:
- `screenshot_YYYYMMDD_HHMMSS.png` (full screen)
- `screenshot_window_YYYYMMDD_HHMMSS.png` (window)

The script emits a `FILE:/path/to/file` line that the bot uses to send the image via Telegram.

## Tools Used

- `screencapture` — macOS built-in screenshot tool
- `osascript` — get window ID for targeted window capture

## Environment

- `WORKSPACE_DIR` — if set by the bot, screenshots go here; otherwise falls back to `$PROJECT_DIR/temp`

## Notes

- `-x` flag suppresses the camera shutter sound.
- Window capture falls back to full screen if the window ID cannot be determined.
- Requires Screen Recording permission granted to Terminal in System Preferences > Privacy & Security.
- Screenshots are ephemeral — `temp/` is periodically cleaned.
