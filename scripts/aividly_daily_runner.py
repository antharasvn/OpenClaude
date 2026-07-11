#!/usr/bin/env python3
"""
AIVidly Daily Report Runner
===========================
FTUE, video creation, token economy, sub gate, sharing, trending.
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

PROJECT_ID = "aividly-8a1c3"
DATASET_ID = "analytics_510101525"
BASE = PROJECT_ROOT / "data" / "aividly"
REPORT_PATH = PROJECT_ROOT / "reports" / "aividly" / "daily"
TZ = "America/New_York"


def q(sql: str):
    return bq_query(PROJECT_ID, sql)


def cte(ss, se):
    return events_cte(PROJECT_ID, DATASET_ID, ss, se)


def q_metrics(start_us, end_us, ss, se):
    sql = f"""
WITH {cte(ss, se)}
SELECT
  COUNT(DISTINCT user_pseudo_id) AS total_users,
  COUNT(DISTINCT IF(event_name='first_open', user_pseudo_id, NULL)) AS new_users,
  COUNTIF(event_name='session_start') AS sessions,
  COUNTIF(event_name='ftue_app_opened') AS ftue_opened,
  COUNTIF(event_name='ftue_welcome_shown') AS welcome_shown,
  COUNTIF(event_name='ftue_welcome_cta_tapped') AS welcome_cta_tapped,
  COUNTIF(event_name='ftue_intent_onboarding_started') AS intent_started,
  COUNTIF(event_name='ftue_intent_onboarding_completed') AS intent_completed,
  COUNTIF(event_name='onboarding_completed') AS onboarding_completed,
  COUNTIF(event_name='ftue_first_creation_completed') AS first_creation_completed,
  COUNTIF(event_name='video_generation_started') AS gen_started,
  COUNTIF(event_name='video_generation_completed') AS gen_completed,
  COUNTIF(event_name='first_video_created') AS first_video,
  COUNTIF(event_name='preview_opened') AS preview_opened,
  COUNTIF(event_name='preview_dismissed') AS preview_dismissed,
  COUNTIF(event_name='first_export_completed') AS first_export,
  COUNTIF(event_name='video_auto_saved') AS auto_saved,
  COUNTIF(event_name='starter_tokens_granted') AS starter_granted,
  COUNTIF(event_name='tokens_insufficient_shown') AS tokens_insufficient,
  COUNTIF(event_name='token_store_viewed') AS store_viewed,
  COUNTIF(event_name='tokens_path_selected') AS path_selected,
  COUNTIF(event_name='token_pack_selected') AS pack_selected,
  COUNTIF(event_name='token_pack_purchase_started') AS purchase_started,
  COUNTIF(event_name='token_pack_purchased') AS pack_purchased,
  COUNTIF(event_name='paywall_shown') AS paywall_shown,
  COUNTIF(event_name='subscription_gate_shown') AS sub_gate_shown,
  COUNTIF(event_name='subscription_gate_dismissed') AS sub_gate_dismissed,
  COUNTIF(event_name='subscription_gate_tokens_tap') AS sub_gate_tokens_tap,
  COUNTIF(event_name='subscription_gate_more_options_tap') AS sub_gate_more_options,
  COUNTIF(event_name='purchase') AS purchases,
  COUNTIF(event_name IN ('in_app_purchase','rc_initial_purchase')) AS iap_purchases,
  COUNTIF(event_name='preview_share_clicked') AS share_clicked,
  COUNTIF(event_name='preview_share_completed') AS share_completed,
  COUNTIF(event_name='share_funnel_completion') AS share_funnel,
  COUNTIF(event_name='content_shared') AS content_shared,
  COUNTIF(event_name='video_shared') AS video_shared,
  COUNTIF(event_name='celebration_variant_shown') AS celebrations,
  COUNTIF(event_name='trending_topics_viewed') AS trending_viewed,
  COUNTIF(event_name='trending_topic_selected') AS trending_selected,
  COUNTIF(event_name='trend_used_for_video') AS trend_used
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
GROUP BY 1 ORDER BY new_users DESC LIMIT 5
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
    print(f"=== AIVidly Daily Report — {display_date} ===\n")

    t = row(q_metrics(h24, now_us, ss, se))
    y = row(q_metrics(h48, h24, ss, se))
    lw = row(q_metrics(h192, h168, sws, swe))
    sources = q_source(h24, now_us, ss, se)
    countries = q_countries(h24, now_us, ss, se)

    total_u, new_u, sessions = i(t, "total_users"), i(t, "new_users"), i(t, "sessions")
    onb_rate = safe_rate(i(t, "onboarding_completed"), i(t, "ftue_opened"))
    welcome_rate = safe_rate(i(t, "welcome_cta_tapped"), i(t, "ftue_opened"))
    gen_success = safe_rate(i(t, "gen_completed"), i(t, "gen_started"))
    first_video_rate = safe_rate(i(t, "first_video"), new_u)
    exhaust = safe_rate(i(t, "tokens_insufficient"), sessions)
    dismiss_rate = safe_rate(i(t, "sub_gate_dismissed"), i(t, "sub_gate_shown"))
    share_rate = safe_rate(
        i(t, "share_completed") + i(t, "video_shared"),
        i(t, "gen_completed"),
    )
    token_conv = safe_rate(i(t, "pack_purchased"), i(t, "store_viewed"))
    purchases = i(t, "purchases") + i(t, "iap_purchases")

    country_top = " · ".join(
        f"{r.get('country','?')} {int(r.get('new_users',0) or 0)}" for r in countries[:5]
    ) or "(no data)"

    alerts = []
    if exhaust > 15:
        alerts.append(f"High token exhaustion {exhaust}% of sessions")
    if dismiss_rate > 80 and i(t, "sub_gate_shown") >= 10:
        alerts.append(f"Sub gate dismiss rate {dismiss_rate}%")
    if gen_success < 50 and i(t, "gen_started") >= 10:
        alerts.append(f"Video gen success only {gen_success}%")
    if purchases == 0 and i(t, "paywall_shown") + i(t, "sub_gate_shown") >= 20:
        alerts.append("0 purchases with meaningful paywall/gate traffic")
    alerts_block = ("\n⚠️ Alerts\n" + "\n".join(f"• {a}" for a in alerts)) if alerts else ""

    report = f'''📊 AIVidly Daily Report — {display_date} ({display_time} {tz_label})

👥 USERS (24h)
• Total: {total_u}
• New: {new_u} (DoD {pct(new_u, i(y,'new_users'))} · WoW {pct(new_u, i(lw,'new_users'))})
• Sessions: {sessions}
• Source: {format_source_split(sources)}
Top countries: {country_top}

🎯 ONBOARDING FUNNEL
FTUE: {i(t,'ftue_opened')}
├─ Welcome CTA: {i(t,'welcome_cta_tapped')} ({welcome_rate}%)
├─ Intent completed: {i(t,'intent_completed')}
├─ Onboarding done: {i(t,'onboarding_completed')} ({onb_rate}%)
└─ First creation: {i(t,'first_creation_completed')}

🎥 VIDEO CREATION
• Started: {i(t,'gen_started')} → Completed: {i(t,'gen_completed')} ({gen_success}%)
• First video: {i(t,'first_video')} ({first_video_rate}% of new)
• Previews: {i(t,'preview_opened')} opened → {i(t,'preview_dismissed')} dismissed
• First export: {i(t,'first_export')}

🪙 TOKEN ECONOMY
• Starter granted: {i(t,'starter_granted')}
• Insufficient shown: {i(t,'tokens_insufficient')} ({exhaust}% of sessions)
• Store viewed: {i(t,'store_viewed')} → Purchased: {i(t,'pack_purchased')} ({token_conv}%)

💰 MONETIZATION
Sub Gate:
• Shown: {i(t,'sub_gate_shown')} → Dismissed: {i(t,'sub_gate_dismissed')} ({dismiss_rate}%)
• Tokens tap: {i(t,'sub_gate_tokens_tap')} · More options: {i(t,'sub_gate_more_options')}
Paywall shown: {i(t,'paywall_shown')}
Purchases: {purchases} (DoD {pct(purchases, i(y,'purchases')+i(y,'iap_purchases'))} · WoW {pct(purchases, i(lw,'purchases')+i(lw,'iap_purchases'))}) {get_conversion_emoji(safe_rate(purchases, max(1, i(t,'paywall_shown'))))}

📤 SHARING
• Click: {i(t,'share_clicked')} → Complete: {i(t,'share_completed')}
• Videos shared: {i(t,'video_shared')} · Share rate: {share_rate}% of completed videos

🔥 TRENDING
• Viewed: {i(t,'trending_viewed')} → Selected: {i(t,'trending_selected')} → Used: {i(t,'trend_used')}{alerts_block}'''

    save_report(BASE, report, REPORT_PATH, display_date)
    (BASE / "daily-reports").mkdir(parents=True, exist_ok=True)
    (BASE / "daily-reports" / f"{display_date}.md").write_text(report + "\n")
    tg = send_telegram(report)
    print(report)
    print("TELEGRAM_SENT_OK")
    print(json.dumps(tg))


if __name__ == "__main__":
    main()
