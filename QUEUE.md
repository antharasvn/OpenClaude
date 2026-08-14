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

**The actual ask:** the script wedges outright roughly twice a month. Needs a look at what it blocks
on (network I/O with no per-request timeout is the obvious candidate), not a bigger budget.

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
