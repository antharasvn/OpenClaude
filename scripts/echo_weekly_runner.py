#!/usr/bin/env python3
"""
Echo Weekly Report Runner
=========================
Rolling 7d vs prior 7d. Modeled on echo_daily_runner.py.
Does NOT deliver to Telegram — just prints + saves to latest_weekly_report.txt.
"""
import json, subprocess, pathlib, shutil, os
from pathlib import Path
from datetime import datetime, timezone, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ID = 'echo-79900'
DATASET_ID = 'analytics_420731841'
APP_NAME = 'Echo'
BASE = PROJECT_ROOT / 'data' / 'echo'


def run(cmd, input_text=None, timeout=300):
    # See daily_report_common.run — this shim was a copy of it with the timeout
    # parameter dropped.
    return subprocess.run(
        cmd, input=input_text, text=True, capture_output=True, check=False, timeout=timeout
    )


def bq_query(sql: str):
    cp = run(['bq', 'query', '--use_legacy_sql=false',
              f'--project_id={PROJECT_ID}', '--format=json'], input_text=sql)
    if cp.returncode != 0:
        raise RuntimeError(f"BQ ERROR:\n{cp.stderr or cp.stdout}\n---SQL---\n{sql}")
    return json.loads(cp.stdout or '[]')


def pct(cur, base):
    if not base:
        return 'N/A'
    try:
        return f'{((cur-base)/base)*100:+.0f}%'
    except ZeroDivisionError:
        return 'N/A'


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
  SELECT user_pseudo_id, event_name, event_timestamp, geo, user_properties FROM `{PROJECT_ID}.{DATASET_ID}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT user_pseudo_id, event_name, event_timestamp, geo, user_properties FROM `{PROJECT_ID}.{DATASET_ID}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
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
  SELECT user_pseudo_id, event_name, event_timestamp, geo, user_properties FROM `{PROJECT_ID}.{DATASET_ID}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT user_pseudo_id, event_name, event_timestamp, geo, user_properties FROM `{PROJECT_ID}.{DATASET_ID}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
)
SELECT geo.country, COUNT(DISTINCT user_pseudo_id) AS new_users
FROM all_events
WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  AND event_name = 'first_open'
GROUP BY 1 ORDER BY new_users DESC LIMIT 10
'''
    return bq_query(sql)


def q_monetization_funnel(start_us, end_us, suffix_start, suffix_end):
    sql = f'''
WITH all_events AS (
  SELECT user_pseudo_id, event_name, event_timestamp, geo, user_properties FROM `{PROJECT_ID}.{DATASET_ID}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT user_pseudo_id, event_name, event_timestamp, geo, user_properties FROM `{PROJECT_ID}.{DATASET_ID}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
), user_seg AS (
  SELECT user_pseudo_id, MAX(IF(event_name="first_open",1,0)) AS is_new
  FROM all_events WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1
), funnel AS (
  SELECT
    us.is_new,
    e.user_pseudo_id,
    MAX(IF(e.event_name = 'paywall_viewed', 1, 0)) AS saw_paywall,
    MAX(IF(e.event_name = 'purchase', 1, 0)) AS purchased,
    MAX(IF(e.event_name = 'credit_purchased', 1, 0)) AS credit_purchased
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
  SUM(credit_purchased) AS credit_users
FROM funnel
GROUP BY 1
'''
    return bq_query(sql)


def q_conversion_by_country(start_us, end_us, suffix_start, suffix_end):
    sql = f'''
WITH all_events AS (
  SELECT user_pseudo_id, event_name, event_timestamp, geo, user_properties FROM `{PROJECT_ID}.{DATASET_ID}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT user_pseudo_id, event_name, event_timestamp, geo, user_properties FROM `{PROJECT_ID}.{DATASET_ID}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
), country_events AS (
  SELECT geo.country, user_pseudo_id, event_name
  FROM all_events WHERE event_timestamp BETWEEN {start_us} AND {end_us}
), country_metrics AS (
  SELECT
    country,
    COUNT(DISTINCT IF(event_name = 'paywall_viewed', user_pseudo_id, NULL)) AS paywall_shown,
    COUNT(DISTINCT IF(event_name = 'purchase', user_pseudo_id, NULL)) AS converted
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
  SELECT user_pseudo_id, event_name, event_timestamp, geo, user_properties FROM `{PROJECT_ID}.{DATASET_ID}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT user_pseudo_id, event_name, event_timestamp, geo, user_properties FROM `{PROJECT_ID}.{DATASET_ID}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
)
SELECT event_name, COUNT(DISTINCT user_pseudo_id) AS users, COUNT(*) AS events
FROM all_events
WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  AND event_name IN (
    "music_creation_started","music_generation_completed","first_music_generated",
    "voice_cloning_started","voice_isolator_started","tts_started","tts_credit_charged",
    "tap_famous_voice","famous_voice_cloning_started","famous_voice_selected"
  )
GROUP BY 1 ORDER BY users DESC
'''
    return bq_query(sql)


def q_daily_trends(start_us, end_us, suffix_start, suffix_end):
    """Day-by-day new users + paid conversions over the window."""
    sql = f'''
WITH all_events AS (
  SELECT user_pseudo_id, event_name, event_timestamp, geo, user_properties FROM `{PROJECT_ID}.{DATASET_ID}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT user_pseudo_id, event_name, event_timestamp, geo, user_properties FROM `{PROJECT_ID}.{DATASET_ID}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
)
SELECT
  DATE(TIMESTAMP_MICROS(event_timestamp), 'America/New_York') AS d,
  COUNT(DISTINCT IF(event_name='first_open', user_pseudo_id, NULL)) AS new_users,
  COUNT(DISTINCT IF(event_name='purchase', user_pseudo_id, NULL)) AS paid_users,
  COUNT(DISTINCT IF(event_name='paywall_viewed', user_pseudo_id, NULL)) AS paywall_users
FROM all_events
WHERE event_timestamp BETWEEN {start_us} AND {end_us}
GROUP BY 1 ORDER BY 1
'''
    return bq_query(sql)


def get_running_experiments():
    firebase_path = shutil.which('firebase')
    if not firebase_path:
        for path in ['/opt/homebrew/bin/firebase', '~/.nvm/versions/node/v24.12.0/bin/firebase']:
            expanded = os.path.expanduser(path)
            if os.path.exists(expanded):
                firebase_path = expanded
                break
    if not firebase_path:
        return []
    result = subprocess.run(
        [firebase_path, 'remoteconfig:experiments:list', '--project', PROJECT_ID, '--pageSize', '0'],
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
  SELECT user_pseudo_id, event_name, event_timestamp, geo, user_properties FROM `{PROJECT_ID}.{DATASET_ID}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT user_pseudo_id, event_name, event_timestamp, geo, user_properties FROM `{PROJECT_ID}.{DATASET_ID}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
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
    MAX(IF(e.event_name = 'paywall_viewed', 1, 0)) as saw_paywall,
    MAX(IF(e.event_name = 'purchase_initiated', 1, 0)) as initiated,
    MAX(IF(e.event_name = 'purchase', 1, 0)) as converted
  FROM all_events e JOIN exp_users ue ON e.user_pseudo_id = ue.user_pseudo_id
  WHERE e.event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1, 2
)
SELECT variant, SUM(saw_paywall) as paywall,
  ROUND(SAFE_DIVIDE(SUM(initiated), SUM(saw_paywall)) * 100, 1) as initiate_rate,
  ROUND(SAFE_DIVIDE(SUM(converted), SUM(saw_paywall)) * 100, 1) as conv_rate
FROM user_events WHERE saw_paywall = 1 GROUP BY variant ORDER BY variant
'''
        try:
            rows = bq_query(sql)
            for row in rows:
                row['exp_id'] = exp_id
                row['exp_name'] = exp['name']
            results.extend(rows)
        except Exception:
            pass
    return results


def get_backend_errors(hours=168):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    cutoff_str = cutoff.strftime('%Y-%m-%dT%H:%M:%SZ')
    cmd = [
        'gcloud', 'logging', 'read',
        f'resource.type="cloud_function" AND severity>=ERROR AND timestamp>="{cutoff_str}"',
        f'--project={PROJECT_ID}',
        '--limit=2000',
        '--format=json'
    ]
    result = run(cmd)
    if result.returncode != 0:
        return {'total': -1, 'by_function': {}, 'by_type': {}, 'error': result.stderr}
    try:
        errors = json.loads(result.stdout or '[]')
    except json.JSONDecodeError:
        return {'total': -1, 'by_function': {}, 'by_type': {}, 'error': 'JSON parse failed'}

    by_function = {}
    by_type = {}
    for err in errors:
        func_name = err.get('resource', {}).get('labels', {}).get('function_name', 'unknown')
        by_function[func_name] = by_function.get(func_name, 0) + 1
        msg = err.get('jsonPayload', {}).get('message', '') or err.get('textPayload', '')
        low = msg.lower()
        if 'no user record' in low:
            err_type = 'UserNotFound'
        elif 'timeout' in low:
            err_type = 'Timeout'
        elif 'quota' in low or 'rate limit' in low:
            err_type = 'Quota'
        elif 'api' in low and 'error' in low:
            err_type = 'APIError'
        else:
            err_type = 'Other'
        by_type[err_type] = by_type.get(err_type, 0) + 1
    return {
        'total': len(errors),
        'by_function': by_function,
        'by_type': by_type,
        'actionable': len(errors) - by_type.get('UserNotFound', 0),
    }


def format_backend_errors(errors):
    if errors.get('total', 0) < 0:
        return f"  ⚠️ Could not fetch backend logs: {errors.get('error','')[:120]}"
    total = errors['total']
    actionable = errors.get('actionable', total)
    if total == 0:
        return "  ✅ No errors in last 7d"
    lines = [f"  Total: {total} | Actionable: {actionable}"]
    top_funcs = sorted(errors['by_function'].items(), key=lambda x: -x[1])[:5]
    if top_funcs:
        func_str = ', '.join([f"{(k.split('-')[-1] if '-' in k else k[:18])}: {v}" for k, v in top_funcs])
        lines.append(f"  By function: {func_str}")
    if errors['by_type']:
        type_str = ', '.join([f"{k}: {v}" for k, v in sorted(errors['by_type'].items(), key=lambda x: -x[1])])
        lines.append(f"  By type: {type_str}")
    if actionable > 200:
        lines[0] = f"  🚨 Total: {total} | Actionable: {actionable}"
    elif actionable > 100:
        lines[0] = f"  ⚠️ Total: {total} | Actionable: {actionable}"
    return '\n'.join(lines)


def format_country_growth(cur_rows, prev_rows):
    prev = {r.get('country', '?'): int(r.get('new_users', 0) or 0) for r in prev_rows}
    lines = []
    for r in cur_rows[:10]:
        c = r.get('country', '?')
        n = int(r.get('new_users', 0) or 0)
        lines.append(f"    {c}: {n} (WoW {pct(n, prev.get(c, 0))})")
    return '\n'.join(lines)


def format_country_conversion(data):
    total_shown = sum(int(r.get('paywall_shown', 0) or 0) for r in data)
    total_conv = sum(int(r.get('converted', 0) or 0) for r in data)
    total_rate = round(total_conv / max(1, total_shown) * 100, 1)
    lines = [
        f"    TOTAL: {total_shown}→{total_conv} ({total_rate}%) {get_conversion_emoji(total_rate)}",
        "    ─────────────────────",
    ]
    for r in data[:10]:
        country = r.get('country', '?')
        shown = int(r.get('paywall_shown', 0) or 0)
        conv = int(r.get('converted', 0) or 0)
        rate = float(r.get('conversion_rate', 0) or 0)
        lines.append(f"    {country}: {shown}→{conv} ({rate}%) {get_conversion_emoji(rate)}")
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
        lines.append(f"    {exp_id} — {data['name']}: {' | '.join(var_strs)}")
    return '\n'.join(lines)


def format_trends(rows):
    if not rows:
        return "    (no data)"
    rows_sorted = sorted(rows, key=lambda r: r.get('d', ''))
    max_new = max((int(r.get('new_users', 0) or 0) for r in rows_sorted), default=1) or 1
    lines = ["    Date        New   Paywall   Paid   spark"]
    for r in rows_sorted:
        d = r.get('d', '?')
        n = int(r.get('new_users', 0) or 0)
        pw = int(r.get('paywall_users', 0) or 0)
        pd = int(r.get('paid_users', 0) or 0)
        blocks = '█' * max(1, int((n / max_new) * 20)) if n else ''
        lines.append(f"    {d}  {n:>4}  {pw:>6}   {pd:>4}   {blocks}")
    return '\n'.join(lines)


def parse_funnel(data):
    result = {'new_users': 0, 'new_paywall': 0, 'new_paid': 0, 'new_credits': 0,
              'ret_users': 0, 'ret_paywall': 0, 'ret_paid': 0, 'ret_credits': 0}
    for r in data:
        seg = r.get('segment', '')
        if seg == 'new':
            result['new_users'] = int(r.get('total_users', 0) or 0)
            result['new_paywall'] = int(r.get('paywall_users', 0) or 0)
            result['new_paid'] = int(r.get('paid_users', 0) or 0)
            result['new_credits'] = int(r.get('credit_users', 0) or 0)
        elif seg == 'returning':
            result['ret_users'] = int(r.get('total_users', 0) or 0)
            result['ret_paywall'] = int(r.get('paywall_users', 0) or 0)
            result['ret_paid'] = int(r.get('paid_users', 0) or 0)
            result['ret_credits'] = int(r.get('credit_users', 0) or 0)
    return result


def funnel_overall_rate(f):
    total_pw = f['new_paywall'] + f['ret_paywall']
    total_pd = f['new_paid'] + f['ret_paid']
    return round(total_pd / max(1, total_pw) * 100, 1)


def main():
    errors_encountered = []

    now = datetime.now()
    now_epoch = int(now.timestamp())
    now_us = now_epoch * 1_000_000
    d7 = (now_epoch - 7 * 86400) * 1_000_000
    d14 = (now_epoch - 14 * 86400) * 1_000_000

    display_date = now.strftime('%Y-%m-%d')
    display_time = now.strftime('%H:%M')
    cur_start = (now - timedelta(days=7)).strftime('%Y-%m-%d')
    cur_end = now.strftime('%Y-%m-%d')
    prior_start = (now - timedelta(days=14)).strftime('%Y-%m-%d')
    prior_end = cur_start

    # Table suffix window — scan enough tables to cover the full 14d range plus today's intraday
    suffix_cur_start = (now - timedelta(days=8)).strftime('%Y%m%d')    # +1 day back for safety
    suffix_cur_end = now.strftime('%Y%m%d')
    suffix_prev_start = (now - timedelta(days=15)).strftime('%Y%m%d')
    suffix_prev_end = (now - timedelta(days=6)).strftime('%Y%m%d')

    # ===== Growth =====
    try:
        g_cur = q_growth(d7, now_us, suffix_cur_start, suffix_cur_end)
        g_prev = q_growth(d14, d7, suffix_prev_start, suffix_prev_end)
        seg_cur = {r['segment']: int(r['users']) for r in g_cur}
        seg_prev = {r['segment']: int(r['users']) for r in g_prev}
        new_users = seg_cur.get('new', 0)
        returning = seg_cur.get('returning', 0)
        prev_new = seg_prev.get('new', 0)
        prev_returning = seg_prev.get('returning', 0)
    except Exception as e:
        errors_encountered.append(('growth', str(e)))
        new_users = returning = prev_new = prev_returning = 0

    # ===== Countries (new users) =====
    try:
        cur_cty_new = q_countries_new_users(d7, now_us, suffix_cur_start, suffix_cur_end)
        prev_cty_new = q_countries_new_users(d14, d7, suffix_prev_start, suffix_prev_end)
        country_growth_block = format_country_growth(cur_cty_new, prev_cty_new)
    except Exception as e:
        errors_encountered.append(('countries_new', str(e)))
        country_growth_block = "    ⚠️ query failed"

    # ===== Monetization funnel =====
    try:
        fr_cur = q_monetization_funnel(d7, now_us, suffix_cur_start, suffix_cur_end)
        fr_prev = q_monetization_funnel(d14, d7, suffix_prev_start, suffix_prev_end)
        f = parse_funnel(fr_cur)
        fp = parse_funnel(fr_prev)
        new_paid_rate = round(f['new_paid'] / max(1, f['new_paywall']) * 100, 1)
        ret_paid_rate = round(f['ret_paid'] / max(1, f['ret_paywall']) * 100, 1)
        total_paywall = f['new_paywall'] + f['ret_paywall']
        total_paid = f['new_paid'] + f['ret_paid']
        overall_rate = funnel_overall_rate(f)
        overall_rate_prev = funnel_overall_rate(fp)
        total_credits_cur = f['new_credits'] + f['ret_credits']
        total_credits_prev = fp['new_credits'] + fp['ret_credits']
        total_paid_prev = fp['new_paid'] + fp['ret_paid']
    except Exception as e:
        errors_encountered.append(('monetization', str(e)))
        f = parse_funnel([])
        fp = parse_funnel([])
        new_paid_rate = ret_paid_rate = overall_rate = overall_rate_prev = 0
        total_paywall = total_paid = total_credits_cur = total_credits_prev = total_paid_prev = 0

    # ===== Conversion by country =====
    try:
        conv_by_country = q_conversion_by_country(d7, now_us, suffix_cur_start, suffix_cur_end)
        country_conv_block = format_country_conversion(conv_by_country)
    except Exception as e:
        errors_encountered.append(('conv_by_country', str(e)))
        country_conv_block = "    ⚠️ query failed"

    # ===== Product =====
    try:
        p_cur = q_product(d7, now_us, suffix_cur_start, suffix_cur_end)
        p_prev = q_product(d14, d7, suffix_prev_start, suffix_prev_end)
        pu = {r['event_name']: int(r['users']) for r in p_cur}
        pe = {r['event_name']: int(r['events']) for r in p_cur}
        pu_prev = {r['event_name']: int(r['users']) for r in p_prev}
    except Exception as e:
        errors_encountered.append(('product', str(e)))
        pu = pe = pu_prev = {}

    # ===== Experiments =====
    try:
        exp_metrics = q_experiment_metrics(d7, now_us, suffix_cur_start, suffix_cur_end)
        exp_block = format_experiments(exp_metrics)
    except Exception as e:
        errors_encountered.append(('experiments', str(e)))
        exp_block = "    ⚠️ query failed"

    # ===== Trends =====
    try:
        trend_rows = q_daily_trends(d7, now_us, suffix_cur_start, suffix_cur_end)
        trend_block = format_trends(trend_rows)
    except Exception as e:
        errors_encountered.append(('trends', str(e)))
        trend_block = "    ⚠️ query failed"

    # ===== Backend =====
    backend_errors = get_backend_errors(hours=24 * 7)
    backend_section = format_backend_errors(backend_errors)

    # ===== Assemble report =====
    report = f'''📊 Echo Weekly — {display_date} (rolling 7d as of {display_time} ET)
Window: {cur_start} → {cur_end}  vs prior {prior_start} → {prior_end}

👥 GROWTH
  New users: {new_users} (WoW {pct(new_users, prev_new)})
  Returning: {returning} (WoW {pct(returning, prev_returning)})

  📍 New Users by Country (Top 10):
{country_growth_block}

💰 MONETIZATION
  📊 Funnel (7d):
    New users: {f['new_users']} → paywall {f['new_paywall']} → paid {f['new_paid']} ({new_paid_rate}%) {get_conversion_emoji(new_paid_rate)}
    Returning: {f['ret_users']} → paywall {f['ret_paywall']} → paid {f['ret_paid']} ({ret_paid_rate}%) {get_conversion_emoji(ret_paid_rate)}

  Overall: {total_paywall} paywall → {total_paid} paid ({overall_rate}%) {get_conversion_emoji(overall_rate)}
  WoW paid users: {total_paid} vs {total_paid_prev} ({pct(total_paid, total_paid_prev)})
  WoW conv rate:  {overall_rate}% vs {overall_rate_prev}% ({pct(overall_rate, overall_rate_prev)})
  Credits purchased: {total_credits_cur} users (WoW {pct(total_credits_cur, total_credits_prev)})

  📍 Conversion by Country (Top 10):
{country_conv_block}

🧪 EXPERIMENTS (B=Baseline | users/conv%, 7d)
{exp_block}

🎵 PRODUCT
  Music created: {pu.get('music_generation_completed', 0)} users ({pe.get('music_generation_completed', 0)} tracks) — WoW {pct(pu.get('music_generation_completed', 0), pu_prev.get('music_generation_completed', 0))}
  First music: {pu.get('first_music_generated', 0)} new users — WoW {pct(pu.get('first_music_generated', 0), pu_prev.get('first_music_generated', 0))}

  🎤 VOICE FEATURES
  Famous voices tapped: {pu.get('tap_famous_voice', 0)} users ({pe.get('tap_famous_voice', 0)} taps) — WoW {pct(pu.get('tap_famous_voice', 0), pu_prev.get('tap_famous_voice', 0))}
  Famous voice cloning: {pu.get('famous_voice_cloning_started', 0)} users — WoW {pct(pu.get('famous_voice_cloning_started', 0), pu_prev.get('famous_voice_cloning_started', 0))}
  Custom voice cloning: {pu.get('voice_cloning_started', 0)} users — WoW {pct(pu.get('voice_cloning_started', 0), pu_prev.get('voice_cloning_started', 0))}
  Voice isolator: {pu.get('voice_isolator_started', 0)} users — WoW {pct(pu.get('voice_isolator_started', 0), pu_prev.get('voice_isolator_started', 0))}
  TTS: {pu.get('tts_started', 0)} users ({pe.get('tts_credit_charged', 0)} credits) — WoW {pct(pu.get('tts_started', 0), pu_prev.get('tts_started', 0))}

🔧 BACKEND (Firebase Functions, 7d)
{backend_section}

📈 TRENDS (per-day, America/New_York)
{trend_block}'''

    if errors_encountered:
        report += "\n\n⚠️ ERRORS\n"
        for name, err in errors_encountered:
            report += f"  [{name}] {err[:300]}\n"

    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / 'latest_weekly_report.txt').write_text(report + '\n')
    print(report)


if __name__ == '__main__':
    main()
