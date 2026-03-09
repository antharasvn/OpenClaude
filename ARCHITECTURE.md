# Project Structure

```
OpenClaude/
├── bot/                          # Main bot package (python -m bot)
│   ├── __init__.py               # Package init
│   ├── __main__.py               # Entry point
│   ├── app.py                    # Application builder, startup, shutdown
│   ├── attachments.py            # 📎 file marker parsing, FileAttachment types
│   ├── auth.py                   # Authorization helpers
│   ├── backends.py               # Streaming backends (SDK and subprocess)
│   ├── batching.py               # Message batching logic
│   ├── cache.py                  # FileBackedCache (write-behind disk cache)
│   ├── claude.py                 # Claude integration (thin wrapper)
│   ├── config.py                 # Configuration, constants
│   ├── core/                     # Hexagonal architecture core
│   │   ├── __init__.py           # Package init
│   │   ├── models.py             # UserMessage, ChatSession, StreamState
│   │   ├── ports.py              # AICompletionPort, SessionRepository protocols
│   │   ├── repositories.py       # JsonFile* (prod) + InMemory* (test) repos
│   │   └── use_cases.py          # SessionService, StreamTrackingService
│   ├── events.py                 # Event type definitions
│   ├── exceptions.py             # Custom exception classes
│   ├── formatting.py             # Text formatting utilities
│   ├── handlers.py               # Message handlers, streaming UI
│   ├── latex_render.py           # KaTeX rendering via pinchtab headless Chrome
│   ├── logging_setup.py          # Logger setup (infra, workspace loggers)
│   ├── media.py                  # Media processing utilities
│   ├── media_handlers.py         # Photo/video/audio/document Telegram handlers
│   ├── permissions.py            # Security rules, env building, permission handler
│   ├── process.py                # Subprocess management
│   ├── prompts.py                # System prompt construction
│   ├── renderer.py               # TelegramRenderer + message splitting
│   ├── restart_recovery.py       # Recovery after unexpected restart
│   ├── routing.py                # Message routing logic
│   ├── sdk_session.py            # SDKSession class, idle cleanup
│   ├── sessions.py               # Session persistence (load/save/clear)
│   ├── streaming_session.py      # StreamingSession class (streaming UI state machine)
│   ├── streams.py                # Active stream tracking (crash recovery)
│   ├── telegram_sender.py        # send_file_group, send_rendered, send_rendered_collect
│   ├── telegram_utils.py         # Telegram API helpers
│   ├── transcribe.py             # Voice transcription bridge
│   ├── types.py                  # Shared type definitions (FileAttachment, FileSegment, etc.)
│   ├── utils.py                  # Miscellaneous utilities
│   └── workspaces.py             # Per-chat workspace creation, symlinks
├── commands/                     # Slash command handlers
│   ├── __init__.py               # Package init
│   ├── admin.py                  # /sessions, /restart, /logs, /usage
│   ├── config.py                 # /stream, /verbose, /respond
│   ├── memory.py                 # /memory, /save, /remember, /forget, /history
│   └── utility.py                # /model, /whoami, /files, /clean
├── tests/                        # Test suite (218 tests)
│   ├── conftest.py               # Shared fixtures
│   ├── test_commands.py          # Command handler tests
│   ├── test_commands_memory.py   # Memory command tests
│   ├── test_core_models.py       # Core domain model tests
│   ├── test_core_ports.py        # Core port/protocol tests
│   ├── test_core_repositories.py # Repository implementation tests
│   ├── test_core_use_cases.py    # Use case tests
│   ├── test_permissions.py       # Permission/security tests
│   ├── test_renderer.py          # Renderer tests
│   ├── test_sessions.py          # Session persistence tests
│   ├── test_smoke.py             # Smoke tests
│   ├── test_streaming.py         # Streaming tests
│   ├── test_streaming_session.py # StreamingSession tests
│   └── test_streams.py           # Active stream tracking tests
├── bin/                          # Operational scripts
│   ├── start.sh                  # Start the bot (systemd or nohup)
│   ├── stop.sh                   # Stop the bot
│   ├── restart.sh                # Restart the bot
│   ├── safe-restart.sh           # Graceful restart (waits for streams)
│   ├── setup.sh                  # Interactive setup wizard
│   ├── ouroboros.sh              # Watchdog — auto-restarts dead bot
│   ├── log-cleanup.sh            # Log rotation
│   └── notify-interrupted.sh     # Notify users of interrupted streams
├── guard/                        # Security hooks
│   ├── guard.sh                  # Blocks dangerous Bash commands
│   └── guard-write.sh            # Blocks writes to protected files
├── services/                     # Daemon configs
│   ├── systemd/                  # Linux systemd units
│   │   ├── claude-telegram-bot.service
│   │   ├── ouroboros.service
│   │   └── pinchtab.service      # Pinchtab headless Chrome service
│   └── launchd/                  # macOS launch agents
│       ├── com.claude.telegram-bot.plist
│       └── com.claude.daily-brief.plist
├── skills/                       # Skill scripts
│   ├── telegram-sender/          # Send messages/files via Telegram API
│   ├── ssh-vps/                  # Run commands on VPS via SSH
│   ├── moodle/                   # Moodle LMS integration
│   ├── ai-news/                  # Daily AI news digest (cron)
│   ├── kaggle-compete/           # Kaggle competition helper
│   ├── telegram-lead-monitor/    # Telegram lead monitoring
│   ├── telegram-lead-monitor-ai/ # AI-powered lead monitoring
│   ├── create-skill/             # Skill template & safety guidelines
│   ├── heartbeat/                # Periodic check-in skill
│   └── daily-brief/              # Daily briefing skill
├── workspaces/                   # Claude Code workspaces (per-chat)
│   └── c{chat_id}/               # Each chat's isolated workspace
│       ├── IDENTITY.md            # Per-user identity (created via BOOTSTRAP)
│       ├── USER.md                # Per-user profile (created via BOOTSTRAP)
│       ├── memory/                # Memory (MEMORY.md + t{id}/YYYY-MM-DD/*.md)
│       ├── temp/                  # Ephemeral working artifacts
│       └── uploads/               # Uploaded files (per-topic: t{thread_id}/)
├── .github/
│   └── workflows/
│       └── ci.yml                # GitHub Actions CI (lint + test)
├── .claude/
│   └── settings.json             # Claude Code permissions & hooks
├── telegram-bot.py               # Backward-compatible entry point
├── transcribe.py                 # Voice transcription module (Deepgram)
├── pyproject.toml                # Python package config (replaces requirements.txt)
├── requirements.txt              # Legacy Python dependencies
├── CLAUDE.md                     # Claude's operating instructions
├── IDENTITY.md                   # Agent identity template
├── USER.md                       # User info template
├── TOOLS.md                      # Available tools and environment
├── AGENTS.md                     # Agent delegation rules
├── BOOTSTRAP.md                  # First-run ritual (self-deletes)
├── ARCHITECTURE.md               # This file
├── README.md                     # Project documentation
├── .env.example                  # Environment template
├── .env                          # Environment variables (not in git)
└── .gitignore
```
