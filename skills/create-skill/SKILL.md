# Skill: create-skill

## Purpose
Template and safety guidelines for creating new skills.

## How to Create a Skill

1. Create a directory: `skills/<skill-name>/`
2. Add `SKILL.md` — purpose, usage, examples, env vars
3. Add `run.sh` — the executable script
4. Register in `TOOLS.md` under the Skills section

## Skill Template

```bash
#!/usr/bin/env bash
# <skill-name> — <one-line description>
# Usage: ./skills/<skill-name>/run.sh <args>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source workspace .env only (user credentials, not project secrets)
if [[ -f "$PWD/.env" ]]; then
    set -a
    source "$PWD/.env"
    set +a
fi

# --- skill logic here ---
```

## Safety Rules — MANDATORY

### Environment & Credentials
- **Only source `$PWD/.env`** (the user's workspace). Never source the project root `.env` — it contains bot tokens and infrastructure secrets that must not leak to user-facing skills.
- **Exception:** Infrastructure/cron skills (not invoked by users) may source `$PROJECT_DIR/.env` if they need bot-level tokens (e.g., telegram-sender, ai-news). Mark these clearly with a comment.
- **Never hardcode credentials.** Always read from env vars.
- **Never log or echo credentials.** Use `sshpass -e` (not `-p`), env vars over CLI args.

### Data Safety
- **Never read, copy, or exfiltrate user data** from other workspaces, other users' files, or the project `.env`.
- **Never send user data to external services** without explicit user intent (the user must invoke the skill knowing what it does).
- **Never modify files outside the user's workspace** unless the skill's explicit purpose requires it and the user is aware.

### System Safety
- **Never modify system services**, systemd units, SSH config, firewall rules, or the bot process.
- **Never modify guard scripts**, `.claude/settings.json`, or security hooks.
- **Never install system packages** — skills should use what's already available.
- **Never run destructive commands** (`rm -rf /`, `dd`, disk wipes, etc.).

### Input Validation
- **Validate all user inputs.** Filenames, dates, paths — sanitize everything.
- **Prevent path traversal** — reject inputs containing `..`, `/`, or other path separators where a simple name is expected.
- **Use timeouts** for network operations (SSH, curl, API calls).

### Naming & Structure
- Skill directory name should be kebab-case: `my-skill/`
- Always include `SKILL.md` with purpose, usage, examples, and required env vars
- Always include `run.sh` as the entry point (executable, `chmod +x`)
- Keep skills focused — one skill, one purpose
