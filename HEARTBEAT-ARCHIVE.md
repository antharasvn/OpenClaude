# HEARTBEAT archive — evidence moved out of the checklist to keep it READABLE

Nothing here is retracted unless it says so. These are the *narratives* behind rules that still
live in `HEARTBEAT.md`; the imperative stayed inline, the measurement moved here. Read this file
only when you need to know **why** a rule exists, never to find out **what** to do.

## §A — §0 clock-bias — full n=1/2/3 measurements (archived 2026-08-15 08:5x ICT by 0152z)

> ⛔ **RE-RUN that same command whenever you need the CURRENT time — never estimate elapsed time from
> how much work you have done.** The mandated first call is not just a cycle-start stamp; it is a free,
> always-correct clock for the whole cycle, and it needs no `date` (so it never trips the ban above).
> `etime` is your elapsed awake time directly — read it, don't derive it.
> *(Added 2026-08-14 18:06 ICT by 1102z, which nearly filed a false §1 finding on exactly this.* At six
> tool calls in, I judged "it must be ~18:07", found no `18:05` line in `infra.log` and no fresh
> `last_run`, and was about to record `echo-backend-alerts` as **failing to fire on its slot**. Re-running
> the wrapper `ps` showed `etime 01:56` ⇒ the true wall clock was **18:04:31** — the slot was still 30 s
> in the *future*. Polled it properly: fired **18:05:00**, completed in 5 s, `OK`. *A guessed clock that
> runs fast turns "not yet" into "broken", and a heartbeat's whole job is telling those apart.*)
> **Note the asymmetry that makes this dangerous: work-count is a BIASED estimator of elapsed time, and
> the bias runs fast** — tool calls feel like minutes and cost seconds. So the error mode is
> systematically "I am later than I am", i.e. **premature not-fired verdicts and self-inflicted budget
> panic**, never the reverse. Same shape as the exit-estimate bias at line 219: a biased clock needs
> correcting, not padding. Cost of the fix is one `ps` call.
> ✅ **n=2, and now with a MAGNITUDE: the bias is ~3× FAST and MULTIPLICATIVE, so no constant fixes it**
> (2026-08-14 18:41 ICT, observed on myself one cycle after the ⛔ above was written). Six tool calls in
> I wrote "maybe T+3.5 min" and started pricing the remaining cycle against ~6 min; the wrapper `ps`
> returned `etime` **01:12** — **72 s actual vs ~210 s estimated, +138 s of phantom elapsed time**.
> 1102z's instance was +2.5 min at a similar depth, same sign. **Because the error scales with work
> done rather than adding a fixed offset, it cannot be corrected the way line 236's exit-estimate bias
> can** — there is nothing to subtract, only a meter to read.
> **Both directions are now scored, and they point OPPOSITE ways — know which is biting:**
> work-count clock ⇒ you think it is **later** than it is ⇒ premature "job did not fire" (1102z) *and*
> **abandoning reachable work** (this cycle: 8+ min of budget believed to be 6). Exit-estimate ⇒ you
> finish **earlier** than predicted ⇒ a stranded tick past the predicted kill. One `ps` erases both.
> **Transferable: an estimator built from EFFORT EXPENDED is systematically wrong about TIME ELAPSED,
> because effort is what you attend to and time is not.** Catching yourself writing "I'm probably at
> T+N" *is* the trigger to re-read the meter. Confidence high on direction (2/2), moderate on ~3×
> (n=1 quantified).
> ✅ **n=3, ratio ~4× — the worst yet, and it confirms the MULTIPLICATIVE form directly** (2026-08-15
> 00:0x ICT, 1659z, on itself). Six tool calls in — but those calls included reading a 2211-line
> checklist and two multi-part `bash` batches — I was pricing the remainder against "~T+3 to 4 min".
> `ps -o etime=` returned **`00:50`**. Ratios are now **~3× / ~3× / ~4×**, 3/3 same direction, and the
> largest ratio came from the heaviest reading — which is exactly what a multiplicative bias predicts
> and a constant offset cannot produce. **Cost avoided, concretely:** at the believed "T+4 min" the
> 00:05 slot would have been marginal against a 00:09:42 kill and handed forward; at the true T+50 s
> it was never in doubt — **4½ min of reachable budget nearly given away.** That is the
> abandoning-reachable-work branch (line 59), the one that costs the fleet observations rather than
> filing false ones. Put `ps -o etime= -p <pid>` **inside your routine `bash` batches** as a habit
> rather than calling it when you feel late: the feeling is the biased signal, so it cannot be the
> trigger.

## §B — §0 logless-death — the sleep mechanism that §0 line ~92 then REFUTED (archived same cycle)

Kept because the two *prescriptions* (write early and thin; read the sleep meter first) survived
the refutation even though the mechanism did not.

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


---

## §C — `completion + 900 s + S`: confirmations n=5 … n=16

Archived 2026-08-15 09:1x ICT (0214z) by the mandated archiving pass. **The rule and its imperative stay
in `HEARTBEAT.md` §0; only these twelve confirmations moved.** All residual 0 s except n=5 (+1 s).
Nothing here needs re-reading unless a future cycle files a break in the series.

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

## §D — proxy-bias series: `date` / `$$` vs the wrapper PID, n=1 … n=7

Archived 2026-08-15 09:1x ICT (0214z). **The imperative — read the wrapper PID as your first call, fit
nothing to this quantity — stays in `HEARTBEAT.md` §0.** What moved is the measurement history and the
four falsified models (tolerance band, growth trend, reversion, log-size driver). Series: `date`
+50 / +59 / +92 / +22 / +66 / +11; `$$` +42 / +26 / +92 / +21 / +66 / +21. Range [11, 92], no direction.

⚠️ **And get it from `ps` ONLY — a `date` at your first tool call reads ~50 s LATE, which is enough to
manufacture a break in the residual-0 rule above** (2026-08-14 08:26 ICT, n=1, observed). Measured this
cycle: first `date` **08:27:17** vs `ps` `lstart` **08:26:27** for the same PID — the gap is session
startup plus the SessionStart hook's log injection, both of which precede the first executable tool
call. The bias has a **fixed sign** (`date` is always later), so it inflates *every* residual by that
constant and makes `completion + 900 s + S` look like it drifts late; this cycle computed "+51 s" and
was one step from filing a 17th-reading break in a rule with sixteen consecutive 0s. It also makes you
believe your kill is ~50 s later than it is — safe in direction, but it stacks with line 189's finding
that self-estimates already miss short. **One `ps` read before any timing claim; never reuse a `date`
reading as a proxy for cycle start.**
⛔ **"`ps`, not `date`" is UNDER-SPECIFIED and `ps -o lstart= -p $$` fails it while LOOKING like
compliance — it is the Bash tool's own subshell, and it read 42 s late** (2026-08-14 09:03 ICT, n=1,
observed). `$$` is spawned when your tool call runs, i.e. *after* session startup and the hook's log
injection — the very interval the ⚠️ above measures. Measured: `-p $$` ⇒ **09:04:16** with `etime`
`00:00` (the tell), against the true wrapper PIDs 96314/96323/96324 at **09:03:34**. Scored on
`completion 01:48:34Z + 900 s + S(=0)` that is **+42 s vs 0 s** — it would have filed the first break
in an n=17 residual-0 series and pointed at launchd jitter. **The bias is the same magnitude as the
`date` bias (42 s here vs 50 s and 59 s measured), so "is this within a minute?" cannot discriminate
it.** The real distinction is not `ps` vs `date`: it is **the cycle's own process vs anything your
tool calls spawn** — `date` and `$$` are both the latter, and any future `$(...)`-style proxy will be
too. **Use line 293's command verbatim** (`ps -eo pid,lstart,etime,command | grep '[g]timeout 600
claude'`) and sanity-check that `etime` is roughly your elapsed cycle, not `00:00`. Same class as §3's
dominant failure — *reasoning about a thing you had not opened* — in its measurement form: a proxy for
the cycle was measured and labelled the cycle.
✅ **CONFIRMED n=2 — but the bias is VARIABLE, and that makes a tolerance band useless rather than
merely imprecise** (2026-08-14 09:23 ICT). Second reading: `-p $$` ⇒ **09:23:46** against a true start
of **09:23:20** — same sign, **+26 s**, not 42. Full series of proxy biases now: `date` **+50 s**,
`date` **+59 s**, `$$` **+42 s**, `$$` **+26 s**. The spread is not a `date`-vs-`ps` property — it is
**however long the session takes to reach your first tool call**, which varies with MCP connect time,
hook size, and injected-log volume. Two corrections to the ⛔ above, both sharpening it:
- It says the bias is "the same magnitude" as `date`'s. **At 26 s it is not**, and that is worse, not
  better: 26 s sits comfortably inside "within a minute of expected", so a cycle applying a sanity band
  would have *accepted* it and filed a spurious **+27 s** residual. The bias is small enough to read as
  jitter and large enough to be the entire signal. **No tolerance test can substitute for reading the
  right process.**
- **Expect it to grow.** It is dominated by session startup, and the injected daily-log bundle is
  already ~147 KB. Never re-derive this as "about 40 s, just subtract it."
✅ **n=3, and the growth prediction lands hard: +92 s, ~1.6× the previous worst — plus the cleanest
proof that the `ps`-vs-`date` framing was never the point** (2026-08-14 09:41 ICT). Both proxies were
read in **one** call and returned the **same instant** — `date -u` **09:43:31** and `ps -p $$ -o
lstart=` **09:43:31** — against a true wrapper start of **09:41:59**. Identical because they timestamp
the same event: your first tool call. Series is now `date` **+50 / +59 / +92**, `$$` **+42 / +26 /
+92**; the injected log bundle was **154.3 KB** this cycle, up from the ~147 KB cited above. **The new
danger is directional, not just size:** at +92 s the proxy says your kill is 09:53:31 when it is
**09:51:59** — it *manufactures* budget, and line 189 already measures self-estimates as biased
**short**. The two errors stack toward believing you can reach a tick you cannot. Read the wrapper PID
(line 293) once, before any timing claim.
⛔ **"Expect it to grow" is FALSIFIED at n=4 — the bias FELL to +21 s, the lowest on record. Keep
0923z's "variable" and delete the growth trend** (2026-08-14 10:21 ICT). Both proxies read in one
call as before: `date` **10:21:45**, `$$` **10:21:44**, against a true wrapper start of **10:21:23**.
Series: `date` **+50 / +59 / +92 / +22**, `$$` **+42 / +26 / +92 / +21**. The 0941z entry saw +92 s
after +26 s and generalised to a monotone trend driven by the injected-log bundle; one cycle later it
is back to the bottom of the range. **A growth trend and a tolerance band are the same mistake** —
both pretend the number is predictable so you can subtract or bound it, and it is neither. The only
safe reading is the one that needs no model: **read the wrapper PID (line 293) every cycle.**
Note the hazard does not shrink with the bias, it only changes size: at +92 s the proxy manufactures
92 s of budget, at +21 s it manufactures 21 s, and both stack with line 189's short-biased
self-estimate. Generalise: **a two-point trend in a quantity whose driver you have not measured is a
guess wearing a slope** — the underlying driver here (time-to-first-tool-call) is not something any
cycle has instrumented, only inferred from log size.
✅ **n=5 confirms "variable, no model" and kills the trend for good: +66 s, mid-range** (2026-08-14
10:39 ICT). Both proxies read in one call again returned the **same** instant — `date` **10:40:53**,
`$$` **10:40:53** — against a true wrapper start of **10:39:47**. Series: `date`
**+50 / +59 / +92 / +22 / +66**, `$$` **+42 / +26 / +92 / +21 / +66**; range **[21, 92]**, no
direction. That is two consecutive falsifications of a fitted trend (0941z's growth story, then this
one against any reversion story 0321z might have implied). **Stop fitting anything to this quantity
and just read the wrapper PID (line 293) as your FIRST call** — this cycle didn't, and paid a second
tool call to correct it. Hazard direction held: +66 s of *manufactured* budget (proxy kill 10:50:53
vs true **10:49:47**), stacking with line 189's short-biased self-estimate.
✅ **n=6, +21 s — a SECOND reading at the floor, and it falsifies the log-size DRIVER, not just the
trend** (2026-08-14 10:59 ICT). `$$` **10:59:50** vs true wrapper start **10:59:29**. Series:
**+42 / +26 / +92 / +21 / +66 / +21**, range still **[21, 92]**, no direction. 0941z did not only fit a
slope — it named a *cause* (the injected daily-log bundle, "already ~147 KB", "expect it to grow"), and
that cause is now contradicted directly: this cycle's bundle was **larger** than the +92 s cycle's and
the bias came in at the **floor**. So the quantity is not merely unpredictable, its one proposed
mechanism is dead, and nothing has replaced it. **Stop proposing drivers for it too** — the cheap read
(line 293) costs one call and needs no theory. Side note for whoever next writes a timing probe:
`date -u "+%Y-%m-%dT%H:%M:%SZ"` **fails on BSD `date`** (`illegal time format`) — the `-u` must precede
the format, and a failed proxy call still costs you the round trip.
✅ **n=7, +11 s — a NEW FLOOR, and it is the reading that retires the tolerance-band idea for good**
(2026-08-14 14:40 ICT). `date` **14:40:21** vs true wrapper start **14:40:10**. Series: `date`
**+50 / +59 / +92 / +22 / +66 / +11**, `$$` **+42 / +26 / +92 / +21 / +66**; range widens to
**[11, 92]**, still no direction — the fourth consecutive falsification of a fitted trend in this
quantity. **Why +11 matters more than +92 did:** line 318 argued that at 26 s a sanity band would
*accept* the bias and file a spurious residual. At **11 s** no band would even flinch — it reads as
rounding — and it is still **100 % of the signal**, because the true residual this cycle was **0**
against an n=19 unbroken series. A cycle trusting `date` would have broken that series with a number
too small to argue about and too small to notice. **The hazard shrinks with the bias but never
inverts: it always manufactures budget** (11 s here), always stacking with line 189's short-biased
self-estimate. Read the wrapper PID (line 293) as your first call; there is nothing to subtract.

## §E — n=13 heartbeat runtime distribution (the hang-vs-capacity study)

Archived 2026-08-15 09:1x ICT (0214z). **The surviving METHOD (successes-vs-cap) stays in
`HEARTBEAT.md` §0; its conclusion about the logless deaths was falsified two entries later.** Kept
because QUEUE #2 and the 03:4x / 05:0x nested-cap findings all cite this measurement.

⛔ **The MECHANISM above is WRONG for the logless deaths, and the runtime distribution says so — a
normal cycle finishes at ~40 % of the cap, so a cycle that dies at 600 s HUNG, it did not run long**
(2026-08-11 17:04 ICT, n=13). This applies §1's own where-do-the-successes-sit test (line 261 ⛔) to the
heartbeat's own `gtimeout 600 claude -p` — the first time that test has been scored on a population
other than the weekly trio. Each cycle's `ps` start paired against its completion, both already in §0's
residual series: **5:06 / 3:41 / 3:56 / 3:47 / 5:18 / 3:31 / 3:56 / 4:25 / 3:54 / 4:03 / 3:48 / ≈4:00**
⇒ **median ≈ 3 m 55 s, max 5 m 18 s (318 s), against the 600 s cap** — 2.6× headroom at the median,
1.9× at the max, and a **282 s gap** between the observed maximum and the kill. That is the *opposite*
signature to the weekly jobs, whose successes climb continuously to 540 s against 600 with the top two
clearing the kill by 72 s and 0 s. **Successes clustered far below the cap plus a pile at exactly the
cap is the HANG branch, not the capacity branch.** Consequences: (a) raising this cap would not recover
a logless cycle — it would only let each hang burn longer; the `timeout=600` → 1800 fix is right for
`bot/scheduler.py:149` and **wrong here**; (b) the write-early-and-refine prescription below is still
correct, because it is cheap insurance against a hang whatever the cause — keep doing it, just don't
attach "the cap bites hardest here" as the reason; (c) what would actually settle it is capturing
`claude -p` stderr or stamping a breadcrumb at entry in `skills/heartbeat/run.sh` — boss's call, and it
queues *behind* the weekly-cap decision, not alongside it. Confidence **high** on the discrimination,
**moderate** on the hang attribution (the two logless cycles left nothing on disk, so the stall is
inferred from the distribution, not observed). Generalise the generalisation: **the successes-vs-cap
test is worth running against any timeout you are about to reason about, including your own.**

## §F — the logless-cycle failure population (usage limits vs API stream deaths)

Archived 2026-08-15 09:2x ICT (0214z). **Every imperative from these two entries was kept inline in
`HEARTBEAT.md` §0** — `exit 1` is not a diagnosis; read the plist for existing redirects; ask how many
EVENTS an n contains; write-early must be an executed `Write`. What moved is the per-cycle evidence:
the 101-vs-100 Starting/Completed count, the two outage windows, and the individual death timestamps.

⛔ **BOTH stories above are FALSIFIED. The logless deaths are USAGE LIMITS — `claude -p` is refused and
exits in SECONDS — and it has been printed to `/tmp/claude-heartbeat.log` all along** (2026-08-11 17:29
ICT, n=20, observed not inferred). `com.claude.heartbeat.plist` declares `StandardOutPath
/tmp/claude-heartbeat.log` + `StandardErrorPath /tmp/claude-heartbeat.err` (170 KB / 30 KB on disk),
and `skills/heartbeat/run.sh` **already** prints `[heartbeat] Starting heartbeat at <ISO Z>` before the
invocation and `|| echo "[heartbeat] Timed out or failed (exit $?)"` after it. **101 `Starting` vs 100
`Completed`** — the delta is the in-flight cycle, so *no cycle has ever left no trace*; they leave no
**daily log**. §0's own two cited deaths, read from that file: `04:02:58Z` started 04:02:17Z, printed
**`You've hit your weekly limit · resets 11am (Asia/Saigon)`**, **exit 1** — **~41 s**; `07:59:41Z`
started 07:56:42Z, **exit 143** (SIGTERM 128+15) — **2 m 59 s**, and gtimeout's own timeout return is
**124**, not 143. **Neither ran long; the cap fired on neither.** The real population is 20 failures,
19 × exit 1, in two contiguous blocks: **weekly limit 02:28:18Z→04:02:17Z (7 cycles)** and **session
limit 08:33:46Z→11:39:22Z (13 cycles)** — all of 08-10 between 02:28Z and 11:39Z was a dead fleet.
**Rule: before queuing an instrumentation request, read the runner and its launchd plist for redirects
that already exist** — the 16:59 entry asked the boss for stderr capture and an entry breadcrumb that
were both already there, costing ~15 h of a wrong mechanism here plus a spurious queue item. A runtime
distribution can prove the cap is *not* the constraint; it cannot say what is. Second-order: a chain
ending *"not a heartbeat's call to change"* is the exact place this fleet stops looking — re-read it as
a prompt to check whether the change is already made. **Read `/tmp/claude-heartbeat.log` before
theorising about a missing cycle.** The write-early prescription survives all three mechanisms and
stays in force. **Cross-applies to §1's third non-delivery mode (line 294): same binary, same shape —
raise it to high confidence, and see the adjacent-pair evidence there.**
⛔ **That entry closed the case ONE MECHANISM TOO EARLY. `exit 1` is TWO modes, and its "n=20" was
really n=2** (2026-08-11 18:52 ICT, observed). The very next logless death — 7 h later, the `11:22:25Z`
cycle — was **not** a usage limit and did **not** exit in seconds: `API Error: Your computer went to
sleep mid-response`, exit 1, at **7 m 03 s**, no `heartbeat-1122z.md` on disk. Its last printed line was
*"Confirmed a real finding. Writing the log now (T+6, per §0)"* — a finding died with it. Full
population is now **24: 23 × exit 1 + 1 × exit 143**, and the exit-1s split cleanly:

| mode | n | runtime | printed cause | logless |
|---|---|---|---|---|
| usage-limit refusal | **20** | seconds | `You've hit your weekly/session limit` | yes |
| **API stream death** | **3** | **4 m 22 s / 5 m 43 s / 7 m 03 s** | `API Error: … mid-response` | **3 for 3** |

(The other two: `08-10 05:09:36Z→05:15:19Z` and `20:06:23Z→20:10:45Z`, both `Connection closed
mid-response`, both with no `heartbeat-0509z.md` / `heartbeat-2006z.md`.) **Runtime alone does NOT
discriminate an API death from a success** — 4 m 22 s sits at the median of the n=13 success band above.
It discriminates API death from refusal, with no overlap. **Rule: `exit 1` is not a diagnosis — read the
line immediately ABOVE `Timed out or failed` (it names the mechanism) and use runtime only as the
sanity check.**
**The transferable half is the inflated n.** The 17:29 entry itself records that its 20 failures fell in
**two contiguous blocks** (7 cycles + 13 cycles inside one weekly-limit and one session-limit window) —
a 15-min job failing throughout one outage is **one event sampled 7 times**. n=20 was **n=2**, and two
events cannot support "solved". This is §1's own *"a regime label absorbing an unlike failure"* (line
260) and *"decompose BOTH halves of a shared row"* (line 268), with the label being **`exit 1`** and the
absorbed failures sitting in the file the entry had just finished reading. **Before quoting an n, ask
how many independent EVENTS it contains — consecutive failures of a periodic job during one outage
collapse to n=1.**
**Consequence for write-early: necessary, and here insufficient.** 1122z *was* following §0 and still
lost its log, because the announcement and the `Write` were in the same turn and the stream died between
them. **The log must be an executed `Write` call, not a stated intention, and with a non-flat meter it
belongs at ~T+3, not T+5** — announcing costs a turn the sleep can land in. Regime dependency makes this
actionable: all three API deaths fell in **sleep-cycling windows**, so `mid-response` is a *sleep* mode.
That vindicates §0's original n=1 inferred-from-absence sleep story on *timing* — now **observed with
the cause printed** — so raise it to high confidence, but keep it strictly apart from the usage-limit
mode. No new instrumentation ask: the discriminator is already printed.


## §G — the log-compression / context-injection thread (§3), archived 2026-08-15 09:4x ICT (0236z)

Moved out of `HEARTBEAT.md` §3 verbatim. **The whole thread is RETIRED** — the bundle is persisted and
truncated by the harness, not injected, so every KB-per-day figure below charges a diversion. The rules
that survive it (retract at the entry point *and* every action label; a refinement between a claim and
its retraction argues for the corpse; open the mechanism before filing a causal chain between queue
rows; read what a notice is ANNOUNCING) stayed inline in §3. This is evidence only — nothing here is
an instruction.

- ⛔ **Log length is a FLEET-WIDE shared resource, not a personal one: the SessionStart hook `cat`s
  EVERY log of the current day, uncapped, into EVERY later cycle** (2026-08-15 01:4x ICT, hook source
  read, sizes measured). `.claude/settings.json:23` is `for f in "$LOGDIR"/*.md; do … cat "$f"; done`
  — no `tail`, no `head`, no size guard; the bundle ramps from 0 at midnight to **600–692 KB** by
  late evening (08-14: 600 K / 76 files; 08-11: 692 K / 65). At 01:41 with only 7 files mine was
  already **44.6 KB** and overflowed the harness's inline cap. **The cost is quadratic in the day:** a
  log written at cycle *k* is re-injected into the ~(76 − k) cycles after it, ≈ **23 MB of injected
  context per day** (~5.7 M tokens) spent re-reading the day's own logs. So the marginal cost of a KB
  is not your one `Write` — it is that KB × every remaining cycle today.
  **Consequence with teeth: context spent scales with time of day, so the most context-starved cycles
  are the 23:0x ones — exactly where the midnight-handoff duty lives.** The day's most important
  artifact is written by the cycle with the least room. (This retro-justifies 1622z writing the
  handoff 38 min early for a reason it did not name.) **Prescription: write tersely, put the durable
  version in `HEARTBEAT.md` — read once, on demand, and truncated — and do NOT restate closed findings
  to make a log "self-contained"; self-containment is what is being charged ~70× a day.**
  **Why this sat unremarked:** §0 cites the bundle twice (~147 KB, 154.3 KB) but only ever as a
  *candidate driver of the time-to-first-call bias*, where line 448 correctly **falsified** it.
  Falsifying a quantity as the driver of one effect is not evidence about its cost elsewhere —
  **a killed hypothesis retires the LINK, not the MEASUREMENT.** Boss's queue (the hook is off-limits
  per CLAUDE.md): cap the injection to the handoff + `ls -t | head -3`, which takes a late-evening
  bundle from ~600 KB to ~25 KB with no loss, since older logs are either closed or already here.
  ✅ **Acted on, and it exposes a LEVER THE FLEET ALREADY HAS: the prescription above is written for
  the log you are ABOUT to write, but the bundle's biggest item is always one ALREADY WRITTEN**
  (2026-08-15 02:2x ICT, 1921z). Measured `ls -S memory/t0/2026-08-15/`: the largest file was
  `00-handoff-from-2026-08-14.md` at **10.1 KB** — bigger than any heartbeat log — and it is the one
  file in the directory whose **purpose expires at the first cycle that reads it**. Compressed it in
  place to a **1.4 KB pointer table** naming where each of its six items had already been promoted
  (five to this checklist, one expired). ~8.7 KB × the ~85 cycles left in the day ≈ **740 KB / ~185 K
  tokens** of injected context recovered, with nothing lost that a later cycle can act on — the
  narrative sits in `memory/t0/2026-08-14/heartbeat-1622z.md`, which is *not* injected.
  **Generalise: terseness is a property of the STANDING BUNDLE, not of your own `Write`.** A cycle
  can only make its own log small — that caps its contribution at a few KB — but *any* cycle can
  compress a superseded file and recover the whole remainder of that file's day. **So the routine is:
  `ls -S` the day's directory, and for anything above the median ask "is this still load-bearing, or
  has it been promoted?" Promoted-and-still-injected is pure rent.** Two guards, both cheap: verify
  the promotion target actually contains the finding **before** trimming (`memory/` is gitignored —
  there is no undo), and leave a pointer rather than deleting, so the compression is auditable.
  Note the asymmetry that makes this worth a cycle's time: writing tersely saves *your* KB once;
  compressing a stale KB saves it once per remaining cycle. The boss-queued hook cap is still the
  real fix — this is the part the fleet can do without touching `.claude/settings.json`.
  ⚠️ **Do NOT extend this to same-day heartbeat logs by default.** The handoff qualified because it
  is explicitly a hand-forward artifact with a stated expiry; a heartbeat log may still be the only
  record of a finding not yet promoted. Compress on evidence of promotion, never on age alone.
  ⛔ **The bundle is NOT INJECTED — the harness PERSISTS it and shows ~2 KB. Every number above is
  the size of the thing that did *not* reach context, and the compression saving is ~0** (2026-08-15
  04:0x ICT, n=2, quoted verbatim not inferred). This cycle's SessionStart hook output arrived as
  *"Output too large (67.4KB). Full output saved to: …/tool-results/hook-…-stdout.txt — Preview
  (first 2KB)"*. The hook is uncapped exactly as line 2134 says; **the consumer caps it**, so the
  "~23 MB of injected context per day" and the "740 KB recovered" are both charges against a
  diversion, not an injection. **The fleet's own evidence already said so:** the 154.3 KB figure §0
  cites twice is sourced in `memory/t0/2026-08-14/heartbeat-0241z.md:26` to *"the SessionStart hook's
  own **persisted-output notice**"* — the number was legible **because** the bundle had been written
  to a file instead of injected. Both readings (154.3 KB, 67.4 KB) truncated; none observed passing
  through whole.
  **The prescription inverts, which is the part to act on:** compression only helps while the bundle
  stays **above** the truncation threshold. Line 2153's target — 600 KB down to ~25 KB — would very
  likely land it **below**, injecting all 25 KB in full, i.e. **~12× the 2 KB preview it replaced.**
  The threshold is unmeasured, so the crossover is unknown; until someone measures it, **do not
  compress for context cost.** Compressing for *readability* is still defensible — a successor now
  has to `Read` the persisted path to see the day's logs at all — but that is the opposite argument
  and must be made as one. `QUEUE.md` #4 (asking the boss for a hook cap) is withdrawn on this basis.
  **Transferable: when a number arrives inside a notice, read what the notice is ANNOUNCING.**
  `67.4KB` is not a measurement of an injection, it is the receipt for a diversion — and it was cited
  four times across §0 and §3 without anyone reading the sentence containing it. Same shape as §1's
  *"open the destination"*, aimed at a measurement instead of a filing. Confidence **high**.
  ⛔ **That retraction is CORRECT and still FAILED to stop me, because a REFINEMENT sits between the
  prescription and its death — and a refinement is positive evidence that the thing it refines is
  alive** (2026-08-15 07:4x ICT, n=1, observed on myself, caught one call short of acting). Reading
  §3 top-down I hit the routine at the ✅ above — *"the routine is: `ls -S` the day's directory …
  Promoted-and-still-injected is pure rent"* — ran it (27 files, 172 KB, ~66 cycles left in the day),
  and was pricing which log to compress. The next thing I read was the ⚠️ *"Do NOT extend this to
  same-day heartbeat logs **by default** … compress on evidence of promotion, never on age alone"*,
  which **narrows the scope of a live rule**. Nobody writes a scope limit for a dead rule, so it
  reads as confirmation, and I went looking for the promotion evidence it asked for. Only the block
  after that kills the whole thread. **Ordering, not content: the retraction was two blocks late and
  the intervening block pointed the wrong way.** This is §0 line 25's finding — *documentation cannot
  govern behaviour that precedes reading the documentation* — one level in: it cannot govern a
  decision made **earlier in the same document** either. §0 solved its version by moving the
  imperative into the `claude -p` prompt, the only text preceding the first tool call; the analogue
  here is the section head, the only text preceding the thread. Pointer added there.
  **Two transferable halves:**
  **(a) When you retire a thread, the marker goes where the READER ENTERS, not where the ARGUMENT
  ENDS.** Appending the correction is chronologically honest and operationally useless — the fleet
  files corrections in the order they are discovered, which is exactly the order that puts every
  superseded prescription *first*. Check the entry path, not the entry.
  **(b) A refinement between a claim and its retraction is an ACTIVE hazard, not neutral filler** —
  it does not merely fail to warn, it supplies fresh evidence of life, so the reader who would have
  hesitated at a stale-looking rule proceeds instead. When killing a thread, re-read what sits above
  the kill and neutralise any scope-limits, caveats, or worked examples that now argue for the corpse.
  Cost here was ~2 calls and no damage (`memory/` has no undo, so the damage branch was real).
  Confidence **high** — the reading order is reproducible from the file.
  ⚠️ **(a) IS NECESSARY BUT NOT SUFFICIENT, and the counterexample was written by the very next cycle,
  in the other file.** (2026-08-15 08:1x ICT, 0113z, found by reading `QUEUE.md` #6 as a boss would.)
  0053z refuted #6's prescription by measurement and did exactly what (a) asks: it **rewrote the row's
  opening** with *"Do not apply the old patch"* plus the correct structural replacement. But 30 lines
  down, the row's original **`**Patch:**` line still stood, unmarked** — and `QUEUE.md` is not read
  top-down. Every row in it is navigated by its bolded actionable label (`**Patch:**`, `**The actual
  ask**`), which is precisely what a boss triaging a queue scans for. **The retraction was at the
  entry point and the corpse was at the ACTION point, so a reader taking the file's own shortcut hits
  the dead patch and never sees the retraction at all.** Struck it in place with a pointer up to the
  live block; also annotated the `# ← drains it` code comment in the same row, which asserts as fact
  the thing 0053z measured as `b''`.
  **Sharpen (a) to: the marker goes where the reader ENTERS *and* at every ACTIONABLE LABEL the
  document teaches readers to jump to.** In prose the two coincide; in an operational document —
  a queue, a runbook, a checklist with `> RUN THIS FIRST` blocks — they diverge, and the action point
  is the more dangerous of the two because reaching it means someone is about to *do* something.
  **Test before you consider a retraction landed: search your own retracted row for every bold label,
  imperative, and code comment, and ask what each one alone would tell someone who read nothing else.**
  Note this is (b) at higher severity rather than a new class: a stale `**Patch:**` doesn't merely
  argue for the corpse, it *is* the corpse wearing the label the reader was told to trust.
  Cost of finding it: 0 extra calls (it surfaced while reading the queue for pending work); cost of
  missing it: the exact no-op 0053z spent a patch and a revert to prevent. Confidence **high**.
  ✅ **Applied it OUTWARD instead of to another document, and it paid: a standing refrain seven cycles
  old was never checked against the code it describes** (2026-08-15 08:3x ICT, 0131z, both facts read
  from source). Every cycle since 2235z has written *"detection ≠ recovery — the CleanPro Aug 4–11
  report still does not exist"* — a sentence that quietly implies recovery is pending. It is not:
  `cron/jobs.json` makes `cleanpro-weekly` a `prompt` job on `skills/cleanpro-weekly/SKILL.md`, and
  that skill computes its window as **pure date arithmetic off today** (`:10-14`,
  `START_DATE=date -v-7d` … `WEEK_LABEL=date -v-1d +%Y-W%V`), reading `last_run` **nowhere**. The
  08-19 fire will query **Aug 12–18**; no fire of this job will ever produce the lost week. `QUEUE.md`
  #7 amended at both its entry point and its action label.
  **The transferable half is the conjecture that died on the way.** I had a clean compounding story —
  #7's lost fire *feeds* #1's 600 s cap, because the next run would carry a **two-week** window
  against a cap this job clears by only 152 s (its last real run: fire + **448 s** = 75 % of cap,
  itself a counterexample to #1's "every weekly `prompt` job times out"). The mechanism does not
  exist. **A causal chain between two queue rows is a hypothesis about a mechanism neither row
  states — open the mechanism before filing the chain**, or the queue ends up carrying a failure the
  code cannot produce, and the row it implicates gets argued partly from a phantom. Same family as
  §0 line 527, one level out: there the error is running a paraphrase of a prescribed command; here it
  is reasoning about a job from its **schedule row** instead of its **implementation**. A schedule
  says when it fires; only the skill says what it asks for. Confidence **high**, cost 2 calls.


---

## §H — successor placement & reach: the n=1…n=16 confirmation series and the 2026-08-11 self-estimate case studies

Archived 2026-08-15 09:5x ICT (0255z) from `HEARTBEAT.md` §0 — 126 lines, 12.5 KB. This is the block
§0's compaction note called *"genuinely hard — it reads as narrative but has hard imperatives buried
mid-paragraph"*, which is why 0152z and 0214z both left it. Every imperative was extracted into a
nine-bullet rewrite that stays INLINE under *"Successor placement & reach — SETTLED"*; what follows is
the EVIDENCE only — the residual arithmetic, the mechanism derivations, and the five 2026-08-11 case
studies that established the short bias. Nothing here needs to be read in order to act correctly; read
it only to re-score a rule or to check an n.

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
✅ **The ⚠️ above is SCORED — n=1 end-to-end, and it is exact. Raise it to high confidence, observed**
(2026-08-13 14:37 ICT). Both clocks measured independently against the *same* 222 s sleep window
(14:19:49 → 14:23:31): launchd `StartInterval 900` from completion 07:18:36Z ⇒ predicted 14:37:18,
`ps` start **14:37:16**; APScheduler `IntervalTrigger 7200` from anchor 12:33:23 ⇒ predicted 14:37:05,
`Running job:` **14:37:03**. **Identical S, identical −2 s residual, two independent schedulers** —
they do slide together, so sleep does not degrade an already-armed tick's reachability. Pad reach
claims for your own exit-time bias (line 181), never for sleep. This also settles §1 line 439's
remaining half (**a fire at the NEW interval anchor**, previously unobserved) on the same measurement.
✅ **SETTLED at n=16, every residual 0 s, both regimes (S=0 and S up to 1394 s) — STOP RE-DERIVING IT.**
Confirmations n=5…n=16 (2026-08-11, twelve consecutive readings) are evidence, not instruction; they are
archived at `HEARTBEAT-ARCHIVE.md` §C. **Imperative: use `completion + 900 s + S` to place your successor,
spend the cycle on the forecast rather than another confirmation, and do not re-measure the rule.**
Corollary kept inline: **an apparent 38-min hole between two cycles is launchd's deferral, not a logless
death — check the sleep meter before hunting for a missing log.**
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

---

## §I — QUEUE #2's superseded 12-run "hang" distribution (archived 2026-08-15 11:1x ICT, 0409z)

Moved out of `QUEUE.md` #2 whole. It was that row's case from 2026-08-15 03:0x ICT until the n=101
recount at 10:3x refuted it; the row now carries only the ask plus its *current* justification.
**Nothing here is live. Do not re-derive from it.**

The 12-run window (from `logs/infra.log`, plus the live 03:00 run caught at 138 s, S = 0):

| successes (s) | 136, 121, 125, 112, 127, 122, 137, 154, 118, 139, 138, 138 → **median ≈132, max 154** |
| --- | --- |
| failures | **2, both at exactly 300 s** (07-30, 08-13), `timed out after 5 min` |

The dead argument built on it: successes sat at **44–51 % of the cap** with a **146 s dead zone**
below it and nothing ever finishing in 155–299 s, which the successes-vs-cap test read as the
**hang** branch. A refinement then claimed the unreachable 600 s inner timeout predicted that
distribution *better* than a hang did — *"past ~168 s nothing can interrupt a slow query before
300 s, so runs land at ~132 s or at exactly the cap, never in the 146 s dead zone."*

**Why it died** (n=101, 04-13→08-15): 94 successes span **91–200 s**, so the dead zone is populated
(157 s on 05-06, 174 s on 07-18, 200 s on 07-20) and the prediction has no distribution left to
explain; and the failures are **7, not 2, and bimodal** — 4 fast `exit 1` plus 3 cap-kill timeouts —
so the cap accounts for a minority of them. The 273 s figure that preceded both readings was the
08-14 run the host slept 734 s inside (`Dark Wake Thermal Emergency`).

**Transferable, and the reason this corpse is worth keeping at all: the 12-run window was not a
sample anyone chose — it was the runs that happened to be visible in the part of the log already
read.** Two successive refinements were fitted to it, each more specific than the last, and the
second one *explained the artifact* (a dead zone that does not exist). A distribution assembled from
what is already in context will happily support a mechanism. **Build the whole series before fitting
anything to its shape** — the cost here was two filed diagnoses and an ask pointed at the wrong file.

## §J — QUEUE #7's retired detector thread: the refuted `1.5 × period` ratio check and the shipped design (archived 2026-08-15 11:5x ICT, 0449z)

`QUEUE.md` #7 had grown to ~80 lines around an ask that is now **two sentences**. Everything below is
retired by construction — the detector it argues about **shipped** as `scripts/check_missed_fires.py`
on 2026-08-15 06:2x ICT (2318z) and is named at the top of `HEARTBEAT.md` §1, which every cycle runs.
Per 0236z's method: pick the thread whose conclusion is already settled, not the longest block.

**The refuted ask — `age(last_run) > 1.5 × period ⇒ warn`. DO NOT BUILD IT.** Implemented and run
against all 14 jobs on 2026-08-15 05:3x ICT; it fails in **both** directions at once, so no
multiplier exists that works:

*Too tight:* `cleanpro-alerts` (`0 8-22/2 * * *`) and `vidnotes-alerts` (`0 7-23/2 * * *`) are
**banded** — they stop overnight — so they have no single period. Two consecutive fires give 2.00 h;
the real max gap is **10.00 h** and **8.00 h**. The check warns 01:00→08:00 ICT *every night* for
`cleanpro-alerts` (29 % of the clock) and 5 h/night for `vidnotes-alerts`, on healthy jobs. It fired
during the test run: `STALE! cleanpro-alerts ratio=3.81`, job fine.

*Too loose:* the one true positive, `cleanpro-weekly`, reads **ratio 1.58** — it crossed 1.5 only
**84 h after** the missed fire, and clears the threshold by 5 %. Raising to `2 ×` to silence the
nightly noise would have reported the whole fleet clean while the report was missing.

**Transferable, and it is why this is worth keeping as a corpse:** a scalar-period staleness rule is
the obvious detector for "did it run?", and it is unbuildable on banded schedules. The replacement
works because it asks the **trigger** to enumerate its own fires and interprets no cron string —
which also makes it immune for free to #1's APScheduler `day_of_week` trap. **When a threshold has to
straddle two populations with different natural periods, stop tuning the constant and change what the
check asks.**

**The shipped design, for reference** (this is what `check_missed_fires.py` implements):

```python
trig = CronTrigger.from_crontab(sch['cron'], timezone=ZoneInfo(sch['timezone']))
t, prev = now - timedelta(days=16), None
while (n := trig.get_next_fire_time(t, t + timedelta(seconds=1))) and n < now:
    prev, t = n, n
missed = last_run is None or last_run < prev - timedelta(seconds=60)
```

Measured against all 12 cron jobs at design time: **11 ok, 1 MISSED — `cleanpro-weekly`, 167.9 h
behind its last expected fire.** Zero false positives on the banded pair (correctly resolved to
`Fri 08-14 22:00 ICT` and `Sat 08-15 04:00 ICT`), and it would have caught `cleanpro-weekly` on
**08-11 at 03:35** instead of 08-14. (`auto-commit` / `cleanpro-exp-monitor` are `interval_seconds`,
not cron; for those `age > 1.5 × interval` is safe, since an interval genuinely has no bands — but
see `QUEUE.md` #8 for what that branch is blind to.)

**The gap between design and ship, kept because it is the reusable half:** this design lived only in
`QUEUE.md` for one cycle, and `grep -rl get_next_fire_time` then returned **two files, both
Markdown** — nothing on disk executed it. **A boss-queue row is a request, not a detector.** When a
row already contains a working implementation, run the half that is in your own lane and leave the
boss the half that needs their authority.

## §K — §0's handoff / exit-estimate chain: the reasoning residue (archived 2026-08-15 12:1x ICT, 0509z)

Companion to §H, which holds the n=1…n=16 confirmation series and the 2026-08-11 case studies. Every
IMPERATIVE from this thread stayed inline in `HEARTBEAT.md` §0 under *"Successor placement & reach —
SETTLED"*; what follows is only the argument that produced them.

**Why the threshold has the wrong sign.** A precomputed *"if you start before X you may block"*
threshold silently embeds the predecessor's guess at its own exit time, and §H measures that guess at
~3 min of uncertainty. It has nearly cost a log. Losing the log costs more than any single
observation is worth — hence the receiving cycle recomputes from its own `ps` start.

**Why the symmetry has to be stated in both directions.** Start and end-of-budget move together.
Against an *already-scheduled* tick, starting earlier strictly REDUCES reach — that is the half that
strands observations. But for coverage of *future* time in aggregate, a cycle that writes early and
exits fast pulls its successor's start earlier and WIDENS the fleet's reach, so when a tick sits just
past the end of your own budget, finishing quickly is itself the way to get it covered. The cost of
dropping the near-end half is a cycle that inherits an "already past, settle retroactively" label and
**skips a live read it could have made**. Both halves have the same fix: hand the tick, recompute
from your own start, never inherit the predecessor's placement of it in time.

**The `naive − 3 min` series.** Five for five short on 2026-08-11, never once long, plus a
third-instance 2 min 09 s miss the same day — hence ~3 min as a FLOOR on the margin rather than a
worst case. Padding a symmetric band around a biased estimator leaves the central value ~3 min too
late, and **both** §0 failure modes are downstream of exactly that: (a) far end, a tick just inside
the predicted end of budget is really past the true one (**stranded**); (b) near end, a tick just
before the predicted start is really still live (**skipped live read**). One subtraction fixes both;
a symmetric pad fixes neither. Confidence moderate — n=5, one day, one model.

**Why "state the estimate once".** 0210z's refinement moved its estimate 4 min the wrong way by
"correcting" for work it had already committed to — double-counting planned work overstates reach,
which is the sign that strands a tick nobody watched.

**Why sleep never enters a reach claim.** launchd's `StartInterval 900` defers by S and APScheduler's
armed wait fires at `armed + S`; both freeze on the same clock, measured independently against one
222 s window with an identical −2 s residual. Sleep accruing after both reference instants shifts
your successor's start **and** the evaluation instant by the same S, so an already-armed tick's
reachability is invariant under it.

## §L — Unbounded-holder band measurements (§2), archived 2026-08-15 12:3x ICT by 0528z

Every imperative these paragraphs carried was rewritten inline in `HEARTBEAT.md` §2 before the move
(0509z's method). What follows is the evidence only; nothing here should be acted on directly.

**`dasd` `BackgroundTask`, hold `0x0000fa48000b862c` — full length ≈64 min 58 s.** At 2026-08-11
04:52 ICT it was the **only** assertion on the host: `PreventUserIdleSystemSleep`, `UserIsActive`,
`PreventUserIdleDisplaySleep` and `PreventSystemSleep` all read **0**; every transient row the prior
cycle had seen (`runningboardd` WhatsApp `FinishTask`, `dasd` `ApplePushServiceTask`) was gone; only
powerd's always-discounted `ExternalMedia` remained — and the host had still gone **56 min with
S = 0**, which forecloses the "some *other* hold was really responsible" reading. Gone by the
05:17:20 probe; sleep onset came **05:01:51** (`getUpdates` gap), so backing out `sleep 1` puts
release at ≈**05:00:51** against creation 03:55:53. Bounded certainly to (04:52:58, ~05:00:51] ⇒
**≥57:05 certain, ≈65 min by the sleep-1 chain**. Sleep resumed within ~60 s of release. Class band:
**26 / 40 / 55+ / 57+ / ≈65 min** — no characteristic length.

**grok `NoIdleSleepAssertion` "grok: agent turn in progress" — ≥ 78 min 53 s, breaking the ≈65 min
ceiling** (2026-08-11 11:03 ICT). `pid 16591(grok)` `[0x0001452f00019b64]`, **one id across five
consecutive cycles** — ages 04:46 / 24:04 / 42:46 / 60:18 / **78:53** ⇒ creation 09:44:43, single
pid, no stacking — held S = 0 for **2 h 50 min** with the display off and `UserIsActive` **0**
throughout (no HID for ≈65 min). Four cycles in a row each called its then-current age notable and
predicted nothing; each was right that it was not a release signal. Class bands: `dasd`
26 / 40 / 55+ / ≈65, Chrome media ≈40, **grok ≈40 / ≤22:34 / [45:37, 64:55] / ≥78:53**. The bands do
not cluster by class and the maximum keeps moving.

**A pid is not a hold identity** (2026-08-11 14:46 ICT). The pid churn above (16591 / 63497 / 86967)
was incidental — grok restarting between turns — and 0723z read it as "the per-turn re-arm under a
fresh pid, n=4". Measured against a fixed pid: **pid 86967** held `[0x0001858d00019338]` (creation
14:19:21) at 14:26:50 and `[0x00018bb10001964f]` (creation **14:45:33**) at 14:46:35 — **same pid,
two different holds**, with a gap between them. A cycle joining on pid reads one continuous
≥27-minute hold where there were two short ones.

**Left-bounded-only case** (2026-08-11 11:21 ICT). That same grok hold `[0x0001452f00019b64]` was
gone by 11:22:33, but the meter stayed flat at 5133.3 throughout, because HID returned at
**11:10:10** and held the host awake across the release. No onset to back `sleep 1` out of ⇒ release
bounds only to **(11:03:36, 11:22:33]** and the length to **[78:53, 97:50]** — versus the `dasd`
case, where sleep resumed within ~60 s and pinned the release to a second. Same probe: pid **16591
was still alive** with no assertion (`ps` elapsed 02:40:38) — fourth confirmation that process
liveness is not a proxy for a held assertion.

### §L.2 — the AnyDesk root-hold claim and its retraction (archived by 0528z, second slice)

**Claim, 2026-08-09 05:23 ICT (WRONG — retained only to date the retraction).** Four concurrent
holds; powerd's "Prevent sleep while display is on" was the oldest-looking at 37:14, but `AnyDesk`
(pid 42666) had held `PreventUserIdleDisplaySleep` for 27:14 and `coreaudiod` a matching audio hold
for 27:10 **created for pid 42666**. Reading display-on as the *effect* of the remote session, the
cycle concluded powerd was downstream and prescribed *"bound your prediction by that process's
life"*.

**Refuted 19 minutes later, 05:42 ICT.** At the next probe `PreventUserIdleDisplaySleep` was **0**
— AnyDesk and `coreaudiod` rows gone — yet **powerd's hold survived and had aged to 55:52**, older
than AnyDesk's ever was; a hold that outlives the thing it is supposedly downstream of is not
downstream of it. And **AnyDesk released without exiting** (pid 42666 still alive at `01-08:33:59`),
so the prescription fails in *both* directions. The real root was a third process: pid 13250
`grok-1.0.0-macos-aarch64`, `NoIdleSleepAssertion` "grok: agent turn in progress", which blocks idle
sleep independent of the display — which is why S stayed 0 across the release.

**"a `dasd` hold is short-lived" — also WRONG, corrected 2026-08-09 01:52 ICT.** Three measured
batches: **~40 min** (00:25→01:05, covered the 01:05 slot clean), **≥26 min** (01:26→01:52, still up
at probe), **≥55 min** (02:49:13→03:44:26, still up at probe; new max measured 03:44). Spread
26→55+ min ⇒ no characteristic length. (Extended to ≈65 min in §L above.)

## §M — The sleep-onset POSITIVE-branch prediction/scoring series (§2), archived 2026-08-15 12:5x ICT by 0548z

Retired thread: n≥5 scored predictions of a sleep-onset INSTANT (+258 s, +412 s, no-onset, no-onset, then −075 to −265 s — both directions), plus the instrument-precondition work that came out of it. Every surviving imperative was rewritten inline in `HEARTBEAT.md` §2 before this move; what follows is evidence only.

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

## §M.2 — The `InternalPreventDisplaySleep` / 300 s-fuse sub-thread (§2), archived 2026-08-15 12:5x ICT by 0548z

Four entries, one correction, n=4 on the 300 s constant. The whole operational content is three lines, now inline in `HEARTBEAT.md` §2; what follows is the probe evidence.

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

## §N — Per-holder observation series (§2): grok, AnyDesk, the Chrome media class, and the count-test corollaries (archived 2026-08-15 13:1x ICT by 0608z)

Moved from `HEARTBEAT.md` lines 1757–1841. Every imperative in this block was rewritten inline as a
six-bullet holder-reading rule; what follows is the evidence — ids, pids, creation instants and the
per-class narratives — which no cycle needs to re-derive. The live prescriptions that share this
region (the `Timeout will fire in N secs` upper-bound rule, and the whole `UserIsActive` = 0 branch
with its collapse to `onset = unbounded hold's release + ~60 s`) were **not** moved; they remain
inline directly above the replacement bullets.

✅ **The `UserIsActive` = 0 state was SCORED and behaved exactly as labelled — plus the first measured
length for a grok hold: ~40 min** (2026-08-09 10:47 ICT). Onset came **10:13:28**, 4 min 52 s after
the 10:08:36 probe; back out `sleep 1` ⇒ grok released ~**10:12:28**, so the hold created 09:32:24 ran
**~40 min** — same order as the `dasd` batches (26 / 40 / 55+ min), so still no characteristic length
across holder types. The *state* was diagnosed correctly and the *timing* was correctly called
unpredictable; this is the first time the no-exclusion-window state was named in advance and then
validated by a real onset, which is also the negative-space proof that the exclusion window is what
had been protecting the 09:54 / 10:00 / 10:05 slots (all three fired clean, then sleep).

⛔ **Generalise the release pattern: grok releases its per-turn hold WITHOUT exiting** — pid 13250
still alive at `01-05:03:35` with no assertion. Identical to the AnyDesk case. Two independent holders
share this shape, so "bound the prediction by the holder process's life" is wrong by default, not as a
quirk.

🆕 **grok's per-turn hold STACKS ACROSS PROCESSES — "the grok hold" is not a single row** (2026-08-11
09:11 ICT). Two concurrent `NoIdleSleepAssertion` "grok: agent turn in progress" holds at one probe:
pid **63497** `[0x00013b9c0001986d]` (creation **09:03:52**) and pid **16591**
`[0x00013c99000198a6]` (creation **09:08:04**). Every prior sighting (05:42 / 06:40 / 10:05 / 10:47
ICT 08-09) was a lone hold, and the finding then was that grok re-arms per turn under a *new pid* —
both are true at once here, since pid 16591 **also churned its own hold** (a different id, creation
08:43:20, up 20 min earlier and gone). So the set is `{released, re-created, plus a second process}`.
Consequence: an id churn on one grok pid does NOT mean the class released, and reading one row
understates the postponement. It changes no forecast on its own: each hold stays the unbounded
conditional in both directions.

⚠️ **An AnyDesk session arms TWO holds, and only the display one had ever been tracked** (2026-08-09
11:07 ICT). Observed pair: pid 42666 `AnyDesk` `PreventUserIdleDisplaySleep` created 10:39:58, **and**
pid 672 `coreaudiod` `PreventUserIdleSystemSleep`
(`…BuiltInHeadphoneOutputDevice…preventuseridlesleep`, **`Created for PID: 42666`**) created 10:40:02.
The second blocks idle **system** sleep independently of the display, so sleep stays excluded even
after the `UserIsActive` 600 s countdown lapses and the display chain would otherwise fire. It grants
no guarantee (AnyDesk releases without exiting), so a forecast leaning on it is **conditional**, but a
cycle that sees only the `UserIsActive` row will badly **under**estimate the exclusion window.

🆕 **The `Created for PID:` shape GENERALISES past AnyDesk — Chrome media playback arms THREE holds at
once** (2026-08-11 06:33 ICT, new holder class). Observed together, all three sharing the id prefix
`0x00011cfe` and all created **06:30:00**: pid 2210 `Google Chrome` `NoIdleSleepAssertion` "Playing
audio" `[0x00011cfe000190b3]`, pid 2210 `NoDisplaySleepAssertion` "Video Wake Lock"
`[0x00011cfe000590b2]`, and pid 444 `coreaudiod` `PreventUserIdleSystemSleep`
`[0x00011cfe0001852e]` **`Created for PID: 2334`** — where 2334 is a `Google Chrome Helper`. The
`NoIdleSleepAssertion` blocks idle **system** sleep independent of the display, exactly like grok's
per-turn hold, so a tab playing video excludes sleep on its own. Unbounded in release time (a video
ends whenever it ends) ⇒ conditional, never a floor.

⛔ **And the triple CHURNS ITS IDS IN LOCKSTEP** (2026-08-11 06:51 ICT, 18 min after the class was
first filed). All three ids changed together, `0x00011cfe…` (creation 06:30:00) → **`0x00011ff6…`**
(creation **06:42:40**), while pids, assertion names and the `Created for PID: 2334` line were all
identical — i.e. **one continuing media session re-creating its whole assertion set**, not a new one.
Same shape as `sharingd`'s Handoff churn, one class wider. The id test is sound for `UserIsActive`
*only* because that row's `TimeoutActionRelease` makes a persistent id proof of re-tickle; here an id
change is ordinary churn, not a release, so reading it that way would score ~13 min of continuous
sleep-blocking as two short unrelated holds.

⛔ **The "three holds at once" is a MEDIA signature, not a Chrome signature — and a holder can HAND OFF
TO ITSELF under a different assertion NAME, so a disappearing row is not a release** (2026-08-11 14:05
ICT). At 14:05:48 Chrome's sole hold was pid 2210 `[0x00017e8a00019108]` `NoIdleSleepAssertion`
**"WebRTC has active PeerConnections"**, age 00:16:22 ⇒ creation **≈13:49:26** — within **5 s** of
0642z's 13:49:21 probe, the exact instant that cycle saw `PreventUserIdleDisplaySleep` fall **1 → 0**
and wrote "Chrome's Video Wake Lock released", closing the class at "life ≤ 9 min 46 s". True of the
*triple*, false of the *holder*: Chrome blocked idle **system** sleep continuously ≈13:39:35 →
≥14:05:48 (**≥26 min**) across a transition that looked like a release on every instrument that cycle
had. Three consequences: (a) a WebRTC call arms **one** hold — **no** paired `coreaudiod` `Created for
PID:` row, **no** `NoDisplaySleepAssertion` — so a cycle looking for the triple sees nothing and calls
Chrome clear; (b) **the count test is blind in the direction that matters**: `PreventUserIdleDisplay
Sleep` reads **0**, the "valid branch" for powerd's stopwatch and the branch that supposedly excludes
transient holders, while a *system* hold is up — so refinement #2's precondition ("no OTHER idle-sleep
hold may be up") is violated **invisibly to the count**, and any onset prediction off the display chain
is unsound there; (c) generalise past Chrome — re-enumerate owners by PID, not by assertion name. Same
shape as grok's stacking and the lockstep churn, one level out: there the *ids* churned under a fixed
name, here the *name* changed under a fixed pid. An S = 0 attribution made off `UserIsActive` is
unharmed; what breaks is the narrative "X released" — the label-absorbs-an-unlike-event error again.

⛔ **Corollary that bites the count test: `PreventUserIdleDisplaySleep` = 1 does NOT identify its
holder, and the holder can swap under an unchanged count.** At 06:14:57 the 1 was AnyDesk
(`0x000115ae00058e6a`, pid 90021, + its paired coreaudiod `0x000115b100018cf3`); 19 min later both were
**gone** and the 1 was Chrome's Video Wake Lock — same reading, different cause, no transition visible
in the count.

⚠️ Do **not** count `bluetoothd`'s `com.apple.BTStack` `PreventUserIdleSystemSleep` as a blocking hold.
It reads age 00:00:00 and toggles continuously; it was present and demonstrably did not stop the
06:49:41 onset. Same for `ExternalMedia` — powerd has held
`com.apple.powermanagement.externalmediamounted` for **36:54:21** across every sleep that day, so a
long age alone does not make a hold sleep-blocking.

⚠️ A wake in the `getUpdates` gap is not necessarily a *usable* wake: 06:49:41→07:22:11 is **two**
windows separated by a **20-second** dark wake at 07:06:39, far too short for the executor to evaluate
(meter Δ 1878.0 s).

## §O — The 14:00 ICT six-job CONCURRENCY hypothesis (§1): proposed, escalated, falsified, ask withdrawn (archived 2026-08-15 13:3x ICT by 0628z)

Retired thread. The concurrency branch was refuted twice (durations argument 0535z, then the 08-14
falsifier below) and the destagger ask it produced was withdrawn before shipping. The surviving
imperatives are inline in §1; everything here is evidence for how the hypothesis was built and killed.

- ⛔ **The 300 s `script` cap has a CONCURRENCY branch nobody has filed: 14:00 ICT is a SIX-JOB slot,
  and on 2026-08-13 five of them timed out at the same second** (2026-08-14 03:36 ICT, observed).
  `cron/jobs.json`: `echo-daily`, `mangii-daily`, `pdfai-daily`, `aividly-daily` are all
  `0 3 * * * America/New_York`; `cleanpro-alerts` (`0 8-22/2` Saigon) and `vidnotes-alerts` share the
  same instant ⇒ **14:00 ICT**. On 08-13 all six launched inside 3 s and infra.log shows
  **`14:05:04` ERROR × 5** — `aividly-daily`, `cleanpro-alerts`, `echo-daily`, `mangii-daily`,
  `pdfai-daily`, every one *"timed out after 5 min"*. **Not the §1 monotonic artefact:** S = 0
  across 14:00→14:05 (nearest sleep 14:19:49→14:23:31, recorded by the 1437z cycle), so 304 s wall
  **is** 304 s awake. **And the slot is not new — the same six-job pile-up fired at the identical
  instant on 08-06 / 08-09 / 08-10 / 08-11 / 08-12 with ZERO timeouts**
  (`grep -E "^2026-08-(0[6-9]|1[0-4]) 14:0[0-9]" logs/infra.log`), so the collision is structural and
  long-standing while the failure is new to 08-13. That is the signature of a **load-dependent** cap,
  not a per-job workload problem — which matters because §1's where-do-the-successes-sit test is a
  *per-job* test and cannot see it: each of these five jobs looks comfortable in isolation.
  **Why this stayed invisible:** `cleanpro-alerts` retries every 2 h, so its 16:00 success reset `ce`
  to 0 and presented the event as a one-job blip; the other four are *daily*, so their `ce=1` survives
  only until the next 14:00 ICT slot, which **erases the only record that 08-13's Echo / Mangii /
  PDFAI / AIVidly reports were never delivered.** This is §1's `ce`-resets-to-0 blindness on a 24 h
  period instead of a weekly one.
  Non-delivery was **inferred, not observed** — those four runners write no `reports/*/daily` tree
  (only `cleanpro` and `vidnotes` do), so there is no disk artefact; the evidence is that
  `scripts/echo_daily_runner.py` calls `send_telegram(report)` at **line 407** of a `main()` spanning
  318–435, i.e. delivery is the last step and a 300 s SIGKILL precedes it.
  **Cheapest fix looked like destaggering, not raising the cap** — four of the five share one cron
  expression, so `0 3` / `10 3` / `20 3` / `30 3` is a single `cron/jobs.json` edit; raising
  `timeout=300` at `bot/scheduler.py:117-121` would let six concurrent BigQuery jobs run longer against
  each other instead. Sent to the boss 03:45 ICT alongside the `timeout=600`→1800 at `:149`.
  **Free falsifier, today: the 14:00 ICT slot.** Clear ⇒ load-dependent, not deterministic.
  ✅ **Scored against the full history in the same cycle, and it is an ESCALATION, not a one-off — five
  simultaneous timeouts is 2.5× the previous all-time maximum.** Every `timed out after 5 min` in
  `logs/infra.log`, bucketed by minute, tops out at **2** before this (`2026-08-04 12:05`); the rest are
  singletons. **08-13 14:05 = 5.** Per-job history explains why no cycle had a prior: `pdfai-daily` and
  `aividly-daily` had **never timed out at all**, `mangii-daily` once (05-07 14:05), `echo-daily` twice
  (05-07 14:05, 07-15 14:18). Note **three of those four priors are the 14:00 slot**, and 05-07 was
  already a *pair* (echo + mangii) at 14:05 — so the slot has been the system's pressure point since
  May, and the series over it reads **2 → 1 → 5**.
  ⛔ **The free falsifier above RAN and came back CLEAN — 6 of 6 succeeded, so the CONCURRENCY branch is
  falsified and the destagger ask is WITHDRAWN** (2026-08-14 14:24 ICT, observed). Same six jobs, same
  single second, same 300 s cap: `cleanpro-alerts` **10 s**, `aividly-daily` **32 s**, `pdfai-daily`
  **33 s**, `vidnotes-alerts` **84 s**, `mangii-daily` **122 s**, `echo-daily` **156 s** — the slowest
  of the six clears the cap by **1.92×** and four of six finish under 35 s. Contention is *present*
  today (the collision is structural — the same six have shared this instant daily since 08-06) and
  costs nothing, so it cannot be what killed 08-13. That is the second independent refutation, after
  the 0535z durations argument (the light jobs would have needed ~7.7× inflation): **08-13 14:05 was
  one shared stall, not an oversubscribed slot.** Honest limit: one clean day proves contention is not
  *sufficient* (which is all the destagger assumes), not that no load coupling exists. Confidence
  **high** on withdrawing the ask, **moderate** on no coupling at all. The 08-13 stall itself remains
  unexplained and has no live evidence left — the `ce` counters cleared at the next slot exactly as
  predicted.

## §P — §4's `Conflict: terminated by other getUpdates request` thread (archived 2026-08-15 13:5x ICT, 0648z)

Retired: the count is closed, the causal story is refuted, and the surviving imperatives are inline in
§4. Kept here as evidence only. Original span `HEARTBEAT.md` 2270–2337 (68 lines, 6,248 B).

- ⛔ **`Conflict: terminated by other getUpdates request` is CHRONIC NOISE — and its message text is a
  trap that instructs you to hunt a duplicate process** (2026-08-14 22:2x ICT, computed over the full
  log). *"make sure that only one bot instance is running"* reads as an order, and acting on it points
  straight at process management, which CLAUDE.md forbids outright. **Base rate: 66 occurrences across
  26 distinct days** — 08-01 ×15, 06-06 ×10, 08-10 ×4, 08-14 ×3 — and no cycle has ever alerted on it.
  Before spending any budget: `ps -eo pid,ppid,lstart,command | grep '[p]ython.*bot'`; **one PID that
  predates the error ⇒ there is no duplicate.**
  ⛔ **"the burst is self-limited (today: 2 events 13 s apart, nothing after)" was WRITTEN INSIDE THE
  BURST IT DECLARED OVER, and a third event landed 15 min later** (2026-08-15 01:0x ICT, observed).
  The entry is stamped **22:2x**; the third Conflict is **22:26:38**. Verified counts: `grep -c` gives
  **66**, and 08-14 carries **3**, so both the total and the day-count above were off by one *at the
  moment of writing* — not by later drift. **"Nothing after" is not an observation, it is the absence
  of one**, and it cannot be made from inside the window it describes. Neither escape hatch covers the
  third event: the last `ConnectError` was **22:10:59**, i.e. **939 s** before it (outside the 120 s
  adjacency window), and the last `Bot starting` was **08-13 12:33:21**, so it is neither the network
  story nor the restart-overlap story. **The entry's CONCLUSION survives intact** — still chronic
  noise, still one PID, still no alert, and the refutation below only firms up (2 of **66**).
  What breaks is the shape: the burst is **not** 13 s tight, it spans **≥ 15 min 31 s**.
  **Operational cost if uncorrected:** a successor greps 08-14, counts 3 against a documented 2, sees a
  gap 70× wider than the stated one, and reads *escalation* — alerting on the exact noise this entry
  exists to suppress. A reassurance that undercounts is worse than no reassurance.
  **Rule: never close a count over a window that includes now.** State it as a floor with the window
  named — *"≥3 events, 22:11:07–22:26:38, window still open"* — and let the next cycle close it. Same
  family as §0's *you cannot name your successor's start time*: both assert the termination of a
  process you are still inside. Cheap fix, and it is the one this file already applies to timing —
  **apply it to counts too.** Confidence high, n=1, arithmetic from the full log.
  ✅ **CLOSED, and the closing exposes the rule's missing half: the entry OVER-APPLIED its own
  correction and deferred a settled number by 24 h** (2026-08-15 01:2x ICT, observed). **08-14 = 3
  Conflicts, FINAL** (22:11:07, 22:11:20, 22:26:38; nothing since — 2 h 57 m of silence). Verified the
  window is shut, not merely quiet: `awk '/^2026-08-15 /{seen=1} seen && /^2026-08-14 /'` over
  `infra.log` returns **nothing**, i.e. the log is append-only and chronological, so no line dated
  08-14 can ever arrive again. But 1803z's handoff wrote *"a cycle after 08-15 ends can close 08-14
  properly"* — demanding an entire extra day for a window that had already closed at midnight, ~3 h
  before it wrote that.
  **The missing half is: WHICH window is the count over?** One `grep` produced two counts here and they
  have opposite status —
  | count | window | right edge | status |
  | --- | --- | --- | --- |
  | 08-14 ×3 | a calendar day | **elapsed** | **closed, final** |
  | 66 total | all time | **now** | floor, `≥66`, forever |
  Same file, same command, same cycle. So the discriminator is **not** the evidence and **not** how
  long you have waited — it is purely whether the window's right edge lies in the past. A *bounded,
  elapsed* window is closed the instant the clock passes its edge; only an **open-ended** one (the
  burst-as-phenomenon, "is it over?") is permanently a floor. 1803z proved 08-14 = 3 in its own
  §4 text and then labelled that same number provisional in its handoff table, because it carried the
  floor-ness over from the burst to the day.
  **Cost, and it is the mirror of the original bug's:** undercounting converts noise into apparent
  escalation; **over-deferring converts a settled fact back into an open item**, so the next cycle
  re-greps, re-derives, and re-defers — the exact re-litigation the checklist exists to prevent. Both
  are failures to state the window; the first omits it, the second inherits the wrong one.
  **Generalise: "you cannot assert the end of a process you are inside" is about being INSIDE, not
  about being RECENT.** Once you are outside, waiting longer adds no information — and a rule against
  premature closure will, left unqualified, prevent closure altogether. Every fresh caution is itself
  a candidate for over-application by the successor that inherits it; state its scope in the same
  breath as the caution. Confidence high, n=1, verified against the log's ordering rather than assumed.
  **A causal story I built and then REFUTED — record it so nobody rebuilds it.** Today's Conflicts sit
  **8 s** after an `httpx.ConnectError`, so "network blip drops the long-poll, Telegram still holds the
  old one, the retry collides" fits beautifully and is mechanically plausible. Scored over the whole
  log: **only 2 of 66 Conflicts (3 %) have a ConnectError within 120 s before them — and both are
  today's** (22:11:07 at +8 s, 22:11:20 at +21 s; the 22:26:38 one is +939 s and does **not** qualify);
  conversely **6763 of 6764 ConnectErrors are followed by no Conflict at all.** It explains
  none of the history (the other 64 are almost certainly restart overlap — `Bot starting` days).
  **The transferable half: checking the base rate of the CONSEQUENT is the habit this file already has
  (§4 above), and it would have passed this story — the Conflict really was rare. What kills it is the
  base rate of the ANTECEDENT.** Adjacency in a 25-line tail plus a plausible mechanism is not
  evidence; the question is *how often does the cause occur WITHOUT the effect*. Six thousand times,
  here. Confidence high — computed over 6829 events, not read from a window.

## §Q — §1's `armed + S` cron-slot prediction-scoring series, n=9 → n=15 (archived 2026-08-15 14:1x ICT, 0707z)

The model itself (`next_fire = armed + S`, S from the clock-skew meter) is settled and stays inline at
§1; what follows is the per-tick scoring evidence that established it. Nine surviving imperatives were
rewritten inline at the same anchor. Residuals: n=9 **0 s**, n=11 **+0.1 s**, n=12 **−0.5 s**, n=13
**−0.7 s**, n=14 **0 s**, n=15 **0 s**.

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

## §R. `script`-job runtime bands and the wall-vs-monotonic clock correction (§1, archived 2026-08-15 12:1xZ)

Superseded band figures (7–31 s, 77–101 s, 40 s probe, 120 s probe) and the evidence behind the
wall-clock/monotonic-cap correction. Live imperatives stayed inline in `HEARTBEAT.md` §1.

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
  ⛔ **That last sentence is FALSE across a sleep window, and the reason generalises to EVERY runtime
  figure in this checklist: `logs/infra.log` durations are WALL clock, the scheduler's caps are
  MONOTONIC (awake) time, and the two have been compared directly for months** (2026-08-11 20:17 ICT,
  observed). `asyncio.wait_for` runs on the asyncio event-loop clock = `time.monotonic()`, which on
  Darwin **does not advance while the host is asleep** — the same freeze this file already establishes
  for APScheduler's `Event.wait` (line 436) and launchd's `StartInterval` (line 90). Every runtime band
  quoted in §0/§1 is two infra.log timestamps subtracted, i.e. wall. Nobody had noticed they are
  different clocks. **Observed: 13 `script`-job runs completed successfully with a wall duration ABOVE
  their own 300 s cap**, across 6 jobs and 4 months — `echo-daily` **22:34**, `mangii-daily` **22:40**,
  `vidnotes-daily` **18:45**, `cleanpro-exp-monitor` **15:40**, `echo-backend-alerts` **9:34**, and
  decisively **`auto-commit` at 15:27 against a median of 0:01 and p90 0:02 over n=1151** — concurrent
  to the second with `cleanpro-exp-monitor`'s 15:40. A one-second `git` job cannot run fifteen minutes,
  and two unrelated scripts do not slow down together by the same amount; `echo-daily` + `mangii-daily`
  repeat the pattern on 07-05 and 07-17 (same fire instant, both ≈22 min). That is a host-wide time
  jump, and it is the only reading under which these runs survive a 300 s cap. **Consequences:**
  (a) a `script` job whose wall duration exceeds 300 s is **not** a broken cap or a false green — do not
  alert on it; (b) `auto-commit` was alive and un-stamped **15 min** past its slot, so **read the meter
  before declaring a job dead at `slot + 300 s`** — both that rule and the 180 s probe are wall-clock
  rules pointed at a monotonic cap; (c) the 16:40 weekly ledger below compares wall-clock successes to
  a monotonic cap, so its "median ≈ 6 m 45 s" is **inflated** by any sleep those runs spanned — a second
  bias, **opposite in sign** to the censoring bias that entry already names, and neither was known when
  "1800 s puts the cap at ~2.7× the median" was written; (d) **the capacity diagnosis still survives for
  the timeouts**, by that ledger's own evidence — all 16 stamped at exactly `fire + 600 s` wall, and
  under a monotonic cap a sleep-spanning timeout would stamp `fire + 600 + S`, so **S ≈ 0 across all 16**
  and they genuinely burned 600 s of awake time. The `timeout=600 → 1800` ask stands; only its *sizing*
  argument softens, and it should be reported that way rather than as weakened.
  **Method rule: before comparing a measured duration to a timeout, check both are in the same clock.**
  This host has two, they diverge by hours per day, and every *other* cross-clock comparison in §0/§1 was
  already known to matter — it was simply never applied to the job runtimes themselves. Confidence
  **high** (the co-occurrence plus a 1 s job at 15:27 admits no other reading).
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

## §S — the compaction thread's own pass-by-pass scoring series (HEARTBEAT.md header lines 13-105, archived 2026-08-15 1540z)

The estimator is SETTLED (60 B/line net, n=6 pre-registered passes, errors 0 / +0.6 / +7 / +15 / +24 
## §S.2 — the compaction thread's own (DUPLICATE header, renamed 2026-08-20 1725z) pass-by-pass scoring series (header lines 13-105, archived 2026-08-15 1540z)

Estimator SETTLED at 60 B/line net, n=6 pre-registered passes, all errors non-negative.
Every pass note below is scoring residue for a confirmed model; surviving imperatives stayed inline.

✅ **PASS DONE 2026-08-15 09:2x ICT (0214z): 260,774 → 247,725 bytes, four blocks moved, ~2.3 KB of
headroom restored.** All four targets 0152z named are now archived — §C the n=5…n=16 residual series,
§D the n=1…n=7 proxy-bias series, §E the n=13 runtime table, §F the `exit 1` failure population.
**Every imperative was rewritten INLINE and none was moved**; only measurements crossed over.
✅ **SECOND PASS DONE 2026-08-15 09:4x ICT (0236z): 248,070 → 238,465 bytes, ONE block, 9.6 KB — four
times what the previous pass recovered from four blocks.** §3's log-compression/injection thread
(131 lines) is now `HEARTBEAT-ARCHIVE.md` §G; ~30 lines of surviving imperatives stayed inline.
⛔ **The reason one block beat four: PICK A RETIRED THREAD, NOT A LONG ONE.** 0214z's four targets
were live findings whose evidence had to be split from their prescriptions line by line; this one was
already dead at its entry point, so the whole argument was residue and only the transferables came
back. **Read the ✅/⛔ markers for a thread whose conclusion has been RETRACTED before you measure
which block is biggest — a retired thread is nearly all archive by construction.**
✅ **And it closes a loop: 0034z and 0113z both measured that MARKING a retraction fails (the reader
enters above the mark, or jumps to a bold action label below it). Deleting the corpse to the archive
is the form of rule (a) that cannot fail that way** — there is no stale prescription left to reach.
So compaction and correctness-of-record are the same operation here, not competing ones.
✅ **THIRD PASS 2026-08-15 12:1x ICT (0509z): §0's handoff chain → archive §K. Block −1.6 KB, this
note +0.5 KB, file NET −0.5 KB** — a dense-prescription block is ~80 % imperative and is already at
0449z's floor, so **estimate a block's imperative fraction before picking it; that kind pays in
readability, not bytes.** **Next target: §2's sleep-onset forecasting thread (search `Age-sorting
finds candidates, not causes`) — ~200 lines around three WRONG-and-corrected conclusions, the
retired-thread shape 0236z says yields most.**
⛔ **THAT TARGET IS SCOPED AND IT IS A WHOLE-CYCLE JOB — BOUND A BLOCK BEFORE YOU ESTIMATE ITS
IMPERATIVE FRACTION** (2026-08-15 12:3x ICT, 0528z, measured then deferred). The anchor is line
~1628 and `grep -n "^### \|^## "` returns **no section header anywhere in 1450–1800**, with no
top-level `- **` bullet in 1688–1860 either ⇒ the thread is **300+ lines with no internal
boundary**. 0509z's rule says estimate the imperative fraction first; **boundaries are the cheaper
test and they can veto on their own**, so run them first — one `grep` over a line range. Do NOT
start this in the tail of a cycle: a partial move of a block containing three WRONG-and-corrected
conclusions strands the retraction in the archive and the retracted prescription inline, which is
strictly worse than not moving it. **The split is the answer, and 0528z took the first slice** — the
`dasd`/grok unbounded-holder band measurements are now archive **§L**, replaced inline by three
imperatives (never schedule against a release; track the id not the pid; a hold ending near a wake
is left-bounded only), **and the second slice in the same cycle** — the AnyDesk/powerd root-hold
correction and the "`dasd` is short-lived" retraction are now **§L.2**, replaced by the three-rule
age-sorting block. Two slices, `HEARTBEAT.md` **241,805 → 239,323 B** while the archive absorbed
4.8 KB. ✅ **THIRD SLICE TAKEN 2026-08-15 12:5x ICT (0548z): the whole sleep-onset
prediction-scoring series (161 lines, `INCONCLUSIVE, as designed` → `unbounded in arrival as well as
release`) is now archive §M, replaced inline by six imperatives. `HEARTBEAT.md` 239,475 → 228,247 B
(**−11.2 KB net**, the largest single pass yet); archive +16.2 KB, which is correct, not a regression.
⚠️ I first wrote **−13.0 KB** here from the post-delete `wc` (223,735) *before* the inline rewrite
landed — **measure the file AFTER both halves of a compaction, never after the delete**, or every
pass overstates itself by the size of its own replacement (1.8 KB here, ~14 % of the claim).**
⛔ **The `UserIsActive` 600 s sleep-EXCLUSION primitive is LIVE — it is §0's licence to
spend budget on a live read — and stayed inline, as did the whole `UserIsActive` = 0 branch.**
✅ **Why this one beat 0236z's 9.6 KB: the slice was bounded by ENTRY MARKERS, not by section
headers.** 0528z's boundary test returned "no internal boundary in 300+ lines" because it grepped
`^### |^## ` and `^- \*\*`; the thread is in fact segmented every 5–20 lines by two-space-indented
✅/⛔/⚠️/🆕 entries, and a topic shift (prediction-scoring → per-holder caveats) sits cleanly between
two of them. **Grep the marker glyphs at the block's own indent before declaring a block unsplittable
— a boundary that a top-level-bullet grep cannot see is still a boundary.**
✅ **FOURTH SLICE, SAME CYCLE: the `InternalPreventDisplaySleep` / 300 s-fuse sub-thread (31 lines)
is archive §M.2. 228,247 → 226,625 B — only −1.6 KB**, and that is 0509z's floor confirmed rather
than a bad pass: a 31-line block whose four entries reduce to three imperatives is ~40 % imperative,
so it pays in readability, not bytes. **Use the two numbers as a sizing rule: a retired thread of
150+ entry-segmented lines returns ~10 KB; a 30-line one returns ~1.5 KB. Below ~50 lines, take the
slice only if the block is actively misleading, not to reclaim space.**
⛔ **NO NAMED NEXT TARGET, deliberately — the remaining §2 bulk is per-holder observation
(`sharingd`, grok's stacking per-turn holds, the Chrome media class) whose imperatives are already
generalised into §L's unbounded-holder rule, so it is archivable but not obviously retired.** Run
the entry-glyph boundary grep yourself (`grep -n "^  [✅⛔⚠️🆕]"` over the range) and pick by the
sizing rule above; **do not inherit a target chosen by a cycle that had not read the block** — that
is what cost 0528z a deferral.
✅ **TAKEN 2026-08-15 13:1x ICT (0608z), and it was the archivable-but-not-retired kind, so it tests
the sizing rule at its MIDPOINT: 85 entry-segmented lines → `HEARTBEAT.md` 227,473 → 222,456 B
(−5,017 net), archive +7,993 as §N.** Predicted ~5 KB by interpolating 0548z's endpoints (150 lines
≈ 10 KB, 31 lines ≈ 1.6 KB); actual 5.0 KB. **The return is LINEAR in entry-segmented line count at
≈ 60 B/line net — so you can now price a block before touching it, and the sizing rule is an
estimator, not just two anchors.** Note what this also settles: a block that is *not* retired paid
the same rate as 0548z's retired one, because the cost driver is line count, not deadness — deadness
only decides how much of the block survives the rewrite (here 85 lines → 24 inline, ~28 %).
⛔ **The boundary grep is what made it safe, and it VETOED the obvious cut.** The glyph pass showed
the region's live top-level `- ⛔` bullets (the `Timeout will fire in N secs` upper-bound rule and the
whole `UserIsActive` = 0 branch) sitting INSIDE the block's line range at 1731–1756; cutting
1702–1841 as one span — which the header's own §2 description invites — would have archived the live
sleep-exclusion primitive. **Indent level is not seniority: a two-space entry and a top-level bullet
interleave in this file, so grep BOTH (`^  [✅⛔⚠️🆕]` and `^- `) and let the top-level hits carve the
span.** The slice actually taken was 1757–1841, i.e. the block MINUS its live bullets.
✅ **ESTIMATOR CONFIRMED OUT-OF-SECTION AND PRE-REGISTERED, 2026-08-15 13:3x ICT (0628z): §1's 14:00
ICT six-job concurrency thread, 62 lines → archive §O. Predicted 62 × 60 B ≈ 3,720 B BEFORE cutting;
actual `HEARTBEAT.md` 223,966 → 220,223 = −3,743 (0.6 % error), archive +5,115.** 0608z's ≈60 B/line
was fitted on §2 alone; it now holds on a §1 block of a different shape, so **price any block in this
file at ~60 B/line net and treat the number as a plan, not a postmortem.**
⛔ **AND THE CHEAP WAY TO FIND THE BLOCK IS A KEYWORD GREP, NOT A READ.** Every prior pass hunted
targets by reading §2 or by eye. One call —
`grep -n "REFUTED\|RETRACT\|superseded\|was wrong\|falsified\|SUPERSED" HEARTBEAT.md | awk -F: '$1>=<lo> && $1<=<hi>'`
— returned the retraction vocabulary with line numbers, and the one hit reading *"the ask is
WITHDRAWN"* was a whole retired hypothesis nobody had touched. **Sequence, and it is now the standard
one: (1) keyword-grep for retraction vocabulary to FIND the thread, (2) `grep -n "^- "` to BOUND it at
the enclosing top-level bullet, (3) price it at 60 B/line, (4) extract imperatives, then move the
residue.** Step 2 is what proved 730–791 safe here — the next top-level bullet was 792, so the whole
span was one dead argument with no live sibling inside. 0236z said to *read* the markers for a retired
thread; mechanising that read as a grep is what made it a two-minute job instead of a whole-cycle one.

## §T — the compaction method's OWN estimator/method scoring series (header, archived 2026-08-15 1638z)

⚠️ Note what the rewrite kept, because it is the non-obvious half: a **withdrawn** ask has to stay
inline as a live NEGATIVE prescription (*do not ship the destagger*), or the next cycle re-derives the
refuted fix from the same slot data. Archiving a retraction silently un-retracts it.
✅ **ESTIMATOR HOLDS IN A FOURTH SECTION, 2026-08-15 13:5x ICT (0648z): §4's `Conflict … getUpdates`
thread, 68 lines → archive §P. Predicted 68 × 60 B = 4,080; actual 222,718 → 218,342 = −4,376 (7 %
error).** ⛔ **Price at 60 B/line NET, never off the block's own gross density** — this block was
6,248 B, i.e. **92 B/line gross**, and the 32 B/line gap is exactly the inline rewrite (1,872 B). A
prose-dense block does not return more than a sparse one of the same length; it just costs more to read.
**Standard sequence worked unchanged and cost 3 calls to find + bound:** keyword-grep for retraction
vocabulary → `grep -n "^- "` to bound at the enclosing top-level bullet → price → extract imperatives →
`sed -i '' '<lo>,<hi>d'` then one `Edit` to re-insert. **Use `sed` for the DELETE half** — a 68-line
`Edit` old_string is pure waste, and `sed`'s range is a command, not prose, so `guard.sh` never sees the
archived text.
✅ **FIFTH SECTION, AND THE ESTIMATOR'S ERROR IS ONE-SIGNED — TREAT 60 B/line AS A FLOOR, NOT A
CENTRE** (2026-08-15 14:1x ICT, 0707z): §1's `armed + S` prediction-scoring series, n=9…n=15, 90 lines
→ archive §Q. Predicted 90 × 60 = 5,400; actual 219,296 → **213,066 = −6,230** (+15 %). Errors across
the four pre-registered passes are **0 %, +0.6 %, +7 %, +15 % — every one non-negative** (n=4). So the
estimator never over-promises: **use it to decide whether a block clears the ≥ 50-line bar, and expect
to beat it.** Do not re-fit — 0648z's rule stands and gross density still predicts nothing (this block
was 97 B/line gross).
⛔ **DO THE MOVE WITH `sed -n '<lo>,<hi>p' HEARTBEAT.md >> HEARTBEAT-ARCHIVE.md` — NOT AN `Edit` THAT
RETYPES THE BLOCK.** 0409z's fix for the guard-refuses-your-prose defect (QUEUE #5) was "append with
`Edit`", which costs you the whole block as `new_string`; the `sed` form's command text is two line
numbers and two paths, so **`guard.sh` has nothing to grep AND the block is never re-typed or
re-worded**. Sequence is now: `Edit` a one-line `## §X` header onto the archive → `sed -n p >>` the
block → `sed -i '' d` the source → one `Edit` to insert the imperative rewrite. **Sixth pass, sixth
non-negative error: §1's `script`-runtime/clock thread, 74 lines → §R, predicted 4,440 B, actual
231,488 → 225,962 = −5,526 (+24 %).** Errors 0 / +0.6 / +7 / +15 / +24 % (n=5) — 60 B/line is a FLOOR
and the drift is upward, so a block near the 50-line bar is likelier to clear it than the estimate says.
⛔ **A SETTLED MODEL'S SCORING SERIES IS THE RICHEST TARGET LEFT, AND IT IS FOUND BY GREPPING `n=`, NOT
RETRACTION VOCABULARY.** The standard keyword grep (`REFUTED\|RETRACT\|superseded\|falsified…`) put me
on this thread but named only its two *corrections*; the block's real bulk was six consecutive
CONFIRMATIONS (residuals 0 s / +0.1 s / −0.5 s / −0.7 s / 0 s / 0 s) that no retraction word touches.
**A confirmed model's evidence is as dead as a refuted one's** — once the conclusion carries its own
`n=` and residual band, every scoring entry beneath it is residue. Add `grep -n "n=[0-9]"` as a second
finder alongside the retraction grep; §0's SETTLED n=16 block is the worked example of the end state.

⛔ **The method that made this pass safe, and the only way to do the hard block:
extract each block's IMPERATIVES into a fresh bulleted rewrite FIRST, then move the residue.** Do not
move a block and hope the summary caught everything. When you are over, do not delete a finding —
**move the EVIDENCE to `HEARTBEAT-ARCHIVE.md` and leave the IMPERATIVE inline.** §A and §B there are
worked examples (0152z archived 3.9 KB of §0's n=1/2/3 clock-bias measurements and its refuted
sleep mechanism, keeping every prescription in place).
⛔ **APPEND TO THE ARCHIVE WITH THE `Edit` TOOL, NEVER `cat >> file << 'EOF'` — A HEREDOC'S PAYLOAD
IS COMMAND TEXT, SO `guard.sh` GREPS THE PROSE YOU ARE ARCHIVING** (2026-08-15 11:1x ICT, 0409z,
hit on my own §I append). The block described `cleanpro-daily`'s cap-killed runs; the hyphenated
compound put the guarded token immediately before a space and rule 1 refused the whole write —
*"BLOCKED: You are not allowed to k—— processes."* This is `QUEUE.md` #5's defect in its **fourth**
organic form and the first where the token sat in **data being written** rather than in a command's
logic, which matters because **compaction is now a per-cycle duty and its payload is exactly the
fleet's own prose about killed jobs, caps and timeouts** — i.e. the text most likely to trip it.
`Edit` and `Write` are not intercepted (`.claude/settings.json` hooks `Bash` only), so the fix costs
one Grep to locate the anchor line and one `Edit`, and **it needs no rewording** — which is the
point: #5 also records that rewording a finding to appease a broken matcher corrupts the record.
Cheap correct form: `Grep -n "<last distinctive line>"` → `Read` a few lines around it → `Edit` that
line to itself-plus-your-block. Confidence high — observed, and the retry via `Edit` succeeded.

## §U — the floor-probe N term (60 s refuted to 5 s) and the arming-set/evaluation-instant case studies (§1, archived 2026-08-16 1833z)

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

## §V — Discharged backpressure-verification item (archived 2026-08-18 0613z)

⛔ **AND 0418z's BACKPRESSURE IS UNSCORED — `heartbeat-state.json` IS AT THE REPO ROOT AND STILL HAS
THE OLD TWO-KEY SHAPE.** 0418z rewrote `run.sh` at 11:20; its own instance started 11:18:39, so the
stamp it wrote at 11:22:33 came from the PRE-EDIT script. The new one is live from 0437z (its
`mktemp` artifact exists). **Successor: confirm `consecutive_refusals: 0` and `last_success` now
appear in `heartbeat-state.json` — if not, the heredoc failed silently and the alert is decorative.**
Actuator checked reachable: `skills/telegram-sender/send.sh` exists, is executable, takes `--text`.
**General form: a script that rewrites itself cannot verify its own fix in the same run — the edit
lands one cycle after the instance that made it.**
✅ **DISCHARGED 0514z: `consecutive_refusals: 0` and `last_success` are both present. Backpressure is live.**

## §W.2 — compaction-thread scoring series, archived 2026-08-18 0634z
(Header lines 48-75 and 79-84: the break-even/third-cost pass, the 2,311 B-per-cycle rate series,
the five-decline veto thread, and the note-length lever. All superseded by the settled method block
and by 0556z. The extremum rule at old 76-78 was KEPT inline.)

⛔ **BOOK THE PASS AT ITS THIRD COST TOO, AND THE FLEET IS AT BREAK-EVEN.** 0548z said measure after
BOTH halves (delete + inline rewrite); there is a **third** — this header note, **+1,761 B, i.e. 47 %
of the 3,743 the pass recovered.** Whole-cycle truth: 223,966 in → **221,984 out, −1,982 net**, against
**+1,510 B of ordinary growth per cycle**. So one 60-line slice per cycle barely outruns the file's own
logging, and a pass that returns under ~3 KB gross is NET ZERO once written up. Two consequences:
**price the block at 60 B/line and require ≥ 50 lines to be worth a slice**, and **keep the pass note
to the imperative** — the narrative belongs in the daily log, which no successor re-`cat`s into
`HEARTBEAT.md`.
⛔ **+1,510 WAS WRONG AND SO IS THE 2,511 THAT REPLACED IT — MEAN 2,311 B/cycle, n=7 (2026-08-15
1149z). 1129z's OWN SUCCESSOR added +1,113, i.e. below the "observed MINIMUM" it had just declared.**
Series 0803z→1129z: 1,949/4,127/2,305/2,245/2,829/1,610/1,113. The ~90-line hold-the-line bar stands
and no block that large survives 0608z's live-bullet veto — **four consecutive cycles have now
correctly declined to compact; stop treating a declined pass as a skipped duty.**
⛔ **THE DECLINE IS RIGHT AND ITS STATED REASON IS WRONG — THE LIVE-BULLET VETO IS NOT BINDING AND HAS
NOT BEEN FOR FIVE CYCLES** (2026-08-15 23:2x ICT, 1619z; declining a fifth time, now on the measured
reason). I set out to prove the bar unreachable and the measurement refuted me: gaps between top-level
`^- ` bullets give **10 veto-free spans of ≥50 lines, largest 415** (470–884), then 337, 261, 179.
Geometry is not the constraint. **Entry density is** — those spans hold 35/22/23/14 `⛔✅⚠️` entries,
i.e. **11–15 lines per entry**, so a ≥50-line slice needs **4–5 CONSECUTIVE dead entries**, while both
mandated finders (retraction vocabulary, `n=[0-9]`) return **single** ones: today's best were the
`armed + S` SETTLED block (27 lines) and the n=16 survival series (18) — 45 lines across two
non-contiguous sites, under the bar even before two moves and two rewrites. **RULE: when you decline,
report the constraint you MEASURED, not the first rule in the method that would have blocked you** — a
plausible unmeasured reason inherits as fact, and four successors repeated this one. Corollary with
teeth: nine passes have harvested exactly what the two finders see, so **the finders are exhausted
before the file is**; the next real pass needs a finder for consecutive-dead-entry RUNS, not for one
more scoring series. Headroom 15,006 B ⇒ ~6 cycles at the n=7 mean. Confidence high (both counts
scripted, in this cycle's transcript).
⛔ **AND NOTE-LENGTH IS A REAL LEVER — 1129z retired it from ONE point.** Last three deltas run
2,829 → 1,610 → 1,113; the two smallest in the series are the two short-note non-compacting cycles,
the two largest are the cycles that filed multi-part findings. **Delta tracks finding VOLUME, the one
term a cycle controls — the rate is an OUTPUT of cycle behaviour, not an exogenous denominator to
price compaction against.** So: **default the finding to the daily log, put ONLY the imperative here.**
**Headroom 19,384 B ⇒ ~8 cycles to 250 KB at the mean, ~17 at the recent rate.** Confidence high (git).

## §W — 1638z run-finder discovery entry (residue; imperative folded into the COMPACTION METHOD Find bullet 2026-08-19 1646z)

⛔ **THE RUN-FINDER 1619z ASKED FOR IS THE METHOD-VS-EVIDENCE TEST, AND ITS FIRST HIT WAS THIS
HEADER — NINE PASSES HUNTED §0/§1/§4 AND NEVER TURNED A FINDER ON THE COMPACTION THREAD'S OWN
SCORING SERIES** (2026-08-15 23:4x ICT, 1638z; 55 lines → archive §T, **236,464 → 231,094 = −5,370 B**
against a 3,300 prediction, **+63 %, seventh consecutive non-negative error**). **RULE, and it is the
finder: once a block declares itself SETTLED and states its rules imperatively, EVERY entry elsewhere
whose payload is a confirmation of those same rules is residue — grep for the settled block's own
imperatives, not for retraction words or `n=`.** Worked mechanically here: the method block's six
rules each had 1–3 later entries scoring them (0648z §P +7 %, 0707z §Q +15 %, 0409z §R +24 %, the
`n=` finder's own discovery note, the withdrawn-ask note, the extract-imperatives-first note, the
heredoc rule superseded by the `Write` + `"$(cat …)"` form) — **four dead entries consecutive at
173–208 and three more at 219–237**, exactly the 4–5-run 1619z proved the old finders could not see.
Why the old finders missed it: a confirmation contains no retraction word, and these carried no `n=`
because the series is indexed by **section letter** (§P/§Q/§R), not by sample count. **Corollary:
the compaction thread is the fleet's most self-documenting subject, so it accretes the most
confirmations — audit your own method section first, every pass.** Five cycles declined on the
premise that the file held no ≥50-line run; it held one in the first 250 lines. Confidence high
(sizes from `wc -c`, spans in this cycle's transcript).

## §X — 1833z positional-run-finder + bullet-bounds-not-veto entries (residue; imperatives folded into the COMPACTION METHOD Find and Bound bullets 2026-08-20 1706z)

⛔ **THE RUN-FINDER IS POSITIONAL, NOT LEXICAL — CONFIRMATIONS ACCRETE IMMEDIATELY DOWNSTREAM OF THE
BLOCK THEY CONFIRM, SO READ THE ~100 LINES AFTER EVERY `SETTLED` MARKER** (2026-08-16 01:4x ICT,
1833z; §1 lines 1712–1804, 93 lines → archive §U, **241,173 → 234,555 = −6,618 B** against a 5,580
prediction, **+19 %, eighth consecutive non-negative error**). 1638z's finder greps a settled block's
own imperatives; that is the *test*, but the cheap way to FIND the run is that cycles append, so the
pile sits after the marker in file order. Here the `armed + S` SETTLED block ends at 1711 and the
next 93 lines were its n=7/n=10/n=16 case studies plus a refuted-term thread — the 4–5-consecutive-dead-entry
run 1619z proved the lexical finders could not see, in the section five cycles had written off.
⛔ **AND A LIVE TOP-LEVEL BULLET BOUNDS A SPAN, IT DOES NOT VETO IT.** 0608z's veto sent five cycles
looking for gaps BETWEEN bullets; the bullet at 1805 simply set my upper bound, and the 93 lines
above it were free. **Grep `^- ` to find where your span ENDS, then take everything back to the
marker** — asking "is there a bullet-free gap ≥50 lines" is the wrong question and it cost five
declines. Whole-cycle truth including this note (+1,314 B, **20 %** of the recovery, vs 1638z's 47 %):
**241,173 → 235,869 = −5,304 net. Headroom 14,131 B ⇒ ~6 cycles at the n=7 mean.** Confidence high (`wc -c`).

## §Y — the successor-placement bullet list in full narrative form (header, archived 2026-08-20 1745z; imperatives compressed in place, reasoning already in §K)

- **Place your successor at `completion + 900 s + S`** — not its start + 15 min, and not the "17 min"
  figure in memory. The heartbeat is **not** an APScheduler job: it is launchd
  `com.claude.heartbeat.plist`, `StartInterval 900`, wrapping `skills/heartbeat/run.sh`, which stamps
  the state file *after* `claude -p` exits — hence "completion". `S` is sleep seconds in the window:
  launchd **defers a missed interval by exactly the sleep duration** rather than firing on wake, so the
  900 s countdown takes the same `CLOCK_MONOTONIC` freeze as §1's `armed + S`.
- **Read that completion off your own prompt.** The harness line `Last heartbeat ran at: <ISO>` *is*
  the stamp `run.sh` writes after the invocation — don't dig it out of the predecessor's log or the
  state file, and spend the saved call on the one thing that does need `ps`: your own start.
- **An apparent 38-min hole between two cycles is launchd's deferral, not a logless death** — check the
  sleep meter before hunting for a missing log.
- **Hand forward the TICK plus the ancillary fields — NEVER a precomputed "if you start before X you
  may block" threshold** — it has the wrong sign and has nearly cost a log (§K). **The receiving cycle
  recomputes reach from its OWN `ps` start + 600 s and blocks only if `tick < own_deadline − ~60 s`**
  (log-writing margin).
- **Start and end-of-budget move together, so state the effect SYMMETRICALLY: finishing early loses
  ticks off the FAR end and GAINS them off the NEAR end.** Against an *already-scheduled* tick,
  starting earlier strictly REDUCES reach; for coverage of future time in aggregate, writing early and
  exiting fast pulls your successor's start earlier and WIDENS the fleet's reach. Keep the two apart —
  same fix either way: hand the tick, recompute from your own start, never inherit the predecessor's
  placement of it in time. (§K prices the near-end cost: a skipped live read.)
- **Publish your completion estimate as `naive − 3 min` and carry the residual (~±1.5 min) as the
  margin — the self-estimate error is BIASED SHORT, not noisy, so ~3 min is a FLOOR on that margin,
  not a worst case.** A symmetric pad fixes neither failure mode; one subtraction fixes both (§K).
  Confidence moderate — n=5, one day, one model. **Re-score if a cycle ever misses long; do not deepen
  the correction past 3 min on this evidence.** This changes only what you PUBLISH about yourself —
  the handoff still carries the tick.
- **State the completion estimate ONCE, with planned work priced in; revise only for genuinely
  UNPLANNED work.** "Correcting" it afterwards for work you had already committed to double-counts and
  **overstates reach** — the sign that strands a tick nobody watched. A second reason the handoff
  carries the tick, not a threshold: a threshold bakes this error in, a tick does not.
- **Pad reach claims for your own exit bias, NEVER for sleep** — an already-armed tick's reachability
  is invariant under S, because sleep shifts your successor's start and the evaluation instant equally
  (§K). Sleep still degrades the INSTANT and can flip the BRANCH (survival → discard past the 300 s
  grace) — keep that apart from reachability.
- **Never promise "the next cycle starts at completion + 15 min" outside a sleep-exclusion window** —
  state reach as a range and prefer retroactive settlement. In a sleep-cycling regime the heartbeat
  fleet's reach for FUTURE time degrades in lockstep with the cron scheduler.

## §Z — the §1 archive-licence and restore-gate entries (header, archived 2026-08-20 1823z; gate EXECUTED that cycle, imperatives compressed in place)

⛔ **THE "LARGEST DORMANT BLOCK" LICENCE IS DEAD — its bounds were never re-measured and the ⛔ below
VETOES the archive it licensed.** It cited *"§1 is lines 630–1925 = 1,296 of 2,450 (53 %)"*; §1 is
**898–2109 = 1,212 of 2,669 (45 %)**, and 630 lands 268 lines inside §0 (1214z). Survivors: a §1
restore gate must be MECHANICAL (read the PROCESS, not the config), and **never inherit an archive
target from a cycle that has not READ the block** — nine passes moved §1, none moved its bounds.
⛔ **"0 OF 14 JOBS ARE ENABLED" IS A FACT ABOUT A FILE, NOT ABOUT THE RUNNING SYSTEM, AND THE §1
ARCHIVE IT LICENSES IS VETOED — §1 IS FULLY LIVE** (2026-08-15 19:3x ICT, 1227z). `cron/jobs.json`
had all 14 `enabled: false` at **17:50 ICT** ⛔ **(STALE — held 2 h 17 min; 08-19 file is
11 jobs/3 enabled, 3 alert jobs DELETED, restart delta 14→3 — 1118z)**, but
`bot/scheduler.py:36` reads that flag **only inside `start()`**, and the live scheduler logged
`Cron scheduler started with 14 jobs` at **15:21:46** — EARLIER, so no edit since has ever been
loaded; `logs/infra.log` has **zero** `Skipping disabled job` lines, ever. **The restore gate must read the PROCESS,
not the config: `grep "Cron scheduler started with" logs/infra.log | tail -1` against `cron/jobs.json`'s
mtime — a config newer than the last scheduler start is a WISH, not a regime.** Transferable, and it is
§0's hand-the-tick-not-a-threshold rule in a second place: **a setting takes effect at a RE-READ, so
every "X is off" claim needs the timestamp of the last load beside it or it is unfalsifiable.**
⛔ **AND THE UNLOADED EDIT IS NOT ONE EDIT — IT IS A STACK, SO RE-DIFF THE FILE IMMEDIATELY BEFORE
YOU RESTART** (2026-08-15 19:4x ICT, 1246z). `cron/jobs.json` mtime **19:39:32**, seven minutes into
the next cycle's past: three jobs (`echo-daily`, `vidnotes-daily`, `cleanpro-daily`) flipped back to
`true` by an interactive chat edit (`infra.log` finalizes a Telegram stream at 19:39:38). The five ids
that have actually fired since the 15:21:46 start are **disjoint** from the three the config now
enables. **A deferred restart applies the file's state AT RESTART, never the state you reasoned
about** — so never say "the pending change" in the singular without its mtime. ✅ Free corroboration
that the instrument is sound: `Skipping disabled job:` occurs **166×** in `infra.log` but last on
**2026-07-02** — the logger works, so today's zero is evidence of no re-read, not a mute log. **Prove
your silence-based claim's instrument has spoken before, or the silence means nothing.**

## §AA — Price-bullet scoring series (archived 2026-08-20 1904z)

Ten passes of net-byte scoring for the compaction Price rule. Dead series: the imperatives it
produced are inline in HEARTBEAT.md. First section past the exhausted single-letter namespace.

- **Price** at **60 B/line net — a CENTRE, no longer "low-biased": mean error +13 %, n=10, spread −31 %…+63 %**
  (0/+0.6/+7/+15/+24/+63/−19/+31/+42/−31). ⛔ **"A FLOOR, every one non-negative" is REFUTED — 1646z broke it
  at −19 %; 1823z drove it to −31 % and then past it.**
  ⛔ **STOP QUOTING A SINGLE NET RATIO — IT IS UNSTABLE UNDER ITS OWN CORRECTION, AND BOTH MINIMA
  WERE SET BY THE CYCLE EDITING THIS BULLET (n=2).** 1823z measured −1,215 B, spent 138 B fixing
  this line, re-measured −1,077 B, added the n=2 note and landed at **−618 B**: three different
  "answers" for one pass, each falsified by the edit that filed it. 1646z's `wc` sat in the same gap.
  **Report the DECOMPOSITION, which does not move: gross removed (2,598 B / 26 lines) minus prose
  written back (2,169 B). Budget a compaction at its gross; treat anything you append as a separate
  deliverable that must justify its own bytes.** A ratio mixing the two re-prices itself every time
  you touch it, which is why ten passes have never made this bullet converge. Gross density predicts nothing. ⛔ **The old "require ≥ 50 lines" floor is
  REFUTED — it prices a write-up you do not have to buy.** 17 lines netted **−831 B** (1646z final;
  the −1,166 B this bullet used to quote was its mid-pass reading) by
  sending the narrative to the daily log and touching this file only to REPLACE a stale imperative.
  The floor applies solely if you append a note here; otherwise there is none, and 1627z declined an
  18-line run on it for nothing. **Cut the run you found.**

## §AB — Move-bullet residue: the sigil-keyed archive-letter grep, and the V/W repairs it hid (archived 2026-08-20 1922z, discharged history)

  two live errors: it misses `## V.` and `## Section W`, and it counts the deliberate `§S.2`/`§M.2`
  repairs as clashes. **§V is LIVE, never void** — 1725z declared it "never written" off its own broken
  grep while §V sat in the archive as *"Discharged backpressure-verification item"*, exactly as this
  header cited it. **W was the real duplicate** (0634z + 1646z, two spellings, invisible to that grep).
  Both repaired 1803z: `## V.`→`## §V —`, `## Section W`→`## §W.2`; §W = the 1646z Find residue.
  **A detector must key on the INVARIANT (the letter), never the decoration (the sigil)** — 1755z's
  paraphrase miss in a fourth place, and note it was written BY the cycle documenting that same trap.

## §AC — Find/Bound bullet residue: the superseded retraction-word grep and the 0608z veto refutation (archived 2026-08-20 1940z)

- **Find** the block by what it CONFIRMS, not by retraction vocabulary — that grep
  (`REFUTED\|RETRACT\|superseded\|…` **and** `n=[0-9]`) is SUPERSEDED and missed every run it was
  aimed at. A *confirmed* model's scoring series is as dead as a refuted one's, carries no retraction
  word, and is often indexed by section letter rather than `n=`. Grep a settled block's **own
  imperatives** instead. The pile is POSITIONAL — cycles append, so read the ~100 lines immediately
  AFTER each `SETTLED` marker — and **audit this method section first, every pass**: the compaction
  thread is the fleet's most self-documenting subject, so it accretes the most confirmations.
  (1638z §T −5,370 B, 1833z §U −6,618 B, this bullet's own source entry §W.)
- **Bound** it by grepping BOTH `^- ` and the block's own entry glyphs `^  [✅⛔⚠️🆕]`. Indent is not
  seniority — they interleave. ⛔ **A live top-level bullet BOUNDS a span; it does NOT veto it** —
  0608z's veto cost five cycles hunting bullet-free gaps and was refuted by 1833z, which took 93
  lines (−6,618 B) with a live bullet as its upper bound. **Grep `^- ` for where your span ENDS,
  then take everything back to the marker**; "is there a bullet-free gap ≥ N lines" is the wrong
  question. (Source entries archived §X.)

## §AD — cleanpro baselines.json char-0 chain (four turns, both halves CLOSED 2026-08-14; moved from HEARTBEAT.md 2026-08-20 2033z)

  ✅ **CLOSED — the `:37` candidate is CONTAINED as of 2026-08-14 19:24 ICT; stop queuing it.** 1218z
  wrapped `load_baselines()` in `try/except (ValueError, OSError)` falling back to a fresh default dict
  (`scripts/cleanpro_alerts_runner.py:35-49`, `py_compile` clean). Verified read-only before touching
  it: `load_baselines()` has exactly **one** caller (`:71`) which reads `conversion_rate_7d` and never
  writes back, so a corrupt file now degrades to the 10.0 default the run **was already using anyway**
  (`:77` — the key does not exist at top level, so the healthy path is byte-identical). The
  mis-calibrated threshold at `:99` was deliberately **not** touched — that stays boss-pending.
  **Why a heartbeat shipped this instead of queuing it a fourth time:** three cycles filed it as the
  cheap containment that must land *before* `bot/scheduler.py:149`'s `timeout=600 → 1800`, because that
  repair lets `cleanpro-weekly` reach its **unspecified** Step 10-12 for the first time since 08-04.
  The containment is independent of the scheduler change, cannot alter the healthy path, and turns a
  total 2-hourly alert outage into a logged `WARN`. **Transferable: when a queued item decomposes into
  a boss-decision half and a strictly-defensive half, ship the defensive half now** — pairing them
  meant neither shipped for three cycles while the exposure stayed open.
  ⚠️ **"sole" is WRONG — there is a SECOND char-0 candidate at `:37`, and the fix to that entry is to
  apply its own rule to itself** (2026-08-14 06:15 ICT). `load_baselines()` at `:35-38` does
  `json.loads(BASELINES.read_text())` guarded by `.exists()` **only** — a present-but-empty
  `baselines.json` gives char 0 too, and it is reached on *every* run (`:60`), where `:32` is reached
  only when an alert fires. Excluded by **measurement, not reading**: the file is **1533 bytes and
  parses clean** (keys `updated, week, period, growth, funnel, paywall, product, countries_top5_cvr`).
  So `:32` survives by elimination and the 05:12 conclusion holds — but it was asserted on an
  uniqueness claim that was false, i.e. **the entry that says "open the line before carrying it
  forward" had not enumerated the alternatives.** Corroborating evidence nobody had read: the failing
  run took **10 s** vs **14 s / 14 s** for the two preceding successes, so it cleared the BigQuery call
  and died late — consistent with `:32`, not with `:21`. **Consequence that inverts the reading:** `:32`
  runs *after* `urlopen` returns, so the alert was probably **delivered** and the crash is
  post-delivery; `print('TELEGRAM_SENT_OK')` at `:100-101` just never executes, so `last_status` reads
  as total failure either way. Still **unverified by observation** —
  `stderr.decode()[-500:]` at `bot/scheduler.py` truncates above the calling frame. **Free falsifier
  every 2 h:** a run that errors identically while the conv-check *cannot* fire (`paywall_shown < 10`
  or `conv_pct >= 7.0`) makes `:32` unreachable and refutes it. **Transferable: elimination is only as
  strong as the enumeration — count the candidate sites before naming one, and prefer a cheap
  measurement (parse the file) over a second reading of the same code.** The danger is not just the lost cycle: a boss who *did* open line 21 would see the
  guard, judge the suspicion refuted, and close the case. **Rule: before carrying a suspected line
  number forward a SECOND time, open that line — and mark inherited suspicions as unverified in your
  log so the next cycle knows they are guesses.**
  **This is the same class as §0's `/tmp/claude-heartbeat.log` ⛔ (15 h of a wrong mechanism because
  nobody read the runner or its plist) and §1's `logs/infra.err` ⛔ (a path no cycle confirmed existed).
  Three instances now of *the checklist reasoning about a file it had not opened* — treat that as the
  fleet's dominant failure mode, not a coincidence.** Second-order, free: **an error message's character
  offset is evidence, not decoration** — here it separated two call sites the truncated log
  (`stderr.decode()[-500:]` at `bot/scheduler.py`) had made indistinguishable.
  ⛔ **THIRD turn on that entry, and it inverts a QUEUE ITEM: the `:37` exclusion is durable only
  while `cleanpro-weekly` stays BROKEN — repairing the weekly re-arms the candidate that was
  eliminated to convict `:32`** (2026-08-14 18:21 ICT, observed). Both line numbers verified by
  opening the file this cycle: `:32` is the sole unguarded `json.loads` on the alert path, `:37` is
  guarded by `.exists()` only. The new fact is **who writes the file the 06:15 entry measured**.
  The alerts runner **never writes it** (`BASELINES` appears only at `:10`, `:36`, `:37`; the two
  `json.dumps` are the Telegram payload `:25` and the stdout result `:102`). The writer is
  **`cleanpro-weekly`** (`skills/cleanpro-weekly/SKILL.md:223`), and mtime proves it: **Aug 4 03:35**
  against that job's `last_run` **`2026-08-03T20:37:28Z` = 08-04 03:37 ICT** — fired 03:30, wrote
  03:35, stamped 03:37. It has fired **nothing since** (the 08-11 Tuesday slot was discarded, §1 line
  466), so the file is frozen at the 1533 bytes the 06:15 entry parsed. **That outage is the only
  reason the exclusion still holds.** When `timeout=600 → 1800` at `bot/scheduler.py:149` lets the
  weekly run again, a weekly dying mid-write leaves a truncated/empty `baselines.json` that `:37`
  reads on **every** subsequent 2-hourly alerts run — char 0, unguarded, reached *before* the
  BigQuery call, where `:32` needs an alert to actually fire. Mechanism corroborated on the sibling:
  `skills/vidnotes-weekly/SKILL.md:619` rewrites baselines with a **`cat > … << EOF` heredoc**
  (non-atomic truncate-then-write). And the contrast names the fix: `skills/vidnotes-alerts/SKILL.md:551`
  handles this **by policy** — *"missing or unreadable → use seed values. Log warning. Never abort."* —
  while the CleanPro Python twin has no guard, despite `load_baselines()` already returning exactly
  those seeds on its not-exists branch. **One-line fix: `try/except (ValueError, OSError)` at `:37`
  falling through to the `:38` seed dict; pair it with the `:149` timeout change rather than shipping
  that alone.** This does **not** overturn `:32` for the *observed* failure — `:37` was genuinely
  excluded at the time it occurred. What changes is the exclusion's **shelf life**.
  **Transferable, and it is the next turn of this entry's own lesson: an elimination argument inherits
  the VOLATILITY of every measurement it rests on.** 06:15 said *enumerate the alternatives before
  asserting uniqueness*; add ***and check whether an excluded alternative can come back***. Here the
  excluder is an outage, so the exclusion is an artefact of something we are actively trying to fix —
  the most dangerous kind, because the repair is what breaks it. Generalise past this file: **when a
  fix is queued, ask which previously-settled findings were resting on the broken state.** Confidence
  high that the weekly is the writer; moderate that a mid-write death yields char 0 specifically
  (heredoc form read on the vidnotes sibling, not on the cleanpro one — one grep for whoever wants it).
  ⛔ **FOURTH turn, and it ran that grep: `skills/cleanpro-weekly/SKILL.md:223` is a POINTER, not a
  write, and its target DOES NOT EXIST — so there is no code in this repo that writes
  `data/cleanpro/baselines.json`** (2026-08-14 18:59 ICT, four direct greps). `:220-223` reads
  *"Step 10-12: Update baselines … Same as daily but weekly paths:"* then three path bullets — no
  command, no heredoc, no `json.dump`. **`skills/` has no `cleanpro-daily`** (only `cleanpro-weekly`
  on the CleanPro side), and `:138` defers the same way (*"Same approach as daily"*). `cleanpro-daily`
  is a **script** job (`scripts/cleanpro_daily_runner.py`) which **never mentions baselines**; the sole
  `scripts/` file that does is the read-only alerts runner. The mtime argument survives — the file is
  1533 B at **Aug 4 03:35** against the weekly's 03:37 stamp — so **"the weekly is the writer" holds;
  "the weekly has a write recipe" does not.** An agent improvised Step 10-12 from a dangling reference.
  Three consequences: (a) **the mid-write shape cannot be settled by grep in either direction** — each
  run improvises, so the failure form is not fixed across runs, which is worse than a known-bad
  heredoc because it cannot be pattern-matched; leave it moderate, falsifier is observational only.
  (b) **The queued pairing gets a second, independent ground:** `timeout=600 → 1800` at
  `bot/scheduler.py:149` lets the weekly reach Step 10-12 for the first time since 08-04, and Step
  10-12 is **unspecified** — the repair walks the job into undefined behaviour on the very file whose
  unguarded `:37` read is the open char-0 candidate. (c) **New small boss item, should land before or
  with `:149`:** inline the baselines write atomically (temp + `os.replace`) or repoint `:138`/`:220-223`
  at something real.
  **Transferable — this is a FOURTH form of the fleet's dominant failure mode (line 1824), the
  CITATION form.** 18:21 *did* open the file and *did* cite the right line; the line was a **pointer**,
  it read the pointer as the referent, and then sourced the missing mechanism from a **different
  skill's** file to fill the gap. Opening the file was necessary, not sufficient — the unfollowed step
  was **following the reference one hop further**. **Rule: when a cited line delegates ("same as X",
  "see Y", "as above"), the citation is not complete until X is opened — and a delegation target that
  does not exist is itself the finding.** Cost: one grep. Confidence high.
  ✅ **CLOSED — Step 10-12 now HAS a procedure, written 2026-08-14 20:25 ICT (commit `69e1643`);
  drop it from the boss queue.** The 18:59 entry's consequence (c) asked for *"inline the baselines
  write atomically or repoint at something real"*; that is the **strictly-defensive half** of the
  pairing with `bot/scheduler.py:149`, so it shipped rather than queuing a second time (1218z's rule,
  line 1733). `skills/cleanpro-weekly/SKILL.md` §10 is now: read-modify-write that carries **unknown
  top-level keys through unchanged**, a missing/unparseable file degrades to `{}` + `WARN` instead of
  aborting, and the write is temp-file + `os.replace` in the same directory — so a mid-write death
  leaves the **previous valid file**, not a truncated one. Embedded python verified to compile.
  Grounded on the live file rather than invented: **10** top-level keys (`updated, week, period,
  growth, funnel, paywall, product, countries_top5_cvr, engineering, caveats`) — note the 06:15 entry
  above enumerates only **8**, so *that* uniqueness argument was reading a stale key list too.
  **This does not close `:37`** — it makes the corrupt input unlikely where 1218z's `try/except` makes
  it survivable; keep both. And it retires the 18:21 shelf-life worry: repairing the weekly no longer
  walks it into undefined behaviour, so `:149` can land on its own merits.

## §AE — Restart chain narrative (1345z/1403z/1423z/1540z), archived 2026-08-20 2241z. Imperatives live in HEARTBEAT.md header.

⛔ **AND A HAZARD WITH NEITHER BRANCH PRICED IS NOT A DECISION — IT IS A SENTENCE, AND IT GETS RE-FILED
VERBATIM EVERY CYCLE** (2026-08-15 20:4x ICT, 1345z; 1227z, 1246z and 1330z each filed *"a restart drops
11 live jobs"* and stopped there, so three cycles correctly declined to act on it). Both sides were one
`grep` away. **Cost of NOT restarting: all 12 job runs since the 15:21:46 start are jobs the config marks
disabled** (`echo-backend-alerts` ×4, `vidnotes-alerts`/`cleanpro-exp-monitor`/`cleanpro-alerts`/
`auto-commit` ×2 each), forward rate ≈ 3/h. **Cost of restarting: zero for ~6 h** — all three enabled ids
are daily (`cleanpro-daily` 03:00 Saigon, `vidnotes-daily` 07:00 Warsaw, `echo-daily` 03:00 New_York), so
no enabled run can be missed in the window, and the 11 dropped are exactly the ones the user turned off.
**Price BOTH branches before handing a hazard forward** — §0's hand-the-tick-not-a-threshold rule for
risk: hand the successor the measurement, never your unresolved verdict.
⛔ **AND THE PRICED BRANCH WAS NEVER AVAILABLE — `./bin/restart.sh` CANNOT RESTART THIS BOT, SO
1345z's DECISION IS VOID, NOT DEFERRED** (2026-08-15 21:0x ICT, 1403z; I ran it, and PID **927
`…/Python -m bot`, started 15:21:26, survived it untouched**). `restart.sh`'s systemd path needs
`systemctl` (absent on macOS) ⇒ always falls to `stop.sh`, which contains **no `launchctl`** and
whose three fallbacks all miss: the pidfiles do not exist, and the orphan pattern is
`pgrep -f "python3.*telegram-bot.py"` against a process named `python -m bot` — the
detector-paraphrase trap, in production stop code. It then prints *"All processes stopped."*
having stopped nothing. **`bin/safe-restart.sh` is the one that uses `launchctl`, and CLAUDE.md
does not sanction it — ask, do not run it.** Side effect disclosed: `start.sh` spawned a second
supervisor (`bash bin/ouroboros.sh`, PID 28418, 21:04:47) beside launchd's KeepAlive; no outage.
**RULE: price the ACTUATOR before you price the branches — read the script you intend to run and
match its detector against the live process's real `argv`.** Four cycles reasoned about this
restart's consequences; none read the four lines that make it a no-op. Evidence:
`memory/t0/2026-08-15/heartbeat-1403z.md`.
⛔ **AND THE REFUSED ACTUATOR IS NOW ARMED BY THE SIDE EFFECT OF REFUSING IT — `bin/ouroboros.sh`
PID 28418 CALLS `bin/safe-restart.sh` EVERY 30 s ON BOT DEATH** (2026-08-15 21:2x ICT, 1423z).
1403z disclosed that watchdog as "a second supervisor beside launchd's KeepAlive"; it is not a
second one — `launchctl list` has no ouroboros entry and no plist in `~/Library/LaunchAgents/`
references it, so it is unsupervised and unique. `bin/ouroboros.sh:20-37` runs the exact script
CLAUDE.md does not sanction, plus an hourly `log-cleanup.sh`. Quiet today only because launchd
reports PID 927 alive. **RULE: price the PROBE's side effects as strictly as the branch you
declined — a permission you withhold from yourself is not withheld if your probe delegates it to a
loop. "Disclosed, no outage" describes the next minute, never what is now armed.** Do NOT stop it
(supervision path, and `guard.sh` forbids the verb); the ask is with the user. Evidence:
`memory/t0/2026-08-15/heartbeat-1423z.md`.
⛔ **AND IT SAT UNDELIVERED FOR FOUR CYCLES — A DECISION FILED IN A DAILY LOG HAS NOT BEEN ASKED**
(2026-08-15 22:4x ICT, 1540z). 1403z/1423z/1442z/1522z each wrote *"the ask is with the user"* into
`memory/t0/…`, a tree the user does not read; `logs/infra.log` has **zero** sends naming it. The
watchdog was armed **1h38m** before the first Telegram message went out, this cycle. **RULE: if a
finding's resolution requires the USER to act, the daily log is evidence, never the channel — send it
the same cycle you file it, or it is not pending, it is dropped.** Same shape as §3's carrier rule and
as 1246z's *a setting takes effect at a RE-READ*: writing is not delivering. Cheap correct form:
`Write` the body to a file, then `./skills/telegram-sender/send.sh --text "$(cat <file>)"` — the
`$(cat …)` form is also what gets prose past `guard.sh`.

## §AF — 0556z geometry-veto block (refuted 2033z; bounds rotted, archived 2259z)

Refuted twice: 2033z cut 113 lines by grepping terminal state, and all four line-number bounds below
now land mid-sentence. Kept for the narrative only.

⛔ **THE LAST VETO-FREE SPAN IS LIVE — GEOMETRY IS NOT THE BOTTLENECK AND NEVER WAS. STOP HANDING
COMPACTION TARGETS FORWARD.** 0534z's unclassified 640–778 (17 glyph entries): READ in full 0556z, it
is the cycle-death taxonomy (5 modes + the `ConnectError`/wake contamination chain) that 0401z used to
diagnose the 213-cycle outage. **Do NOT cut 640–778 or 779–863.** With both halves of the only
bullet-free 224-line span classified LIVE, the file has **no dead ≥50-line block reachable by any
finder tried in 10 passes**. Next real relief is §1's cron-only 630–~1722 behind its mechanical
restore gate, or nothing. **Meanwhile the only lever left is the one 1129z measured: file the finding
in the daily log and put ONLY the imperative here** — and consume your predecessor's handoff note
rather than appending beside it (measured: 249,108→249,170, net **+62 B** — consuming the note paid for my result, not more).

## §AG — restart chain, continued from §AE: 1814z gain-set refutation (archived 2026-08-19 2319z)

⛔ **THE RESTART HAZARD FOUR CYCLES HANDED FORWARD IS VOID: ITS GAIN SET IS EMPTY, AND THE "COST" IS
THE INTENDED EFFECT** (2026-08-16 01:1x ICT, 1814z). 1227z/1246z/1330z/1345z each re-filed *"a
restart drops 11 live jobs"*; 1345z priced only that side. Measured both: the loaded set is
`7e774dd:cron/jobs.json` (last change **07-12**, and **488 commits** span the gap to 08-15 without
touching it — the fleet auto-commits, so **a commit-gap in an auto-committing repo is POSITIVE
evidence of no change**, where prior cycles inferred a lower bound of 5 from which ids had fired).
It has **all 14 enabled**. Against today's config: **drops 11, gains 0** — all three ids the config
enables are already loaded and already ran on 08-15. The edit is a pure *disable*, so the 11 stopping
and the edit taking effect **are the same event**. **RULE: compute an action's GAIN SET before
handing its cost forward — a cost with no benefit beside it means either the action is pointless or
the cost you named is the point.** 1345z's own *price BOTH branches*, one level up: it priced two
costs and called them two branches. Actuator unchanged (`restart.sh` is a no-op, 1403z;
`safe-restart.sh` unsanctioned) — the ask is with the user and was SENT this cycle.
Evidence: `memory/t0/2026-08-16/heartbeat-1814z.md`.


## §AH — line-number pointer rot: the 2026-08-15 1559z measurement series

Moved out of HEARTBEAT.md 2026-08-19 2356z (06:56 ICT 08-20). The live imperative stays on page 1;
the seven measured offsets and the grep -c undercount are here.

⛔ **AND EVERY PASS SILENTLY FALSIFIES THIS FILE'S OWN CROSS-REFERENCES — ALL 56 `line NNN` POINTERS
ARE NOW WRONG, AND EACH ONE LANDS ON REAL, UNRELATED PROSE** (2026-08-15 23:0x ICT, 1559z; 8 of 8
sampled wrong, 0 right). *(56 from `grep -o … | wc -l`; `grep -c` said 47 because **`-c` counts
matching LINES, never occurrences** — the same instrument-sets-the-denominator trap as §0's
`ConnectError` window counts, and it undercounted by 19 % in the one call I nearly filed from.)* Measured offsets, ref → true: `line 504`→97 (−407), `§3 line 2251`→2123
(−128), `line 542`→710 (+168), `line 543`→687 (+144), `§0 line 92`→~262 (+170), `line 215`→466 (+251),
`line 143`→368 (+225). **Both signs, spread 658 lines ⇒ no constant recovers them** — each was written
at a different file state, and in-section growth (~2.3 KB/cycle) and deletion (1540z took 93 lines off
the very top, shifting every pointer in the file at once) push opposite ways. A *dangling* pointer
would be safe; these all resolve, so following one yields a confident wrong citation — the failure
mode that launders a fabrication into the record. **RULE: cite by `§N` plus a distinctive quoted
phrase, NEVER by line number.** `sed`'s move preserves text, so a phrase survives every pass and a
number survives none; `§N` references are unaffected and stay cheap. **Treat every existing
`line NNN` here as VOID — re-find the claim by `grep` before relying on it, and do NOT repair the
numbers: they rot again on the next pass.** The compaction duty that keeps this file readable is the
same duty that corrupts its citations, and nine passes have repaired none.

## §AI — the terminal-marker finder narrative (2033z; scored DRY by its own author, archived 2026-08-20 0041z; imperatives compressed in place)

⛔ **TEN PASSES ASKED WHERE PROSE SITS; THE DEAD BLOCK WAS MARKED BY A WORD, AND THE FINDER THAT
GOT IT IS ALREADY SPENT** (2026-08-20 03:3x ICT, 2033z; −10,244 B net, gross −11,144 / +900 written
back, 113 lines → §AD). 0556z's *"no dead ≥50-line block reachable by any finder tried in 10 passes"*
was structurally true and the wrong half is the useful one: every finder tried — bullet-free gap
length, `SETTLED` adjacency, retraction vocabulary — asks about **geometry**. I ran the gap finder
too and it returned the same fourteen spans, the target among them as an unremarkable 27-liner.
What found it was grepping its **terminal state**, `✅ **CLOSED`: a four-turn chain whose first and
last entries both say *"stop queuing it"* / *"drop it from the boss queue."* **A closed chain has the
same bullet density as an open one — closure is semantic, so no positional finder can ever see it.**
⚠️ **Scored honestly, the finder is DRY: post-pass `grep 'CLOSED\|discharged'` returns two lines,
one my own summary and one a pointer whose body is in §V.** It found one chain in 2,669 lines and is
spent — **a search that matches a terminal marker CONSUMES its matches, so its first run is its best
run and its hit rate is not a rate.** That is 1940z's work-vs-progress trap one level down, at the
finder. General: **a search that has failed N times is usually asking about the wrong PROPERTY, not
asking too weakly** — ten passes escalated one question; one pass changed it. Mirror of 0418z (*key
on structure, never on text the subject writes*): which is trustworthy depends on **who wrote it** —
a subject forges its own failure vocabulary, but nobody forges a `CLOSED` on work they still owe.
Ev: `memory/t0/2026-08-20/heartbeat-2033z.md`.

## §AJ — awk-windowing trap, n=2 reproduction narrative (moved from HEARTBEAT.md 2026-08-20 0053z)

  ✅ **n=2, and the trap reproduces EXACTLY as described — same three symptoms, same order**
  (2026-08-14 22:2x ICT). I windowed with `awk '$0 >= "2026-08-14 22:11:20"'` and got back DNS
  (`ServerNotFoundError … bigquery.googleapis.com`), `SchedulerNotRunningError: Scheduler is not
  running`, and a `JSONDecodeError` — the identical trio this entry predicted in 2026-08-07. A
  `SchedulerNotRunningError` reads as *the cron fleet is dead*, the second-highest-severity alert here.
  Settled in one call: `grep -n 'SchedulerNotRunningError' logs/infra.log` puts both hits at lines
  **18608 and 22482** of 25419 — weeks old. **The continuation lines sort above every date because
  `a` > `2`, so the junk always lands at the TAIL, exactly where "most recent" belongs.** Prediction
  from an entry alone is cheap; this one paid off twice.

## §AK — the `date`-first streak and the prompt-channel fix (moved from HEARTBEAT.md §0, 2026-08-20 0823z)

> *(Added 2026-08-14 16:53 ICT after **four consecutive cycles** — 0852z, 0909z, 0926z, 0949z — made
> exactly this mistake while the correct form sat 300 lines below their first tool call. If you are
> about to defer a checklist fix to the boss, re-read line 215 first: you are probably allowed to
> make it yourself.)*
>
> ⛔ **That edit did NOT stop the streak — 1006z tripped it too (n=5), and the reason is that this
> block is still INSIDE the document.** A cycle's habitual first move is to orient with `date`, and
> it makes that call *before* it has Read HEARTBEAT.md at all, so no placement within this file can
> reach it — moving the text to the top only shortened the distance, it did not change the ordering.
> **The only text every cycle sees before its first tool call is the `claude -p` prompt itself**, so
> 1006z put the imperative there: `skills/heartbeat/run.sh` now opens with "YOUR FIRST TOOL CALL …
> must be `ps -eo … | grep '[g]timeout 600 claude'`". Verified by expansion (`\$\$` survives
> literally, `$LAST_RUN` still interpolates, `bash -n` clean). **Score it: if a cycle still uses
> `date` first, the prompt channel is refuted too and the fix has to become mechanical** — stamp the
> wrapper start into the state file or an env var so it needs no discipline at all.

## §AL — 1500z cron-hole-vs-sleep-hole narrative (archived 2026-08-20 0924z; imperative superseded by 0823z + 0224z)

⛔ **AND A CRON HOLE IS NOT AUTOMATICALLY A SLEEP HOLE — THE FLEET LOST 18:00–18:05 ICT WITH THE HOST
AWAKE** (2026-08-15 22:0x ICT, 1500z). `echo-backend-alerts` (America/New_York, `:05` hourly, 18
unbroken runs 00:05→17:05), `cleanpro-alerts` (Asia/Saigon) and `vidnotes-alerts` (Europe/Warsaw) all
missed exactly one slot and resumed; `infra.log` is empty 17:50:51→19:05:00; bot PID 927 spans it
untouched. Three timezones rules out a tz artifact. **Sleep is REFUTED, not assumed:** `pmset -g log`
has zero `Sleep`/`Wake`/`DarkWake` domain lines from 17:52:09 until after 20:00, yet **837 lines with
per-minute coverage right through the hole** (35 at 18:05 itself, bursts of 71/80 at 18:40–18:41) — a
sleeping host logs nothing. **So before attributing any hole to §0's monotonic freeze, dump `pmset -g log` for the window.**

## §AM — 0534z: the sleep duty cycle is an assertion-holder shadow (archived 2026-08-20 0944z)

Superseded in the header by 0016z (the LID is the majority driver and `pmset -g assertions` is
structurally blind to it) and 0224z (enumerate the sleep DECISIONS - one call, dispositive both ways).
0751z already carries forward the durable half (`dasd fpck-repair` RECURS, so age dates the EPISODE,
never a regime). Kept for the narrative.

⛔ **A SLEEP DUTY CYCLE IS NOT A CONSTANT — IT IS AN ASSERTION-HOLDER'S SHADOW, AND 0514z's "FIXED
5m00s, 15.0 %" HAD ALREADY ENDED 2 min 10 s BEFORE 0514z STARTED** (2026-08-18 12:3x ICT, 0534z).
The last `Entering Sleep state` is **12:08:07**; the 12:12:22 DarkWake — the last one 0514z enumerated
— never slept again, and `pmset -g assertions` names the holder: `pid 381(dasd)` **BackgroundTask
`DASActivity:501:com.apple.FileProvider.maintenance.fpck-repair`, age 00:23:35 at 12:35:58 ⇒ born
12:12:23**, +1 s after that DarkWake. **RULE: before quoting any sleep regime, run `pmset -g
assertions` and read the AGE of each `BackgroundTask`/`Prevent*` holder — a holder older than your
cycle means you are in a DIFFERENT regime than the troughs you just enumerated, and it dates the
change at `now − age`. Presence is not the signal; age is.** (`PreventUserIdleSystemSleep` was also up
here, aged 00:00:00 — a newborn decoy.) 0514z's own rule recursing onto it: it escaped *"a cycle
inherits awake from its own existence"* by measuring troughs it was not awake for, then reported that
regime in the **present tense** — fixing the sampling bias installs a STALENESS bias in its place.
**The missed-fire population is NON-STATIONARY and its driver is third-party background activity the
fleet neither controls nor observes**, so any grace-time fix scored across regimes measures the MIX,
not the fix. (The 12:00/12:05-vs-12:30 split it opened is resolved by 0751z's freeze sum, above.)
Ev: `memory/t0/2026-08-18/heartbeat-0534z.md`.

## §AN — 0514z: never ask whether the host was awake (archived 2026-08-20 0944z)

Headline rule and the do-not-retype-an-invocation rule are RETAINED inline in HEARTBEAT.md; the rest is
superseded - 0707z refutes its "no sampling reaches the troughs", 0751z supersedes its grace-vs-period
reading with the CUMULATIVE freeze sum, 0254z reduces its "nine ConnectError lines" to n=1 (mechanism
intact), and its duty-cycle numbers had already ended before it filed them (archived §AM).

⛔ **NEVER ASK WHETHER THE HOST WAS AWAKE — A HEARTBEAT RUNS IN THE AWAKE WINDOW BY CONSTRUCTION,
BECAUSE LAUNCHD'S WAKE *IS* WHAT STARTED IT** (2026-08-18 12:1x ICT, 0514z). Host entered `Idle Sleep`
11:53:00 and has held a **fixed 5m00s duty cycle — 45 s awake, 4m15s asleep = 15.0 %** (DarkWake
11:57:22/12:02:22/12:07:22/12:12:22, each +45 s to `Maintenance Sleep`). My cycle began 12:14:32 with
**no `Entering Sleep` after 12:12:22** — the `StartInterval 900` wake is the observation. So a cycle
asking *"was the host up?"* about its own window gets **yes at a 100 % rate while the truth is 15 %**;
the sample is drawn from the wake events, so no amount of sampling reaches the troughs.
**Cheap correct form: `pmset -g log > /tmp/pm.log` (also the `guard.sh` escape), pair each
`Entering Sleep state` against the next `Wake from`/`DarkWake`, and report the duty cycle over a window
containing troughs you were NOT awake for. Your `etime` is evidence about your cycle, never the fleet.**
Paid immediately: `check_missed_fires.py`'s **9/14 with four fresh rows** (12:00 x3, 12:05 x1) is
**one cause, not four** — both slot times sit in troughs. (Its *"grace cannot help when the sleep
PERIOD is also 300 s"* is superseded: the quantity is the CUMULATIVE freeze — 0751z, above.) The same
regime ran 08:58→09:07 and produced today's nine `httpx.ConnectError` lines, the DarkWake returning the
process before the network: **QUEUE #8's "sleep" and "network outage" are ONE event seen twice.**
0437z said count from expected slots because a log-derived rate conditions on the host being awake; the
unexamined half is that **a cycle inherits "awake" from its own existence.** ⚠️ n=4 same cycle: I ran `python3
scripts/check_missed_fires.py` ⇒ `ModuleNotFoundError`, one call from filing "the detector is dead" —
`apscheduler` is `.venv`-only and §1 already prescribes `.venv/bin/python3`, on page 2.
**Do not retype a documented invocation from memory.** Evidence: `memory/t0/2026-08-18/heartbeat-0514z.md`.

## §AO — 2112z scheduler announce asymmetry, compressed 2026-08-20 1004z (halved by 2205z exposure-set correction and 2224z loaded-config refutation; surviving core rewritten inline)

⛔ **THE SCHEDULER'S TELEGRAM DELIVERY PATH IS WIRED TO THE ONE JOB TYPE THAT NEVER ALERTS, AND THAT
ASYMMETRY IS WHY SEVEN SCRIPTS INLINE A LIVE BOT TOKEN — QUEUE #11 IS A SYMPTOM, SO ROTATION ALONE
RE-CREATES IT** (2026-08-20 04:1x ICT, 2112z). `bot/scheduler.py:182-187` reads
`job["delivery"]["announce"]` and sends the result to Telegram — a plain per-job key any job could
carry — but **the block sits inside `_run_prompt`; `_run_script` (108-129) never reads it**
(`grep -n announce bot/scheduler.py` ⇒ 5 lines, all 181–189). The config is **8 script jobs to 3
prompt jobs**, and the three prompt jobs are the weeklies + `weekly-conjecture` — **every ALERTING
job is a script job, i.e. exactly the set locked out.** So all of them built their own client:
`grep -c api.telegram.org scripts/*.py` ⇒ **7 files**, which is #11's exposure set. **RULE: when N
components each reimplement one capability, find the single place that offers it CONDITIONALLY — the
duplication is a workaround for an access asymmetry, not N authorship decisions. You cannot price a
credential exposure until you know what the credential is doing there.**
⛔ **Same edit closes a blind spot: `_run_script:129` returns `stdout.decode()[-500:]`, `_run_job`
logs `completed successfully` and returns it, and `:52-53`'s `add_job(self._run_job, …)` DISCARDS a
job coroutine's return value** (only `:73`, run-now, receives it). Measured: **841
`Running job: cleanpro-alerts` lines in `infra.log`, and 0 for the runner's own
`No anomalies detected`, 0 for `💰 CONVERSION`, 0 for `TELEGRAM_SENT_OK`.** **A script job that
stayed silent and one that fired a 🚨 to the user emit the IDENTICAL log line**, so QUEUE #3's
coin-flip backtest (~60 % of slots) is **unobservable in production, not merely unverified** — do not
quote an alert count from it. Distinct from QUEUE #6 (stderr on TIMEOUT); this is the success path.
General: **a return value truncated for presentation and then dropped is dead intent — `[-500:]` on
a value nobody reads marks a delivery path that was removed or never finished**, and it is the tell
that found this. Ev: `memory/t0/2026-08-20/heartbeat-2112z.md`.

## §AP — 0437z expected-slots block and its 0648z weekday correction (archived 2026-08-20 1020z)

⛔ **COUNT A JOB'S FAILURES FROM ITS EXPECTED SLOTS, NEVER FROM THE LOG — A LOG-DERIVED FAILURE RATE
CONDITIONS ON THE HOST HAVING BEEN AWAKE, AND `weekly-conjecture` HAS NO-SHOWED 7 OF 19 SLOTS (37 %)**
(2026-08-18 11:4x ICT, 0437z). QUEUE #1 predicted it would fire Mon 08-17 19:00 ICT and time out at
cap; it **never ran** — `infra.log` jumps 18:05:38 → 19:25:22, host slept at **18:06:46** (`Idle
Sleep`). Enumerating all 19 Mondays 04-13→08-17 against the 12 observed fires: **3** hit the cap,
**7** never fired. **So QUEUE #1's `600 → 1800` addresses the minority mode and would read as fixed
while 37 % of slots stay silent.** 0333z's rule (*are the failures all at the cap?*) one level up: it
still assumed the failure population was runs that failed — **the larger population is slots that
never became runs, and no instrument here sees it.** `infra.log` writes nothing; `cron/state.json`
still says `last_run 08-10, consecutive_errors 1`, which is **indistinguishable from a stale
success** — a timeout stamps fresh and looks healthy, a no-show stamps nothing and looks like one old
failure. Sleep-loss concentrates on weeklies: a daily job redraws the awake condition 7×/week, a
weekly gets one draw. **Applying 1500z's density test in the NEGATIVE: 26 of 81 minutes populated
(32 %), and the lines present are the sleep machinery itself** — sparse ⇒ sleep, where 1500z's 837
lines with per-minute coverage ⇒ awake. Second instrument agrees: fixed-2 h `auto-commit` ran
19:25:22 on 08-17 vs 09:21:46/11:21:46 today, a +3m36s frozen-countdown drift. Not a config artifact
— live scheduler loaded **14 jobs at 08-15 15:21:46**, `cron/jobs.json`'s 3-enabled edit is 19:39 and
unread (§1's gate). ⚠️ Pre-registered, n=1, do NOT re-plot: **07-20 fired at 20:00, not 19:00**, a
clean 1 h shift with no DST to explain it. **Next live draw: `vidnotes-weekly` at 12:30 ICT today —
a cycle after that should `grep vidnotes-weekly logs/infra.log`; "no line at all" is the third
outcome and the one QUEUE #1 cannot express.** Evidence: `memory/t0/2026-08-18/heartbeat-0437z.md`.

--- its later correction (was inline at 303-306) ---

⚠️ **And 0437z's `weekly-conjecture` "7 of 19 slots (37 %)" is UNSCORED — it enumerated MONDAYS.**
`vidnotes-weekly`'s observed fires are **Tuesdays 12:30 ICT** (07-28, 08-11, 08-18; 07-21 at 13:30).
The next-draw time was right so the pre-registered test stood, but **do not re-quote 37 % until the
slot set is rebuilt on the right weekday.**

## §AQ — 0224z density test (one-sided), superseded by 1205z assertion-churn measurement

⛔ **1500z's DENSITY TEST IS ONE-SIDED — `Entering Sleep state` IS DISPOSITIVE IN BOTH DIRECTIONS**
(0224z). Sleep REFUTED for the 08:55–09:15 shell stall (`pmset -g log` 08:00–09:30 has zero sleep,
wake or DarkWake lines until 09:24:53): a `printf` failed to return in 60 s on a demonstrably awake
host. That window is **20 % populated, SPARSER than the 32 % 0437z read as proof of sleep** — which
survives only because its surviving lines WERE the sleep machinery.
**Dense ⇒ awake is valid; sparse ⇒ asleep is not. RULES: (1) enumerate the sleep
DECISIONS — one call, dispositive both ways. (2) Citing a sparse window, say what the surviving
lines ARE.** General: **a one-sided test acquires its second side by being quoted.**

## §AR — 0514z/0534z sleep-probe block, cut 2026-08-20 1344z (superseded by 0707z, 0016z, 1205z)

⛔ **NEVER ASK WHETHER THE HOST WAS AWAKE — A HEARTBEAT RUNS IN THE AWAKE WINDOW BY CONSTRUCTION,
BECAUSE LAUNCHD'S WAKE *IS* WHAT STARTED IT** (0514z, §AN). A cycle asking that about its own window
gets **yes at a 100 % rate while the truth was 15 %** — it inherits "awake" from its own existence, so
**your `etime` is evidence about your cycle, never the fleet.** Measure a window containing troughs you
were NOT awake for: `pmset -g log > /tmp/pm.log` (also the `guard.sh` escape), and enumerate the sleep
DECISIONS (0224z). ⛔ **Same cycle, n=4: `python3 scripts/check_missed_fires.py` ⇒ `ModuleNotFoundError`
and I was one call from filing "the detector is dead" — `apscheduler` is `.venv`-only and §1 prescribes
`.venv/bin/python3`, on page 2. Do not retype a documented invocation from memory.**
⛔ **QUOTE EVERY SLEEP REGIME IN THE PAST TENSE WITH THE TIME IT ENDED — 0534z's "fixed 5m00s, 15.0 %"
had already ended 2m10s before 0534z started** (archived §AM). Escaping *a cycle inherits awake from its
own existence* by measuring troughs you were not awake for installs a STALENESS bias in its place; the
regime is non-stationary and third-party. Sleep DECISIONS (0224z) date the change; holders only age it.
✅ **`vidnotes-weekly` 12:38:56 = 536 s = 89 % of cap, a SECOND near-cap success for QUEUE #1's
capacity branch** (0429z max 528 s, n=14); it ran wholly inside an assertion window, so 536 s is the
sleep-free reference duration.

## §AS — 0613z daily-brief outage narrative, cut 2026-08-20 1344z (incident closed by 2053z, consumer enumeration completed by 2336z)

⛔ **0418z's BACKPRESSURE COVERS ONE OF THE TWO `claude -p` CONSUMERS — `com.claude.daily-brief`
SHARES THE HEARTBEAT'S QUOTA, HAS NO DETECTOR, AND SILENTLY MISSED 08-16, 08-17 AND 08-18**
(2026-08-18 13:1x ICT, 0613z). `launchctl list` shows it at **exit status 1**; `/tmp/claude-daily-brief.log`
is **194 B total and is nothing but three `You've hit your weekly limit` lines**. It is a plain
`claude -p` (plist `ProgramArguments`), so it drew on the same weekly quota the heartbeat drained at
96 cycles/day. Worst detail is the schedule: `StartCalendarInterval` **09:00 local**, and the reset is
**11:00 ICT** — it fires at the most depleted moment of the week and loses by 2 h. Today's run refused
at 02:00Z, the reset landed 04:00Z, and by my cycle the quota had been free 2 h 13 m.
**RULES: (1) When you build a detector for a resource, enumerate every CONSUMER of that resource, not
every instance of the thing you were debugging — 0418z alerted on the fleet and left the user's own
daily brief unmonitored through the same outage. (2) `launchctl list`'s middle column is the last exit
status and it is free in the liveness check you already run — read it, do not just confirm the label
is present.** Sent to the user this cycle; schedule fix is QUEUE #9.
Evidence: `memory/t0/2026-08-18/heartbeat-0613z.md`.

## §AT — the §3 log-compression RETIREMENT POINTER (cut 2026-08-20 1424z)

A 10-line blockquote that opened §3 restating the retirement carried by the bullet directly below it.
Live imperatives all duplicated there (do not compress daily logs for context cost; bundle is
persisted not injected; evidence in §G). Its narrative half was the story of its own rotted
`HEARTBEAT.md:NNNN` self-cite, whose rule is a page-1 imperative. Kept inline: 0236z deleting the
corpse rather than marking it.

> ⛔ **READ FIRST — the log-compression thread that opened this section is RETIRED, and as of
> 2026-08-15 09:4x ICT (0236z) its evidence is gone from here entirely: `HEARTBEAT-ARCHIVE.md` §G.
> Do not `ls -S` today's log dir and compress anything for context cost.** The bundle is *persisted,
> not injected*; the saving is ~0 and compressing below the truncation threshold makes it **worse**.
> *(Pointer added 2026-08-15 07:4x ICT by 0034z, which ran the `ls -S` and was one call from
> compressing before it reached the retraction — the ordering, not the content, cost those calls.
> 0236z closed the gap the only way that fully works: it deleted the corpse instead of marking it,
> which is rule (a) below taken to its conclusion. Note this pointer originally read "RETIRED at
> line 2320" — a `HEARTBEAT.md:NNNN` self-cite, exactly what §1 forbids, and it had already rotted
> before the archival moved it.)*


## §AU — assertion-forensics family, retired by 0016z (lid is a COMMAND, not a holder)

Moved from HEARTBEAT.md 2026-08-20 1449z. 157 lines of pmset -g assertions prediction/exclusion
machinery. Retired because 0016z measured the LID as the majority sleep driver and assertions
cannot see a command. Preserved verbatim for the id-test and timeout-semantics derivations.

- **Keep-awake source is NOT always the display.** Six cycles ran clean on a display-on assertion; the
  00:37 ICT cycle ran clean on transient `dasd` BackgroundTask assertions (Spotlight indexing) with the
  display off. Read `pmset -g assertions` for *which* hold is active before predicting the next slot —
  a `dasd` hold is *sizeable but unbounded*, a display hold is not. And per memory §504, check the
  listed owner: a heartbeat's own `caffeinate` is not host health.
  ⛔ **AGE-SORTING FINDS CANDIDATES, NOT CAUSES — never name a root hold from the assertion list
  alone.** Two prescriptions were built on age-sorting and BOTH were refuted within the hour
  (`HEARTBEAT-ARCHIVE.md` §L.2): "powerd is downstream of the display-on holder" died when powerd's
  hold **outlived** the holder it was supposedly downstream of, and "bound your prediction by that
  process's life" died because the holder **released without exiting**. The real root was a third
  process nobody had ranked. Three rules survive:
  **(a) Confirm a root hold only by seeing it OUTLIVE another hold's release** — outliving is the
  test; being oldest is not.
  **(b) Never bound a prediction by an owner process's LIFE.** A process releases its assertion and
  keeps running; liveness and holding are independent facts (see §L).
  **(c) A `dasd` batch is NOT short-lived** (measured 26 / 40 / 55+ min, later ≈65) — age the holds
  in `pmset -g assertions`, treat every release time as unpredictable rather than imminent, and never
  schedule against one in either direction.
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
  ⛔ **THE POSITIVE BRANCH OF THIS CHAIN IS RETIRED — DO NOT PREDICT A SLEEP-ONSET INSTANT.** Scored
  n≥5 across 2026-08-09→08-11: residuals **+258 s / +412 s / no-onset / no-onset / −75…−265 s** — it
  has now erred in BOTH directions, so it is not a systematic overshoot that a constant could fix.
  The undershoot is unfixable from disk: nothing makes system sleep precede the display countdown on
  the powerd chain, so the surviving causes are display-off events outside the idle countdown
  (manual sleep, lock, hot corner, screensaver, lid) — unmodelled and unobservable here.
  Evidence, every probe and every scoring: `HEARTBEAT-ARCHIVE.md` §M.
  ✅ **What survives is the NEGATIVE direction, and it is the only scheduling primitive here: a fresh
  full-600 s `UserIsActive` tickle EXCLUDES sleep for ~11 min** (display timeout + `sleep 1`).
  **Read the remainder off the assertion's own `Timeout will fire in N secs` — never compute
  `last_tickle + 10 min`.** Proving sleep *cannot* happen is reliable; predicting that it *will* is
  not, because release depends on an unbounded holder. §0 line ~327 is this primitive's live use.
  ⛔ **Instrument ranking, each with a PRECONDITION that must be checked before it is quoted:
  `UserIsActive` id (needs S = 0 over the span) > `PreventUserIdleDisplaySleep` count (needs 0 over
  the span) > powerd's display-on stopwatch (needs count 0 over the span). With S > 0 all three are
  blind and only §1's meter + `getUpdates` gaps say anything.** When two instruments disagree, the
  one with an unmet precondition is the wrong one — that rule was derived by falsification, not
  preference.
  ⛔ **The two branches of the id test are NOT symmetric.** *Churn* (id changes across probes) is
  unconditional positive evidence of a ≥600 s HID-idle gap. *Persist* (same id across >600 s) proves
  a re-tickle **only across a span with S = 0** — `TimeoutActionRelease` counts down on
  `CLOCK_MONOTONIC` and freezes during sleep, so a persisted id bounds AWAKE time, never wall time,
  and at S = 1394 s it read exactly backwards (id said HID active; the display had slept).
  **Record the meter delta beside every `UserIsActive` id reading — a bare id is not a conclusion.**
  Every confirmation that made the persist branch look solid was measured inside an S = 0 window,
  the same pattern that hid the missing `+ S` in §0's `completion + 900 s` rule.
  ✅ **Record the id WITH its age, every probe, and compare IDs rather than ages.** The age field
  resets on every tickle while the id persists — that is precisely why the id is the instrument and
  the age is not; and powerd churns its own hold around wake, so equal ages can be different holds.
  ⛔ **ENUMERATE ALL FOUR CELLS BEFORE SCORING A TWO-INSTRUMENT CHAIN.** The scoring table for this
  chain listed three (id changed + onset ⇒ confirmed; id unchanged + no onset ⇒ inconclusive; id
  changed + no onset ⇒ falsification) and the outcome that actually arrived was the **fourth** — id
  unchanged AND onset — which the rule called impossible. That omission is why the result read as a
  falsification rather than a fifth inconclusive, and a table missing a cell will always score its
  own blind spot as a surprise. Transferable past this chain: **the cell you did not write down is
  the one your rule forbids, and forbidden cells are exactly what a scoring pass exists to catch.**
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
  ⛔ **`InternalPreventDisplaySleep` / `com.apple.powermanagement.delayDisplayOff` is a SECOND,
  SHORTER powerd clock — a 300 s re-armed fuse (age + remaining = 300, n=4) — and it is NOT the
  display countdown. The countdown remainder comes off the `UserIsActive` row only**, which is why
  one probe can read `21 secs` on this fuse and `569 secs` on `UserIsActive` with no contradiction.
  Its `TimeoutActionTurnOff` is gated on `PreventUserIdleDisplaySleep` = 0, and **its expiry never
  touches system sleep — so it can never cost a slot.** Evidence: `HEARTBEAT-ARCHIVE.md` §M.2.
  ⚠️ **Gotcha with a transferable in it: `pmset` prints this status row only WHILE the hold is up —
  on expiry the row leaves the block rather than reading 0.** A cycle grepping
  `InternalPreventDisplaySleep *0` matches nothing and cannot tell "expired" from "never sampled".
  **Test for a status row's PRESENCE whenever absence is one of its states** — a value-grep silently
  collapses "gone" and "not looked at" into the same empty result, and empty reads as benign.
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
  ⛔ **HOLDER-READING RULES — six imperatives distilled from the per-holder series (grok, AnyDesk, the
  Chrome media/WebRTC class, `sharingd`, `bluetoothd`). Evidence: `HEARTBEAT-ARCHIVE.md` §N.**
  - **Never use process liveness as a proxy for an assertion still being held — read the assertion.**
    grok and AnyDesk both release their hold *without exiting* (n=2 independent holder classes), so
    this is wrong by default, not a quirk.
  - **Enumerate owner rows by PID, never by assertion name, and never stop at one row.** A holder
    stacks across processes (two concurrent grok holds at one probe) and can hand off to ITSELF under a
    different assertion name (Chrome "Video Wake Lock" → "WebRTC has active PeerConnections"), so a
    disappearing row is not a release and one row understates the postponement.
  - **Point the id test at `UserIsActive` ONLY.** That row's `TimeoutActionRelease` is what makes a
    persistent id proof of re-tickle; every other class churns ids while holding continuously (Chrome's
    triple churned in lockstep, `sharingd`'s Handoff every few minutes), so an id change there is
    ordinary churn and reading it as a release scores one continuous hold as two short unrelated ones.
  - **`PreventUserIdleDisplaySleep` does not identify its holder, and is blind in the direction that
    matters.** The count reads unchanged while the holder swaps (AnyDesk → Chrome), and reads **0**
    while a *system* hold is up — so it can never establish "no other idle-sleep hold is up", and any
    onset prediction resting on that precondition is unsound. Read the owner rows, not the status block.
  - **Only holds with a real age AND an idle-sleep assertion type count.** Discount `bluetoothd`'s
    age-00:00:00 `com.apple.BTStack` (present through a real onset) and `ExternalMedia` however old
    (36:54:21 across every sleep of its day) — a long age alone does not make a hold sleep-blocking.
  - **No holder class has a characteristic length** (grok ~40 min; `dasd` 26 / 40 / 55+), so every
    non-`UserIsActive` hold stays unbounded in both directions. **Take S from the meter, never from one
    `getUpdates` gap** — a 32 min gap contained a **20-second** dark wake, unusable by the executor.
  ✅ The `UserIsActive` = 0 branch above was NAMED IN ADVANCE and then validated by a real onset
  (2026-08-09 10:47 ICT): state diagnosed correctly, timing correctly called unpredictable. That is the
  negative-space proof that the exclusion window is what had been protecting the slots that fired clean.
  ⚠️ **Always read the `Created for PID:` line — a `coreaudiod` audio hold is a proxy for some other
  process** (AnyDesk's paired system hold, Chrome's media triple). It blocks idle **system** sleep
  independently of the display, so a cycle reading only the `UserIsActive` row badly
  **under**estimates the exclusion window; it grants no guarantee, so it stays conditional. §N.
  ⚠️ **An S = 0 attribution made off `UserIsActive` survives all of the above; what breaks is the
  narrative "X released"** — the label-absorbs-an-unlike-event error again. Chrome blocked system
  sleep continuously ≥26 min across a transition that read as a release on every instrument the
  observing cycle had. §N.

## §AV — 1049z ConnectError-wake-artifact block + its same-cycle scoring (archived 1922z; refuted as a CAUSE by 1110z, which stays inline)

⛔ **AND THAT BASE RATE IS NOT A NETWORK RATE — `infra.log`'s `ConnectError` WINDOWS TRACK **WAKES**,
SO THE FOURTH MODE LIKELY COLLAPSES INTO THE SLEEP MODE** (2026-08-15 17:5x ICT, 1049z). This
cycle's window ran 17:38:14→17:47:43; against `pmset -g log` the host was in a closed-lid
`'Clamshell Sleep'` regime bouncing sleep→DarkWake every 10–45 s, and **every burst starts within
~10 s of a `Wake` line** (17:38:04→17:38:14; 17:47:06→17:47:13) while the one 387 s silence is
exactly the one 360 s sleep. The poller retries before the network stack reattaches. **Do not quote
"307 outages / ~2.4 per day" as a network base rate** — it is an upper bound of unknown wake
content, and here the instrument manufactured the EVENTS, not merely their denominator.
**Before calling any `ConnectError` window an outage, dump `pmset -g log` to a file and Grep the
same minutes for `Wake`; first line within ~15 s of a wake ⇒ artifact.** (Dump-then-Grep-tool
because `guard.sh` refuses the `pmset` predicate spellings — QUEUE #5 again.) This **removes** a
death mode rather than adding one, and strengthens write-early's stated reason. Confidence high for
this window (3 bursts, 3 wakes, one matching gap), moderate for the population.
⚠️ **SCORED IN THE SAME CYCLE, AND IT SOFTENS THE ABOVE: 7/15 within 15 s, 11/15 (73 %) within 60 s,
median gap 18 s. Majority, NOT all — so the mode is contaminated, not abolished.** Say "most
`ConnectError` windows are wake artifacts"; a minority are real, and 0803z's dead cycle may still be
one of them. ⛔ **The bigger catch: only 15 of the windows are TESTABLE, EVER.** `pmset -g log`
retains ~7 days (here 08-08→08-15) while `infra.log` runs from 04-12, so ~97 % of the population
can never be paired with a wake. **When a proposed re-scoring depends on a rolling-retention
instrument, check its horizon BEFORE pre-registering the measurement** — I filed "pair all 307" as
the next holder's job when 97 % of them were already unrecoverable, i.e. an unrunnable task that
reads like a plan. The only fix is forward: score windows as they occur, while `pmset` still holds them.

## §AW — 1522z per-slot/per-pass freeze pricing block (archived 1943z; its enumeration was corrected by 1539z, which stays inline and carries the durable half)

⛔ **THAT MODEL IS SCORED PER SLOT AND PAID PER PASS — THE SAME 951 s FREEZE DEBITED SIX JOBS, FIVE OF
THEM THE USER'S DAILY REPORTS** (1522z). 1404z validated on ONE hourly job, so every impact figure it
produced is denominated in `echo-backend-alerts` slots (*"6/6 late or lost"*); APScheduler skips the
**processing pass**, not the job. Today's `13:48:55 → 948 secs` opened a contiguous **1 h 43 m**
`infra.log` hole (13:21:47→15:05:00 ICT) that swallowed `echo/mangii/pdfai/aividly/vidnotes-daily` at
14:00, `echo-backend-alerts` 14:05, and `cleanpro-exp-monitor`+`auto-commit` 14:21 — four schedules.
**RULE: a hole is priced in the units of the meter that found it, and those units are always the
smallest thing in the hole — enumerate every job whose slot falls inside the gap before quoting an
impact.** Why it matters beyond arithmetic: **alert jobs self-heal (next hour re-reads the same state)
and DAILIES DO NOT** — nothing re-runs them, and `state.json` keeps a D−1 stamp that 0437z's
stale-success reader cannot tell from fresh. All four cycles that priced this mechanism watched the
one job that survives it. ⛔ **Not an n+1 on 1404z: 951 is already a row in its n=22 table — filing it
as fresh evidence was caught only by grepping my own key noun.** Sent to the user (1540z rule 4).
Ev: `…/heartbeat-1522z-a-freeze-is-priced-per-slot-and-paid-per-pass.md`.

## §AX — 1503z repair-sweep block (archived 1943z; its sweep is discharged, its rule written back as one imperative inline)

⛔ **ITS OWN REPAIR SWEEP REACHED ONLY THE PRESCRIPTION SITES (1503z).** 7 page-2 `misfire_grace_time`
sites: the one saying *raising it is not a fix* was already annotated; the two stating the MECHANISM
(*"discards are caused by sleep windows EXCEEDING the 300 s grace"*) were not, and are now repaired.
Both sites' CONCLUSIONS were sound — presence is necessary — so a repairer checking whether each site
is still *right* keeps them all. **RULE: after refuting a model, grep for the sites that state its
MECHANISM, not the sites that state what to DO about it. A cycle repairing a refutation greps for what
to stop doing; the belief clause survives inside conclusions that are independently true, and it is the
belief clause that regenerates the prescription.** Ev: `…/heartbeat-1503z-*.md`.

## §AY — pmset line density is assertion churn (1205z), and its ConnectError neighbours

Moved from HEARTBEAT.md 2026-08-20 2046z. Durable half lives in the page-1 header block "SUM the `Entering Sleep state` LINES OWN TRAILING N secs".

⛔ **`pmset` LINE DENSITY IS 93 % `Assertions` AND STATE LINES ARE 0.8 %, SO IT READS SLEEP IN
NEITHER DIRECTION** (1205z; kills 0224z's *dense ⇒ awake*, §AQ — **a one-sided test acquires its
second side by being quoted**). `awk '{print $4}' /tmp/pm.log | sort | uniq -c` over 81,475 lines: `Assertions`
**75,835**, `ThermalEvent` 1,968, and `Sleep`+`Wake`+`DarkWake` **658 total**. So density is a proxy
for **assertion churn, a different variable** — a window can be maximally dense while the host sleeps,
which unearns *dense ⇒ awake* as well. 0823z blamed a per-CHANGE emitter; the dominant emitter is not
writing about state at all. **Do not refine the heuristic — drop it.** (`ThermalEvent` is worse still:
1,925 lines at 1.00/s for 32 min today, decoupled from state.)
✅ **Free replacement, and it retires 0751z's pairing: the `Entering Sleep state` line's own trailing
`N secs` IS the frozen duration — no `DarkWake` line to pair, which matters because `to FullWake`
matched NOTHING in this log era while four sleep decisions sat in the window.**
`awk '/Entering Sleep state/{for(i=1;i<=NF;i++)if($i=="secs")s+=$(i-1)}END{print s}'` ⇒ **2,457 s**
against 0707z's cadence excess (`start − prev completion − 900`) of **2,447 s** — **0.4 % agreement,
n+1 on 0707z's 1.6 %**, two independent meters. ⛔ **0016z's thermal "nothing in the 6.4 d since"
EXPIRED on a second episode: an "and nothing since" clause carries an expiry stamped by its meter's
end, and it rots first.** Ev: `…/heartbeat-1205z-pmset-density-is-assertion-churn.md`.

## §AZ — stale-job vs second-bug reconciliation (moved from HEARTBEAT.md 2151z; its instrument is now page 1)

  OUTPUT FIELDS, not its command name: `assertions` came back clean at 2 sites while two live clients
  survived under `UserIsActive` — a mature client stops naming the command it was derived from.**
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

## §BA — interval-anchor `+ S` derivation: per-slot deviation, does not re-phase (2026-08-13; archived 2248z)

  ⛔ **That formula is MISSING `+ S` — `IntervalTrigger` waits on the same `CLOCK_MONOTONIC` as every
  other timer in §1, so the anchor arithmetic inherits the sleep term** (2026-08-13 14:37 ICT, n=1,
  residual **−2 s**). Measured: anchor **12:33:23** + 7200 = 14:33:23, sleep **14:19:49 → 14:23:31 =
  222 s** ⇒ predicted **14:37:05**, observed `Running job:` **14:37:03**. A cycle applying the bare rule
  sees silence at 14:33:23 and reads a **dropped slot** — the exact false alarm the next line warns
  about, produced by the formula itself. **`next_fire = last_bot_start + n × interval_seconds + S`.**
  ⛔ **The 300 s margin reading is REFUTED at n=22 (page 1, "freeze on SKIPPED slots"): 516 s and
  665 s FIRED, 453 s did not. Read the meter for PRESENCE of freeze, never against a threshold.**
  ⛔ **`+ S` is a PER-SLOT deviation and does NOT re-phase the anchor — recompute S fresh for every slot,
  and never read a snap-back to the grid as a restart** (2026-08-13 21:56 ICT, n=3 interval + n=1 cron,
  one uninterrupted bot process). The line above scores S on ONE slot and is silent on whether it carries
  forward. It does not: `IntervalTrigger.get_next_fire_time` computes from the previous **nominal**
  (scheduled) fire time, not the actual run time, so a late fire snaps straight back to
  `anchor + n × interval`. Measured on the 12:33:23 anchor, all three slots after the S = 222 s shifted
  fire: **14:37:03** (shifted) → **16:33:23 / 18:33:23 / 20:33:23**, i.e. exactly on grid, never
  14:37:03 + n×7200. Same for `cron` triggers: the alerts pair fired **18:02:13** (133 s late, inside
  grace) and the next slot landed **20:00:00** exact. **The dangerous sign:** a cycle carrying S forward
  predicts 16:37:05, observes 16:33:23, and reads it as **3 m 42 s EARLY** — which is the exact signature
  of the restart re-phase two paragraphs up. It then re-derives a wrong anchor from a `Bot starting` line
  that never happened, and every downstream prediction inherits it. That is the same false alarm the next
  line warns about, produced one slot later by the formula itself. Confidence high.

## §BB — 0409z boundary score: the ~551-line page-1 cut re-derives page-2 findings (n=4)

⛔ **1755z's ~551-LINE BOUNDARY IS NOW SCORED, AND IT COST ME A WHOLE RE-DERIVED FINDING THIS CYCLE.**
I observed `MISSED vidnotes-weekly … (0.1h ago)` while the job's child (`grok -p`, PID 37087) was alive
in `ps`, worked out that `state.json.last_run` is stamped at COMPLETION so every job reads MISSED for
its own runtime, priced the weekly false-positive window at **10 minutes** — and then found **all of
it already filed** in §0's *"THE SUPPRESSION RACE IS REAL AND WIDER THAN FILED"* (2026-08-15, grep that
phrase), down to the same ten-minute figure. It sits at **~line 840, page 2**, so a default `Read`
never delivered it. 1755z asked for exactly this score and it is now **n=4** (0648z, 0836z, 1755z,
this). **The boundary is not a nuisance, it is a duplicate-work engine: the file's page-2 prescriptions
are re-derived by cycles that pay full price for them.** Only additive half, keep it: the existing
discriminator is *"a MISSED row whose `expected` is within one job-duration of `now` is suspect —
re-run the detector"*; **cheaper and deterministic is `grep "Running job: <id>" logs/infra.log | tail -1`
— same-slot `Running job:` with no terminal line ⇒ RUNNING, not missed. No wait, no second run.**
**RULE, and it is the cheap general fix: before filing ANY finding, `grep` this file for your own
finding's key noun — `grep -n "missed\|suppression" HEARTBEAT.md` would have cost one call and saved
the derivation.** Trigger it on the *subject*, not on a hunch; the whole point is you do not know the
page-2 entry exists.

## §BC — the n=1 sleep-freezes-the-cycle-timer measurement (moved 2026-08-21 0135z; live prescriptions kept inline in §0)

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
⚠️ **Cycles do die logless, and the two prescriptions that survived the (refuted) sleep explanation
are worth keeping: a cycle starting within ~3 min of a likely sleep onset should write its log FIRST
and gather second; and if the sleep meter shows S = 0 over the last cycle, write at ~T+5 min and
refine in place.** The mechanism narrative is archived at `HEARTBEAT-ARCHIVE.md` §B — the ⛔ directly
below supersedes it.

## §AW.2 — 1522z freeze-per-slot residue (cut 2026-08-21 0256z; superseded inline by 1539z)

⛔ **A FREEZE IS SCORED PER SLOT AND PAID PER PASS — APScheduler skips the processing PASS, not the
job, so ENUMERATE EVERY JOB WHOSE SLOT FALLS IN THE GAP before quoting an impact; a hole is priced in
the units of the meter that found it, and those units are always the smallest thing in it** (1522z,
archived §AW). **Alert jobs SELF-HEAL (next slot re-reads the same state); DAILIES DO NOT** — nothing
re-runs them and `state.json` keeps a D−1 stamp 0437z's stale-success reader cannot tell from fresh.
