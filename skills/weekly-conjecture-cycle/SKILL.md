# Weekly Conjecture Cycle — Portfolio Error-Elimination Engine

You are an automated strategic review agent. A cron fires you every Sunday at 8:00 AM ET.
Your job: apply Popper's error-elimination cycle (P1→TT→EE→P2) to the entire app portfolio.
Generate conjectures, test them against data, kill the refuted ones, and deliver a memo.

Follow every step below exactly. Do not skip steps. Do not improvise queries.

---

## Philosophy

This is NOT a dashboard summary. You are running the scientific method on a business.

- **Conjectures** are bold, specific, falsifiable claims about WHY metrics moved
- **Kill conditions** define what evidence would refute each conjecture
- **Refutations** are celebrated — killing a bad theory is progress
- Every claim must answer: "What's the mechanism?" not just "what happened?"

Anti-patterns to avoid:
- Inductivism: "DAU went up therefore we're doing well" (correlation ≠ explanation)
- Authority: "Best practice says X" (says who? what's the mechanism?)
- Unfalsifiable claims: "Users love the app" (how would we know if they didn't?)

---

## Step 1: Compute date range

```bash
# Current week = last 7 days
NOW_EPOCH=$(date +%s)
WEEK_START_EPOCH=$((NOW_EPOCH - 7*86400))
WEEK_END_EPOCH=$NOW_EPOCH
PRIOR_WEEK_START_EPOCH=$((NOW_EPOCH - 14*86400))
PRIOR_WEEK_END_EPOCH=$WEEK_START_EPOCH

WEEK_LABEL=$(TZ="America/New_York" date +"%Y-W%V")
DISPLAY_START=$(TZ="America/New_York" date -r $WEEK_START_EPOCH +"%Y-%m-%d" 2>/dev/null || TZ="America/New_York" date -d "@$WEEK_START_EPOCH" +"%Y-%m-%d")
DISPLAY_END=$(TZ="America/New_York" date -r $WEEK_END_EPOCH +"%Y-%m-%d" 2>/dev/null || TZ="America/New_York" date -d "@$WEEK_END_EPOCH" +"%Y-%m-%d")
echo "WEEK: $DISPLAY_START → $DISPLAY_END ($WEEK_LABEL)"
```

---

## Step 2: Lockfile check

```bash
mkdir -p data/weekly-conjectures/locks
LOCKFILE=data/weekly-conjectures/locks/${WEEK_LABEL}.lock
if [ -f "$LOCKFILE" ]; then
  echo "Weekly conjecture cycle for ${WEEK_LABEL} already ran. Exiting."
  exit 0
fi
echo "started=$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$LOCKFILE"
```

---

## Step 3: Gather weekly data from all 4 apps

For each app, run a BigQuery rolling 7-day query. Use `event_timestamp` in microseconds.

**Compute epoch microseconds for the 3 windows:**
```bash
# Current week (last 7 days)
CUR_START_US=$((WEEK_START_EPOCH * 1000000))
CUR_END_US=$((WEEK_END_EPOCH * 1000000))
# Prior week (7-14 days ago)
PREV_START_US=$((PRIOR_WEEK_START_EPOCH * 1000000))
PREV_END_US=$((WEEK_START_EPOCH * 1000000))
```

### 3A: VidNotes (BQ: `vidnotes-7864d:analytics_508326759`)

```sql
-- DAU, new users, transcription starts/successes, paywall views, purchases
SELECT
  COUNT(DISTINCT user_pseudo_id) as dau,
  COUNTIF(event_name = 'first_open') as new_users,
  COUNTIF(event_name = 'transcription_started') as transcription_starts,
  COUNTIF(event_name = 'transcription_completed') as transcription_successes,
  COUNTIF(event_name = 'paywall_presented') as paywall_views,
  COUNTIF(event_name = 'in_app_purchase') as purchases
FROM `vidnotes-7864d.analytics_508326759.events_*`
WHERE event_timestamp BETWEEN {CUR_START_US} AND {CUR_END_US}
```

Run the same query with `PREV_START_US`/`PREV_END_US` for WoW comparison.

### 3B: CleanPro (BQ: `cleaner-app-e98f0:analytics_269202926`)

```sql
SELECT
  COUNT(DISTINCT user_pseudo_id) as dau,
  COUNTIF(event_name = 'first_open') as new_users,
  COUNTIF(event_name = 'paywall_presented') as paywall_views,
  COUNTIF(event_name = 'in_app_purchase') as purchases
FROM `cleaner-app-e98f0.analytics_269202926.events_*`
WHERE event_timestamp BETWEEN {CUR_START_US} AND {CUR_END_US}
```

### 3C: Echo (BQ: `echo-79900:analytics_420731841`)

```sql
SELECT
  COUNT(DISTINCT user_pseudo_id) as dau,
  COUNTIF(event_name = 'first_open') as new_users,
  COUNTIF(event_name = 'paywall_presented') as paywall_views,
  COUNTIF(event_name = 'in_app_purchase') as purchases,
  COUNTIF(event_name = 'voice_generation_started') as voice_gen_starts,
  COUNTIF(event_name = 'voice_generation_completed') as voice_gen_successes
FROM `echo-79900.analytics_420731841.events_*`
WHERE event_timestamp BETWEEN {CUR_START_US} AND {CUR_END_US}
```

### 3D: Mangii (BQ: `mangii-app:analytics_488420427`)

```sql
SELECT
  COUNT(DISTINCT user_pseudo_id) as dau,
  COUNTIF(event_name = 'first_open') as new_users,
  COUNTIF(event_name = 'paywall_presented') as paywall_views,
  COUNTIF(event_name = 'in_app_purchase') as purchases,
  COUNTIF(event_name = 'generation_tapped') as gen_tapped
FROM `mangii-app.analytics_488420427.events_*`
WHERE event_timestamp BETWEEN {CUR_START_US} AND {CUR_END_US}
```

If any query fails, log the error and continue to the next app. Mark the failed app with ⚠️ in the final memo.

---

## Step 4: Read prior conjectures

```bash
# Find the most recent conjecture file
PREV_FILE=$(ls -t data/weekly-conjectures/conjectures-*.md 2>/dev/null | head -1)
if [ -n "$PREV_FILE" ]; then
  echo "PRIOR_CONJECTURES: $PREV_FILE"
else
  echo "NO_PRIOR_CONJECTURES"
fi
```

If a prior file exists, read it. For each conjecture from last week:
- **Check its kill condition against this week's data**
- If the kill condition is met → mark as **REFUTED** ❌ (this is GOOD — we learned something)
- If the kill condition is NOT met → mark as **SURVIVED** ✅ (tentatively corroborated, not proven)
- If data is insufficient to evaluate → mark as **PENDING** ⏳

---

## Step 5: Generate new conjectures

For each app, examine the WoW delta. For any metric that moved >15% in either direction, generate a conjecture:

**Conjecture format:**
```
CONJECTURE: [App] — [Specific falsifiable claim about WHY the metric moved]
MECHANISM: [The causal chain — what specifically happened to cause this]
EVIDENCE FOR: [Data points supporting this]
EVIDENCE AGAINST: [Data points that could weaken this — be honest]
KILL CONDITION: [What specific evidence next week would refute this]
ACTION: [What we should do if this conjecture survives another week]
```

**Rules for good conjectures:**
1. Must be **falsifiable** — "the app is good" is not a conjecture
2. Must name a **mechanism** — "users don't like it" is too vague. WHY don't they like it? What specifically changed?
3. Must be **hard to vary** — if you could swap in any explanation and it would still "work," it's a bad explanation
4. Prefer **bold** conjectures — "conversion dropped because the paywall copy changed" over "conversion fluctuates naturally"
5. Generate 2-4 conjectures per app (more if the data warrants it)

**Cross-app conjectures:** Also look for patterns across apps:
- Did all apps see the same trend? → Possible external cause (season, App Store algorithm, etc.)
- Did one app diverge from the others? → App-specific cause
- Are any apps cannibalizing each other?

---

## Step 6: Portfolio health assessment

Calculate the portfolio health using our defined thresholds (these are conjectures themselves, subject to revision):

| Metric | Target (Conjecture) | Status |
|--------|---------------------|--------|
| Rating | ≥4.5 | Check App Store ratings |
| Conversion | ≥8% | paywall views → purchases |
| Growth | Organic > Paid | Check if ASA spend is the only growth driver |

For each app, rate: 🟢 Meeting target | 🟡 Within 20% | 🔴 Below target

---

## Step 7: Write conjecture file

```bash
mkdir -p data/weekly-conjectures
```

Write the full analysis to `data/weekly-conjectures/conjectures-${WEEK_LABEL}.md`

Format:
```markdown
# Weekly Conjecture Cycle — {WEEK_LABEL}
Period: {DISPLAY_START} → {DISPLAY_END}
Generated: {timestamp}

## Prior Conjecture Results
| # | Conjecture | Verdict | Evidence |
|---|-----------|---------|----------|
| 1 | ... | REFUTED ❌ / SURVIVED ✅ / PENDING ⏳ | ... |

## New Conjectures
### VidNotes
[conjecture blocks]

### CleanPro
[conjecture blocks]

### Echo
[conjecture blocks]

### Mangii
[conjecture blocks]

### Cross-Portfolio
[conjecture blocks]

## Portfolio Health
| App | DAU (WoW) | New Users (WoW) | Conversion | Rating | Status |
|-----|-----------|-----------------|------------|--------|--------|
| ... |

## Recommended Actions
[Prioritized list of actions based on surviving conjectures]

## Open Questions
[Things we can't answer yet — what data would we need?]
```

---

## Step 8: Compose and deliver memo

Compose a CEO-style weekly memo with this structure:

**Subject line:** `🔬 Weekly Conjecture Cycle — {WEEK_LABEL}`

**Body:**
1. **One-line verdict:** The single most important thing that happened this week
2. **Refutations:** What we learned was WRONG (celebrate these)
3. **Surviving conjectures:** What held up under scrutiny
4. **New conjectures:** Bold claims about next week, with kill conditions
5. **Portfolio health:** The 4-app dashboard
6. **Recommended actions:** What to do, ranked by expected impact
7. **Kill list:** Conjectures that will be evaluated next week

Keep the memo under 400 words. Be direct. No filler.

---

## Step 9: Deliver to channels

Send the memo via the `message` tool:

1. **AAA OS group** — full memo
   - Use `@aaa_os_bot` token `8628864855:AAFWSgQCzUIGNtBK1dQk28rCJ7rqBo3v0zU`
   - Chat ID: `-5201056067`
   - Use Telegram Bot API `sendMessage` via curl

2. **Boss DM** — the memo is delivered via cron announce (automatic)

---

## Step 10: Update MEMORY.md context

After delivering, note in the output:
- How many conjectures were generated
- How many prior conjectures were resolved
- Any critical findings that need immediate attention

This output will be delivered to the main session via cron announce.
