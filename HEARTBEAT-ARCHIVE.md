# HEARTBEAT archive — evidence moved out of the checklist to keep it READABLE

Nothing here is retracted unless it says so. These are the *narratives* behind rules that still
live in `HEARTBEAT.md`; the imperative stayed inline, the measurement moved here. Read this file
only when you need to know **why** a rule exists, never to find out **what** to do.

## A. §0 clock-bias — full n=1/2/3 measurements (archived 2026-08-15 08:5x ICT by 0152z)

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

## B. §0 logless-death — the sleep mechanism that §0 line ~92 then REFUTED (archived same cycle)

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
