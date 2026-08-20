# Skill: heartbeat

## Purpose
Periodic proactive check-in that reviews pending tasks, checks memory for reminders or follow-ups, and sends a brief update via Telegram if anything notable is found.

Designed to run on a schedule (e.g., every 2-4 hours via cron, launchd, or systemd timer) so Claude stays aware of ongoing work without being explicitly prompted.

## What It Does
When invoked, the heartbeat skill will:
1. Read `heartbeat-state.json` to determine when the last heartbeat ran
2. Review memory files (`memory/t0/MEMORY.md` at the repo root, plus today's daily logs) for pending
   tasks, reminders, or items flagged for follow-up. **Not `memory/MEMORY.md`** — that path has never
   existed at the repo root (corrected 2026-08-07 18:1xZ); nothing is auto-injected, so Read it.
3. Check if anything notable has changed or needs attention
4. If there is something worth reporting, send a brief update via the `telegram-sender` skill
5. Update `heartbeat-state.json` with the current timestamp

## State File
`heartbeat-state.json` lives in the project root. Real schema (6 fields), all written by `run.sh`
**except one**:
```json
{
  "last_run":            "2026-08-20T19:28:45Z",   // every invocation, refusal included
  "last_success":        "2026-08-20T19:28:45Z",   // rc==0, or rc==124 with an in-window commit
  "last_refusal":        "2026-08-20T19:07:34Z",
  "last_refusal_reason": "exit 124 with empty output",
  "consecutive_refusals": 0,                        // alerts on 2, re-alerts every 96
  "last_message_sent":   "2026-07-15T00:11:32Z"     // ⛔ DEAD — see below
}
```
⛔ **`last_message_sent` HAS NO WRITER AND NO READER.** `run.sh:23` names it once, in the *seed* line
for a fresh state file, and never touches it again; cycles send through
`./skills/telegram-sender/send.sh`, which does not stamp state. Its live value is **37 days stale**
while cycles messaged the user twice on 08-20 alone. **Do NOT build a send-rate gate on it** — it can
only ever read "silent for weeks", so the gate is unconditionally open. Either stamp it in
`send.sh` first, or use `git log`/`/tmp/claude-heartbeat.log` for send history.

This file is gitignored since it is instance-specific.

## Usage
```bash
# Run directly
./skills/heartbeat/run.sh

# Or via claude CLI
claude -p "Run heartbeat: review pending tasks, check memory for reminders..." \
  --allowedTools Read,Write,Edit,Bash,Glob,Grep,WebFetch,WebSearch,Skill
```

## Schedule
- Recommended: every 2-4 hours during waking hours
- Configure via cron, launchd plist, or systemd timer
- Example crontab entry:
  ```
  0 */3 9-22 * * /path/to/OpenClaude/skills/heartbeat/run.sh
  ```

## Guidelines
- Be brief. Don't send a message just to say "nothing to report."
- Batch small updates into a single message rather than spamming.
- Only send a Telegram message if there is something genuinely useful to share.
- The heartbeat is a background process, not a conversation.
