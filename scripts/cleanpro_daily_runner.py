#!/usr/bin/env python3
"""
CleanPro Daily Report Runner
============================
Onboarding completion (cohort-safe), paywall→trial→paid, RC health, product scans.
Rolling 24h. No events_*/intraday double-count.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from daily_report_common import (  # noqa: E402
    PROJECT_ROOT,
    DEFAULT_BOT_TOKEN,
    DEFAULT_CHAT_ID,
    bq_query,
    events_cte,
    exp_user_property_keys,
    format_country_conversion,
    format_country_lines,
    format_experiments,
    format_source_split,
    get_conversion_emoji,
    get_onboarding_emoji,
    get_running_experiments,
    pct,
    rolling_windows,
    safe_rate,
    save_report,
    send_telegram,
    traffic_bucket_sql,
)

PROJECT_ID = "cleaner-app-e98f0"
DATASET_ID = "analytics_269202926"
BASE = PROJECT_ROOT / "data" / "cleanpro"
REPORT_PATH = PROJECT_ROOT / "reports" / "cleanpro" / "daily"
TZ = "Asia/Saigon"

PAYWALL_SHOWN = "('onboarding_paywall_shown','cleanpro_paywall_shown')"
TRIAL_EV = "('onboarding_paywall_converted','cleanpro_paywall_converted','native_paywall_converted')"
PAID_EV = "('purchase','app_initial_purchase')"


def q(sql: str):
    return bq_query(PROJECT_ID, sql)


def cte(ss, se):
    return events_cte(PROJECT_ID, DATASET_ID, ss, se)


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


def q_onboarding_completion_by_country(start_us, end_us, ss, se):
    """Cohort-safe: only new users (first_open in window). Finished only among those who saw paywall."""
    sql = f"""
WITH {cte(ss, se)},
new_users AS (
  SELECT user_pseudo_id, ANY_VALUE(geo.country) AS country
  FROM all_events
  WHERE event_timestamp BETWEEN {start_us} AND {end_us} AND event_name='first_open'
  GROUP BY 1
),
flags AS (
  SELECT
    nu.user_pseudo_id,
    nu.country,
    MAX(IF(e.event_name IN ('onboarding_paywall_shown'), 1, 0)) AS saw_paywall,
    MAX(IF(e.event_name IN ('onboarding_paywall_dismissed','onboarding_paywall_converted'), 1, 0)) AS finished
  FROM new_users nu
  LEFT JOIN all_events e
    ON e.user_pseudo_id = nu.user_pseudo_id
   AND e.event_timestamp BETWEEN {start_us} AND {end_us}
   AND e.event_name IN (
     'onboarding_paywall_shown','onboarding_paywall_dismissed','onboarding_paywall_converted'
   )
  GROUP BY 1, 2
)
SELECT
  country,
  COUNT(*) AS new_users,
  SUM(saw_paywall) AS saw_paywall,
  -- finished only counts users who also saw paywall (avoids >100%)
  SUM(IF(saw_paywall=1 AND finished=1, 1, 0)) AS finished_onboarding,
  ROUND(SAFE_DIVIDE(SUM(saw_paywall), COUNT(*)) * 100, 1) AS reach_paywall_rate,
  ROUND(SAFE_DIVIDE(SUM(IF(saw_paywall=1 AND finished=1, 1, 0)), SUM(saw_paywall)) * 100, 1) AS completion_rate
FROM flags
GROUP BY country
HAVING new_users > 0
ORDER BY new_users DESC
LIMIT 10
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
    MAX(IF(e.event_name IN {PAYWALL_SHOWN}, 1, 0)) AS saw_paywall,
    MAX(IF(e.event_name IN {TRIAL_EV}, 1, 0)) AS started_trial,
    MAX(IF(e.event_name IN {PAID_EV}, 1, 0)) AS purchased
  FROM all_events e
  JOIN user_seg us ON e.user_pseudo_id = us.user_pseudo_id
  WHERE e.event_timestamp BETWEEN {start_us} AND {end_us}
    AND NOT STARTS_WITH(e.event_name, 'rc_')
  GROUP BY 1, 2
)
SELECT IF(is_new=1,'new','returning') AS segment,
  COUNT(*) AS total_users,
  SUM(saw_paywall) AS paywall_users,
  SUM(started_trial) AS trial_users,
  SUM(purchased) AS paid_users
FROM funnel GROUP BY 1
"""
    return q(sql)


def q_rc_events(start_us, end_us, ss, se):
    sql = f"""
WITH {cte(ss, se)}
SELECT event_name, COUNT(DISTINCT user_pseudo_id) AS users
FROM all_events
WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  AND event_name IN ('rc_trial_start','rc_initial_purchase','rc_cancellation','rc_expiration','rc_billing_issue')
GROUP BY 1
"""
    return q(sql)


def q_trial_to_paid_7d_client(now_us, ss, se):
    """Client-side trial→paid over rolling 7d (same ID namespace as funnel)."""
    start_7d = now_us - 604800 * 1_000_000
    sql = f"""
WITH {cte(ss, se)},
trial_users AS (
  SELECT DISTINCT user_pseudo_id
  FROM all_events
  WHERE event_timestamp BETWEEN {start_7d} AND {now_us}
    AND event_name IN {TRIAL_EV}
),
paid_users AS (
  SELECT DISTINCT user_pseudo_id
  FROM all_events
  WHERE event_timestamp BETWEEN {start_7d} AND {now_us}
    AND event_name IN {PAID_EV}
)
SELECT
  (SELECT COUNT(*) FROM trial_users) AS trial_count,
  (SELECT COUNT(*) FROM trial_users t JOIN paid_users p USING (user_pseudo_id)) AS trial_to_paid_count
"""
    return q(sql)


def q_trial_to_paid_7d_rc(now_us, ss, se):
    """RC S2S-only trial→paid (separate user_pseudo_id namespace — do not mix with client)."""
    start_7d = now_us - 604800 * 1_000_000
    sql = f"""
WITH {cte(ss, se)},
trial_users AS (
  SELECT DISTINCT user_pseudo_id FROM all_events
  WHERE event_timestamp BETWEEN {start_7d} AND {now_us} AND event_name='rc_trial_start'
),
paid_users AS (
  SELECT DISTINCT user_pseudo_id FROM all_events
  WHERE event_timestamp BETWEEN {start_7d} AND {now_us} AND event_name='rc_initial_purchase'
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
    COUNT(DISTINCT IF(event_name IN {PAYWALL_SHOWN}, user_pseudo_id, NULL)) AS paywall_shown,
    COUNT(DISTINCT IF(event_name IN {TRIAL_EV} OR event_name IN {PAID_EV}, user_pseudo_id, NULL)) AS converted
  FROM all_events
  WHERE event_timestamp BETWEEN {start_us} AND {end_us}
    AND NOT STARTS_WITH(event_name, 'rc_')
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
  COUNT(DISTINCT IF(event_name IN {PAYWALL_SHOWN}, user_pseudo_id, NULL)) AS paywall_shown,
  COUNT(DISTINCT IF(event_name IN {TRIAL_EV} OR event_name IN {PAID_EV}, user_pseudo_id, NULL)) AS converted
FROM all_events
WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  AND NOT STARTS_WITH(event_name, 'rc_')
"""
    return q(sql)


def q_product(start_us, end_us, ss, se):
    sql = f"""
WITH {cte(ss, se)}
SELECT event_name, COUNT(DISTINCT user_pseudo_id) AS users, COUNT(*) AS events
FROM all_events
WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  AND event_name IN (
    'scan_completed','first_scan_complete','clean_completed','first_delete_complete',
    'scan_v2_start','scan_v2_complete'
  )
GROUP BY 1 ORDER BY users DESC
"""
    return q(sql)


def q_experiment_metrics(start_us, end_us, ss, se):
    experiments = get_running_experiments(PROJECT_ID)
    if not experiments:
        return []
    results = []
    for exp in experiments[:8]:
        exp_id = exp["id"]
        keys = ", ".join(f"'{k}'" for k in exp_user_property_keys(exp_id))
        sql = f"""
WITH {cte(ss, se)},
exp_users AS (
  SELECT user_pseudo_id,
    (SELECT value.string_value FROM UNNEST(user_properties) WHERE key IN ({keys}) LIMIT 1) AS variant
  FROM all_events
  WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1, 2 HAVING variant IS NOT NULL
),
user_events AS (
  SELECT ue.variant, e.user_pseudo_id,
    MAX(IF(e.event_name IN {PAYWALL_SHOWN},1,0)) AS saw_paywall,
    MAX(IF(e.event_name IN ('onboarding_paywall_dismissed','onboarding_paywall_converted','cleanpro_paywall_converted'),1,0)) AS finished,
    MAX(IF(e.event_name IN {TRIAL_EV},1,0)) AS trial,
    MAX(IF(e.event_name IN {PAID_EV},1,0)) AS converted
  FROM all_events e JOIN exp_users ue USING (user_pseudo_id)
  WHERE e.event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1, 2
)
SELECT variant, SUM(saw_paywall) AS paywall,
  ROUND(SAFE_DIVIDE(SUM(finished), SUM(saw_paywall))*100,1) AS completion,
  ROUND(SAFE_DIVIDE(SUM(trial), SUM(saw_paywall))*100,1) AS trial_rate,
  ROUND(SAFE_DIVIDE(SUM(converted), SUM(saw_paywall))*100,1) AS conv_rate
FROM user_events WHERE saw_paywall=1 GROUP BY variant ORDER BY variant
"""
        try:
            rows = q(sql)
            for row in rows:
                row["exp_id"] = exp_id
                row["exp_name"] = exp.get("name", exp_id)
            results.extend(rows)
        except Exception as exc:
            results.append({
                "exp_id": exp_id, "exp_name": exp.get("name", exp_id),
                "variant": "?", "paywall": 0, "completion": 0, "trial_rate": 0, "conv_rate": 0,
                "error": str(exc)[:80],
            })
    return results


def parse_funnel(data):
    result = {
        "new_users": 0, "new_paywall": 0, "new_trial": 0, "new_paid": 0,
        "ret_users": 0, "ret_paywall": 0, "ret_trial": 0, "ret_paid": 0,
    }
    for r in data:
        p = "new_" if r.get("segment") == "new" else ("ret_" if r.get("segment") == "returning" else None)
        if not p:
            continue
        result[f"{p}users"] = int(r.get("total_users", 0) or 0)
        result[f"{p}paywall"] = int(r.get("paywall_users", 0) or 0)
        result[f"{p}trial"] = int(r.get("trial_users", 0) or 0)
        result[f"{p}paid"] = int(r.get("paid_users", 0) or 0)
    return result


def format_onboarding(rows):
    lines = []
    for r in rows[:10]:
        country = r.get("country") or "?"
        nu = int(r.get("new_users", 0) or 0)
        saw = int(r.get("saw_paywall", 0) or 0)
        fin = int(r.get("finished_onboarding", 0) or 0)
        rate = float(r.get("completion_rate", 0) or 0)
        lines.append(f"    {country}: {nu}→{saw}→{fin} ({rate}% complete) {get_onboarding_emoji(rate)}")
    return "\n".join(lines) if lines else "    (no data)"


def main():
    w = rolling_windows(TZ)
    now_us, h24, h48 = w["now_us"], w["h24_us"], w["h48_us"]
    h168, h192 = w["h168_us"], w["h192_us"]
    ss, se = w["suffix_start"], w["suffix_end"]
    sws, swe = w["suffix_week_start"], w["suffix_week_end"]
    s7 = w["suffix_7d_start"]
    display_date, display_time, tz_label = w["display_date"], w["display_time"], w["tz_label"]
    print(f"=== CleanPro Daily Report — {display_date} ===\n")

    g = q_growth(h24, now_us, ss, se)
    gd = q_growth(h48, h24, ss, se)
    gw = q_growth(h192, h168, sws, swe)
    seg = {r["segment"]: int(r["users"]) for r in g}
    segd = {r["segment"]: int(r["users"]) for r in gd}
    segw = {r["segment"]: int(r["users"]) for r in gw}
    new_users, returning = seg.get("new", 0), seg.get("returning", 0)

    sources = q_source_new_users(h24, now_us, ss, se)
    countries_new = q_countries_new_users(h24, now_us, ss, se)
    onboarding = q_onboarding_completion_by_country(h24, now_us, ss, se)

    f = parse_funnel(q_monetization_funnel(h24, now_us, ss, se))
    fd = parse_funnel(q_monetization_funnel(h48, h24, ss, se))
    fw = parse_funnel(q_monetization_funnel(h192, h168, sws, swe))
    new_rate = safe_rate(f["new_paid"], f["new_paywall"])
    ret_rate = safe_rate(f["ret_paid"], f["ret_paywall"])
    total_pw = f["new_paywall"] + f["ret_paywall"]
    total_trial = f["new_trial"] + f["ret_trial"]
    total_paid = f["new_paid"] + f["ret_paid"]
    pw_to_trial = safe_rate(total_trial, total_pw)
    paid_d = fd["new_paid"] + fd["ret_paid"]
    paid_w = fw["new_paid"] + fw["ret_paid"]

    rc_rows = q_rc_events(h24, now_us, ss, se)
    rc = {r.get("event_name"): int(r.get("users", 0) or 0) for r in rc_rows}

    t2p_c = (q_trial_to_paid_7d_client(now_us, s7, se) or [{}])[0]
    t2p_r = (q_trial_to_paid_7d_rc(now_us, s7, se) or [{}])[0]
    c_trial = int(t2p_c.get("trial_count", 0) or 0)
    c_paid = int(t2p_c.get("trial_to_paid_count", 0) or 0)
    r_trial = int(t2p_r.get("trial_count", 0) or 0)
    r_paid = int(t2p_r.get("trial_to_paid_count", 0) or 0)

    conv_country = q_conversion_by_country(h24, now_us, ss, se)
    glob = (q_conversion_global(h24, now_us, ss, se) or [{}])[0]

    p = q_product(h24, now_us, ss, se)
    pu = {r["event_name"]: int(r["users"]) for r in p}
    pe = {r["event_name"]: int(r["events"]) for r in p}
    scans_u = pu.get("scan_completed", 0) + pu.get("scan_v2_complete", 0)
    scans_e = pe.get("scan_completed", 0) + pe.get("scan_v2_complete", 0)

    exp_metrics = q_experiment_metrics(h24, now_us, ss, se)
    exp_ok = [r for r in exp_metrics if "error" not in r]
    exp_breakdown = format_experiments(exp_ok if exp_ok else exp_metrics, style="full")

    report = f'''📊 CleanPro Daily — {display_date} (rolling 24h as of {display_time} {tz_label})

👥 GROWTH
  New users: {new_users} (DoD {pct(new_users, segd.get('new', 0))} · WoW {pct(new_users, segw.get('new', 0))})
  Returning: {returning}
  Source: {format_source_split(sources)}

  📍 New Users by Country (Top 10):
{format_country_lines(countries_new)}

🚀 ONBOARDING (new→paywall→home; cohort-safe)
  📍 Completion by Country (Top 10):
{format_onboarding(onboarding)}

💰 MONETIZATION
  📊 Funnel (client events):
    New users: {f['new_users']} → paywall {f['new_paywall']} → trial {f['new_trial']} → paid {f['new_paid']} ({new_rate}%) {get_conversion_emoji(new_rate)}
    Returning: {f['ret_users']} → paywall {f['ret_paywall']} → trial {f['ret_trial']} → paid {f['ret_paid']} ({ret_rate}%) {get_conversion_emoji(ret_rate)}

  Overall: {total_pw} paywall → {total_trial} trial → {total_paid} paid
  Paywall→Trial: {pw_to_trial}%
  Trial→Paid 7d (client): {c_paid}/{c_trial} ({safe_rate(c_paid, c_trial)}%)
  Trial→Paid 7d (RC S2S): {r_paid}/{r_trial} ({safe_rate(r_paid, r_trial)}%)
  RC 24h: trials {rc.get('rc_trial_start',0)} · initial {rc.get('rc_initial_purchase',0)} · cancel {rc.get('rc_cancellation',0)} · expire {rc.get('rc_expiration',0)} · billing {rc.get('rc_billing_issue',0)}
  Paid DoD {pct(total_paid, paid_d)} · WoW {pct(total_paid, paid_w)}

  📍 Conversion by Country (Top 10; TOTAL=global; trial+paid):
{format_country_conversion(conv_country, int(glob.get('paywall_shown',0) or 0), int(glob.get('converted',0) or 0))}

🧪 EXPERIMENTS (B=Baseline | users/done%/trial%/conv%)
{exp_breakdown}

🧹 PRODUCT
  Scans: {scans_u} users ({scans_e} total scans)
  Cleans: {pu.get('clean_completed', 0)} users
  First scan: {pu.get('first_scan_complete', 0)} new users completed
  First delete: {pu.get('first_delete_complete', 0)} new users completed'''

    save_report(BASE, report, REPORT_PATH, display_date)
    tg = send_telegram(report)
    print(report)
    print("TELEGRAM_SENT_OK")
    print(json.dumps(tg))

    heatmap_script = PROJECT_ROOT / "scripts" / "experiment_heatmap_pro.py"
    if heatmap_script.exists():
        print("\n📊 Generating experiment heatmap...")
        result = subprocess.run(["python3", str(heatmap_script)], capture_output=True, text=True)
        heatmap_path = PROJECT_ROOT / "reports" / "experiments_heatmap_pro.png"
        if result.returncode == 0 and heatmap_path.exists():
            # send via curl multipart
            subprocess.run(
                [
                    # 120s ceiling: multipart photo upload, not a text POST.
                    # Unflagged curl has no overall timeout, so a hung
                    # api.telegram.org would burn this job's whole slot.
                    "curl", "-s", "-X", "POST",
                    "--connect-timeout", "10", "--max-time", "120",
                    f"https://api.telegram.org/bot{DEFAULT_BOT_TOKEN}/sendPhoto",
                    "-F", f"chat_id={DEFAULT_CHAT_ID}",
                    "-F", f"photo=@{heatmap_path}",
                    "-F", f"caption=🧪 CleanPro Experiments Heatmap — {display_date}",
                ],
                capture_output=True,
                text=True,
            )
            print("HEATMAP_SENT_OK")
        else:
            print("⚠️ Heatmap generation skipped or failed")


if __name__ == "__main__":
    main()
