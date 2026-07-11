#!/usr/bin/env python3
"""
PDFAI Scanner Daily Report Runner
=================================
Scan funnel, value realization, monetization, features, cloud, reviews.
Rolling 24h. Deterministic Python (replaces prompt skill).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from daily_report_common import (  # noqa: E402
    PROJECT_ROOT,
    bq_query,
    events_cte,
    format_country_lines,
    format_source_split,
    get_conversion_emoji,
    pct,
    rolling_windows,
    safe_rate,
    save_report,
    send_telegram,
    traffic_bucket_sql,
)

PROJECT_ID = "pdfai-scanner"
DATASET_ID = "analytics_502367642"
BASE = PROJECT_ROOT / "data" / "pdfai"
REPORT_PATH = PROJECT_ROOT / "reports" / "pdfai" / "daily"
TZ = "America/New_York"


def q(sql: str):
    return bq_query(PROJECT_ID, sql)


def cte(ss, se):
    return events_cte(PROJECT_ID, DATASET_ID, ss, se)


def q_metrics(start_us, end_us, ss, se):
    sql = f"""
WITH {cte(ss, se)}
SELECT
  COUNT(DISTINCT user_pseudo_id) AS dau,
  COUNT(DISTINCT IF(event_name='first_open', user_pseudo_id, NULL)) AS new_users,
  COUNTIF(event_name='session_start') AS sessions,
  COUNTIF(event_name='onboarding_progress') AS onboarding_progress,
  COUNTIF(event_name='onboarding_completed') AS onboarding_completed,
  COUNTIF(event_name='onboarding_start_creating_pdf_tapped') AS onboarding_start_tapped,
  COUNTIF(event_name='scan_started') AS scan_started,
  COUNTIF(event_name='scan_completed') AS scan_completed,
  COUNTIF(event_name='export_success') AS export_success,
  COUNTIF(event_name='export_failure') AS export_failure,
  COUNTIF(event_name='value_realization_scan_completed') AS value_realized,
  COUNTIF(event_name='activation_milestone') AS activation_milestones,
  COUNTIF(event_name='activation_first_export_complete') AS first_export_complete,
  COUNTIF(event_name='paywall_shown') AS paywall_views,
  COUNTIF(event_name='paywall_dismissed') AS paywall_dismissed,
  COUNTIF(event_name='purchase_attempt') AS purchase_attempts,
  COUNTIF(event_name IN ('in_app_purchase','purchase_success','purchase')) AS purchases,
  COUNTIF(event_name='purchase_failed') AS purchase_failed,
  COUNTIF(event_name='feature_used') AS features_used,
  COUNTIF(event_name='audio_export_initiated') AS audio_exports,
  COUNTIF(event_name='reading_position_saved') AS reading_positions_saved,
  COUNTIF(REGEXP_CONTAINS(event_name, r'quiz')) AS quiz_events,
  COUNTIF(REGEXP_CONTAINS(event_name, r'flash')) AS flashcard_events,
  COUNTIF(REGEXP_CONTAINS(event_name, r'tts') OR event_name='quickread_text_file_tts_opened') AS tts_events,
  COUNTIF(event_name='anonymous_auth_success') AS auth_success,
  COUNTIF(REGEXP_CONTAINS(event_name, r'cloud|icloud')) AS cloud_events,
  COUNTIF(event_name='smart_naming_cloud_ai_failure') AS ai_naming_failures,
  COUNTIF(event_name='review_modal_shown') AS review_modal_shown,
  COUNTIF(event_name='review_modal_completed') AS review_modal_completed,
  COUNTIF(event_name='review_open_write_review_page') AS review_write_page,
  COUNTIF(event_name='savetopdfai_ext_share_extension_opened') AS share_extension_opened,
  COUNTIF(event_name='deep_link_scan_opened') AS deep_link_opens
FROM all_events
WHERE event_timestamp BETWEEN {start_us} AND {end_us}
"""
    return q(sql)


def q_source(start_us, end_us, ss, se):
    bucket = traffic_bucket_sql("e")
    sql = f"""
WITH {cte(ss, se)}
SELECT {bucket} AS source, COUNT(DISTINCT e.user_pseudo_id) AS new_users
FROM all_events e
WHERE e.event_timestamp BETWEEN {start_us} AND {end_us} AND e.event_name='first_open'
GROUP BY 1
"""
    return q(sql)


def q_countries(start_us, end_us, ss, se):
    sql = f"""
WITH {cte(ss, se)}
SELECT geo.country, COUNT(DISTINCT user_pseudo_id) AS new_users
FROM all_events
WHERE event_timestamp BETWEEN {start_us} AND {end_us} AND event_name='first_open'
GROUP BY 1 ORDER BY new_users DESC LIMIT 10
"""
    return q(sql)


def row(data):
    return data[0] if data else {}


def i(d, k):
    return int(d.get(k, 0) or 0)


def main():
    w = rolling_windows(TZ)
    now_us, h24, h48 = w["now_us"], w["h24_us"], w["h48_us"]
    h168, h192 = w["h168_us"], w["h192_us"]
    ss, se = w["suffix_start"], w["suffix_end"]
    sws, swe = w["suffix_week_start"], w["suffix_week_end"]
    display_date, display_time, tz_label = w["display_date"], w["display_time"], w["tz_label"]
    print(f"=== PDFAI Daily Report — {display_date} ===\n")

    t = row(q_metrics(h24, now_us, ss, se))
    y = row(q_metrics(h48, h24, ss, se))
    lw = row(q_metrics(h192, h168, sws, swe))
    sources = q_source(h24, now_us, ss, se)
    countries = q_countries(h24, now_us, ss, se)

    dau, new_u, sessions = i(t, "dau"), i(t, "new_users"), i(t, "sessions")
    scan_c = safe_rate(i(t, "scan_completed"), i(t, "scan_started"))
    export_ok = i(t, "export_success")
    export_fail = i(t, "export_failure")
    export_rate = safe_rate(export_ok, export_ok + export_fail)
    conv = safe_rate(i(t, "purchases"), i(t, "paywall_views"))
    onb = safe_rate(i(t, "onboarding_completed"), i(t, "onboarding_progress"))
    value_rate = safe_rate(i(t, "value_realized"), new_u)

    report = f'''📄 PDFAI Scanner — Daily Report
📅 {display_date} (as of {display_time} {tz_label})

📊 OVERVIEW
• DAU: {dau} (DoD {pct(dau, i(y,'dau'))} · WoW {pct(dau, i(lw,'dau'))})
• New Users: {new_u} (DoD {pct(new_u, i(y,'new_users'))} · WoW {pct(new_u, i(lw,'new_users'))})
• Sessions: {sessions}
• Source: {format_source_split(sources)}

📍 New Users by Country (Top 10):
{format_country_lines(countries)}

📷 SCAN FUNNEL
• Started: {i(t,'scan_started')} → Completed: {i(t,'scan_completed')} ({scan_c}%)
• Exports: {export_ok} ({export_rate}% success) · Failures: {export_fail}
• Value Realized: {i(t,'value_realized')} ({value_rate}% of new users)
• First export complete: {i(t,'first_export_complete')}

💰 MONETIZATION
• Paywall Views: {i(t,'paywall_views')} → Dismissed: {i(t,'paywall_dismissed')}
• Purchase Attempts: {i(t,'purchase_attempts')} → Purchases: {i(t,'purchases')} ({conv}%) {get_conversion_emoji(conv)}
• Purchase Failures: {i(t,'purchase_failed')}
• Paid DoD {pct(i(t,'purchases'), i(y,'purchases'))} · WoW {pct(i(t,'purchases'), i(lw,'purchases'))}

🎓 ONBOARDING
• Progress: {i(t,'onboarding_progress')} → Completed: {i(t,'onboarding_completed')} ({onb}%)
• Start Creating Tapped: {i(t,'onboarding_start_tapped')}

🔧 FEATURES
• Features Used: {i(t,'features_used')}
• Audio Exports: {i(t,'audio_exports')} · TTS: {i(t,'tts_events')}
• Quiz/Flashcard: {i(t,'quiz_events')}/{i(t,'flashcard_events')}
• Reading Positions Saved: {i(t,'reading_positions_saved')}

☁️ CLOUD & AUTH
• Auth Success: {i(t,'auth_success')} · Cloud Events: {i(t,'cloud_events')}

⚠️ ERRORS
• AI Naming Failures: {i(t,'ai_naming_failures')}
• Export Failures: {export_fail} · Purchase Failures: {i(t,'purchase_failed')}

⭐ REVIEWS
• Modal Shown: {i(t,'review_modal_shown')} → Completed: {i(t,'review_modal_completed')}
• Write Review Page: {i(t,'review_write_page')}

🔗 VIRAL
• Share Extension: {i(t,'share_extension_opened')} · Deep Links: {i(t,'deep_link_opens')}'''

    save_report(BASE, report, REPORT_PATH, display_date)
    # also skill-compatible path
    (BASE / "daily-reports").mkdir(parents=True, exist_ok=True)
    (BASE / "daily-reports" / f"{display_date}.md").write_text(report + "\n")
    tg = send_telegram(report)
    print(report)
    print("TELEGRAM_SENT_OK")
    print(json.dumps(tg))


if __name__ == "__main__":
    main()
