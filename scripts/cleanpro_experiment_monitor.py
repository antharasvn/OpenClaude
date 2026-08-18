#!/usr/bin/env python3
"""
CleanPro Experiment Monitor
===========================
Runs every 2 hours to check running experiments.
Reports completion rate, trial start rate, and conversion by variant.
Flags experiments that should be killed (clear loser) or rolled out (clear winner).
"""
import json
import subprocess
import urllib.request
import os
from datetime import datetime

BOT_TOKEN = '8628864855:AAFWSgQCzUIGNtBK1dQk28rCJ7rqBo3v0zU'
CHAT_ID = '-5201056067'  # AAA OS
PROJECT_ID = 'cleaner-app-e98f0'

def bq_query(sql: str):
    cp = subprocess.run(
        ['bq', 'query', '--use_legacy_sql=false', f'--project_id={PROJECT_ID}', '--format=json'],
        input=sql, text=True, capture_output=True, check=False
    )
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

def get_running_experiments():
    """Get list of running experiments from Firebase CLI."""
    result = subprocess.run(
        ['firebase', 'remoteconfig:experiments:list', '--project', PROJECT_ID, '--pageSize', '0'],
        capture_output=True, text=True
    )
    
    experiments = []
    lines = result.stdout.split('\n')
    for line in lines:
        if '│ RUNNING │' in line:
            parts = [p.strip() for p in line.split('│') if p.strip()]
            if len(parts) >= 6:
                experiments.append({
                    'id': parts[0],
                    'name': parts[1],
                    'start_time': parts[4]
                })
    return experiments

def get_experiment_metrics(exp_id: str, hours: int = 24):
    """Get key metrics for an experiment."""
    sql = f'''
WITH all_events AS (
  SELECT * FROM `{PROJECT_ID}.analytics_269202926.events_*` 
  WHERE _TABLE_SUFFIX >= FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 2 DAY))
  UNION ALL
  SELECT * FROM `{PROJECT_ID}.analytics_269202926.events_intraday_*` 
  WHERE _TABLE_SUFFIX >= FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 2 DAY))
),
exp_users AS (
  SELECT 
    user_pseudo_id,
    (SELECT value.string_value FROM UNNEST(user_properties) WHERE key = 'firebase_exp_{exp_id}') as variant
  FROM all_events
  WHERE (SELECT value.string_value FROM UNNEST(user_properties) WHERE key = 'firebase_exp_{exp_id}') IS NOT NULL
  GROUP BY 1, 2
),
user_events AS (
  SELECT 
    ue.variant,
    e.user_pseudo_id,
    MAX(IF(e.event_name = 'onboarding_paywall_shown', 1, 0)) as saw_paywall,
    MAX(IF(e.event_name IN ('onboarding_paywall_dismissed', 'onboarding_paywall_converted'), 1, 0)) as finished_onboarding,
    MAX(IF(e.event_name = 'rc_trial_start', 1, 0)) as trial_started,
    MAX(IF(e.event_name = 'onboarding_paywall_converted', 1, 0)) as converted,
    MAX(IF(e.event_name = 'rc_initial_purchase', 1, 0)) as purchased
  FROM all_events e
  JOIN exp_users ue ON e.user_pseudo_id = ue.user_pseudo_id
  WHERE e.event_timestamp >= UNIX_MICROS(TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR))
  GROUP BY 1, 2
)
SELECT 
  variant,
  COUNT(*) as users,
  SUM(saw_paywall) as saw_paywall,
  SUM(finished_onboarding) as finished_onboarding,
  SUM(trial_started) as trial_started,
  SUM(converted) as converted,
  SUM(purchased) as purchased,
  ROUND(SAFE_DIVIDE(SUM(finished_onboarding), SUM(saw_paywall)) * 100, 1) as completion_rate,
  ROUND(SAFE_DIVIDE(SUM(trial_started), SUM(saw_paywall)) * 100, 1) as trial_rate,
  ROUND(SAFE_DIVIDE(SUM(converted), SUM(saw_paywall)) * 100, 1) as conversion_rate
FROM user_events
WHERE saw_paywall = 1
GROUP BY variant
ORDER BY variant
'''
    return bq_query(sql)

def get_conversion_emoji(rate):
    if rate > 50: return '🟣'
    elif rate > 30: return '🔵'
    elif rate > 20: return '🟢'
    elif rate > 10: return '✅'
    elif rate > 5: return '⚠️'
    elif rate > 2: return '🟠'
    else: return '🔴'

def format_experiment_report(exp_id, exp_name, metrics):
    """Format a single experiment report."""
    if not metrics:
        return f"Exp {exp_id} ({exp_name}): No data yet\n"
    
    lines = [f"📊 Exp {exp_id}: {exp_name[:30]}"]
    
    for m in metrics:
        variant = m.get('variant', '?')
        users = int(m.get('saw_paywall', 0))
        completion = float(m.get('completion_rate', 0) or 0)
        trial = float(m.get('trial_rate', 0) or 0)
        conv = float(m.get('conversion_rate', 0) or 0)
        
        variant_name = 'Baseline' if variant == '0' else f'Var {variant}'
        emoji = get_conversion_emoji(conv)
        
        lines.append(f"  {variant_name}: {users}u | {completion}% done | {trial}% trial | {conv}% conv {emoji}")
    
    # Check for clear winner/loser
    if len(metrics) >= 2:
        rates = [(m.get('variant'), float(m.get('conversion_rate', 0) or 0), int(m.get('saw_paywall', 0))) for m in metrics]
        rates.sort(key=lambda x: x[1], reverse=True)
        
        # Need at least 50 users per variant for signal
        if all(r[2] >= 50 for r in rates):
            best = rates[0]
            worst = rates[-1]
            diff = best[1] - worst[1]
            
            if diff > 5 and worst[1] < 2:
                lines.append(f"  ⚠️ KILL? Var {worst[0]} underperforming ({worst[1]}% vs {best[1]}%)")
            elif diff > 10:
                lines.append(f"  🚀 WINNER? Var {best[0]} leading ({best[1]}% vs {worst[1]}%)")
    
    return '\n'.join(lines)

def main():
    # Job removed from cron/jobs.json; exit so leftover in-memory scheduler ticks do nothing.
    print("cleanpro_experiment_monitor is no longer scheduled; exiting")
    return

    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    print(f"=== CleanPro Experiment Monitor — {now} ===\n")
    
    experiments = get_running_experiments()
    
    if not experiments:
        print("No running experiments found")
        return
    
    print(f"Found {len(experiments)} running experiments\n")
    
    reports = []
    for exp in experiments:
        exp_id = exp['id']
        exp_name = exp['name']
        
        try:
            metrics = get_experiment_metrics(exp_id)
            report = format_experiment_report(exp_id, exp_name, metrics)
            reports.append(report)
            print(report)
            print()
        except Exception as e:
            print(f"Exp {exp_id}: Error - {e}")
    
    # Send via direct Telegram either way so cron announce delivery is not required.
    alerts = [r for r in reports if 'KILL?' in r or 'WINNER?' in r]
    if alerts:
        msg = f"🧪 CleanPro Experiment Alert — {now}\n\n" + '\n\n'.join(alerts)
        send_telegram(msg)
        print("\n📤 Alert sent to Telegram")
    else:
        print("No actionable alerts; staying silent")

if __name__ == '__main__':
    main()
