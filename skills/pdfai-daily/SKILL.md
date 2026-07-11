# PDFAI Scanner Daily Report — Agent Skill

> **Canonical runner (2026-07-12):** cron uses deterministic `scripts/pdfai_daily_runner.py` (not this prompt). Keep this skill as the metric/spec reference. Only use this skill if the Python runner is unavailable.

You are an automated reporting agent for PDFAI Scanner (App Store ID `6654887952`, bundle `com.mni.ai.ocuscan.smart.pdf.tool`). Follow every step exactly. If one fails, mark with warning and continue.

**IMPORTANT: All BQ queries use ROLLING 24-HOUR WINDOWS, not calendar days.**
- "Today" = last 24 hours from NOW
- "Yesterday" = 24-48 hours ago
- "Last week" = 168-192 hours ago
- BQ filter: `event_timestamp BETWEEN` in microseconds
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
```

## Step 2: Lockfile (idempotency)

```bash
LOCK=data/pdfai/locks/daily-${DISPLAY_DATE}.lock
if [ -f "$LOCK" ]; then echo "Already sent for $DISPLAY_DATE. Exiting."; exit 0; fi
mkdir -p data/pdfai/locks data/pdfai/daily-reports data/pdfai/keyword-snapshots
echo "started=$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$LOCK"
```

## BigQuery Robustness Rule (mandatory)

When running BigQuery queries:
- Prefer `--format=json` and parse JSON output, not loose text parsing
- If a query job reaches `DONE` but the wrapper/parser fails, treat it as an **infra/parser bug**, not a business metric of zero
- Do **not** silently replace failed metrics with zero unless the SQL itself returned zero rows successfully
- If parsing fails, label the metric block as `⚠️ BigQuery result parsing failed` and continue the rest of the report
- Never confuse `query failed` with `metric = 0`

## Step 3: GA4 BigQuery — Rolling 24h Metrics

Project: `pdfai-scanner`, Dataset: `analytics_502367642`

Check for both `events_*` and `events_intraday_*` tables. Use UNION ALL if intraday exists, otherwise just `events_*`. Filter by `event_timestamp`.

**To check if intraday tables exist:**
```bash
bq ls "pdfai-scanner:analytics_502367642" 2>/dev/null | grep "events_intraday" | head -1
```
If no intraday tables exist, skip the UNION ALL and query only `events_*`.

### Query (run for 3 windows: last 24h, 24-48h ago, 7 days ago)

For each window, set the appropriate `START_US` and `END_US` values:
- Window 1 (today): `H24_AGO_US` to `NOW_US`
- Window 2 (yesterday): `H48_AGO_US` to `H24_AGO_US`
- Window 3 (last week): `H192_AGO_US` to `H168_AGO_US`

Compute `_TABLE_SUFFIX` range: convert the epoch microseconds to YYYYMMDD format for the start and end, expanding by 1 day on each side to account for timezone differences.

```sql
SELECT
  COUNT(DISTINCT user_pseudo_id) as dau,
  COUNTIF(event_name = 'first_open') as new_users,
  COUNTIF(event_name = 'session_start') as sessions,

  -- Onboarding funnel
  COUNTIF(event_name = 'onboarding_progress') as onboarding_progress,
  COUNTIF(event_name = 'onboarding_completed') as onboarding_completed,
  COUNTIF(event_name = 'onboarding_start_creating_pdf_tapped') as onboarding_start_tapped,

  -- Core scan funnel
  COUNTIF(event_name = 'scan_started') as scan_started,
  COUNTIF(event_name = 'scan_completed') as scan_completed,
  COUNTIF(event_name = 'export_success') as export_success,
  COUNTIF(event_name = 'export_failure') as export_failure,

  -- Value realization
  COUNTIF(event_name = 'value_realization_scan_completed') as value_realized,
  COUNTIF(event_name = 'activation_milestone') as activation_milestones,
  COUNTIF(event_name = 'activation_first_export_complete') as first_export_complete,

  -- Monetization
  COUNTIF(event_name = 'paywall_shown') as paywall_views,
  COUNTIF(event_name = 'paywall_dismissed') as paywall_dismissed,
  COUNTIF(event_name = 'purchase_attempt') as purchase_attempts,
  COUNTIF(event_name IN ('in_app_purchase', 'purchase_success')) as purchases,
  COUNTIF(event_name = 'purchase_failed') as purchase_failed,

  -- Features used
  COUNTIF(event_name = 'feature_used') as features_used,
  COUNTIF(event_name = 'audio_export_initiated') as audio_exports,
  COUNTIF(event_name = 'reading_position_saved') as reading_positions_saved,
  COUNTIF(event_name LIKE '%quiz%') as quiz_events,
  COUNTIF(event_name LIKE '%flash%') as flashcard_events,
  COUNTIF(event_name LIKE '%tts%' OR event_name = 'quickread_text_file_tts_opened') as tts_events,

  -- Cloud / sync
  COUNTIF(event_name = 'anonymous_auth_success') as auth_success,
  COUNTIF(event_name LIKE '%cloud%' OR event_name LIKE '%icloud%') as cloud_events,
  COUNTIF(event_name = 'connectivity_restored') as connectivity_restored,

  -- Errors
  COUNTIF(event_name = 'smart_naming_cloud_ai_failure') as ai_naming_failures,

  -- Reviews
  COUNTIF(event_name = 'review_modal_shown') as review_modal_shown,
  COUNTIF(event_name = 'review_modal_completed') as review_modal_completed,
  COUNTIF(event_name = 'review_open_write_review_page') as review_write_page,

  -- Share / viral
  COUNTIF(event_name = 'savetopdfai_ext_share_extension_opened') as share_extension_opened,
  COUNTIF(event_name = 'deep_link_scan_opened') as deep_link_opens

FROM `pdfai-scanner.analytics_502367642.events_*`
WHERE _TABLE_SUFFIX BETWEEN '{YYYYMMDD_start}' AND '{YYYYMMDD_end}'
  AND event_timestamp BETWEEN {START_US} AND {END_US}
```

**IMPORTANT:** Replace `{START_US}`, `{END_US}`, `{YYYYMMDD_start}`, `{YYYYMMDD_end}` with actual values. The `_TABLE_SUFFIX` range should cover the date range of the window plus 1 day buffer on each side.

---

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

## Step 4: Astro ASO — Keyword Rankings

Fetch keyword rankings from Astro API for US store.

```bash
# US store keywords
curl -s "https://api.astro.withfluffy.com/api/v1/app/apple/6654887952/top-keywords?country=us&limit=25" \
  -H "x-api-key: sk-astro-998ef58e-ea5c-48db-a75c-13d9d8deb289" | python3 -c "
import json, sys
data = json.load(sys.stdin)
keywords = data.get('keywords', data.get('data', []))
if isinstance(keywords, list):
    print(f'Total keywords tracked: {len(keywords)}')
    for kw in sorted(keywords, key=lambda x: x.get('rank', 999))[:25]:
        name = kw.get('keyword', kw.get('name', '?'))
        rank = kw.get('rank', '?')
        change = kw.get('change', kw.get('delta', 0))
        vol = kw.get('volume', kw.get('searchVolume', '?'))
        sign = '+' if change and int(change) > 0 else ''
        print(f'  #{rank} ({sign}{change}) | vol {vol} | {name}')
"
```

If the Astro API returns an error or the app is not tracked yet, note it and skip this section. Do NOT fail the entire report.

---

## Step 5: Compute derived metrics & deltas

Calculate from the raw numbers:

1. **Scan completion rate** = scan_completed / scan_started × 100
2. **Export success rate** = export_success / (export_success + export_failure) × 100
3. **Paywall conversion** = purchases / paywall_views × 100 (skip if paywall_views < 5)
4. **Onboarding completion** = onboarding_completed / onboarding_progress × 100 (skip if < 5 events)
5. **Value realization rate** = value_realized / new_users × 100
6. **AI naming failure rate** = ai_naming_failures / sessions × 100

For each metric, compute:
- **DoD** = ((today - yesterday) / yesterday) × 100 — show as percentage with + or -
- **WoW** = ((today - last_week) / last_week) × 100

If the denominator is 0, show "N/A" instead of dividing by zero.

---

## Step 6: Format the report

Use this template exactly:

```
📄 PDFAI Scanner — Daily Report
📅 {DISPLAY_DATE} (as of {DISPLAY_TIME} ET)

📊 OVERVIEW
• DAU: {dau} ({DoD}% DoD, {WoW}% WoW)
• New Users: {new_users} ({DoD}% DoD, {WoW}% WoW)
• Sessions: {sessions}

📷 SCAN FUNNEL
• Started: {scan_started} → Completed: {scan_completed} ({completion_rate}%)
• Exports: {export_success} ({export_success_rate}% success)
• Value Realized: {value_realized} ({value_realization_rate}% of new users)

💰 MONETIZATION
• Paywall Views: {paywall_views} → Dismissed: {paywall_dismissed}
• Purchase Attempts: {purchase_attempts} → Purchases: {purchases}
• Conversion: {conversion}% ({DoD} DoD, {WoW} WoW)

🎓 ONBOARDING
• Progress: {onboarding_progress} → Completed: {onboarding_completed} ({completion}%)
• Start Creating Tapped: {onboarding_start_tapped}

🔧 FEATURES
• Features Used: {features_used}
• Audio Exports: {audio_exports}
• TTS Events: {tts_events}
• Quiz/Flashcard: {quiz_events}/{flashcard_events}
• Reading Positions Saved: {reading_positions_saved}

☁️ CLOUD & AUTH
• Auth Success: {auth_success}
• Cloud Events: {cloud_events}

⚠️ ERRORS
• AI Naming Failures: {ai_naming_failures} ({failure_rate}% of sessions)
• Export Failures: {export_failure}
• Purchase Failures: {purchase_failed}

⭐ REVIEWS
• Modal Shown: {review_modal_shown} → Completed: {review_modal_completed}
• Write Review Page: {review_write_page}

🔗 VIRAL
• Share Extension: {share_extension_opened}
• Deep Links: {deep_link_opens}

🔍 ASO (US)
{top 10 keywords with rank, change, volume — or "Not tracked yet"}
```

If any section has all zeros or N/A, still include it but note "(no activity)".

---

## Step 7: Save report to disk

```bash
mkdir -p data/pdfai/daily-reports
```

Write the formatted report to `data/pdfai/daily-reports/${DISPLAY_DATE}.md`

---

## Step 8: Deliver to channels

### 8A: AAA OS Telegram Group

Send via Telegram Bot API:
```bash
curl -s -X POST "https://api.telegram.org/bot8628864855:AAFWSgQCzUIGNtBK1dQk28rCJ7rqBo3v0zU/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "-5201056067",
    "text": "<REPORT_TEXT>",
    "parse_mode": "Markdown"
  }'
```

If Markdown parse fails, retry with `parse_mode` removed (plain text fallback).

### 8B: Boss DM

The report will also be delivered via cron announce (automatic). The announce delivery is the primary delivery to the boss — do not send a separate DM.

---

## Step 9: Output summary for cron announce

Print a condensed version of the report (the full report is saved to disk and sent to AAA OS).
The cron announce system will deliver your output to the boss DM.

Focus the summary on:
1. One-line headline (biggest change)
2. Key numbers: DAU, New Users, Conversion, Scan Completion
3. Any anomalies or concerns
4. ASO movers (keywords with |change| > 5)

Keep under 300 words.
