# mac-clipboard

macOS clipboard read/write skill for the OpenClaude Telegram bot.

## Commands

| Command | Description |
|---------|-------------|
| `get` | Read and return current clipboard contents |
| `set <text>` | Replace clipboard contents with given text |

## Usage

```bash
./skills/mac-clipboard/run.sh get
./skills/mac-clipboard/run.sh set "Hello, world!"
./skills/mac-clipboard/run.sh set "Multi word text with spaces"
```

## Tools Used

- `pbpaste` — read clipboard
- `pbcopy` — write to clipboard

## Notes

- `get` shows the character count alongside the content.
- `set` uses `printf '%s'` (not `echo`) to avoid adding a trailing newline to the clipboard.
- Only plain text is supported. Images or rich content on the clipboard will return garbled output from `pbpaste`.
- Clipboard contents are not truncated — be mindful when sending very large clipboard contents via Telegram (4096 char limit per message).
