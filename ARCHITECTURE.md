# Project Structure

```
OpenClaude/
├── bot/                 # Main bot package (python -m bot)
│   ├── __main__.py      # Entry point
│   ├── app.py           # Application builder, startup, shutdown
│   ├── config.py        # Configuration, constants, authorization
│   ├── logging_setup.py # Logger setup (infra, workspace loggers)
│   ├── sessions.py      # Session persistence (load/save/clear)
│   ├── streams.py       # Active stream tracking (crash recovery)
│   ├── sdk_session.py   # SDKSession class, idle cleanup
│   ├── workspaces.py    # Per-chat workspace creation, symlinks
│   ├── permissions.py   # Security rules, env building, permission handler
│   ├── claude.py        # Claude integration (streaming, SDK/subprocess)
│   ├── renderer.py      # TelegramRenderer + message splitting
│   ├── handlers.py      # Message/media handlers, batching, streaming UI
│   └── transcribe.py    # Voice transcription bridge
├── commands/            # Slash command handlers
├── telegram-bot.py      # Backward-compatible entry point
├── transcribe.py        # Voice transcription module
├── CLAUDE.md            # Operating manual (instructions, rules, safety)
├── TOOLS.md             # Available tools and environment
├── BOOTSTRAP.md         # First-run ritual (deleted after)
├── ARCHITECTURE.md      # This file
├── README.md            # Project documentation
├── requirements.txt     # Python dependencies
├── .env.example         # Environment template
├── bin/                 # Operational scripts
│   ├── start.sh         # Start the bot
│   ├── stop.sh          # Stop the bot
│   ├── restart.sh       # Restart the bot
│   ├── safe-restart.sh  # Graceful restart (waits for streams)
│   ├── setup.sh         # Interactive setup
│   ├── ouroboros.sh     # Watchdog loop
│   ├── log-cleanup.sh   # Log rotation
│   └── notify-interrupted.sh  # Notify users of interrupted streams
├── guard/               # Security hooks
│   ├── guard.sh         # Blocks dangerous Bash commands
│   └── guard-write.sh   # Blocks writes to protected files
├── services/            # Daemon configs
│   ├── systemd/         # Linux service units
│   └── launchd/         # macOS launch agents
├── skills/              # Skill scripts
│   ├── telegram-sender/ # Send messages via Telegram API
│   ├── ssh-vps/         # Run commands on VPS via SSH
│   ├── moodle/          # Moodle LMS integration
│   ├── ai-news/         # Daily AI news digest (cron)
│   ├── create-skill/    # Skill template & safety guidelines
│   ├── heartbeat/       # Periodic check-in skill
│   └── daily-brief/     # Daily briefing skill
├── workspaces/          # Claude Code workspaces (per-chat)
│   └── c{chat_id}/      # Each chat's isolated workspace
│       ├── IDENTITY.md  # Per-user identity (created via BOOTSTRAP)
│       ├── USER.md      # Per-user profile (created via BOOTSTRAP)
│       ├── memory/      # Memory (MEMORY.md + t{id}/YYYY-MM-DD/*.md)
│       └── uploads/     # Uploaded files (per-topic: t{thread_id}/)
└── .env                 # Environment variables (not in git)
```
