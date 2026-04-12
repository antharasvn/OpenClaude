#!/usr/bin/env python3
"""VidNotes Daily Report Runner - Direct Telegram delivery."""
import json, subprocess, pathlib, urllib.request
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# AAA OS bot (same as CleanPro)
AAA_BOT_TOKEN = '8628864855:AAFWSgQCzUIGNtBK1dQk28rCJ7rqBo3v0zU'
AAA_CHAT_ID = '-5201056067'

# Silpho OS bot
SILPHO_BOT_TOKEN = '8733346629:AAGixlBDK2fg6Xyjx5iLQDjsBGOhKz3xF4Q'
SILPHO_CHAT_ID = '-5088617466'

BASE = PROJECT_ROOT / 'data' / 'vidnotes'
REPORT_PATH = PROJECT_ROOT / 'reports' / 'vidnotes' / 'daily'
PROJECT_ID = 'vidnotes-7864d'
DATASET = 'analytics_508326759'


def run(cmd, input_text=None):
    return subprocess.run(cmd, input=input_text, text=True, capture_output=True, check=False)


def bq_query(sql: str):
    cp = run(['bq', 'query', '--use_legacy_sql=false', f'--project_id={PROJECT_ID}', '--format=json'], input_text=sql)
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr or cp.stdout)
    return json.loads(cp.stdout or '[]')


def send_telegram(text: str, bot_token: str, chat_id: str):
    payload = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": ""}).encode('utf-8')
    req = urllib.request.Request(
        f'https://api.telegram.org/bot{bot_token}/sendMessage',
        data=payload,
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def pct(cur, base):
    if not base:
        return 'N/A'
    return f'{((cur - base) / base) * 100:+.0f}%'


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
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
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
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
)
SELECT geo.country, COUNT(DISTINCT user_pseudo_id) AS users
FROM all_events WHERE event_timestamp BETWEEN {start_us} AND {end_us}
GROUP BY 1 ORDER BY users DESC LIMIT 5
'''
    return bq_query(sql)


def q_platform_breakdown(start_us, end_us, suffix_start, suffix_end):
    """Get user breakdown by platform (iPhone, iPad, Android, Web)."""
    sql = f'''
WITH all_events AS (
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
)
SELECT 
  CASE 
    WHEN device.category = 'tablet' AND device.operating_system = 'iOS' THEN 'iPad'
    WHEN device.category = 'mobile' AND device.operating_system = 'iOS' THEN 'iPhone'
    WHEN device.operating_system = 'Android' THEN 'Android'
    WHEN device.category = 'desktop' OR device.operating_system IN ('Windows', 'Macintosh', 'Linux') THEN 'Web'
    ELSE 'Other'
  END AS platform,
  COUNT(DISTINCT user_pseudo_id) AS users
FROM all_events 
WHERE event_timestamp BETWEEN {start_us} AND {end_us}
GROUP BY 1
ORDER BY users DESC
'''
    return bq_query(sql)


def q_countries_new_users(start_us, end_us, suffix_start, suffix_end):
    sql = f'''
WITH all_events AS (
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
)
SELECT geo.country, COUNT(DISTINCT user_pseudo_id) AS new_users
FROM all_events 
WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  AND event_name = 'first_open'
GROUP BY 1 ORDER BY new_users DESC LIMIT 10
'''
    return bq_query(sql)


def q_conversion_by_country(start_us, end_us, suffix_start, suffix_end):
    sql = f'''
WITH all_events AS (
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
), country_events AS (
  SELECT
    geo.country,
    user_pseudo_id,
    event_name
  FROM all_events
  WHERE event_timestamp BETWEEN {start_us} AND {end_us}
    AND event_name IN ('onboarding_paywall_viewed', 'paywall_viewed', 'onboarding_purchase_completed', 'purchase', 'trial_start')
), country_metrics AS (
  SELECT
    country,
    COUNT(DISTINCT CASE WHEN event_name IN ('onboarding_paywall_viewed', 'paywall_viewed') THEN user_pseudo_id END) AS paywall_shown,
    COUNT(DISTINCT CASE WHEN event_name IN ('onboarding_purchase_completed', 'purchase', 'trial_start') THEN user_pseudo_id END) AS converted
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


def q_conversion_by_platform(start_us, end_us, suffix_start, suffix_end):
    """Get paywall shown and conversion by platform (iPhone, iPad, Android, Web)."""
    sql = f'''
WITH all_events AS (
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
), platform_events AS (
  SELECT
    CASE
      WHEN device.category = 'tablet' AND device.operating_system = 'iOS' THEN 'iPad'
      WHEN device.category = 'mobile' AND device.operating_system = 'iOS' THEN 'iPhone'
      WHEN device.operating_system = 'Android' THEN 'Android'
      WHEN device.category = 'desktop' OR device.operating_system IN ('Windows', 'Macintosh', 'Linux') THEN 'Web'
      ELSE 'Other'
    END AS platform,
    user_pseudo_id,
    event_name
  FROM all_events
  WHERE event_timestamp BETWEEN {start_us} AND {end_us}
    AND event_name IN ('onboarding_paywall_viewed', 'paywall_viewed', 'onboarding_purchase_completed', 'purchase', 'trial_start')
), platform_metrics AS (
  SELECT
    platform,
    COUNT(DISTINCT CASE WHEN event_name IN ('onboarding_paywall_viewed', 'paywall_viewed') THEN user_pseudo_id END) AS paywall_shown,
    COUNT(DISTINCT CASE WHEN event_name IN ('onboarding_purchase_completed', 'purchase', 'trial_start') THEN user_pseudo_id END) AS converted
  FROM platform_events
  GROUP BY platform
)
SELECT
  platform,
  paywall_shown,
  converted,
  ROUND(SAFE_DIVIDE(converted, paywall_shown) * 100, 1) AS conversion_rate
FROM platform_metrics
WHERE paywall_shown > 0
ORDER BY paywall_shown DESC
'''
    return bq_query(sql)


def q_monetization_funnel(start_us, end_us, suffix_start, suffix_end):
    """Monetization funnel: new vs returning users who hit paywall/trial/purchase events."""
    sql = f'''
WITH all_events AS (
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
), user_seg AS (
  SELECT user_pseudo_id, MAX(IF(event_name="first_open",1,0)) AS is_new
  FROM all_events WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1
), funnel AS (
  SELECT
    us.is_new,
    e.user_pseudo_id,
    MAX(IF(e.event_name IN ('onboarding_paywall_viewed', 'paywall_viewed'), 1, 0)) AS saw_paywall,
    MAX(IF(e.event_name = 'trial_start', 1, 0)) AS started_trial,
    MAX(IF(e.event_name IN ('onboarding_purchase_completed', 'purchase'), 1, 0)) AS purchased,
    MAX(IF(e.event_name = 'purchase_cancelled', 1, 0)) AS cancelled,
    MAX(IF(e.event_name = 'onboarding_purchase_failed', 1, 0)) AS failed,
    MAX(IF(e.event_name = 'onboarding_paywall_skipped', 1, 0)) AS skipped
  FROM all_events e
  JOIN user_seg us ON e.user_pseudo_id = us.user_pseudo_id
  WHERE e.event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1, 2
)
SELECT
  IF(is_new=1,"new","returning") AS segment,
  COUNT(*) AS total_users,
  SUM(saw_paywall) AS paywall_users,
  SUM(started_trial) AS trial_users,
  SUM(purchased) AS paid_users,
  SUM(cancelled) AS cancelled_users,
  SUM(failed) AS failed_users,
  SUM(skipped) AS skipped_users
FROM funnel
GROUP BY 1
'''
    return bq_query(sql)


def q_trial_to_paid_7d(now_us, suffix_start_7d, suffix_end):
    """Rolling 7-day trial-to-paid: users who started trial AND purchased within the window."""
    start_7d = now_us - 604800 * 1_000_000
    sql = f'''
WITH all_events AS (
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start_7d}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start_7d}' AND '{suffix_end}'
), trial_users AS (
  SELECT DISTINCT user_pseudo_id
  FROM all_events
  WHERE event_timestamp BETWEEN {start_7d} AND {now_us}
    AND event_name = 'trial_start'
), paid_users AS (
  SELECT DISTINCT user_pseudo_id
  FROM all_events
  WHERE event_timestamp BETWEEN {start_7d} AND {now_us}
    AND event_name IN ('onboarding_purchase_completed', 'purchase')
)
SELECT
  (SELECT COUNT(*) FROM trial_users) AS trial_count,
  (SELECT COUNT(*) FROM trial_users t JOIN paid_users p ON t.user_pseudo_id = p.user_pseudo_id) AS trial_to_paid_count
'''
    return bq_query(sql)


def q_transcription(start_us, end_us, suffix_start, suffix_end):
    sql = f'''
WITH all_events AS (
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
)
SELECT
  COUNT(DISTINCT IF(event_name="transcription_start", user_pseudo_id, NULL)) AS started,
  COUNT(DISTINCT IF(event_name="transcription_complete", user_pseudo_id, NULL)) AS completed
FROM all_events
WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  AND event_name IN ("transcription_start", "transcription_complete")
'''
    return bq_query(sql)


def q_ai_features(start_us, end_us, suffix_start, suffix_end):
    sql = f'''
WITH all_events AS (
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
)
SELECT event_name, COUNT(DISTINCT user_pseudo_id) AS users, COUNT(*) AS events
FROM all_events
WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  AND event_name IN ("ai_summary_generated","flashcard_created","content_export","export_initiated")
GROUP BY 1 ORDER BY users DESC
'''
    return bq_query(sql)


def parse_funnel(data):
    """Parse monetization funnel query results into a dict."""
    result = {'new_users': 0, 'new_paywall': 0, 'new_trial': 0, 'new_paid': 0,
              'new_cancelled': 0, 'new_failed': 0, 'new_skipped': 0,
              'ret_users': 0, 'ret_paywall': 0, 'ret_trial': 0, 'ret_paid': 0,
              'ret_cancelled': 0, 'ret_failed': 0, 'ret_skipped': 0}
    for r in data:
        seg = r.get('segment', '')
        if seg == 'new':
            result['new_users'] = int(r.get('total_users', 0) or 0)
            result['new_paywall'] = int(r.get('paywall_users', 0) or 0)
            result['new_trial'] = int(r.get('trial_users', 0) or 0)
            result['new_paid'] = int(r.get('paid_users', 0) or 0)
            result['new_cancelled'] = int(r.get('cancelled_users', 0) or 0)
            result['new_failed'] = int(r.get('failed_users', 0) or 0)
            result['new_skipped'] = int(r.get('skipped_users', 0) or 0)
        elif seg == 'returning':
            result['ret_users'] = int(r.get('total_users', 0) or 0)
            result['ret_paywall'] = int(r.get('paywall_users', 0) or 0)
            result['ret_trial'] = int(r.get('trial_users', 0) or 0)
            result['ret_paid'] = int(r.get('paid_users', 0) or 0)
            result['ret_cancelled'] = int(r.get('cancelled_users', 0) or 0)
            result['ret_failed'] = int(r.get('failed_users', 0) or 0)
            result['ret_skipped'] = int(r.get('skipped_users', 0) or 0)
    return result


def format_country_growth(countries_new):
    lines = []
    for r in countries_new[:10]:
        country = r.get('country', '?')
        users = int(r.get('new_users', 0))
        lines.append(f"    {country}: {users}")
    return '\n'.join(lines) if lines else "    (no data)"


def format_country_conversion(conv_by_country):
    if not conv_by_country:
        return "    (no data)"
    
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


def main():
    # Time windows (ET timezone for VidNotes)
    now_epoch = int(subprocess.run(['bash', '-lc', 'TZ="America/New_York" date +%s'], capture_output=True, text=True).stdout.strip())
    now_us = now_epoch * 1_000_000
    h24 = (now_epoch - 86400) * 1_000_000
    h48 = (now_epoch - 172800) * 1_000_000
    h168 = (now_epoch - 604800) * 1_000_000
    h192 = (now_epoch - 691200) * 1_000_000
    
    display_date = subprocess.run(['bash', '-lc', 'TZ="America/New_York" date +%Y-%m-%d'], capture_output=True, text=True).stdout.strip()
    display_time = subprocess.run(['bash', '-lc', 'TZ="America/New_York" date +%H:%M'], capture_output=True, text=True).stdout.strip()
    
    suffix_start = subprocess.run(['bash', '-lc', 'TZ="America/New_York" date -v-2d +%Y%m%d 2>/dev/null || TZ="America/New_York" date -d "2 days ago" +%Y%m%d'], capture_output=True, text=True).stdout.strip()
    suffix_end = subprocess.run(['bash', '-lc', 'TZ="America/New_York" date +%Y%m%d'], capture_output=True, text=True).stdout.strip()
    suffix_week_start = subprocess.run(['bash', '-lc', 'TZ="America/New_York" date -v-9d +%Y%m%d 2>/dev/null || TZ="America/New_York" date -d "9 days ago" +%Y%m%d'], capture_output=True, text=True).stdout.strip()
    suffix_week_end = subprocess.run(['bash', '-lc', 'TZ="America/New_York" date -v-6d +%Y%m%d 2>/dev/null || TZ="America/New_York" date -d "6 days ago" +%Y%m%d'], capture_output=True, text=True).stdout.strip()

    # Today's data
    g = q_growth(h24, now_us, suffix_start, suffix_end)
    gd = q_growth(h48, h24, suffix_start, suffix_end)
    gw = q_growth(h192, h168, suffix_week_start, suffix_week_end)
    countries = q_countries(h24, now_us, suffix_start, suffix_end)
    countries_new = q_countries_new_users(h24, now_us, suffix_start, suffix_end)
    conv_by_country = q_conversion_by_country(h24, now_us, suffix_start, suffix_end)
    conv_by_platform = q_conversion_by_platform(h24, now_us, suffix_start, suffix_end)
    platforms = q_platform_breakdown(h24, now_us, suffix_start, suffix_end)
    
    # Monetization funnel: today, yesterday, last week
    f = parse_funnel(q_monetization_funnel(h24, now_us, suffix_start, suffix_end))
    f_d = parse_funnel(q_monetization_funnel(h48, h24, suffix_start, suffix_end))
    f_w = parse_funnel(q_monetization_funnel(h192, h168, suffix_week_start, suffix_week_end))

    # 7-day trial-to-paid
    t2p_raw = q_trial_to_paid_7d(now_us, suffix_week_start, suffix_end)
    t2p = t2p_raw[0] if t2p_raw else {}
    trial_7d = int(t2p.get('trial_count', 0) or 0)
    trial_to_paid_7d = int(t2p.get('trial_to_paid_count', 0) or 0)
    t2p_rate = round(trial_to_paid_7d / max(1, trial_7d) * 100, 1)
    
    trans = q_transcription(h24, now_us, suffix_start, suffix_end)
    ai = q_ai_features(h24, now_us, suffix_start, suffix_end)

    # Parse growth
    seg = {r['segment']: int(r['users']) for r in g}
    segd = {r['segment']: int(r['users']) for r in gd}
    segw = {r['segment']: int(r['users']) for r in gw}
    
    new_users = seg.get('new', 0)
    returning = seg.get('returning', 0)
    
    # Parse platform breakdown
    platform_dict = {r.get('platform', 'Other'): int(r.get('users', 0) or 0) for r in platforms}
    iphone = platform_dict.get('iPhone', 0)
    ipad = platform_dict.get('iPad', 0)
    android = platform_dict.get('Android', 0)
    web = platform_dict.get('Web', 0)
    total_platform = iphone + ipad + android + web
    platform_line = f"iPhone {iphone} · iPad {ipad} · Android {android} · Web {web}"
    
    # Parse transcription
    trans_data = trans[0] if trans else {}
    trans_started = int(trans_data.get('started', 0) or 0)
    trans_completed = int(trans_data.get('completed', 0) or 0)
    trans_success = round((trans_completed / trans_started * 100), 1) if trans_started else 0.0
    
    # Parse AI features
    ai_dict = {r.get('event_name'): int(r.get('users', 0) or 0) for r in ai}
    ai_summaries = ai_dict.get('ai_summary_generated', 0)
    exports = ai_dict.get('content_export', 0) + ai_dict.get('export_initiated', 0)
    flashcards = ai_dict.get('flashcard_created', 0)
    
    # Format country breakdowns
    country_growth_breakdown = format_country_growth(countries_new)
    country_conv_breakdown = format_country_conversion(conv_by_country)
    
    # Format platform conversion breakdown
    platform_conv_lines = []
    for r in conv_by_platform:
        plat = r.get('platform', '?')
        shown = int(r.get('paywall_shown', 0) or 0)
        converted = int(r.get('converted', 0) or 0)
        rate = float(r.get('conversion_rate', 0) or 0)
        emoji = get_conversion_emoji(rate)
        platform_conv_lines.append(f"    {plat}: {shown}→{converted} ({rate}%) {emoji}")
    platform_conv_breakdown = '\n'.join(platform_conv_lines) if platform_conv_lines else "    (no data)"
    
    # Funnel derived metrics — today
    total_pw = f['new_paywall'] + f['ret_paywall']
    total_trial = f['new_trial'] + f['ret_trial']
    total_paid = f['new_paid'] + f['ret_paid']
    total_cancelled = f['new_cancelled'] + f['ret_cancelled']
    total_failed = f['new_failed'] + f['ret_failed']
    total_skipped = f['new_skipped'] + f['ret_skipped']

    new_rate = round(f['new_paid'] / max(1, f['new_users']) * 100, 1)
    ret_rate = round(f['ret_paid'] / max(1, f['ret_users']) * 100, 1)
    trial_rate = round(total_trial / max(1, total_pw) * 100, 1)
    pw_to_paid_rate = round(total_paid / max(1, total_pw) * 100, 1)

    # Funnel DoD/WoW — compare total paid users
    total_paid_d = f_d['new_paid'] + f_d['ret_paid']
    total_paid_w = f_w['new_paid'] + f_w['ret_paid']
    dod_paid = pct(total_paid, total_paid_d)
    wow_paid = pct(total_paid, total_paid_w)

    trans_emoji = '✅' if trans_success >= 82.0 else '🔴'

    report = f'''📊 VidNotes Daily — {display_date} (rolling 24h as of {display_time} ET)

👥 GROWTH
  New users: {new_users} (DoD {pct(new_users, segd.get('new', 0))} · WoW {pct(new_users, segw.get('new', 0))})
  Returning: {returning}

  📱 Platform: {platform_line}

  📍 New Users by Country (Top 10):
{country_growth_breakdown}

💰 MONETIZATION
  📊 Funnel:
    New users: {f['new_users']} → paywall {f['new_paywall']} → trial {f['new_trial']} → paid {f['new_paid']} ({new_rate}%) {get_conversion_emoji(new_rate)}
    Returning: {f['ret_users']} → paywall {f['ret_paywall']} → trial {f['ret_trial']} → paid {f['ret_paid']} ({ret_rate}%) {get_conversion_emoji(ret_rate)}

  Overall: {total_pw} paywall → {total_trial} trial → {total_paid} paid
  Paywall→Trial: {trial_rate}% · Trial→Paid (7d): {trial_to_paid_7d}/{trial_7d} ({t2p_rate}%)
  Skipped: {total_skipped} · Failed: {total_failed} · Cancelled: {total_cancelled}
  DoD {dod_paid} · WoW {wow_paid}

  📱 Conversion by Platform:
{platform_conv_breakdown}

  📍 Conversion by Country (Top 10):
{country_conv_breakdown}

🎙 PRODUCT
  Transcription success: {trans_success}% {trans_emoji}
  AI summaries: {ai_summaries} users · Exports: {exports} · Flashcards: {flashcards}'''

    # Save report locally
    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / 'latest_report.txt').write_text(report + '\n')
    
    # Archive to repo
    REPORT_PATH.mkdir(parents=True, exist_ok=True)
    (REPORT_PATH / f'{display_date}.md').write_text(report + '\n')
    
    # Send to both Telegram groups
    print(report)
    
    # Silpho OS (VidNotes partnership group)
    try:
        tg1 = send_telegram(report, SILPHO_BOT_TOKEN, SILPHO_CHAT_ID)
        print('SILPHO_TELEGRAM_SENT_OK')
    except Exception as e:
        print(f'SILPHO_TELEGRAM_ERROR: {e}')
    
    # AAA OS (main group)
    try:
        tg2 = send_telegram(report, AAA_BOT_TOKEN, AAA_CHAT_ID)
        print('AAA_TELEGRAM_SENT_OK')
    except Exception as e:
        print(f'AAA_TELEGRAM_ERROR: {e}')


if __name__ == '__main__':
    main()
