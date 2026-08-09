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
⚠️ **Awake-time budget survives a nap; the PROCESS may not — write early and thin if sleep is near**
(2026-08-09 10:47 ICT, n=1). The 03:10:48Z cycle started 10:10:48 ICT, the host slept at **10:13:28**
(2 min 40 s in), woke 10:28:57, slept again 10:29:18 after a 21 s sliver, and the cycle **left no
daily log at all** — no `heartbeat-031*z.md` anywhere, and no surviving process. It had budget to
spare under the awake-time rule above. Cause is not isolated (a `gtimeout` kill and `claude -p` dying
across two suspend/resume cycles are not separable from what is on disk), so treat this as a
reliability floor, not a mechanism: **a cycle beginning within ~3 min of a likely onset should write
its log first and gather second.** Confidence moderate, n=1.
⚠️ **When you hand a checkpoint forward, name the cycle that can actually resolve it — don't assume
"the next one" does.** Cycles start ~15 min apart, so a tick at T+10 min of *this* cycle lands only
~5 min before the next cycle even starts, and can miss it too. Measured 2026-08-09: the 20:28Z cycle
(start 03:26:17) handed the 03:54:17 interval-pair tick to "the next cycle"; that cycle started
**03:44:08** with its `gtimeout` kill at **03:54:08** — short of the tick by **9 s**, so the checkpoint
had to be handed forward a second time. Before writing the handoff, compare the tick against
`next_cycle_start + 600 s` (≈ this cycle's start + ~15 min + 600 s), not against the interval alone.
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
  liveness; (b) `Running job:` proves evaluation but its ABSENCE does not disprove one — see below;
  (c) you can *predict* the
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
  ⛔ **An evaluation that discards every job it finds writes NOTHING to `logs/infra.log`** (measured
  2026-08-09 04:21:36 ICT). `Running job:` is logged by `bot/scheduler.py` only when a job actually
  runs; a slot past `misfire_grace_time` is dropped inside APScheduler, so the sole trace is the
  **timestamp on the `was missed by` warning in `/tmp/claude-telegram-bot.err`**. The n=8 confirmation
  below was nearly recorded as a falsification because the watcher polled
  `grep -c "Running job:" logs/infra.log`, which sat unchanged at 6545 across the predicted instant.
  **Verify a predicted evaluation with `grep "was missed by" …err | tail -1` and read its LEADING
  timestamp — not the count** (§1's detector-lag rule bans the count, and it is the wrong field here
  anyway). Only fall back to `Running job:` when you expect the slot to survive.
  ✅ **The model's POSITIVE branch is now confirmed too — it predicts survivals, not just deaths**
  (2026-08-09 05:05 ICT, n=9). Every prior confirmation predicted a *discard*; this one predicted a
  **clean fire** and got it. Armed at 04:21:36 for `echo-backend-alerts` 05:05:00 ICT, S = 0 s of
  accrued sleep (meter flat at 34510.2–34510.3 across 04:45:05 → 05:05:31), predicted a clean fire
  with **no** warning written — observed `Running job: echo-backend-alerts` at **05:05:00**, completed
  05:05:07, `was missed by` unchanged at 42 with its latest stamp still 04:21:36. Residual **0 s**.
  So a handoff may now assert *"this slot will survive"*, and it is **cheaper to resolve than a
  discard**: a clean fire leaves durable evidence (`Running job:` in `logs/infra.log` + a fresh
  `last_run` in `cron/state.json`), so **any** later cycle can settle it retroactively — no blocking
  watch, and no §0 budget arithmetic about which cycle can reach the tick. Prefer forecasting the
  survival branch for exactly this reason.
  ⚠️ **Compute S from the METER, not from summed `getUpdates` gaps** (n=11, 2026-08-09 08:12 ICT).
  Same tick scored twice: meter S = 1082.9 → predicted 08:12:19.9 vs observed **08:12:20**, residual
  **+0.1 s**; summed gaps (323 + 755 = 1078) → 08:12:15, residual +5 s. The gaps miss short naps —
  the meter rose **16.5 s in 64 s of wall** with no poll gap over 45 s that same cycle — and they
  also carry wake overhead. Poll gaps date an onset; only the meter measures S.
  ⛔ **The gap error is NOT consistently negative — don't treat summed gaps as a safe lower bound**
  (2026-08-09 11:52 ICT). The n=11 wording above ("miss short naps") reads as if gaps undercount; over
  **three** windows they **overcounted by 76.9 s**: gaps 324 + 323 + 974 = **1621 s** against a meter Δ
  of 41197.5 − 39653.4 = **1544.1 s**, ≈ 25.6 s of wake overhead per window. The two error sources
  trade places — missed naps pull negative, per-window wake overhead pulls positive — so the sign
  depends on how many windows you sum. n=2 in each direction. Never substitute gaps for the meter in
  either direction.
  ✅ **Corollary — use the gaps to ORDER a nap against the arming, which turns a range for S into a
  point** (2026-08-09 09:06 ICT). That same 16.5 s nap sat between two meter readings (37471.2 @
  08:12:02, 37487.7 @ 08:13:06) straddling the 08:12:20 evaluation, so the 08:47 cycle had to publish
  **S ∈ [903.0, 919.5]**. The poll cadence dates it: 10–11 s throughout except **08:12:18 → 08:12:42
  (24 s)**. It counts toward S because **a process cannot write a log line at a wall time the host
  slept through** — APScheduler stamped 08:12:20, so the nap starts ≥ 08:12:20 ⇒ meter at arming =
  37471.2 ⇒ **S = 919.5 s**. Cadence at 08:12:07/08:12:18 rules out sleep before it. Generalise: when
  the meter brackets an arming, find the gap, then order it against the arming by any timestamped log
  line — the nap counts only if it falls *after*.
  ✅ **That corollary is now SCORED and it DISCRIMINATED** (2026-08-09 09:25 ICT, n=12, residual
  **−0.5 s**). The two orderings gave different predictions — nap-after ⇒ S = 919.5 ⇒ **09:20:19.5**,
  nap-before ⇒ S = 903.0 ⇒ 09:20:03 — and the observed evaluation was **09:20:19**. The forecast also
  called every field of the warning in advance: one job, `Echo Backend Alerts`, `next run at:
  2026-08-08 23:05:00 EDT`, `missed by 0:15:19` (observed `0:15:19.555906`), count 47 → 48. So a
  bracketing meter no longer forces you to publish a range for S — order the nap and publish a point.
  ⚠️ **Never let a survival forecast extend past the exclusion window that justifies it.** The
  07:29 cycle's forecast of clean fires at 07:54:17 and 08:00:00 was **falsified** — its
  sleep-exclusion primitive expired 07:42:21 and onset came 07:49:13, killing four slots. Forecasting
  the survival branch is still right (§1 above), but past the exclusion window it is *conditional*,
  and must be labelled so. A survival forecast whose reach exceeds its guarantee is a guess.
  ✅ **A falsified CONDITIONAL timestamp is not a falsified model — re-score it with the true S**
  (2026-08-09 11:52 ICT, **n=13**, residual **−0.7 s**). The 11:05:00 slot was published as
  unconditional-discard + conditional-instant 11:26:02.6. The discard was right (and called the job and
  the count, 48 → 49); the instant was **out by +1543 s** because three sleep windows intervened. Meter
  at arming 38390.8, at evaluation 41197.5 ⇒ S = **2806.7** ⇒ `11:05:00 + 2806.7 = 11:51:46.7` vs
  observed **11:51:46**. This is the labelling paying off: publish the discard unconditionally and the
  instant conditionally, and a blown instant costs nothing. Always re-derive S from the meter before
  recording a miss as a falsification.
  ✅ **The retroactive-settlement dividend is now DEMONSTRATED, not just argued** (2026-08-09 15:08
  ICT, **n=14**, residual **0 s**). The 07:50 cycle published an unconditional survival call for
  `echo-backend-alerts` 15:05:00 with four ancillary fields and a kill at 15:00:12 — it could not reach
  its own tick. The next cycle settled all five in two greps off durable evidence: fire at **15:05:00**,
  no warning, count stayed **52**, stamp stayed **14:04:52**, `last_run` `2026-08-09T08:05:06.793400Z`.
  No blocking watch, no §0 arithmetic about which cycle can reach the tick. **Publish the ancillary
  fields (count, latest stamp, `last_run`) with every survival call** — they are what makes it settleable
  by a cycle that never saw the instant. Note the fatal window there was only 2 min 45 s wide *and*
  required a >5 min nap inside it; a survival call is cheap to make confidently once the exclusion
  window covers most of the arming interval.
  Confirmed n=14; residuals +6 / −15 / +9 / −6 / ~0 / ~0 / +0.7 / −0.4 / 0 / 0 / +0.1 / −0.5 / −0.7 / 0 s. The n=10 case
  (2026-08-09 07:36:18, predicted 07:36:18 from armed 07:05:00 + S=1878.0 s across TWO sleep
  windows) also called the exact warning text — one job, `Echo Backend Alerts`, `next run at:
  2026-08-08 21:05:00 EDT`. It is the first tick *blocked on* rather than handed forward, because
  the sleep-exclusion primitive above proved no sleep could intervene. Use that pairing: a fresh
  full-600 s `UserIsActive` tickle turns an `armed + S` forecast into a deterministic in-cycle
  observation, provided the tick also clears §0's awake-time budget. Derive the arming set from
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
  ⚠️ **`powerd`'s "Prevent sleep while display is on" is usually NOT the root hold — sort by age to
  find the real one** (2026-08-09 05:23 ICT). That cycle read four concurrent holds; powerd's was the
  oldest-looking at 37:14, but `AnyDesk` (pid 42666) had held `PreventUserIdleDisplaySleep` for 27:14
  and `coreaudiod` a matching audio hold for 27:10 **created for pid 42666**. Display-on is the
  *effect* of the remote session, so powerd is downstream. This matters for forecasting: a powerd
  hold looks open-ended, but here every hold falls the moment the boss closes AnyDesk, and sleep
  becomes possible within minutes. **Attribute S = 0 to the root owner and bound your prediction by
  that process's life, not by powerd's.**
  ⛔ **That AnyDesk conclusion was WRONG and is corrected here (2026-08-09 05:42 ICT, 19 min later).**
  At the next probe `PreventUserIdleDisplaySleep` was **0** — the AnyDesk and `coreaudiod` rows gone —
  yet **powerd's hold survived and had aged to 55:52**, older than AnyDesk's ever was. A hold that
  outlives the thing it is supposedly downstream of is not downstream of it. Worse, **AnyDesk released
  without exiting** (pid 42666 still alive at `01-08:33:59`), so "bound the prediction by that
  process's life" fails in *both* directions. The real root at that probe was a third process:
  pid 13250 `grok-1.0.0-macos-aarch64`, `NoIdleSleepAssertion` named "grok: agent turn in progress",
  which blocks idle sleep independent of the display — that is why S stayed 0 across the release.
  **Age-sorting finds candidates, not causes.** Confirm a root hold by seeing it outlive another
  hold's release, and treat any unbounded holder (a multi-minute "agent turn in progress", a `dasd`
  batch) as unpredictable in release time — never schedule against it in either direction.
  ⛔ **"a dasd hold is short-lived" was WRONG and is corrected here (2026-08-09 01:52 ICT).** Three
  measured batches ran **~40 min** (00:25→01:05, covered the 01:05 slot clean), **≥26 min**
  (01:26→01:52, still up at probe), and **≥55 min** (02:49:13→03:44:26, still up at probe — new max,
  measured 2026-08-09 03:44 ICT). The spread 26→55+ min shows no characteristic length. Age the holds
  in `pmset -g assertions` and treat the release time as *unpredictable*, not imminent — you cannot
  schedule against it in either direction.
- **Read `pmset -g custom` too — assertions say WHAT holds the host awake, the timers say FOR HOW
  LONG** (added 2026-08-09 06:21 ICT; never read by any prior cycle). Measured on this host:
  `displaysleep 10`, `sleep 1`, identical on AC and Battery. So powerd's "Prevent sleep while display
  is on" — which §1 above calls open-ended — is really a **10-minute countdown re-armed by every HID
  event**, and since `sleep 1` has long expired by then, system sleep follows within ~1 min of the
  display going dark. Date the last HID event from the `UserIsActive` row's age in
  `pmset -g assertions` (or its `Timeout will fire in N secs`), then predict sleep onset at
  last_tickle + ~11 min. What is unbounded is the *user*, not the assertion. This also explains the
  05:42 paradox above: `PreventUserIdleDisplaySleep` can read **0** while powerd's hold stands,
  because powerd tracks the display's *power state*, not the assertion count. Confidence moderate,
  n=0 — the timers are measured, the chain is inferred. Confirm it for free on any cycle that sees
  sleep accrue: the onset is datable to the second from the `getUpdates` polling gap in
  `/tmp/claude-telegram-bot.err`. A later-than-predicted gap means something re-tickled HID and is
  **inconclusive, not a refutation**.
  ✅ **First scoring of that rule — INCONCLUSIVE, as designed, and it yields two refinements**
  (2026-08-09 06:40 ICT). The 06:21 cycle predicted display sleep 06:28:31 / system sleep ~06:29:31
  from a 06:18:31 tickle. Neither happened: meter flat at **34510.3** from 06:21:57 through 06:39:58,
  no `getUpdates` gap. Cause is datable, not speculative — at 06:40:40 `UserIsActive` age was
  **00:06:17**, i.e. HID re-tickled at **06:34:23**. Re-tickle ⇒ inconclusive. Two fixes:
  1. **Don't compute `last_tickle + 10 min` — read the release time off the assertion.** The
     `UserIsActive` row prints `Timeout will fire in N secs`; that N *is* the countdown remainder.
     It also confirms the 600 s length arithmetically at n=2 probes: 06:22:20 → age 229 s + 370 s
     remaining = 599; 06:40:40 → 377 s + 223 s = 600. Matches `displaysleep 10` exactly.
  2. ⛔ **The chain has an unstated precondition: no OTHER idle-sleep hold may be up.** "Display
     sleeps → powerd's hold falls → system sleep within ~1 min" is only valid when powerd's is the
     lone hold. At 06:40:40 `grok-1.0.0-macos-aarch64` (pid **88960**) again held
     `NoIdleSleepAssertion` "grok: agent turn in progress" — a *different pid* from the 13250 seen at
     05:42, so grok re-arms this hold **per agent turn**, and it blocks idle sleep independently of
     the display. Before predicting sleep onset, check `PreventUserIdleSystemSleep` /
     `NoIdleSleepAssertion` for non-powerd owners; if any is up, the onset is **unpredictable** (§1's
     unbounded-holder rule), regardless of what the `UserIsActive` timer says.
  ✅ **Chain CONFIRMED, and refinement #2 is now quantified — a non-powerd hold POSTPONES onset, it
  does not cancel it** (2026-08-09 07:29 ICT, n=1, first sleep after ~9.5 h awake). Predicted from
  the 06:40:40 probe: display timeout **06:44:23** (age 377 s + 223 s remaining), `sleep 1` ⇒ system
  sleep **~06:45:23**. Observed onset **06:49:41–06:49:51** (last `getUpdates` before a 1018 s gap).
  Residual **+258 s**. An HID re-tickle is **excluded arithmetically, not assumed**: a tickle at
  06:38:41 would fit the observed onset but contradicts the 06:40:40 age reading (6:17 ⇒ 06:34:23),
  and any tickle after 06:40:40 pushes onset to ≥ 06:51:40, later than observed. The only surviving
  candidate is the hold refinement #2 named — grok pid 88960 `NoIdleSleepAssertion`, absent by
  07:31:21. **So predict onset as `max(display_timeout + 60 s, the other hold's release)`.** Practical
  consequence: a cycle that sees a fresh full-600 s `UserIsActive` tickle can assert sleep is
  **excluded** for ~11 min and safely watch a tick in that window — that is a real scheduling
  primitive, and it is the *negative* direction (proving sleep can't happen) that is reliable, since
  the positive direction still depends on an unbounded holder.
  ✅ **Exclusion primitive now n=2; the positive direction scored INCONCLUSIVE a second time**
  (2026-08-09 08:10 ICT). From the 07:31:21 full-600 s tickle: predicted display timeout 07:41:21,
  system sleep ~07:42:21; observed onset **07:49:13**, residual **+412 s**. With no intermediate
  probe an HID re-tickle cannot be excluded arithmetically, so it is inconclusive — but sleep *was*
  excluded through 07:42:21 as promised. **Take a probe mid-window if you want the positive branch
  to be scoreable at all**; without one, only the exclusion half survives. `runningboardd`'s
  `osservice<…CFNetwork.StorageDB>` hold falls under the bluetoothd rule below — age 00:00:00, not blocking.
  ✅ **n=3 INCONCLUSIVE — but the postponement is ATTRIBUTED for the first time, via a new free test:
  powerd's hold age is a display-on stopwatch** (2026-08-09 08:49 ICT). Predicted from the 08:29:16
  probe: display timeout 08:39:10, system sleep ~08:40:10. Observed: **no sleep at all** — meter flat
  at **38390.7** across 08:29:37 / 08:47:37 / 08:49:34, and no `getUpdates` gap since 08:28:34.
  The n=2 case had to be filed as unattributable ("no intermediate probe exists, so an HID re-tickle
  cannot be excluded"). **That gap is now closable retroactively, with no intermediate probe:**
  powerd's `PreventUserIdleSystemSleep` "Prevent sleep while display is on" is created when the
  display turns on and released when it sleeps, so **its age is how long the display has been on.**
  Here it read `00:18:02` @ 08:48:08 and `00:19:28` @ 08:49:34 — both resolving to creation
  **08:30:06**, same assertion id `0x000179aa000187c4`, i.e. one continuous hold. **19.5 min of
  display-on against a 600 s `displaysleep` countdown, with `PreventUserIdleDisplaySleep` = 0 at both
  probes, means the countdown was re-armed by HID — proof, not inference.** Live confirmation in the
  same probe: the `UserIsActive` row kept its id `0x0001797200098727` while its device flipped
  `Logi K580 Keyboard` (age 4 s, 596 secs left) → `Logi M650 L` (age 0 s, 600 secs left).
  **So: read powerd's hold age on ANY later cycle; `age > 600 s` retroactively proves a re-tickle and
  converts an unexplained no-onset from "unattributable" to "inconclusive, cause identified."**
  ⚠️ Two caveats, both measured here: (a) **compare assertion IDs, not just ages** — the previous
  cycle read powerd at age 00:00:06 @ 08:29:16 (creation 08:29:10), a *different* hold from the
  08:30:06 one, so powerd churns its hold briefly around wake and the stopwatch resets with it;
  (b) the alternative to a re-tickle is a transient `PreventUserIdleDisplaySleep` holder (the AnyDesk
  case above) that has since released — a single probe cannot separate the two, but both are
  postponements, so the *inconclusive* verdict is unchanged either way. Confidence moderate, n=1.
  ✅ **Caveat (b) IS separable when you have repeated probes — first clean split 2026-08-09 09:44 ICT.**
  powerd's hold `[0x000179aa000187c4]` ran one continuous 75 min (creation 08:30:06, same id at the
  08:48 / 08:49 / 09:08 / 09:26 / 09:45 probes). AnyDesk (pid 42666) re-created its
  `PreventUserIdleDisplaySleep` at **09:32:46** — *strictly inside* that window — so the segment splits:
  **08:30:06 → 09:32:46 had `PreventUserIdleDisplaySleep` observed 0 at three separate probes**, which
  excludes the transient-holder branch by direct observation and makes that segment **re-tickle,
  proved**; only from 09:32:46 is a holder responsible. **Generalise: sample the assertion COUNT every
  cycle, not just powerd's age** — a count of 0 at a probe retroactively rules out the holder branch for
  the span up to it, converting "inconclusive, cause identified" into an attributed re-tickle.
  ⚠️ **Don't mistake `InternalPreventDisplaySleep` / `com.apple.powermanagement.delayDisplayOff` for
  the display countdown** (first seen 2026-08-09 09:26 ICT). powerd holds it with its own short fuse —
  observed age 00:04:39, `Timeout will fire in 21 secs Action=TimeoutActionTurnOff` — in the *same*
  probe where the `UserIsActive` row read **569 secs left**. The countdown remainder still comes off
  the `UserIsActive` row only.
  ✅ **The "21 s vs 569 s" is arithmetic, not a paradox — it is a 300 s re-armed fuse** (2026-08-09
  09:44 ICT, n=2). Age + remaining sums to the same constant at both probes: 09:26:29 id
  `0x000184bd00108c65` 279 s + 21 s = **300**; 09:45:31 id `0x00018abe00108c65` 106 s + 193 s = **299**.
  Different ids ⇒ powerd churns the hold, as it does around wake. So it is a second, *shorter* clock
  running alongside the 600 s `displaysleep` countdown, and the two probes merely caught it at
  different phases. Still unexplained: why a 300 s `TimeoutActionTurnOff` exists alongside the 600 s
  one and never fires — it is evidently re-armed by the same HID events. Confidence moderate, n=2.
  ✅ **Resolved — it fires fine; earlier probes just always had HID re-arming it** (2026-08-09 10:08
  ICT, n=3 on the constant: 10:05:42 id `0x00018f6500108c65`, 173 s + 126 s = **299**). That probe was
  the first with `UserIsActive` = **0**, so nothing was left to re-arm it: predicted expiry 10:07:48,
  and at two independent probes (10:08:24, 10:08:36) the hold was **gone**, meter flat at 38390.8
  across it. Bounded to (10:05:42, 10:08:24] — consistent with 10:07:48, not resolved to the second.
  **Its expiry turns the display off and does NOT touch system sleep**, so it is never the thing that
  kills a slot. ⚠️ **Gotcha: `pmset` prints the `InternalPreventDisplaySleep` status row only while the
  hold is up — when it expires the row leaves the block entirely rather than reading 0.** A cycle
  grepping for `InternalPreventDisplaySleep *0` finds nothing and cannot distinguish "expired" from
  "never sampled"; test for the row's *presence*.
  ⛔ **"Its expiry turns the display off" is too strong — the `TimeoutActionTurnOff` is GATED on
  `PreventUserIdleDisplaySleep` = 0** (2026-08-09 11:09 ICT, n=1). Probed at 11:07:39: id
  `0x0001985a00108c65`, age 293 s, **7 secs** remaining ⇒ due ~11:07:46. At 11:09:23 a **different**
  id `0x000199f700108c65`, creation 11:08:58 (25 s + 274 s = 299 — the 300 s constant now n=4). Across
  that span powerd's display-on hold kept **one unchanged id**, so the display never turned off, and
  AnyDesk's `PreventUserIdleDisplaySleep` was up throughout. The 10:08 case fired visibly precisely
  because that count was **0** there. Caveat: a 72 s hole (11:07:46 → 11:08:58) has no probe, so
  "reached 0" vs "released early" is unseparable — but no display-off occurred on either branch.
  Operationally unchanged: still never touches system sleep, so still never kills a slot.
- ⛔ **The sleep-exclusion primitive is UNAVAILABLE when `UserIsActive` = 0 — check for it before
  leaning on any survival forecast** (2026-08-09 10:05 ICT). The n=2/n=3 exclusion cases both had a
  fresh full-600 s tickle to lean on. This configuration is the opposite and reads:
  `UserIsActive` **0**, `PreventUserIdleDisplaySleep` **0**, and powerd's display-on stopwatch
  (§1's re-tickle instrument) **absent from the owner list**. Its absence *is* the measurement — the
  display is already off, so the 600 s countdown has expired rather than been re-armed, and there is
  **no exclusion window at all**. When that happens the chain collapses to
  **`onset = the remaining unbounded hold's release + ~60 s`** (`sleep 1`), which §1's unbounded-holder
  rule makes unpredictable in *both* directions. Here the sole remaining hold was `pid 13250`
  `grok-1.0.0-macos-aarch64` `NoIdleSleepAssertion` "grok: agent turn in progress" — id
  `0x0001884400018bd5`, creation **09:32:24** derived identically at three probes. **So the whole cron
  scheduler's survival can rest on one unrelated process's assertion.** A forecast made in this state
  must be labelled *conditional on that hold*, never asserted. Discount `ExternalMedia` as always (§1).
  ✅ **That state was SCORED and it behaved exactly as labelled — plus the first measured length for a
  grok hold: ~40 min** (2026-08-09 10:47 ICT). Onset came **10:13:28**, 4 min 52 s after the 10:08:36
  probe; back out `sleep 1` ⇒ grok released ~**10:12:28**, so the hold created 09:32:24 ran **~40 min**
  — same order as the `dasd` batches (26 / 40 / 55+ min), so still no characteristic length across
  holder types. The *state* was diagnosed correctly and the *timing* was correctly called
  unpredictable; this is the first time the no-exclusion-window state was named in advance and then
  validated by a real onset, which is also the negative-space proof that the exclusion window is what
  had been protecting the 09:54 / 10:00 / 10:05 slots (all three fired clean, then sleep).
  ⛔ **Generalise the release pattern: grok releases its per-turn hold WITHOUT exiting** — pid 13250
  still alive at `01-05:03:35` with no assertion. Identical to the AnyDesk case above. Two independent
  holders now share this shape, so **"bound the prediction by the holder process's life" is wrong by
  default**, not as a quirk — never use process liveness as a proxy for an assertion still being held;
  read the assertion.
  ⚠️ **An AnyDesk session arms TWO holds, and only the display one has ever been tracked here**
  (2026-08-09 11:07 ICT). Observed pair: pid 42666 `AnyDesk` `PreventUserIdleDisplaySleep` created
  10:39:58, **and** pid 672 `coreaudiod` `PreventUserIdleSystemSleep`
  (`…BuiltInHeadphoneOutputDevice…preventuseridlesleep`, **`Created for PID: 42666`**) created
  10:40:02. The second blocks idle **system** sleep independently of the display, so sleep stays
  excluded even after the `UserIsActive` 600 s countdown lapses and the display chain would otherwise
  fire. This is §1's unbounded-holder case pointing the *helpful* way — it grants no guarantee (§1:
  AnyDesk releases without exiting), so a forecast leaning on it is **conditional**, but a cycle that
  sees only the `UserIsActive` row will badly **under**estimate the exclusion window. Always read the
  `Created for PID:` line: a `coreaudiod` audio hold is usually a proxy for some other process.
  ⚠️ Do **not** count `bluetoothd`'s `com.apple.BTStack` `PreventUserIdleSystemSleep` as a blocking
  hold. It reads age 00:00:00 and toggles continuously; it was present and demonstrably did not stop
  the 06:49:41 onset. Only holds with a real age qualify. Same for `ExternalMedia` — powerd has held
  `com.apple.powermanagement.externalmediamounted` for **36:54:21** across every sleep today, so a
  long age alone does not make a hold sleep-blocking; only the idle-sleep assertion types count.
  ⚠️ A wake in the `getUpdates` gap is not necessarily a *usable* wake: 06:49:41→07:22:11 is **two**
  windows separated by a **20-second** dark wake at 07:06:39, far too short for the executor to
  evaluate. Count sleep from the meter (Δ 1878.0 s), not from one gap.
- ✅ **To decide whether a stale job is the KNOWN misfire or a SECOND bug, reconcile expected slots
  against `was missed by` warnings inside the bot process's lifetime** (2026-08-09 11:52 ICT). A job
  reading `last_status: OK` + `ce=0` while weeks stale (§326's silent-failure mode) does not say
  *which* fault it is. Method: `ps -o lstart -p $(pgrep -f "python.*-m bot")` to date the process
  (the `.err` file starts there, §1 caveat (a)), enumerate the slots each stale job owed since then
  from `cron/jobs.json`, and count its warnings via
  `grep "was missed by" /tmp/claude-telegram-bot.err | sed -E 's/.*job "([^(]*)\(.*/\1/' | sort | uniq -c`.
  Worked example — the six-job reporting blackout: process up since 08-07 19:54, owed slots CleanPro
  Daily 2 + VidNotes Daily 1 + the 14:00 quad 1 each = **7**, observed warnings **7**, zero
  unexplained ⇒ entirely the `CLOCK_MONOTONIC` misfire mechanism, no second fault. **A shortfall is
  the interesting result** — it means slots were never evaluated at all, which is a different bug.
  Mind `coalesce` (below): the count is a lower bound, so reconcile per job, not in aggregate, and
  treat an exact match as strong evidence rather than proof.
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
