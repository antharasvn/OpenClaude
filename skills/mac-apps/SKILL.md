# mac-apps

macOS application control skill for the OpenClaude Telegram bot.

## Commands

| Command | Description |
|---------|-------------|
| `open <app>` | Open an application by name |
| `quit <app>` | Quit an application gracefully |
| `list` | List all running (visible) applications |
| `frontmost` | Show the currently frontmost app |

## Usage

```bash
./skills/mac-apps/run.sh open Safari
./skills/mac-apps/run.sh open "Google Chrome"
./skills/mac-apps/run.sh quit Finder
./skills/mac-apps/run.sh list
./skills/mac-apps/run.sh frontmost
```

## Tools Used

- `open -a` — launch applications
- `osascript` (AppleScript) — quit apps, list processes, get frontmost

## Notes

- App names are case-sensitive and must match exactly (e.g., "Google Chrome" not "chrome").
- `quit` sends a graceful quit signal — the app may prompt to save unsaved work.
- `list` only shows user-visible apps (excludes background daemons).
- Requires Accessibility permissions for `System Events` if the user hasn't granted them already.
