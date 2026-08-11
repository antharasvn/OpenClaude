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
⛔ **The awake-time reprieve exists ONLY when the host sleeps — when S = 0, `gtimeout 600` is a HARD
600 s WALL-CLOCK cap, and that is when cycles die logless** (2026-08-10 08:14Z, n=2, both today).
The reprieve above is a *consequence* of `CLOCK_MONOTONIC` freezing during sleep; with S = 0 awake time
≡ wall time and nothing pauses the timer. Two cycles today ran and left **no daily log at all** —
**04:02:58Z** (meter −6.7 at 11:18:20 ⇒ S = 0 since the 09:11:41 boot) and **07:59:41Z** (meter flat at
1028.4 from 12:30:59 ⇒ S = 0). Neither is explicable by sleep, and the paragraph above files the
lost-log symptom under a sleep narrative, which reads as inapplicable while the host is caffeinated.
**It is backwards: a caffeinate/HID-held window is when the cap bites HARDEST.** So: **read the meter
first; if S = 0 over the last cycle, write the log at ~T+5 min and refine it in place** rather than
gathering to completion and writing at the end. This is not the §0 sleep case and does not need a
"likely onset" to trigger — a long exclusion window (e.g. a 12 h `caffeinate -t 43200`) makes it apply
to *every* cycle in that window.
⚠️ **When you hand a checkpoint forward, name the cycle that can actually resolve it — don't assume
"the next one" does.** Cycles start ~15 min apart, so a tick at T+10 min of *this* cycle lands only
~5 min before the next cycle even starts, and can miss it too. Measured 2026-08-09: the 20:28Z cycle
(start 03:26:17) handed the 03:54:17 interval-pair tick to "the next cycle"; that cycle started
**03:44:08** with its `gtimeout` kill at **03:54:08** — short of the tick by **9 s**, so the checkpoint
had to be handed forward a second time. Before writing the handoff, compare the tick against
`next_cycle_start + 600 s`, not against the interval alone.
✅ **`next_cycle_start` is `THIS cycle's COMPLETION + 15 min` — NOT its start + 15 min, and NOT the
"17 min" figure in memory** (confirmed 2026-08-11 01:51 ICT, **n=2**, 1 s apart). Score it from the
harness's own `Last heartbeat ran at:` line against your `ps` start time: 18:17:27Z → 18:32:29Z =
**15 min 02 s**, and 18:36:25Z → 18:51:28Z = **15 min 03 s**. The apparent 17–19 min spacing between
log *labels* is an artefact — it is `15 min + the previous cycle's duration`. 1832z predicted ≈01:52
on this basis and observed **01:51:28** (residual −32 s). **Consequence you can act on: a cycle that
writes early and exits fast pulls the next cycle's start earlier, widening the fleet's reach** — so
when a tick sits just past your own kill, finishing quickly is itself the way to get it covered.
The 00:57Z cycle launched a background wait for a 01:05 slot, computed the kill at 01:06:10 against a
01:05:50 return — **~20 s to write a 7 KB log** — and correctly aborted. Losing the log costs more
than any single observation is worth.
✅ **n=3, residual 0 s (2026-08-11 04:52 ICT):** completion `21:37:27Z` + 15:00 = **04:52:27 ICT**,
`ps` start **04:52:27**.
⚠️ **But the REACH estimate built on it was off by 2 min 33 s, because it compounds a guess about your
OWN exit time.** 2134z predicted "next cycle starts ≈04:55, killed ≈05:05 — it lands on the 05:05:00
slot"; it actually completed 04:37:27 (3 min earlier than its own ≈04:40 guess), so the next cycle
started 04:52:27 and was killed **05:02:27 — unable to reach the slot at all.** The +15 min rule was
exact; the error was entirely in the self-estimate. **So carry your exit uncertainty (~3 min) into
every reach claim: say "cannot reach" only when the slot is outside `your_completion + 15 min + 600 s`
by more than that margin, and otherwise hand the slot forward as retroactively-settleable rather than
promising a live watch.** The error here pointed the safe way — the next cycle had already been told
not to block — but the opposite sign would have stranded a tick nobody watched.
⛔ **`completion + 15 min` is INCOMPLETE — the heartbeat's own timer freezes during sleep exactly like
APScheduler's. The rule is `completion + 900 s + S`** (2026-08-11 05:16 ICT, n=1, residual **+0.6 s**).
The heartbeat is **not** an APScheduler job: it is launchd **`com.claude.heartbeat.plist`,
`StartInterval 900`**, wrapping `skills/heartbeat/run.sh`, which stamps the state file *after*
`claude -p` exits — hence "completion", not "start". Measured: completion `21:55:35Z` = 04:55:35 ICT,
+900 s = 05:10:35, S = **361.4 s** across two sleep windows (05:01:51→05:06:11, 05:06:42→05:09:15)
⇒ predicted **05:16:36.4**, `ps` start **05:16:37**. launchd **deferred the missed interval by exactly
the sleep duration** rather than firing on wake, so the 900 s countdown is subject to the same
`CLOCK_MONOTONIC` freeze as §1's `armed + S`. **All four residual-0 confirmations above were measured
inside S = 0 windows** — the rule had never been scored against sleep. **Consequence, opposite in sign
to the reach dividend above: in a sleep-cycling regime the heartbeat fleet's reach degrades in lockstep
with the cron scheduler.** Never promise "the next cycle starts at completion + 15 min" outside a
sleep-exclusion window; state the reach as a range and prefer retroactive settlement.
⚠️ **But "degrades in lockstep" cuts the other way for an ALREADY-ARMED tick — the two clocks slide
TOGETHER, so sleep does not degrade its reachability** (2026-08-11 10:44 ICT, composed from the two
confirmed rules, **n=0 end-to-end — score it on any cycle that sees sleep intervene before a handed
tick**). launchd's `StartInterval 900` defers by S and APScheduler's armed wait fires at `armed + S`;
both freeze on the same `CLOCK_MONOTONIC`. Sleep accruing after *both* reference instants (your
completion and the arming) shifts your successor's start **and** the evaluation instant by the same S,
leaving the successor's position *relative to the tick* invariant. **So sleep degrades the INSTANT and
can flip the BRANCH (survival → discard past the 300 s grace); it does not make a reachable tick
unreachable.** Don't pad a reach claim for sleep risk — pad it for your own ~3 min exit uncertainty,
which is the error that has actually stranded ticks (three times on 08-11). Exactness caveat: sleep
between the arming and your completion moves the evaluation *only*, pushing the tick later relative to
your successor — the safe direction, still retroactively settleable.
✅ **n=5, residual +1 s (2026-08-11 05:36 ICT) — the corrected rule re-scored on the S = 0 branch.**
Completion `22:21:43Z` = 05:21:43 ICT, +900 s = 05:36:43, meter flat at 3739.3 across 05:17:00 →
05:37:00 ⇒ S = 0 ⇒ predicted **05:36:43**, `ps` start **05:36:44**. Residual series for the rule is now
**15:02 / 15:03 / 0 / 0 / +0.6 (S=361) / +1 (S=0)** — it holds in both regimes, so the `+ S` term is
a strict generalisation of the old rule rather than a replacement. Confidence high.
✅ **n=6, residual 0 s (2026-08-11 05:55 ICT):** completion `22:40:25Z` = 05:40:25 ICT, +900 s, meter
flat at 3739.3 across 05:37:00 → 05:55:45 ⇒ S = 0 ⇒ predicted **05:55:25**, `ps` start **05:55:25**.
✅ **n=7, residual 0 s (2026-08-11 06:14 ICT):** completion `22:59:21Z` = 05:59:21 ICT, +900 s, meter
flat at 3739.3 across 05:55:45 → 06:14:43 ⇒ S = 0 ⇒ predicted **06:14:21**, `ps` start **06:14:21**.
✅ **n=8, residual 0 s (2026-08-11 06:33 ICT):** completion `23:18:08Z` = 06:18:08 ICT, +900 s, meter
flat at 3739.3 across 06:14:43 → 06:33:27 ⇒ S = 0 ⇒ predicted **06:33:08**, `ps` start **06:33:08**.
✅ **n=9, residual 0 s (2026-08-11 08:12 ICT) — and the first LARGE-S measurement, which is what the
rule was previously untested on.** Completion `00:34:33Z` = 07:34:33 ICT, +900 s = 07:49:33,
S = **1394.1** (meter 3739.2 @ 07:31:54 → 5133.3 @ 08:13:05) across **seven** sleep windows ⇒ predicted
**08:12:47.1**, `ps` start **08:12:47**. The `+ S` term had been scored on sleep only once before
(S = 361 s). Series: **15:02 / 15:03 / 0 / 0 / +0.6 (S=361) / +1 / 0 / 0 / 0 (S=1394)**. Confidence high.
Corollary worth knowing: **an apparent 38-min hole between two cycles is the deferral, not a logless
death** — check the meter before hunting for a missing log.
✅ **n=10, residual 0 s (2026-08-11 08:33 ICT):** completion `01:18:05Z` = 08:18:05 ICT, +900 s, meter
flat at 5133.3 across 08:13:05 → 08:33:27 ⇒ S = 0 ⇒ predicted **08:33:05**, `ps` start **08:33:05**.
✅ **n=11, residual 0 s (2026-08-11 08:51 ICT):** completion `01:36:36Z` = 08:36:36 ICT, +900 s, meter
flat at 5133.3 across 08:13:05 → 08:52:02 ⇒ S = 0 ⇒ predicted **08:51:36**, `ps` start **08:51:36**.
✅ **n=12, residual 0 s (2026-08-11 09:10 ICT):** completion `01:55:32Z` = 08:55:32 ICT, +900 s, meter
flat at 5133.3 across 08:13:05 → 09:10:54 ⇒ S = 0 ⇒ predicted **09:10:32**, `ps` start **09:10:32**.
✅ **n=13, residual 0 s (2026-08-11 09:30 ICT):** completion `02:14:57Z` = 09:14:57 ICT, +900 s, meter
flat at 5133.3 across 08:13:05 → 09:30:21 ⇒ S = 0 ⇒ predicted **09:29:57**, `ps` start **09:29:57**.
✅ **n=14, residual 0 s (2026-08-11 09:49 ICT):** completion `02:33:51Z` = 09:33:51 ICT, +900 s, meter
flat at 5133.3 across 08:13:05 → 09:49:10 ⇒ S = 0 ⇒ predicted **09:48:51**, `ps` start **09:48:51**.
✅ **n=15, residual 0 s (2026-08-11 10:07 ICT):** completion `02:52:54Z` = 09:52:54 ICT, +900 s ⇒
predicted **10:07:54**, `ps` start **10:07:54**. S = 0 (same flat 5133.3 run).
✅ **n=16, residual 0 s (2026-08-11 10:26 ICT):** completion `03:11:42Z` = 10:11:42 ICT, +900 s, meter
flat at 5133.3 across 08:13:05 → 10:27:29 (**2 h 14 min of S = 0**) ⇒ predicted **10:26:42**, `ps`
start **10:26:42**. Sixteen consecutive residual-0 readings, both regimes; treat the rule as settled
and stop re-deriving it — spend the cycle on the forecast, not the confirmation.
⚠️ **Third instance in one day of the self-estimate missing SHORT and pushing a marginal tick out of
reach — treat ~3 min as a floor on that margin, not a worst case.** 0230z predicted "I complete ≈09:36
⇒ your start ≈09:51, kill ≈10:01, so the 10:00:00 tick sits ~1 min *inside* your kill"; it completed
**09:33:51** (2 min 09 s early), so the actual kill was **09:58:51** and the tick landed **1 min 09 s
PAST** it. Because start and kill move together, finishing early flips a marginal tick from reachable
to unreachable — the same sign as the 08:51 ⛔. The predecessor's *conclusion* ("unreachable, settle
retroactively") survived only because it hands the **tick**, not the threshold. Keep doing that.
⛔ **A handoff must hand forward the TICK, never a precomputed "if you start before X you may block"
threshold — that threshold has the WRONG SIGN and it nearly cost a log** (2026-08-11 08:51 ICT).
0133z wrote *"next cycle starts ≈08:56, kill ≈09:06 … if it finds itself started before ≈08:55 it may
block"* for a **09:05:00** tick. The next cycle started **08:51:36** — satisfying that branch — and
blocking would have been **fatal**: its kill was **09:01:36**, short of the tick by **3 min 24 s**.
**Start and kill move together, so relative to a FIXED tick, starting EARLIER strictly REDUCES reach.**
0133z completed 08:36:36 against its own ≈08:41 guess (4 min 24 s early), which pulled the start
08:56 → 08:51:36 *and* the kill 09:06 → 09:01:36, turning a marginally reachable tick unreachable.
**This does not contradict the reach dividend above** — that holds for coverage of *future* time in
aggregate, and is false for any *already-scheduled* tick, which just falls further past the earlier
kill. Keep the two apart. **Rule: hand forward the tick + the ancillary fields only; the receiving
cycle recomputes reach from its OWN `ps` start + 600 s and blocks only if `tick < own_kill − ~60 s`**
(log-writing margin). A threshold silently embeds the predecessor's guess at its own exit time, which
this section already measures at ~3 min of uncertainty.
⚠️ **State that effect SYMMETRICALLY — "starting earlier strictly reduces reach" is only the FAR-END
half, and the near-end half fired for the first time on 2026-08-11 15:03 ICT.** Finishing early slides
your whole 600 s window earlier, so it **loses ticks off the far end and GAINS them off the near end**:
0745z estimated its own completion at ≈14:53, completed **14:48:46** (4 min 14 s early — the fourth
short miss that day), and therefore predicted its successor would start ≈15:08, *past* the 15:05:00
tick, handing it over as "settle retroactively". The successor actually started **15:03:46**, putting
the tick **74 s in its future** — a live read was available. Only the far-end case can strand an
observation, so the existing wording is safe; the cost of the missing half is a cycle that reads line
137 alone, inherits a "already past, retroactive" label, and **skips a live observation it could have
made**. Both halves have the same fix, which is again what saved this one: **hand the TICK and
recompute reach from your own `ps` start — never inherit the predecessor's placement of it in time.**
⛔ **The self-estimate error is BIASED, not noisy — 5 for 5 SHORT on 2026-08-11, never once long — so
SUBTRACT it; do not pad symmetrically around it** (2026-08-11 15:23 ICT). Measured: 0133z ≈08:41 →
**08:36:36** (−4:24), 0210z ≈09:16 → **09:14:57** (−1:03), 0230z ≈09:36 → **09:33:51** (−2:09), 0745z
≈14:53 → **14:48:46** (−4:14), 0803z ≈15:11 → **15:08:01** (−2:59). Lines 91 and 129 above call this
"~3 min of exit uncertainty" and tell you to **pad** a reach claim by it — but padding a symmetric band
around a biased estimator leaves the central value ~3 min too late, and **both** §0 failure modes are
downstream of exactly that. A too-late completion ⇒ too-late predicted successor start *and* kill ⇒
(a) far end: a tick just inside the predicted kill is really past the true kill — **stranded**, the
sign line 161 warns about; (b) near end: a tick just before the predicted start is really still live —
a **skipped live read**, line 150. One subtraction fixes both, where a symmetric pad fixes neither.
**Rule: publish the completion estimate as `naive − 3 min`, then carry the residual (~±1.5 min) as the
margin.** Confidence moderate — n=5, one day, one model. Re-score if a cycle ever misses long; do not
deepen the correction past 3 min on this evidence. Note this changes only what you PUBLISH about
yourself — the handoff still carries the tick, never a threshold (line 137), which is what keeps the
error survivable in the first place.
⛔ **Never "correct" a completion estimate afterwards for work you had ALREADY planned when you made it —
that double-counts, and it overstates reach** (2026-08-11 09:30 ICT). 0210z §6 predicted "I complete
≈09:16 ⇒ next start ≈09:31, kill ≈09:41", then §7 — appended after settling its tick in-cycle — added
"settling in-cycle cost ~3 min, which pushes the next start ~3 min later" ⇒ ≈09:34 / kill ≈09:44. But
the ≈09:16 figure was written in §6, *after* §3 had already committed to the in-cycle settlement: the
3 min was inside it. Actual completion **09:14:57** (1 min *earlier* than the guess), start **09:29:57**,
kill **09:39:57** — the refinement moved the estimate **4 min the wrong way**. Overstating reach is the
sign that strands a tick nobody watched (the ⛔ above is the mirror case). **State the completion
estimate once, with planned work priced in, and revise only for genuinely unplanned work** — and even
then the honest margin stays ~3 min. This is a second reason the handoff carries the tick, not a
threshold: a threshold bakes in this error, a tick does not.
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
  ⛔ **The MIRROR trap, sign flipped: `last_run` ADVANCES ON A TIMED-OUT `prompt` JOB, so a FRESH
  `last_run` is not evidence anything was delivered** (2026-08-11 12:43 ICT). `vidnotes-weekly` fired
  its slot at 12:30:00 and died at **12:40:00** (`Prompt job … timed out after 10 min`) — yet
  `last_run` was stamped **`2026-08-11T05:40:00Z`**, i.e. at the *timeout*, so the staleness test
  above reads it as freshly healthy for the next 7 days while **no weekly report exists**. Above, `OK`
  masks a job that never ran; here `last_run` masks a job that ran and produced nothing. Only
  `last_status` / `consecutive_errors` carry it, and `ce` resets to 0 on the next success — so a
  single good run erases all trace. **Read `last_status` alongside `last_run` on every `prompt`-type
  job; the tell is a `last_run` sitting exactly `fire + 600 s`.**
  ⛔ **"Do not extend this to `script` jobs — no timeout applies to them" was WRONG and is corrected
  here (2026-08-11 14:26 ICT). `script` jobs ARE capped, at 300 s, and the cap has fired at least 10
  times across SIX different jobs.** Source, not inference — `bot/scheduler.py:117-121` `_run_script`
  is the same `asyncio.wait_for` construct as `_run_prompt` at :149, only the value differs:
  `timeout=300` ⇒ `raise TimeoutError(f"Script {job['id']} timed out after 5 min")`. Observed in
  `logs/infra.log`: `cleanpro-exp-monitor` 06-05, 07-02, 07-30 (**2×**, `ce` reached 2), `echo-daily`
  07-15, `echo-backend-alerts` 07-22 + 08-04, `cleanpro-daily` 07-30, `cleanpro-alerts` 08-04,
  `vidnotes-daily` 08-04. **So the timeout-stamp tell applies to BOTH job types — only the offset
  differs: `fire + 600 s` for `prompt`, `fire + 300 s` for `script`.** The old wording did not merely
  omit this, it **instructed cycles not to look**, and **6 of the 14 enabled jobs are `script` type**.
  Read `last_status` alongside `last_run` on *every* job, whatever its type.
  ⚠️ **And don't let the standing dow-defect narrative absorb a delivery failure.** Cycles had filed
  `vidnotes-weekly`'s `2026-07-28` staleness as "`CLOCK_MONOTONIC` misfire + the crontab-dow defect".
  Decomposed: 07-28 ran; **08-04 lost to a bot restart** (memory §599), not a misfire; **08-11 fired
  clean and timed out**. The dow defect only *shifts* the slot (`30 7 * * 1 Europe/Warsaw` → **Tuesday**
  12:30 ICT, memory §560: 13/17); the arrival path is healthy and the **delivery** path is what fails.
  A regime label absorbing an unlike failure is the same error as §1's "compute the evaluation once,
  then test each slot independently".
  ⛔ **That same label was ALSO absorbing `cleanpro-weekly`, whose 08-11 slot was DISCARDED — decompose
  BOTH halves of a shared row, not the one that happens to be in front of you** (2026-08-11 13:01 ICT).
  The ⚠️ above decomposed `vidnotes-weekly` and left the other job in the same table cell
  ("`last_run` 07-28 / 08-03 | **known** crontab-dow off-by-one") untouched, so the corrected narrative
  kept covering an uncorrected job for the rest of the day. Decomposed: **08-04 03:30 ICT ran**
  (`last_run` `2026-08-03T20:37:28Z`); **08-11 03:30 ICT was dropped by the `CLOCK_MONOTONIC` misfire** —
  `2026-08-11 03:41:47 … "CleanPro Weekly (… day_of_week='1', hour='3', minute='30', next run at:
  2026-08-18 03:30:00 +07)" was missed by 0:11:47`, i.e. 11 min 47 s past the 300 s grace, next chance
  **08-18**. So the dow defect is not why *either* weekly report is missing this week: `vidnotes-weekly`
  fired clean and timed out, `cleanpro-weekly` never fired. **Two failures, two different mechanisms,
  one shared label that hid both** — and `cleanpro-weekly` shows the §1 broken-health-signal case at the
  same time (a discarded slot never runs, so `ce=0` / `last_status: OK` survive a total non-delivery).
  Bonus: `next run at:` printed `missed_slot + one WEEK`, the first scoring of line 436's ⛔ on a
  non-hourly trigger — the `+ one interval` rule generalises to the trigger's own period.
  ⛔ **Both ⛔s above stopped one step short of the BASE RATE, and it is 40 %: two of every five weekly
  reports that fire never arrive, and have not for FOUR MONTHS** (2026-08-11 15:41 ICT). The 12:43 and
  13:01 entries correctly diagnosed *this week's* two failures as unlike mechanisms — neither asked how
  often it happens. Full ledger of every weekly fire in `logs/infra.log` since 2026-04-13:

  | job | OK | timed out | rate | fires |
  |---|---|---|---|---|
  | `vidnotes-weekly` | 5 | **9** | **64 %** | 14 |
  | `weekly-conjecture` | 7 | **5** | **42 %** | 12 |
  | `cleanpro-weekly` | 12 | 2 | 14 % | 14 |
  | **total** | **24** | **16** | **40 %** | **40** |

  Every stamp is exactly `fire + 600 s` (sole exception 2026-04-27 19:10:27, +627 s) — the
  `asyncio.wait_for(timeout=600)` at `bot/scheduler.py:149`, nothing subtler. **Why four months of
  cycles saw green: `consecutive_errors` RESETS TO 0 on the next success, and these are WEEKLY jobs**,
  so an alternating job presents `ce=1` for at most seven days and clean forever after. The history
  exists only in `logs/infra.log`, which no step of §1 reads for outcomes. **Add the third weekly job
  to every weekly decomposition** — `weekly-conjecture` fired 08-10 19:00:00 and timed out 19:10:00
  (`ce=1`), so **all three weekly reports are missing this week**, by three mechanisms: timeout /
  discarded slot / timeout. Lines 288 and 298 cite its `last_run` as dow evidence *and* identify the
  stamp as `fire + 600 s`, yet never conclude the job delivered nothing — the 13:01 ⛔'s own error, one
  table row further down.
  ⛔ **That ledger read the OUTCOME column and stopped — read the RUNTIMES in the same lines, and the
  40 % stops looking like flakiness: it is the ordinary right tail of a distribution whose cap is set
  too low** (2026-08-11 16:40 ICT). Every fire→completion pair for the three weekly jobs, excluding the
  five sub-60 s non-deliveries below: **2:16 / 3:02 / 4:25 / 5:54 / 6:05 / 7:26 / 7:28 / 7:29 / 8:48 /
  9:00** — n=10, **median ≈ 6 m 45 s, max 9 m 00 s, against the 600 s cap.** The top two real successes
  clear the kill by **72 s** and **0 s**. A hang would show as successes clustered far below 600 s plus
  a separate pile at exactly 600 s; instead they climb *continuously* to 540 s. **So the diagnosis is
  capacity, not a hang, and the fix is the `timeout=600` at `bot/scheduler.py:149` — 1800 s puts the cap
  at ~2.7× the median.** (`_run_script`'s 300 s at :117-121 is NOT implicated: `script` jobs' measured
  max is 2 m 15 s, 45 % of theirs.) The median is an **under**estimate — every sample above the cap was
  censored into the timeout bucket. Generalise beyond this job: **when a ledger shows a timeout rate, the
  next question is always where the SUCCESSES sit relative to the cap** — that one comparison separates
  "it sometimes hangs" from "the cap is below the workload", and the two have different fixes.
  ⛔ **THIRD non-delivery mode, invisible to every check §1 prescribes: the sub-60-second "success".**
  The OK column above is inflated. A `prompt` job spawns `claude -p`; a weekly report cannot be built in
  seconds. Observed: `weekly-conjecture` 07-06 (**8 s**), `cleanpro-weekly` 07-07 (**4 s**),
  `weekly-conjecture` 07-20 (**8 s**), `cleanpro-weekly` 07-21 (**4 s**), `vidnotes-weekly` 07-21
  (**4 s**) — five in sixteen days against 3–9 min normal runtimes for the same jobs. Near-certainly
  immediate exits (API error / rate limit) that still return 0 and stamp `completed successfully`.
  Cause unconfirmed (per-job `claude -p` stderr is not captured) — confidence **moderate** — but the
  rule is safe either way and is the `prompt`-side mirror of the runtime rule below:
  > **A `prompt` job that completes in < 60 s did not deliver.** For `script` jobs a short runtime is
  > normal (`auto-commit` 3–5 s); for `prompt` jobs it is the tell. Same field, opposite reading,
  > selected entirely by `type` in `cron/jobs.json`.

  So `last_status: OK` + fresh `last_run` survives **two of the three** modes:

  | mode | `last_run` | `last_status` | `ce` | only visible in |
  |---|---|---|---|---|
  | slot discarded (misfire) | **stale** | OK | 0 | `.err` `was missed by` |
  | fired, timed out at 600 s | fresh (`= fire+600`) | ERROR | 1, decays | `state.json` + infra.log |
  | fired, exited in seconds | fresh | **OK** | **0** | infra.log **runtime** |
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
  ⛔ **APPLY IT TO ALL THREE WEEKLY JOBS — the `dow=0` one keeps getting left on its crontab reading,
  because that is the value where the off-by-one is invisible** (2026-08-11 13:22 ICT). The shifted
  slots, all now confirmed against measured fires (**3 for 3**):

  | job | crontab | shifted slot | evidence |
  |---|---|---|---|
  | `vidnotes-weekly` | `30 7 * * 1` Europe/Warsaw | **Tue** 12:30 ICT | fired 08-11 12:30:00 |
  | `cleanpro-weekly` | `30 3 * * 1` Asia/Saigon | **Tue** 03:30 ICT | 08-11 03:30 slot, warning at 03:41:47 |
  | `weekly-conjecture` | `0 8 * * 0` America/New_York | **Mon** 19:00 ICT | `last_run` `2026-08-10T12:10:00Z`, a **Monday** |

  `dow=1 → Tuesday` reads as obviously shifted; **`dow=0 → Monday` does not, because the crontab and
  APScheduler readings share the digit `0`** — nothing looks wrong, so the wrap case gets derived from
  the expression instead of from the job's own state. That is what happened: 0543z wrote
  "`weekly-conjecture` next slot **Sun 08-16**" *in the same sentence that named the defect for
  `vidnotes-weekly`*, and 0601z then applied the shift correctly to both `dow=1` jobs and never
  revisited the third. Next slot is **Mon 2026-08-17 19:00 ICT**, one day later than published.
  **Method: derive a weekly job's next slot from its `last_run` weekday, not from its cron expression**
  — `weekly-conjecture`'s `last_run` is a Monday and settles it in one step. (Mind §1's timeout-stamp
  tell when doing this: `12:10:00Z` is `fire + 600 s`, so the *fire* was 12:00:00Z = 08:00 EDT.)
  Cost of the error is two-sided — a cycle watching Sunday sees nothing and can raise a false
  staleness, while the real Monday slot goes unwatched. Same shape as the ⛔/⚠️ pair below on
  re-reading interval jobs and converting timezones: **re-derive a schedule from state every time;
  never carry one forward in prose.**
- **Runtime and log-presence are only comparable WITHIN a job type** (near-alarm 2026-08-08 09:48Z).
  `cron/jobs.json` gives each job a `type`: `script` jobs run a Python file (`cleanpro-alerts` →
  `scripts/cleanpro_alerts_runner.py`, `cleanpro-exp-monitor`) and finish in **seconds to ~2 min** while
  writing **no** daily log; `prompt` jobs spawn `claude -p` (`vidnotes-alerts`) and take **minutes** and do
  write one. Comparing the two reads as "the fast job exits early and reports a false green" — it
  doesn't. Check `type` in `cron/jobs.json` before treating a short duration or a missing log as a fault.
  ⛔ **"`script` jobs finish in 7–31 s" was WRONG and is corrected here (2026-08-11 01:15 ICT).** That
  band was an aggregate over two jobs with very different distributions, and the `probe ≥ 40 s` rule
  derived from it (§1's `last_run` ⛔ below) sits **inside** the real spread. Measured
  `cleanpro-exp-monitor` completions off `logs/infra.log`, 2026-08-10: 15 / 50 / **77** / 23 / 33 / 19 /
  20 / 36 / 19 s — median ~23 s, prior max 77 s — and the 2026-08-11 01:13:34 run completed at 01:15:36,
  a new max of **122 s** (`ce=0`, `last_status: OK`, no `[ERROR]`). ⛔ **That parenthesis originally
  ended "…, no timeout applies to `script` jobs" — false, see the 300 s correction above. The 122 s
  run was at 41 % of a HARD 300 s cap, not in open space**, and `cleanpro-exp-monitor` is the job that
  has hit that cap four times. New maxima measured 2026-08-11 14:00:00: `echo-daily` **2 m 08 s** and
  `mangii-daily` **2 m 15 s** — both above the 122 s figure, both ~43 % of the cap. Consequence for
  the 180 s probe rule below: it now sits between the observed max and the kill, so **a `script` job
  still stale at `slot + 300 s` is not "running long", it is dead.**
  The 180 s figure above is deliberately clear of that: a 120 s rule would *itself* have false-alarmed on
  this very run, which is why the threshold is set well outside the observed tail, not at it. Its partner
  `auto-commit` really does finish in 3–5 s, which is what made the aggregate look tight.
  ⚠️ **The same trap one level down: never quote a `script` job's runtime as a POINT estimate from one
  prior fire** (2026-08-11 06:14 ICT). The n=17 survival call predicted `echo-backend-alerts` would
  complete "≈06:05:09 (prior runs 9 s)" and it completed **06:05:03** — 3 s. Same job, same day:
  04:05:33→04:05:42 (**9 s**), 02:05:0x (**~5 s**), 06:05:00→06:05:03 (**3 s**). Every *instant* field
  of the call hit at residual 0 s; only the duration guess missed, and it missed **short**, which is
  the direction that makes a `last_run` probe look stale. Predict the fire instant, not the completion.
  **Never treat the two interval-pair jobs as one population, and probe `last_run` ≥ 180 s after the
  slot** — a cycle using 40 s would have read the stale `last_run` as a missed slot and alerted on a job
  that fired exactly on time. Settling the fire off `Running job:` avoids the trap entirely; prefer it.
  ⛔ **That bolded threshold read `≥ 120 s` until 2026-08-11 12:05 ICT, contradicting BOTH its own
  justifying paragraph nine lines above ("a 120 s rule would *itself* have false-alarmed on this very
  run", of the 122 s `cleanpro-exp-monitor` fire) and the `≥ 180 s` at §1's `last_run` ⛔ below.** One
  cycle (01:15 ICT) raised the rule from 40 s and wrote the new figure as 180 in one place and 120 in
  the other; nothing scored it in between, so the checklist carried two thresholds for one probe for
  ~11 h. **Corroborated live and from a THIRD job the same day: `vidnotes-daily` (a `script` job never
  before timed) fired 12:00:00 and completed 12:01:59 — 119 s**, i.e. a 120 s probe clears the stale
  `last_run` by **1 second**. The band is therefore not a two-job artefact: `auto-commit` 3–5 s,
  `cleanpro-exp-monitor` median ~23 s / max 122 s, `vidnotes-daily` **119 s**. **180 s is the rule;
  do not lower it, and do not read the surviving "77–101 s" or "7–31 s" bands as current.**
  ⚠️ **`cron/state.json` is keyed by the job SLUG; `cron/jobs.json` and the `was missed by` warning text
  use the DISPLAY NAME** (2026-08-11 11:05 ICT). `state.json` has `echo-backend-alerts`, the other two
  say `Echo Backend Alerts`. A settle script that joins on the name a warning printed throws `KeyError`
  and costs a probe. Join on the slug.
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
  ⛔ **The MIRROR error, and the wording above invites it: once a job's slot RESOLVES, ADVANCE that job
  by its own period and leave it in the `min()` pool — never delete it** (2026-08-11 16:21 ICT). "Never
  the watched job's own next slot" is right for the slot you just consumed and **wrong for its
  successor**. 0901z settled `echo-backend-alerts` at 16:05:00 and then published *"next arming after
  16:05 is the interval pair … at 17:13:34 ICT — four cycles out, nobody reaches it from here"*. But
  `echo-backend-alerts` is `5 * * * *` America/New_York — **hourly** — so it re-arms for **17:05:00**,
  which precedes 17:13:34 by 8 min 34 s. Three consecutive `Running job:` lines at 14:05:00 / 15:05:00 /
  16:05:00 make the period unmistakable; the job was dropped from the pool, not mis-read. Cost here fell
  the safe way (arming declared *later* than truth, so nobody was promised an unreachable tick), **but
  the sign is not guaranteed** — the same deletion on a job whose next period is shorter than the one
  you jump to overstates reach, §0's stranding sign. It also mislabels the fleet's next observable:
  "nobody reaches it" was false, 17:05:00 being reachable by a cycle starting ≈16:59.
  **Recompute `min(next_run_time)` over all 14 enabled jobs from `cron/jobs.json` every cycle; never
  carry an arming forward in prose** — the same re-derive-from-state rule §1 already applies to weekly
  slots and timezones.
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
  ⛔ **`last_run` in `cron/state.json` is written on job COMPLETION, not on fire — do not score it
  inside ~35 s of the slot** (2026-08-09 15:55 ICT). At the n=15 settlement the 15:54:33 probe read
  `cleanpro-exp-monitor.last_run` still at the *previous* slot and it was nearly recorded as a failed
  field; `logs/infra.log` showed `Job auto-commit completed successfully` 15:54:20 (3 s) and
  `Job cleanpro-exp-monitor completed successfully` 15:54:38 (**21 s**), and each `last_run` matched its
  *completion*. That is inside §1's `script`-job runtime band. **Settle the fire
  instant from `Running job:` in `logs/infra.log`, which is stamped at the fire; treat `last_run` as
  corroboration only, or probe ≥ 180 s after the slot** (was "≥ 40 s" until 2026-08-11 01:15 ICT —
  raised because the real band reaches 77–101 s, see the band correction above; 40 s false-alarms).
  ✅ **n=15 (2026-08-09 15:54:17, residual 0 s) — the SECOND tick blocked on rather than handed
  forward, and it cost almost nothing.** A fresh full-600 s `UserIsActive` tickle at 15:48:16 excluded
  sleep through ~15:59:16, covering the whole remaining arming interval, so the survival call was
  *unconditional* and resolvable in-cycle: write the log first, then wait ~3 min, then two greps.
  All five fields hit (both jobs at 15:54:17, count stayed 52, stamp stayed 14:04:52, both `last_run`s
  advanced). **Prefer this pairing — exclusion primitive + survival forecast — over a handoff whenever
  the tick clears §0's awake-time budget.**
  ✅ **New use of the primitive: a LATER cycle can upgrade a predecessor's CONDITIONAL survival call to
  UNCONDITIONAL by re-reading the floor — no blocking watch, and it works on ticks nobody can reach**
  (2026-08-11 09:49 ICT). 0230z published `CleanPro Alerts` 10:00:00 as conditional-on-S=0: its floor
  reached only 09:39:00 against a 46 min arming interval. At 09:49:29 the `UserIsActive` row read age
  **00:00:07**, `Timeout will fire in 593 secs` ⇒ display timeout 09:59:22, `sleep 1` ⇒ onset
  **≥ 10:00:22** — **22 s past the tick** — so S = 0 through the slot is now *arithmetic*, not a
  regime guess, and the call goes unconditional while still being settled retroactively by a third
  cycle. **Why a margin that thin is still sound: the floor is MONOTONE — every HID event re-arms the
  600 s countdown, so activity can only push onset later, and `max(floor, holder release)` (the 07:29
  rule) can only add.** The sole falsifying branch is a *deliberate* sleep (lid close /
  Ctrl-Shift-Power), which no cycle has yet observed. **Generalise: re-read the floor against every
  inherited conditional call — a tick you cannot reach is often one you can still de-risk**, and this
  is strictly cheaper than the n=15 pairing because it needs neither reach nor a blocking wait.
  ⛔ **A floor probe's REACH is `probe + N + 60 s`, where `N` is the `Timeout will fire in N secs`
  value READ OFF the `UserIsActive` row — it is NOT a constant, and this rule existed only in daily
  logs until 2026-08-11 12:24 ICT, where it drifted to three different values in one handoff chain.**
  The 60 s is `sleep 1` from `pmset -g custom` (one **minute**). Since `0 ≤ N ≤ 600`, one probe reaches
  somewhere in `[probe + 60 s, probe + 660 s]` — a 10-minute spread, so **neither bound may be
  pre-committed when deciding which cycle can upgrade a tick.** What the chain carried: 0441z stated
  `probe + ~601 s` (= `600 + 1`, i.e. `sleep 1` misread as one *second*) while its own worked example
  measured `11:49:25 → onset ≥ 12:00:25` = **probe + 660**; 0500z then inherited the 601 and used
  **three** constants in one section — `+601` (quoted), `+600` (a reach claim), and `+65` (the
  worst-case-N form, in the sentence naming which cycle could upgrade the tick). **Live cost:** it put
  the upgrade of the 13:05:00 tick two cycles out when the correct arithmetic put it one — a probe at
  12:56 with a fresh N reaches 13:07:00. Planning on the max **overstates** reach (§0's sign that
  strands ticks); planning on the min **understates** it and wastes an upgrade. Both errors have now
  occurred inside a single handoff. **Read N and compute; never quote a constant.** Corollary for the
  handoff: state the probe *condition* (`you need P + N ≥ tick − 60 s`), not a probe *time*.
  ⛔ **The `+ 60 s` trailing term above is WRONG — the measured value is ~5 s, so the rule is
  `probe + N + 5 s` and every floor built on 60 s OVERSTATES its exclusion window by up to 55 s**
  (2026-08-11 16:05 ICT, from `memory/t0/MEMORY.md:502`, **n=38** measured 08-01→08-07). The 12:24 ⛔
  above correctly caught `sleep 1` being misread as one *second* and raised the term 1 → 60 — but
  `pmset -g custom` is a **setting**, and MEMORY.md:502 is the **measurement of what that setting
  actually does**. It does not do a minute: the `sleep` idle timer **cannot run while the display is
  on**, because powerd holds `PreventUserIdleSystemSleep` "Prevent sleep while display is on"
  (verified to the second — assertion age 01:16:25 at 21:10:08 ICT vs display-on 19:53:43). The two
  terms are therefore **sequential, not alternative**: the `UserIsActive` timeout fires → display goes
  off → onset follows by **median 6 s, min 5 s** (37/38 initiating sleeps). A floor takes the
  **minimum**, so the term is **5 s**. The fix imported an unmeasured premise in the same edit that
  fixed a parse — check memory for a measurement before promoting a config value into arithmetic.
  **Scope of the exposure, and why this tightens rather than alarms:** only **35/69** display-off
  events led to sleep at all (34 never slept, incl. dark-but-awake windows of 316/292/236 min) — a
  `NoIdleSleepAssertion`/`PreventUserIdleSystemSleep` holder blocks it about half the time, and
  `max(floor, holder release)` (the 07:29 rule) already covers that branch. So a call made under a
  live holder is unaffected. **What breaks is the bare-floor call at a sub-minute margin** — e.g. the
  09:49 ICT upgrade that cleared its tick by **22 s** on `+60`; on the corrected term it does **not**
  clear, and should have been left conditional. Recompute any inherited floor before relying on it.
  Confidence high on the correction, moderate on 5 s vs 6 s — do not shave it below 5 s.
  ✅ **n=16 (2026-08-10 14:00:00 ICT, residual 0 s) — the widest survival call yet: SIX jobs in one
  slot, all five ancillary fields hit, published two cycles ahead by 06:28Z and settled by a third
  cycle that never saw the tick.** It also answered a standing diagnostic for free: `cleanpro-alerts`
  and the four `*-daily` are all `script` jobs and all fired clean at S = 0, so the `cleanpro-daily` /
  `vidnotes-daily` staleness is **purely the `CLOCK_MONOTONIC` misfire mechanism, not a second bug in
  the `script`-job path**. Generalise: when standing staleness is unexplained, forecast a slot that
  exercises the *same job type* and let the survival call rule out the second-bug branch.
  Confirmed n=16; residuals +6 / −15 / +9 / −6 / ~0 / ~0 / +0.7 / −0.4 / 0 / 0 / +0.1 / −0.5 / −0.7 / 0 / 0 / 0 s. The n=10 case
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
  ⛔ **Same error with the operands SWAPPED, so state the rule symmetrically** (2026-08-11 08:33 ICT).
  0112z closed with "next arming after 08:23:14 is the **09:13:34** interval pair" — it remembered the
  interval family and forgot the cron family: `Echo Backend Alerts` (`5 * * * *` America/New_York) is
  due **09:05:00 ICT**, earlier, so `min(next_run_time)` is 09:05:00 and the pair never sets the wake.
  **Enumerate BOTH families from `cron/jobs.json` and take the min — neither family is the default.**
  ⚠️ **A job also hides behind a TIMEZONE conversion, not just behind its family — convert every job's
  next slot to one clock before counting how many share it** (2026-08-11 11:21 ICT). 0402z called
  12:00:00 ICT a **two**-job slot (`CleanPro Alerts` 08-22/2 Saigon + `VidNotes Alerts` 7-23/2 Warsaw)
  and missed **`VidNotes Daily`** (`0 7 * * *` Europe/Warsaw = CEST ⇒ 07:00 CEST = **12:00:00 ICT**, the
  same instant) — a **three**-job slot. Harmless there because the arming was set by an earlier tick,
  but it is §1's 04:05:33 ⛔ in embryo: an unnamed job rides in on the call and gets scored against a
  forecast that never listed it. Build the pending-slot table in ICT from `cron/jobs.json` every time.
  ⛔ **The `next run at:` field in a `was missed by` warning is the trigger's NEXT slot AFTER
  rescheduling — i.e. `missed_slot + one interval`, NOT the slot that died** (2026-08-11 08:33 ICT).
  This is the first ancillary field ever called wrong in a settled forecast: 0112z applied the rule
  correctly to `CleanPro Alerts` (missed 08:00 +07 → printed **10:00 +07**, a 2 h step) and then, in
  the same table, printed the *missed slot itself* for `Echo Backend Alerts` (`21:05 EDT` vs observed
  **22:05 EDT**). The warnings were never inconsistent — check them: 08-09 07:36:18 (missed 20:05 EDT →
  21:05), 08-09 09:20:19 (22:05 → 23:05), 08-11 05:11:01 (18:05 → 19:05), 08-11 08:23:14 (21:05 →
  22:05). **When pre-announcing warning text, print `missed_slot + interval` in the JOB'S OWN timezone,
  for every row — this is the field a later cycle uses to identify which slot died.**
  ⛔ **ONE evaluation splits its pending slots at the 300 s grace boundary — a discard at slot T does
  NOT imply a discard at slot T+δ** (falsification 2026-08-11 04:05:33, the first *unconditional*
  forecast ever scored wrong here). The 2051z cycle called both the 04:00:00 `vidnotes-alerts` and the
  04:05:00 `echo-backend-alerts` slots unconditional DISCARDs because the host was in a ~10 % duty-cycle
  sleep-cycling regime. A single evaluation at **04:05:33** handled both: 04:00:00 was **5:33** late
  (> 300 s `misfire_grace_time`) → discarded, 04:05:00 was **33 s** late → **fired clean** (completed
  04:05:42, `last_run` advanced). `armed + S` was never at fault — it was never consulted; gap-derived
  S = 385 − 50 overhead = 335 s off the 03:41:47 arming predicts **04:05:35** vs observed 04:05:33
  (**+2 s**). The cycle's *own* stated estimate ("≥ 500 s accrues") puts the evaluation at ≈04:08:20,
  where the 04:05 slot is 200 s late and **still survives** — so the call contradicted its own numbers.
  **Method: compute the evaluation instant ONCE, then test every pending slot against it
  independently — a later slot dies only if `evaluation − slot > 300 s`, i.e. only if
  `evaluation > T + δ + 300 s`.** A regime label ("cycling", "S = 0", "no exclusion window") selects the
  *input* to the model; it is never a substitute for running it. Enumerate the pending slots from
  `cron/jobs.json` before forecasting, or a survivor gets swept up in a neighbour's discard.
- ⛔ **Never dismiss a power assertion using a sleep window that closed BEFORE the hold was created —
  order the two timestamps first** (2026-08-11 04:16 ICT). 2051z read `pid 407(dasd)` `BackgroundTask`
  `DASActivity:501:com.apple.FileProvider.maintenance.fpck-repair` id `0x0000fa48000b862c` at 03:56:58
  (age 00:01:05 ⇒ creation **03:55:53**) and filed it "demonstrably not blocking — the host is sleeping
  through it." The sleep it cited ended **03:56:06**, thirteen seconds *after* the hold was created,
  and no sleep occurred for the next 20 min: same id still up at 04:16:19, aged **00:20:27**, meter flat
  at 3378.0. The hold was the thing that **ended** the cycling regime. This also contradicted §1's own
  record (the 00:37 ICT cycle "ran clean on transient `dasd` BackgroundTask assertions with the display
  off"), so check the checklist before overriding it. `BackgroundTask` is not an idle-sleep assertion
  type, but a `dasd` batch demonstrably suppresses sleep anyway — treat it as §1's unbounded holder
  (measured batches 26 / 40 / 55+ min / **≥57 min**), conditional in both directions.
  ✅ **Strongest form of this observed 2026-08-11 04:52 ICT — that same hold `0x0000fa48000b862c` reached
  `00:57:05` as the ONLY assertion on the host.** `PreventUserIdleSystemSleep`, `UserIsActive`,
  `PreventUserIdleDisplaySleep` and `PreventSystemSleep` all read **0**; every transient row the prior
  cycle saw (`runningboardd` WhatsApp `FinishTask`, `dasd` `ApplePushServiceTask`) was gone; only
  powerd's always-discounted `ExternalMedia` remained — and the host had still gone **56 min with
  S = 0**. This forecloses the "some *other* hold was really responsible" reading: a lone `dasd`
  `BackgroundTask` suppresses system sleep by itself. **≥57 min is a new max, and the band 26 → 57+
  still shows no characteristic length — never read "approaching an hour" as a release signal.**
  ✅ **That same hold's FULL length is now measured: ≈64 min 58 s** (2026-08-11 05:17 ICT). It was gone
  by the 05:17:20 probe; sleep onset came **05:01:51** (`getUpdates` gap), so backing out `sleep 1`
  puts release at ≈**05:00:51** against creation 03:55:53. Bounded certainly to (04:52:58, ~05:00:51]
  because at 04:52:58 it was the *only* hold ⇒ **≥57:05 certain, ≈65 min by the sleep-1 chain.**
  Band is now **26 / 40 / 55+ / 57+ / ≈65 min** and sleep resumed within ~60 s of the release, which
  is the cleanest confirmation of the 04:16 correction above. Still no characteristic length.
  ⛔ **That ≈65 min is NO LONGER the all-class ceiling — a grok hold has been observed at ≥ 78 min 53 s
  and still running, so stop treating "longer than anything measured" as a release signal** (2026-08-11
  11:03 ICT). `pid 16591(grok)` `[0x0001452f00019b64]` `NoIdleSleepAssertion` "grok: agent turn in
  progress", **one id across five consecutive cycles** — ages 04:46 / 24:04 / 42:46 / 60:18 / **78:53**
  ⇒ creation 09:44:43, single pid, no stacking — held S = 0 for **2 h 50 min** with the display off and
  `UserIsActive` **0** throughout (no HID for ≈65 min). Four cycles in a row each called its then-current
  age notable and predicted nothing; each was right that it was not a release signal. Class bands:
  `dasd` 26 / 40 / 55+ / ≈65, Chrome media ≈40, **grok ≈40 / ≤22:34 / [45:37, 64:55] / ≥78:53**. The
  bands do not cluster by class and the maximum keeps moving, so the unbounded-holder rule is not a
  statement about typical length that a long observation can erode — **never schedule against a release
  in either direction, however old the hold.**
  ⛔ **grok re-arms PER TURN, not per PID — so a PID is not a hold identity, and tracking by pid
  OVERSTATES a class length** (2026-08-11 14:46 ICT). The pid churn above (16591 / 63497 / 86967) was
  incidental — grok restarting between turns — and 0723z read it as "the per-turn re-arm under a fresh
  pid, n=4". Measured against a fixed pid: **pid 86967** held `[0x0001858d00019338]` (creation
  14:19:21) at 14:26:50 and `[0x00018bb10001964f]` (creation **14:45:33**) at 14:46:35 — **same pid,
  two different holds**, with a gap between them. A cycle joining on pid reads one continuous
  ≥27-minute hold where there were two short ones. **Track the assertion id, exactly as this section
  already requires for `UserIsActive` — the id is the instrument for every holder class, not just HID.**
  ⛔ **And when the boss sits down, that hold's length becomes LEFT-BOUNDED ONLY — the `sleep 1`
  back-out dates a release only when the release is what PERMITTED the sleep** (2026-08-11 11:21 ICT).
  That same grok hold `[0x0001452f00019b64]` was gone by 11:22:33, but the meter stayed flat at 5133.3
  throughout, because HID returned at **11:10:10** and held the host awake across the release. There is
  no onset to back `sleep 1` out of, so the release bounds only to **(11:03:36, 11:22:33]** and the
  length to **[78:53, 97:50]** — versus the `dasd` case, where sleep resumed within ~60 s and pinned the
  release to a second. **Expect this exact loss whenever a long hold ends near a wake, which is when
  they most often do end.** Corollary in the same probe: pid **16591 was still alive** with no assertion
  (`ps` elapsed 02:40:38) — fourth confirmation that process liveness is not a proxy for a held
  assertion. Record the bracketing probe times on any hold you are timing; they are all you may get.
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
  ⛔ **powerd's stopwatch is a DISPLAY-on stopwatch, not an HID stopwatch — "age > 600 s ⇒ re-tickle
  proved" is FALSE whenever a display holder is up, and here is the counterexample** (2026-08-11 07:09
  ICT, first time caveat (b) actually bit). The rule's proof step is valid only on the branch where
  `PreventUserIdleDisplaySleep` = **0** over the span; 2351z published it with the count at **1**
  (Chrome's Video Wake Lock) and was falsified within 18 min. Measured: the `UserIsActive` id
  **churned** — `0x000109fe00098b4c` (last tickle 06:42:40, due to release 06:52:40) →
  `0x00012385000991d9` (creation **06:59:57**), i.e. **≈7 min of `UserIsActive` = 0, HID demonstrably
  idle** — while powerd's `0x000109fa00018adc` ticked straight through it, unchanged since 05:08:52
  (age 02:00:16 at that probe). A second churn followed inside the same cycle:
  → `0x000126c30009927d` (creation **07:12:21**), a further **2 min 24 s** idle. **Rank the
  instruments: `UserIsActive` id > count > stopwatch.** An id CHANGE is positive evidence of a ≥600 s
  HID-idle gap; the stopwatch is corroboration only, and only where the count is 0. This does not
  weaken the id test — the 05:37 and 05:56 ICT entries stand — it strips the *third* instrument of the
  proof role they lent it.
  ✅ **First measured length for the Chrome media class: ≈39–42 min** (same probe pair). The triple
  released in (07:09:09, 07:12:21] against a first-observed creation of 06:30:00 — a lower bound,
  since that is the first *observed* id of a churning set. Band across holder types is now
  `dasd` 26 / 40 / 55+ / ≈65, grok ≈40, **Chrome ≈40 min** — no characteristic length, and it does
  **not** cluster by class, so §1's unbounded-holder rule still governs all of them. Keep session
  length and id length apart: this session ran ≈40 min while each of its ids lived ≈12.7 min.
  ✅ **Cheaper and hole-free instrument — the `UserIsActive` ASSERTION ID is itself the re-tickle
  proof** (2026-08-09 15:27 ICT, n=1). The row carries `Timeout will fire in N secs
  Action=TimeoutActionRelease`, so the assertion **releases at its own 600 s timeout**. Therefore
  **the same id observed at two probes more than 600 s apart proves the countdown was re-armed** — HID
  activity by construction, no inference. Measured: id `0x0001a36700099a6e` at 15:09:06 (age 0, 600
  secs left), 15:28:13 (age 0, 600), 15:30:22 (age 2, **598**) — 1276 s on one id, across the 08:08Z
  cycle's predicted ~15:20:06 onset, which did not happen (meter flat 44789.7 → 44789.8, no
  `getUpdates` gap). This closes caveat (b) above: a transient `PreventUserIdleDisplaySleep` holder
  keeps the display on **without** re-arming `UserIsActive`, so it yields id churn/release — a
  *different* observable, not a confounded one.
  ✅ **First span where the count test was blind THROUGHOUT and the id test carried it alone**
  (2026-08-11 05:37 ICT). `PreventUserIdleDisplaySleep` read **1** at *both* probes (AnyDesk
  `0x00010aba00058be1`, creation 05:12:04), so the 09:44 ICT count rule could rule out nothing — the
  16:12 case at least had the holder arrive mid-span. Both remaining instruments agreed:
  `UserIsActive` id `0x000109fe00098b4c` unchanged 05:17:20 → 05:37:20 = **1200 s = 2.0×** its own
  600 s `TimeoutActionRelease`, and powerd's stopwatch `0x000109fa00018adc` at age **00:28:28**
  (creation 05:08:52, same id) = 1708 s of display-on against a 600 s countdown. **Re-tickle proved by
  construction.** Operational rule: when anyone is remoted in, the count test is unavailable for the
  whole session — **read the `UserIsActive` id, not the count.**
  ✅ **Mirror image of that span, 19 min later — the count test came back and AGREED** (2026-08-11
  05:56 ICT). AnyDesk's `0x00010aba00058be1` released, so `PreventUserIdleDisplaySleep` read **0**,
  and all three instruments returned the same verdict on one probe: `UserIsActive` id
  `0x000109fe00098b4c` **unchanged since 05:17:20 = 2328 s = 3.9×** its 600 s `TimeoutActionRelease`;
  powerd's stopwatch `0x000109fa00018adc` age **00:47:16** (creation 05:08:52, same id) = 2836 s of
  display-on against a 600 s countdown; count **0**, excluding the transient-holder branch outright.
  The pair of cycles is a natural experiment — **the id test returns the same answer with a display
  holder up for the whole span and with none up** — which promotes it from "the one that still works"
  to the default. Record the `UserIsActive` id every probe; treat the count as corroboration.
  ✅ **Both DIRECTIONS of the id test are now scored inside 20 min, and the count agreed each time it
  was available** (2026-08-11 07:31 ICT). 0008z scored the **churn** branch with the count blind (1,
  Chrome's Video Wake Lock) and the stopwatch saying the opposite; this cycle scored the **persist**
  branch with the count **0 at both ends**: id `0x000126c30009927d` unchanged 07:12:21 → 07:31:01 =
  **1120 s = 1.87×** its own 600 s `TimeoutActionRelease` ⇒ re-tickle proved by construction, count 0
  excluding the transient-holder branch, and powerd's stopwatch (`0x000109fa00018adc`, creation
  05:08:52, age 02:22:09) on its *valid* branch for once and agreeing. Churn ⇒ ≥600 s HID idle;
  persist across >600 s ⇒ re-tickle. **Both directions, one field, one row.**
  ⛔ **The PERSIST branch is FALSIFIED without an `S = 0` precondition — `TimeoutActionRelease` counts
  down on MONOTONIC time and freezes during sleep, so a persisted id bounds AWAKE time, never wall
  time** (2026-08-11 08:13 ICT). Measured: id `0x000126c30009927d` unchanged **07:12:21 → 08:13:34 =
  3673 s = 6.1×** its own 600 s timeout — which the rule above reads as "re-tickle proved by
  construction, HID active throughout" — while the meter says **S = 1394.1 s** (3739.2 @ 07:31:54 →
  5133.3 @ 08:13:05) and powerd's display-on hold **churned** (`0x000109fa00018adc` creation 05:08:52 →
  `0x00012e5e0001955d` creation **08:07:22**), i.e. the display went dark and came back. The id test
  said HID was active; the display had slept. No sub-span of *continuous awake* time need reach 600 s —
  ~1480 s awake pre-onset, six ~20 s dark-wake slivers, then a tickle at the 08:06:53 wake resets it —
  so the assertion never released. **Churn branch is unaffected** (id changes ⇒ ≥600 s HID idle, still
  positive evidence). **Persist branch is valid only across a span with S = 0**; with S > 0 it can read
  exactly backwards. Every prior confirmation (05:37 / 05:56 / 07:31 ICT) was measured inside an S = 0
  window — the same pattern that hid the missing `+ S` in §0's `completion + 900 s` rule. Ranking, all
  three instruments now carrying a precondition of the same kind:
  **id (S = 0 over the span) > count (0 over the span) > powerd stopwatch (count 0 over the span);
  with S > 0 all three are blind and only the meter + `getUpdates` gaps say anything.** When two
  instruments disagree, the one with an unmet precondition is the wrong one. **Record the meter delta
  alongside every `UserIsActive` id reading — a bare id is no longer a conclusion.**
  ⚠️ **The sleep-onset chain's positive branch has now erred in BOTH directions — stop calling it
  "overshoots"** (same cycle). 0030z predicted, from tickle 07:29:57: display timeout 07:39:57, system
  sleep **≈07:40:57**. Observed onset is bounded by the `getUpdates` cadence to **(07:36:32, 07:39:42)**
  — sleep began at or before the predicted *display* timeout — residual **−75 to −265 s** against a
  prior series of **+258 / +412 / no-onset / no-onset**. Nothing can make system sleep precede the
  display countdown on the powerd chain, so the surviving candidates are a display sleep that did not
  come from the idle countdown (manual sleep, lock, hot corner, screensaver, lid) — unmodelled and
  undecidable from disk. Also note 0030z's scoring table enumerated three cells and the observed one was
  the **fourth — id unchanged AND onset** — which the old rule called impossible; that is why this is a
  falsification and not a fifth inconclusive. Enumerate all four cells when scoring the chain.
  🆕 **A no-onset is only EXCUSABLE while some unbounded holder is up — when they all clear, the
  positive branch becomes falsifiable, so take that observation** (2026-08-11 07:31 ICT). The positive
  direction has scored +258 s / +412 s / no-onset / no-onset and has never landed, each time excused by
  a holder or a re-tickle. At 07:31:01 powerd's display-on hold was the **sole** idle-sleep assertion —
  no `dasd`, no grok, no AnyDesk, and Chrome's media triple released — leaving §1's unbounded-holder
  rule nothing to point at. Score such a window with the id test: id **changed** + onset ⇒ chain
  **confirmed**; id **unchanged** + no onset ⇒ inconclusive, cause proved; id **changed** + **no onset**
  ⇒ **genuine falsification**, unreachable in every prior case. Set the observation up before the
  confounders return — they are unbounded in arrival as well as release.
  ⚠️ **`sharingd`'s `PreventUserIdleSystemSleep` "Handoff" CHURNS its id — never build a floor on it**
  (same probe): `0x00010bc600018c27` @ 05:17:20 → `0x00010faf00018cd4` @ 05:37:20 (age 00:04:07 ⇒
  creation 05:33:13). Two different holds 20 min apart, each a few minutes old. It has a real age so
  it does not fall under the `bluetoothd` age-00:00:00 discount, but it is transient by the same
  reasoning as §1's unbounded-holder rule pointed the other way — treat it as neither a floor nor a
  ceiling. powerd's stopwatch agreed here
  (`0x0001a361000199b9`, creation 13:14:44/45 at both probes, 135.6 min, count 0 both times), so use it
  as corroboration, but **record the `UserIsActive` id with its age every probe** — it is one field
  from one row and it settles the question alone.
  ✅ **Same id extended to 3812 s (2026-08-09 16:12 ICT), and it survives a mid-span holder arrival.**
  `0x0001a36700099a6e` still up at 16:12:38 (age 00:01:26, 513 secs left) — 15:09:06 → 16:12:38 on one
  id, 6.4× its own 600 s timeout, meter flat at 44789.7 throughout. Note the **age field resets on
  every tickle while the id persists**, which is exactly why the id is the instrument and the age is
  not. Also a clean illustration of the count-branch closing mid-span: `PreventUserIdleDisplaySleep`
  read 0 at the 15:09–15:30 probes but **1** at 16:12 (AnyDesk re-created its hold ~15:57:31, with the
  paired `coreaudiod` `Created for PID: 42666`), so 13:14:45 → 15:57:31 stays re-tickle-**proved** while
  the segment after it is merely inconclusive. The id test kept working across that transition; the
  count test did not.
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
- ⛔ **`Timeout will fire in N secs` on a NON-`UserIsActive` holder is an UPPER bound on that hold's
  life — it is the WRONG DIRECTION for a sleep-exclusion window, never build a floor from it**
  (2026-08-11 02:50 ICT). Some `PreventUserIdleSystemSleep` owners carry a real absolute countdown
  (`AddressBookSourceSync`, n=4 as of 2026-08-10 02:28 ICT: the timeout does **not** re-arm, unlike
  `UserIsActive` — see the id test above). That makes the timeout a genuine *release* deadline, and it
  is tempting to read a large N as free exclusion: at 02:46:33 on 08-11, `pid 80238` held one with
  **1613 secs** remaining, which would appear to guarantee the 03:05:00 slot outright. **It
  guarantees nothing.** `Timeout will fire in N` says the hold is gone **by** that instant, not that
  it survives **until** it — the holder may release early, as the 1910z→1928z instance did somewhere
  in an unresolvable 16 min window. An exclusion window needs a *lower* bound on holder life.
  **Only `UserIsActive` yields a floor**, because powerd's display-on hold tracks the display
  countdown and that chain is measured (n=2 exclusion cases above). Treat every other holder as
  §1's unbounded case even when it prints a number.
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
  🆕 **grok's per-turn hold STACKS ACROSS PROCESSES — "the grok hold" is not a single row** (2026-08-11
  09:11 ICT). Two concurrent `NoIdleSleepAssertion` "grok: agent turn in progress" holds were up at one
  probe: pid **63497** `[0x00013b9c0001986d]` (creation **09:03:52**) and pid **16591**
  `[0x00013c99000198a6]` (creation **09:08:04**). Every prior sighting (05:42 / 06:40 / 10:05 / 10:47
  ICT 08-09) was a lone hold, and the finding then was that grok re-arms per turn under a *new pid* —
  both are true at once here, since pid 16591 **also churned its own hold** (a different id, creation
  08:43:20, was up 20 min earlier and is gone). So the set is `{released, re-created, plus a second
  process}`. **Consequence: an id churn on one grok pid does NOT mean the class released, and reading
  one row understates the postponement.** Same failure shape as Chrome's lockstep triple — when
  attributing an S = 0 window, enumerate every owner row, never a single one. It changes no forecast
  on its own: each hold stays §1's unbounded conditional in both directions.
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
  🆕 **The `Created for PID:` shape GENERALISES past AnyDesk — Chrome media playback arms THREE holds
  at once** (2026-08-11 06:33 ICT, new holder class). Observed together, all three sharing the id
  prefix `0x00011cfe` and all created **06:30:00**: pid 2210 `Google Chrome`
  `NoIdleSleepAssertion` "Playing audio" `[0x00011cfe000190b3]`, pid 2210 `NoDisplaySleepAssertion`
  "Video Wake Lock" `[0x00011cfe000590b2]`, and pid 444 `coreaudiod` `PreventUserIdleSystemSleep`
  `[0x00011cfe0001852e]` **`Created for PID: 2334`** — where 2334 is a `Google Chrome Helper`. The
  `NoIdleSleepAssertion` blocks idle **system** sleep independent of the display, exactly like grok's
  per-turn hold, so a tab playing video excludes sleep on its own. Unbounded in release time (a video
  ends whenever it ends) ⇒ **conditional, never a floor**.
  ⛔ **And the triple CHURNS ITS IDS IN LOCKSTEP — never point the id test at this holder** (2026-08-11
  06:51 ICT, 18 min after the class was first filed). All three ids changed together, `0x00011cfe…`
  (creation 06:30:00) → **`0x00011ff6…`** (creation **06:42:40**), while pids, assertion names and the
  `Created for PID: 2334` line were all identical — i.e. **one continuing media session re-creating its
  whole assertion set**, not a new one. Same shape as `sharingd`'s Handoff churn, one class wider. The
  id test is sound for `UserIsActive` *only* because that row's `TimeoutActionRelease` makes a
  persistent id proof of re-tickle; here an id change is ordinary churn, not a release, so reading it
  that way would score ~13 min of continuous sleep-blocking as two short unrelated holds. **Take the
  floor from `UserIsActive`; treat Chrome as an unbounded conditional postponement only.**
  ⛔ **The "three holds at once" above is a MEDIA signature, not a Chrome signature — and a holder can
  HAND OFF TO ITSELF under a different assertion NAME, so a disappearing row is not a release**
  (2026-08-11 14:05 ICT). At 14:05:48 Chrome's sole hold was pid 2210 `[0x00017e8a00019108]`
  `NoIdleSleepAssertion` **"WebRTC has active PeerConnections"**, age 00:16:22 ⇒ creation **≈13:49:26**
  — within **5 s** of 0642z's 13:49:21 probe, the exact instant that cycle saw
  `PreventUserIdleDisplaySleep` fall **1 → 0** and wrote "Chrome's Video Wake Lock released", closing
  the class at "life ≤ 9 min 46 s". True of the *triple*, false of the *holder*: Chrome blocked idle
  **system** sleep continuously ≈13:39:35 → ≥14:05:48 (**≥26 min**) across a transition that looked
  like a release on every instrument that cycle had. Three consequences: (a) a WebRTC call arms **one**
  hold — **no** paired `coreaudiod` `Created for PID:` row, **no** `NoDisplaySleepAssertion` — so a
  cycle looking for the triple sees nothing and calls Chrome clear; (b) **the count test is blind in
  the direction that matters**: `PreventUserIdleDisplaySleep` reads **0**, the "valid branch" for
  powerd's stopwatch and the branch that supposedly excludes transient holders, while a *system* hold
  is up — so refinement #2's precondition ("no OTHER idle-sleep hold may be up") is violated
  **invisibly to the count**, and any onset prediction off the display chain is unsound there;
  (c) generalise past Chrome — **re-enumerate owners by PID, not by assertion name.** Same shape as
  grok's stacking and the lockstep churn, one level out: there the *ids* churned under a fixed name,
  here the *name* changed under a fixed pid. An S = 0 attribution made off `UserIsActive` is unharmed;
  what breaks is the narrative "X released", which is the label-absorbs-an-unlike-event error again.
  ⛔ **Corollary that bites the count test: `PreventUserIdleDisplaySleep` = 1 does NOT identify its
  holder, and the holder can swap under an unchanged count.** At 06:14:57 the 1 was AnyDesk
  (`0x000115ae00058e6a`, pid 90021, + its paired coreaudiod `0x000115b100018cf3`); 19 min later both
  were **gone** and the 1 was Chrome's Video Wake Lock — same reading, different cause, no transition
  visible in the count. Read the owner rows, not the status block; and per the id test above, record
  the `UserIsActive` id rather than leaning on the count at all.
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
  ⚠️ **That pattern SELF-MATCHES the shell running it** (2026-08-09 15:49 ICT) — the command line of
  the `zsh` executing the `pgrep` contains the pattern, so it returns a phantom second PID. Confirm any
  extra PID with `ps -o pid,ppid,lstart,command -p <pid>` before reporting a duplicate bot instance.
- Check `/tmp/claude-telegram-bot.err` for recent errors (last 5 min)
- Alert if bot is down or throwing repeated errors

### 3. Memory & Reminders
- **Read memory FIRST, before drafting any alert** — otherwise known issues get re-reported as new discoveries
- Read `memory/t0/MEMORY.md` (repo root) for pending tasks or reminders
- Check today's daily logs at `memory/t0/{YYYY-MM-DD}/` for context on what's been done
- **Path warning:** `workspaces/c352342178/memory/` is a STALE duplicate tree. Never read or write it.
  Heartbeat logs go to `memory/t0/{YYYY-MM-DD}/heartbeat-{HHMM}z.md` at the repo root.
- ⛔ **LOCAL MIDNIGHT SILENTLY BREAKS THE HANDOFF CHAIN — a cycle that starts before it and hands off
  to a cycle that starts after it must ALSO write into the next day's directory** (added 2026-08-11
  00:02 ICT). The SessionStart hook injects **today's** daily logs only, and "today" is ICT. The
  16:55Z cycle started 23:55 ICT and logged to `memory/t0/2026-08-10/`; the ≈00:12 ICT cycle's
  injected context is `memory/t0/2026-08-11/`, which was **empty**. Everything §1/§7 exists to carry
  — the pending survival calls, the caffeinate exclusion window and its 00:27:32 expiry, the meter
  baseline, the measured 17-min cadence, the do-not-alert list, the standing order on the 00:00 ICT
  `vidnotes-alerts` deliverable — would have vanished at midnight with no error and no gap in the
  logs, and the next cycle would have re-derived it all from scratch or, worse, re-reported known
  items as new. Note this is the *same class* of failure as the CLAUDE.md finding that
  `memory/t0/MEMORY.md` is write-only: a file being written is not evidence that anything reads it.
  **Rule: if your cycle starts within ~20 min of local midnight, write the handoff to
  `memory/t0/{TOMORROW}/00-handoff-from-{TODAY}.md` as well as your own log** (condensed carry-over
  is enough — link the full log by path). Worked example:
  `memory/t0/2026-08-11/00-handoff-from-2026-08-10.md`.

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
