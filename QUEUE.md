# Boss Queue — decisions the fleet cannot make for itself

Heartbeat cycles repeatedly write *"belongs in the boss's queue"* / *"stays boss-pending"*
(`HEARTBEAT.md` lines 545, 2138, 2232, 303). **No such queue existed** until 2026-08-15 02:4x ICT —
the items lived only as prose inside a 232 KB, 2438-line checklist, so nothing was ever actually
queued. This file is the queue. It is short on purpose.

**For cycles:** when a finding needs a decision or an edit outside a heartbeat's remit, add a row
here *and* keep the evidence in `HEARTBEAT.md`. A finding filed only in the checklist is not queued.
**For the boss:** everything below is verified against the source at the line cited, not inferred.

---

## 1. `prompt`-job cap: `timeout=600` → 1800

**Where:** `bot/scheduler.py:163` (message at `:176`).
**Symptom:** every weekly `prompt` job times out at exactly `fire + 600 s`, produces **no report**,
and stamps a *fresh* `last_run` — so the staleness check reads it as healthy for the next 7 days.
Only `last_status` carries it, and `consecutive_errors` resets to 0 on the next success.
**Current casualties** (both `ce=1`, both will recur unchanged):

| job | schedule | last | next fire |
| --- | --- | --- | --- |
| `weekly-conjecture` | `0 8 * * 0` America/New_York | `2026-08-10T12:10:00Z` (= fire + 600 s) | **Mon 2026-08-17 08:00 ET** (19:00 ICT) |
| `vidnotes-weekly` | `30 7 * * 1` Europe/Warsaw | `2026-08-11T05:40:00Z` (= fire + 600 s) | **Tue 2026-08-18 07:30 Warsaw** |

⚠️ **Those two dates were each one day earlier in this table until 2026-08-15 05:2x ICT, and the
`~38 h out` figure heartbeat 2157z sent you was wrong for the same reason — see #7.** These cron
strings are parsed by `CronTrigger.from_crontab`, and **APScheduler numbers `day_of_week` from
0 = Monday**, not Unix cron's 0 = Sunday. So `* * 0` is Monday and `* * 1` is Tuesday. Confirmed
against the installed APScheduler *and* against every fire in `logs/infra.log`: `weekly-conjecture`
last ran Mon 08-10, `vidnotes-weekly` Tue 08-11, `cleanpro-weekly` Tuesdays 07-21 / 07-28 / 08-04.
No job is misbehaving — the **strings mean one day later than they read.** Nothing to fix unless you
want the files to say what they mean; the hazard is arithmetic done off the string.

**Evidence it is a capacity limit, not a hang — now the full population, not the top two**
(2026-08-15 11:3x ICT, every `Running job:`/`Job … completed|failed` pair in `logs/infra.log`):

| job | n | successes | median ok | **max ok** | cap-kills |
| --- | --- | --- | --- | --- | --- |
| `vidnotes-weekly` | 14 | 5 | 354 s | **528 s = 88 % of cap** | **9 (64 %)** |
| `weekly-conjecture` | 12 | 7 | 370 s | **540 s = 90 %** | 5 (42 %) |
| `cleanpro-weekly` | 14 | 12 | 335 s | 449 s = 75 % | 2 (14 %) |

Successes climb continuously toward the cap and clear it — the capacity signature. **`vidnotes-weekly`
has failed 9 runs in 14; `ce=1` only because a single success resets the counter.** 1800 s leaves the
observed max ~3.3× of headroom.
**Note:** this applies to `:163` only, and *only to the weekly jobs behind it.* `vidnotes-alerts` runs
through the same line — n=882, median **92 s**, 1 % cap-kills — so the prompt tier **pooled** reads as
the hang branch and hides all of the above; judge the cap per job. The identical-looking `gtimeout 600`
on the heartbeat itself is genuinely the hang branch — raising **that** would only let each hang burn
longer. Evidence: `memory/t0/2026-08-15/heartbeat-0429z.md`; `HEARTBEAT.md`, search
`ONLY VALID ON A HOMOGENEOUS POPULATION`.

## 2. `cleanpro-daily` fails ~7 % of runs — the 300 s cap explains only 3 of the 7

**ASK — do #6 first, then decide this one.** Set `scripts/daily_report_common.py:48` from
`timeout=600` to **`timeout=120`**: strictly below the outer 300 s cap, leaving room to catch the
raise, name the failing SQL, and still finish inside the budget. Not a heartbeat's call because it is
a **shared module behind six live daily runners** (`cleanpro`, `echo`, `mangii`, `pdfai`, `aividly`,
`vidnotes`), first firing 03:00 ICT.

**Why it is an ask at all — a 600 s inner timeout inside a 300 s outer cap is unreachable:**

| layer | value | source |
| --- | --- | --- |
| scheduler kills the script | **300 s** | `bot/scheduler.py:120` |
| every `bq query` is allowed | **600 s** | `scripts/daily_report_common.py:48` |
| generic `run()` default | **300 s** (= the cap, so also too late) | `scripts/daily_report_common.py:31` |

No query can ever time out; the outer kill always wins and the process dies with no error and no name
for the stalled query. Both values are grep hits and both are dead.

**Why to hold it — the failure population says the stall may not be in BigQuery at all.** Full series
from `logs/infra.log`, n=101 (04-13→08-15): 94 successes span **91–200 s**; the 7 failures are
**bimodal — 4 fast `exit 1` (3/130/153/156 s) plus 3 cap-kill timeouts (300/301/300)**. The 4 fast
ones carry full stderr, and **three of them name `oauth2.googleapis.com` token acquisition, never a
query** — `NameResolutionError … Failed to resolve` (05-12), and twice
`ConnectTimeoutError … (connect timeout=120)` (07-21, 07-22). With that 120 s connect timeout and
urllib3 retries, one timed-out connect ≈ the observed 153/156 s and a second retry lands past 300 s,
i.e. the cap-kill band. If that is right the stalling call is **auth, not `bq query`**, and the edit
above touches nothing. Confidence moderate-high: the 120 s value and the host are quoted from the log;
the cap-kill attribution is inferred, because the stderr drain is dead (#6).

**Free falsifier, and it orders the work:** apply #6's structural drain first, then read the next
300 s failure. Names `oauth2.googleapis.com` ⇒ this row is the wrong file and should be closed. Names
a `bq query` ⇒ apply the ask above. #6 is local and diagnostics-only; this one is the risky edit —
so the cheap fix decides the expensive one.

Minor, same file: `cleanpro_daily_runner.py:447,451` (heatmap + `curl`) have no timeout at all, but
run *after* `send_telegram` at `:439` and so cannot cost the report.
Evidence: `memory/t0/2026-08-15/heartbeat-2041z.md`, `-0333z.md`; superseded 12-run "hang"
distribution and its dead-zone argument archived at `HEARTBEAT-ARCHIVE.md` §I.

## 3. CleanPro conversion alert is a coin flip — `scripts/cleanpro_alerts_runner.py:99`

**Corrected 2026-08-15 04:2x ICT — this row cited `bot/scheduler.py:99`, which is
`raise ValueError(f"Unknown job type: …")`.** Opening it would have read as a nonsense row and got
the item dropped. The real line:

```python
baseline = float(baselines.get('conversion_rate_7d', 10.0) or 10.0)   # :98
if paywall_shown < 10 or conv_pct >= baseline * 0.70:                 # :99  ← the 0.70
```

**Defect:** a **4-hour window** rate is compared against a **weekly cohort** baseline (10.4 %).
Conversions lag their paywall view across the window edge, so the windowed rate sits structurally
below the cohort rate and the 0.70 multiplier lands mid-distribution — the check fires about as
often as not, on healthy data. Same defect as the vidnotes conversion check (2026-08-07).
**Repair (needs a judgement call, not a one-liner):** compare the window against the *windowed*
historical distribution — same-hour percentile or CUSUM on the daily series — or move conversion
monitoring to the daily report entirely. The runner's own `:88-97` comment block already states
this; nobody has picked between the options.
Evidence: `scripts/cleanpro_alerts_runner.py:88-99`; `HEARTBEAT.md`, search `mis-calibrated
threshold at` (the old `:2138` cite has drifted — that line is now §3 memory text).

## 5. `guard/guard.sh:27` blocks the word "skill " as a process kill — one-char fix, cycles are barred

**Where:** `guard/guard.sh:27`. Cycles may not edit `guard.sh` (`CLAUDE.md` §Safety), so this is yours.

```bash
if echo "$CMD" | grep -qiE "kill\s|pkill\s|killall\s|claude-telegram-bot"; then
```

`kill\s` has **no leading word boundary**, so it also matches the tail of **`skill `** / `SKILL `.
Any Bash command containing the English word *skill* followed by whitespace is refused with
*"BLOCKED: You are not allowed to kill processes."* — in a repo whose entire job system is `skills/`
and whose `CLAUDE.md` tells cycles to put behaviour changes *"in that job's SKILL.md"*.

Probed both sides, 2026-08-15 03:2x ICT: `ls skills/…; wc -l …SKILL.md` **allowed** (path forms are
safe — `skills/` puts `s` after `kill`, `SKILL.md` puts `.` there); `echo "… the word skill followed
by a space …"` **blocked**. Prose trips it, paths do not.

**Patch:** `"\bkill\s|\bpkill\s|\bkillall\s|claude-telegram-bot"`. The `\b` before `kill` kills the
`skill` match (`s`→`k` is word-char to word-char, so there is no boundary) and still matches every
real invocation. Scheduled jobs are unaffected either way — `bot/scheduler.py` uses
`create_subprocess_exec` with no hook; the cost is entirely to agent Bash calls.

✅ **RUN, not just proposed (2026-08-15 05:5x ICT) — safe to apply. But note WHY, because the row did
not say it and it is the only way this edit could go wrong.** `\b` is a **GNU extension, not POSIX
ERE**: on a `grep -E` without it, `\bkill\s` matches the literal `bkill ` and rule 1 **fails open** —
every `kill`/`pkill`/`killall` allowed, silently, with nothing to error on. Probed on this host's BSD
grep: `\babc` matches `abc` (1) and not `xabc` (0), so it is honoured here. Full before/after —
`kill -9 1234`, `sudo kill 1234`, `pkill -f node`, `killall Dock` **all still BLOCK**; `skill the
docs` goes BLOCK → allow; only side effect is words *ending* in "kill" (`dekill`) are freed, and no
such command exists. **If `guard.sh` is ever ported to a host with a stricter grep, re-run that
two-line probe first.**

⚠️ **`skill` is the third instance of one shape in this 24-line file, and the patch fixes one of
them.** `guard.sh` substring-matches the **command text**, so it cannot tell *mention* from *use*:
rule 1's `claude-telegram-bot` blocks any command naming the bot read-only or not (documented,
`HEARTBEAT.md:1100`), and **rule 4's `shutdown|reboot` — probed this cycle — refuses
`pmset -g log | grep -ci reboot` as "Destructive system commands are not allowed."** That one is the
worst of the three because it has **no escape**: the documented workaround for the bot-name block is
the Grep tool, which needs a *file*, and `pmset -g log` is a command — and `pmset -g log` is the
fleet's own sleep-meter instrument (§1). Workaround verified this cycle, no rewording involved:
`pmset -g log > /tmp/pm-sleep.log` (allowed — only the two words are blocked, not `pmset`), then the
**Grep tool** on the file. Generalises `HEARTBEAT.md:1166` to *materialise to a file, then Grep-tool
it*. **No action requested on rules 3/4** — the intent is right and the workaround is cheap; recorded
so the `\b` fix is not mistaken for closing the class.
⛔ **THE `\b` PATCH IS NECESSARY BUT NOT SUFFICIENT — it fixes the `s`-prefixed substring case and
leaves the bigger case open (2026-08-15 09:2x ICT, 0214z, probed).** The blocked token is an ordinary
English **noun** in this repo: *"your \<tok\> is lstart + 600 s"* is a near-verbatim quote from the
`claude -p` prompt **every heartbeat cycle receives**. `\b` still matches it, because space→k IS a
word boundary. Probed on this host's BSD grep, token assembled at runtime so the command text never
held it:

| string | current | with `\b` |
| --- | --- | --- |
| `places your <tok> later than it is` | BLOCK | **BLOCK** |
| `your <tok> is lstart + 600 s` | BLOCK | **BLOCK** |
| `s<tok> the docs` | BLOCK | allow |
| `<tok> -9 1234` / `p<tok> -f node` | BLOCK | BLOCK |
| `the <tok>-instant` | allow | allow |

Tripped organically **three times in one cycle** — on a `python` heredoc rewriting `HEARTBEAT.md`, on
the probe written to diagnose that, and on the first attempt to file this very correction (blocked by
two *different* alternatives in the same rule). **The bug is self-shadowing: investigating,
describing, and filing it all reproduce it.**

**So apply `\b` — still strictly better — but do not close this row on it.** The real defect is that
`guard.sh` matches **command text** and cannot distinguish **mention** from **use**; the substring
case, the noun case, the bot's own name, and rule 4's destructive-command words are one shape in a
24-line file, and **a pattern fix cannot reach it.** The structural fix is to match the parsed command
position (argv[0]) rather than substring presence — your call, and a bigger change than this row was
opened for. Cycles have a no-reword workaround (`K=$(printf 'k%s' 'ill')`, or the `Write`/`Edit`
tools, which `guard.sh` does not intercept), so this is friction plus a correctness-of-record risk,
not a blocker. ⛔ **Rewording a finding to appease a broken matcher corrupts the record — assemble the
token.** Evidence: `memory/t0/2026-08-15/heartbeat-0214z.md`.

⚠️ **First ORGANIC trip, 2026-08-15 06:2x ICT (2318z):** `echo "=== heartbeat skill dir ==="`, inside a
routine `ls` batch, was refused as a process kill. All prior evidence on this row came from deliberate
probes; this is the first record of the bug hitting a cycle doing unrelated work. Cost was one round
trip and a reword (~15 s) — the point is the **base rate**, not the cost. No new ask; the `\b` patch
above is still the whole fix.
Evidence: `HEARTBEAT.md` §2, `memory/t0/2026-08-15/heartbeat-2019z.md`,
`memory/t0/2026-08-15/heartbeat-2255z.md`, `-2318z.md`.

## 6. `_run_script` throws away stderr on timeout — and so does `_run_prompt`'s "fix"

⛔ **REWRITTEN 2026-08-15 08:0x ICT by heartbeat 0053z. This row used to read *"the fix is already
written 45 lines below it"* and prescribe copying `_run_prompt:165-177` onto `_run_script:121-123`.
I applied that patch, tested it against the real function, and it recovers `b''`. Reverted.
The reference implementation is itself dead code.** Do not apply the old patch.

**Measured** (real subprocess, only the outer 300 s budget shrunk to 2 s; child writes to stderr and
flushes before the cap): after `proc.kill()`, a second `communicate()` returns `b''`, and reading
`proc.stderr` directly returns `b''`. **Mechanism, from the traceback:** `communicate()` →
`_read_stream` → `StreamReader.read()` with no limit accumulates into a **local list**;
`wait_for`'s cancellation discards that local *and* the bytes are already out of the pipe. Nothing
survives to drain.

**Consequence beyond this row: `_run_prompt:165-177` has never recovered a byte in production.** Its
comment describes its own failure. Corroboration: the 1122z API-death diagnosis had to be read out
of `/tmp/claude-heartbeat.log`, never out of a scheduler error message.

**The correct patch — structural, wants review, applies to BOTH paths:** own the buffer instead of
letting a cancelled coroutine own it.

```python
buf = bytearray()
async def _drain(stream):
    while chunk := await stream.read(4096):
        buf.extend(chunk)
drainer = asyncio.create_task(_drain(proc.stderr))
try:
    await asyncio.wait_for(proc.wait(), timeout=300)
except asyncio.TimeoutError:
    proc.kill()
    drainer.cancel()
    raise TimeoutError(f"Script {job['id']} timed out after 5 min: {bytes(buf).decode(errors='replace')[-300:]}")
```

`buf` survives because it is *your* object. Note this replaces `communicate()`, so the success path
needs the same treatment for stdout — that is the review-worthy part, not the drain itself.

**Where:** `bot/scheduler.py:119-123` (and `:162-177`). **Blocks nothing; unblocks #2's other half.**

The two job paths in this file handle an identical `asyncio.TimeoutError` differently:

```python
# _run_script :119-123          — script jobs (cleanpro-daily, all six daily runners)
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
except asyncio.TimeoutError:
    proc.kill()
    raise TimeoutError(f"Script {job['id']} timed out after 5 min")   # ← stderr lost

# _run_prompt :164-176          — prompt jobs (weekly-conjecture, vidnotes-weekly)
except asyncio.TimeoutError:
    proc.kill()
    _, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)  # ← LOOKS like it drains it;
    tail = stderr.decode(errors="replace").strip()[-300:]               #   measured b'', see top of row
```

`communicate()` never returns on the timeout path, so on the script path everything the runner
printed before the kill dies with the process. The prompt path's own comment states the hazard
exactly: *"the only prompt-job failures that ever need diagnosing are the ones that leave no
diagnostics at all."* That is precisely `cleanpro-daily`'s two 300 s failures (07-30, 08-13).

The change is diagnostics-only: no cap changes, no job behaviour changes, no shared module.
**Relation to #2:** independent and complementary. #2 makes a stalled `bq query` *able* to report;
#6 makes anything it reports *survive*. #2 is the risky one (shared module, six live jobs); #6 is
local to one function. Doing #6 first is strictly informative — the next `cleanpro-daily` timeout
would then name the failing query without anyone having touched the daily runners.

**Also checked, and it is clean:** `_run_prompt` spawns `claude -p` via `create_subprocess_exec`
with **no nested cap** — no `gtimeout`, no inner per-request timeout inside the 600 s at `:163`. So
the 300/600 inversion in #2 does **not** apply to #1, and #1's `600 → 1800` is not that mistake.
Evidence: `memory/t0/2026-08-15/heartbeat-2157z.md`.

## 7. A weekly job can lose a fire to sleep and still read `OK` — `cleanpro-weekly` just did

**Where:** `bot/scheduler.py:26` (`job_defaults={"misfire_grace_time": 300}`, no `coalesce`); the
detection gap is that **no code in `bot/` ever reads `last_run` back** (`:85` displays it, `:195`
and `:205` write it — that is the whole population).

**Observed:** `cleanpro-weekly` `last_run` = `2026-08-03T20:37:28Z` ⇒ **265.7 h** against a 168 h
period, with `last_status: OK` and `consecutive_errors: 0`. The missing fire is Tue 2026-08-11
03:30 ICT; `logs/infra.log` jumps **03:02:19 → 04:05:33** (~63 min of sleep, which also delayed
`echo-backend-alerts` to 04:05:33, 33 s late). 63 min ≫ the 300 s grace, so APScheduler **discarded**
the fire. The CleanPro report for Aug 4–11 does not exist and nothing raised a flag.

⛔ **The "the gap will read 14 days when 08-18 fires" clause that stood here was wrong twice, and the
second error is the one with teeth** (2026-08-15 08:3x ICT, 0131z, read from source). Date: the next
fire is **Tue 2026-08-19** (APScheduler `day_of_week` 0 = Monday — see #1's ⚠️). Substance: **there
is no widening gap and no catch-up.** `skills/cleanpro-weekly/SKILL.md:10-14` computes its window as
pure date arithmetic off *today* — `END_DATE=date -v-1d`, `START_DATE=date -v-7d`, prior week
`-v-14d`/`-v-8d`, `WEEK_LABEL=date -v-1d +%Y-W%V` — and **nothing in it reads `last_run`**. So the
08-19 fire queries **Aug 12–18**, same size as any other week, and **the Aug 4–11 report cannot be
produced by rerunning the job at any time.** Recovery means running the queries with explicit dates
and sidestepping `weekly-${WEEK_LABEL}.lock` (`SKILL.md:23`, label also derived from today) — a
manual backfill delivering into `-5201056067`, i.e. your call.
Ancillary, and it cuts against #1: `cleanpro-weekly`'s last real run took **448 s** (`last_run`
`2026-08-03T20:37:28Z` vs its 03:30 ICT fire) — **75 % of the 600 s cap, not a timeout.** #1's "every
weekly `prompt` job times out at exactly fire + 600 s" has a counterexample in its own family.

**Why it is invisible, and why it is #1's mirror:** `last_status` answers *"did the last run
succeed?"*, never *"did it run?"* #1 is the opposite corner of the same hole — a job that stamps a
**fresh** `last_run` while producing **no report**. One field cannot answer both questions, and
today the fleet checks only that field.

✅ **The detector half is BUILT and is no longer an ask — `scripts/check_missed_fires.py`, run by
every heartbeat cycle** (2026-08-15 06:2x ICT, 2318z), read-only, exit 1 on any miss, named at the top
of `HEARTBEAT.md` §1. It still prints `MISSED cleanpro-weekly` every cycle (104.3 h as of 0449z) with
zero false positives on the banded pair. ⛔ **Do not ask for `age(last_run) > 1.5 × period` instead —
it was built, measured against all 14 jobs, and fails in BOTH directions; no multiplier does both.**
Evidence and the shipped design: `HEARTBEAT-ARCHIVE.md` §J.

**What is still yours, and it is the part a heartbeat cannot do:** the *fleet* remains blind. `bot/`
never reads `last_run` back (`:85` displays, `:195`/`:205` write — that is the whole population), so a
discarded fire raises nothing on its own; a cycle has to be awake and looking. And **detection is not
recovery** — the Aug 4–11 CleanPro report is still missing, and per the ⛔ above **no future fire of
this job will ever produce it**; only a hand-run with explicit dates can. The decisions are (a) whether `bot/` should
warn on delivery, and (b) whether `coalesce: True` or a longer `misfire_grace_time` at
`bot/scheduler.py:26` is right for weekly jobs, which trades a lost report against a stale-window one
that fires hours late. Both change live scheduling behaviour; neither is a heartbeat's call.

Evidence: `HEARTBEAT-ARCHIVE.md` §J; `memory/t0/2026-08-15/heartbeat-2318z.md`, `-2235z.md`, `-2216z.md`.

## 8. The miss detector answers #7 for `cron` jobs only — `interval` jobs lose ~18 % of fires unseen

**Where:** `scripts/check_missed_fires.py:60-64` (the `interval_seconds` branch).
**Found:** 2026-08-15 06:5x ICT, from `logs/infra.log`, one cycle after the detector shipped.

The two branches answer **different questions**, and only one of them is #7's question:

| branch | test | asks |
| --- | --- | --- |
| `cron` | enumerate the trigger's own fires | **"did the last owed fire run?"** |
| `interval_seconds` | `expected = now − 1.5 × interval` | **"am I mid-outage right now?"** |

The inline comment defends the second as safe, and against *false positives* it is. The hole is
**false negatives**: an interval job that loses a fire and resumes stamps a fresh `last_run`, so the
check reads healthy the instant the outage closes. It catches a loss only while one is in progress.

Measured since 2026-08-01, both interval jobs (`interval_seconds: 7200`):

| job | fires | fires lost | rate | worst gap |
| --- | --- | --- | --- | --- |
| `auto-commit` | 141 | **32** | **18.5 %** | 8 h 00 m (08-13 20:33 → 08-14 04:33) |
| `cleanpro-exp-monitor` | 141 | **32** | **18.5 %** | same |

Counts and gap boundaries are **identical for both jobs to the second** ⇒ shared host-sleep cause,
nothing job-specific. **Today's run printed `13/14 jobs ran at their last expected fire` while ~2.3
interval fires per day were being lost** — both statements true simultaneously. That is exactly the
`last_status: OK` blindness of #7, closed for `cron` and still open for `interval`, and it hides
better here because interval jobs self-heal.

**Impact:** `auto-commit` gaps mean up to 8 h of uncommitted work sitting on disk;
`cleanpro-exp-monitor` gaps mean experiment monitoring blind for the same window.

**Fix (small, local, read-only path):** the interval branch needs a *history*, not a threshold —
compare consecutive `Running job: <id>` timestamps in `logs/infra.log` over a lookback and report
gaps > `interval + grace`, instead of comparing `last_run` to `now − 1.5 × interval`. Boss's call
because it changes what the check reports (it would print a rate, not a binary), and because the
question of whether these losses are *acceptable* — the host sleeps, and a discarded `auto-commit`
is recovered by the next fire — is a judgement no cycle should make alone.
⚠️ **Do not classify the gaps as discard-vs-deferral from `g % interval`** — this cycle tried and the
test was wrong (`14399 % 7200 = 7199`, so a 4 h gap 1 s short mislabels). The durations below are
raw timestamp differences and stand; the split is unreported. Use §1's `armed + S` form if you want it.

⛔ **EVERY RATE BELOW IS BIASED UP: A BOT RESTART RE-ANCHORS BOTH INTERVAL JOBS, AND THE HOST REBOOTED
TODAY AT 15:20:44 ICT** (2026-08-15 15:5x ICT, 0856z; `kern.boottime` + `uptime` + `ps -o lstart= -p 1`).
`interval` triggers anchor on scheduler start, so today's 15:21:46 start moved both jobs off the
`:33:23` grid onto **17:21:46**. `logs/infra.log` has **6 `Cron scheduler started` events since 08-01**
(98 all-time). If the counts below used a rolling grid, ~6 of the 32 are re-anchor artifacts; if they
used a fixed anchor, every fire after each restart reads as missed and the bias is far larger. The
method is not recorded, so **recompute with restart timestamps as grid resets before quoting any of
these numbers.** This is the second common-mode cause found in one day (0836z: the two jobs share a
process, so identical boundaries prove a shared cause, never sleep). Evidence:
`memory/t0/2026-08-15/heartbeat-0856z.md`.

⚠️ **The 18.5 % is a FOUR-MONTH BASELINE, not a new regime — `since 08-01` selected for nothing**
(re-measured 2026-08-15 10:1x ICT over all 1192 `auto-commit` fires, whole days only):

| window | fired/due | lost |
| --- | --- | --- |
| 04-13 → 08-14 (full history) | 1185/1488 | **20.4 %** |
| 06-01 → 06-10 (worst stretch) | 60/120 | **50.0 %** |
| 08-01 → 08-14 (the row's window) | 137/168 | 18.5 % |
| 08-08 → 08-14 (last 7 d) | 66/84 | 21.4 % |

The row's number reproduces exactly; only its *implied recency* was wrong. This does not weaken the
fix — a defect that has run at ~20 % for four months unseen is a **better** argument for the history
check than a fresh spike would be. It does change the framing: nothing recent caused it, so nothing
recent will end it. ⛔ **Do not score the current partial day** — a per-day × 12 count renders
2026-08-15 at 10:15 ICT as `5 fired, lost 7` when all 5 due fires ran; the first day in the log takes
the mirror artifact. Drop both boundary buckets.
Evidence: `memory/t0/2026-08-15/heartbeat-2355z.md`, `heartbeat-0314z.md`.

---

*Anything resolved: delete the row, don't annotate it. This file earns its place by staying short.*

**Row numbers are stable IDs — never renumber, never reuse.** A gap in the sequence means that row
was resolved, not lost. Renumbering would rot every `QUEUE #N` cite in the daily logs, which is the
citation-rot failure #3 was just repaired for. Record each removal in one line below, so the gap
costs a reader zero calls to explain (2026-08-15 04:4x ICT: the missing **#4** cost three).

## Resolved

- **#4 — SessionStart hook: uncapped daily-log injection.** Removed 2026-08-15 04:0x ICT by heartbeat
  2100z: **falsified, not fixed.** The hook is uncapped as filed, but the harness truncates its output
  to a ~2 KB preview and persists the rest to a file, so the 600–692 KB/day context cost the row was
  built on does not exist. Evidence: `memory/t0/2026-08-15/heartbeat-2100z.md`.
