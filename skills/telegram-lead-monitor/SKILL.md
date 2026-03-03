# Skill: telegram-lead-monitor

## Purpose
Monitors all incoming Telegram messages across a user account's chats using the Telegram User API (Telethon).
Uses keyword matching to detect lead requests for software development services (no AI API required).
Sends notifications to the admin chat when a lead is found.

## Usage

### Start monitoring
```bash
./skills/telegram-lead-monitor/run.sh start
```

### Stop monitoring
```bash
./skills/telegram-lead-monitor/run.sh stop
```

### Check status
```bash
./skills/telegram-lead-monitor/run.sh status
```

### First run (interactive — requires 2FA code)
```bash
python3 ./skills/telegram-lead-monitor/monitor.py --auth-only
```

## Environment Variables
**Infrastructure skill** — sources `$PROJECT_DIR/.env` for bot tokens, plus workspace `.env` for monitor credentials.

| Variable | Description |
|----------|-------------|
| `TG_MONITOR_API_ID` | Telegram API ID for the user account |
| `TG_MONITOR_API_HASH` | Telegram API hash for the user account |
| `TG_MONITOR_PHONE` | Phone number of the monitored account |
| `TG_MONITOR_ADMIN_CHAT_ID` | Chat ID where lead notifications are sent |
| `TELEGRAM_BOT_TOKEN` | Bot token used by telegram-sender for notifications |

## Notification Format
```
🎯 Ищут разработчика:

{matched keyword + context snippet}

💬 Chat: {chat_name}
🔗 Link: {message_link}
```

## Files
- `monitor.py` — Main Python daemon
- `run.sh` — Start/stop/status wrapper
- `requirements.txt` — Python dependencies

## Session & Data
- Telegram session file stored in workspace directory
- SQLite database tracks processed message IDs to prevent duplicates
- Logs written to `logs/lead-monitor.log` in workspace
