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

**Evidence it is a capacity limit, not a hang:** weekly-job successes climb continuously toward the
cap (top two clear it by 72 s and 0 s) — the opposite signature to the heartbeat's own runtimes,
which cluster at ~40 % of their cap. `HEARTBEAT.md` §1 lines 798–875.
**Note:** this reasoning applies to `:163` only. The identical-looking `gtimeout 600` on the
heartbeat itself is the *hang* branch — raising **that** cap would only let each hang burn longer.

## 2. `cleanpro-daily` HANGS on ~13 % of runs — and the cap is *not* the problem

**Where:** `scripts/cleanpro_daily_runner.py` (cap at `bot/scheduler.py:120` — **leave it at 300**).
**Superseded** the previous "9 % margin, currently passing" framing, which was built on a single
sleep-contaminated sample. Settled 2026-08-15 03:0x ICT by catching the live 03:00 run (**138 s**,
S = 0) and then reading the whole population out of `logs/infra.log`:

| successes (s) | 136, 121, 125, 112, 127, 122, 137, 154, 118, 139, 138, 138 → **median ≈132, max 154** |
| --- | --- |
| failures | **2, both at exactly 300 s** (07-30, 08-13), `timed out after 5 min` |

Successes sit at **44–51 % of the cap** with a **146 s dead zone** below it; nothing has ever
finished in 155–299 s. By the fleet's own successes-vs-cap test (`HEARTBEAT.md` §0 line 116) that is
the **hang** signature, not capacity — so **raising 300 would recover nothing and let each hang burn
longer**. The prior 273 s figure was the 08-14 run, the one the host slept 734 s inside
(`Dark Wake Thermal Emergency`); it is 2× the median and the only reading near the cap.

**ANSWERED 2026-08-15 03:4x ICT — and the guess in this row was wrong.** It read *"network I/O with
no per-request timeout is the obvious candidate."* There **is** a per-request timeout; it is **twice
the job's whole budget**, which is worse than none because it answers the grep:

| layer | value | source |
| --- | --- | --- |
| scheduler kills the script | **300 s** | `bot/scheduler.py:120` |
| every `bq query` is allowed | **600 s** | `scripts/daily_report_common.py:48` |
| generic `run()` default | **300 s** | `scripts/daily_report_common.py:31` |

**The inner timeout is unreachable** — at 600 s inside a 300 s cap no query can ever time out; the
outer kill always wins, and `run()`'s default *equals* the cap so it cannot fire in time either. The
process dies mid-flight with no error and **no indication which query stalled**. ⚠️ **That is TWO
causes, not one — fixing this timeout alone leaves the failure silent. See #6:** `bot/scheduler.py`
also discards the script's stderr on the timeout path, so even a runner that *did* print a
diagnostic would lose it. This predicts the
distribution above better than "hang" does: past ~168 s nothing can interrupt a slow query before
300 s, so runs land at ~132 s or at exactly the cap, never in the 146 s dead zone. A true wedge and
a merely slow query are indistinguishable from outside.

**The actual ask (one line, but not a heartbeat's call):** set `daily_report_common.py:48` to
`timeout=120` — strictly below the outer cap, leaving room to catch the raise, report the failing
SQL, and still finish inside 300. **It is a shared module behind six live jobs** (`cleanpro`, `echo`,
`mangii`, `pdfai`, `aividly`, `vidnotes` daily runners), first firing 03:00 ICT, which is why no
cycle has applied it. `cleanpro` merely surfaced it first — it makes the heaviest queries.
Minor, same file: `cleanpro_daily_runner.py:447,451` (heatmap + `curl`) have no timeout at all, but
run *after* `send_telegram` at `:439` and so cannot cost the report.
Evidence: `memory/t0/2026-08-15/heartbeat-2041z.md`.

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
⚠️ **First ORGANIC trip, 2026-08-15 06:2x ICT (2318z):** `echo "=== heartbeat skill dir ==="`, inside a
routine `ls` batch, was refused as a process kill. All prior evidence on this row came from deliberate
probes; this is the first record of the bug hitting a cycle doing unrelated work. Cost was one round
trip and a reword (~15 s) — the point is the **base rate**, not the cost. No new ask; the `\b` patch
above is still the whole fix.
Evidence: `HEARTBEAT.md` §2, `memory/t0/2026-08-15/heartbeat-2019z.md`,
`memory/t0/2026-08-15/heartbeat-2255z.md`, `-2318z.md`.

## 6. `_run_script` throws away stderr on timeout — the fix is already written 45 lines below it

**Where:** `bot/scheduler.py:119-123`. **Blocks nothing; unblocks #2's other half.**

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
    _, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)  # ← drains it
    tail = stderr.decode(errors="replace").strip()[-300:]
```

`communicate()` never returns on the timeout path, so on the script path everything the runner
printed before the kill dies with the process. The prompt path's own comment states the hazard
exactly: *"the only prompt-job failures that ever need diagnosing are the ones that leave no
diagnostics at all."* That is precisely `cleanpro-daily`'s two 300 s failures (07-30, 08-13).

**Patch:** apply the `:169-175` drain to `:121-123` — same 10 s inner wait, append the tail to the
raised message. Diagnostics only: no cap changes, no job behaviour changes, no shared module.
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
the fire. The CleanPro report for Aug 4–11 does not exist and nothing raised a flag; the gap will
read 14 days when 08-18 fires.

**Why it is invisible, and why it is #1's mirror:** `last_status` answers *"did the last run
succeed?"*, never *"did it run?"* #1 is the opposite corner of the same hole — a job that stamps a
**fresh** `last_run` while producing **no report**. One field cannot answer both questions, and
today the fleet checks only that field.

⚠️ **This row originally asked for `age(last_run) > 1.5 × period ⇒ warn`. Do not build that — it was
implemented and run against all 14 jobs on 2026-08-15 05:3x ICT and it fails in BOTH directions.**

*Too tight:* `cleanpro-alerts` (`0 8-22/2 * * *`) and `vidnotes-alerts` (`0 7-23/2 * * *`) are
**banded** — they stop overnight — so they have no single period. Two consecutive fires give 2.00 h;
the real max gap is **10.00 h** and **8.00 h**. The check warns 01:00→08:00 ICT *every night* for
`cleanpro-alerts` (29 % of the clock) and 5 h/night for `vidnotes-alerts`, on healthy jobs. It fired
during the test run: `STALE! cleanpro-alerts ratio=3.81`, job fine.

*Too loose:* the one true positive, `cleanpro-weekly`, reads **ratio 1.58** — it crossed 1.5 only
**84 h after** the missed fire, and clears the threshold by 5 %. Raising to `2 ×` to silence the
nightly noise would have reported the whole fleet clean while the report was missing. No multiplier
does both.

✅ **The detector half is BUILT and is no longer an ask — `scripts/check_missed_fires.py`, run by
every heartbeat cycle** (2026-08-15 06:2x ICT, 2318z). The design below had lived only in this file:
`grep -rl get_next_fire_time` returned **two files, both Markdown**, so nothing executed it. It is now
a read-only script (exit 1 on any miss) named at the top of `HEARTBEAT.md` §1. First run reproduces
2235z's measurement exactly — `MISSED cleanpro-weekly, 98.8 h behind its expected 2026-08-11 03:30 ICT
fire; 13/14 otherwise`, zero false positives on the banded pair.

**What is still yours, and it is the part a heartbeat cannot do:** the *fleet* remains blind. `bot/`
never reads `last_run` back (`:85` displays, `:195`/`:205` write — that is the whole population), so a
discarded fire raises nothing on its own; a cycle has to be awake and looking. And **detection is not
recovery** — the Aug 4–11 CleanPro report is still missing. The decisions are (a) whether `bot/` should
warn on delivery, and (b) whether `coalesce: True` or a longer `misfire_grace_time` at
`bot/scheduler.py:26` is right for weekly jobs, which trades a lost report against a stale-window one
that fires hours late. Both change live scheduling behaviour; neither is a heartbeat's call.

<details><summary>Design, for reference — implemented as above</summary>

```python
trig = CronTrigger.from_crontab(sch['cron'], timezone=ZoneInfo(sch['timezone']))
t, prev = now - timedelta(days=16), None
while (n := trig.get_next_fire_time(t, t + timedelta(seconds=1))) and n < now:
    prev, t = n, n
missed = last_run is None or last_run < prev - timedelta(seconds=60)
```

Measured against all 12 cron jobs: **11 ok, 1 MISSED — `cleanpro-weekly`, 167.9 h behind its last
expected fire.** Zero false positives on the banded pair (correctly resolved to `Fri 08-14 22:00 ICT`
and `Sat 08-15 04:00 ICT`), and it would have caught `cleanpro-weekly` on **08-11 at 03:35** instead
of 08-14. It is also immune to #1's day-of-week trap for free — it never interprets the string, it
asks the parser. (`auto-commit` / `cleanpro-exp-monitor` are `interval_seconds`, not cron; for those
`age > 1.5 × interval` is safe, since an interval genuinely has no bands.)
</details>

Evidence: `memory/t0/2026-08-15/heartbeat-2318z.md`, `-2235z.md`, `-2216z.md`.

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
