#!/usr/bin/env python3
"""
Echo Daily Report Runner
========================
Growth + source/platform/market, monetization, product (music/voice), backend errors.
Rolling 24h. No events_*/intraday double-count.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
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
    format_platform_line,
    format_source_split,
    get_conversion_emoji,
    get_running_experiments,
    pct,
    platform_sql,
    rolling_windows,
    run,
    safe_rate,
    save_report,
    send_telegram,
    traffic_bucket_sql,
)

PROJECT_ID = "echo-79900"
DATASET_ID = "analytics_420731841"
BASE = PROJECT_ROOT / "data" / "echo"
REPORT_PATH = PROJECT_ROOT / "reports" / "echo" / "daily"
LOGO_PATH = Path.home() / "Projects/Echo/Code/Echo/Assets.xcassets/AppIcon.appiconset/app-icon-1024.png"
TZ = "America/New_York"


def q(sql: str):
    return bq_query(PROJECT_ID, sql)


def cte(ss, se):
    return events_cte(PROJECT_ID, DATASET_ID, ss, se)


def get_backend_errors(hours=24):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    cmd = [
        "gcloud", "logging", "read",
        f'resource.type="cloud_function" AND severity>=ERROR AND timestamp>="{cutoff_str}"',
        f"--project={PROJECT_ID}",
        "--limit=500",
        "--format=json",
    ]
    result = run(cmd)
    if result.returncode != 0:
        return {"total": -1, "by_function": {}, "by_type": {}, "error": result.stderr}
    try:
        errors = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return {"total": -1, "by_function": {}, "by_type": {}, "error": "JSON parse failed"}
    by_function, by_type = {}, {}
    for err in errors:
        func_name = err.get("resource", {}).get("labels", {}).get("function_name", "unknown")
        by_function[func_name] = by_function.get(func_name, 0) + 1
        msg = (err.get("jsonPayload", {}) or {}).get("message", "") or err.get("textPayload", "") or ""
        ml = msg.lower()
        if "no user record" in ml:
            err_type = "UserNotFound"
        elif "timeout" in ml:
            err_type = "Timeout"
        elif "quota" in ml or "rate limit" in ml:
            err_type = "Quota"
        elif "api" in ml and "error" in ml:
            err_type = "APIError"
        else:
            err_type = "Other"
        by_type[err_type] = by_type.get(err_type, 0) + 1
    return {
        "total": len(errors),
        "by_function": by_function,
        "by_type": by_type,
        "actionable": len(errors) - by_type.get("UserNotFound", 0),
    }


def format_backend_errors(errors):
    if errors.get("total", 0) < 0:
        return "  ⚠️ Could not fetch backend logs"
    total = errors["total"]
    actionable = errors.get("actionable", total)
    if total == 0:
        return "  ✅ No errors in last 24h"
    prefix = "🚨" if actionable > 50 else ("⚠️" if actionable > 20 else "")
    lines = [f"  {prefix} Total: {total} | Actionable: {actionable}".strip()]
    top_funcs = sorted(errors["by_function"].items(), key=lambda x: -x[1])[:3]
    if top_funcs:
        func_str = ", ".join(
            f"{(k.split('-')[-1] if '-' in k else k[:15])}: {v}" for k, v in top_funcs
        )
        lines.append(f"  By function: {func_str}")
    if errors["by_type"]:
        type_str = ", ".join(f"{k}: {v}" for k, v in errors["by_type"].items())
        lines.append(f"  By type: {type_str}")
    return "\n".join(lines)


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


def q_platform_new_users(start_us, end_us, ss, se):
    plat = platform_sql("e")
    sql = f"""
WITH {cte(ss, se)}
SELECT {plat} AS platform, COUNT(DISTINCT e.user_pseudo_id) AS users
FROM all_events e
WHERE e.event_timestamp BETWEEN {start_us} AND {end_us} AND e.event_name='first_open'
GROUP BY 1
"""
    return q(sql)


def q_market_new_users(start_us, end_us, ss, se):
    sql = f"""
WITH {cte(ss, se)}
SELECT
  CASE
    WHEN geo.country IN ('Turkey', 'Türkiye') THEN 'TR'
    WHEN geo.country = 'Vietnam' THEN 'VN'
    ELSE 'Other'
  END AS market,
  COUNT(DISTINCT user_pseudo_id) AS new_users
FROM all_events
WHERE event_timestamp BETWEEN {start_us} AND {end_us} AND event_name='first_open'
GROUP BY 1 ORDER BY new_users DESC
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


def q_monetization_funnel(start_us, end_us, ss, se):
    sql = f"""
WITH {cte(ss, se)},
user_seg AS (
  SELECT user_pseudo_id, MAX(IF(event_name='first_open',1,0)) AS is_new
  FROM all_events WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1
), funnel AS (
  SELECT us.is_new, e.user_pseudo_id,
    MAX(IF(e.event_name = 'paywall_viewed', 1, 0)) AS saw_paywall,
    MAX(IF(e.event_name IN ('purchase','in_app_purchase'), 1, 0)) AS purchased,
    MAX(IF(e.event_name = 'credit_purchased', 1, 0)) AS credit_purchased,
    MAX(IF(e.event_name IN ('trial_start','rc_trial_start'), 1, 0)) AS trial
  FROM all_events e
  JOIN user_seg us ON e.user_pseudo_id = us.user_pseudo_id
  WHERE e.event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1, 2
)
SELECT IF(is_new=1,'new','returning') AS segment,
  COUNT(*) AS total_users,
  SUM(saw_paywall) AS paywall_users,
  SUM(purchased) AS paid_users,
  SUM(credit_purchased) AS credit_users,
  SUM(trial) AS trial_users
FROM funnel GROUP BY 1
"""
    return q(sql)


def q_conversion_by_country(start_us, end_us, ss, se):
    sql = f"""
WITH {cte(ss, se)},
m AS (
  SELECT geo.country AS country,
    COUNT(DISTINCT IF(event_name='paywall_viewed', user_pseudo_id, NULL)) AS paywall_shown,
    COUNT(DISTINCT IF(event_name IN ('purchase','in_app_purchase'), user_pseudo_id, NULL)) AS converted
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
  COUNT(DISTINCT IF(event_name='paywall_viewed', user_pseudo_id, NULL)) AS paywall_shown,
  COUNT(DISTINCT IF(event_name IN ('purchase','in_app_purchase'), user_pseudo_id, NULL)) AS converted
FROM all_events
WHERE event_timestamp BETWEEN {start_us} AND {end_us}
"""
    return q(sql)


def q_product(start_us, end_us, ss, se):
    sql = f"""
WITH {cte(ss, se)}
SELECT event_name, COUNT(DISTINCT user_pseudo_id) AS users, COUNT(*) AS events
FROM all_events
WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  AND event_name IN (
    'music_creation_started','music_generation_completed','first_music_generated',
    'voice_cloning_started','voice_isolator_started','tts_started','tts_credit_charged',
    'tap_famous_voice','famous_voice_cloning_started','famous_voice_selected'
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
    MAX(IF(e.event_name='paywall_viewed',1,0)) AS saw_paywall,
    MAX(IF(e.event_name IN ('purchase','in_app_purchase'),1,0)) AS converted
  FROM all_events e JOIN exp_users ue USING (user_pseudo_id)
  WHERE e.event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1, 2
)
SELECT variant, SUM(saw_paywall) AS paywall,
  ROUND(SAFE_DIVIDE(SUM(converted), SUM(saw_paywall))*100,1) AS conv_rate
FROM user_events WHERE saw_paywall=1 GROUP BY variant ORDER BY variant
"""
        try:
            rows = q(sql)
            for row in rows:
                row["exp_id"] = exp_id
                row["exp_name"] = exp["name"]
            results.extend(rows)
        except Exception as exc:
            results.append({"exp_id": exp_id, "exp_name": exp["name"], "variant": "?", "paywall": 0, "conv_rate": 0, "error": str(exc)[:80]})
    return results


def parse_funnel(data):
    out = {
        "new_users": 0, "new_paywall": 0, "new_paid": 0, "new_credits": 0, "new_trial": 0,
        "ret_users": 0, "ret_paywall": 0, "ret_paid": 0, "ret_credits": 0, "ret_trial": 0,
    }
    for r in data:
        p = "new_" if r.get("segment") == "new" else ("ret_" if r.get("segment") == "returning" else None)
        if not p:
            continue
        out[f"{p}users"] = int(r.get("total_users", 0) or 0)
        out[f"{p}paywall"] = int(r.get("paywall_users", 0) or 0)
        out[f"{p}paid"] = int(r.get("paid_users", 0) or 0)
        out[f"{p}credits"] = int(r.get("credit_users", 0) or 0)
        out[f"{p}trial"] = int(r.get("trial_users", 0) or 0)
    return out


def main():
    w = rolling_windows(TZ)
    now_us, h24, h48, h168, h192 = w["now_us"], w["h24_us"], w["h48_us"], w["h168_us"], w["h192_us"]
    ss, se, sws, swe = w["suffix_start"], w["suffix_end"], w["suffix_week_start"], w["suffix_week_end"]
    display_date, display_time, tz_label = w["display_date"], w["display_time"], w["tz_label"]
    print(f"=== Echo Daily Report — {display_date} ===\n")

    g = q_growth(h24, now_us, ss, se)
    gd = q_growth(h48, h24, ss, se)
    gw = q_growth(h192, h168, sws, swe)
    seg = {r["segment"]: int(r["users"]) for r in g}
    segd = {r["segment"]: int(r["users"]) for r in gd}
    segw = {r["segment"]: int(r["users"]) for r in gw}
    new_users, returning = seg.get("new", 0), seg.get("returning", 0)

    sources = q_source_new_users(h24, now_us, ss, se)
    platforms = q_platform_new_users(h24, now_us, ss, se)
    markets = q_market_new_users(h24, now_us, ss, se)
    market_line = " · ".join(
        f"{r.get('market','?')} {int(r.get('new_users',0) or 0)}" for r in markets
    ) or "(no data)"
    countries_new = q_countries_new_users(h24, now_us, ss, se)

    f = parse_funnel(q_monetization_funnel(h24, now_us, ss, se))
    fd = parse_funnel(q_monetization_funnel(h48, h24, ss, se))
    fw = parse_funnel(q_monetization_funnel(h192, h168, sws, swe))
    new_rate = safe_rate(f["new_paid"], f["new_paywall"])
    ret_rate = safe_rate(f["ret_paid"], f["ret_paywall"])
    total_pw = f["new_paywall"] + f["ret_paywall"]
    total_paid = f["new_paid"] + f["ret_paid"]
    total_credits = f["new_credits"] + f["ret_credits"]
    total_trial = f["new_trial"] + f["ret_trial"]
    overall = safe_rate(total_paid, total_pw)
    paid_d = fd["new_paid"] + fd["ret_paid"]
    paid_w = fw["new_paid"] + fw["ret_paid"]

    conv_country = q_conversion_by_country(h24, now_us, ss, se)
    glob = (q_conversion_global(h24, now_us, ss, se) or [{}])[0]
    p = q_product(h24, now_us, ss, se)
    pu = {r["event_name"]: int(r["users"]) for r in p}
    pe = {r["event_name"]: int(r["events"]) for r in p}

    exp_metrics = q_experiment_metrics(h24, now_us, ss, se)
    exp_ok = [r for r in exp_metrics if "error" not in r]
    exp_breakdown = format_experiments(exp_ok if exp_ok else exp_metrics)
    backend_section = format_backend_errors(get_backend_errors(24))

    report = f'''📊 Echo Daily — {display_date} (rolling 24h as of {display_time} {tz_label})

👥 GROWTH
  New users: {new_users} (DoD {pct(new_users, segd.get('new', 0))} · WoW {pct(new_users, segw.get('new', 0))})
  Returning: {returning}
  Source: {format_source_split(sources)}
  📱 Platform (new): {format_platform_line(platforms)}
  🌍 Market (new): {market_line}

  📍 New Users by Country (Top 10):
{format_country_lines(countries_new)}

💰 MONETIZATION
  📊 Funnel:
    New users: {f['new_users']} → paywall {f['new_paywall']} → paid {f['new_paid']} ({new_rate}%) {get_conversion_emoji(new_rate)}
    Returning: {f['ret_users']} → paywall {f['ret_paywall']} → paid {f['ret_paid']} ({ret_rate}%) {get_conversion_emoji(ret_rate)}

  Overall: {total_pw} paywall → {total_paid} paid ({overall}%) {get_conversion_emoji(overall)}
  Credits purchased: {total_credits} users · Trials: {total_trial}
  Paid DoD {pct(total_paid, paid_d)} · WoW {pct(total_paid, paid_w)}

  📍 Conversion by Country (Top 10; TOTAL=global):
{format_country_conversion(conv_country, int(glob.get('paywall_shown',0) or 0), int(glob.get('converted',0) or 0))}

🧪 EXPERIMENTS (B=Baseline | users/conv%)
{exp_breakdown}

🎵 PRODUCT
  Music created: {pu.get('music_generation_completed', 0)} users ({pe.get('music_generation_completed', 0)} tracks)
  First music: {pu.get('first_music_generated', 0)} new users

  🎤 VOICE FEATURES
  Famous voices tapped: {pu.get('tap_famous_voice', 0)} users ({pe.get('tap_famous_voice', 0)} taps)
  Famous voice cloning: {pu.get('famous_voice_cloning_started', 0)} users
  Custom voice cloning: {pu.get('voice_cloning_started', 0)} users
  Voice isolator: {pu.get('voice_isolator_started', 0)} users
  TTS: {pu.get('tts_started', 0)} users ({pe.get('tts_credit_charged', 0)} credits)

🔧 BACKEND (Firebase Functions)
{backend_section}'''

    save_report(BASE, report, REPORT_PATH, display_date)
    tg = send_telegram(report)
    print(report)
    print("TELEGRAM_SENT_OK")
    print(json.dumps(tg))

    if exp_ok:
        heatmap_script = PROJECT_ROOT / "scripts" / "app_experiment_heatmap.py"
        heatmap_output = PROJECT_ROOT / "reports" / "echo_experiments.png"
        if heatmap_script.exists():
            subprocess.run(
                ["python3", str(heatmap_script), "Echo", PROJECT_ID, DATASET_ID, str(LOGO_PATH)],
                capture_output=True,
                timeout=600,
            )
            if heatmap_output.exists():
                subprocess.run(
                    [
                        "curl", "-s", "-X", "POST",
                        "--connect-timeout", "10", "--max-time", "120",
                        f"https://api.telegram.org/bot{DEFAULT_BOT_TOKEN}/sendPhoto",
                        "-F", f"chat_id={DEFAULT_CHAT_ID}",
                        "-F", f"photo=@{heatmap_output}",
                        "-F", "caption=🧪 Echo Experiments (24h)",
                    ],
                    capture_output=True,
                    text=True,
                )
                print("HEATMAP_SENT")


if __name__ == "__main__":
    main()
