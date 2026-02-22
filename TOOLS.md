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

## Tool Usage Rules

- **Always use timeouts** for `WebFetch`, `WebSearch`, and `Task` (agents) — they can hang for several minutes and block the bot.
  - `WebSearch` — run via `Bash` with `timeout 30` if you need to limit it
  - `WebFetch` — **has no timeout**, never use directly. Instead: `Bash` + `pinchtab "<url>"` or `curl --max-time 15`
  - `Task` (agents) — always set a reasonable `timeout` in `TaskOutput`
- **pinchtab is the default browser** (`/usr/local/bin/pinchtab`). Use via `Bash`: `pinchtab "<url>"`. Supports JS and page rendering. AppArmor is disabled, Chrome is installed.
  - pinchtab runs as an HTTP API server on `localhost:3000`. Chrome runs separately on port 9222.
  - To get page text: `pinchtab-fetch "<url>"` (wrapper script)
  - API: `POST /navigate`, `GET /text`, `GET /snapshot`, `POST /click`, `POST /type`, `POST /screenshot`

## Skills

### telegram-sender
- **Location:** `skills/telegram-sender/send.sh`
- **Purpose:** Send messages and files to Telegram chats directly
- **Usage:** `send.sh --text "message" --chat CHAT_ID` or `send.sh --file /path/to/file --chat CHAT_ID`

### ssh-vps
- **Location:** `skills/ssh-vps/run.sh`
- **Purpose:** Run commands on the VPS over SSH via sshpass
- **Usage:** `./skills/ssh-vps/run.sh "command"`
- **Examples:**
  ```bash
  ./skills/ssh-vps/run.sh "df -h"
  ./skills/ssh-vps/run.sh "uptime && free -h"
  ./skills/ssh-vps/run.sh "cat /var/log/syslog | tail -50"
  ```
- **Credentials:** Read from the user's workspace `.env` file (`VPS_HOST`, `VPS_PORT`, `VPS_USER`, `VPS_PASSWORD`). Never hardcode credentials.

### daily-brief (planned)
- **Location:** `skills/daily-brief/`
- **Purpose:** Generate and deliver daily briefings

## Environment

### Server
- **OS:** _Not yet documented_
- **Working Directory:** _Set via WORKING_DIR in .env or defaults to project root_

### SSH Hosts
- Configured per-workspace via `.env` files in `workspaces/c{chat_id}/.env`
- Required variables: `VPS_HOST`, `VPS_PORT`, `VPS_USER`, `VPS_PASSWORD`

### API Keys & Services
_None configured yet — document available APIs here as they're added_

### Local Services
_None running yet — document local services (databases, servers, etc.) here_

## Notes
_Add environment-specific notes here as you discover them_
