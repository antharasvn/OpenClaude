# Skill: telegram-sender

## Purpose
Send messages, files, and photos to Telegram chats directly via the Telegram Bot API.
Useful for proactive notifications, delivering files, sending images, and sending messages outside of the normal request-response flow.

## Usage

### Send a text message
```bash
./skills/telegram-sender/send.sh --text "Hello from Claude!" --chat CHAT_ID
```

### Send a file
```bash
./skills/telegram-sender/send.sh --file /path/to/file.pdf --chat CHAT_ID
```

### Send a file with caption
```bash
./skills/telegram-sender/send.sh --file /path/to/file.pdf --caption "Here's the report" --chat CHAT_ID
```

### Send a photo (local file)
```bash
./skills/telegram-sender/send.sh --photo /path/to/image.jpg --chat CHAT_ID
```

### Send a photo with caption
```bash
./skills/telegram-sender/send.sh --photo /path/to/image.jpg --caption "Check this out" --chat CHAT_ID
```

### Send a photo by URL
```bash
./skills/telegram-sender/send.sh --photo-url "https://example.com/img.jpg" --chat CHAT_ID
```

### Send with HTML formatting
```bash
./skills/telegram-sender/send.sh --text "<b>Important:</b> Task complete" --chat CHAT_ID --html
```

## Options
| Flag | Description |
|------|-------------|
| `--text` | Text message to send |
| `--file` | Path to file to send as a document (downloadable) |
| `--photo` | Path to image file to send as a photo (displayed inline) |
| `--photo-url` | URL of image to send as a photo (displayed inline, no download needed) |
| `--chat` | Target chat ID (overrides `TELEGRAM_CHAT_ID`) |
| `--caption` | Caption for files and photos |
| `--html` | Parse message/caption as HTML |
| `--markdown` | Parse message/caption as MarkdownV2 |
| `--token` | Bot token (overrides `TELEGRAM_BOT_TOKEN`) |

## Environment Variables
- `TELEGRAM_BOT_TOKEN` — Required. Read from .env if not set.
- `TELEGRAM_CHAT_ID` — Default chat ID. Can be overridden with --chat flag.

## Exit Codes
- 0: Success
- 1: Missing required parameters
- 2: API request failed
