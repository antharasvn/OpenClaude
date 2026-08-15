#!/usr/bin/env python3
"""Did every enabled cron job actually RUN at its last expected fire?

`last_status` answers "did the last run succeed?", never "did it run?" — a fire discarded by
APScheduler's 300 s `misfire_grace_time` (host asleep) leaves `last_status: OK` and
`consecutive_errors: 0` behind it. `cleanpro-weekly` lost its 2026-08-11 fire that way and read
healthy for 84 h. See QUEUE.md #7.

No period, no multiplier, no threshold: ask the trigger for its own fires and compare the last one
before now against `last_run`. This is immune to two traps for free —
  * banded schedules (`0 7-23/2 * * *`) have no scalar period, so any `age > k x period` rule warns
    every night on a healthy job;
  * APScheduler numbers `day_of_week` from 0 = MONDAY, so arithmetic on the string is off by a day.
Both vanish because nothing here interprets the string; the parser does.

Usage:  .venv/bin/python3 scripts/check_missed_fires.py
Exit 0 = all jobs ran at their last expected fire; exit 1 = at least one MISSED.
Read-only.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.triggers.cron import CronTrigger

ROOT = Path(__file__).resolve().parent.parent
INFRA_LOG = ROOT / "logs" / "infra.log"
LOOKBACK = timedelta(days=16)  # > 2 weekly periods, so a weekly job always has a prior fire
SLACK = timedelta(seconds=60)  # last_run is stamped at completion, fire time is the start


def last_expected_fire(cron: str, tz: str, now: datetime):
    """Walk the trigger's own fires forward; return the last one strictly before `now`."""
    trig = CronTrigger.from_crontab(cron, timezone=ZoneInfo(tz))
    t, prev = now - LOOKBACK, None
    while (nxt := trig.get_next_fire_time(t, t + timedelta(seconds=1))) and nxt < now:
        prev, t = nxt, nxt
    return prev


def last_scheduler_start(log: Path = INFRA_LOG):
    """Most recent `Cron scheduler started`, i.e. the epoch the interval grid is anchored on.

    Timestamps in `infra.log` are host-local and naive; the writer is a process on this host.
    """
    if not log.exists():
        return None
    stamp = None
    with log.open(errors="replace") as fh:
        for line in fh:
            if "Cron scheduler started" in line:
                stamp = line[:19]
    if stamp is None:
        return None
    try:
        parsed = datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    return parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)


def interval_expected_fire(interval_seconds: int, scheduler_start, now: datetime):
    """Last interval fire due before `now`, or None if none is due since the last restart.

    A restart re-anchors every interval trigger and the first fire lands at
    `start + interval`, never at `start` (QUEUE.md #8) — so inside that first interval an
    arbitrarily stale `last_run` is correct rather than missed. Without that guard the
    2 h jobs read MISSED for ~1.5 intervals after every reboot.
    """
    if scheduler_start is not None and now < scheduler_start + timedelta(seconds=interval_seconds):
        return None
    # An interval genuinely has no bands, so age vs interval is safe here.
    return now - timedelta(seconds=1.5 * interval_seconds)


def main() -> int:
    now = datetime.now(timezone.utc)
    jobs = json.loads((ROOT / "cron" / "jobs.json").read_text())["jobs"]
    state = json.loads((ROOT / "cron" / "state.json").read_text())

    started = last_scheduler_start()

    missed, checked = [], 0
    for job in jobs:
        if not job.get("enabled", True):
            continue
        jid = job["id"]
        sched = job.get("schedule", {})
        raw = (state.get(jid) or {}).get("last_run")
        last_run = datetime.fromisoformat(raw.replace("Z", "+00:00")) if raw else None

        if "cron" in sched:
            expected = last_expected_fire(sched["cron"], sched["timezone"], now)
            if expected is None:
                continue
        elif "interval_seconds" in sched:
            expected = interval_expected_fire(sched["interval_seconds"], started, now)
            if expected is None:
                checked += 1  # re-anchored by a restart, not yet due — healthy
                continue
        else:
            continue

        checked += 1
        if last_run is None or last_run < expected - SLACK:
            behind = (now - expected).total_seconds() / 3600
            missed.append((jid, expected, behind, raw))

    for jid, expected, behind, raw in missed:
        print(f"MISSED  {jid:24} expected {expected.isoformat()}  ({behind:.1f}h ago)  last_run={raw}")
    print(f"{checked - len(missed)}/{checked} jobs ran at their last expected fire.")
    return 1 if missed else 0


if __name__ == "__main__":
    sys.exit(main())
