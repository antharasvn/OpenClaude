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
