#!/usr/bin/env python3
"""
Mangii Daily Report Runner
==========================
Enhanced format matching CleanPro: country breakdowns, onboarding funnel, experiments, pro heatmap.
"""
import json, subprocess, pathlib, urllib.request
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent

BOT_TOKEN = '8628864855:AAFWSgQCzUIGNtBK1dQk28rCJ7rqBo3v0zU'
CHAT_ID = '-5201056067'  # AAA OS
PROJECT_ID = 'mangii-app'
DATASET_ID = 'analytics_488420427'
APP_NAME = 'Mangii'
LOGO_PATH = pathlib.Path.home() / 'Projects/Mangii/ios/Mangii/Assets.xcassets/AppIcon.appiconset/app-icon-1024.png'
BASE = PROJECT_ROOT / 'data' / 'mangii'


def run(cmd, input_text=None):
    return subprocess.run(cmd, input=input_text, text=True, capture_output=True, check=False)


def bq_query(sql: str):
    cp = run(['bq','query','--use_legacy_sql=false',f'--project_id={PROJECT_ID}','--format=json'], input_text=sql)
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


def pct(cur, base):
    if not base:
        return 'N/A'
    return f'{((cur-base)/base)*100:+.0f}%'


def get_conversion_emoji(rate):
    if rate > 50: return '🟣'
    elif rate > 30: return '🔵'
    elif rate > 20: return '🟢'
    elif rate > 10: return '✅'
    elif rate > 5: return '⚠️'
    elif rate > 2: return '🟠'
    else: return '🔴'


def q_growth(start_us, end_us, suffix_start, suffix_end):
    sql = f'''
WITH all_events AS (
  SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
), user_seg AS (
  SELECT user_pseudo_id, MAX(IF(event_name="first_open",1,0)) AS is_new
  FROM all_events WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1
)
SELECT IF(is_new=1,"new","returning") AS segment, COUNT(*) AS users
FROM user_seg GROUP BY 1
'''
    return bq_query(sql)


def q_countries_new_users(start_us, end_us, suffix_start, suffix_end):
    sql = f'''
WITH all_events AS (
  SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
)
SELECT geo.country, COUNT(DISTINCT user_pseudo_id) AS new_users
FROM all_events 
WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  AND event_name = 'first_open'
GROUP BY 1 ORDER BY new_users DESC LIMIT 10
'''
    return bq_query(sql)


def q_monetization_funnel(start_us, end_us, suffix_start, suffix_end):
    """Monetization funnel: new vs returning users through paywall to purchase."""
    sql = f'''
WITH all_events AS (
  SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
), user_seg AS (
  SELECT user_pseudo_id, MAX(IF(event_name="first_open",1,0)) AS is_new
  FROM all_events WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1
), funnel AS (
  SELECT
    us.is_new,
    e.user_pseudo_id,
    MAX(IF(e.event_name = 'paywall_shown', 1, 0)) AS saw_paywall,
    MAX(IF(e.event_name = 'paywall_purchase_success', 1, 0)) AS purchased,
    MAX(IF(e.event_name = 'paywall_cta_tapped', 1, 0)) AS cta_tapped,
    MAX(IF(e.event_name = 'paywall_plan_selected', 1, 0)) AS plan_selected,
    MAX(IF(e.event_name = 'paywall_purchase_cancelled', 1, 0)) AS purchase_cancelled,
    MAX(IF(e.event_name = 'paywall_purchase_failed', 1, 0)) AS purchase_failed
  FROM all_events e
  JOIN user_seg us ON e.user_pseudo_id = us.user_pseudo_id
  WHERE e.event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1, 2
)
SELECT
  IF(is_new=1,"new","returning") AS segment,
  COUNT(*) AS total_users,
  SUM(saw_paywall) AS paywall_users,
  SUM(purchased) AS paid_users,
  SUM(cta_tapped) AS cta_tapped_users,
  SUM(plan_selected) AS plan_selected_users,
  SUM(purchase_cancelled) AS purchase_cancelled_users,
  SUM(purchase_failed) AS purchase_failed_users
FROM funnel
GROUP BY 1
'''
    return bq_query(sql)


def q_conversion_by_country(start_us, end_us, suffix_start, suffix_end):
    sql = f'''
WITH all_events AS (
  SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
), country_events AS (
  SELECT geo.country, user_pseudo_id, event_name
  FROM all_events WHERE event_timestamp BETWEEN {start_us} AND {end_us}
), country_metrics AS (
  SELECT 
    country,
    COUNT(DISTINCT IF(event_name = 'paywall_shown', user_pseudo_id, NULL)) AS paywall_shown,
    COUNT(DISTINCT IF(event_name = 'paywall_purchase_success', user_pseudo_id, NULL)) AS converted
  FROM country_events GROUP BY 1
)
SELECT country, paywall_shown, converted,
  ROUND(SAFE_DIVIDE(converted, paywall_shown) * 100, 1) AS conversion_rate
FROM country_metrics
WHERE paywall_shown > 0
ORDER BY paywall_shown DESC LIMIT 10
'''
    return bq_query(sql)


def q_product(start_us, end_us, suffix_start, suffix_end):
    sql = f'''
WITH all_events AS (
  SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
)
SELECT event_name, COUNT(DISTINCT user_pseudo_id) AS users, COUNT(*) AS events
FROM all_events
WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  AND event_name IN (
    "panel_generate_tapped","panel_generated","panel_generate_blocked",
    "panel_regenerated","credit_depleted","first_gen_preview_shown"
  )
GROUP BY 1 ORDER BY users DESC
'''
    return bq_query(sql)


def get_running_experiments():
    result = subprocess.run(
        ['firebase', 'remoteconfig:experiments:list', '--project', PROJECT_ID, '--pageSize', '0'],
        capture_output=True, text=True
    )
    experiments = []
    for line in result.stdout.split('\n'):
        if '│ RUNNING │' in line:
            parts = [p.strip() for p in line.split('│') if p.strip()]
            if len(parts) >= 6:
                experiments.append({'id': parts[0], 'name': parts[1][:35]})
    return experiments


def q_experiment_metrics(start_us, end_us, suffix_start, suffix_end):
    experiments = get_running_experiments()
    if not experiments:
        return []
    
    results = []
    for exp in experiments[:8]:
        exp_id = exp['id']
        sql = f'''
WITH all_events AS (
  SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
),
exp_users AS (
  SELECT user_pseudo_id,
    (SELECT value.string_value FROM UNNEST(user_properties) WHERE key = 'firebase_exp_{exp_id}') as variant
  FROM all_events
  WHERE event_timestamp BETWEEN {start_us} AND {end_us}
    AND (SELECT value.string_value FROM UNNEST(user_properties) WHERE key = 'firebase_exp_{exp_id}') IS NOT NULL
  GROUP BY 1, 2
),
user_events AS (
  SELECT ue.variant, e.user_pseudo_id,
    MAX(IF(e.event_name = 'paywall_shown', 1, 0)) as saw_paywall,
    MAX(IF(e.event_name = 'paywall_dismissed', 1, 0)) as finished,
    MAX(IF(e.event_name = 'rc_trial_start', 1, 0)) as trial,
    MAX(IF(e.event_name IN ('rc_initial_purchase', 'paywall_purchase_success'), 1, 0)) as converted
  FROM all_events e JOIN exp_users ue ON e.user_pseudo_id = ue.user_pseudo_id
  WHERE e.event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1, 2
)
SELECT variant, SUM(saw_paywall) as paywall,
  ROUND(SAFE_DIVIDE(SUM(finished), SUM(saw_paywall)) * 100, 1) as completion,
  ROUND(SAFE_DIVIDE(SUM(trial), SUM(saw_paywall)) * 100, 1) as trial_rate,
  ROUND(SAFE_DIVIDE(SUM(converted), SUM(saw_paywall)) * 100, 1) as conv_rate
FROM user_events WHERE saw_paywall = 1 GROUP BY variant ORDER BY variant
'''
        try:
            rows = bq_query(sql)
            for row in rows:
                row['exp_id'] = exp_id
                row['exp_name'] = exp['name']
            results.extend(rows)
        except:
            pass
    return results


def format_country_growth(data):
    lines = []
    for r in data[:10]:
        lines.append(f"    {r.get('country', '?')}: {r.get('new_users', 0)}")
    return '\n'.join(lines)


def format_country_conversion(data):
    total_shown = sum(int(r.get('paywall_shown', 0) or 0) for r in data)
    total_conv = sum(int(r.get('converted', 0) or 0) for r in data)
    total_rate = round(total_conv / max(1, total_shown) * 100, 1)
    
    lines = [f"    TOTAL: {total_shown}→{total_conv} ({total_rate}%) {get_conversion_emoji(total_rate)}",
             "    ─────────────────────"]
    for r in data[:10]:
        country = r.get('country', '?')
        shown = int(r.get('paywall_shown', 0) or 0)
        conv = int(r.get('converted', 0) or 0)
        rate = float(r.get('conversion_rate', 0) or 0)
        emoji = get_conversion_emoji(rate)
        lines.append(f"    {country}: {shown}→{conv} ({rate}%) {emoji}")
    return '\n'.join(lines)


def format_experiments(exp_metrics):
    if not exp_metrics:
        return "    No running experiments"
    
    exp_data = {}
    for row in exp_metrics:
        exp_id = row.get('exp_id', '?')
        if exp_id not in exp_data:
            exp_data[exp_id] = {'name': row.get('exp_name', exp_id), 'variants': []}
        exp_data[exp_id]['variants'].append(row)
    
    lines = []
    for exp_id, data in exp_data.items():
        var_strs = []
        for v in sorted(data['variants'], key=lambda x: x.get('variant', '0')):
            variant = v.get('variant', '?')
            paywall = int(v.get('paywall', 0) or 0)
            conv = float(v.get('conv_rate', 0) or 0)
            vname = 'B' if variant == '0' else f'V{variant}'
            emoji = get_conversion_emoji(conv)
            var_strs.append(f"{vname}:{paywall}u/{conv:.0f}%{emoji}")
        lines.append(f"    {exp_id}: {' | '.join(var_strs)}")
    return '\n'.join(lines)


def main():
    now = datetime.now()
    now_epoch = int(now.timestamp())
    now_us = now_epoch * 1_000_000
    h24 = (now_epoch - 86400) * 1_000_000
    h48 = (now_epoch - 172800) * 1_000_000
    h168 = (now_epoch - 604800) * 1_000_000
    h192 = (now_epoch - 691200) * 1_000_000
    
    display_date = now.strftime('%Y-%m-%d')
    display_time = now.strftime('%H:%M')
    suffix_end = now.strftime('%Y%m%d')
    suffix_start = (now.replace(hour=0, minute=0, second=0) - __import__('datetime').timedelta(days=2)).strftime('%Y%m%d')
    suffix_week_start = (now - __import__('datetime').timedelta(days=9)).strftime('%Y%m%d')
    suffix_week_end = (now - __import__('datetime').timedelta(days=6)).strftime('%Y%m%d')
    
    print(f"=== Mangii Daily Report — {display_date} ===\n")
    
    # Growth
    g = q_growth(h24, now_us, suffix_start, suffix_end)
    gd = q_growth(h48, h24, suffix_start, suffix_end)
    gw = q_growth(h192, h168, suffix_week_start, suffix_week_end)
    seg = {r['segment']: int(r['users']) for r in g}
    segd = {r['segment']: int(r['users']) for r in gd}
    segw = {r['segment']: int(r['users']) for r in gw}
    
    new_users = seg.get('new', 0)
    returning = seg.get('returning', 0)
    
    # Countries
    countries_new = q_countries_new_users(h24, now_us, suffix_start, suffix_end)
    conv_by_country = q_conversion_by_country(h24, now_us, suffix_start, suffix_end)
    
    # Monetization funnel (today, yesterday, last week)
    funnel_raw = q_monetization_funnel(h24, now_us, suffix_start, suffix_end)
    funnel_raw_d = q_monetization_funnel(h48, h24, suffix_start, suffix_end)
    funnel_raw_w = q_monetization_funnel(h192, h168, suffix_week_start, suffix_week_end)

    def parse_funnel(data):
        result = {'new_users': 0, 'new_paywall': 0, 'new_paid': 0,
                  'new_cta': 0, 'new_plan_sel': 0, 'new_cancelled': 0, 'new_failed': 0,
                  'ret_users': 0, 'ret_paywall': 0, 'ret_paid': 0,
                  'ret_cta': 0, 'ret_plan_sel': 0, 'ret_cancelled': 0, 'ret_failed': 0}
        for r in data:
            seg = r.get('segment', '')
            if seg == 'new':
                result['new_users'] = int(r.get('total_users', 0) or 0)
                result['new_paywall'] = int(r.get('paywall_users', 0) or 0)
                result['new_paid'] = int(r.get('paid_users', 0) or 0)
                result['new_cta'] = int(r.get('cta_tapped_users', 0) or 0)
                result['new_plan_sel'] = int(r.get('plan_selected_users', 0) or 0)
                result['new_cancelled'] = int(r.get('purchase_cancelled_users', 0) or 0)
                result['new_failed'] = int(r.get('purchase_failed_users', 0) or 0)
            elif seg == 'returning':
                result['ret_users'] = int(r.get('total_users', 0) or 0)
                result['ret_paywall'] = int(r.get('paywall_users', 0) or 0)
                result['ret_paid'] = int(r.get('paid_users', 0) or 0)
                result['ret_cta'] = int(r.get('cta_tapped_users', 0) or 0)
                result['ret_plan_sel'] = int(r.get('plan_selected_users', 0) or 0)
                result['ret_cancelled'] = int(r.get('purchase_cancelled_users', 0) or 0)
                result['ret_failed'] = int(r.get('purchase_failed_users', 0) or 0)
        return result

    f = parse_funnel(funnel_raw)

    new_paid_rate = round(f['new_paid'] / max(1, f['new_paywall']) * 100, 1)
    ret_paid_rate = round(f['ret_paid'] / max(1, f['ret_paywall']) * 100, 1)
    total_paywall = f['new_paywall'] + f['ret_paywall']
    total_paid = f['new_paid'] + f['ret_paid']
    overall_rate = round(total_paid / max(1, total_paywall) * 100, 1)
    total_cta = f['new_cta'] + f['ret_cta']
    total_plan_sel = f['new_plan_sel'] + f['ret_plan_sel']
    total_cancelled = f['new_cancelled'] + f['ret_cancelled']
    total_failed = f['new_failed'] + f['ret_failed']

    # DoD / WoW for monetization
    fd = parse_funnel(funnel_raw_d)
    fw = parse_funnel(funnel_raw_w)
    dod_pw = fd['new_paywall'] + fd['ret_paywall']
    dod_paid = fd['new_paid'] + fd['ret_paid']
    dod_rate = round(dod_paid / max(1, dod_pw) * 100, 1)
    wow_pw = fw['new_paywall'] + fw['ret_paywall']
    wow_paid = fw['new_paid'] + fw['ret_paid']
    wow_rate = round(wow_paid / max(1, wow_pw) * 100, 1)

    # Product
    p = q_product(h24, now_us, suffix_start, suffix_end)
    pu = {r['event_name']: int(r['users']) for r in p}
    pe = {r['event_name']: int(r['events']) for r in p}
    
    # Experiments
    exp_metrics = q_experiment_metrics(h24, now_us, suffix_start, suffix_end)
    
    country_growth = format_country_growth(countries_new)
    country_conv = format_country_conversion(conv_by_country)
    exp_breakdown = format_experiments(exp_metrics)
    
    report = f'''📊 Mangii Daily — {display_date} (rolling 24h as of {display_time} ET)

👥 GROWTH
  New users: {new_users} (DoD {pct(new_users, segd.get('new', 0))} · WoW {pct(new_users, segw.get('new', 0))})
  Returning: {returning}

  📍 New Users by Country (Top 10):
{country_growth}

💰 MONETIZATION
  📊 Funnel:
    New users: {f['new_users']} → paywall {f['new_paywall']} → paid {f['new_paid']} ({new_paid_rate}%)
    Returning: {f['ret_users']} → paywall {f['ret_paywall']} → paid {f['ret_paid']} ({ret_paid_rate}%)

  Overall: {total_paywall} paywall → {total_paid} paid ({overall_rate}%)
  CTA tapped: {total_cta} · Plan selected: {total_plan_sel} · Purchase cancelled: {total_cancelled} · Failed: {total_failed}
  DoD {pct(overall_rate, dod_rate)} · WoW {pct(overall_rate, wow_rate)}

  📍 Conversion by Country (Top 10):
{country_conv}

🧪 EXPERIMENTS (B=Baseline | users/conv%)
{exp_breakdown}

🎨 PRODUCT
  Panels generated: {pu.get('panel_generated', 0)} users ({pe.get('panel_generated', 0)} panels)
  Generate tapped: {pu.get('panel_generate_tapped', 0)} users
  Blocked (no credits): {pu.get('panel_generate_blocked', 0)} users
  Credits depleted: {pu.get('credit_depleted', 0)} users
  Regenerated: {pu.get('panel_regenerated', 0)} users'''

    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / 'latest_report.txt').write_text(report + '\n')
    
    tg = send_telegram(report)
    print(report)
    print('TELEGRAM_SENT_OK')
    print(json.dumps(tg))
    
    # Generate and send heatmap if experiments exist
    if exp_metrics:
        heatmap_script = PROJECT_ROOT / 'scripts' / 'app_experiment_heatmap.py'
        heatmap_output = PROJECT_ROOT / 'reports' / 'mangii_experiments.png'
        subprocess.run([
            'python3', str(heatmap_script), 
            'Mangii', PROJECT_ID, DATASET_ID, str(LOGO_PATH)
        ], capture_output=True)
        
        if heatmap_output.exists():
            result = subprocess.run([
                'curl', '-s', '-X', 'POST',
                f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto',
                '-F', f'chat_id={CHAT_ID}',
                '-F', f'photo=@{heatmap_output}',
                '-F', 'caption=🧪 Mangii Experiments (24h)'
            ], capture_output=True, text=True)
            print('HEATMAP_SENT')


if __name__ == '__main__':
    main()
