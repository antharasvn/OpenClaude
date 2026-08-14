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

## 2. `script`-job cap: `timeout=300` — 9 % margin, currently passing

**Where:** `bot/scheduler.py:120`.
**Why now:** `cleanpro-daily` on 2026-08-14 ran **273 s of awake time against the 300 s cap**. It
showed 1007 s of *wall* time and did not raise only because the host slept 734 s inside the window —
`asyncio.wait_for` waits on `time.monotonic()`, which freezes on Darwin sleep.
**A clean run is not a clearance.** Next observation point: `cleanpro-daily` fires **03:00 ICT daily**.

## 3. Mis-calibrated threshold at `bot/scheduler.py:99`

Deliberately left untouched by the cycle that found it; needs a judgement call, not an edit.
Context: `HEARTBEAT.md:2138`.

## 4. SessionStart hook: uncapped daily-log injection

The hook `cat`s **every** log in `memory/t0/{today}/` into **every** later cycle that day, uncapped.
A log's real cost is its size × the number of remaining cycles (~85 at 02:00 ICT, ~4/hour).
The fleet has taken the part it can reach — compressing superseded files in place, which recovered
≈740 KB of injected context on 08-15 — but **a cap belongs in the hook**, and cycles are barred from
editing `.claude/settings.json`. Boss's call.

---

*Anything resolved: delete the row, don't annotate it. This file earns its place by staying short.*
