# CleanPro Weekly Report — 2026-W30 (run 2026-07-28, a day late)

## Result: delivered ✅ + correction sent
- Window: 2026-07-20 → 2026-07-26 (true last Mon–Sun). Script's -1d/-7d math assumes a Monday
  run; Monday's cron misfired (Mac sleep, misfire_grace_time=300s) so I shifted the window
  rather than use Tue–Mon. GA4 daily table for 07-27 had not exported (max daily = 20260726).
- Telegram AAA OS group (-5201056067): report msg 2084, then a correction message.
- Archive: CleanPro/source/dev/reports/weekly/2026-W30.md. Baselines updated to W30.
- W28 and W29 were never produced (no locks) — those weeks are unreported.

## THE FINDING (this is the whole week)
Paid acquisition to **Romania and Costa Rica stopped dead on 2026-07-18** and has not resumed.
- first_open where traffic_source.medium='search': RO 271→0, CR 134→1 (Jul 6–17 vs Jul 18–26).
  Organic '(none)' continued normally ⇒ campaign/account-side, not a tracking break.
- Both countries had converted healthily for 6 straight weeks (RO 12–25 conv/wk, CR 5–20 conv/wk).
- Simultaneous two-country stop on one date ⇒ suspect account-level (billing/budget), not per-campaign.

## Why the headline numbers lie
- New users 391 (−30.7%): RO (−116) + CR (−86) ≈ the entire drop.
- Paywall CVR 9.2%→9.9% and retention 62.5%→69.9% are **survivorship artefacts**, not improvements.
  Losing two mid-CVR markets raised the average and gutted the new-user denominator.
- Conversions 48→37; trials 67→47.

## Mistake I made and corrected
First message called RO/CR "chronic 0% markets" and re-proposed PPP geo-pricing for them (5th time).
Wrong — the W25 baseline showed Romania at 6.6% CVR. Checked the 7-week trend, found the Jul-18
cliff, sent a correction. **Lesson: before calling a country a chronic zero, diff it against
baselines.json — and when a metric goes to exactly 0 in multiple markets on one date, that is an
ops event, not user behaviour.**

## Still-open items
- PPP geo-pricing test is still valid, but only for PH / US / UK / SA (genuinely never converted).
  RO and CR must be removed from it.
- ASO skipped for the 8th consecutive week — Astro MCP (127.0.0.1:8089) is not running, no Appeeky
  key on disk. Either install it or cut Step 6 from the skill.
- Skill bug: Step 3's freshness gate compares MAX(_TABLE_SUFFIX) which returns "intraday_YYYYMMDD";
  string-compares greater than any date so the gate can never fail. Needs
  `WHERE _TABLE_SUFFIX NOT LIKE 'intraday%'`.
- Skill bug: date math silently produces a wrong window on any non-Monday run.
- Crashlytics: still GA4 app_exception proxy only (2 events/2 users, healthy). No native export.
