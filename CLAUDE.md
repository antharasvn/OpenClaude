# Claude — Workspace Instructions

## General Rules
- **Never use WebFetch** — it hangs indefinitely on many pages. Always fetch URLs via Bash: `curl -sL --max-time 15 "<url>"`

## Sub-agent gate
If your task prompt starts with `[SUBAGENT]`: skip everything below. Go directly to your task. Do not read IDENTITY.md, USER.md, TOOLS.md, or AGENTS.md.

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

| Tier | File | Purpose | Actually injected? |
|------|------|---------|--------------------|
| Hot | `memory/t{TID}/MEMORY.md` | Topic-specific persistent knowledge | **NO — you must Read it explicitly** |
| Cold | `memory/t{TID}/{date}/*.md` | Daily logs — written by you | **Yes, today's only**, in full, by the SessionStart hook |

⛔ **"Auto-injected into system prompt" was WRONG and is corrected here (2026-08-07 18:1xZ).** Both Hot
rows carried that claim, and a third row named `memory/MEMORY.md` — a file that **does not exist at the
repo root**. Verified: `bot/scheduler.py:140-147` `_run_prompt` spawns `claude -p` directly and never
calls `bot/permissions.py`, so **no `append_system_prompt` is built for any cron prompt-job** — no
IDENTITY.md, no USER.md, no MEMORY.md. The `_build_append_system_prompt` machinery at
`permissions.py:75-123` is reached only by the interactive chat path (`backends.py:249`), and it reads
`{cwd}/memory/MEMORY.md`, i.e. the **stale** `workspaces/c352342178/` copy (8.5 KB, last touched
2026-08-04) — never this repo's 36 KB `memory/t0/MEMORY.md`. It also skips topic memory outright for
`thread_id == 0` (`permissions.py:110`).

**Consequence: `memory/t0/MEMORY.md` is write-only unless a prompt explicitly Reads it.** Only
`HEARTBEAT.md` §3 names the correct path. Filing a durable finding there does **not** make the next
day's `vidnotes-alerts` / `cleanpro-weekly` / `weekly-conjecture` run see it — only same-day
propagation works, via the daily-log hook. If a finding must change a job's behaviour, **put it in that
job's `SKILL.md`**, not only in memory. (This is why the Crashlytics false negative recurred 4× while
correctly documented in memory, and only stopped once the recipe was inlined into SKILL.md Step 5.)

When you learn something project/topic-specific → update `memory/t{TID}/MEMORY.md`, and if it must
change a scheduled job, patch that job's `SKILL.md` too. Keep memory files high-value.

**Location rules:** All memory paths are relative to the **repo root** (`bot/scheduler.py` runs every
prompt-job with `cwd=PROJECT_ROOT`), i.e. `memory/t{TID}/…` at the top of this repo. Never write
memory outside the repo.

⛔ **`workspaces/c{chat_id}/memory/` is a STALE duplicate tree — never read or write it.** This line
said "relative to your workspace (`workspaces/c{chat_id}/`)" until 2026-08-07 17:30Z, which
contradicted the injected `[Write daily logs to memory/t0/…]` footer and stranded logs in the dead
tree at random: on 08-07 the vidnotes-alerts runs split 0700et→live, 0900et→dead, 1100et→dead,
1300et→live. HEARTBEAT.md §3 was corrected on 08-07 at 22:52 ICT but this file was not, so only
heartbeat logs were landing correctly.

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
- **Admin**: full filesystem access, git, gh CLI, pip/npm/brew, all env vars
- **Non-admin**: workspace-only, no credentials, no package installs, no git push

## Task Routing
See `AGENTS.md` for when to delegate to sub-agents vs handle directly.

## Safety Rules

**Never (regardless of admin status):**
- Run `kill`, `pkill`, `killall`, or any command that stops/restarts the bot process or its launchd service. You must not stop, restart, or interfere with the `com.claude.telegram-bot` launchd service in any way.
- The only allowed restart method: `./bin/restart.sh`
- Modify SSH access in any way — this includes sshd config, authorized_keys, or the user's macOS keychain credentials
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
