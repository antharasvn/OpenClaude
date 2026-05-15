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


def q_new_user_funnel_by_platform(start_us, end_us, suffix_start, suffix_end, now_us, suffix_end_7d):
    """Per-platform funnel for NEW users only (cohort-restricted to first_open in window).

    New users = first_open in [start_us, end_us]. Same-window paywall_viewed/trial_start.
    Converted (7d) = those new users who purchased within 7d of first_open (window goes
    forward to now_us; uses suffixes that span the lookback window).
    """
    sql = f'''
WITH all_events AS (
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end_7d}'
  UNION ALL
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end_7d}'
), new_users AS (
  SELECT
    user_pseudo_id,
    CASE
      WHEN device.category = 'tablet' AND device.operating_system = 'iOS' THEN 'iPad'
      WHEN device.category = 'mobile' AND device.operating_system = 'iOS' THEN 'iPhone'
      WHEN device.operating_system = 'Android' THEN 'Android'
      WHEN device.category = 'desktop' OR device.operating_system IN ('Windows', 'Macintosh', 'Linux') THEN 'Web'
      ELSE 'Other'
    END AS platform,
    MIN(event_timestamp) AS first_open_us
  FROM all_events
  WHERE event_name = 'first_open'
    AND event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1, 2
), new_user_events AS (
  SELECT
    nu.platform,
    nu.user_pseudo_id,
    e.event_name,
    e.event_timestamp,
    nu.first_open_us
  FROM all_events e
  JOIN new_users nu USING (user_pseudo_id)
  WHERE e.event_timestamp BETWEEN nu.first_open_us AND nu.first_open_us + 7 * 24 * 60 * 60 * 1000000
), funnel AS (
  SELECT
    platform,
    user_pseudo_id,
    MAX(IF(event_name IN ('onboarding_paywall_viewed','paywall_viewed')
           AND event_timestamp BETWEEN {start_us} AND {end_us}, 1, 0)) AS saw_paywall,
    MAX(IF(event_name = 'trial_start'
           AND event_timestamp BETWEEN {start_us} AND {end_us}, 1, 0)) AS started_trial,
    MAX(IF(event_name IN ('onboarding_purchase_completed','purchase'), 1, 0)) AS converted_7d
  FROM new_user_events
  GROUP BY 1, 2
)
SELECT
  platform,
  COUNT(*) AS new_users,
  SUM(saw_paywall) AS saw_paywall,
  SUM(started_trial) AS started_trial,
  SUM(converted_7d) AS converted_7d
FROM funnel
GROUP BY 1
'''
    return bq_query(sql)


def q_transcription_by_platform(start_us, end_us, suffix_start, suffix_end):
    """Per-platform transcription start/complete counts."""
    sql = f'''
WITH all_events AS (
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
), platform_evt AS (
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
    AND event_name IN ('transcription_start', 'transcription_complete')
)
SELECT
  platform,
  COUNT(DISTINCT IF(event_name='transcription_start', user_pseudo_id, NULL)) AS started,
  COUNT(DISTINCT IF(event_name='transcription_complete', user_pseudo_id, NULL)) AS completed
FROM platform_evt
GROUP BY platform
'''
    return bq_query(sql)


def q_web_conversions_3d(now_us, suffix_start_3d, suffix_end):
    """Web platform conversions per day for the last 3 calendar UTC days.

    Counts distinct users on platform=Web who fired a purchase event in each
    of the last 3 days (relative to now_us). Used by the alerts engine to
    detect 3+ consecutive zero days.
    """
    day_us = 24 * 60 * 60 * 1_000_000
    d0_start = now_us - day_us
    d1_start = now_us - 2 * day_us
    d2_start = now_us - 3 * day_us
    sql = f'''
WITH all_events AS (
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start_3d}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start_3d}' AND '{suffix_end}'
), web_purchase AS (
  SELECT user_pseudo_id, event_timestamp
  FROM all_events
  WHERE event_name IN ('onboarding_purchase_completed', 'purchase', 'trial_start')
    AND ((device.category = 'desktop') OR device.operating_system IN ('Windows', 'Macintosh', 'Linux'))
)
SELECT
  COUNT(DISTINCT IF(event_timestamp BETWEEN {d0_start} AND {now_us}, user_pseudo_id, NULL)) AS d0,
  COUNT(DISTINCT IF(event_timestamp BETWEEN {d1_start} AND {d0_start}, user_pseudo_id, NULL)) AS d1,
  COUNT(DISTINCT IF(event_timestamp BETWEEN {d2_start} AND {d1_start}, user_pseudo_id, NULL)) AS d2
FROM web_purchase
'''
    return bq_query(sql)


def q_platform_breakdown_by_segment(start_us, end_us, suffix_start, suffix_end):
    """Platform breakdown split by NEW vs RETURNING cohort (mutually exclusive)."""
    sql = f'''
WITH all_events AS (
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
  UNION ALL
  SELECT * FROM `{PROJECT_ID}.{DATASET}.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{suffix_start}' AND '{suffix_end}'
), in_window AS (
  SELECT
    user_pseudo_id,
    event_name,
    CASE
      WHEN device.category = 'tablet' AND device.operating_system = 'iOS' THEN 'iPad'
      WHEN device.category = 'mobile' AND device.operating_system = 'iOS' THEN 'iPhone'
      WHEN device.operating_system = 'Android' THEN 'Android'
      WHEN device.category = 'desktop' OR device.operating_system IN ('Windows', 'Macintosh', 'Linux') THEN 'Web'
      ELSE 'Other'
    END AS platform
  FROM all_events
  WHERE event_timestamp BETWEEN {start_us} AND {end_us}
), user_seg AS (
  SELECT
    user_pseudo_id,
    ANY_VALUE(platform) AS platform,
    MAX(IF(event_name='first_open', 1, 0)) AS is_new
  FROM in_window
  GROUP BY 1
)
SELECT
  IF(is_new=1,'new','returning') AS segment,
  platform,
  COUNT(*) AS users
FROM user_seg
GROUP BY 1, 2
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
    # For 7d-forward windows (e.g. trial-to-paid for new users acquired today),
    # extend the suffix window 7 days into the future so events_* tables match.
    suffix_end_7d = subprocess.run(['bash', '-lc', 'TZ="America/New_York" date -v+7d +%Y%m%d 2>/dev/null || TZ="America/New_York" date -d "7 days" +%Y%m%d'], capture_output=True, text=True).stdout.strip()
    suffix_3d_start = subprocess.run(['bash', '-lc', 'TZ="America/New_York" date -v-4d +%Y%m%d 2>/dev/null || TZ="America/New_York" date -d "4 days ago" +%Y%m%d'], capture_output=True, text=True).stdout.strip()

    # Today's data
    g = q_growth(h24, now_us, suffix_start, suffix_end)
    gd = q_growth(h48, h24, suffix_start, suffix_end)
    gw = q_growth(h192, h168, suffix_week_start, suffix_week_end)
    countries = q_countries(h24, now_us, suffix_start, suffix_end)
    countries_new = q_countries_new_users(h24, now_us, suffix_start, suffix_end)
    conv_by_country = q_conversion_by_country(h24, now_us, suffix_start, suffix_end)
    conv_by_platform = q_conversion_by_platform(h24, now_us, suffix_start, suffix_end)
    platforms = q_platform_breakdown(h24, now_us, suffix_start, suffix_end)
    platforms_by_seg = q_platform_breakdown_by_segment(h24, now_us, suffix_start, suffix_end)
    new_funnel_by_platform = q_new_user_funnel_by_platform(
        h24, now_us, suffix_start, suffix_end, now_us, suffix_end_7d
    )
    trans_by_platform = q_transcription_by_platform(h24, now_us, suffix_start, suffix_end)
    web_3d = q_web_conversions_3d(now_us, suffix_3d_start, suffix_end)
    
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
    
    # Parse platform breakdown by segment (NEW vs RETURNING — mutually exclusive)
    plat_order = ['iPhone', 'iPad', 'Android', 'Web']
    new_plat = {p: 0 for p in plat_order}
    ret_plat = {p: 0 for p in plat_order}
    for r in platforms_by_seg:
        seg = r.get('segment', '')
        plat = r.get('platform', 'Other')
        if plat not in new_plat:
            continue
        n = int(r.get('users', 0) or 0)
        if seg == 'new':
            new_plat[plat] += n
        elif seg == 'returning':
            ret_plat[plat] += n
    new_platform_line = f"iPhone {new_plat['iPhone']} · iPad {new_plat['iPad']} · Android {new_plat['Android']} · Web {new_plat['Web']}"
    ret_platform_line = f"iPhone {ret_plat['iPhone']} · iPad {ret_plat['iPad']} · Android {ret_plat['Android']} · Web {ret_plat['Web']}"

    # Parse new-user funnel by platform
    nf = {p: {'new_users': 0, 'saw_paywall': 0, 'started_trial': 0, 'converted_7d': 0} for p in plat_order}
    for r in new_funnel_by_platform:
        p = r.get('platform', 'Other')
        if p not in nf:
            continue
        nf[p]['new_users'] = int(r.get('new_users', 0) or 0)
        nf[p]['saw_paywall'] = int(r.get('saw_paywall', 0) or 0)
        nf[p]['started_trial'] = int(r.get('started_trial', 0) or 0)
        nf[p]['converted_7d'] = int(r.get('converted_7d', 0) or 0)

    # Parse transcription (overall)
    trans_data = trans[0] if trans else {}
    trans_started = int(trans_data.get('started', 0) or 0)
    trans_completed = int(trans_data.get('completed', 0) or 0)
    trans_success = round((trans_completed / trans_started * 100), 1) if trans_started else 0.0

    # Parse transcription per platform
    trans_plat = {p: {'started': 0, 'completed': 0} for p in plat_order}
    for r in trans_by_platform:
        p = r.get('platform', 'Other')
        if p not in trans_plat:
            continue
        trans_plat[p]['started'] = int(r.get('started', 0) or 0)
        trans_plat[p]['completed'] = int(r.get('completed', 0) or 0)
    trans_plat_rate = {}
    for p in plat_order:
        s = trans_plat[p]['started']
        c = trans_plat[p]['completed']
        trans_plat_rate[p] = round((c / s * 100), 1) if s else None  # None = no data, omit

    # Web conversions for last 3 days
    web_row = web_3d[0] if web_3d else {}
    web_d0 = int(web_row.get('d0', 0) or 0)
    web_d1 = int(web_row.get('d1', 0) or 0)
    web_d2 = int(web_row.get('d2', 0) or 0)
    
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

    # ---- Per-platform NEW user funnel table (fixed-width columns) ----
    def col(v):
        return f"{v:>7}"

    funnel_table = (
        f"                    iPhone    iPad   Android    Web\n"
        f"  New users     :  {col(nf['iPhone']['new_users'])} {col(nf['iPad']['new_users'])} {col(nf['Android']['new_users'])} {col(nf['Web']['new_users'])}\n"
        f"  Saw paywall   :  {col(nf['iPhone']['saw_paywall'])} {col(nf['iPad']['saw_paywall'])} {col(nf['Android']['saw_paywall'])} {col(nf['Web']['saw_paywall'])}\n"
        f"  Started trial :  {col(nf['iPhone']['started_trial'])} {col(nf['iPad']['started_trial'])} {col(nf['Android']['started_trial'])} {col(nf['Web']['started_trial'])}\n"
        f"  Converted (7d):  {col(nf['iPhone']['converted_7d'])} {col(nf['iPad']['converted_7d'])} {col(nf['Android']['converted_7d'])} {col(nf['Web']['converted_7d'])}"
    )

    # Per-platform funnel rates (skip platforms with no signal)
    def rate_str(num, den):
        if den <= 0:
            return None
        return round(num / den * 100, 0)

    pv_rates = {p: rate_str(nf[p]['saw_paywall'], nf[p]['new_users']) for p in plat_order}
    pt_rates = {p: rate_str(nf[p]['started_trial'], nf[p]['saw_paywall']) for p in plat_order}
    tp_rates = {p: rate_str(nf[p]['converted_7d'], nf[p]['started_trial']) for p in plat_order}

    def fmt_rates(rates_dict):
        parts = []
        for p in plat_order:
            v = rates_dict[p]
            if v is None:
                continue
            parts.append(f"{p} {int(v)}%")
        return ' · '.join(parts) if parts else '(no data)'

    pv_line = fmt_rates(pv_rates)
    pt_line = fmt_rates(pt_rates)
    tp_line = fmt_rates(tp_rates)

    # ---- Per-platform transcription line ----
    trans_parts = []
    for p in plat_order:
        r = trans_plat_rate[p]
        if r is None:
            continue
        # Per-platform color: <70 red, <82 amber, else default
        if r < 70:
            badge = ' 🔴'
        elif r < 82:
            badge = ' ⚠️'
        else:
            badge = ''
        trans_parts.append(f"{p}: {int(round(r))}%{badge}")
    trans_per_plat_line = ' · '.join(trans_parts) if trans_parts else '(no data)'

    # ---- Alerts engine ----
    alerts = []
    # 1) Paywall view rate <30% on a platform when others >50%
    pv_high = [p for p in plat_order if pv_rates[p] is not None and pv_rates[p] > 50]
    pv_low = [p for p in plat_order if pv_rates[p] is not None and pv_rates[p] < 30]
    if pv_low and pv_high:
        for p in pv_low:
            alerts.append(f"{p} paywall view rate {int(pv_rates[p])}% (others >50%) — paywall trigger may be broken")
    # 2) Trial→Paid <10% on a platform when others >25%
    tp_high = [p for p in plat_order if tp_rates[p] is not None and tp_rates[p] > 25]
    tp_low = [p for p in plat_order if tp_rates[p] is not None and tp_rates[p] < 10]
    if tp_low and tp_high:
        for p in tp_low:
            alerts.append(f"{p} trial→paid {int(tp_rates[p])}% (others >25%) — conversion is broken")
    # 3) Transcription success on any platform <70%
    for p in plat_order:
        r = trans_plat_rate[p]
        if r is not None and r < 70:
            alerts.append(f"{p} transcription {int(round(r))}% — degraded (overall {trans_success}%)")
    # 4) Web 0 conversions for 3+ consecutive days
    if web_d0 == 0 and web_d1 == 0 and web_d2 == 0:
        alerts.append("Web 0 conversions for 3 consecutive days — Web monetization stalled")

    if alerts:
        alerts_block = '\n🚨 ALERTS\n' + '\n'.join(f"  - {a}" for a in alerts)
    else:
        alerts_block = ''

    report = f'''📊 VidNotes Daily — {display_date} (rolling 24h as of {display_time} ET)

👥 GROWTH
  New users: {new_users} (DoD {pct(new_users, segd.get('new', 0))} · WoW {pct(new_users, segw.get('new', 0))})
  Returning: {returning}

  📱 Platform (NEW): {new_platform_line}
  📱 Platform (RET): {ret_platform_line}

  📍 New Users by Country (Top 10):
{country_growth_breakdown}

📊 NEW USER FUNNEL BY PLATFORM
{funnel_table}

  Paywall view rate : {pv_line}
  Paywall→Trial     : {pt_line}
  Trial→Paid (7d)   : {tp_line}

💰 MONETIZATION
  📊 Funnel:
    New users: {f['new_users']} → paywall {f['new_paywall']} → trial {f['new_trial']} → paid {f['new_paid']} ({new_rate}%) {get_conversion_emoji(new_rate)}
    Returning: {f['ret_users']} → paywall {f['ret_paywall']} → trial {f['ret_trial']} → paid {f['ret_paid']} ({ret_rate}%) {get_conversion_emoji(ret_rate)}

  Overall: {total_pw} paywall → {total_trial} trial → {total_paid} paid
  Paywall→Trial: {trial_rate}% · Trial→Paid (7d): {trial_to_paid_7d}/{trial_7d} ({t2p_rate}%)
  Skipped: {total_skipped} · Failed: {total_failed} · Cancelled: {total_cancelled}
  DoD {dod_paid} · WoW {wow_paid}

  📍 Conversion by Country (Top 10):
{country_conv_breakdown}

🎙 PRODUCT
  Transcription success:
    {trans_per_plat_line}
  Overall: {trans_success}% {trans_emoji}
  AI summaries: {ai_summaries} · Exports: {exports} · Flashcards: {flashcards}{alerts_block}'''

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
