#!/usr/bin/env bash
# guard.sh — PreToolUse hook that blocks dangerous Bash commands.
# Called by .claude/settings.json before every Bash tool invocation.
# Exit 0 = allow, Exit 2 = block.
set -euo pipefail

# Claude Code passes the tool input in $CLAUDE_TOOL_INPUT; grok passes the whole
# event as JSON on stdin (camelCase .toolInput) and never sets that variable.
# Without the stdin fallback this hook reads an empty string and exits 0, which
# fails open and silently allows every command below.
TOOL_INPUT="${CLAUDE_TOOL_INPUT:-}"
if [ -z "$TOOL_INPUT" ] && [ ! -t 0 ]; then
    TOOL_INPUT=$(jq -c '.toolInput // .tool_input // empty' 2>/dev/null || true)
fi

CMD=$(echo "$TOOL_INPUT" | jq -r '.command // empty' 2>/dev/null || true)
if [ -z "$CMD" ]; then
    exit 0
fi

# Also check Write/Edit tool for protected file paths
FILEPATH=$(echo "$TOOL_INPUT" | jq -r '.file_path // empty' 2>/dev/null || true)

# ── Blocked patterns (everyone) ──────────────────────────────────────

# 1. Service management — don't kill the bot or unload launchd services
if echo "$CMD" | grep -qiE "kill\s|pkill\s|killall\s|claude-telegram-bot"; then
    echo "BLOCKED: You are not allowed to kill processes. Use ./bin/restart.sh for the bot." >&2
    exit 2
fi

# 2. launchd service management — don't unload/remove bot services
if echo "$CMD" | grep -qiE "launchctl\s+(unload|remove|bootout).*com\.claude"; then
    echo "BLOCKED: You are not allowed to disable bot launchd services." >&2
    exit 2
fi

# 3. SSH access — do not touch SSH config or keys
if echo "$CMD" | grep -qiE "sshd|ssh_config|authorized_keys"; then
    echo "BLOCKED: You are not allowed to modify SSH configuration or keys." >&2
    exit 2
fi

# 4. Destructive system commands
if echo "$CMD" | grep -qiE "sudo\s+rm\s+-rf\s+/[^w]|diskutil\s+erase|shutdown|reboot"; then
    echo "BLOCKED: Destructive system commands are not allowed." >&2
    exit 2
fi

# ── Non-admin additional restrictions ────────────────────────────────
if [ "$OPENCLAUDE_IS_ADMIN" != "1" ]; then
    WORKSPACE="${OPENCLAUDE_WORKSPACE:-}"

    # 7. Credential / env var snooping — block attempts to read host credentials
    if echo "$CMD" | grep -qiE "\benv\b|\bprintenv\b|/proc/.*environ|\bset\b\s*$|\bexport\s+-p\b"; then
        echo "BLOCKED: You are not allowed to inspect host environment variables." >&2
        exit 2
    fi
    if echo "$CMD" | grep -qiE "\.config/(gh|git)/|\.claude/\.credentials|\.netrc|\.npmrc|\.pypirc|/etc/shadow|\.ssh/|\.aws/|\.kube/"; then
        echo "BLOCKED: You are not allowed to access credential files." >&2
        exit 2
    fi
    # Block reading the project-level .env (host credentials)
    if echo "$CMD" | grep -qiE "cat.*/OpenClaude/\.env|head.*/OpenClaude/\.env|tail.*/OpenClaude/\.env|less.*/OpenClaude/\.env|more.*/OpenClaude/\.env"; then
        echo "BLOCKED: You are not allowed to read the host .env file." >&2
        exit 2
    fi

    # 9. chmod/chown on files outside workspace
    if [ -n "$WORKSPACE" ]; then
        if echo "$CMD" | grep -qiE "\b(chmod|chown)\b"; then
            # Extract paths from chmod/chown — block if any path is outside workspace
            # Simple heuristic: block if command doesn't reference workspace path
            if ! echo "$CMD" | grep -qF "$WORKSPACE"; then
                echo "BLOCKED: You can only change permissions on files within your workspace." >&2
                exit 2
            fi
        fi

        # 12. rm -rf on paths outside workspace
        if echo "$CMD" | grep -qiE "\brm\s+.*-[a-zA-Z]*r[a-zA-Z]*f|\brm\s+.*-[a-zA-Z]*f[a-zA-Z]*r"; then
            if ! echo "$CMD" | grep -qF "$WORKSPACE"; then
                echo "BLOCKED: You can only delete files within your workspace." >&2
                exit 2
            fi
        fi
    fi
fi

# All clear
exit 0
