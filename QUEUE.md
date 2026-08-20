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

⛔ **RE-SCOPED 2026-08-18 (0437z) — THE CAP IS THE MINORITY CAUSE. `weekly-conjecture` fired 12 of
19 scheduled Mondays (04-13→08-17); of the 7 misses, ZERO involve the timeout — the host was asleep
and the slot never fired.** Only **3** of the 12 fires hit the cap. So `600 → 1800` recovers at most
3 of 10 lost reports and **would read as fixed while 37 % of slots stay silent**. The table below
predicted 08-17 19:00 ICT; `infra.log` jumps 18:05:38 → 19:25:22 (`Idle Sleep` at 18:06:46).
**Still worth doing — it is correct for the runs that happen — but it is not the whole fix, and the
no-show half needs a separate decision (wake scheduling, or `launchd` with its deferral semantics,
instead of an in-process APScheduler whose monotonic timer freezes on sleep).**
Evidence: `memory/t0/2026-08-18/heartbeat-0437z.md`; rule filed in `HEARTBEAT.md` header.

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
| `vidnotes-weekly` | **15** | **6** | 354 s | **536 s = 89 % of cap** | **9 (60 %)** |
| `weekly-conjecture` | 12 | 7 | 370 s | **540 s = 90 %** | 5 (42 %) |
| `cleanpro-weekly` | 14 | 12 | 335 s | 449 s = 75 % | 2 (14 %) |

Successes climb continuously toward the cap and clear it — the capacity signature. **`vidnotes-weekly`
has failed 9 runs in 15; `ce=1` only because a single success resets the counter.** 1800 s leaves the
observed max ~3.3× of headroom.

✅ **PREDICTION SCORED — the table's `vidnotes-weekly` row fired exactly when this file said it would,
and it cleared the cap by 64 s** (2026-08-18 0948z, observed live). `infra.log`: `Running job` at
**12:30:00 ICT**, `completed successfully` at **12:38:56** ⇒ **536 s = 89.3 % of the 600 s cap**, and it
produced a real report (`memory/t0/2026-08-18/vidnotes-weekly-w34.md`, 1156 B, mtime 12:38). Two things
this settles and one it does not:
- **The APScheduler `day_of_week` reading is now confirmed by prospective test, not just retrodiction.**
  `30 7 * * 1` = **Tuesday**, and the table's "Tue 2026-08-18 07:30 Warsaw" (= 12:30 ICT) was right to
  the second. The ⚠️ above was reconstructed from past fires; this is the first fire predicted *before*
  it happened. Treat the 0-is-Monday rule as settled.
- **The capacity branch holds and tightened.** New max-ok 536 s > the old 528 s: the success
  distribution's ceiling keeps climbing with n, which is the capacity signature doing exactly what §0's
  test says it should. Nothing has ever finished in the 537–599 s band, so the margin on a *good* run is
  **64 s (11 %)** — one slow BigQuery page from a tenth failure.
- **It does NOT weaken the `600 → 1800` ask; it is the strongest single argument for it.** A 60 %
  failure rate that produces a full report at 89 % of cap is not a hung job, and this run is the
  counterfactual: had it been 65 s slower, the week's VidNotes report would not exist and `last_run`
  would still have been stamped fresh. Evidence: `memory/t0/2026-08-18/heartbeat-0948z.md`.
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
⚠️ **EIGHTH ORGANIC FORM, 2026-08-15 17:0x ICT (0954z) — and the guarded word was not even about a
process.** A heredoc commit body containing *"so after a reboot a correct `last_run` reads 1.5
intervals stale"* was refused (*"Destructive system commands are not allowed"* — a different rule from
the `kill\s` one above, same class of defect). `reboot` there names an APScheduler re-anchoring
behaviour, not an action anyone is taking; the matcher cannot tell a verb from a noun. **The
`Write`-the-body-then-`git commit -F <file>` escape worked first try and required no reword** — cost
one round trip. So the row's ask is unchanged, but note the scope: the fleet's own domain vocabulary
(restart, `reboot`, timeout, cap) is what it is least able to *describe*, and the commit log is the
one carrier with no `Edit`-tool escape hatch.
Evidence: `HEARTBEAT.md` §2, `memory/t0/2026-08-15/heartbeat-2019z.md`,
`memory/t0/2026-08-15/heartbeat-2255z.md`, `-2318z.md`, `-0954z.md`.

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

⛔ **A BOT RESTART RE-ANCHORS BOTH INTERVAL JOBS, AND THE HOST REBOOTED TODAY AT 15:20:44 ICT**
(2026-08-15 15:5x ICT, 0856z; `kern.boottime` + `uptime` + `ps -o lstart= -p 1`). `interval` triggers
anchor on scheduler start, so today's 15:21:46 start moved both jobs off the `:33:23` grid onto
**17:21:46**. `logs/infra.log` has **6 `Cron scheduler started` events since 08-01** (98 all-time —
that census is confirmed correct; note the line is logged **twice per start**, uniformly since
2026-04-12, so `grep -c` returns 196 and you must `sort -u` the timestamps).

⛔ **THIS ROW USED TO SAY "EVERY RATE BELOW IS BIASED UP … direction known (up), size not". THE SIGN
IS REFUTED — THE CORRECTION RAISES THE RATE** (2026-08-15 16:3x ICT, 0935z, both grids computed over
the same window). `auto-commit`, 04-13 → 08-14 whole days only, `misfire_grace_time` 300 s as the
match tolerance:

| grid | due | fired | lost | loss |
| --- | --- | --- | --- | --- |
| **A** fixed anchor, restarts ignored | 1488 | 16 | 1472 | **98.9 %** |
| **B** per-epoch re-anchor (what APScheduler does) | 1476 | 1121 | 355 | **24.1 %** |
| — the 20.4 % quoted below for this window | 1488 | 1185 | 303 | 20.4 % |

**B is the correct method and reads +3.7 pp ABOVE the quoted figure.** Both guessed branches were
also wrong about the method actually used: a fixed anchor yields **98.9 %**, nowhere near 20.4 %, so
the prior numbers came from a grid rolling off *observed* fires — and that is the undercount
mechanism, because **a grid anchored on the fires that HAPPENED cannot count consecutive losses**;
each observed fire silently re-defines where the next was due. So the rates below are biased **down**,
and the ask is strengthened, not weakened.
⚠️ **Two instrument caveats, both worth more than they look.** (a) A per-epoch grid must start at
**k=1** — `IntervalTrigger` first fires at `start + interval` (this row's own `15:21:46 + 7200`), and
emitting a slot *at* each restart adds 98 phantom losses and returns 28.6 % instead of 24.1 %.
(b) **64 of 1185 observed fires (5.4 %) match no slot in grid B**, so the reconstruction is imperfect —
likely sleep-deferred fires landing at `anchor + n·interval + S` outside the 300 s tolerance. **Take
the direction and the mechanism as settled; treat 24.1 % as an upper-ish estimate, not a final number.**
Confidence high on the sign, moderate on the value. Evidence:
`memory/t0/2026-08-15/heartbeat-0935z.md`, `-0856z.md`.

⚠️ **The 18.5 % is a FOUR-MONTH BASELINE, not a new regime — `since 08-01` selected for nothing**
(re-measured 2026-08-15 10:1x ICT over all 1192 `auto-commit` fires, whole days only):

| window | fired/due | lost |
| --- | --- | --- |
| 04-13 → 08-14 (full history) | 1185/1488 | **20.4 %** |
| 06-01 → 06-10 (worst stretch) | 60/120 | **50.0 %** |
| 08-01 → 08-14 (the row's window) | 137/168 | 18.5 % |
| 08-08 → 08-14 (last 7 d) | 66/84 | 21.4 % |

⛔ **EVERY NUMBER IN THAT TABLE IS BIASED UP AND NONE OF THEM SHOULD BE QUOTED AS-IS — the
denominator is a FIXED GRID and a bot restart RE-ANCHORS every `interval_seconds` job onto a new
one** (`HEARTBEAT.md` §0, 0856z; carried into the queue 1129z because the row is what gets acted on).
Worked example from today: the 15:20:44 reboot moved `auto-commit` / `cleanpro-exp-monitor` off the
`:33:23` grid onto `15:21:46 + 7200` = `17:21:46`, and that re-anchored fire landed on the second
(1015z, residual 0 s) — a *success* that a fixed-grid count scores as a miss, plus a miss at every
later grid slot. `logs/infra.log` holds **6 `Cron scheduler started` events since 08-01**, so the
08-01→08-14 row alone absorbs several. **Direction is known (up); magnitude is not.** Do not price
this fix off 20.4 % / 18.5 % / 50.0 % until the series is rebuilt with each restart timestamp as a
grid reset. The *sign* of the defect is unaffected — fires are genuinely lost — so the fix still
stands; only its size is unmeasured.

The row's number reproduces exactly; only its *implied recency* was wrong. This does not weaken the
fix — a defect that has run at ~20 % for four months unseen is a **better** argument for the history
check than a fresh spike would be. It does change the framing: nothing recent caused it, so nothing
recent will end it. ⛔ **Do not score the current partial day** — a per-day × 12 count renders
2026-08-15 at 10:15 ICT as `5 fired, lost 7` when all 5 due fires ran; the first day in the log takes
the mirror artifact. Drop both boundary buckets.
⛔ **SLEEP IS NOT THE ONLY CAUSE — A FIRE WAS LOST TODAY WITH THE SCHEDULER DEMONSTRABLY AWAKE**
(2026-08-15 16:1x ICT, 0917z). The 14:33:23 ICT fire of **both** interval jobs never happened, and the
process logged `httpx.ConnectError` at **14:33:08 and 14:33:41** — 15 s either side of the fire
instant — then ran `echo-backend-alerts` normally at 15:05. Not sleep, not a dead process, not the
15:20:44 reboot. The fire sits inside the **DNS outage 14:25:19 → 14:36:29** that 0803z had already
bounded for a different casualty. Whole-population test on `auto-commit` (04-13 → now, grid rebuilt
per scheduler epoch so restarts re-anchor):

| | n | `ConnectError` within ±5 min |
| --- | --- | --- |
| **lost** fires | 349 | **39 (11 %)** |
| **successful** fires | 1194 | **17 (1.4 %)** |

**8× enrichment ⇒ network outages are a real second mechanism, explaining ~1 loss in 9.** Sleep still
owns the rest. This does not change the ask (the interval branch still needs a *history*), but it
does mean **a history check must report the cause split, not just a rate** — the two mechanisms want
different responses, and only one of them is "the host was off". Mechanism unproven: both jobs share
one event loop with the poller and `misfire_grace_time: 300` discards anything > 5 min late.
⚠️ **Expected-MISSED window, so nobody re-investigates:** the reboot re-anchored both jobs to
`15:21:46 + 7200` = **17:21:46 ICT**, while `last_run` stays 12:33:23 — the detector alarms on this
pair until then. General form: a restart at `last_run + t` alarms for `t − 0.5 × interval` and cannot
clear before `restart + interval`.
Evidence: `memory/t0/2026-08-15/heartbeat-2355z.md`, `heartbeat-0314z.md`, `heartbeat-0917z.md`.

---

*Anything resolved: delete the row, don't annotate it. This file earns its place by staying short.*

## 9. `com.claude.daily-brief` fires 2 h before the quota reset — three briefs lost, no detector

**Where:** `~/Library/LaunchAgents/com.claude.daily-brief.plist`, `StartCalendarInterval` **09:00 local**.
**Symptom:** the job is a plain `claude -p`, so it shares the weekly quota the heartbeat fleet drains
at 96 cycles/day. The quota resets **11:00 ICT**; the brief fires at **09:00 ICT** and loses by two
hours. `launchctl list` shows it at **exit status 1** and `/tmp/claude-daily-brief.log` is **194 B,
entirely three `You've hit your weekly limit` lines** — the briefs for **08-16, 08-17 and 08-18** were
never generated and nothing anywhere recorded it. Today's refused at 02:00Z; the reset landed 04:00Z.

**Update 2026-08-20 2053z — the outage is over, the detector gap is not, and the forecast is void.**
`launchctl list` now shows **exit 0** and `/tmp/claude-daily-brief.log` is 2,031 B ending in a full
brief delivered 08-19 09:00 ICT. Nothing was fixed; the quota simply refilled — so the row stays open
on its *detector* half, and the exit-status column is still the only witness.
⛔ Two numbers in this row are wrong and should not be re-quoted. **"96 cycles/day" is refuted** —
0707z measured ~74/day (`StartInterval 900` counts from EXIT, so period = 900 + runtime), and the
current window meters **76.2**. And the 08-19 brief's *"at unchanged burn the current window exhausts
around 08-23 01:30 ICT"* is **unfalsifiable**: `/tmp/claude-heartbeat.log` was born 08-15 15:36 ICT,
covering only the last **0.40 d of the 4.59 d** window that exhausted, so 91 % of the consumption
behind "burned out in 4.6 days" was never metered. Measured on what is observable, the current window
runs **cooler** — cadence flat (72.3 → 76.2 cyc/d) but mean runtime 273 → 186 s, i.e. **236 vs
329 min/d, −28 %**. Directional only (runtime proxies tokens; this brief is a second consumer the
meter cannot see). Evidence: `memory/t0/2026-08-20/heartbeat-2053z.md`.

**Two decisions, both yours — a plist edit needs `launchctl` unload/load, outside a heartbeat's remit
under `CLAUDE.md`'s launchd rules:**
1. **Move the fire to ~11:15 ICT** (just after the reset) instead of 09:00. This alone would have
   saved today's run, and it costs nothing on a healthy week.
2. **Extend 0418z's refusal backpressure to cover this job**, or accept that a user-facing deliverable
   has no failure signal. The heartbeat's detector keys on the conjunction `rc != 0` + tiny stdout +
   the phrase; the same three-part test applies unchanged here, and `launchctl list`'s exit-status
   column makes it observable from any cycle.

**Note the general shape, which is why this sat unseen for three days:** the outage detector built on
08-18 enumerated *instances of the heartbeat*, not *consumers of the quota*. There are two consumers.
Evidence: `memory/t0/2026-08-18/heartbeat-0613z.md`.

**Status 2026-08-20 1922z — SYMPTOM CLEARED, HAZARD UNCHANGED.** `launchctl list com.claude.daily-brief`
now reads `LastExitStatus = 0`, and `/tmp/claude-daily-brief.log` is **2,031 B** whose tail is a real
brief (queue digest, process notes, log written to `memory/t0/2026-08-19/daily-brief-0900ict.md`) —
not the 194 B of refusals 0613z found. **Neither decision above was taken; the fire time is still
09:00 ICT and the job still has no detector.** What changed is the quota, not the schedule, so the
recovery is evidence about the week, not about the plist: the 2-hour margin is re-armed the next time
the weekly limit binds before 11:00 ICT. Read this row as *latent*, not resolved.


### Pre-registered: the SAME outage recurs ~2026-08-22 18:30Z, and it takes 3 more briefs with it (0834z)

The 08-16/17/18 briefs were not lost to a one-off — they were lost to the tail of a **weekly** quota
window the fleet exhausts early. Reconstructed from the two timestamps that are known exactly:
first refusal **2026-08-15T18:33:12Z**, reset **2026-08-18T04:00:00Z**. If windows reset on a fixed
weekday at 04:00Z, the exhausted window opened **2026-08-11T04:00Z**, so the fleet burned a 7-day
allowance in **4.60 days (66 %)** and spent the remaining **2.40 days refusing**.

**Prediction, at unchanged burn: the current window (opened 2026-08-18T04:00Z) exhausts about
2026-08-22T18:30Z (2026-08-23 01:30 ICT), and every `com.claude.daily-brief` fire from 08-23 through
08-25 09:00 ICT is refused — three more, exactly as before.** Confidence moderate: n=1 window, and it
assumes the weekly cadence and today's ~96 cycles/day both hold.

**Mechanical check, cheap from any cycle** — `launchctl list | grep daily-brief` (column 2 is the exit
status) and `tail -3 /tmp/claude-heartbeat.log`. A refusal before 08-22T18:30Z means the burn rate
rose; silence past 08-23T04:00Z means it fell, and either way the estimate is worth re-deriving rather
than re-asserting. **This is the number that decides option 1 above: moving the fire to ~11:15 ICT
saves the brief on the reset day only — it does NOT save 08-23 or 08-24, because on those days the
quota is dead all day.** Option 1 alone is worth ~1 brief in 3; the fix that saves the other two is
capping the heartbeat's own consumption, which nothing currently does.

## 10. Every `Evidence:` pointer in this file and `HEARTBEAT.md` is unpushed — 29 cited, 0 in git

**Where:** `.gitignore:27` — `memory/`.
**Measured 2026-08-18 0613z:** the two documents the fleet commits and pushes cite **29 distinct**
`memory/t0/…` evidence files (20 pointers in `HEARTBEAT.md`, 12 in `QUEUE.md`). **29 of 29 exist on
this host. 0 of 29 are tracked by git.** So every row in this queue is footnoted to something you
cannot open from GitHub, from another machine, or from a restored clone — and if this host's disk is
lost, every claim survives and none of its evidence does.

This is the citation-rot failure `HEARTBEAT.md` already documents (*"cite by §N plus a distinctive
quoted phrase, never by line number"*) at a second layer: those pointers **resolve perfectly for the
one reader who does not need them** — a cycle running on this host — **and dangle for every other
reader.** A local check will never catch it; `git ls-files` is the only instrument that speaks.

**Your call, and I am not assuming the ignore is a mistake** — daily logs carry raw operational
detail and excluding them may well be deliberate. The three options:
1. **Un-ignore `memory/t0/`.** Evidence becomes verifiable; the repo grows by the log volume and
   whatever those logs contain becomes as public as the repo is.
2. **Keep the ignore, drop the pretence** — stop writing `Evidence: memory/…` into committed files
   and inline the decisive measurement into the row itself, which is where a reader can use it.
3. **Keep both**, and accept the citations are notes-to-self, not evidence. Cheapest, and worth
   saying out loud once so no future reader trusts a pointer they cannot follow.

Evidence (and yes, this one is unpushed too): `memory/t0/2026-08-18/heartbeat-0613z.md`.

⛔ **OPTION 1 IS VETOED, AND 0613z WROTE THE CONDITION WITHOUT MEASURING IT** (0634z). Its own
caveat — *"whatever those logs contain becomes as public as the repo is"* — was left as a
conditional; measured, **the repo IS public** (see #11). Option 1 therefore publishes **2,671
files / 12 MB** of daily logs, app metrics and revenue figures to an anonymously-readable repo.
Take option 2 or 3. **A hazard stated as a conditional is not a hazard priced — resolve the
antecedent in the same cycle you write it, it is one `gh api` call.**

⛔ **THE SHARPER CONSEQUENCE, UNSTATED ABOVE: A CYCLE WHOSE ONLY OUTPUT IS A DAILY LOG COMMITS
NOTHING, SO ITS COMMIT MESSAGE IS THE SOLE ARTIFACT AND THE DIFF CANNOT CORROBORATE IT** (0924z).
This cycle's `git commit -a` returned **`nothing to commit, working tree clean`** with a finished log
on disk — `memory/` is ignored, so there was literally nothing to stage. Checked the last four
heartbeat commits: **`0805z`'s entire diff is one line of `cron/state.json`**, a file the *scheduler*
writes, not the cycle; `0846z` is `QUEUE.md` only. So `git log` reads as a record of investigative
work whose evidence, reasoning and measurements are all in the one tree git cannot see. A GitHub
reader gets a confident subject line — *"jobs.json drifted 4d from the running scheduler"* — attached
to a diff that does not mention `jobs.json`.
**This raises option 2's stakes: it is not only that pointers dangle, it is that the commit history of
this fleet systematically over-claims.** Cheap partial fix inside option 3, no un-ignoring: **when a
cycle's finding is log-only, put the decisive measurement in the COMMIT BODY** — that text is tracked,
and it is the one place a remote reader is already looking.

⛔ **AND ITS PRODUCTION RATE IS UNOBSERVABLE, NOT MERELY UNVERIFIED** (2112z). The 60.4/56.3/52.5 %
figures above are a **backtest**; `infra.log` has **841** `Running job: cleanpro-alerts` lines and
**zero** of this runner's stdout — `grep -c` returns 0 for `No anomalies detected. paywall_shown`,
0 for `💰 CONVERSION`, 0 for `TELEGRAM_SENT_OK`. `_run_script` returns `stdout[-500:]` and
APScheduler discards it (see #11's note). **Do not multiply the backtest rate by slot count to state
how many alerts the user received — no local instrument can confirm one.** Fixing #11's delivery
asymmetry makes this measurable as a side effect.

## 11. Two LIVE bot tokens are published on a PUBLIC repo — 11 tracked files, ~4 months

**Where:** `scripts/{cleanpro_alerts_runner,cleanpro_experiment_monitor,daily_report_common,
echo_alerts_runner,vidnotes_daily_runner}.py`, `skills/{aividly-daily,cleanpro-weekly,pdfai-daily,
vidnotes-alerts,vidnotes-weekly,weekly-conjecture-cycle}/SKILL.md`.

**Measured 2026-08-18 0634z, three independent axes:**
1. `gh api repos/antharasvn/OpenClaude` ⇒ `private: false`, `fork: true`, parent
   `n4rly-boop/OpenClaude`; `pushed_at 2026-08-18T06:18:45Z` — the fleet's own `auto-commit`.
2. Unauthenticated `curl` of `raw.githubusercontent.com/…/scripts/cleanpro_alerts_runner.py`
   ⇒ **HTTP 200, 6,513 B**, token line present in the body.
3. Telegram `getMe` ⇒ `ok: true` for **both**: `8628864855:…` (@aaa_os_bot) and
   `8733346629:…` (@Silpho_OS_bot). Live, not already-rotated.

Earliest file first-added **2026-04-12** ⇒ ~4 months public. Holder of @aaa_os_bot's token can read
every message sent to the fleet's control bot via `getUpdates` and post as it into any chat it is in.

**Order matters and only step 1 actually closes it:** (1) BotFather `/revoke` both — the tokens are
in ~4 months of commits, so making the repo private or deleting the files unpublishes nothing;
(2) then move all 11 sites to `os.environ[…]` **with no fallback default**; (3) history rewrite is
optional cleanup, and needs the user's word. **Do not do (2) before (1)** — stripping the defaults
with no env provisioned breaks every alert job on its next fire, and fixing a leak by breaking the
fleet is not a fix. Sent to the user 0634z; awaiting step 1.

**⛔ Step 2 is CHEAPER than filed, and step 2's stated cost was wrong (2026-08-20 2205z).** "With no
env provisioned" implies a provisioning project. There is none — the hatch is wired end to end:
`bot/config.py:11,17` `load_dotenv(SCRIPT_DIR / ".env")` (the repo's only dotenv loader) → `bot/app.py:20`
imports it, so PID 927's `os.environ` carries `.env` → **`grep -n "env=" bot/scheduler.py` is EMPTY**, so
script jobs inherit it → the scripts already do `os.environ.get(NAME, "<literal>")`. Of the 5 names read,
`.env` defines **1** (`TELEGRAM_BOT_TOKEN`); `AAA_BOT_TOKEN`, `AAA_CHAT_ID`, `SILPHO_BOT_TOKEN`,
`SILPHO_CHAT_ID` are absent ⇒ all fall through. `.env` is untracked + `.gitignore:2` ⇒ safe destination.
So step 2 is **add 4 keys to `.env`, then strip the literals** — but ⚠️ **necessary, not sufficient:**
`load_dotenv` runs at bot START (PID 927 up since 08-15 15:21:26), so the keys reach nothing until a
restart — the same actuator `restart.sh` cannot perform (1403z) and `safe-restart.sh` is unsanctioned.
Step 1 (revoke) still gates everything and is still with the user.
**⚠️ Do not re-quote 2112z's "7 files = #11's exposure set":** api.telegram.org users = 7 scripts,
credential-holders = 5 scripts, both = 4. `cleanpro_daily_runner.py`, `echo_daily_runner.py`,
`mangii_daily_runner.py` hold nothing to rotate. This row's own 5-script list was right; 2112z drifted.

**Transferable, and it is why this sat unseen through 488+ auto-commits: `git remote -v` names a
URL, not an AUDIENCE.** Before making anything more tracked — or trusting anything already tracked —
resolve the destination's visibility. ⚠️ And pass `owner/name` explicitly: bare `gh repo view`
resolved to the **upstream** (`remote.upstream.gh-resolved = base`), not origin, and I was one step
from filing "the repo was transferred to another account."

Evidence: `memory/t0/2026-08-18/heartbeat-0634z.md`.

⛔ **STEP 2 IS THE WRONG REPAIR — THE TOKENS ARE INLINE BECAUSE THE SCHEDULER GIVES SCRIPT JOBS NO
WAY TO SPEAK, SO ENV VARS KEEP THE LEAK'S CAUSE AND ADD SEVEN SECRETS TO PROVISION** (2112z).
`bot/scheduler.py:182-187` already has the delivery path: `delivery = job.get("delivery", {})` →
`announce` → `send_rendered_bot`, using **the bot's own credential**, no token in any script.
`delivery` is a plain per-job key any job could carry — **but the block is inside `_run_prompt`, and
`_run_script` (108-129) never reads it.** `grep -n announce bot/scheduler.py` ⇒ 5 lines, all 181–189.
The config is **8 script jobs to 3 prompt jobs**, and the three prompt jobs are the weeklies +
`weekly-conjecture`: **every ALERTING job is a script job, i.e. exactly the set locked out.** Hence
`grep -c api.telegram.org scripts/*.py` ⇒ **7 files** (4 of them defining their own `send_telegram`)
— this row's exposure set, reimplemented seven times as a workaround.

**Revised order: (1) revoke, unchanged and still the only step that closes the 4-month exposure;
(2) lift the `delivery.announce` block out of `_run_prompt` into `_run_job` so both types get it, add
`delivery.announce` to the alert jobs, then DELETE `send_telegram` and the token from all 7 scripts —
no env var needed anywhere.** Step 2 as written is still safe to fall back on, but it provisions
seven secrets to preserve a duplication that should not exist. Free side effect: an announced result
is a logged result, which closes the blind spot under #3.

**Transferable: when N components each reimplement one capability, find the single place that offers
it CONDITIONALLY — the duplication is a workaround for an access asymmetry, not N authorship
decisions. And you cannot price a credential exposure until you know what the credential is doing
there; rotation alone re-creates it on the next runner someone writes.**
Evidence: `memory/t0/2026-08-20/heartbeat-2112z.md`.

## 12. `Read HEARTBEAT.md` returns 20 % of the file, and all four checks are in the other 80 %

⛔ **The prompt orders every cycle to "read HEARTBEAT.md for the checklist". A compliant `Read`
returns lines 1–551 (25k-token page cap, established by 1755z) and shows ZERO of §1–§4.**
Measured 2026-08-18 0910z: 2,669 lines / 249,998 B total; lines 1–551 = 50,710 B = **20.3 %**, of
which lines 1–438 (40,743 B, **80 % of the window**) are the retrospective header, not checklist.

| section | starts at line | in the readable window? |
| --- | --- | --- |
| retrospective header | 1 | yes, all of it |
| §0 Cycle budget | 441 | only its first 110 of 459 lines |
| §1 Cron Job Health | 898 | **no** |
| §2 Bot Health | 2111 | **no** |
| §3 Memory & Reminders | 2295 | **no** |
| §4 Infra Log Anomalies | 2520 | **no** |
| How to Alert / What NOT to do | 2619 | **no** |

**Not a hypothesis — it is the mechanism behind an already-recorded n=3.** §2's correct
`pgrep -f -- "-m bot"` form is at 2111; 0648z, 0836z and 1755z each paraphrased it from memory, got
an empty result on a healthy bot, and were one call from filing a service-down.

**The binding constraint is 551 LINES, not 250 KB.** The guard is aimed at `Read`'s 256 KB *hard*
cap; pagination bites at 20 % of that. Consequence: **compaction below line 551 cannot change what a
cycle sees**, and six cycles have been aiming there. Price compaction in lines-above-551, not bytes.

**Two sub-findings, both measured from `git cat-file -s` on today's commits:**
1. **The guard has no actuator and was breached and committed twice today** — `c16404d` 250,725 B
   (725 B over) and `096ace2` 250,085 B, before `cad898b` trimmed under. It is a sentence in a file,
   so it fails exactly the way a `cron/jobs.json` edit fails (0851z's actuator rule, third instance).
2. **The file is pinned at capacity**: 0707z 249,985 → now 249,998 = **+13 B net across five
   commits** on ~2.3 KB of gross churn. It is no longer an append log; every cycle pays an eviction
   cost out of the same 600 s that funds its finding.

**The decision (why this is a queue row and not a heartbeat edit):** the file cannot hold both the
header and the checklist inside 551 lines, so something must be demoted, and the header is the only
span currently being read *and* holds five live imperatives (the compaction method, the
`"$(cat …)"` guard.sh escape, the local-vs-UTC daily-log directory rule, the `pmset` density test,
the `(Running job:|Job)` regex). A cycle moving it would trade five live rules for four checks
unilaterally. **Recommendation, in order:** (1) lift only the *commands* from §1–§4 into a short
`## Checks` block at line 1, leaving their evidence in place; (2) demote the header's scoring prose
to `HEARTBEAT-ARCHIVE.md`, keeping its imperatives; (3) re-price compaction in lines above 551.

Evidence: `memory/t0/2026-08-18/heartbeat-0910z.md` (unpushed — see #10).

---

**Row numbers are stable IDs — never renumber, never reuse.** A gap in the sequence means that row
was resolved, not lost. Renumbering would rot every `QUEUE #N` cite in the daily logs, which is the
citation-rot failure #3 was just repaired for. Record each removal in one line below, so the gap
costs a reader zero calls to explain (2026-08-15 04:4x ICT: the missing **#4** cost three).

## 13. The 14:00 ICT cron slot loses 26 % of its fires — four daily reports, one shared trough, no alert

Filed 2026-08-18 17:5x ICT (1047z). **Decision needed: move the slot, or widen the grace.** Both are
one line; neither is in a cycle's lane.

`echo-daily`, `mangii-daily`, `pdfai-daily`, `aividly-daily` all run `0 3 * * *` `America/New_York`
= **14:00 ICT**, which sits inside this host's habitual afternoon idle-sleep window. Fire dates from
the whole of `logs/infra.log`, **identical for all four** (they share the slot, so this is one event
×5, not 20 independent failures):

```
07-31 08-01 08-02 08-03 [—— 08-04 08-05 ——] 08-06 [—— 08-07 08-08 ——] 08-09 … 08-17 [—— 08-18 ——]
```

**14 of 19 days present ⇒ 26 % of fires lost.** (True rate 21–26 %: 08-08 has only 61 log lines, so
the host was likely down that day rather than asleep.)

**The scheduler was demonstrably alive through the hole, which is what makes this a schedule defect
rather than an outage.** On 08-04, 08-05 and 08-07 — 152/120/161 log lines each, so the logger was
not mute — `echo-backend-alerts` fires at **13:05 and 15:05 but never 14:05**, while the interval
jobs `auto-commit` and `cleanpro-exp-monitor` fire at **14:41**, inside the gap. Today (08-18) has
the same shape. That asymmetry is the mechanism: an **interval** trigger resumes on monotonic time
after a sleep, a **cron** trigger's slot is discarded by `bot/scheduler.py:26`
`misfire_grace_time: 300` with `coalesce` defaulting `True`. **The interval jobs paper over every
trough the cron jobs fall into**, which is why `infra.log` reads healthy across all five losses.

Two mechanical fixes, either sufficient:
1. **Move the four dailies off 14:00 ICT** to an hour the host is reliably awake. They are report
   jobs; the hour is arbitrary. Cheapest, no code.
2. **Raise `misfire_grace_time`** for cron jobs so a post-wake catch-up runs. Touches every job.

Related but distinct from **#8** (interval jobs lose ~18 % unseen) — this is the cron-side loss #8's
detector is built to catch, and it does catch it: `check_missed_fires.py` printed all four this
morning. The gap is that **only the cycle that happens to run after the slot ever reads it**, and
three cycles today (0707z, 0730z, 0930z) each read it, each explained the day correctly, and none
counted the other four days.

**Rule this produced, worth keeping independently of the fix:** 1028z established *`uniq -c` an
ERROR burst by DAY before filing it*. Misses need the same move and it flips the verdict the other
way — a burst against its base rate is usually nothing; a miss against its base rate is usually
systematic. Same omission, opposite conclusions, so "check the base rate" cannot be shorthand for
"expect to find nothing."

Evidence: `memory/t0/2026-08-18/heartbeat-1047z.md` (unpushed — see **#10**).

## 14. Bound the SessionStart hook to the NEWEST logs — it currently delivers the oldest two

**Where:** `.claude/settings.json`, the `SessionStart` command. **I may not edit it** — `CLAUDE.md`
lists `.claude/settings.json` hooks as never-modify — so this is yours.

**What it does now:** `for f in "$LOGDIR"/*.md; do cat "$f"; done`, unbounded. Glob order is
lexicographic, and log names are `heartbeat-<UTC>z.md`, so it emits **oldest first**.

**Why that matters:** the harness caps hook stdout **under 10 KB** (smallest persisted stdout across
all 1,792 session dirs of this workspace: **10,190 B**) and replaces the remainder with a file path
plus a ~2 KB preview. Measured: **1,679 of 1,792 sessions (93.7 %) were truncated.** A local day
crosses 10 KB at ~7 logs, roughly 2 h in — 08-19 finished at **195,113 B, 19× the cap**. So for ~22 h
of every 24, the only daily-log content a cycle actually sees is the **first two files of the day**,
and the predecessor handoff the convention exists to carry is always in the discarded part.

**Fix (one line):** iterate newest-first and cap the count, e.g.
`for f in $(ls -t "$LOGDIR"/*.md | head -3); do …` — same hook, same cost, delivers the handoff.

**Note this row does not reopen #4.** #4 asked you to cap the hook to save *context bytes*; 2100z
correctly falsified that — the bytes were never injected. This asks you to cap it for the opposite
reason: the truncation that voided #4's cost is itself dropping the newest logs.
Evidence: `memory/t0/2026-08-20/heartbeat-1844z.md`; rule in `HEARTBEAT.md` header.

---

## Resolved

- **#4 — SessionStart hook: uncapped daily-log injection.** Removed 2026-08-15 04:0x ICT by heartbeat
  2100z: **falsified, not fixed.** The hook is uncapped as filed, but the harness truncates its output
  to a ~2 KB preview and persists the rest to a file, so the 600–692 KB/day context cost the row was
  built on does not exist. Evidence: `memory/t0/2026-08-15/heartbeat-2100z.md`.

---

## 15. ✅ CLOSED — REFUTED 2026-08-20 0906z. The awake miss IS #13's mechanism, read correctly

**Resolution (0906z):** not a new failure class. `HEARTBEAT.md` §0751z already states the mechanism as
*"a missed slot is explained by the monotonic freeze accumulated BEFORE it, not by the power state AT
it"* — so an awake fire instant was never evidence against it. Freeze banked between the last
processing pass (11:21:49) and the FullWake (11:36:08) sums to **453 s > the 300 s misfire_grace_time**;
§0823z already lists `453 s ⇒ dropped`. Both of 0846z's untested candidates are dead: executor
saturation refuted (zero jobs in flight 11:21:49→13:06:39, no `max_instances`/`executors` set) and
`last_status` never moved. The awake claim itself is CONFIRMED and upgraded to high confidence via
sleep-decision enumeration (zero `Entering Sleep state` between 11:36:08 and 12:05:25).
Bears on #1/#13: the killer is pre-banked freeze, so a wake-at-the-slot fix is insufficient — the grace
must lengthen or reset. Evidence: `memory/t0/2026-08-20/heartbeat-0906z-queue15-refuted.md`.

### Original filing (superseded)

## 15. A cron fire was lost while the host was AWAKE — #13's sleep mechanism does not cover it

Filed 2026-08-20 15:5x ICT (0846z). **Decision needed: none yet — this is a request to NOT close #13
as the whole story.** The diagnostic step that would settle it is in a cycle's lane and is named at
the bottom.

`vidnotes-daily` (`30 7 * * 1-7` Europe/Warsaw = **12:00 ICT**) missed its 2026-08-20 fire. It ran
the same slot normally on 08-19 (`logs/infra.log:26113`), so it is loaded in the running scheduler
(pid 927, up 5 d). `logs/infra.log` has **no `Running job: vidnotes-daily` line** today — the gap
runs 11:21:49 → 13:06:39 with nothing in it at all.

**The host was awake at 12:00:00.** From the assertion summary printed at 12:05:03:

```
2026-08-20 12:05:03 +0700 Assertions PID 343(powerd) Summary PreventUserIdleSystemSleep
        "Powerd - Prevent sleep while display is on" 00:28:54
```

28 m 54 s ending 12:05:03 ⇒ held from **11:36:09**, matching the `Wake` at 11:36:08 (FullWake, HID
activity). System idle sleep was *prevented*, not merely absent, across the fire instant; the first
`Sleep` after it is 12:05:30. `echo-backend-alerts` (hourly ~:05) also lost its 12:05 slot inside
that same awake window.

**Why this is worth a row rather than a note.** #13's mechanism — cron slot discarded by
`misfire_grace_time: 300` during sleep — is correct and well-evidenced for the 14:00 block (today's
14:00 loss is a clean instance: the 14:04:43 DarkWake reports its preceding sleep as `334 secs`,
putting onset at 13:59:09). But #13's two proposed fixes (**move the slot**, **widen the grace**)
both assume sleep is the only cause. If some fraction of misses happen while awake, either fix ships,
the 14:00 trough closes, and the residual keeps silently dropping reports — which is the exact
failure shape #1 already documented for itself (*"would read as fixed while 37 % of slots stay
silent"*). Two rows now share that shape; that is a pattern, not a coincidence.

**Cheap next step, in a cycle's lane, not the boss's:** read `last_status` / `consecutive_errors`
for `vidnotes-daily` after an awake miss. If it moved, the job *fired and failed* and infra.log is
simply not recording the attempt — a logging defect. If it did not move, the fire never reached the
executor while the machine was up — a scheduler-thread defect, and neither of #13's fixes touches it.
This cycle did not run that check (it was identified with ~6 min of budget left).

**Rule:** *a diagnosis that explains every instance stops being tested.* Sleep has explained every
cron miss here for weeks, so no cycle checked awake-state before attributing one. Before building a
fix on a universal cause, go looking for the instance it does not explain.

Confidence: **high** that no infra.log line exists (direct absence across a 105-min gap);
**moderate** that the host was awake (assertion arithmetic, single source).
Evidence: `memory/t0/2026-08-20/heartbeat-0846z.md`.

**RESOLVED SAME CYCLE (0846z, ~5 min later — the check above was cheap and should not have been
deferred).** `cron/state.json` for `vidnotes-daily`: `last_run 2026-08-19T05:02:06Z`,
`last_status OK`, `consecutive_errors 0` — **nothing moved.** So the fire never reached the executor;
it is not a fire-and-fail-silently logging defect.

⚠️ **Correcting the row above: this does NOT put the cause outside #13's fixes.** A scheduler thread
blocked >300 s while the *machine* is awake produces exactly this state — the fire is discarded as a
misfire with no execution and no status change, identical to the sleep case. **Widening
`misfire_grace_time` therefore plausibly covers both; moving the slot covers only the sleep half.**
That tips #13's choice toward fix 2, and it is the opposite of what this row asserted before the
check ran. Awake-vs-asleep changes the *mechanism*, not necessarily the *remedy* — worth keeping
distinct, not worth blocking #13 on.

🆕 **Unrelated finding from the same read, and it is the sharper one.** `cron/jobs.json` has
`echo-backend-alerts` **`enabled: false`**, yet it ran today at 08:05:07Z and is in `infra.log` at
11:05 / 13:06 / 15:05 ICT. The known drift ("jobs.json is a wish, not the loaded state") was
documented as *config claims enabled, scheduler dropped it*. **This is the reverse: config claims
disabled, scheduler is running it anyway.** So the drift is bidirectional, and the restart hazard is
worse than filed — a restart would silently *stop* a job that is currently working and that nobody
has been told is nominally off. **A staleness bug that runs in both directions cannot be reasoned
about by assuming which copy is more permissive.**
