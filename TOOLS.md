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
- **Key rules:**
  - User-facing skills source **only `$PWD/.env`** (workspace), never project root `.env`
  - Never hardcode credentials, never exfiltrate user data
  - Never modify system services, guard scripts, or security hooks
  - Validate all inputs, prevent path traversal, use timeouts

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

### moodle
- **Location:** `skills/moodle/run.sh`
- **Purpose:** Log into Innopolis University Moodle via SSO and fetch upcoming deadlines
- **Usage:** `./skills/moodle/run.sh [deadlines|courses]`
- **Commands:**
  - `deadlines` (default) — upcoming assignment deadlines (next 90 days)
  - `courses` — list current semester [S26] courses
  - `lectures [course_id]` — list resources for a course (default: NLP id=3440)
  - `download <resource_id> [outdir]` — download a file; prints saved path to stdout
- **Credentials:** Read from workspace `.env` (`MOODLE_USERNAME`, `MOODLE_PASSWORD`)

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
