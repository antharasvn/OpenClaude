# Heartbeat Checklist

## Every Check (runs every 15 min)

### 1. Cron Job Health
- Check `cron/state.json` for jobs with `consecutive_errors >= 3` or `last_status` containing ERROR
- Alert if any enabled job has been failing repeatedly
- **Staleness check (required — the above is blind without it):** for each enabled job, derive the
  **last expected fire time** from `cron/jobs.json` (per-job cron expression + timezone; interval
  jobs use the interval). Alert only if `last_run` predates that slot by a full extra cycle.
  A job dropped by `misfire_grace_time` never runs, never errors, and keeps `last_status: OK`
  forever — `OK` plus staleness is a *broken health signal*, not a healthy job. Resolve schedules
  from `cron/jobs.json` (per-job timezones), never from prior heartbeat prose.
- **Do NOT compare `now - last_run` against a nominal interval** (this checklist said "alert if > 2x
  the interval" until 2026-08-07 00:23Z — it was wrong). Cron jobs with designed overnight gaps fail
  that test every night: `vidnotes-alerts` (`0 7-23/2` Warsaw) is dark 23:00→07:00 Warsaw = 8h = 4x
  its 2h interval, and `cleanpro-alerts` (`0 8-22/2` Saigon) is dark 22:00→08:00 Saigon = 10h = 5x.
  A 2x rule false-alarms 4h and 6h per night respectively. Schedule gaps are not staleness.
- Known open defect (reported 2026-08-07, needs a bot restart = boss's call): `CronTrigger.from_crontab`
  in `bot/scheduler.py` does not remap crontab dow (0=Sun) to APScheduler dow (0=Mon), so every
  weekly job fires one day late. Don't re-report it as new; check `memory/t0/MEMORY.md` first.

### 2. Bot Health
- Check if the Telegram bot process is running: `pgrep -f "python.*-m bot"`
- Check `/tmp/claude-telegram-bot.err` for recent errors (last 5 min)
- Alert if bot is down or throwing repeated errors

### 3. Memory & Reminders
- **Read memory FIRST, before drafting any alert** — otherwise known issues get re-reported as new discoveries
- Read `memory/t0/MEMORY.md` (repo root) for pending tasks or reminders
- Check today's daily logs at `memory/t0/{YYYY-MM-DD}/` for context on what's been done
- **Path warning:** `workspaces/c352342178/memory/` is a STALE duplicate tree. Never read or write it.
  Heartbeat logs go to `memory/t0/{YYYY-MM-DD}/heartbeat-{HHMM}z.md` at the repo root.

### 4. Infra Log Anomalies
- Read last 20 lines of `logs/infra.log`
- Check for repeated `resp=0` or `resp=66` (stuck/failed sessions)
- Check for lock acquisition timeouts

## How to Alert
- Send via telegram-sender skill to chat 352342178 (Boss DM)
- Be brief: problem + what you see + suggested action
- **Only send if something needs attention** — silence means healthy

## What NOT to do
- Don't check disk space, Downloads folder, or calendar
- Don't send "all clear" messages — silence is the signal for healthy
- Don't restart services — only report issues
