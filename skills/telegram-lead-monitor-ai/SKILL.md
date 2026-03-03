# Skill: telegram-lead-monitor-ai

## Purpose
Two-stage Telegram lead monitor: a Python collector gathers messages on a cron schedule, then the Claude coordinator analyzes them with full AI intelligence and sends notifications.

## Architecture

### Stage 1: Collection (Python, cron every 10 min)
1. `run.sh run-once` triggers `collect.py`
2. `collect.py` connects to Telegram via Telethon (user account)
3. Fetches messages from last 12 minutes across all group chats
4. Saves to JSON: `workspace/temp/pending-messages-TIMESTAMP.json`
5. `run.sh` sends a notification to admin chat via `telegram-sender`

### Stage 2: Analysis (Claude coordinator, triggered by notification)
When the coordinator sees a "Lead analysis requested" message:
1. Read the JSON file referenced in the message
2. Analyze each message for development leads using AI judgment
3. Check dedup against SQLite DB (`lead-monitor-ai.db`)
4. Send notifications for valid leads to the target chat/thread
5. Record sent leads in the DB
6. Clean up the temp JSON file

## Usage
```bash
# Run once (for testing or manual invocation)
./skills/telegram-lead-monitor-ai/run.sh run-once

# Install cron job (every 10 minutes)
./skills/telegram-lead-monitor-ai/cron-setup.sh install

# Remove cron job
./skills/telegram-lead-monitor-ai/cron-setup.sh uninstall
```

## Required Environment Variables

### From workspace .env:
- `TG_MONITOR_API_ID` — Telegram API ID
- `TG_MONITOR_API_HASH` — Telegram API Hash
- `TG_MONITOR_PHONE` — Phone number for Telegram auth

### From project .env (infrastructure):
- `TELEGRAM_BOT_TOKEN` — Bot token for sending notifications

### Optional:
- `TELEGRAM_ADMIN_CHAT_ID` — Admin chat ID for notifications (default: 917951142)
- `TG_MONITOR_TARGET_CHAT` — Chat ID for lead notifications (e.g., `c-1003610406070`)
- `TG_MONITOR_TARGET_THREAD` — Thread/topic ID for lead notifications (e.g., `83`)

## JSON Message Format
```json
[
  {
    "chat_id": -1001234567890,
    "chat_name": "Dev Chat",
    "message_id": 12345,
    "sender_id": 987654321,
    "text": "Message text...",
    "date": "2026-02-27T10:30:00+00:00",
    "link": "https://t.me/c/1234567890/12345"
  }
]
```

## Coordinator Analysis Guidelines

When analyzing messages, the coordinator should:

### Consider as leads (score 50+):
- Someone looking to hire a developer/contractor/freelancer
- Someone asking who can build a website/bot/app/integration
- Budget mentions with technical requirements
- Deadline + technical task descriptions

### Exclude:
- **Job seekers** — people looking for work, not hiring
- **Vacancies** — full-time positions (unless freelance/contract)
- **Tutorials** — learning questions without hiring intent
- **Self-promotion** — developers advertising their own services
- **Vague questions** — "who knows about X?" without hiring intent
- **Illegal requests** — hacking, spam, fraud

### Dedup:
- Check `leads` table in `lead-monitor-ai.db` for similar messages from same chat in last 24h
- Use word overlap similarity (>= 0.88 overlap ratio) to detect duplicates

### Notification format:
Send to target chat/thread via `telegram-sender`:
```
🎯 Ищут разработчика:

[Brief description of what they need]

Приоритет: 🔴/🟡/🟢 strong/medium/weak
💬 Chat: [chat name]
🔗 Link: [message link]

Контекст: [what type of service: website, bot, AI, etc.]
```

## Files
- `SKILL.md` — this file
- `run.sh` — entry point: runs collector and notifies coordinator
- `collect.py` — Python collector: fetches messages, saves JSON
- `cron-setup.sh` — helper to install/uninstall cron job
- `requirements.txt` — Python dependencies (telethon only)

## Database
SQLite DB at `{workspace}/lead-monitor-ai.db`:
- `leads` — sent lead notifications (for dedup): chat_id, message_id, text, score, priority, sent_at, text_hash
- `state` — per-chat last_message_id and last_run_time for tracking progress
