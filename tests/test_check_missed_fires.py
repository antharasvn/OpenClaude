"""A restart re-anchors every interval job, so a stale `last_run` is not yet a miss.

APScheduler's `IntervalTrigger` first fires at `start + interval`, never at `start`
(QUEUE.md #8). The detector's `now - 1.5 x interval` staleness rule knows nothing about
process starts, so for the 1.5 intervals after every reboot it reports each 2 h job as
MISSED while nothing is wrong — three cycles on 2026-08-15 each re-derived that by hand.
"""

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "check_missed_fires", ROOT / "scripts" / "check_missed_fires.py"
)
cmf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cmf)

IV = 7200
NOW = datetime(2026, 8, 15, 9, 55, tzinfo=timezone.utc)


def test_no_fire_is_due_before_start_plus_one_interval():
    started = NOW - timedelta(seconds=IV - 1)
    assert cmf.interval_expected_fire(IV, started, NOW) is None


def test_fire_is_due_once_a_full_interval_has_passed():
    started = NOW - timedelta(seconds=IV + 1)
    assert cmf.interval_expected_fire(IV, started, NOW) == NOW - timedelta(seconds=1.5 * IV)


def test_unknown_start_falls_back_to_the_staleness_rule():
    assert cmf.interval_expected_fire(IV, None, NOW) == NOW - timedelta(seconds=1.5 * IV)


def test_last_scheduler_start_takes_the_final_match(tmp_path):
    log = tmp_path / "infra.log"
    log.write_text(
        "2026-08-13 12:33:23 [INFO] Cron scheduler started with 14 jobs\n"
        "2026-08-13 12:33:23 [INFO] Cron scheduler started\n"
        "2026-08-15 15:21:46 [INFO] Cron scheduler started with 14 jobs\n"
        "2026-08-15 15:21:46 [INFO] Cron scheduler started\n"
        "2026-08-15 16:00:00 [INFO] Running job: cleanpro-alerts\n"
    )
    got = cmf.last_scheduler_start(log)
    assert got is not None
    local = datetime.now().astimezone().tzinfo
    assert got == datetime(2026, 8, 15, 15, 21, 46, tzinfo=local)


def test_last_scheduler_start_tolerates_a_missing_log(tmp_path):
    assert cmf.last_scheduler_start(tmp_path / "nope.log") is None
