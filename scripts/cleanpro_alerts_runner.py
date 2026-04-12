#!/usr/bin/env python3
import json, subprocess, tempfile, os, urllib.request, pathlib
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent

BOT_TOKEN = '8628864855:AAFWSgQCzUIGNtBK1dQk28rCJ7rqBo3v0zU'
CHAT_ID = '-5201056067'
BASELINES = PROJECT_ROOT / 'data' / 'cleanpro' / 'baselines.json'


def run(cmd, input_text=None):
    return subprocess.run(cmd, input=input_text, text=True, capture_output=True, check=False)


def bq_query(sql: str):
    cp = run(['bq','query','--use_legacy_sql=false','--project_id=cleaner-app-e98f0','--format=json'], input_text=sql)
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


def load_baselines():
    if BASELINES.exists():
        return json.loads(BASELINES.read_text())
    return {"conversion_rate_7d": 10.0, "new_users_7d_avg": 60, "seen_crash_issue_ids": []}


def main():
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
