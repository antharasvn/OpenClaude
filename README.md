# OpenClaude

A personal AI assistant that connects Claude Code to Telegram. Send messages on Telegram, get responses powered by the full Claude CLI with tool access (file reading, web search, code execution, and more).

Built in the spirit of [OpenClaw](https://github.com/nicholasgasior/OpenClaw) -- a persistent AI companion with memory, personality, and real tools.

## How It Works

```
You (Telegram) --> bot/ package --> Claude Code SDK --> Response --> You (Telegram)
```

1. You send a message on Telegram
2. The bot connects to Claude via the Claude Code SDK (with subprocess fallback)
3. Claude runs with full tool access (read files, search web, execute code, etc.)
4. Tool progress is shown live, then the response is converted from markdown to Telegram HTML
5. Session IDs are saved so conversations persist across messages

## Architecture

The bot follows a **hexagonal (ports & adapters) architecture** in `bot/core/`:

- **Models** (`core/models.py`) -- domain objects like `UserMessage`, `ChatSession`, `StreamState`
- **Ports** (`core/ports.py`) -- abstract protocols (`AICompletionPort`, `SessionRepository`) that define boundaries
- **Use Cases** (`core/use_cases.py`) -- business logic (`SessionService`, `StreamTrackingService`)
- **Repositories** (`core/repositories.py`) -- concrete implementations: `JsonFile*` for production, `InMemory*` for tests

Key subsystems:

- **Streaming backends** (`backends.py`) -- SDK and subprocess backends for Claude communication
- **StreamingSession** (`streaming_session.py`) -- state machine for live-updating Telegram messages during Claude responses
- **LaTeX rendering** (`latex_render.py`) -- KaTeX rendering via pinchtab headless Chrome; falls back to matplotlib
- **File attachments** (`attachments.py`) -- `📎` marker parsing for sending files back to users
- **Message batching** (`batching.py`) -- groups rapid-fire messages before sending to Claude
- **Restart recovery** (`restart_recovery.py`) -- notifies users of interrupted streams after unexpected restarts

## Features

- **Hexagonal architecture** -- clean separation of domain logic, ports, and adapters in `bot/core/`
- **Streaming live updates** -- Claude's responses stream to Telegram in real time with tool-use indicators
- **LaTeX rendering** -- mathematical expressions rendered via KaTeX (pinchtab headless Chrome) with matplotlib fallback
- **File attachments** -- Claude can send files back to users via `📎` markers (photos, documents, audio, video)
- **Per-user workspace isolation** -- each user gets their own sandboxed workspace at `workspaces/c{chat_id}/`
- **Session continuity** -- conversations persist across messages using Claude's `--resume` flag
- **Full tool access** -- Claude can read/write files, search the web, run shell commands, and more
- **Memory system** -- 3-tier memory: workspace-wide, per-topic, and daily session logs
- **Voice messages** -- voice notes and audio files are transcribed via Deepgram and routed to Claude
- **File and photo handling** -- documents and photos are downloaded and made available to Claude
- **Telegram HTML rendering** -- markdown responses are converted to Telegram-compatible HTML
- **Message splitting** -- long responses are automatically split at paragraph/sentence boundaries
- **User authorization** -- only allowed Telegram user IDs can interact with the bot
- **Telegram sender skill** -- Claude can proactively send messages and files via Telegram
- **Heartbeat & daily briefs** -- scheduled skills for periodic check-ins and morning briefings
- **218 tests** with GitHub Actions CI (lint via ruff + pytest)

## Project Structure

```
OpenClaude/
├── bot/                          # Main bot package (python -m bot)
│   ├── __main__.py               # Entry point
│   ├── app.py                    # Application builder, startup, shutdown
│   ├── attachments.py            # 📎 file marker parsing
│   ├── auth.py                   # Authorization helpers
│   ├── backends.py               # Streaming backends (SDK and subprocess)
│   ├── batching.py               # Message batching logic
│   ├── cache.py                  # FileBackedCache (write-behind disk cache)
│   ├── claude.py                 # Claude integration (thin wrapper)
│   ├── config.py                 # Configuration, constants
│   ├── core/                     # Hexagonal architecture core
│   │   ├── models.py             # UserMessage, ChatSession, StreamState
│   │   ├── ports.py              # AICompletionPort, SessionRepository protocols
│   │   ├── repositories.py       # JsonFile* (prod) + InMemory* (test) repos
│   │   └── use_cases.py          # SessionService, StreamTrackingService
│   ├── events.py                 # Event type definitions
│   ├── exceptions.py             # Custom exception classes
│   ├── formatting.py             # Text formatting utilities
│   ├── handlers.py               # Message handlers, streaming UI
│   ├── latex_render.py           # KaTeX rendering via pinchtab headless Chrome
│   ├── logging_setup.py          # Logger setup
│   ├── media.py                  # Media processing utilities
│   ├── media_handlers.py         # Photo/video/audio/document handlers
│   ├── permissions.py            # Security rules, env building
│   ├── process.py                # Subprocess management
│   ├── prompts.py                # System prompt construction
│   ├── renderer.py               # TelegramRenderer + message splitting
│   ├── restart_recovery.py       # Recovery after unexpected restart
│   ├── routing.py                # Message routing logic
│   ├── sdk_session.py            # SDKSession class, idle cleanup
│   ├── sessions.py               # Session persistence
│   ├── streaming_session.py      # StreamingSession (streaming UI state machine)
│   ├── streams.py                # Active stream tracking
│   ├── telegram_sender.py        # File group sending, rendered message sending
│   ├── telegram_utils.py         # Telegram API helpers
│   ├── transcribe.py             # Voice transcription bridge
│   ├── types.py                  # Shared type definitions
│   ├── utils.py                  # Miscellaneous utilities
│   └── workspaces.py             # Per-chat workspace creation, symlinks
├── commands/                     # Slash command modules
│   ├── admin.py                  # /sessions, /restart, /logs, /usage
│   ├── config.py                 # /stream, /verbose, /respond
│   ├── memory.py                 # /memory, /save, /remember, /forget, /history
│   └── utility.py                # /model, /whoami, /files, /clean
├── tests/                        # Test suite (218 tests)
├── bin/                          # Operational scripts
│   ├── start.sh                  # Start the bot (systemd or nohup)
│   ├── stop.sh / restart.sh      # Stop / restart
│   ├── safe-restart.sh           # Graceful restart (waits for streams)
│   ├── setup.sh                  # Interactive setup wizard
│   └── ouroboros.sh              # Watchdog — auto-restarts dead bot
├── guard/                        # Security hooks
│   ├── guard.sh                  # Blocks dangerous Bash commands
│   └── guard-write.sh            # Blocks writes to protected files
├── services/                     # Daemon configs
│   ├── systemd/                  # claude-telegram-bot, ouroboros, pinchtab
│   └── launchd/                  # macOS launch agents
├── skills/                       # Skill scripts
│   ├── telegram-sender/          # Send messages/files via Telegram API
│   ├── heartbeat/                # Periodic check-in skill
│   ├── daily-brief/              # Daily briefing skill
│   └── ...                       # More skills (ai-news, moodle, ssh-vps, etc.)
├── .github/workflows/ci.yml     # GitHub Actions CI (ruff lint + pytest)
├── pyproject.toml                # Python package config
├── requirements.txt              # Legacy dependency list
├── telegram-bot.py               # Backward-compatible entry point
├── CLAUDE.md                     # Claude's operating instructions
└── .env.example                  # Environment template
```

## Setup

### Prerequisites

- Python 3.11+
- [Claude CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- Your Telegram user ID (from [@userinfobot](https://t.me/userinfobot))

### Quick Setup

Run the interactive setup wizard:

```bash
git clone https://github.com/n4rly-boop/OpenClaude.git
cd OpenClaude
bash bin/setup.sh
```

This will check prerequisites, configure your `.env`, install Python dependencies, and optionally set up daemon services.

### Manual Installation

1. **Clone the repo:**
   ```bash
   git clone https://github.com/n4rly-boop/OpenClaude.git
   cd OpenClaude
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -e .
   ```

3. **Create your `.env` file:**
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

4. **Start the bot:**
   ```bash
   bash bin/start.sh
   ```

### First Run

On first launch, if `BOOTSTRAP.md` exists, Claude will enter bootstrap mode and guide you through:
- Choosing a name and identity for your AI
- Recording your preferences
- Creating the first memory entry

## Running as a Service

### Linux (systemd)

`bin/start.sh` automatically installs and starts the systemd service. To manage manually:

```bash
systemctl --user status claude-telegram-bot
systemctl --user restart claude-telegram-bot
journalctl --user -u claude-telegram-bot -f
```

### macOS (launchd)

Run `bin/setup.sh` and select "yes" for launchd setup, or install manually:

```bash
cp services/launchd/com.claude.telegram-bot.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.claude.telegram-bot.plist
```

### Ouroboros Watchdog

The ouroboros watchdog (`bin/ouroboros.sh`) monitors the bot service and auto-restarts it if it dies. It runs as its own systemd service:

```bash
systemctl --user enable --now ouroboros
```

Configure the check interval via `OUROBOROS_INTERVAL` (default: 30 seconds).

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Show welcome message |
| `/new` | Clear session, start a fresh conversation |
| `/status` | Show your user ID, session info, and bot config |
| `/memory` | Show current memory contents |
| `/save` | Save a note to today's daily log |
| `/remember` | Save a note to long-term memory |
| `/forget` | Ask Claude to remove something from memory |
| `/history` | Summarize recent conversation |
| `/model` | Show or switch the Claude model |
| `/whoami` | Show what the bot knows about you |
| `/files` | List files in your workspace |
| `/clean` | Clean uploaded files |
| `/stream` | Toggle live streaming of Claude's response |
| `/verbose` | Toggle tool usage display |
| `/respond` | Set group response mode (mention/all) |
| `/sessions` | List all active sessions (admin) |
| `/restart` | Graceful bot restart (admin) |
| `/logs` | Show recent infrastructure logs (admin) |
| `/usage` | Show usage statistics (admin) |

### Voice Messages

Send a voice message or audio file on Telegram and the bot will transcribe it via [Deepgram](https://deepgram.com/), then pass the text to Claude. Requires a `DEEPGRAM_API_KEY` in your `.env`:

```env
DEEPGRAM_API_KEY=your-deepgram-key
```

### File and Photo Handling

Send a document or photo on Telegram and the bot will download it to `workspaces/uploads/YYYY-MM-DD/` and tell Claude the file path. Claude can then read, analyze, or process the file using its tools. Add a caption to your file to give Claude context about what you want done with it.

## Security & Permissions

Only users listed in `ALLOWED_USERS` can interact with the bot. The first user in the list is the **admin**.

### What everyone can do

- Read files, search the codebase, browse the web
- Run shell commands (`ls`, `curl`, `python3`, etc.)
- Install packages (`apt`, `pip`, `npm`, `cargo`, etc.)
- Use `git` and `gh` CLI (with their own credentials)
- Use `yt-dlp`, `ffmpeg`, and other installed tools
- Write to memory files

### What everyone is blocked from (enforced by guard hooks)

| Blocked action | Why |
|---|---|
| `systemctl`, `service`, `kill`, `pkill`, `killall` | Prevents killing the bot or other services |
| Modifying SSH config, `authorized_keys`, `/etc/ssh` | Prevents SSH lockout |
| `iptables`, `ufw`, `nftables` | Prevents firewall lockout |
| Bringing down network interfaces | Prevents network lockout |
| Modifying PAM / NSS config | Prevents auth lockout |
| Modifying the `root` user account | Prevents admin lockout |
| Writing to guard scripts or `.claude/settings.json` | Prevents disabling security |

### Additional non-admin restrictions

| Blocked action | Why |
|---|---|
| Reading host env vars (`env`, `printenv`, `/proc/*/environ`) | Prevents credential leaks |
| Reading credential files (`.env`, `.ssh/`, `.aws/`, `.npmrc`, etc.) | Prevents credential leaks |
| `chmod`/`chown` outside their workspace | Workspace isolation |
| `rm -rf` outside their workspace | Workspace isolation |
| Writing/editing files outside their workspace | Workspace isolation |

### Per-user environments

Each user gets an isolated workspace at `workspaces/c{chat_id}/`. Users can have their own `.env` file in their workspace to set credentials (e.g. `GH_TOKEN` for their own GitHub account). Admin inherits the full host environment; non-admin users only get safe system vars plus their workspace `.env`.

## License

MIT
