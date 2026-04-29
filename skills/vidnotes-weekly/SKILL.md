# VidNotes Weekly Report — Agent Skill

You are an automated reporting agent. A cron fires you every Monday at 3:30 AM ET. Follow every step below exactly. Do not skip steps. Do not improvise queries. Each section is independent — if one fails, mark it with a warning and continue.

---

## Step 1: Compute date range (last Mon–Sun)

```bash
END_DATE=$(TZ="America/New_York" date -v-1d +%Y%m%d 2>/dev/null || TZ="America/New_York" date -d "yesterday" +%Y%m%d)
START_DATE=$(TZ="America/New_York" date -v-7d +%Y%m%d 2>/dev/null || TZ="America/New_York" date -d "7 days ago" +%Y%m%d)
PRIOR_END=$(TZ="America/New_York" date -v-8d +%Y%m%d 2>/dev/null || TZ="America/New_York" date -d "8 days ago" +%Y%m%d)
PRIOR_START=$(TZ="America/New_York" date -v-14d +%Y%m%d 2>/dev/null || TZ="America/New_York" date -d "14 days ago" +%Y%m%d)
WEEK_LABEL=$(TZ="America/New_York" date -v-1d +"%Y-W%V" 2>/dev/null || TZ="America/New_York" date -d "yesterday" +"%Y-W%V")
DISPLAY_START=$(echo "$START_DATE" | sed 's/\(....\)\(..\)\(..\)/\1-\2-\3/')
DISPLAY_END=$(echo "$END_DATE" | sed 's/\(....\)\(..\)\(..\)/\1-\2-\3/')
```

Store all variables for use in subsequent steps:
- `START_DATE` / `END_DATE` — current week range (YYYYMMDD)
- `PRIOR_START` / `PRIOR_END` — prior week range (YYYYMMDD)
- `WEEK_LABEL` — e.g. `2026-W12`
- `DISPLAY_START` / `DISPLAY_END` — human-readable dates

---

## Step 2: Lockfile check (idempotency)

1. Check if the file `workspaces/c352342178/vidnotes/locks/weekly-${WEEK_LABEL}.lock` exists.
2. If it exists, print `"Weekly report for ${WEEK_LABEL} already sent. Exiting."` and **stop immediately**. Do no further work.
3. If it does not exist, create the directory and lockfile now, before any other work:

```bash
mkdir -p workspaces/c352342178/vidnotes/locks
echo "started=$(date -u +%Y-%m-%dT%H:%M:%SZ)" > workspaces/c352342178/vidnotes/locks/weekly-${WEEK_LABEL}.lock
```

The lockfile is never deleted. It prevents duplicate runs.

---

## Step 3: GA4 freshness gate

Run this BigQuery query to check whether the final day's GA4 export has landed:

```bash
bq query --use_legacy_sql=false --project_id=vidnotes-7864d --format=json \
  'SELECT MAX(_TABLE_SUFFIX) AS latest_table FROM `vidnotes-7864d.analytics_508326759.events_*`'
```

Parse `latest_table` from the JSON output.

- If `latest_table >= END_DATE`: proceed to Step 4.
- If `latest_table < END_DATE`: wait 30 minutes (`sleep 1800`), then retry the same query exactly once.
  - If still `latest_table < END_DATE` after retry: output the message `"⚠️ VidNotes Weekly — ${WEEK_LABEL}: GA4 export not ready (latest: ${latest_table}, need: ${END_DATE}). Will retry manually."` (OpenClaude delivers it) and **stop**. Do not delete the lockfile.

---

## BigQuery Robustness Rule (mandatory)

When running BigQuery queries:
- Prefer `--format=json` and parse JSON output, not loose text parsing
- If a query job reaches `DONE` but the wrapper/parser fails, treat it as an **infra/parser bug**, not a business metric of zero
- Do **not** silently replace failed metrics with zero unless the SQL itself returned zero rows successfully
- If parsing fails, label the metric block as `⚠️ BigQuery result parsing failed` and continue the rest of the report
- Never confuse `query failed` with `metric = 0`

## Step 4: Run BigQuery queries

BigQuery project: `vidnotes-7864d`
Dataset: `analytics_508326759`

Run each query via:
```bash
bq query --use_legacy_sql=false --project_id=vidnotes-7864d --format=json '<SQL>'
```

**IMPORTANT: No version filter on any query.** These queries count ALL app versions.

If any individual query fails, mark that section with `⚠️ {Section} data unavailable — query error` in the final report and continue with the remaining queries.

### Q1 — GROWTH: Current week user segments

```sql
WITH user_seg AS (
  SELECT user_pseudo_id, MAX(IF(event_name="first_open",1,0)) AS is_new
  FROM `vidnotes-7864d.analytics_508326759.events_*`
  WHERE _TABLE_SUFFIX BETWEEN "{START_DATE}" AND "{END_DATE}"
  GROUP BY 1
)
SELECT IF(is_new=1,"new","returning") AS segment, COUNT(*) AS users
FROM user_seg GROUP BY 1
```

Extract:
- `curr_new_users` — count where segment = "new"
- `curr_returning_users` — count where segment = "returning"
- `curr_total_users` = `curr_new_users + curr_returning_users`
- `curr_retention_pct` = `curr_returning_users / curr_total_users * 100`, rounded to 1 decimal

### Q1b — GROWTH: Prior week user segments

Run the **same query** but with `PRIOR_START` and `PRIOR_END`:

```sql
WITH user_seg AS (
  SELECT user_pseudo_id, MAX(IF(event_name="first_open",1,0)) AS is_new
  FROM `vidnotes-7864d.analytics_508326759.events_*`
  WHERE _TABLE_SUFFIX BETWEEN "{PRIOR_START}" AND "{PRIOR_END}"
  GROUP BY 1
)
SELECT IF(is_new=1,"new","returning") AS segment, COUNT(*) AS users
FROM user_seg GROUP BY 1
```

Extract:
- `prior_new_users` — count where segment = "new"
- `prior_returning_users` — count where segment = "returning"

Compute week-over-week deltas:
- `new_users_delta_pct` = `((curr_new_users - prior_new_users) / prior_new_users) * 100`, rounded to 0 decimals. Format as `+N%` or `-N%`.
- `returning_delta_pct` = same formula for returning users.

### Q1c — GROWTH: Best day of week

```sql
SELECT
  FORMAT_DATE('%A', PARSE_DATE('%Y%m%d', event_date)) AS day_of_week,
  COUNT(DISTINCT user_pseudo_id) AS users
FROM `vidnotes-7864d.analytics_508326759.events_*`
WHERE _TABLE_SUFFIX BETWEEN "{START_DATE}" AND "{END_DATE}"
GROUP BY 1
ORDER BY users DESC
LIMIT 1
```

Extract:
- `best_day` — day name
- `best_day_users` — user count

### Q2 — FULL ONBOARDING FUNNEL

**Note: native paywall events.** As of v1.x the app uses a native StoreKit/RevenueCat paywall (Superwall is deprecated). Paywall views fire `paywall_viewed` (in-app gates) and `onboarding_paywall_viewed` (onboarding flow). Conversions fire the canonical Firebase `purchase` event (also `onboarding_purchase_completed` inside onboarding — these are a subset of `purchase` for distinct-user counts). Do NOT use `superwall_conversion` — it never fires.

```sql
WITH user_seg AS (
  SELECT user_pseudo_id, MAX(IF(event_name="first_open",1,0)) AS is_new
  FROM `vidnotes-7864d.analytics_508326759.events_*`
  WHERE _TABLE_SUFFIX BETWEEN "{START_DATE}" AND "{END_DATE}"
  GROUP BY 1
),
all_events AS (
  SELECT user_pseudo_id, event_name,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = "action") AS action,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = "product_id") AS product_id
  FROM `vidnotes-7864d.analytics_508326759.events_*`
  WHERE _TABLE_SUFFIX BETWEEN "{START_DATE}" AND "{END_DATE}"
)
SELECT
  COUNT(DISTINCT us.user_pseudo_id) AS users,
  COUNT(DISTINCT IF(e.event_name="onboarding_start", e.user_pseudo_id, NULL)) AS ob_started,
  COUNT(DISTINCT IF(e.event_name="onboarding_complete", e.user_pseudo_id, NULL)) AS ob_completed,
  COUNT(DISTINCT IF(e.event_name IN ("paywall_viewed","onboarding_paywall_viewed"), e.user_pseudo_id, NULL)) AS pw_shown,
  COUNT(DISTINCT IF(e.event_name IN ("purchase","onboarding_purchase_completed"), e.user_pseudo_id, NULL)) AS pw_converted,
  COUNT(DISTINCT IF(e.event_name="trial_start", e.user_pseudo_id, NULL)) AS trial_start,
  COUNT(DISTINCT IF(e.event_name="subscription_cancelled", e.user_pseudo_id, NULL)) AS sub_cancelled,
  COUNT(DISTINCT IF(e.event_name="purchase_cancelled", e.user_pseudo_id, NULL)) AS purchase_cancelled,
  COUNT(DISTINCT IF(e.event_name="purchase_failed", e.user_pseudo_id, NULL)) AS purchase_failed
FROM user_seg us
JOIN all_events e ON us.user_pseudo_id = e.user_pseudo_id
```

Extract and compute funnel rates:
- `first_open_to_ob_start` = `ob_started / users * 100`, rounded to 1 decimal
- `ob_start_to_complete` = `ob_completed / ob_started * 100`, rounded to 1 decimal
- `ob_to_pw_shown` = `pw_shown / ob_completed * 100`, rounded to 1 decimal
- `pw_shown_to_converted` = `pw_converted / pw_shown * 100` — **this is the MAIN METRIC** (native paywall purchases over all paywall views; `purchase` covers both direct subs and trial-with-payment, `onboarding_purchase_completed` is a subset)
- `trial_start`, `sub_cancelled`, `purchase_cancelled`, `purchase_failed` for display

### Q4 — FAILURE BREAKDOWN

```sql
SELECT
  (SELECT value.string_value FROM UNNEST(event_params) WHERE key = "error_type") AS error_type,
  COUNT(DISTINCT user_pseudo_id) AS users,
  COUNT(*) AS events
FROM `vidnotes-7864d.analytics_508326759.events_*`
WHERE _TABLE_SUFFIX BETWEEN "{START_DATE}" AND "{END_DATE}"
  AND event_name = "onboarding_transcription_failed"
GROUP BY 1
ORDER BY events DESC
LIMIT 5
```

Extract a list of `{error_type}: {users} users ({events} events)` for each row.

### Q3 — TRANSCRIPTION SUCCESS

```sql
SELECT
  COUNT(DISTINCT IF(event_name="transcription_start", user_pseudo_id, NULL)) AS started,
  COUNT(DISTINCT IF(event_name="transcription_complete", user_pseudo_id, NULL)) AS completed,
  ROUND(SAFE_DIVIDE(
    COUNT(DISTINCT IF(event_name="transcription_complete", user_pseudo_id, NULL)),
    COUNT(DISTINCT IF(event_name="transcription_start", user_pseudo_id, NULL))
  ) * 100, 1) AS success_pct
FROM `vidnotes-7864d.analytics_508326759.events_*`
WHERE _TABLE_SUFFIX BETWEEN "{START_DATE}" AND "{END_DATE}"
  AND event_name IN ("transcription_start", "transcription_complete")
```

Extract:
- `transcription_success_pct` — the `success_pct` value

### Q5 — COUNTRY PERFORMANCE (top 10)

```sql
SELECT
  geo.country,
  COUNT(DISTINCT user_pseudo_id) AS users,
  COUNT(DISTINCT IF(event_name="superwall_conversion", user_pseudo_id, NULL)) AS purchased,
  ROUND(SAFE_DIVIDE(
    COUNT(DISTINCT IF(event_name="superwall_conversion", user_pseudo_id, NULL)),
    COUNT(DISTINCT user_pseudo_id)
  ) * 100, 1) AS overall_conv_pct
FROM `vidnotes-7864d.analytics_508326759.events_*`
WHERE _TABLE_SUFFIX BETWEEN "{START_DATE}" AND "{END_DATE}"
GROUP BY 1
ORDER BY users DESC
LIMIT 10
```

Extract:
- A table of `country`, `users`, `overall_conv_pct` for 10 rows.
- Compute `avg_conv_pct` = average of all rows' `overall_conv_pct`.
- For each row, compute `vs_avg` = `overall_conv_pct - avg_conv_pct`, formatted as `+N.N` or `-N.N`.

### Q6 — PAYWALL VARIANTS

```sql
SELECT
  event_name,
  (SELECT value.string_value FROM UNNEST(event_params) WHERE key = "paywall_version") AS paywall_version,
  COUNT(DISTINCT user_pseudo_id) AS users
FROM `vidnotes-7864d.analytics_508326759.events_*`
WHERE _TABLE_SUFFIX BETWEEN "{START_DATE}" AND "{END_DATE}"
  AND event_name IN ("paywall_viewed","superwall_conversion")
GROUP BY 1, 2
ORDER BY users DESC
```

Extract:
- For each `paywall_version`, pair the `paywall_viewed` user count (shown) with the `superwall_conversion` user count (converted).
- Compute conversion rate per variant: `converted / shown * 100`, rounded to 1 decimal.

### Q8 — AI FEATURE ENGAGEMENT

```sql
SELECT
  event_name,
  COUNT(DISTINCT user_pseudo_id) AS users,
  COUNT(*) AS events
FROM `vidnotes-7864d.analytics_508326759.events_*`
WHERE _TABLE_SUFFIX BETWEEN "{START_DATE}" AND "{END_DATE}"
  AND event_name IN ("ai_summary_generated","flashcard_created","content_export","export_initiated")
GROUP BY 1
ORDER BY users DESC
```

Extract user counts:
- `ai_summary_users` — users for "ai_summary_generated"
- `flashcard_users` — users for "flashcard_created"
- `export_users` — users for "content_export" or "export_initiated" (sum both)

### Q9 — VIDEO IMPORT SOURCES

```sql
SELECT
  (SELECT value.string_value FROM UNNEST(event_params) WHERE key = "source") AS source,
  COUNT(DISTINCT user_pseudo_id) AS users,
  COUNT(*) AS imports
FROM `vidnotes-7864d.analytics_508326759.events_*`
WHERE _TABLE_SUFFIX BETWEEN "{START_DATE}" AND "{END_DATE}"
  AND event_name = "video_import"
GROUP BY 1
ORDER BY imports DESC
```

Extract a list of `{source}: {users} users, {imports} imports` for each row.

---

## Step 5: Firebase Crashlytics (7-day)

Check for crash data for app `com.karniej.VidNotes` covering the 7-day window.

**Option A — Firebase MCP tools (preferred):**
If `crashlytics_get_report` and `crashlytics_list_events` MCP tools are available, use them:
1. Call `crashlytics_get_report` for the VidNotes app to get the week's crash summary.
2. Call `crashlytics_list_events` to list recent crash events within the date range.
3. Count total crashes, identify new issues (first seen during this week).

**Option B — Firebase Crashlytics REST API (fallback):**
If MCP tools are not available, use the Firebase Crashlytics REST API:
```bash
curl -s -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://firebasecrashlytics.googleapis.com/v1beta1/projects/vidnotes-7864d/apps/com.karniej.VidNotes/issues?filter=firstSeen>=${START_DATE}"
```

If both options fail: use `"⚠️ Crashlytics unavailable — check Firebase MCP config"` for the ENGINEERING section.

Extract:
- `total_crashes` — total crash events for the week
- `new_issues` — number of issues first seen this week
- `top_3_crashes` — list of top 3 crash titles with event counts

Load `workspaces/c352342178/vidnotes/baselines.json` and compare `total_crashes` against the prior week's value if available. Compute `crash_delta` formatted as `+N` or `-N` vs prior week.

---

## Step 6: ASO — Full 7-Day Keyword Analysis

## Astro Dependency Preflight (mandatory for any Astro keyword step)

Before any Astro keyword lookup:

```bash
# 1) Ensure network/DNS is healthy enough for Astro API
if ! curl -Is https://api.astro.withfluffy.com >/dev/null 2>&1; then
  echo "⚠️ Astro DNS/network unavailable"
fi

# 2) Ensure Astro desktop app is running when the skill uses Astro MCP
if command -v pgrep >/dev/null 2>&1; then
  if ! pgrep -f "Astro.app" >/dev/null 2>&1; then
    echo "Starting Astro..."
    open -a Astro >/dev/null 2>&1 || true
    sleep 10
  fi
fi

# 3) If Astro looks hung, restart it once
if command -v pgrep >/dev/null 2>&1 && pgrep -f "Astro.app" >/dev/null 2>&1; then
  if ! curl -Is https://api.astro.withfluffy.com >/dev/null 2>&1; then
    echo "Restarting Astro..."
    pkill -f "Astro.app" >/dev/null 2>&1 || true
    sleep 2
    open -a Astro >/dev/null 2>&1 || true
    sleep 12
  fi
fi
```

If Astro is still unavailable after one restart, mark the ASO section as:
- `⚠️ Astro infra unavailable (DNS/startup/unresponsive)`
- Continue the report without failing the whole run
- Never present Astro infra failures as app ASO failures

### Pre-flight: Astro Health Check

```bash
if ! pgrep -f "Astro.app" > /dev/null 2>&1; then
  echo "Starting Astro..."
  open -a Astro
  sleep 10
fi
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8089/mcp)
if [ "$HTTP_CODE" = "000" ]; then sleep 10; fi
```

Query Astro MCP at `http://127.0.0.1:8089/mcp`. Astro MCP is the **primary** ASO data source for weekly reports (NOT Appeeky).

### 6a: Fetch current keyword rankings

Call Astro MCP `get_app_keywords` for app ID `6752721747` (store: `us`) to get ALL tracked keywords with current ranks. Also query other tracked stores (`gb`, `de`, `tr`, `sa`) if available.

Save today's snapshot to `workspaces/c352342178/vidnotes/keyword-snapshots/${END_DATE}.json` (same format as daily snapshots).

### 6b: 7-day comparison (THIS IS THE CORE WEEKLY VALUE)

1. **Load the snapshot from 7 days ago:** `workspaces/c352342178/vidnotes/keyword-snapshots/{7_DAYS_AGO_DATE}.json`
   - If exact 7-day snapshot doesn't exist, use the closest available (6-8 days back).
   - If no snapshot older than 5 days exists, fall back to Appeeky `rankChange7d` data.

2. **For EVERY tracked keyword**, compute:
   - `rank_now` — current rank (null if unranked)
   - `rank_7d_ago` — rank 7 days ago (null if unranked)
   - `delta` = `rank_7d_ago - rank_now` (positive = improved)

3. **Classify ALL keywords into a full table:**

   | Keyword | Now | 7d Ago | Δ | Trend |
   |---------|-----|--------|---|-------|
   | video transcriber | #6 | #8 | +2 | 🟢 |
   | transcribe video | #12 | #10 | -2 | 🔴 |
   | video to text | — | #45 | 💀 | Lost |
   | ai notes | #33 | — | 🆕 | New |

4. **Summary stats:**
   - Total tracked keywords
   - Total ranked (with rank) vs unranked
   - 🟢 Improved (delta > 2): count + list
   - 🔴 Dropped (delta < -2): count + list  
   - 🆕 Newly ranked (unranked → ranked): count + list
   - 💀 Lost rankings (ranked → unranked): count + list
   - ⚪ Stable (|delta| ≤ 2): count

5. **Top 5 movers** (sorted by |delta|, biggest first)

6. **Keyword health score:** `ranked_keywords / total_tracked * 100`

### 6c: Keyword rankings detail

For each tracked keyword:
1. Compare current rank to 7-day-ago rank from snapshots.
2. Classify moves:
   - **Gainers**: improved by >2 positions (rank number decreased)
   - **Drops**: worsened by >2 positions (rank number increased)
   - **Stable**: moved 2 or fewer positions in either direction

### 6b: Opportunity scouting

Call Astro MCP `get_keyword_suggestions` for opportunity keywords.

For each suggested keyword, compute KEI score:

```
KEI = (popularity^2 / difficulty) * (1 + ranking_boost)
```

Where `ranking_boost`:
- Ranked 1-5: `1.5`
- Ranked 6-15: `1.2`
- Ranked 16-50: `0.8`
- Unranked: `0`

Classify by KEI:
- KEI > 500 — title candidate
- KEI 200-500 — subtitle candidate
- KEI 100-199 — keywords field candidate
- KEI < 100 — skip

Pick the **top 2 opportunities** by KEI score. For each, include: keyword, popularity, difficulty, KEI score, recommended field.

### 6c: Fallback

If Astro MCP is unreachable (connection refused, timeout, or error):
1. Fall back to Appeeky API for rankings:
   ```bash
   curl -s -H "X-API-Key: ${APPEEKY_API_KEY}" \
     "https://api.appeeky.com/v1/apps/6752721747/keywords?country=us"
   ```
2. Note `"Using Appeeky fallback — Astro MCP unavailable"` in the ASO section header.
3. Skip opportunity scouting (KEI scoring requires Astro data).

If both Astro and Appeeky fail: show `"⚠️ ASO data unavailable"` for the entire ASO section.

---

## Step 7: Experiment suggestion

Run `claude -p` with the weekly data to generate an experiment suggestion (uses Claude Max auth — no API key needed):

```bash
EXPERIMENT=$(claude -p "You are a mobile app growth strategist for VidNotes, a video transcription app with a hard paywall. Based on this week's metrics, propose ONE specific, testable A/B experiment targeting the weakest metric.

Format EXACTLY as:
Hypothesis: [specific claim]
Test: [exact screen, copy change, or flow modification]
Success metric: [what to measure]
Expected outcome: [if X then Y]

Weekly data:
- New users: ${curr_new_users} (prior: ${prior_new_users}, ${new_users_delta_pct})
- Funnel: first_open→ob_start ${first_open_to_ob_start}%, ob→complete ${ob_start_to_complete}%, paywall→converted ${pw_shown_to_converted}%
- Transcription success: ${transcription_success_pct}%
- Top failures: ${failure_breakdown}
- AI engagement: summaries ${ai_summary_users}, exports ${export_users}, flashcards ${flashcard_users}
- Paywall variants: ${paywall_variant_breakdown}
- Total crashes: ${total_crashes}" 2>/dev/null)
```

If the command fails or returns empty: show `⚠️ Experiment suggestion unavailable` in that section.

---

## Step 8: AI Narrative synthesis

Run `claude -p` with the weekly data to generate the synthesis (uses Claude Max auth — no API key needed):

```bash
SYNTHESIS=$(claude -p "You are a mobile app analytics narrator for VidNotes. Write exactly 3-4 sentences — no bullet points, no headers, no hedging, max 80 words:
- Sentence 1: The week's story (lead with most impactful shift)
- Sentence 2: Key trend — positive or negative trajectory and why
- Sentence 3: Key decision or one specific action
- Sentence 4 (optional): Notable secondary insight only if meaningful

Weekly data:
- New users: ${curr_new_users} (prior: ${prior_new_users}, ${new_users_delta_pct})
- Retention: ${curr_retention_pct}%
- Funnel: paywall→converted ${pw_shown_to_converted}%
- Transcription success: ${transcription_success_pct}%
- Top failures: ${failure_breakdown}
- Crashes: ${total_crashes} (${crash_delta} vs prior)
- ASO moves: ${aso_summary}
- AI engagement: summaries ${ai_summary_users}, exports ${export_users}" 2>/dev/null)
```

If the command fails or returns empty: omit the SYNTHESIS section from the report entirely.

---

## Step 9: Format and output report

Compose and **print** the report using **exactly** this format. OpenClaude will deliver it via its Telegram announce channel — do NOT use curl or any external API call.

```
📊 VidNotes Weekly — {WEEK_LABEL}

💡 SYNTHESIS
  {3-4 sentence narrative from Step 8}

📈 GROWTH TRENDS (7-day vs prior 7-day)
  New users: {curr_new_users} ({new_users_delta_pct})
  Retention (returning/total): {curr_retention_pct}%
  Best day: {best_day} with {best_day_users} users

💰 CONVERSION FUNNEL
  First open → Onboarding start: {first_open_to_ob_start}%
  Onboarding start → Complete: {ob_start_to_complete}%
  Onboarding → Paywall shown: {ob_to_pw_shown}%
  Paywall shown → Converted: {pw_shown_to_converted}%  ← MAIN METRIC
  Paywall variant breakdown:
    {variant_name}: {shown} shown, {converted} conv ({rate}%)
    {variant_name}: {shown} shown, {converted} conv ({rate}%)

🌍 COUNTRY PERFORMANCE (top 10)
  | Country | Users | Conv% | vs Avg |
  |---------|-------|-------|--------|
  | {country} | {users} | {conv_pct}% | {vs_avg} |
  | ... | | | |

🎙 PRODUCT HEALTH
  Transcription success: {transcription_success_pct}% (7-day)
  Failure breakdown: {error_type}: {N} · {error_type}: {N} · ...
  AI feature engagement: summaries {ai_summary_users} · exports {export_users} · flashcards {flashcard_users}
  Video import sources: {source} {N} · {source} {N} · {source} {N}

🔴 ENGINEERING (7-day)
  Total crashes: {total_crashes} ({crash_delta} vs prior week)
  New issues: {new_issues}
  Top 3: {title} ({N}) · {title} ({N}) · {title} ({N})

📱 ASO — 7-DAY KEYWORD REPORT ({source})
  Tracked: {total_tracked} · Ranked: {total_ranked}/{total_tracked} ({health_pct}%)
  🟢 Improved: {gainers_count} · 🔴 Dropped: {drops_count} · 🆕 New: {new_count} · 💀 Lost: {lost_count}

  TOP MOVERS (7d):
  {keyword1} #{old}→#{new} ({delta}) {emoji}
  {keyword2} #{old}→#{new} ({delta}) {emoji}
  {keyword3} #{old}→#{new} ({delta}) {emoji}
  {keyword4} #{old}→#{new} ({delta}) {emoji}
  {keyword5} #{old}→#{new} ({delta}) {emoji}

  FULL KEYWORD TABLE:
  (List ALL tracked keywords with rank now, rank 7d ago, delta, trend emoji)

  OPPORTUNITIES:
  {keyword}: vol {N}, difficulty {N}, KEI {N} → {field} candidate
  {keyword}: vol {N}, difficulty {N}, KEI {N} → {field} candidate

🧪 THIS WEEK'S EXPERIMENT
  Hypothesis: {claim}
  Test: {what to change}
  Success metric: {metric}
  Expected outcome: {if X then Y}
```

**Section rules:**
- If the SYNTHESIS narrative is unavailable, remove the `💡 SYNTHESIS` section entirely.
- If ENGINEERING has zero total crashes AND zero new issues, **omit the entire ENGINEERING section**.
- If the experiment suggestion is unavailable, replace its content with `⚠️ Experiment suggestion unavailable`.
- If any other section's data is unavailable, replace its content with `⚠️ Data unavailable — {reason}` but keep the section header.
- If ASO data is unavailable, show `⚠️ ASO data unavailable` under the ASO header.
- If using Appeeky fallback, change the ASO header to `📱 ASO — KEYWORD MOVES (Appeeky fallback)` and omit the OPPORTUNITIES sub-section.

**Print the complete formatted report as your final response.** OpenClaude's announce delivery will send it to Telegram automatically.

---

## Step 10: Update baselines.json

After outputting the report, update `workspaces/c352342178/vidnotes/baselines.json`:

1. Read the existing file (or use seed values if missing):
   ```json
   {
     "transcription_success_7d": 82.9,
     "conversion_rate_7d": 21.1,
     "new_users_7d_avg": 17,
     "new_users_history": [],
     "weekly_crashes_prior": 0,
     "seen_crash_issue_ids": [],
     "last_updated": null
   }
   ```
2. Update 7-day rolling averages with this week's data:
   - `transcription_success_7d` = `transcription_success_pct` (direct replacement — weekly is a full 7-day window)
   - `conversion_rate_7d` = `pw_shown_to_converted` (direct replacement)
   - `new_users_7d_avg` = `curr_new_users / 7`, rounded to 0 decimals (daily average from this week)
   - `weekly_crashes_prior` = `total_crashes` (for next week's comparison)
3. **Do NOT clear `seen_crash_issue_ids`** — the daily job manages that array.
4. **Do NOT clear or modify `new_users_history`** — the daily job manages that array.
5. Set `last_updated` to today's date (ISO 8601 format).
6. Write the updated JSON back to the file:

```bash
mkdir -p workspaces/c352342178/vidnotes
cat > workspaces/c352342178/vidnotes/baselines.json << 'BASELINES_EOF'
{
  "new_users_7d_avg": {CALCULATED},
  "transcription_success_7d": {CALCULATED},
  "conversion_rate_7d": {CALCULATED},
  "new_users_history": [{PRESERVE_EXISTING_ARRAY}],
  "weekly_crashes_prior": {TOTAL_CRASHES},
  "seen_crash_issue_ids": [{PRESERVE_EXISTING_ARRAY}],
  "last_updated": "{TODAY_ISO}"
}
BASELINES_EOF
```

---

## Step 11: Git archive

Write the formatted report as a markdown file and commit it to the repository:

```bash
REPORT_DIR="/Users/antharas/Projects/VidNotes/Code/docs/reports/weekly"
REPORT_PATH="${REPORT_DIR}/${WEEK_LABEL}.md"

mkdir -p "$REPORT_DIR"

cat > "$REPORT_PATH" << 'REPORT_EOF'
# VidNotes Weekly Report — {WEEK_LABEL}
## {DISPLAY_START} to {DISPLAY_END}

{Full report content in markdown format, same data as the Telegram message but with proper markdown headers, tables, and formatting}
REPORT_EOF

git -C /Users/antharas/Projects/VidNotes/Code add docs/reports/weekly/
git -C /Users/antharas/Projects/VidNotes/Code commit -m "chore(reports): weekly report ${WEEK_LABEL}"
git -C /Users/antharas/Projects/VidNotes/Code push origin main
```

If any git command fails, log the error and continue. The report has already been output and OpenClaude will deliver it regardless.

---

## Step 12: Finalize lockfile

After outputting the report and completing Steps 10–11, update the lockfile with a completion timestamp:

```bash
echo "completed=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> workspaces/c352342178/vidnotes/locks/weekly-${WEEK_LABEL}.lock
```

**Never delete the lockfile.** It exists to prevent duplicate runs. The lockfile was created in Step 2 before any work began, so even if the agent crashes mid-run, a re-invocation will see the lockfile and exit.

---

## Error handling summary

| Failure | Action |
|---------|--------|
| GA4 not ready after retry | Send warning to Telegram, stop |
| Individual BQ query fails | Mark section with ⚠️, continue |
| Astro MCP unreachable | Fall back to Appeeky, note in report |
| Both Astro and Appeeky fail | Show ⚠️ in ASO section, continue |
| Crashlytics unavailable | Show ⚠️ in ENGINEERING section, continue |
| Narrative generation fails | Omit SYNTHESIS section, continue |
| Experiment generation fails | Show ⚠️ in EXPERIMENT section, continue |
| Output/delivery fails | Log error, continue (OpenClaude handles delivery) |
| Baselines update fails | Log error, continue |
| Git commit/push fails | Log error, continue |

Each section is **independent**. One failure must never block other sections. The report should always be delivered with whatever data is available.


## Silpho OS Telegram Delivery

After outputting the report, also send it to the Silpho OS group:

```bash
SILPHO_BOT_TOKEN="8733346629:AAGixlBDK2fg6Xyjx5iLQDjsBGOhKz3xF4Q"
SILPHO_CHAT_ID="-5088617466"

curl -s -X POST "https://api.telegram.org/bot${SILPHO_BOT_TOKEN}/sendMessage" \
  -H "Content-Type: application/json" \
  -d "{\"chat_id\": \"${SILPHO_CHAT_ID}\", \"text\": $(echo "$REPORT" | python3 -c \"import sys,json; print(json.dumps(sys.stdin.read()))\"), \"parse_mode\": \"\"}" > /dev/null 2>&1
```
