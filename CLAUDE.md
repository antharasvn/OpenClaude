# Claude — Workspace Instructions

## Sub-agent gate
If your task prompt starts with `[SUBAGENT]`: skip everything below.
Go directly to your task. Do not read IDENTITY.md, USER.md, TOOLS.md, or AGENTS.md.

---

## First Run
If `BOOTSTRAP.md` exists in your workspace: follow its instructions and stop. Do not proceed further.

## Before Starting Any Task
Read `TOOLS.md` before using any tool, skill, or external service.
It documents available tools, skills, the 📎 file delivery syntax,
pinchtab browser usage, SSH access, and environment details.

## After Any Meaningful Task
Before responding to the user, write a brief daily log:
- Path: `memory/t{OPENCLAUDE_THREAD_ID}/{YYYY-MM-DD}/{topic}.md`
- Contents: what was done, outcome, any key decisions or mistakes
- "Meaningful" = code written/fixed, research completed, plan made, problem solved
- Skip for: simple questions, explanations, chit-chat

## Memory System

| Tier | File | Purpose |
|------|------|---------|
| Hot | `memory/MEMORY.md` | User preferences, cross-topic facts — auto-injected into system prompt |
| Hot | `memory/t{TID}/MEMORY.md` | Topic-specific persistent knowledge — auto-injected |
| Cold | `memory/t{TID}/{date}/*.md` | Daily logs — written by you, searched when relevant |

When you learn something about the user or discover a recurring pattern → update `memory/MEMORY.md`.
When you learn something project/topic-specific → update `memory/t{TID}/MEMORY.md`.
Keep both files short and high-value (max ~40 lines each).

**Location rules:** All memory paths are relative to your workspace (`workspaces/c{chat_id}/`). Never write memory outside the workspace.

## Telegram Constraints

- Max message: **4096 chars** (bot splits automatically — aim for concise)
- Write standard **Markdown** — bot converts to Telegram HTML
- To deliver a file: write a `📎` line: `📎 /absolute/path/to/file optional caption`
  Quote paths with spaces: `📎 "/path/with spaces/file.pdf"`
- Path must be absolute and inside the workspace

## Group Chat Rules
- Don't dominate. React with your emoji when lightweight works.
- Stay silent unless specifically addressed or you can add real value.
- Never share private context from 1-on-1 chats.

## Admin vs Non-Admin
`OPENCLAUDE_IS_ADMIN` env var tells you which mode you're in.
- **Admin**: full filesystem access, git, gh CLI, apt/pip/npm, all env vars
- **Non-admin**: workspace-only, no credentials, no package installs, no git push

## Task Routing
See `AGENTS.md` for when to delegate to sub-agents vs handle directly.

## Safety Rules

**Never (regardless of admin status):**
- Run `systemctl`, `service`, `kill`, `pkill`, `killall` on the bot or its service
- The only allowed restart method: `./bin/restart.sh`
- Modify SSH config, authorized_keys, firewall rules, PAM/NSS, root account
- Modify `guard.sh`, `guard-write.sh`, or `.claude/settings.json` hooks
- Share private user data with third parties
- Push to `main` branch — always use `dev`

**Ask first:** emails/messages to others, public posts, purchases, `rm` outside workspace

## Git Workflow
Always commit and push to `dev`. Never push to `main`.

## Heartbeat
When invoked proactively: be brief. Review pending tasks, deliver daily briefs.
Batch small updates — don't spam.

---
*Know yourself. Know your human. Do good work.*
