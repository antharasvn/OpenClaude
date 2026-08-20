#!/usr/bin/env python3
import json, subprocess, tempfile, os, urllib.request, pathlib
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent

BOT_TOKEN = '8628864855:AAFWSgQCzUIGNtBK1dQk28rCJ7rqBo3v0zU'
CHAT_ID = '-5201056067'
BASELINES = PROJECT_ROOT / 'data' / 'cleanpro' / 'baselines.json'


def run(cmd, input_text=None, timeout=300):
    # timeout is load-bearing and matches daily_report_common.run: an unbounded
    # bq/gcloud call here hangs until the scheduler's 600 s cap, and _run_script
    # discards stderr on timeout (QUEUE #6), so the failure is invisible.
    return subprocess.run(
        cmd, input=input_text, text=True, capture_output=True, check=False, timeout=timeout
    )


def bq_query(sql: str):
    # timeout=600 mirrors daily_report_common.bq_query — bq is the one call here
    # that legitimately runs past the 300 s shim default.
    cp = run(['bq','query','--use_legacy_sql=false','--project_id=cleaner-app-e98f0','--format=json'], input_text=sql, timeout=600)
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr or cp.stdout)
    return json.loads(cp.stdout or '[]')


def send_telegram(text: str):
    payload = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": ""}).encode('utf-8')
    req = urllib.request.Request(
        f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
        data=payload,
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _default_baselines():
    # Fresh dict per call so no caller can mutate a shared default.
    return {"conversion_rate_7d": 10.0, "new_users_7d_avg": 60, "seen_crash_issue_ids": []}


def load_baselines():
    # A truncated/empty baselines.json used to raise JSONDecodeError here and kill the whole
    # 2-hourly alert run. The weekly writer has no fixed recipe (it improvises Step 10-12 from a
    # dangling reference), so a partial write is possible on any run — fall back, don't crash.
    if BASELINES.exists():
        try:
            return json.loads(BASELINES.read_text())
        except (ValueError, OSError) as e:
            print(f"WARN: unreadable {BASELINES} ({e}); using defaults")
    return _default_baselines()


def main():
    print("cleanpro_alerts_runner is no longer scheduled; exiting")
    return
    sql = r'''
SELECT
  COUNT(DISTINCT IF(event_name IN ("onboarding_paywall_shown","cleanpro_paywall_shown"), user_pseudo_id, NULL)) AS paywall_shown,
  COUNT(DISTINCT IF(event_name IN ("onboarding_paywall_converted","rc_initial_purchase"), user_pseudo_id, NULL)) AS converted,
  ROUND(SAFE_DIVIDE(
    COUNT(DISTINCT IF(event_name IN ("onboarding_paywall_converted","rc_initial_purchase"), user_pseudo_id, NULL)),
    COUNT(DISTINCT IF(event_name IN ("onboarding_paywall_shown","cleanpro_paywall_shown"), user_pseudo_id, NULL))
  ) * 100, 1) AS conv_pct
FROM `cleaner-app-e98f0.analytics_269202926.events_intraday_*`
WHERE _TABLE_SUFFIX >= FORMAT_DATE('%Y%m%d', CURRENT_DATE('Asia/Saigon'))
  AND event_timestamp >= UNIX_MICROS(TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 4 HOUR))
  AND event_name IN ("onboarding_paywall_shown","cleanpro_paywall_shown","onboarding_paywall_converted","rc_initial_purchase")
'''
    rows = bq_query(sql)
    row = rows[0] if rows else {}
    paywall_shown = int(float(row.get('paywall_shown', 0) or 0))
    converted = int(float(row.get('converted', 0) or 0))
    conv_pct = float(row.get('conv_pct', 0) or 0)
    baselines = load_baselines()
    # ⛔ THIS CHECK IS MIS-CALIBRATED AND FIRES ~60% OF RUNS — boss decision pending, do not "repair" piecemeal.
    # Broken since its first commit (8347d75, 2026-04-12); this file has never been modified since.
    # Independently re-measured 2026-08-07 02:1xZ over the 57 real cron slots in 07-31→08-06
    # (48 evaluable): **29 / 48 = 60.4% would alert**, mean windowed rate 5.16% vs a 7.0% threshold.
    # Confirms the earlier 59.8% estimate. Defects, all verified against BigQuery:
    #  1. BASELINE NEVER LOADS. data/cleanpro/baselines.json has no top-level `conversion_rate_7d`
    #     (the real value lives at funnel.pw_cvr_pct = 10.4). So .get(...) silently returns the 10.0
    #     default on every run — the threshold is hardcoded 7.0%, and weekly baseline refreshes are inert.
    #  2. `rc_initial_purchase` DOES NOT EXIST in analytics_269202926 (0 rows, 7d). The event that
    #     actually pairs with cleanpro_paywall_shown is **`cleanpro_paywall_converted`** (9 users/7d).
    #     So the numerator is onboarding_paywall_converted only (49 users/7d) while the denominator
    #     unions BOTH shown events (549 + 501) — in-app views can never contribute a conversion.
    #  3. Floor of 10 is the exact value vidnotes-alerts was hardened away from on 2026-06-03 for
    #     producing bogus "100% drop" breaches. Same failure mode, never backported here.
    # THE TWO OBVIOUS REPAIRS DO NOT WORK — measured, not assumed:
    #  - Adding cleanpro_paywall_converted to the numerator: 60.4% → 56.3%. Correct, but ~useless alone.
    #  - Reading funnel.pw_cvr_pct: raises the threshold 7.0 → 7.28, so it fires MORE, not less.
    #  - Even the clean apples-to-apples version (onboarding-only rate vs the onboarding-only 10.4
    #    baseline) still alerts on 21/40 = 52.5% of slots.
    # ROOT CAUSE is the statistic, not the wiring: a 4h WINDOWED rate (mean 8.63% onboarding-only) is
    # structurally below a weekly COHORT rate (10.4%) because conversions lag their paywall view across
    # the window edge. Calibrating a windowed alert against a cohort baseline is wrong by construction —
    # the 0.70 threshold then lands mid-distribution and the check behaves like a coin flip, which is the
    # same defect found in the vidnotes conversion check on 2026-08-07.
    # Real repair = compare the window against the WINDOWED historical distribution (e.g. same-hour
    # percentile or CUSUM on the daily series), or move conversion monitoring to the daily report.
    baseline = float(baselines.get('conversion_rate_7d', 10.0) or 10.0)
    if paywall_shown < 10 or conv_pct >= baseline * 0.70:
        print(f'No anomalies detected. paywall_shown={paywall_shown} conv_pct={conv_pct} baseline={baseline}')
        return
    drop_pct = round((1 - (conv_pct / baseline)) * 100, 1) if baseline else 0
    now_et = subprocess.run(['bash','-lc','TZ="Asia/Saigon" date +"%H:%M ET"'], capture_output=True, text=True).stdout.strip()
    alert = (
        f'🚨 CleanPro Alert — {now_et}\n\n'
        f'💰 CONVERSION: {conv_pct}% in last 4h ({drop_pct}% drop vs {baseline}% baseline)\n'
        f'Details: {paywall_shown} paywall views, {converted} conversions\n'
        f'Action: Check paywall config and RevenueCat dashboard'
    )
    res = send_telegram(alert)
    print(alert)
    print('TELEGRAM_SENT_OK')
    print(json.dumps(res))


if __name__ == '__main__':
    main()
