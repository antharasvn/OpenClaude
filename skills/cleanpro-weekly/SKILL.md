# CleanPro Weekly Report — Agent Skill

You are an automated reporting agent. Fires every Monday at 3:30 AM ET. Follow every step exactly.

---

## Step 1: Compute date range (last Mon–Sun)

```bash
END_DATE=$(TZ="Asia/Saigon" date -v-1d +%Y%m%d 2>/dev/null || TZ="Asia/Saigon" date -d "yesterday" +%Y%m%d)
START_DATE=$(TZ="Asia/Saigon" date -v-7d +%Y%m%d 2>/dev/null || TZ="Asia/Saigon" date -d "7 days ago" +%Y%m%d)
PRIOR_END=$(TZ="Asia/Saigon" date -v-8d +%Y%m%d 2>/dev/null || TZ="Asia/Saigon" date -d "8 days ago" +%Y%m%d)
PRIOR_START=$(TZ="Asia/Saigon" date -v-14d +%Y%m%d 2>/dev/null || TZ="Asia/Saigon" date -d "14 days ago" +%Y%m%d)
WEEK_LABEL=$(TZ="Asia/Saigon" date -v-1d +"%Y-W%V" 2>/dev/null || TZ="Asia/Saigon" date -d "yesterday" +"%Y-W%V")
DISPLAY_START=$(echo "$START_DATE" | sed 's/\(....\)\(..\)\(..\)/\1-\2-\3/')
DISPLAY_END=$(echo "$END_DATE" | sed 's/\(....\)\(..\)\(..\)/\1-\2-\3/')
```

---

## Step 2: Lockfile check

Check `workspaces/c352342178/cleanpro/locks/weekly-${WEEK_LABEL}.lock`. If exists, stop. Otherwise create it.

---

## Step 3: GA4 freshness gate

```bash
bq query --use_legacy_sql=false --project_id=cleaner-app-e98f0 --format=json \
  'SELECT MAX(_TABLE_SUFFIX) AS latest_table FROM `cleaner-app-e98f0.analytics_269202926.events_*`'
```

If latest_table < END_DATE: wait 30 min, retry once. If still not ready, warn and stop.

---

## BigQuery Robustness Rule (mandatory)

When running BigQuery queries:
- Prefer `--format=json` and parse JSON output, not loose text parsing
- If a query job reaches `DONE` but the wrapper/parser fails, treat it as an **infra/parser bug**, not a business metric of zero
- Do **not** silently replace failed metrics with zero unless the SQL itself returned zero rows successfully
- If parsing fails, label the metric block as `⚠️ BigQuery result parsing failed` and continue the rest of the report
- Never confuse `query failed` with `metric = 0`

## Step 4: Run BigQuery queries

Project: `cleaner-app-e98f0` | Dataset: `analytics_269202926`

### Q1 — GROWTH: Current & prior week

```sql
WITH user_seg AS (
  SELECT user_pseudo_id, MAX(IF(event_name="first_open",1,0)) AS is_new
  FROM `cleaner-app-e98f0.analytics_269202926.events_*`
  WHERE _TABLE_SUFFIX BETWEEN "{START_DATE}" AND "{END_DATE}"
  GROUP BY 1
)
SELECT IF(is_new=1,"new","returning") AS segment, COUNT(*) AS users
FROM user_seg GROUP BY 1
```

Run same for PRIOR_START/PRIOR_END. Compute WoW deltas.

### Q1c — Best day of week

```sql
SELECT FORMAT_DATE('%A', PARSE_DATE('%Y%m%d', event_date)) AS day_of_week,
  COUNT(DISTINCT user_pseudo_id) AS users
FROM `cleaner-app-e98f0.analytics_269202926.events_*`
WHERE _TABLE_SUFFIX BETWEEN "{START_DATE}" AND "{END_DATE}"
GROUP BY 1 ORDER BY users DESC LIMIT 1
```

### Q2 — FULL ONBOARDING FUNNEL

```sql
WITH all_events AS (
  SELECT user_pseudo_id, event_name
  FROM `cleaner-app-e98f0.analytics_269202926.events_*`
  WHERE _TABLE_SUFFIX BETWEEN "{START_DATE}" AND "{END_DATE}"
)
SELECT
  COUNT(DISTINCT IF(event_name="first_open", user_pseudo_id, NULL)) AS first_open,
  COUNT(DISTINCT IF(event_name="onboarding_page_viewed", user_pseudo_id, NULL)) AS ob_viewed,
  COUNT(DISTINCT IF(event_name="onboarding_completed", user_pseudo_id, NULL)) AS ob_completed,
  COUNT(DISTINCT IF(event_name="onboarding_paywall_shown", user_pseudo_id, NULL)) AS pw_shown,
  COUNT(DISTINCT IF(event_name="onboarding_paywall_converted", user_pseudo_id, NULL)) AS pw_converted,
  COUNT(DISTINCT IF(event_name="rc_trial_start", user_pseudo_id, NULL)) AS trial_start,
  COUNT(DISTINCT IF(event_name="subscription_cancelled", user_pseudo_id, NULL)) AS sub_cancelled
FROM all_events
```

### Q3 — PRODUCT ENGAGEMENT

```sql
SELECT event_name, COUNT(DISTINCT user_pseudo_id) AS users, COUNT(*) AS events
FROM `cleaner-app-e98f0.analytics_269202926.events_*`
WHERE _TABLE_SUFFIX BETWEEN "{START_DATE}" AND "{END_DATE}"
  AND event_name IN ("scan_completed","first_scan_complete","clean_completed","first_delete_complete",
    "scan_v2_start","scan_v2_complete","proof_of_value_started","proof_of_value_complete")
GROUP BY 1 ORDER BY users DESC
```

### Q5 — COUNTRY PERFORMANCE (top 10)

```sql
SELECT geo.country, COUNT(DISTINCT user_pseudo_id) AS users,
  COUNT(DISTINCT IF(event_name="onboarding_paywall_converted", user_pseudo_id, NULL)) AS converted,
  ROUND(SAFE_DIVIDE(
    COUNT(DISTINCT IF(event_name="onboarding_paywall_converted", user_pseudo_id, NULL)),
    COUNT(DISTINCT user_pseudo_id)
  ) * 100, 1) AS conv_pct
FROM `cleaner-app-e98f0.analytics_269202926.events_*`
WHERE _TABLE_SUFFIX BETWEEN "{START_DATE}" AND "{END_DATE}"
GROUP BY 1 ORDER BY users DESC LIMIT 10
```

### Q6 — DUAL PAYWALL BREAKDOWN

```sql
SELECT event_name, COUNT(DISTINCT user_pseudo_id) AS users
FROM `cleaner-app-e98f0.analytics_269202926.events_*`
WHERE _TABLE_SUFFIX BETWEEN "{START_DATE}" AND "{END_DATE}"
  AND event_name IN (
    "onboarding_paywall_shown","onboarding_paywall_converted","onboarding_paywall_dismissed",
    "cleanpro_paywall_shown","cleanpro_paywall_purchase_tapped","cleanpro_paywall_closed",
    "rc_trial_start","rc_initial_purchase","purchase","in_app_purchase"
  )
GROUP BY 1 ORDER BY users DESC
```

---

## Step 5: Crashlytics (7-day)

Check crashes for `cleaner-app-e98f0` / `com.inverted.cleanerApp`. Same approach as daily.

---

## Step 6: ASO — Full 7-Day Keyword Analysis

Astro MCP app ID `1561471269`, Appeeky fallback with same API key.
Save snapshot, compare to 7-day-ago snapshot, full keyword table, top movers, KEI opportunities.

---

## Step 7: Experiment suggestion

```bash
claude -p "You are a growth strategist for CleanPro (phone cleaner app with hard paywall). Propose ONE A/B experiment targeting the weakest metric. Format: Hypothesis/Test/Success metric/Expected outcome. Data: ..."
```

---

## Step 8: AI Narrative

```bash
claude -p "You are an analytics narrator for CleanPro. Write 3-4 sentences, max 80 words. Data: ..."
```

---

## Step 9: Format and output report

```
📊 CleanPro Weekly — {WEEK_LABEL}

💡 SYNTHESIS
  {narrative}

📈 GROWTH TRENDS (7d vs prior 7d)
  New users: {curr_new} ({delta})
  Retention (returning/total): {pct}%
  Best day: {day} with {users} users

💰 CONVERSION FUNNEL
  First open → Onboarding complete: {pct}%
  Onboarding → Paywall shown: {pct}%
  Paywall shown → Converted: {pct}% ← MAIN METRIC
  Onboarding paywall: {shown} → {converted}
  In-app paywall: {shown} → {converted}
  Trials: {count} | Purchases: {count}

🌍 COUNTRY PERFORMANCE (top 10)
  {table}

🧹 PRODUCT HEALTH
  Scans: {users} users ({events} total)
  Cleans: {users} users
  First scan completion: {users}
  First delete completion: {users}
  Proof of value started: {users} → completed: {users}

🔴 ENGINEERING (7-day)
  Total crashes: {count}
  Top 3: ...

📱 ASO — 7-DAY KEYWORD REPORT
  {full keyword analysis}

🧪 THIS WEEK'S EXPERIMENT
  {experiment}
```

### AAA OS Telegram Delivery

```bash
AAA_BOT_TOKEN="8628864855:AAFWSgQCzUIGNtBK1dQk28rCJ7rqBo3v0zU"
AAA_CHAT_ID="-5201056067"

curl -s -X POST "https://api.telegram.org/bot${AAA_BOT_TOKEN}/sendMessage" \
  -H "Content-Type: application/json" \
  -d "{\"chat_id\": \"${AAA_CHAT_ID}\", \"text\": $(echo "$REPORT" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))"), \"parse_mode\": \"\"}" > /dev/null 2>&1
```

---

## Step 10-12: Update baselines, git archive, finalize lockfile

Same as daily but weekly paths:
- Baselines: `data/cleanpro/baselines.json`
- Reports: `/Users/antharas/Projects/CleanPro/source/dev/reports/weekly/`
- Lock: `data/cleanpro/locks/weekly-${WEEK_LABEL}.lock`

Each section is independent. One failure must never block others.
