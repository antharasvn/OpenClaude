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
| `weekly-conjecture` | `0 8 * * 0` America/New_York | `2026-08-10T12:10:00Z` (= fire + 600 s) | **Sun 2026-08-16 08:00 ET** |
| `vidnotes-weekly` | `30 7 * * 1` Europe/Warsaw | `2026-08-11T05:40:00Z` (= fire + 600 s) | **Mon 2026-08-17 07:30 Warsaw** |

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
process dies mid-flight with no error and **no indication which query stalled**. This predicts the
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
Evidence: `HEARTBEAT.md` §2, `memory/t0/2026-08-15/heartbeat-2019z.md`.

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
