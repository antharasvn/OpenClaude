# mac-finder

macOS Finder operations skill for the OpenClaude Telegram bot.

## Commands

| Command | Description |
|---------|-------------|
| `reveal <path>` | Reveal a file or folder in Finder (selects it) |
| `trash <path>` | Move a file or folder to the Trash |
| `downloads` | List the 10 most recent items in ~/Downloads |
| `desktop` | List all files and folders on the Desktop |

## Usage

```bash
./skills/mac-finder/run.sh reveal ~/Documents/report.pdf
./skills/mac-finder/run.sh trash ~/Desktop/old-file.txt
./skills/mac-finder/run.sh downloads
./skills/mac-finder/run.sh desktop
```

## Tools Used

- `open -R` — reveal a file in Finder
- `osascript` — move items to Trash via Finder AppleScript
- `ls` / `find` — list Downloads and Desktop contents

## Safety

- `trash` resolves paths to absolute before acting.
- Protected system paths (`/`, `/Users`, `/System`, `/Library`, `/Applications`, `/usr`, `/bin`, `/sbin`, `/etc`) are blocked — the script exits with an error rather than trashing them.
- Non-existent paths are rejected with a clear error message.

## Notes

- `trash` moves items to the Trash (recoverable) — it does NOT permanently delete files.
- `reveal` opens Finder and selects the item in its containing folder.
- `desktop` hides dotfiles (hidden files starting with `.`).
- `downloads` shows the 10 most recently modified items, including both files and folders.
