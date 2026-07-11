#!/usr/bin/env python3
"""
VidNotes Daily Report Runner
============================
Multiplatform growth, new-user funnel by platform, trial→paid, transcription quality, alerts.
Rolling 24h. No events_*/intraday double-count. Dual Telegram delivery.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from daily_report_common import (  # noqa: E402
    PROJECT_ROOT,
    DEFAULT_BOT_TOKEN,
    DEFAULT_CHAT_ID,
    bq_query,
    events_cte,
    format_country_conversion,
    format_country_lines,
    format_source_split,
    get_conversion_emoji,
    pct,
    platform_sql,
    rolling_windows,
    safe_rate,
    save_report,
    send_telegram,
    traffic_bucket_sql,
)

PROJECT_ID = "vidnotes-7864d"
DATASET = "analytics_508326759"
BASE = PROJECT_ROOT / "data" / "vidnotes"
REPORT_PATH = PROJECT_ROOT / "reports" / "vidnotes" / "daily"
TZ = "America/New_York"

AAA_BOT_TOKEN = os.environ.get("AAA_BOT_TOKEN", DEFAULT_BOT_TOKEN)
AAA_CHAT_ID = os.environ.get("AAA_CHAT_ID", DEFAULT_CHAT_ID)
SILPHO_BOT_TOKEN = os.environ.get(
    "SILPHO_BOT_TOKEN", "8733346629:AAGixlBDK2fg6Xyjx5iLQDjsBGOhKz3xF4Q"
)
SILPHO_CHAT_ID = os.environ.get("SILPHO_CHAT_ID", "-5088617466")

PAYWALL = "('onboarding_paywall_viewed','paywall_viewed')"
PAID = "('onboarding_purchase_completed','purchase')"


def q(sql: str):
    return bq_query(PROJECT_ID, sql)


def cte(ss, se):
    return events_cte(PROJECT_ID, DATASET, ss, se)


def q_growth(start_us, end_us, ss, se):
    sql = f"""
WITH {cte(ss, se)}, user_seg AS (
  SELECT user_pseudo_id, MAX(IF(event_name='first_open',1,0)) AS is_new
  FROM all_events WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1
)
SELECT IF(is_new=1,'new','returning') AS segment, COUNT(*) AS users
FROM user_seg GROUP BY 1
"""
    return q(sql)


def q_source_new_users(start_us, end_us, ss, se):
    bucket = traffic_bucket_sql("e")
    sql = f"""
WITH {cte(ss, se)}
SELECT {bucket} AS source, COUNT(DISTINCT e.user_pseudo_id) AS new_users
FROM all_events e
WHERE e.event_timestamp BETWEEN {start_us} AND {end_us} AND e.event_name='first_open'
GROUP BY 1
"""
    return q(sql)


def q_countries_new_users(start_us, end_us, ss, se):
    sql = f"""
WITH {cte(ss, se)}
SELECT geo.country, COUNT(DISTINCT user_pseudo_id) AS new_users
FROM all_events
WHERE event_timestamp BETWEEN {start_us} AND {end_us} AND event_name='first_open'
GROUP BY 1 ORDER BY new_users DESC LIMIT 10
"""
    return q(sql)


def q_platform_by_segment(start_us, end_us, ss, se):
    plat = platform_sql("e")
    sql = f"""
WITH {cte(ss, se)},
user_plat AS (
  SELECT e.user_pseudo_id, {plat} AS platform,
    MAX(IF(e.event_name='first_open',1,0)) AS is_new
  FROM all_events e
  WHERE e.event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1, 2
)
SELECT IF(is_new=1,'new','returning') AS segment, platform, COUNT(*) AS users
FROM user_plat GROUP BY 1, 2
"""
    return q(sql)


def q_new_user_funnel_by_platform(start_us, end_us, ss, se, now_us, se7):
    plat = platform_sql("e")
    # Need wider suffix for 7d look-forward: use se7 for CTE
    sql = f"""
WITH {cte(ss, se7)},
new_users AS (
  SELECT e.user_pseudo_id, {plat} AS platform, MIN(e.event_timestamp) AS first_open_us
  FROM all_events e
  WHERE e.event_name='first_open'
    AND e.event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1, 2
),
funnel AS (
  SELECT nu.platform, nu.user_pseudo_id,
    MAX(IF(e.event_name IN {PAYWALL}
           AND e.event_timestamp BETWEEN {start_us} AND {end_us}, 1, 0)) AS saw_paywall,
    MAX(IF(e.event_name='trial_start'
           AND e.event_timestamp BETWEEN {start_us} AND {end_us}, 1, 0)) AS started_trial,
    MAX(IF(e.event_name IN {PAID}
           AND e.event_timestamp BETWEEN nu.first_open_us
               AND nu.first_open_us + 7*24*60*60*1000000, 1, 0)) AS converted_7d
  FROM new_users nu
  LEFT JOIN all_events e ON e.user_pseudo_id = nu.user_pseudo_id
  GROUP BY 1, 2
)
SELECT platform, COUNT(*) AS new_users,
  SUM(saw_paywall) AS saw_paywall,
  SUM(started_trial) AS started_trial,
  SUM(converted_7d) AS converted_7d
FROM funnel GROUP BY 1
"""
    return q(sql)


def q_monetization_funnel(start_us, end_us, ss, se):
    sql = f"""
WITH {cte(ss, se)},
user_seg AS (
  SELECT user_pseudo_id, MAX(IF(event_name='first_open',1,0)) AS is_new
  FROM all_events WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1
), funnel AS (
  SELECT us.is_new, e.user_pseudo_id,
    MAX(IF(e.event_name IN {PAYWALL},1,0)) AS saw_paywall,
    MAX(IF(e.event_name='trial_start',1,0)) AS started_trial,
    MAX(IF(e.event_name IN {PAID},1,0)) AS purchased,
    MAX(IF(e.event_name='purchase_cancelled',1,0)) AS cancelled,
    MAX(IF(e.event_name='onboarding_purchase_failed',1,0)) AS failed,
    MAX(IF(e.event_name='onboarding_paywall_skipped',1,0)) AS skipped
  FROM all_events e JOIN user_seg us USING (user_pseudo_id)
  WHERE e.event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1, 2
)
SELECT IF(is_new=1,'new','returning') AS segment,
  COUNT(*) AS total_users,
  SUM(saw_paywall) AS paywall_users,
  SUM(started_trial) AS trial_users,
  SUM(purchased) AS paid_users,
  SUM(cancelled) AS cancelled_users,
  SUM(failed) AS failed_users,
  SUM(skipped) AS skipped_users
FROM funnel GROUP BY 1
"""
    return q(sql)


def q_trial_to_paid_7d(now_us, ss, se):
    start_7d = now_us - 604800 * 1_000_000
    sql = f"""
WITH {cte(ss, se)},
trial_users AS (
  SELECT DISTINCT user_pseudo_id FROM all_events
  WHERE event_timestamp BETWEEN {start_7d} AND {now_us} AND event_name='trial_start'
),
paid_users AS (
  SELECT DISTINCT user_pseudo_id FROM all_events
  WHERE event_timestamp BETWEEN {start_7d} AND {now_us} AND event_name IN {PAID}
)
SELECT
  (SELECT COUNT(*) FROM trial_users) AS trial_count,
  (SELECT COUNT(*) FROM trial_users t JOIN paid_users p USING (user_pseudo_id)) AS trial_to_paid_count
"""
    return q(sql)


def q_conversion_by_country(start_us, end_us, ss, se):
    sql = f"""
WITH {cte(ss, se)},
m AS (
  SELECT geo.country AS country,
    COUNT(DISTINCT IF(event_name IN {PAYWALL}, user_pseudo_id, NULL)) AS paywall_shown,
    COUNT(DISTINCT IF(event_name IN {PAID} OR event_name='trial_start', user_pseudo_id, NULL)) AS converted
  FROM all_events
  WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1
)
SELECT country, paywall_shown, converted,
  ROUND(SAFE_DIVIDE(converted, paywall_shown)*100,1) AS conversion_rate
FROM m WHERE paywall_shown > 0
ORDER BY paywall_shown DESC LIMIT 10
"""
    return q(sql)


def q_conversion_global(start_us, end_us, ss, se):
    sql = f"""
WITH {cte(ss, se)}
SELECT
  COUNT(DISTINCT IF(event_name IN {PAYWALL}, user_pseudo_id, NULL)) AS paywall_shown,
  COUNT(DISTINCT IF(event_name IN {PAID} OR event_name='trial_start', user_pseudo_id, NULL)) AS converted
FROM all_events
WHERE event_timestamp BETWEEN {start_us} AND {end_us}
"""
    return q(sql)


def q_transcription_by_platform(start_us, end_us, ss, se):
    plat = platform_sql("e")
    sql = f"""
WITH {cte(ss, se)}
SELECT {plat} AS platform,
  COUNT(DISTINCT IF(e.event_name='transcription_start', e.user_pseudo_id, NULL)) AS started,
  COUNT(DISTINCT IF(e.event_name='transcription_complete', e.user_pseudo_id, NULL)) AS completed
FROM all_events e
WHERE e.event_timestamp BETWEEN {start_us} AND {end_us}
  AND e.event_name IN ('transcription_start','transcription_complete')
GROUP BY 1
"""
    return q(sql)


def q_ai_features(start_us, end_us, ss, se):
    sql = f"""
WITH {cte(ss, se)}
SELECT event_name, COUNT(DISTINCT user_pseudo_id) AS users, COUNT(*) AS events
FROM all_events
WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  AND event_name IN ('ai_summary_generated','flashcard_created','content_export','export_initiated')
GROUP BY 1
"""
    return q(sql)


def q_web_conversions_3d(now_us, ss, se):
    """Distinct web paid/trial users in each of last 3 rolling 24h buckets."""
    rows = []
    for day_offset in range(3):
        end = now_us - day_offset * 86400 * 1_000_000
        start = end - 86400 * 1_000_000
        plat = platform_sql("e")
        sql = f"""
WITH {cte(ss, se)}
SELECT COUNT(DISTINCT e.user_pseudo_id) AS users
FROM all_events e
WHERE e.event_timestamp BETWEEN {start} AND {end}
  AND e.event_name IN ('onboarding_purchase_completed','purchase','trial_start')
  AND ({plat}) = 'Web'
"""
        try:
            r = q(sql)
            rows.append(int((r[0] if r else {}).get("users", 0) or 0))
        except Exception:
            rows.append(-1)
    return rows  # [d0, d1, d2]


def parse_funnel(data):
    result = {
        "new_users": 0, "new_paywall": 0, "new_trial": 0, "new_paid": 0,
        "new_cancelled": 0, "new_failed": 0, "new_skipped": 0,
        "ret_users": 0, "ret_paywall": 0, "ret_trial": 0, "ret_paid": 0,
        "ret_cancelled": 0, "ret_failed": 0, "ret_skipped": 0,
    }
    for r in data:
        p = "new_" if r.get("segment") == "new" else ("ret_" if r.get("segment") == "returning" else None)
        if not p:
            continue
        result[f"{p}users"] = int(r.get("total_users", 0) or 0)
        result[f"{p}paywall"] = int(r.get("paywall_users", 0) or 0)
        result[f"{p}trial"] = int(r.get("trial_users", 0) or 0)
        result[f"{p}paid"] = int(r.get("paid_users", 0) or 0)
        result[f"{p}cancelled"] = int(r.get("cancelled_users", 0) or 0)
        result[f"{p}failed"] = int(r.get("failed_users", 0) or 0)
        result[f"{p}skipped"] = int(r.get("skipped_users", 0) or 0)
    return result


def main():
    w = rolling_windows(TZ)
    now_us, h24, h48 = w["now_us"], w["h24_us"], w["h48_us"]
    h168, h192 = w["h168_us"], w["h192_us"]
    ss, se = w["suffix_start"], w["suffix_end"]
    sws, swe = w["suffix_week_start"], w["suffix_week_end"]
    se7 = w["suffix_end_7d"]
    s7 = w["suffix_7d_start"]
    s3 = w["suffix_3d_start"]
    display_date, display_time, tz_label = w["display_date"], w["display_time"], w["tz_label"]
    print(f"=== VidNotes Daily Report — {display_date} ===\n")

    g = q_growth(h24, now_us, ss, se)
    gd = q_growth(h48, h24, ss, se)
    gw = q_growth(h192, h168, sws, swe)
    seg = {r["segment"]: int(r["users"]) for r in g}
    segd = {r["segment"]: int(r["users"]) for r in gd}
    segw = {r["segment"]: int(r["users"]) for r in gw}
    new_users, returning = seg.get("new", 0), seg.get("returning", 0)

    sources = q_source_new_users(h24, now_us, ss, se)
    countries_new = q_countries_new_users(h24, now_us, ss, se)
    platforms_by_seg = q_platform_by_segment(h24, now_us, ss, se)

    plat_order = ["iPhone", "iPad", "Android", "Web"]
    new_plat = {p: 0 for p in plat_order}
    ret_plat = {p: 0 for p in plat_order}
    for r in platforms_by_seg:
        p = r.get("platform", "Other")
        if p not in new_plat:
            continue
        n = int(r.get("users", 0) or 0)
        if r.get("segment") == "new":
            new_plat[p] += n
        elif r.get("segment") == "returning":
            ret_plat[p] += n
    new_platform_line = " · ".join(f"{p} {new_plat[p]}" for p in plat_order)
    ret_platform_line = " · ".join(f"{p} {ret_plat[p]}" for p in plat_order)

    new_funnel = q_new_user_funnel_by_platform(h24, now_us, ss, se, now_us, se7)
    nf = {p: {"new_users": 0, "saw_paywall": 0, "started_trial": 0, "converted_7d": 0} for p in plat_order}
    for r in new_funnel:
        p = r.get("platform", "Other")
        if p not in nf:
            continue
        nf[p]["new_users"] = int(r.get("new_users", 0) or 0)
        nf[p]["saw_paywall"] = int(r.get("saw_paywall", 0) or 0)
        nf[p]["started_trial"] = int(r.get("started_trial", 0) or 0)
        nf[p]["converted_7d"] = int(r.get("converted_7d", 0) or 0)

    # funnel table
    def col(vals, width=8):
        return "".join(str(v).rjust(width) for v in vals)

    funnel_table = (
        "                    iPhone    iPad   Android    Web\n"
        f"  New users     :{col([nf[p]['new_users'] for p in plat_order])}\n"
        f"  Saw paywall   :{col([nf[p]['saw_paywall'] for p in plat_order])}\n"
        f"  Started trial :{col([nf[p]['started_trial'] for p in plat_order])}\n"
        f"  Converted (7d):{col([nf[p]['converted_7d'] for p in plat_order])}"
    )
    pv_parts, pt_parts, tp_parts = [], [], []
    for p in plat_order:
        nu, sp, st, c7 = nf[p]["new_users"], nf[p]["saw_paywall"], nf[p]["started_trial"], nf[p]["converted_7d"]
        if nu > 0:
            pv_parts.append(f"{p} {safe_rate(sp, nu):.0f}%")
        if sp > 0:
            pt_parts.append(f"{p} {safe_rate(st, sp):.0f}%")
        if st > 0:
            tp_parts.append(f"{p} {safe_rate(c7, st):.0f}%")
    pv_line = " · ".join(pv_parts) or "n/a"
    pt_line = " · ".join(pt_parts) or "n/a"
    tp_line = " · ".join(tp_parts) or "n/a"

    f = parse_funnel(q_monetization_funnel(h24, now_us, ss, se))
    f_d = parse_funnel(q_monetization_funnel(h48, h24, ss, se))
    f_w = parse_funnel(q_monetization_funnel(h192, h168, sws, swe))
    new_rate = safe_rate(f["new_paid"], f["new_paywall"])
    ret_rate = safe_rate(f["ret_paid"], f["ret_paywall"])
    total_pw = f["new_paywall"] + f["ret_paywall"]
    total_trial = f["new_trial"] + f["ret_trial"]
    total_paid = f["new_paid"] + f["ret_paid"]
    total_skipped = f["new_skipped"] + f["ret_skipped"]
    total_failed = f["new_failed"] + f["ret_failed"]
    total_cancelled = f["new_cancelled"] + f["ret_cancelled"]
    trial_rate = safe_rate(total_trial, total_pw)
    paid_d = f_d["new_paid"] + f_d["ret_paid"]
    paid_w = f_w["new_paid"] + f_w["ret_paid"]

    t2p = (q_trial_to_paid_7d(now_us, s7, se) or [{}])[0]
    trial_7d = int(t2p.get("trial_count", 0) or 0)
    trial_to_paid_7d = int(t2p.get("trial_to_paid_count", 0) or 0)
    t2p_rate = safe_rate(trial_to_paid_7d, trial_7d)

    conv_country = q_conversion_by_country(h24, now_us, ss, se)
    glob = (q_conversion_global(h24, now_us, ss, se) or [{}])[0]

    trans_by = q_transcription_by_platform(h24, now_us, ss, se)
    trans_plat = {p: {"started": 0, "completed": 0} for p in plat_order}
    for r in trans_by:
        p = r.get("platform", "Other")
        if p not in trans_plat:
            continue
        trans_plat[p]["started"] = int(r.get("started", 0) or 0)
        trans_plat[p]["completed"] = int(r.get("completed", 0) or 0)
    total_started = sum(v["started"] for v in trans_plat.values())
    total_completed = sum(v["completed"] for v in trans_plat.values())
    trans_success = safe_rate(total_completed, total_started)
    trans_emoji = "🔴" if (total_started and trans_success < 80) else ("⚠️" if trans_success < 90 else "✅")
    trans_per_plat = []
    trans_plat_rate = {}
    for p in plat_order:
        s, c = trans_plat[p]["started"], trans_plat[p]["completed"]
        if s > 0:
            r = safe_rate(c, s)
            trans_plat_rate[p] = r
            flag = " 🔴" if r < 70 else ""
            trans_per_plat.append(f"{p}: {r:.0f}%{flag}")
        else:
            trans_plat_rate[p] = None
    trans_per_plat_line = " · ".join(trans_per_plat) or "n/a"

    ai = q_ai_features(h24, now_us, ss, se)
    ai_map = {r["event_name"]: int(r.get("events", 0) or 0) for r in ai}
    ai_summaries = ai_map.get("ai_summary_generated", 0)
    exports = ai_map.get("content_export", 0) + ai_map.get("export_initiated", 0)
    flashcards = ai_map.get("flashcard_created", 0)

    web_d0, web_d1, web_d2 = q_web_conversions_3d(now_us, s3, se)

    alerts = []
    # Android trial→paid lag vs iPhone
    if nf["iPhone"]["started_trial"] >= 3 and nf["Android"]["started_trial"] >= 3:
        ip_r = safe_rate(nf["iPhone"]["converted_7d"], nf["iPhone"]["started_trial"])
        an_r = safe_rate(nf["Android"]["converted_7d"], nf["Android"]["started_trial"])
        if ip_r > 25 and an_r < 10:
            alerts.append(f"Android trial→paid {an_r:.0f}% vs iPhone {ip_r:.0f}% — conversion gap")
    for p in plat_order:
        r = trans_plat_rate.get(p)
        if r is not None and r < 70:
            alerts.append(f"{p} transcription {int(round(r))}% — degraded (overall {trans_success}%)")
    if web_d0 == 0 and web_d1 == 0 and web_d2 == 0:
        alerts.append("Web 0 conversions for 3 consecutive days — Web monetization stalled")
    alerts_block = ("\n🚨 ALERTS\n" + "\n".join(f"  - {a}" for a in alerts)) if alerts else ""

    report = f'''📊 VidNotes Daily — {display_date} (rolling 24h as of {display_time} {tz_label})

👥 GROWTH
  New users: {new_users} (DoD {pct(new_users, segd.get('new', 0))} · WoW {pct(new_users, segw.get('new', 0))})
  Returning: {returning}
  Source: {format_source_split(sources)}

  📱 Platform (NEW): {new_platform_line}
  📱 Platform (RET): {ret_platform_line}

  📍 New Users by Country (Top 10):
{format_country_lines(countries_new)}

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
  Paid DoD {pct(total_paid, paid_d)} · WoW {pct(total_paid, paid_w)}

  📍 Conversion by Country (Top 10; TOTAL=global):
{format_country_conversion(conv_country, int(glob.get('paywall_shown',0) or 0), int(glob.get('converted',0) or 0))}

🎙 PRODUCT
  Transcription success:
    {trans_per_plat_line}
  Overall: {trans_success}% {trans_emoji}
  AI summaries: {ai_summaries} · Exports: {exports} · Flashcards: {flashcards}{alerts_block}'''

    save_report(BASE, report, REPORT_PATH, display_date)
    print(report)
    try:
        send_telegram(report, SILPHO_BOT_TOKEN, SILPHO_CHAT_ID)
        print("SILPHO_TELEGRAM_SENT_OK")
    except Exception as e:
        print(f"SILPHO_TELEGRAM_ERROR: {e}")
    try:
        send_telegram(report, AAA_BOT_TOKEN, AAA_CHAT_ID)
        print("AAA_TELEGRAM_SENT_OK")
    except Exception as e:
        print(f"AAA_TELEGRAM_ERROR: {e}")


if __name__ == "__main__":
    main()
