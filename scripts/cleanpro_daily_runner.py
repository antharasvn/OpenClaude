#!/usr/bin/env python3
import json, subprocess, pathlib, urllib.request
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent

BOT_TOKEN = '8628864855:AAFWSgQCzUIGNtBK1dQk28rCJ7rqBo3v0zU'
CHAT_ID = '-5201056067'
BASE = PROJECT_ROOT / 'data' / 'cleanpro'
REPORT_PATH = PROJECT_ROOT / 'reports' / 'cleanpro' / 'daily'


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


def send_telegram_photo(photo_path: str, caption: str = ""):
    """Send a photo to Telegram."""
    import mimetypes
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    
    with open(photo_path, 'rb') as f:
        photo_data = f.read()
    
    body = []
    body.append(f'--{boundary}'.encode())
    body.append(b'Content-Disposition: form-data; name="chat_id"')
    body.append(b'')
    body.append(CHAT_ID.encode())
    
    body.append(f'--{boundary}'.encode())
    body.append(f'Content-Disposition: form-data; name="photo"; filename="{pathlib.Path(photo_path).name}"'.encode())
    body.append(b'Content-Type: image/png')
    body.append(b'')
    body.append(photo_data)
    
    if caption:
        body.append(f'--{boundary}'.encode())
        body.append(b'Content-Disposition: form-data; name="caption"')
        body.append(b'')
        body.append(caption.encode())
    
    body.append(f'--{boundary}--'.encode())
    body.append(b'')
    
    body_bytes = b'\r\n'.join(body)
    
    req = urllib.request.Request(
        f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto',
        data=body_bytes,
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def generate_experiment_heatmap():
    """Generate experiment heatmap image using experiment_heatmap_pro.py."""
    heatmap_script = PROJECT_ROOT / 'scripts' / 'experiment_heatmap_pro.py'
    if not heatmap_script.exists():
        return None

    result = subprocess.run(['python3', str(heatmap_script)], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Heatmap generation failed: {result.stderr}")
        return None

    heatmap_path = PROJECT_ROOT / 'reports' / 'experiments_heatmap_pro.png'
    if heatmap_path.exists():
        return str(heatmap_path)
    return None


def pct(cur, base):
    if not base:
        return 'N/A'
    return f'{((cur-base)/base)*100:+.0f}%'


def q_growth(start_us, end_us, suffix_start, suffix_end):
    sql = f'''
WITH all_events AS (
  SELECT * FROM `cleaner-app-e98f0.analytics_269202926.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `cleaner-app-e98f0.analytics_269202926.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
), user_seg AS (
  SELECT user_pseudo_id, MAX(IF(event_name="first_open",1,0)) AS is_new
  FROM all_events WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1
)
SELECT IF(is_new=1,"new","returning") AS segment, COUNT(*) AS users
FROM user_seg GROUP BY 1
'''
    return bq_query(sql)


def q_countries(start_us, end_us, suffix_start, suffix_end):
    sql = f'''
WITH all_events AS (
  SELECT * FROM `cleaner-app-e98f0.analytics_269202926.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `cleaner-app-e98f0.analytics_269202926.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
)
SELECT geo.country, COUNT(DISTINCT user_pseudo_id) AS users
FROM all_events WHERE event_timestamp BETWEEN {start_us} AND {end_us}
GROUP BY 1 ORDER BY users DESC LIMIT 10
'''
    return bq_query(sql)


def q_countries_new_users(start_us, end_us, suffix_start, suffix_end):
    """Get new user counts by top 10 countries."""
    sql = f'''
WITH all_events AS (
  SELECT * FROM `cleaner-app-e98f0.analytics_269202926.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `cleaner-app-e98f0.analytics_269202926.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
)
SELECT geo.country, COUNT(DISTINCT user_pseudo_id) AS new_users
FROM all_events 
WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  AND event_name = 'first_open'
GROUP BY 1 ORDER BY new_users DESC LIMIT 10
'''
    return bq_query(sql)


def q_conversion_by_country(start_us, end_us, suffix_start, suffix_end):
    """Get conversion metrics by top 10 countries.
    Uses client-side events only (no rc_* S2S events which have different user_pseudo_id)."""
    sql = f'''
WITH all_events AS (
  SELECT * FROM `cleaner-app-e98f0.analytics_269202926.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `cleaner-app-e98f0.analytics_269202926.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
), country_events AS (
  SELECT
    geo.country,
    user_pseudo_id,
    event_name
  FROM all_events
  WHERE event_timestamp BETWEEN {start_us} AND {end_us}
    AND event_name IN ('onboarding_paywall_shown', 'cleanpro_paywall_shown',
                       'onboarding_paywall_converted', 'cleanpro_paywall_converted', 'purchase')
), country_metrics AS (
  SELECT
    country,
    COUNT(DISTINCT CASE WHEN event_name IN ('onboarding_paywall_shown', 'cleanpro_paywall_shown') THEN user_pseudo_id END) AS paywall_shown,
    COUNT(DISTINCT CASE WHEN event_name IN ('onboarding_paywall_converted', 'cleanpro_paywall_converted', 'purchase') THEN user_pseudo_id END) AS converted
  FROM country_events
  GROUP BY country
)
SELECT
  country,
  paywall_shown,
  converted,
  ROUND(SAFE_DIVIDE(converted, paywall_shown) * 100, 1) AS conversion_rate
FROM country_metrics
WHERE paywall_shown > 0
ORDER BY paywall_shown DESC
LIMIT 10
'''
    return bq_query(sql)


def q_onboarding_completion_by_country(start_us, end_us, suffix_start, suffix_end):
    """Get onboarding completion rate by country.
    
    Flow: first_open → onboarding_paywall_shown → onboarding_paywall_dismissed (= reached home)
    Completion = users who dismissed paywall / users who saw paywall
    """
    sql = f'''
WITH all_events AS (
  SELECT * FROM `cleaner-app-e98f0.analytics_269202926.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `cleaner-app-e98f0.analytics_269202926.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
), country_events AS (
  SELECT 
    geo.country,
    user_pseudo_id,
    event_name
  FROM all_events
  WHERE event_timestamp BETWEEN {start_us} AND {end_us}
    AND event_name IN ('first_open', 'onboarding_paywall_shown', 'onboarding_paywall_dismissed', 'onboarding_paywall_converted')
), country_metrics AS (
  SELECT 
    country,
    COUNT(DISTINCT CASE WHEN event_name = 'first_open' THEN user_pseudo_id END) AS new_users,
    COUNT(DISTINCT CASE WHEN event_name = 'onboarding_paywall_shown' THEN user_pseudo_id END) AS saw_paywall,
    COUNT(DISTINCT CASE WHEN event_name IN ('onboarding_paywall_dismissed', 'onboarding_paywall_converted') THEN user_pseudo_id END) AS finished_onboarding
  FROM country_events
  GROUP BY country
)
SELECT 
  country,
  new_users,
  saw_paywall,
  finished_onboarding,
  ROUND(SAFE_DIVIDE(saw_paywall, new_users) * 100, 1) AS reach_paywall_rate,
  ROUND(SAFE_DIVIDE(finished_onboarding, saw_paywall) * 100, 1) AS completion_rate
FROM country_metrics
WHERE new_users > 0
ORDER BY new_users DESC
LIMIT 10
'''
    return bq_query(sql)


def q_monetization_funnel(start_us, end_us, suffix_start, suffix_end):
    """Monetization funnel: new vs returning users who hit paywall/purchase events.
    Note: rc_* events are S2S from RevenueCat and use a different user_pseudo_id,
    so they are queried separately via q_rc_events."""
    sql = f'''
WITH all_events AS (
  SELECT * FROM `cleaner-app-e98f0.analytics_269202926.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `cleaner-app-e98f0.analytics_269202926.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
), user_seg AS (
  SELECT user_pseudo_id, MAX(IF(event_name="first_open",1,0)) AS is_new
  FROM all_events WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1
), funnel AS (
  SELECT
    us.is_new,
    e.user_pseudo_id,
    MAX(IF(e.event_name IN ('onboarding_paywall_shown', 'cleanpro_paywall_shown'), 1, 0)) AS saw_paywall,
    MAX(IF(e.event_name IN ('onboarding_paywall_converted', 'cleanpro_paywall_converted', 'native_paywall_converted'), 1, 0)) AS started_trial,
    MAX(IF(e.event_name IN ('purchase', 'app_initial_purchase'), 1, 0)) AS purchased
  FROM all_events e
  JOIN user_seg us ON e.user_pseudo_id = us.user_pseudo_id
  WHERE e.event_timestamp BETWEEN {start_us} AND {end_us}
    AND NOT STARTS_WITH(e.event_name, 'rc_')
  GROUP BY 1, 2
)
SELECT
  IF(is_new=1,"new","returning") AS segment,
  COUNT(*) AS total_users,
  SUM(saw_paywall) AS paywall_users,
  SUM(started_trial) AS trial_users,
  SUM(purchased) AS paid_users
FROM funnel
GROUP BY 1
'''
    return bq_query(sql)


def q_rc_events(start_us, end_us, suffix_start, suffix_end):
    """Query RevenueCat S2S events separately (different user_pseudo_id namespace)."""
    sql = f'''
WITH all_events AS (
  SELECT * FROM `cleaner-app-e98f0.analytics_269202926.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `cleaner-app-e98f0.analytics_269202926.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
)
SELECT
  event_name,
  COUNT(DISTINCT user_pseudo_id) AS users
FROM all_events
WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  AND event_name IN ('rc_trial_start', 'rc_initial_purchase', 'rc_cancellation', 'rc_expiration', 'rc_billing_issue')
GROUP BY 1
'''
    return bq_query(sql)


def q_trial_to_paid_7d(now_us, suffix_start_7d, suffix_end):
    """Rolling 7-day trial-to-paid: rc_trial_start users who also had rc_initial_purchase."""
    start_7d = now_us - 604800 * 1_000_000
    sql = f'''
WITH all_events AS (
  SELECT * FROM `cleaner-app-e98f0.analytics_269202926.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start_7d}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `cleaner-app-e98f0.analytics_269202926.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start_7d}' AND '{suffix_end}'
), trial_users AS (
  SELECT DISTINCT user_pseudo_id
  FROM all_events
  WHERE event_timestamp BETWEEN {start_7d} AND {now_us}
    AND event_name = 'rc_trial_start'
), paid_users AS (
  SELECT DISTINCT user_pseudo_id
  FROM all_events
  WHERE event_timestamp BETWEEN {start_7d} AND {now_us}
    AND event_name = 'rc_initial_purchase'
)
SELECT
  (SELECT COUNT(*) FROM trial_users) AS trial_count,
  (SELECT COUNT(*) FROM trial_users t JOIN paid_users p ON t.user_pseudo_id = p.user_pseudo_id) AS trial_to_paid_count
'''
    return bq_query(sql)


def q_product(start_us, end_us, suffix_start, suffix_end):
    sql = f'''
WITH all_events AS (
  SELECT * FROM `cleaner-app-e98f0.analytics_269202926.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `cleaner-app-e98f0.analytics_269202926.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
)
SELECT event_name, COUNT(DISTINCT user_pseudo_id) AS users, COUNT(*) AS events
FROM all_events
WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  AND event_name IN ("scan_completed","first_scan_complete","clean_completed","first_delete_complete","scan_v2_start","scan_v2_complete")
GROUP BY 1 ORDER BY users DESC
'''
    return bq_query(sql)


def parse_funnel(data):
    """Parse monetization funnel query results into a dict."""
    result = {'new_users': 0, 'new_paywall': 0, 'new_trial': 0, 'new_paid': 0,
              'ret_users': 0, 'ret_paywall': 0, 'ret_trial': 0, 'ret_paid': 0}
    for r in data:
        seg = r.get('segment', '')
        if seg == 'new':
            result['new_users'] = int(r.get('total_users', 0) or 0)
            result['new_paywall'] = int(r.get('paywall_users', 0) or 0)
            result['new_trial'] = int(r.get('trial_users', 0) or 0)
            result['new_paid'] = int(r.get('paid_users', 0) or 0)
        elif seg == 'returning':
            result['ret_users'] = int(r.get('total_users', 0) or 0)
            result['ret_paywall'] = int(r.get('paywall_users', 0) or 0)
            result['ret_trial'] = int(r.get('trial_users', 0) or 0)
            result['ret_paid'] = int(r.get('paid_users', 0) or 0)
    return result


def parse_rc_events(data):
    """Parse RevenueCat S2S event counts."""
    d = {r.get('event_name'): int(r.get('users', 0) or 0) for r in data}
    return {
        'rc_trial_start': d.get('rc_trial_start', 0),
        'rc_initial_purchase': d.get('rc_initial_purchase', 0),
        'rc_cancellation': d.get('rc_cancellation', 0),
        'rc_expiration': d.get('rc_expiration', 0),
        'rc_billing_issue': d.get('rc_billing_issue', 0),
    }


def format_country_growth(countries_new):
    """Format top 10 countries with new user counts."""
    lines = []
    for r in countries_new[:10]:
        country = r.get('country', '?')
        users = int(r.get('new_users', 0))
        lines.append(f"    {country}: {users}")
    return '\n'.join(lines)


def get_conversion_emoji(rate):
    """Get emoji based on conversion rate."""
    if rate > 50:
        return '🟣'  # Exceptional
    elif rate > 30:
        return '🔵'  # Excellent
    elif rate > 20:
        return '🟢'  # Great
    elif rate > 10:
        return '✅'  # Good
    elif rate > 5:
        return '⚠️'  # OK
    elif rate > 2:
        return '🟠'  # Below average
    else:
        return '🔴'  # Poor


def format_country_conversion(conv_by_country):
    """Format top 10 countries with conversion rates.
    
    Emoji scale:
    🟣 >50% - Exceptional
    🔵 >30% - Excellent  
    🟢 >20% - Great
    ✅ >10% - Good
    ⚠️ >5%  - OK
    🟠 >2%  - Below average
    🔴 ≤2%  - Poor
    """
    # Calculate summary row
    total_shown = sum(int(r.get('paywall_shown', 0) or 0) for r in conv_by_country)
    total_converted = sum(int(r.get('converted', 0) or 0) for r in conv_by_country)
    overall_rate = round((total_converted / total_shown * 100), 1) if total_shown else 0.0
    overall_emoji = get_conversion_emoji(overall_rate)
    
    lines = [f"    TOTAL: {total_shown}→{total_converted} ({overall_rate}%) {overall_emoji}"]
    lines.append("    ─────────────────────")
    
    for r in conv_by_country[:10]:
        country = r.get('country', '?')
        shown = int(r.get('paywall_shown', 0))
        converted = int(r.get('converted', 0))
        rate = float(r.get('conversion_rate', 0) or 0)
        emoji = get_conversion_emoji(rate)
        lines.append(f"    {country}: {shown}→{converted} ({rate}%) {emoji}")
    
    return '\n'.join(lines)


def get_onboarding_emoji(rate):
    """Emoji for onboarding completion rate (higher thresholds than conversion)."""
    if rate >= 95: return '🟣'
    elif rate >= 90: return '🔵'
    elif rate >= 85: return '🟢'
    elif rate >= 80: return '✅'
    elif rate >= 70: return '⚠️'
    elif rate >= 60: return '🟠'
    else: return '🔴'


def format_onboarding_completion(onboarding_data):
    """Format onboarding completion rate by country.
    Shows: new users → reached paywall → finished onboarding (dismissed or converted)
    """
    lines = []
    for r in onboarding_data[:10]:
        country = r.get('country', '?')
        new_users = int(r.get('new_users', 0) or 0)
        saw_paywall = int(r.get('saw_paywall', 0) or 0)
        finished = int(r.get('finished_onboarding', 0) or 0)
        reach_rate = float(r.get('reach_paywall_rate', 0) or 0)
        completion_rate = float(r.get('completion_rate', 0) or 0)
        
        emoji = get_onboarding_emoji(completion_rate)
        lines.append(f"    {country}: {new_users}→{saw_paywall}→{finished} ({completion_rate}% complete) {emoji}")
    return '\n'.join(lines)


def get_running_experiments():
    """Get list of running experiments from Firebase CLI."""
    import subprocess as sp
    result = sp.run(
        ['firebase', 'remoteconfig:experiments:list', '--project', 'cleaner-app-e98f0', '--pageSize', '0'],
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
                    'name': parts[1][:35],
                    'start_time': parts[4][:10] if len(parts[4]) > 10 else parts[4]
                })
    return experiments


def q_experiment_metrics(start_us, end_us, suffix_start, suffix_end):
    """Get metrics for all running experiments."""
    # Get running experiment IDs first
    experiments = get_running_experiments()
    if not experiments:
        return []
    
    exp_ids = [e['id'] for e in experiments]
    
    results = []
    for exp_id in exp_ids[:8]:  # Limit to 8 experiments
        sql = f'''
WITH all_events AS (
  SELECT * FROM `cleaner-app-e98f0.analytics_269202926.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `cleaner-app-e98f0.analytics_269202926.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
),
exp_users AS (
  SELECT 
    user_pseudo_id,
    (SELECT value.string_value FROM UNNEST(user_properties) WHERE key = 'firebase_exp_{exp_id}') as variant
  FROM all_events
  WHERE event_timestamp BETWEEN {start_us} AND {end_us}
    AND (SELECT value.string_value FROM UNNEST(user_properties) WHERE key = 'firebase_exp_{exp_id}') IS NOT NULL
  GROUP BY 1, 2
),
user_events AS (
  SELECT 
    ue.variant,
    e.user_pseudo_id,
    MAX(IF(e.event_name = 'onboarding_paywall_shown', 1, 0)) as saw_paywall,
    MAX(IF(e.event_name IN ('onboarding_paywall_dismissed', 'onboarding_paywall_converted'), 1, 0)) as finished,
    MAX(IF(e.event_name = 'rc_trial_start', 1, 0)) as trial,
    MAX(IF(e.event_name IN ('onboarding_paywall_converted', 'rc_initial_purchase'), 1, 0)) as converted
  FROM all_events e
  JOIN exp_users ue ON e.user_pseudo_id = ue.user_pseudo_id
  WHERE e.event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1, 2
)
SELECT 
  '{exp_id}' as exp_id,
  variant,
  SUM(saw_paywall) as paywall,
  ROUND(SAFE_DIVIDE(SUM(finished), SUM(saw_paywall)) * 100, 1) as completion,
  ROUND(SAFE_DIVIDE(SUM(trial), SUM(saw_paywall)) * 100, 1) as trial_rate,
  ROUND(SAFE_DIVIDE(SUM(converted), SUM(saw_paywall)) * 100, 1) as conv_rate
FROM user_events
WHERE saw_paywall = 1
GROUP BY variant
ORDER BY variant
'''
        try:
            rows = bq_query(sql)
            for row in rows:
                row['exp_name'] = next((e['name'] for e in experiments if e['id'] == exp_id), exp_id)
            results.extend(rows)
        except:
            pass
    
    return results


def format_experiments(exp_metrics):
    """Format running experiments with key metrics."""
    if not exp_metrics:
        return "    No running experiments"
    
    # Group by experiment
    exp_data = {}
    for row in exp_metrics:
        exp_id = row.get('exp_id', '?')
        if exp_id not in exp_data:
            exp_data[exp_id] = {'name': row.get('exp_name', exp_id), 'variants': []}
        exp_data[exp_id]['variants'].append(row)
    
    lines = []
    for exp_id, data in exp_data.items():
        variants = data['variants']
        name = data['name'][:25]
        
        # Format: Exp ID: Name | V0: X% done, Y% trial, Z% conv | V1: ...
        var_strs = []
        for v in sorted(variants, key=lambda x: x.get('variant', '0')):
            variant = v.get('variant', '?')
            paywall = int(v.get('paywall', 0) or 0)
            completion = float(v.get('completion', 0) or 0)
            trial = float(v.get('trial_rate', 0) or 0)
            conv = float(v.get('conv_rate', 0) or 0)
            
            vname = 'B' if variant == '0' else f'V{variant}'
            # Use same color scale as conversion by country
            emoji = get_conversion_emoji(conv)
            var_strs.append(f"{vname}:{paywall}u/{completion:.0f}%/{trial:.0f}%/{conv:.0f}%{emoji}")
        
        lines.append(f"    {exp_id}: {' | '.join(var_strs)}")
    
    return '\n'.join(lines)


def main():
    now_epoch = int(subprocess.run(['bash','-lc','TZ="Asia/Saigon" date +%s'], capture_output=True, text=True).stdout.strip())
    now_us = now_epoch * 1_000_000
    h24 = (now_epoch - 86400) * 1_000_000
    h48 = (now_epoch - 172800) * 1_000_000
    h168 = (now_epoch - 604800) * 1_000_000
    h192 = (now_epoch - 691200) * 1_000_000
    display_date = subprocess.run(['bash','-lc','TZ="Asia/Saigon" date +%Y-%m-%d'], capture_output=True, text=True).stdout.strip()
    display_time = subprocess.run(['bash','-lc','TZ="Asia/Saigon" date +%H:%M'], capture_output=True, text=True).stdout.strip()
    suffix_start = subprocess.run(['bash','-lc','TZ="Asia/Saigon" date -v-2d +%Y%m%d 2>/dev/null || TZ="Asia/Saigon" date -d "2 days ago" +%Y%m%d'], capture_output=True, text=True).stdout.strip()
    suffix_end = subprocess.run(['bash','-lc','TZ="Asia/Saigon" date +%Y%m%d'], capture_output=True, text=True).stdout.strip()
    suffix_week_start = subprocess.run(['bash','-lc','TZ="Asia/Saigon" date -v-9d +%Y%m%d 2>/dev/null || TZ="Asia/Saigon" date -d "9 days ago" +%Y%m%d'], capture_output=True, text=True).stdout.strip()
    suffix_week_end = subprocess.run(['bash','-lc','TZ="Asia/Saigon" date -v-6d +%Y%m%d 2>/dev/null || TZ="Asia/Saigon" date -d "6 days ago" +%Y%m%d'], capture_output=True, text=True).stdout.strip()

    g = q_growth(h24, now_us, suffix_start, suffix_end)
    gd = q_growth(h48, h24, suffix_start, suffix_end)
    gw = q_growth(h192, h168, suffix_week_start, suffix_week_end)
    countries = q_countries(h24, now_us, suffix_start, suffix_end)
    countries_new = q_countries_new_users(h24, now_us, suffix_start, suffix_end)
    conv_by_country = q_conversion_by_country(h24, now_us, suffix_start, suffix_end)
    onboarding_by_country = q_onboarding_completion_by_country(h24, now_us, suffix_start, suffix_end)
    # Monetization funnel — today, DoD, WoW
    f = parse_funnel(q_monetization_funnel(h24, now_us, suffix_start, suffix_end))
    fd = parse_funnel(q_monetization_funnel(h48, h24, suffix_start, suffix_end))
    fw = parse_funnel(q_monetization_funnel(h192, h168, suffix_week_start, suffix_week_end))
    rc = parse_rc_events(q_rc_events(h24, now_us, suffix_start, suffix_end))

    # 7-day trial-to-paid
    t2p_raw = q_trial_to_paid_7d(now_us, suffix_week_start, suffix_end)
    t2p = t2p_raw[0] if t2p_raw else {}
    trial_7d = int(t2p.get('trial_count', 0) or 0)
    trial_to_paid_7d = int(t2p.get('trial_to_paid_count', 0) or 0)
    t2p_rate = round(trial_to_paid_7d / max(1, trial_7d) * 100, 1)

    p = q_product(h24, now_us, suffix_start, suffix_end)

    seg = {r['segment']: int(r['users']) for r in g}
    segd = {r['segment']: int(r['users']) for r in gd}
    segw = {r['segment']: int(r['users']) for r in gw}
    pu = {r['event_name']: int(r['users']) for r in p}
    pe = {r['event_name']: int(r['events']) for r in p}

    new_users = seg.get('new', 0)
    returning = seg.get('returning', 0)
    
    country_growth_breakdown = format_country_growth(countries_new)
    country_conv_breakdown = format_country_conversion(conv_by_country)
    onboarding_breakdown = format_onboarding_completion(onboarding_by_country)
    
    # Get experiment metrics
    try:
        exp_metrics = q_experiment_metrics(h24, now_us, suffix_start, suffix_end)
        exp_breakdown = format_experiments(exp_metrics)
    except Exception as e:
        exp_breakdown = f"    Error: {str(e)[:50]}"
    
    new_paid_rate = round(f['new_paid'] / max(1, f['new_users']) * 100, 1)
    ret_paid_rate = round(f['ret_paid'] / max(1, f['ret_users']) * 100, 1)
    total_pw = f['new_paywall'] + f['ret_paywall']
    total_trial = f['new_trial'] + f['ret_trial']
    total_paid = f['new_paid'] + f['ret_paid']
    pw_to_trial_rate = round(total_trial / max(1, total_pw) * 100, 1)

    # DoD / WoW for total paid
    total_paid_d = fd['new_paid'] + fd['ret_paid']
    total_paid_w = fw['new_paid'] + fw['ret_paid']

    report = f'''📊 CleanPro Daily — {display_date} (rolling 24h as of {display_time} ICT)

👥 GROWTH
  New users: {new_users} (DoD {pct(new_users, segd.get('new', 0))} · WoW {pct(new_users, segw.get('new', 0))})
  Returning: {returning}

  📍 New Users by Country (Top 10):
{country_growth_breakdown}

🚀 ONBOARDING (new→paywall→home)
  📍 Completion by Country (Top 10):
{onboarding_breakdown}

💰 MONETIZATION
  📊 Funnel:
    New users: {f['new_users']} → paywall {f['new_paywall']} → trial {f['new_trial']} → paid {f['new_paid']} ({new_paid_rate}%) {get_conversion_emoji(new_paid_rate)}
    Returning: {f['ret_users']} → paywall {f['ret_paywall']} → trial {f['ret_trial']} → paid {f['ret_paid']} ({ret_paid_rate}%) {get_conversion_emoji(ret_paid_rate)}

  Overall: {total_pw} paywall → {total_trial} trial → {total_paid} paid
  Paywall→Trial: {pw_to_trial_rate}% · Trial→Paid (7d): {trial_to_paid_7d}/{trial_7d} ({t2p_rate}%)
  Cancellations: {rc['rc_cancellation']} · Expirations: {rc['rc_expiration']} · Billing issues: {rc['rc_billing_issue']}
  DoD {pct(total_paid, total_paid_d)} · WoW {pct(total_paid, total_paid_w)}

  📍 Conversion by Country (Top 10):
{country_conv_breakdown}

🧪 EXPERIMENTS (B=Baseline | users/done%/trial%/conv%)
{exp_breakdown}

🧹 PRODUCT
  Scans: {pu.get('scan_completed',0)+pu.get('scan_v2_complete',0)} users ({pe.get('scan_completed',0)+pe.get('scan_v2_complete',0)} total scans)
  Cleans: {pu.get('clean_completed',0)} users
  First scan: {pu.get('first_scan_complete',0)} new users completed
  First delete: {pu.get('first_delete_complete',0)} new users completed'''

    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / 'latest_report.txt').write_text(report + '\n')
    REPORT_PATH.mkdir(parents=True, exist_ok=True)
    (REPORT_PATH / f'{display_date}.md').write_text(report + '\n')
    
    # Send text report
    tg = send_telegram(report)
    print(report)
    print('TELEGRAM_SENT_OK')
    print(json.dumps(tg))
    
    # Generate and send experiment heatmap
    print('\n📊 Generating experiment heatmap...')
    heatmap_path = generate_experiment_heatmap()
    if heatmap_path:
        print(f'Heatmap generated: {heatmap_path}')
        tg_photo = send_telegram_photo(heatmap_path, f"🧪 CleanPro Experiments Heatmap — {display_date}")
        print('HEATMAP_SENT_OK')
        print(json.dumps(tg_photo))
    else:
        print('⚠️ Heatmap generation skipped or failed')


if __name__ == '__main__':
    main()
