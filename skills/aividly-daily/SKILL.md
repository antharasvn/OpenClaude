# AIVidly Daily Report — Agent Skill

> **Canonical runner (2026-07-12):** cron uses deterministic `scripts/aividly_daily_runner.py` (not this prompt). Keep this skill as the metric/spec reference. Only use this skill if the Python runner is unavailable.

You are an automated reporting agent. A cron fires you every day at 3 AM ET. Follow every step below exactly. Do not skip steps. Do not improvise queries. Each section is independent — if one fails, mark it with a warning and continue.

**CRITICAL EXECUTION RULES:**
- You MUST actually execute every bash block and curl command. Do NOT simulate, describe, or say "would send". RUN IT.
- The Telegram delivery in Step 9 is MANDATORY. You must run the curl command to send the message. Saying "Would send to" is a FAILURE.
- All bash blocks are meant to be executed via your Bash/shell tool, not described as pseudocode.

**IMPORTANT: All BQ queries use ROLLING 24-HOUR WINDOWS, not calendar days.**
- "Today" = last 24 hours from NOW
- "Yesterday" = 24-48 hours ago (same time window, one day back)
- "Last week" = 168-192 hours ago (same time window, 7 days back)
- This ensures apples-to-apples comparison regardless of when the report runs.
- BQ filter: `event_timestamp BETWEEN (now - 24h) AND now` in microseconds
- Compare DoD (day-over-day) and WoW (week-over-week) using matching time windows

---

## Step 1: Time window setup

```bash
NOW_EPOCH=$(TZ="America/New_York" date +%s)
NOW_US=$((NOW_EPOCH * 1000000))
H24_AGO_US=$(( (NOW_EPOCH - 86400) * 1000000 ))
H48_AGO_US=$(( (NOW_EPOCH - 172800) * 1000000 ))
H168_AGO_US=$(( (NOW_EPOCH - 604800) * 1000000 ))
H192_AGO_US=$(( (NOW_EPOCH - 691200) * 1000000 ))

DISPLAY_DATE=$(TZ="America/New_York" date +%Y-%m-%d)
DISPLAY_TIME=$(TZ="America/New_York" date +%H:%M)

# Table suffix range (cover enough calendar days for rolling windows)
SUFFIX_START=$(TZ="America/New_York" date -v-2d +%Y%m%d 2>/dev/null || TZ="America/New_York" date -d "2 days ago" +%Y%m%d)
SUFFIX_END=$(TZ="America/New_York" date +%Y%m%d)
SUFFIX_WEEK_START=$(TZ="America/New_York" date -v-9d +%Y%m%d 2>/dev/null || TZ="America/New_York" date -d "9 days ago" +%Y%m%d)
SUFFIX_WEEK_END=$(TZ="America/New_York" date -v-6d +%Y%m%d 2>/dev/null || TZ="America/New_York" date -d "6 days ago" +%Y%m%d)
```

---

## Step 2: Lockfile check (idempotency)

1. Check if `data/aividly/locks/daily-${DISPLAY_DATE}.lock` exists.
2. If yes: print "Daily report for ${DISPLAY_DATE} already sent. Exiting." and **stop**.
3. If no: create it:

```bash
mkdir -p data/aividly/locks data/aividly/daily-reports
echo "started=$(date -u +%Y-%m-%dT%H:%M:%SZ)" > data/aividly/locks/daily-${DISPLAY_DATE}.lock
```

---

## Step 3: Event source CTE

All queries use this CTE pattern. Include both daily and intraday tables, then filter by `event_timestamp`:

```sql
WITH all_events AS (
  SELECT * FROM `aividly-8a1c3.analytics_510101525.events_*`
  WHERE _TABLE_SUFFIX BETWEEN '{SUFFIX_START}' AND '{SUFFIX_END}'
  UNION ALL
  SELECT * FROM `aividly-8a1c3.analytics_510101525.events_intraday_*`
  WHERE _TABLE_SUFFIX BETWEEN '{SUFFIX_START}' AND '{SUFFIX_END}'
)
```

- **Last 24h:** `WHERE event_timestamp BETWEEN {H24_AGO_US} AND {NOW_US}`
- **Yesterday (DoD):** `WHERE event_timestamp BETWEEN {H48_AGO_US} AND {H24_AGO_US}`
- **Last week (WoW):** Use `SUFFIX_WEEK_START`/`SUFFIX_WEEK_END` in CTE, `WHERE event_timestamp BETWEEN {H192_AGO_US} AND {H168_AGO_US}`

**Apply this to ALL queries in Step 4.** Never filter by `_TABLE_SUFFIX` alone.

---

## BigQuery Robustness Rule (mandatory)

When running BigQuery queries:
- Prefer `--format=json` and parse JSON output, not loose text parsing
- If a query job reaches `DONE` but the wrapper/parser fails, treat it as an **infra/parser bug**, not a business metric of zero
- Do **not** silently replace failed metrics with zero unless the SQL itself returned zero rows successfully
- If parsing fails, label the metric block as `⚠️ BigQuery result parsing failed` and continue the rest of the report
- Never confuse `query failed` with `metric = 0`

## Step 4: Run BigQuery queries

Project: `aividly-8a1c3` | Dataset: `analytics_510101525`

Run each query via `bq query --use_legacy_sql=false --project_id=aividly-8a1c3 --format=json '<SQL>'`

Run each for **3 windows**: last 24h, 24-48h ago (DoD), 168-192h ago (WoW).

### Q1 — GROWTH

```sql
WITH all_events AS (
  SELECT * FROM `aividly-8a1c3.analytics_510101525.events_*` WHERE _TABLE_SUFFIX BETWEEN '{SUFFIX_START}' AND '{SUFFIX_END}'
  UNION ALL
  SELECT * FROM `aividly-8a1c3.analytics_510101525.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{SUFFIX_START}' AND '{SUFFIX_END}'
)
SELECT
  COUNT(DISTINCT user_pseudo_id) AS total_users,
  COUNTIF(event_name = 'first_open') AS new_users,
  COUNTIF(event_name = 'session_start') AS sessions
FROM all_events
WHERE event_timestamp BETWEEN {H24_AGO_US} AND {NOW_US}
```

### Q2 — TOP COUNTRIES

```sql
WITH all_events AS (
  SELECT * FROM `aividly-8a1c3.analytics_510101525.events_*` WHERE _TABLE_SUFFIX BETWEEN '{SUFFIX_START}' AND '{SUFFIX_END}'
  UNION ALL
  SELECT * FROM `aividly-8a1c3.analytics_510101525.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{SUFFIX_START}' AND '{SUFFIX_END}'
)
SELECT geo.country, COUNT(DISTINCT user_pseudo_id) AS users
FROM all_events
WHERE event_timestamp BETWEEN {H24_AGO_US} AND {NOW_US}
  AND event_name = 'first_open'
GROUP BY 1 ORDER BY users DESC LIMIT 5
```

### Q3 — ONBOARDING FUNNEL

```sql
WITH all_events AS (
  SELECT * FROM `aividly-8a1c3.analytics_510101525.events_*` WHERE _TABLE_SUFFIX BETWEEN '{SUFFIX_START}' AND '{SUFFIX_END}'
  UNION ALL
  SELECT * FROM `aividly-8a1c3.analytics_510101525.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{SUFFIX_START}' AND '{SUFFIX_END}'
)
SELECT
  COUNTIF(event_name = 'ftue_app_opened') AS ftue_opened,
  COUNTIF(event_name = 'ftue_welcome_shown') AS welcome_shown,
  COUNTIF(event_name = 'ftue_welcome_cta_tapped') AS welcome_cta_tapped,
  COUNTIF(event_name = 'ftue_intent_onboarding_started') AS intent_started,
  COUNTIF(event_name = 'ftue_intent_onboarding_completed') AS intent_completed,
  COUNTIF(event_name = 'onboarding_completed') AS onboarding_completed,
  COUNTIF(event_name = 'ftue_first_creation_completed') AS first_creation_completed
FROM all_events
WHERE event_timestamp BETWEEN {H24_AGO_US} AND {NOW_US}
```

### Q4 — VIDEO CREATION

```sql
WITH all_events AS (
  SELECT * FROM `aividly-8a1c3.analytics_510101525.events_*` WHERE _TABLE_SUFFIX BETWEEN '{SUFFIX_START}' AND '{SUFFIX_END}'
  UNION ALL
  SELECT * FROM `aividly-8a1c3.analytics_510101525.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{SUFFIX_START}' AND '{SUFFIX_END}'
)
SELECT
  COUNTIF(event_name = 'video_generation_started') AS gen_started,
  COUNTIF(event_name = 'video_generation_completed') AS gen_completed,
  COUNTIF(event_name = 'first_video_created') AS first_video,
  COUNTIF(event_name = 'preview_opened') AS preview_opened,
  COUNTIF(event_name = 'preview_dismissed') AS preview_dismissed,
  COUNTIF(event_name = 'first_export_completed') AS first_export,
  COUNTIF(event_name = 'video_auto_saved') AS auto_saved
FROM all_events
WHERE event_timestamp BETWEEN {H24_AGO_US} AND {NOW_US}
```

### Q5 — TOKEN ECONOMY

```sql
WITH all_events AS (
  SELECT * FROM `aividly-8a1c3.analytics_510101525.events_*` WHERE _TABLE_SUFFIX BETWEEN '{SUFFIX_START}' AND '{SUFFIX_END}'
  UNION ALL
  SELECT * FROM `aividly-8a1c3.analytics_510101525.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{SUFFIX_START}' AND '{SUFFIX_END}'
)
SELECT
  COUNTIF(event_name = 'starter_tokens_granted') AS starter_granted,
  COUNTIF(event_name = 'tokens_insufficient_shown') AS tokens_insufficient,
  COUNTIF(event_name = 'token_store_viewed') AS store_viewed,
  COUNTIF(event_name = 'tokens_path_selected') AS path_selected,
  COUNTIF(event_name = 'token_pack_selected') AS pack_selected,
  COUNTIF(event_name = 'token_pack_purchase_started') AS purchase_started,
  COUNTIF(event_name = 'token_pack_purchased') AS pack_purchased
FROM all_events
WHERE event_timestamp BETWEEN {H24_AGO_US} AND {NOW_US}
```

### Q6 — MONETIZATION (Paywall + Sub Gate)

```sql
WITH all_events AS (
  SELECT * FROM `aividly-8a1c3.analytics_510101525.events_*` WHERE _TABLE_SUFFIX BETWEEN '{SUFFIX_START}' AND '{SUFFIX_END}'
  UNION ALL
  SELECT * FROM `aividly-8a1c3.analytics_510101525.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{SUFFIX_START}' AND '{SUFFIX_END}'
)
SELECT
  COUNTIF(event_name = 'paywall_shown') AS paywall_shown,
  COUNTIF(event_name = 'subscription_gate_shown') AS sub_gate_shown,
  COUNTIF(event_name = 'subscription_gate_dismissed') AS sub_gate_dismissed,
  COUNTIF(event_name = 'subscription_gate_tokens_tap') AS sub_gate_tokens_tap,
  COUNTIF(event_name = 'subscription_gate_more_options_tap') AS sub_gate_more_options,
  COUNTIF(event_name = 'purchase') AS purchases,
  COUNTIF(event_name IN ('in_app_purchase', 'rc_initial_purchase')) AS iap_purchases
FROM all_events
WHERE event_timestamp BETWEEN {H24_AGO_US} AND {NOW_US}
```

### Q7 — SHARING / VIRAL

```sql
WITH all_events AS (
  SELECT * FROM `aividly-8a1c3.analytics_510101525.events_*` WHERE _TABLE_SUFFIX BETWEEN '{SUFFIX_START}' AND '{SUFFIX_END}'
  UNION ALL
  SELECT * FROM `aividly-8a1c3.analytics_510101525.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{SUFFIX_START}' AND '{SUFFIX_END}'
)
SELECT
  COUNTIF(event_name = 'preview_share_clicked') AS share_clicked,
  COUNTIF(event_name = 'preview_share_completed') AS share_completed,
  COUNTIF(event_name = 'share_funnel_completion') AS share_funnel,
  COUNTIF(event_name = 'content_shared') AS content_shared,
  COUNTIF(event_name = 'video_shared') AS video_shared,
  COUNTIF(event_name = 'celebration_variant_shown') AS celebrations
FROM all_events
WHERE event_timestamp BETWEEN {H24_AGO_US} AND {NOW_US}
```

### Q8 — TRENDING

```sql
WITH all_events AS (
  SELECT * FROM `aividly-8a1c3.analytics_510101525.events_*` WHERE _TABLE_SUFFIX BETWEEN '{SUFFIX_START}' AND '{SUFFIX_END}'
  UNION ALL
  SELECT * FROM `aividly-8a1c3.analytics_510101525.events_intraday_*` WHERE _TABLE_SUFFIX BETWEEN '{SUFFIX_START}' AND '{SUFFIX_END}'
)
SELECT
  COUNTIF(event_name = 'trending_topics_viewed') AS trending_viewed,
  COUNTIF(event_name = 'trending_topic_selected') AS trending_selected,
  COUNTIF(event_name = 'trend_used_for_video') AS trend_used
FROM all_events
WHERE event_timestamp BETWEEN {H24_AGO_US} AND {NOW_US}
```

---

## Astro Dependency Preflight (mandatory)

Before any Astro keyword lookup:

```bash
# Check network/DNS
if ! curl -Is --connect-timeout 5 https://api.astro.withfluffy.com >/dev/null 2>&1; then
  echo "⚠️ Astro DNS/network unavailable"
fi

# Ensure Astro desktop app is running
if command -v pgrep >/dev/null 2>&1; then
  if ! pgrep -f "Astro.app" >/dev/null 2>&1; then
    echo "Starting Astro..."
    open -a Astro >/dev/null 2>&1 || true
    sleep 10
  fi
fi

# If Astro looks hung, restart once
if command -v pgrep >/dev/null 2>&1 && pgrep -f "Astro.app" >/dev/null 2>&1; then
  if ! curl -Is --connect-timeout 5 https://api.astro.withfluffy.com >/dev/null 2>&1; then
    echo "Restarting Astro..."
    pkill -f "Astro.app" >/dev/null 2>&1 || true
    sleep 2
    open -a Astro >/dev/null 2>&1 || true
    sleep 12
  fi
fi
```

If Astro is unavailable after one restart, mark ASO section as:
- `⚠️ Astro infra unavailable`
- Continue the report without ASO data

## Step 5: ASO — Keyword Rankings

App ID: `6698894140`

```bash
curl -s --connect-timeout 10 "https://api.astro.withfluffy.com/api/v1/app/apple/6698894140/top-keywords?country=us&limit=25" \
  -H "x-api-key: sk-astro-998ef58e-ea5c-48db-a75c-13d9d8deb289"
```

Parse output for: total tracked, ranked, gainers, drops, top movers.

---

## Step 6: Compute derived metrics & deltas

Calculate for each window (today, yesterday, last week):

1. **Onboarding rate** = onboarding_completed / ftue_opened × 100
2. **First video rate** = first_video / new_users × 100
3. **Token exhaustion rate** = tokens_insufficient / sessions × 100
4. **Sub gate dismiss rate** = sub_gate_dismissed / sub_gate_shown × 100
5. **Share rate** = (share_completed + video_shared) / gen_completed × 100
6. **Token purchase rate** = pack_purchased / store_viewed × 100 (if store_viewed > 0)

Compute DoD% and WoW% deltas using: `((today - yesterday) / yesterday) × 100`

---

## Step 7: Format the report

Use this exact structure:

```
📊 AIVidly Daily Report — {DISPLAY_DATE} ({DISPLAY_TIME} ET)

👥 USERS (24h)
• Total: {total_users}
• New: {new_users} (DoD {dod}% · WoW {wow}%)
• Sessions: {sessions}

Top countries: {country1} {n1} · {country2} {n2} · {country3} {n3}

🎯 ONBOARDING FUNNEL
```
FTUE: {ftue_opened}
├─ Welcome CTA: {welcome_cta_tapped} ({rate}%)
├─ Intent completed: {intent_completed}
├─ Onboarding done: {onboarding_completed} ({onb_rate}%)
└─ First creation: {first_creation_completed}
```

🎥 VIDEO CREATION
• Started: {gen_started} → Completed: {gen_completed}
• Success rate: {success_rate}%
• First video: {first_video}
• Previews: {preview_opened} opened → {preview_dismissed} dismissed
• First export: {first_export}

🪙 TOKEN ECONOMY
• Starter granted: {starter_granted}
• Insufficient shown: {tokens_insufficient} ({exhaustion_rate}% of sessions) ⚠️
• Store viewed: {store_viewed} → Purchased: {pack_purchased}
• Token conversion: {token_conv}%

💰 MONETIZATION
Sub Gate:
• Shown: {sub_gate_shown} → Dismissed: {sub_gate_dismissed} ({dismiss_rate}%)
• Tokens tap: {sub_gate_tokens_tap} · More options: {sub_gate_more_options}

Purchases: {purchases} (DoD {dod}% · WoW {wow}%)

📤 SHARING
• Click: {share_clicked} → Complete: {share_completed}
• Videos shared: {video_shared}
• Share rate: {share_rate}% of completed videos

🔥 TRENDING
• Viewed: {trending_viewed} → Selected: {trending_selected} → Used: {trend_used}

📈 ASO — US (Astro)
Tracked: ~{total} · Ranked: {ranked}
🟢 Gainers: {gainers} · 🔴 Drops: {drops}
Top movers: {mover1}, {mover2}, {mover3}
Best rank: "{best_kw}" #{best_rank}

⚠️ Alerts
{list any concerns: high dismiss rate, low conversion, token exhaustion, etc.}
```

---

## Step 8: Save report to disk

```bash
mkdir -p data/aividly/daily-reports
cat > data/aividly/daily-reports/${DISPLAY_DATE}.md << 'REPORT_EOF'
{full report content}
REPORT_EOF
```

---

## Step 9: Deliver to AAA OS Telegram — MANDATORY

**YOU MUST EXECUTE THIS COMMAND.** Do NOT say "would send" or describe it. RUN IT.

```bash
REPORT='...'  # The formatted report text

AAA_BOT_TOKEN="8628864855:AAFWSgQCzUIGNtBK1dQk28rCJ7rqBo3v0zU"
AAA_CHAT_ID="-5201056067"

curl -s -X POST "https://api.telegram.org/bot${AAA_BOT_TOKEN}/sendMessage" \
  -H "Content-Type: application/json" \
  -d "{\"chat_id\": \"${AAA_CHAT_ID}\", \"text\": $(echo "$REPORT" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))"), \"parse_mode\": \"\"}"
```

Verify the response contains `"ok":true`. If it fails, log the error and continue.

---

## Step 10: Finalize lockfile

```bash
echo "completed=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> data/aividly/locks/daily-${DISPLAY_DATE}.lock
```

---

## Step 11: Output summary for cron announce

Condensed summary (under 200 words) for boss DM:

```
Key numbers: DAU {n}, New Users {n}, Videos Generated {n}, Token Exhaustion {n}%, Conversion {rate}.
Concerns: {list any red flags}
ASO movers: {top 3 keyword changes or "unavailable"}
```

---

## Error handling

| Failure | Action |
|---------|--------|
| BQ query fails | Mark section ⚠️, continue with other queries |
| Astro unavailable | Mark ASO section ⚠️, continue |
| Telegram send fails | Log error, still mark report as generated |
| Division by zero | Show "N/A" for that metric |

Each section is **independent**. One failure must never block other sections.
