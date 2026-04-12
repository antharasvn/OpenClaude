# Tools & Environment

> This file documents the tools, services, and environment available to you.
> Update it as new tools are added or configurations change.

## Claude Code Tools

You have access to these tools when invoked via the Telegram bot:

| Tool | Purpose |
|------|---------|
| `Read` | Read files from the filesystem |
| `Write` | Write files to the filesystem |
| `Edit` | Edit existing files with find-and-replace |
| `Bash` | Execute shell commands |
| `Glob` | Find files by pattern |
| `Grep` | Search file contents with regex |
| `WebFetch` | Fetch and analyze web pages |
| `WebSearch` | Search the web |
| `Task` | Run a sub-agent for complex tasks |
| `Skill` | Execute predefined skill scripts |

## Skills

### create-skill (template) — READ FIRST
- **Location:** `skills/create-skill/SKILL.md`
- **Purpose:** Template and safety guidelines for creating new skills
- **Usage:** Read `skills/create-skill/SKILL.md` before creating any new skill. Follow all safety rules.

### telegram-sender
- **Location:** `skills/telegram-sender/send.sh`
- **Purpose:** Send messages and files to Telegram chats directly
- **Usage:** `send.sh --text "message" --chat CHAT_ID` or `send.sh --file /path/to/file --chat CHAT_ID`

### heartbeat
- **Location:** `skills/heartbeat/run.sh`
- **Purpose:** Periodic proactive check-in — reviews pending tasks, memory, reminders
- **Schedule:** Every 3 hours via launchd
- **Config:** Reads `HEARTBEAT.md` for what to check

### daily-brief
- **Location:** `skills/daily-brief/run.sh`
- **Purpose:** Generate and deliver daily morning briefing
- **Schedule:** 9:00 AM daily via launchd

### mac-system
- **Location:** `skills/mac-system/run.sh`
- **Purpose:** macOS system information — battery, disk, CPU, memory, network
- **Usage:**
  - `./skills/mac-system/run.sh info` — system overview
  - `./skills/mac-system/run.sh processes` — top processes by CPU
  - `./skills/mac-system/run.sh network` — WiFi and IP info

### mac-apps
- **Location:** `skills/mac-apps/run.sh`
- **Purpose:** Control macOS applications
- **Usage:**
  - `./skills/mac-apps/run.sh open "Safari"` — open an app
  - `./skills/mac-apps/run.sh quit "Safari"` — quit an app
  - `./skills/mac-apps/run.sh list` — list running apps
  - `./skills/mac-apps/run.sh frontmost` — show frontmost app

### mac-calendar
- **Location:** `skills/mac-calendar/run.sh`
- **Purpose:** Access Calendar.app and Reminders.app
- **Usage:**
  - `./skills/mac-calendar/run.sh events 7` — upcoming events (next N days)
  - `./skills/mac-calendar/run.sh reminders` — incomplete reminders
  - `./skills/mac-calendar/run.sh add-event "Meeting" "2026-04-15" "14:00"` — create event
  - `./skills/mac-calendar/run.sh add-reminder "Buy groceries"` — create reminder

### mac-clipboard
- **Location:** `skills/mac-clipboard/run.sh`
- **Purpose:** Read and write the macOS clipboard
- **Usage:**
  - `./skills/mac-clipboard/run.sh get` — get clipboard contents
  - `./skills/mac-clipboard/run.sh set "text to copy"` — set clipboard

### mac-screenshot
- **Location:** `skills/mac-screenshot/run.sh`
- **Purpose:** Capture screenshots
- **Usage:**
  - `./skills/mac-screenshot/run.sh screen` — full screen capture
  - `./skills/mac-screenshot/run.sh window` — frontmost window
- **Output:** Saves to workspace `temp/` with timestamp filename

### mac-notify
- **Location:** `skills/mac-notify/run.sh`
- **Purpose:** Show macOS notifications
- **Usage:** `./skills/mac-notify/run.sh send "Title" "Message body"`

### mac-shortcuts
- **Location:** `skills/mac-shortcuts/run.sh`
- **Purpose:** Run Apple Shortcuts
- **Usage:**
  - `./skills/mac-shortcuts/run.sh list` — list available shortcuts
  - `./skills/mac-shortcuts/run.sh run "Shortcut Name"` — run a shortcut

### mac-finder
- **Location:** `skills/mac-finder/run.sh`
- **Purpose:** Finder operations
- **Usage:**
  - `./skills/mac-finder/run.sh reveal "/path/to/file"` — reveal in Finder
  - `./skills/mac-finder/run.sh trash "/path/to/file"` — move to Trash
  - `./skills/mac-finder/run.sh downloads` — list recent downloads
  - `./skills/mac-finder/run.sh desktop` — list desktop files

## Environment

### Machine
- **OS:** macOS (Apple Silicon)
- **Working Directory:** `/Users/antharas/Projects/AAAI.Studio/OS/OpenClaude`
- **User:** antharas (Duc)

### Services (launchd)
- `com.claude.telegram-bot` — always-on Telegram bot daemon
- `com.claude.heartbeat` — proactive check-in every 3 hours
- `com.claude.daily-brief` — morning briefing at 9 AM

### API Keys & Services
- **Anthropic Claude** — via Claude CLI (already authenticated)
- **Telegram Bot API** — `TELEGRAM_BOT_TOKEN` in `.env`
- Per-workspace keys: stored in `workspaces/c{chat_id}/.env`

### Mac Automation
- **AppleScript:** `osascript -e 'script'` — control any Mac app
- **Shortcuts:** `shortcuts run "Name"` — run Apple Shortcuts
- **screencapture:** screenshots and screen recording
- **pbcopy/pbpaste:** clipboard access
- **open:** open files, URLs, and applications

## Sending Files to the User

To deliver a file to the user in Telegram, write a `📎` marker line in your response:

```
📎 /absolute/path/to/file optional caption here
📎 "/absolute/path/with spaces/file.pdf" optional caption
```

The bot strips the line and sends the file as the correct Telegram media type (photo, video, audio, or document). The path must be absolute and inside the workspace.

## Notes
_Add environment-specific notes here as you discover them_
