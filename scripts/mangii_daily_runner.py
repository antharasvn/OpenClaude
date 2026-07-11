#!/usr/bin/env python3
"""
Mangii Daily Report Runner
==========================
Retention-first dashboard: source split, gen-depth activation, credit economy,
then paywall / experiments. Rolling 24h windows. No events_*/intraday double-count.
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
    format_platform_line,
    format_source_split,
    get_conversion_emoji,
    get_running_experiments,
    pct,
    platform_sql,
    rolling_windows,
    safe_rate,
    save_report,
    send_telegram,
    traffic_bucket_sql,
)

PROJECT_ID = "mangii-app"
DATASET_ID = "analytics_488420427"
APP_NAME = "Mangii"
LOGO_PATH = Path.home() / "Projects/Mangii/ios/Mangii/Assets.xcassets/AppIcon.appiconset/app-icon-1024.png"
BASE = PROJECT_ROOT / "data" / "mangii"
REPORT_PATH = PROJECT_ROOT / "reports" / "mangii" / "daily"
TZ = "America/New_York"


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
WHERE e.event_timestamp BETWEEN {start_us} AND {end_us}
  AND e.event_name = 'first_open'
GROUP BY 1
"""
    return q(sql)


def q_countries_new_users(start_us, end_us, ss, se):
    sql = f"""
WITH {cte(ss, se)}
SELECT geo.country, COUNT(DISTINCT user_pseudo_id) AS new_users
FROM all_events
WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  AND event_name = 'first_open'
GROUP BY 1 ORDER BY new_users DESC LIMIT 10
"""
    return q(sql)


def q_platform_new_users(start_us, end_us, ss, se):
    plat = platform_sql("e")
    sql = f"""
WITH {cte(ss, se)}
SELECT {plat} AS platform, COUNT(DISTINCT e.user_pseudo_id) AS users
FROM all_events e
WHERE e.event_timestamp BETWEEN {start_us} AND {end_us}
  AND e.event_name = 'first_open'
GROUP BY 1 ORDER BY users DESC
"""
    return q(sql)


def q_activation_depth(start_us, end_us, ss, se):
    """Among users with first_open in window: gen count buckets + 1→2 rate."""
    sql = f"""
WITH {cte(ss, se)},
new_users AS (
  SELECT DISTINCT user_pseudo_id
  FROM all_events
  WHERE event_timestamp BETWEEN {start_us} AND {end_us}
    AND event_name = 'first_open'
),
gens AS (
  SELECT nu.user_pseudo_id,
    COUNTIF(e.event_name = 'panel_generated') AS gen_events
  FROM new_users nu
  LEFT JOIN all_events e
    ON e.user_pseudo_id = nu.user_pseudo_id
   AND e.event_timestamp BETWEEN {start_us} AND {end_us}
   AND e.event_name = 'panel_generated'
  GROUP BY 1
)
SELECT
  COUNT(*) AS new_users,
  COUNTIF(gen_events = 0) AS gen0,
  COUNTIF(gen_events = 1) AS gen1,
  COUNTIF(gen_events BETWEEN 2 AND 4) AS gen2_4,
  COUNTIF(gen_events >= 5) AS gen5_plus,
  COUNTIF(gen_events >= 1) AS gen1_plus,
  COUNTIF(gen_events >= 2) AS gen2_plus
FROM gens
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
  SELECT
    us.is_new, e.user_pseudo_id,
    MAX(IF(e.event_name = 'paywall_shown', 1, 0)) AS saw_paywall,
    MAX(IF(e.event_name IN ('paywall_purchase_success','subscription_purchased','credit_pack_purchased'), 1, 0)) AS purchased,
    MAX(IF(e.event_name = 'paywall_cta_tapped', 1, 0)) AS cta_tapped,
    MAX(IF(e.event_name = 'paywall_plan_selected', 1, 0)) AS plan_selected,
    MAX(IF(e.event_name = 'paywall_purchase_cancelled', 1, 0)) AS purchase_cancelled,
    MAX(IF(e.event_name = 'paywall_purchase_failed', 1, 0)) AS purchase_failed,
    MAX(IF(e.event_name = 'subscription_purchased', 1, 0)) AS sub_purchased,
    MAX(IF(e.event_name = 'credit_pack_purchased', 1, 0)) AS pack_purchased
  FROM all_events e
  JOIN user_seg us ON e.user_pseudo_id = us.user_pseudo_id
  WHERE e.event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1, 2
)
SELECT
  IF(is_new=1,'new','returning') AS segment,
  COUNT(*) AS total_users,
  SUM(saw_paywall) AS paywall_users,
  SUM(purchased) AS paid_users,
  SUM(cta_tapped) AS cta_tapped_users,
  SUM(plan_selected) AS plan_selected_users,
  SUM(purchase_cancelled) AS purchase_cancelled_users,
  SUM(purchase_failed) AS purchase_failed_users,
  SUM(sub_purchased) AS sub_users,
  SUM(pack_purchased) AS pack_users
FROM funnel GROUP BY 1
"""
    return q(sql)


def q_conversion_by_country(start_us, end_us, ss, se):
    sql = f"""
WITH {cte(ss, se)},
country_metrics AS (
  SELECT
    geo.country AS country,
    COUNT(DISTINCT IF(event_name = 'paywall_shown', user_pseudo_id, NULL)) AS paywall_shown,
    COUNT(DISTINCT IF(event_name IN ('paywall_purchase_success','subscription_purchased','credit_pack_purchased'), user_pseudo_id, NULL)) AS converted
  FROM all_events
  WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1
)
SELECT country, paywall_shown, converted,
  ROUND(SAFE_DIVIDE(converted, paywall_shown) * 100, 1) AS conversion_rate
FROM country_metrics
WHERE paywall_shown > 0
ORDER BY paywall_shown DESC LIMIT 10
"""
    return q(sql)


def q_conversion_global(start_us, end_us, ss, se):
    sql = f"""
WITH {cte(ss, se)}
SELECT
  COUNT(DISTINCT IF(event_name = 'paywall_shown', user_pseudo_id, NULL)) AS paywall_shown,
  COUNT(DISTINCT IF(event_name IN ('paywall_purchase_success','subscription_purchased','credit_pack_purchased'), user_pseudo_id, NULL)) AS converted
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
    'panel_generate_tapped','panel_generated','panel_generate_blocked',
    'panel_regenerated','credit_depleted','first_gen_preview_shown',
    'credit_pack_purchased','subscription_purchased',
    'nav_continue_story_tapped','story_created',
    'share_completed','share_tapped','download_completed',
    'ad_rewarded_paid','ad_interstitial_shown'
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
        keys = exp_user_property_keys(exp_id)
        key_list = ", ".join(f"'{k}'" for k in keys)
        sql = f"""
WITH {cte(ss, se)},
exp_users AS (
  SELECT user_pseudo_id,
    (SELECT value.string_value FROM UNNEST(user_properties)
     WHERE key IN ({key_list}) LIMIT 1) AS variant
  FROM all_events
  WHERE event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1, 2
  HAVING variant IS NOT NULL
),
user_events AS (
  SELECT ue.variant, e.user_pseudo_id,
    MAX(IF(e.event_name = 'paywall_shown', 1, 0)) AS saw_paywall,
    MAX(IF(e.event_name IN ('paywall_purchase_success','subscription_purchased','credit_pack_purchased'), 1, 0)) AS converted
  FROM all_events e
  JOIN exp_users ue ON e.user_pseudo_id = ue.user_pseudo_id
  WHERE e.event_timestamp BETWEEN {start_us} AND {end_us}
  GROUP BY 1, 2
)
SELECT variant, SUM(saw_paywall) AS paywall,
  ROUND(SAFE_DIVIDE(SUM(converted), SUM(saw_paywall)) * 100, 1) AS conv_rate
FROM user_events WHERE saw_paywall = 1
GROUP BY variant ORDER BY variant
"""
        try:
            rows = q(sql)
            for row in rows:
                row["exp_id"] = exp_id
                row["exp_name"] = exp["name"]
            results.extend(rows)
        except Exception as exc:
            results.append({
                "exp_id": exp_id,
                "exp_name": exp["name"],
                "variant": "?",
                "paywall": 0,
                "conv_rate": 0,
                "error": str(exc)[:80],
            })
    return results


def parse_funnel(data):
    result = {
        "new_users": 0, "new_paywall": 0, "new_paid": 0,
        "new_cta": 0, "new_plan_sel": 0, "new_cancelled": 0, "new_failed": 0,
        "new_sub": 0, "new_pack": 0,
        "ret_users": 0, "ret_paywall": 0, "ret_paid": 0,
        "ret_cta": 0, "ret_plan_sel": 0, "ret_cancelled": 0, "ret_failed": 0,
        "ret_sub": 0, "ret_pack": 0,
    }
    for r in data:
        seg = r.get("segment", "")
        prefix = "new_" if seg == "new" else ("ret_" if seg == "returning" else None)
        if not prefix:
            continue
        result[f"{prefix}users"] = int(r.get("total_users", 0) or 0)
        result[f"{prefix}paywall"] = int(r.get("paywall_users", 0) or 0)
        result[f"{prefix}paid"] = int(r.get("paid_users", 0) or 0)
        result[f"{prefix}cta"] = int(r.get("cta_tapped_users", 0) or 0)
        result[f"{prefix}plan_sel"] = int(r.get("plan_selected_users", 0) or 0)
        result[f"{prefix}cancelled"] = int(r.get("purchase_cancelled_users", 0) or 0)
        result[f"{prefix}failed"] = int(r.get("purchase_failed_users", 0) or 0)
        result[f"{prefix}sub"] = int(r.get("sub_users", 0) or 0)
        result[f"{prefix}pack"] = int(r.get("pack_users", 0) or 0)
    return result


def main():
    w = rolling_windows(TZ)
    now_us, h24, h48 = w["now_us"], w["h24_us"], w["h48_us"]
    h168, h192 = w["h168_us"], w["h192_us"]
    ss, se = w["suffix_start"], w["suffix_end"]
    sws, swe = w["suffix_week_start"], w["suffix_week_end"]
    display_date, display_time, tz_label = w["display_date"], w["display_time"], w["tz_label"]

    print(f"=== Mangii Daily Report — {display_date} ===\n")

    g = q_growth(h24, now_us, ss, se)
    gd = q_growth(h48, h24, ss, se)
    gw = q_growth(h192, h168, sws, swe)
    seg = {r["segment"]: int(r["users"]) for r in g}
    segd = {r["segment"]: int(r["users"]) for r in gd}
    segw = {r["segment"]: int(r["users"]) for r in gw}
    new_users = seg.get("new", 0)
    returning = seg.get("returning", 0)

    sources = q_source_new_users(h24, now_us, ss, se)
    platforms = q_platform_new_users(h24, now_us, ss, se)
    countries_new = q_countries_new_users(h24, now_us, ss, se)

    act_rows = q_activation_depth(h24, now_us, ss, se)
    act = act_rows[0] if act_rows else {}
    gen0 = int(act.get("gen0", 0) or 0)
    gen1 = int(act.get("gen1", 0) or 0)
    gen2_4 = int(act.get("gen2_4", 0) or 0)
    gen5 = int(act.get("gen5_plus", 0) or 0)
    gen1_plus = int(act.get("gen1_plus", 0) or 0)
    gen2_plus = int(act.get("gen2_plus", 0) or 0)
    act_new = int(act.get("new_users", 0) or 0) or new_users
    activation_rate = safe_rate(gen1_plus, act_new)
    one_to_two = safe_rate(gen2_plus, gen1_plus)

    f = parse_funnel(q_monetization_funnel(h24, now_us, ss, se))
    fd = parse_funnel(q_monetization_funnel(h48, h24, ss, se))
    fw = parse_funnel(q_monetization_funnel(h192, h168, sws, swe))

    new_paid_rate = safe_rate(f["new_paid"], f["new_paywall"])
    ret_paid_rate = safe_rate(f["ret_paid"], f["ret_paywall"])
    total_paywall = f["new_paywall"] + f["ret_paywall"]
    total_paid = f["new_paid"] + f["ret_paid"]
    overall_rate = safe_rate(total_paid, total_paywall)
    total_cta = f["new_cta"] + f["ret_cta"]
    total_plan = f["new_plan_sel"] + f["ret_plan_sel"]
    total_cancelled = f["new_cancelled"] + f["ret_cancelled"]
    total_failed = f["new_failed"] + f["ret_failed"]
    total_sub = f["new_sub"] + f["ret_sub"]
    total_pack = f["new_pack"] + f["ret_pack"]
    paid_d = fd["new_paid"] + fd["ret_paid"]
    paid_w = fw["new_paid"] + fw["ret_paid"]

    conv_by_country = q_conversion_by_country(h24, now_us, ss, se)
    glob = (q_conversion_global(h24, now_us, ss, se) or [{}])[0]
    g_shown = int(glob.get("paywall_shown", 0) or 0)
    g_conv = int(glob.get("converted", 0) or 0)

    p = q_product(h24, now_us, ss, se)
    pu = {r["event_name"]: int(r["users"]) for r in p}
    pe = {r["event_name"]: int(r["events"]) for r in p}

    exp_metrics = q_experiment_metrics(h24, now_us, ss, se)
    # Drop error-only rows from display unless only errors
    exp_ok = [r for r in exp_metrics if "error" not in r]
    exp_err = [r for r in exp_metrics if "error" in r]
    exp_breakdown = format_experiments(exp_ok if exp_ok else exp_metrics)
    if exp_err and exp_ok:
        exp_breakdown += f"\n    ⚠️ {len(exp_err)} experiment query error(s)"
    elif exp_err and not exp_ok:
        exp_breakdown = "    ⚠️ Experiment metrics failed:\n" + "\n".join(
            f"    {r['exp_id']}: {r.get('error','?')}" for r in exp_err
        )

    share_users = pu.get("share_completed", 0) or pu.get("share_tapped", 0)
    continue_users = pu.get("nav_continue_story_tapped", 0)
    story_users = pu.get("story_created", 0)

    report = f'''📊 Mangii Daily — {display_date} (rolling 24h as of {display_time} {tz_label})

👥 GROWTH
  New users: {new_users} (DoD {pct(new_users, segd.get('new', 0))} · WoW {pct(new_users, segw.get('new', 0))})
  Returning: {returning}
  Source: {format_source_split(sources)}
  📱 Platform (new): {format_platform_line(platforms)}

  📍 New Users by Country (Top 10):
{format_country_lines(countries_new)}

🔁 ACTIVATION (new users → gen depth)
  New: {act_new} · 0-gen: {gen0} ({safe_rate(gen0, act_new)}%) · 1-gen: {gen1} · 2–4: {gen2_4} · 5+: {gen5}
  Activated (≥1 gen): {gen1_plus} ({activation_rate}%) · 1→2+: {gen2_plus}/{gen1_plus} ({one_to_two}%)

💰 MONETIZATION
  📊 Funnel:
    New users: {f['new_users']} → paywall {f['new_paywall']} → paid {f['new_paid']} ({new_paid_rate}%) {get_conversion_emoji(new_paid_rate)}
    Returning: {f['ret_users']} → paywall {f['ret_paywall']} → paid {f['ret_paid']} ({ret_paid_rate}%) {get_conversion_emoji(ret_paid_rate)}

  Overall: {total_paywall} paywall → {total_paid} paid ({overall_rate}%)
  Sub purchased: {total_sub} · Credit packs: {total_pack}
  CTA tapped: {total_cta} · Plan selected: {total_plan} · Cancelled: {total_cancelled} · Failed: {total_failed}
  Paid DoD {pct(total_paid, paid_d)} · WoW {pct(total_paid, paid_w)}

  📍 Conversion by Country (Top 10; TOTAL=global):
{format_country_conversion(conv_by_country, g_shown, g_conv)}

🧪 EXPERIMENTS (B=Baseline | users/conv%)
{exp_breakdown}

🎨 PRODUCT
  Panels generated: {pu.get('panel_generated', 0)} users ({pe.get('panel_generated', 0)} panels)
  Generate tapped: {pu.get('panel_generate_tapped', 0)} users
  Blocked (no credits): {pu.get('panel_generate_blocked', 0)} users
  Credits depleted: {pu.get('credit_depleted', 0)} users
  Regenerated: {pu.get('panel_regenerated', 0)} users
  First-gen preview: {pu.get('first_gen_preview_shown', 0)} users
  Continue story: {continue_users} · Story created: {story_users} · Share: {share_users}
  Ads: rewarded {pu.get('ad_rewarded_paid', 0)} · interstitial {pu.get('ad_interstitial_shown', 0)}'''

    save_report(BASE, report, REPORT_PATH, display_date)
    tg = send_telegram(report, DEFAULT_BOT_TOKEN, DEFAULT_CHAT_ID)
    print(report)
    print("TELEGRAM_SENT_OK")
    print(json.dumps(tg))

    if exp_ok:
        heatmap_script = PROJECT_ROOT / "scripts" / "app_experiment_heatmap.py"
        heatmap_output = PROJECT_ROOT / "reports" / "mangii_experiments.png"
        if heatmap_script.exists():
            subprocess.run(
                ["python3", str(heatmap_script), "Mangii", PROJECT_ID, DATASET_ID, str(LOGO_PATH)],
                capture_output=True,
            )
            if heatmap_output.exists():
                subprocess.run(
                    [
                        "curl", "-s", "-X", "POST",
                        f"https://api.telegram.org/bot{DEFAULT_BOT_TOKEN}/sendPhoto",
                        "-F", f"chat_id={DEFAULT_CHAT_ID}",
                        "-F", f"photo=@{heatmap_output}",
                        "-F", "caption=🧪 Mangii Experiments (24h)",
                    ],
                    capture_output=True,
                    text=True,
                )
                print("HEATMAP_SENT")


if __name__ == "__main__":
    main()
