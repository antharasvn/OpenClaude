# Heartbeat Checklist

## Every Check (runs every 15 min)

### 0. Cycle budget — 600 s of AWAKE time, not 600 s of wall clock (corrected 2026-08-09 02:50 ICT)
The wrapper is `gtimeout 600 claude -p "Run heartbeat: …"` (seen in `ps`), so the cycle is killed at
T+600 s, mid-write, with no chance to save a log. This is the mechanism behind memory §249's
`exit 124` — that entry records the symptom as fixed but never names the cap.
⛔ **"killed at T+600 s" meant wall clock until 2026-08-09 02:50 ICT. It does not.** The same
`CLOCK_MONOTONIC`-freezes-during-sleep mechanism that blinds APScheduler (§1) also freezes this timer.
Measured, n=1: cycle 83477 started 02:31:46, host slept **1007.6 s** mid-cycle, and at `etime`
**18:30 (1110 s wall)** the process was **still alive** on ~102 s of awake time. It was not a deferred
kill either — 600 s of wall had already elapsed at the 02:49:16 wake and nothing fired.
**Two consequences, opposite in sign:**
- Don't abort a cheap observation just because wall clock passed T+10 min — check awake time
  (wall `etime` minus the cum_sleep delta from §1's meter) before believing you are out of budget.
- A heartbeat can now outlive its own 15-min interval in wall time and overlap the next cycle.
  If `ps` shows two `gtimeout 600 claude` processes, that is this, not a hung cycle.
**Still never schedule an observation later than ~T+7 min of awake time.** A slot outside that window
belongs to the NEXT cycle: write the log now and hand it over with the exact commands to resolve it.
The 00:57Z cycle launched a background wait for a 01:05 slot, computed the kill at 01:06:10 against a
01:05:50 return — **~20 s to write a 7 KB log** — and correctly aborted. Losing the log costs more
than any single observation is worth.
Get cycle start from `ps -eo pid,etime,command | grep '[g]timeout 600 claude'`.

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
- **Do this BEFORE the hand-derivation above — dropped slots are NOT silent:**
  `grep "was missed by" /tmp/claude-telegram-bot.err | tail -20`
  APScheduler logs `Run time of job "<name>" was missed by H:MM:SS` for every slot it discards, with a
  timestamp and the job name. **This never appears in `logs/infra.log`** — `bot/logging_setup.py` gives
  `bot.infra` its own handler with `propagate=False`, while `apscheduler.executors.default` goes to the
  ROOT logger → console → launchd's stderr file. That is why cycles up to 2026-08-07 00:41Z believed the
  drops were invisible and rebuilt them by hand from cron expressions + `pmset`. Caveats: (a) the file
  covers the CURRENT bot process only (it starts at process launch; `pgrep`+`ps -o etime` to date it),
  and (b) `coalesce` collapses some consecutive misses, so the warning count is a **lower bound** —
  it reconciled exactly on 08-05 (20 ran + 4 missed = 24) and was one short on 08-06 (18 + 5 = 23).
  Use it to find *which* jobs and *when*; confirm counts against `Running job:` lines in infra.log.
- **The detector LAGS — never use an unchanged `was missed by` count to clear the CURRENT window.**
  APScheduler writes the warning when the executor NEXT evaluates that job, which can be longer than
  one heartbeat interval. On 2026-08-07 05:03Z three slots (vidnotes-daily + vidnotes-alerts 12:00
  ICT, echo-backend-alerts 12:05 ICT) were already irrecoverably dropped while the count sat at 49.
  For "did anything drop just now", check `Running job:` lines + `last_run` against the derived slot.
  Bonus: a host-sleep window is datable from your own Bash calls — a >1 min gap between consecutive
  tool returns is the machine asleep, and it matches the `getUpdates` polling gap in `.err` exactly.
- ⛔ **"The host is awake, so jobs are firing" is FALSE. The scheduler stays blind for as long as the
  host slept, AFTER it wakes** (mechanism confirmed 2026-08-07 22:19Z, n=3, residuals +6 s / −15 s / +9 s).
  APScheduler's main loop waits on `Event.wait(timeout)`, and Darwin's `CLOCK_MONOTONIC` **does not
  advance while the host is asleep** — so a timer armed for T fires at T *plus the cumulative sleep
  since it was armed*, and the 300 s grace then discards every slot in that gap. Worked example from
  08-08 ICT: last evaluation 01:05:00, next armed for 01:54:17, 1892 s of sleep intervened → executor
  next evaluated at **02:25:43** (predicted 02:25:49) and discarded all four slots. The host was fully
  awake and Telegram-polling every 10 s from 01:38:29 onward — **31 min of awake-but-blind.**
  This **corrects `memory/t0/MEMORY.md`'s "slot awake → 0/54 missed (0%)"**: that was measured
  slot-vs-dark-window, which cannot see this. The right question is *"was there sleep between the last
  evaluation and the slot"*, not *"was the slot dark"*.
  **Consequences for this checklist:** (a) never clear a window using host-awake or `getUpdates`
  liveness; (b) the last `Running job:` line is the only proof of evaluation; (c) you can *predict* the
  next evaluation — take the last evaluation, add the armed interval, add cumulative `pmset` sleep since.
- Known open defect (reported 2026-08-07, needs a bot restart = boss's call): `CronTrigger.from_crontab`
  in `bot/scheduler.py` does not remap crontab dow (0=Sun) to APScheduler dow (0=Mon), so every
  weekly job fires one day late. Don't re-report it as new; check `memory/t0/MEMORY.md` first.
- **Runtime and log-presence are only comparable WITHIN a job type** (near-alarm 2026-08-08 09:48Z).
  `cron/jobs.json` gives each job a `type`: `script` jobs run a Python file (`cleanpro-alerts` →
  `scripts/cleanpro_alerts_runner.py`, `cleanpro-exp-monitor`) and finish in **7–31 s** while writing
  **no** daily log; `prompt` jobs spawn `claude -p` (`vidnotes-alerts`) and take **minutes** and do
  write one. Comparing the two reads as "the fast job exits early and reports a false green" — it
  doesn't. Check `type` in `cron/jobs.json` before treating a short duration or a missing log as a fault.
- **Clock-skew sleep meter — use this, NOT `pmset -g log`** (added 2026-08-09 00:37 ICT; `pmset -g log`
  hung twice on 08-08 precisely when the host was sleeping heavily, i.e. exactly when it is needed).
  Darwin's `CLOCK_MONOTONIC` does not advance during sleep, so wall-minus-monotonic *is* cumulative sleep:
  ```
  python3 -c "
  import time, subprocess, re
  boot=int(re.search(r'sec = (\d+)', subprocess.run(['/usr/sbin/sysctl','-n','kern.boottime'],capture_output=True,text=True).stdout).group(1))
  print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), '%.1f'%time.time(), 'cum_sleep %.1f'%(time.time()-boot-time.monotonic()))"
  ```
  (`sysctl` is not on PATH — use `/usr/sbin/sysctl`.) Take it EVERY cycle and record it, so the next
  cycle has an exact baseline instead of eyeballing `pmset` windows. **Paste epoch and ICT verbatim from
  the same call — never retype or approximate either**: the 00:20Z cycle hand-wrote one epoch as
  `…771.x` and mislabelled another probe by 20 min, and the next cycle had to reconstruct both.
- **Predicting the next evaluation:** last `Running job:` time + armed wait + cumulative sleep since.
  ⚠️ **The armed wait is `min(next_run_time)` across ALL jobs — never the watched job's own next slot.**
  APScheduler waits until the *earliest* due job, so an interval job you don't care about sets the wake.
  Getting this wrong makes the model look falsified by hundreds of seconds: on 08-09 the 01:05:00
  evaluation looked armed for echo's 02:05:00, predicting 02:05:00 + 907 s sleep = 02:20:07 against an
  observed 02:09:24 (−643 s). It was armed for the **interval pair's 01:54:17**, and
  `01:54:17 + 907.1 s = 02:09:24.1` vs observed **02:09:24** — residual ≈ **0 s**.
  Confirmed n=7; residuals +6 / −15 / +9 / −6 / ~0 / ~0 / +0.7 s. Derive the arming set from
  `cron/jobs.json` (every job, all timezones) plus the `next run at:` field in the `was missed by`
  warnings. The n=7 case (2026-08-09 03:16:47, predicted 03:16:47.7) was written **two cycles ahead**
  of the tick and named the exact pair of jobs the warning would carry — the model is now precise
  enough to pre-announce which slots die, so state that prediction in the handoff every cycle.
  ⚠️ The 20:08Z cycle derived the arming set correctly for the tick it was watching and then, one
  paragraph later, forecast the *next* arming from cron expressions alone — missing the interval pair
  at 03:54:17 and calling 04:00:00. **Interval jobs have no cron expression; re-read them from
  `cron/jobs.json` every time you forecast an arming, not just the first time.**
- **Keep-awake source is NOT always the display.** Six cycles ran clean on a display-on assertion; the
  00:37 ICT cycle ran clean on transient `dasd` BackgroundTask assertions (Spotlight indexing) with the
  display off. Read `pmset -g assertions` for *which* hold is active before predicting the next slot —
  a `dasd` hold is *sizeable but unbounded*, a display hold is not. And per memory §504, check the
  listed owner: a heartbeat's own `caffeinate` is not host health.
  ⛔ **"a dasd hold is short-lived" was WRONG and is corrected here (2026-08-09 01:52 ICT).** Two
  measured batches ran **~40 min** (00:25→01:05, covered the 01:05 slot clean) and **≥26 min**
  (01:26→01:52, still up at probe). Age the holds in `pmset -g assertions` and treat the release time
  as *unpredictable*, not imminent — you cannot schedule against it in either direction.
- `coalesce=True` is ALREADY in effect (APScheduler 3.11.3 default; verified in `.venv` —
  `job_defaults -> {'misfire_grace_time': 300, 'coalesce': True, 'max_instances': 1}`). Don't propose
  it as a fix; only raising `misfire_grace_time` at `bot/scheduler.py:24` is a real change.

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
- **DATE these before believing them (2026-08-07 13:47Z): both are DEAD.** Last `resp=0` was
  **2026-07-11**, last `resp=66` **2026-05-15**. A `grep -oE "resp=[0-9]+" | tail | uniq -c` shows
  `2 resp=0 / 4 resp=66` and reads as live — it isn't, those are months-old lines near the tail of a
  file with no rotation. Anchor to the `^2026-` timestamp before alerting.
- Check for lock acquisition timeouts (zero lifetime so far; a bare `grep -i lock` on infra.log
  matches `bot was blocked by the user`, which is unrelated)
- ⛔ **Never window infra.log with `awk '$0 >= "<date>"'`** (near-miss 2026-08-07 23:39Z). Traceback
  continuation lines carry no timestamp, and comparing `httpcore.ConnectError:` to a date literal is
  true (`h` > `2`), so months-old tracebacks surface as current — it looked like a live DNS +
  `SchedulerNotRunningError` + BigQuery cluster. Anchor on the line start instead:
  `grep -E "^2026-08-08 0[456]:" logs/infra.log | grep "\[ERROR\]"`. Same rule as `resp=` above:
  date the line before believing it.

## How to Alert
- Send via telegram-sender skill to chat 352342178 (Boss DM)
- Be brief: problem + what you see + suggested action
- **Only send if something needs attention** — silence means healthy

## What NOT to do
- Don't check disk space, Downloads folder, or calendar
- Don't send "all clear" messages — silence is the signal for healthy
- Don't restart services — only report issues
