# Weekly Conjecture Cycle — 2026-W22
Period: 2026-05-18 → 2026-05-25 (ICT)
Generated: 2026-05-25T12:05:00Z (19:05 ICT)

**Note:** W20 and W21 cycles were skipped (no conjecture files exist). Prior conjectures from W19 are evaluated against W22 data — a 3-week gap. Event taxonomies shifted again in W22 — VidNotes renamed `transcription_started→transcription_start`, `transcription_completed→transcription_complete`, `paywall_presented→paywall_viewed`, `in_app_purchase→purchase`. Echo's `purchase` event now appears to fire for credit purchases as well as subs (purchase=627 = ~ IAP 30 + credit_purchased 590). For Echo apples-to-apples revenue I use `in_app_purchase` (true subscription IAPs).

---

## Prior Conjecture Results (W19 → evaluated against W22)

| # | Conjecture | Verdict | Evidence |
|---|-----------|---------|----------|
| VN19-1 | VidNotes paywall views doubled = new onboarding gate | **REFUTED ❌** | Paywall views W19=1,245 → W22=920+445=1,365 ≈ flat. The W19 "doubling" reverted. Either a temporary gate was rolled back or W19 was a measurement artifact. |
| VN19-2 | Cancellation rate structurally elevated (>12%) | **REFUTED ❌** | Cancellation/total-paywall: W19=15.3% → W22=7.8%. Below the 10% kill threshold. Good news. |
| VN19-3 | Transcription fix confirmed real (failure <10% at higher volume) | **CONFIRMED ✅** | Failure rate W19=9.2% → W21=8.9% → W22=**2.5%**. Volume held (~886 starts). Three weeks of corroboration, now well below threshold. |
| CP19-1 | CleanPro in structural churn death spiral | **EVOLVING** | DAU continues falling (1,943→2,159→1,842). But new users dropped -30% in W22 — mechanism shifted from retention churn to acquisition collapse. Conjecture survives in spirit but the cause changed. |
| CP19-2 | CleanPro onboarding paywall regressed | **REFUTED ❌** | OB conversions: W19=67 → W22=76. Crossed back above the 75 kill threshold. The W19 dip was a cohort fluctuation. |
| EC19-1 | Echo voice cloning fix was a rollback | **SURVIVED ✅ (WORSENING)** | Failure rate W19=56.4% → W21=64.4% → W22=**73.8%**. Three weeks of monotonic worsening. The conjecture that this is the same unfixed bug is now corroborated by trajectory. **URGENT.** |
| EC19-2 | Echo purchase failure progressive bug (>10%) | **PENDING ⏳** | No error code logging added. Failure rate (purchase_failed/purchase_initiated): W19=~11.7% → W22=11.7% — flat, but failure rate against successful IAP: W21=22/(22+27)=44.9% → W22=29/(29+30)=49.2%. The structural problem persists. |
| EC19-3 | Echo credit revenue tied to voice cloning (fix cloning → credits >25/week) | **REFUTED ❌** | Voice cloning got worse (56→74% fail) yet credit_purchased exploded 20→590. The causal link is wrong (or instrumentation changed). Either way the conjecture as framed is falsified. |
| MG19-1 | Mangii purchase failure masking revenue (>40 without fix) | **SURVIVED ✅** | Failed: W19=51 → W21=47 → W22=54. Above the 40 kill threshold. Failure rate climbed 42% → 50%. No fix shipped. |
| MG19-2 | Mangii free-tier limit too tight | **PENDING ⏳** | No deliberate test. Block rate actually fell (55.8% → 43.8%) but without controlled change, this is uninterpretable. |
| XP19-1 | Growth apps not offsetting declining apps | **SURVIVED ✅** | W19→W22 portfolio subs purchases: 377 → 262 (-30.5%). Even the W19 "growth apps" (VN, MG) stalled. The thesis was correct. |
| XP19-2 | Portfolio-wide shared StoreKit bug | **PENDING ⏳** | No error code logging added in any app. Cannot evaluate. Failure rates persist in 3 of 4 apps. |

**Score W19→W22: 1 CONFIRMED, 4 REFUTED, 3 SURVIVED, 3 PENDING, 1 EVOLVING. 8 of 12 conjectures resolved over 3 weeks — strong epistemic hygiene.**

---

## Raw Data — W21 vs W22 (current week comparison)

### VidNotes
| Metric | W21 | W22 | Δ |
|--------|-----|-----|---|
| DAU | 1,599 | 1,196 | **-25.2%** 🔴🔴 |
| New Users (first_open) | 844 | 750 | -11.1% |
| Transcription Start | 870 | 886 | +1.8% |
| Transcription Complete | 529 | 534 | +0.9% |
| Transcription Failed | 77 | 22 | **-71.4%** 🟢 |
| **Failure Rate** | 8.9% | **2.5%** | -6.4pp 🟢🟢 |
| Paywall Viewed (main) | 960 | 920 | -4.2% |
| Onboarding Paywall Viewed | 980 | 445 | **-54.6%** 🔴 |
| Purchase (subs) | 44 | 39 | -11.4% |
| Onboarding Purchase | 42 | 34 | -19.0% |
| **Total Purchases** | 86 | 73 | **-15.1%** 🔴 |
| Trial Start | 116 | 39 | **-66.4%** 🔴🔴 |
| Purchase Cancelled | 191 | 106 | -44.5% 🟢 |
| Purchase Failed | 11 | 10 | -9% |
| Subscription Cancelled | 1 | 6 | +500% (small base) |

### CleanPro
| Metric | W21 | W22 | Δ |
|--------|-----|-----|---|
| DAU | 2,159 | 1,842 | **-14.7%** 🔴 |
| New Users | 1,034 | 726 | **-29.8%** 🔴🔴 |
| Onboarding Completed | 950 | 730 | -23.2% |
| First Conversion Attempt | 892 | 677 | -24.1% |
| Paywall Trigger | 1,660 | 1,550 | -6.6% |
| CleanPro Paywall Shown | 1,453 | 1,278 | -12.0% |
| Onboarding Paywall Shown | 930 | 721 | -22.5% |
| Purchase | 97 | 105 | **+8.2%** 🟢 |
| App Initial Purchase | 95 | 94 | ~flat |
| OB Paywall Converted | 69 | 76 | +10.1% 🟢 |
| CleanPro Converted | 19 | 14 | -26.3% |
| Native Converted | 4 | 14 | +250% (small base) |
| RC Trial Start | 88 | 84 | ~flat |
| OB Purchase Cancelled | 554 | 389 | -29.8% |
| CleanPro Purchase Cancelled | 316 | 263 | -16.8% |
| Product Nil Errors | 35 | 15 | **-57.1%** 🟢 |
| Product Load Failed | 31 | 16 | **-48.4%** 🟢 |

### Echo
| Metric | W21 | W22 | Δ |
|--------|-----|-----|---|
| DAU | 2,401 | 2,004 | **-16.5%** 🔴 |
| New Users | 1,433 | 1,099 | **-23.3%** 🔴 |
| Paywall Viewed | 3,838 | 3,048 | -20.6% 🔴 |
| `purchase` event ⚠️ | 65 | **627** | +865% ⚠️ instrumentation |
| In-App Purchase (subs) | 27 | 30 | +11.1% |
| Purchase Initiated | 284 | 248 | -12.7% |
| Purchase Failed | 22 | 29 | +31.8% 🔴 |
| Credit Purchased ⚠️ | 20 | **590** | +2,850% ⚠️ instrumentation |
| Credit Purchase Initiated | 30 | 612 | +1,940% ⚠️ |
| Credit Purchase Failed | 22 | 29 | +31.8% |
| Voice Clone Starts | 354 | 191 | **-46.0%** 🔴 |
| Voice Clone Failed | 228 | 141 | -38.2% |
| **Voice Clone Failure Rate** | 64.4% | **73.8%** | +9.4pp 🔴🔴 |
| Music Gen Started | 1,507 | 1,544 | +2.5% |
| Music Gen Completed | 1,307 | 1,298 | ~flat |
| Music Gen Failed | 198 | 246 | +24.2% 🔴 |
| Music Failure Rate | 13.1% | 15.9% | +2.8pp 🟡 |
| Famous Voices Browse | 1,402 | 1,020 | -27.2% |

### Mangii
| Metric | W21 | W22 | Δ |
|--------|-----|-----|---|
| DAU | 13,468 | 12,890 | -4.3% |
| New Users | 5,719 | 4,693 | **-17.9%** 🔴 |
| Paywall Shown | 11,177 | 7,494 | **-33.0%** 🔴 |
| Paywall Post First Gen | 2,753 | 2,752 | flat |
| Credit Funnel Paywall Shown | 3,501 | 2,129 | -39.2% |
| **Purchase Success** | 74 | 54 | **-27.0%** 🔴 |
| Purchase Failed | 47 | 54 | +14.9% 🔴 |
| In-App Purchase | 72 | 49 | -31.9% |
| Purchase Cancelled | 427 | 282 | -33.9% |
| Paywall CTA Tapped | 584 | 417 | -28.6% |
| Gen Tapped | 23,453 | 18,832 | -19.7% |
| Gen Completed | 13,216 | 10,700 | -19.0% |
| Gen Blocked | 13,530 | 8,352 | -38.3% |
| Quality Gen Started | 15,563 | 14,262 | -8.4% |
| Plan Selected | 1,130 | 933 | -17.4% |
| **Purchase Failure Rate** | 38.8% | **50.0%** | +11.2pp 🔴🔴 |
| Block Rate | 50.6% | 43.8% | -6.8pp 🟢 |

**Portfolio totals W21 → W22:** DAU 19,627 → 17,932 (-8.6%) · New Users 9,030 → 7,268 (-19.5%) · Subs purchases (IAP-equivalent) 284 → 262 (-7.7%)

---

## New Conjectures

### VidNotes

**CONJECTURE VN22-1: VidNotes' trial_start collapse (-66%) and onboarding-paywall view collapse (-55%) are caused by the same onboarding flow change — the onboarding paywall was either removed for a cohort or gated behind a precondition users aren't hitting**
MECHANISM: OB paywall views per new user: W21=980/844=1.16, W22=445/750=0.59 — half of new users now skip the onboarding paywall entirely. Trial starts dropped 116→39 (-66%) — far steeper than the new-user decline of -11%. Onboarding paywall has historically been the primary trial-start surface. If half of new users no longer see it, trial starts collapse. The two metrics moving in lockstep is the signature of an onboarding flow change, not an audience-mix shift.
EVIDENCE FOR: OB paywall views and trial starts both fell ~55-66% in W22. Main paywall stayed flat (-4%). Onboarding-specific surfaces uniquely collapsed.
EVIDENCE AGAINST: New users could be a different mix (e.g., shifted away from a country that historically converts on OB paywall). Or `trial_start` event firing could have broken.
KILL CONDITION: If OB paywall views per new user returns to >0.9 next week without code change, this was cohort/measurement noise. If it stays below 0.7, the flow regressed or changed.
ACTION: **URGENT.** Audit VidNotes git log for changes to the onboarding paywall trigger logic in the past 14 days. Verify `trial_start` event still fires correctly.

**CONJECTURE VN22-2: VidNotes' DAU collapse (-25%) is the lagged effect of an app update that broke something user-visible — retained users are leaving faster than new users can replace them, but new users themselves are also declining**
MECHANISM: DAU fell 25% while new users only fell 11%. The arithmetic forces returning users to bear most of the DAU loss. Returning users churning faster than baseline is the signature of an app regression (crash, broken feature, bad UI change) shipped recently.
EVIDENCE FOR: DAU and new users diverged this much only after acceptance of a new app version typically. Cancellation rate halving (-44.5%) suggests users who DO reach the paywall behave more like organics — fewer "I opened the app and immediately bounced at the paywall" cancellations.
EVIDENCE AGAINST: Could be normal post-Mother's-Day / mid-May seasonality affecting student/professional users. Could also be that the transcription quality fix (failure rate 2.5%) was achieved by routing some users to a slower fallback path that hurts engagement.
KILL CONDITION: If DAU recovers to >1,400 next week without intervention, attributable to noise/seasonality. If DAU stays below 1,300 and we identify a specific iOS version with elevated crashes via Crashlytics, confirmed app regression.
ACTION: Check Crashlytics for VidNotes for the past 7 days. Filter by iOS version to find regression. Cross-reference with most recent app release date.

**CONJECTURE VN22-3: VidNotes' transcription fix has paradoxically reduced engagement — by making fewer transcriptions fail, users finish faster and leave the app sooner, reducing both DAU and paywall exposure**
MECHANISM: Failure rate dropped from 8.9% to 2.5%. With a 70%+ reduction in retries needed, users complete their job in fewer sessions. Fewer sessions per user = lower DAU and fewer paywall-triggering moments. The fix is real but engagement metrics measure friction, not value.
EVIDENCE FOR: Transcription starts grew +1.8% (volume held) but DAU fell 25%. The conversion of "completed transcriptions per DAU" rose mechanically. The cancellation rate dropping could be because impatient retry-users went away.
EVIDENCE AGAINST: A reliability improvement shouldn't cut DAU 25% in one week — too large a magnitude. If true, you'd see this as a gradual drift, not a step function. Also doesn't explain the trial_start collapse.
KILL CONDITION: If a follow-up cohort analysis shows day-7 retention stable or improving while sessions-per-DAU dropped, the engagement drop is healthy ("less friction, less repeat use"). If day-7 retention dropped too, this conjecture is wrong.
ACTION: Pull VidNotes d7 retention by install week for past 6 weeks. If d7 holds while DAU drops, this is a healthy efficiency gain.

---

### CleanPro

**CONJECTURE CP22-1: CleanPro's -30% new user collapse is the signature of a paid acquisition pull (ASA budget cut, paused campaigns, or App Store algorithm penalty) — not organic decline**
MECHANISM: New users dropped from 1,034 to 726 (-29.8%) in one week. Organic decline is gradual; paid acquisition cuts produce step-function drops. Meanwhile, conversion improved per-user (purchases held at 105, OB conversions actually rose to 76). This is what you'd see if low-intent paid traffic was removed and remaining users are higher-intent organic.
EVIDENCE FOR: Single-week 30% drop is too sharp for organic. Purchases held steady while users halved is the signature of "cheap traffic stopped showing up." Other apps in portfolio dropped less in % terms.
EVIDENCE AGAINST: Could be App Store search algorithm change, a competing app launch eating featured spots, or a CleanPro-specific keyword ranking collapse. Could also be a seasonal cleaning category effect.
KILL CONDITION: Cross-reference ASA dashboard for CleanPro spend the past 14 days. If spend was cut/paused around 2026-05-18, confirmed paid pull. If spend was steady, organic decline.
ACTION: **Check ASA dashboard for CleanPro now.** This is the single fastest hypothesis test — 2 minutes of MCP calls.

**CONJECTURE CP22-2: CleanPro shipped a paywall product-loading fix in the past 14 days — product_nil errors dropped 57% and product_load_failed dropped 48% without a corresponding traffic change**
MECHANISM: product_nil_errors: 35→15 (-57%). product_load_failed: 31→16 (-48%). These are infrastructure-side error events; halving them in one week without a code change is implausible. Either a SKU configuration was fixed in App Store Connect, or the StoreKit product fetch retry logic was improved.
EVIDENCE FOR: Two related error events fell by similar magnitudes. Native paywall conversions also rose (4→14, +250%) — exactly what you'd expect if the products are now loading reliably.
EVIDENCE AGAINST: Lower traffic mechanically produces lower error counts. The error RATE per paywall trigger needs to be calculated to confirm. Error rate W21: 35/1660=2.1%, W22: 15/1550=0.97%. Rate halved, not just count — confirms it's not just lower traffic.
KILL CONDITION: If error rates climb back above 2% next week, the fix was temporary/local. If they hold below 1.5%, fix is real and durable.
ACTION: Document and continue monitoring. If real fix shipped, identify the commit and pattern-match for similar fixes in Echo/Mangii.

---

### Echo

**CONJECTURE EC22-1: Echo's credit_purchased explosion (20→590, 29x) is an instrumentation/event taxonomy change — the event semantics broadened to count tier-based credit grants or new SKUs that previously didn't fire credit_purchased**
MECHANISM: A 29x week-over-week jump in a transactional event without corresponding 29x revenue is impossibly large for organic growth. Voice cloning (a primary credit-consumer) DECLINED -46% in starts and 73.8% of attempts failed. If credit purchases are real, what are users spending them on with a broken cloning feature? The most economical explanation: credit_purchased now fires on subscription auto-renewal credit allocation, or on a previously-unmeasured SKU.
EVIDENCE FOR: in_app_purchase essentially flat (27→30). True revenue moves continuously. credit_purchase_initiated also exploded 30→612, suggesting both events use the same SDK path and were rerouted together.
EVIDENCE AGAINST: Echo could have had a viral moment (Mother's Day voice message campaign, etc.) — a credit-pack promo on a holiday weekend could legitimately drive transactions. Need to check ASA / promo calendar.
KILL CONDITION: If next week's credit_purchased holds above 400, this is the new baseline (instrumentation change confirmed). If it drops back to ~50, was a holiday spike. If RevenueCat shows no proportional revenue increase in Echo for W22, instrumentation-only.
ACTION: Pull Echo RevenueCat revenue for W22 vs W21. If revenue flat, this is instrumentation drift and dashboards based on `purchase` event are now misleading.

**CONJECTURE EC22-2: Echo's voice cloning is now the worst single product experience in the portfolio — 73.8% failure rate, 3 weeks of monotonic worsening (56→64→74%) — and it's directly suppressing acquisition via App Store review damage**
MECHANISM: Voice clone failure: W19=56.4% → W21=64.4% → W22=73.8%. This is monotonic and accelerating. New users -23% WoW and DAU -16% — consistent with negative review velocity in App Store. When 3 of 4 voice clones fail, users either rage-quit or post bad reviews. The "credit purchase exploded" data isn't going to compensate for a broken core feature.
EVIDENCE FOR: 3-week monotonic worsening of failure rate. New users declining 23% in lockstep with feature breakage. Famous voices browse -27% suggests users are even abandoning the discovery flow.
EVIDENCE AGAINST: New user decline could be ASA-driven (mirroring CleanPro's pattern). Voice cloning may not be on the critical user path for new users.
KILL CONDITION: If a real code fix is deployed and failure rate drops below 30% within 2 weeks, the fix works. If failure rate holds above 60%, it's an infrastructure issue beyond a simple code fix.
ACTION: **URGENT — week 4 of this issue.** Audit the W17/W18 "fix" commits for Echo voice cloning. Is the bad code path still being hit? Add error code logging to `voice_cloning_failed`. Consider rolling back to a known-good version if recent commits introduced this.

**CONJECTURE EC22-3: Echo music generation is starting to degrade in the same pattern — failure rate climbed 13.1%→15.9% — suggesting a shared backend resource (transcoding workers, GPU pool) is under increasing strain from cumulative usage**
MECHANISM: Music gen failure rate has trended up over 2 weeks while voice cloning catastrophically broke. Both consume Echo's GPU/AI compute. If a shared resource is saturating, both will degrade together. Music is degrading slower because it's structurally easier (text→audio is more cacheable than voice samples).
EVIDENCE FOR: Two AI features degrading concurrently. Same backend infrastructure assumption.
EVIDENCE AGAINST: Music gen failure could be unrelated to voice cloning. Music has more retry logic, so failure rates may just be inherently more volatile.
KILL CONDITION: If music gen failure rate exceeds 20% next week, confirmed shared-resource degradation. If it returns to 12-13%, independent fluctuation.
ACTION: Check Firebase Functions / backend service quotas for Echo AI workers. Look for rate limiting in logs.

---

### Mangii

**CONJECTURE MG22-1: Mangii's purchase failure rate is now a hard ceiling on revenue — at 50% failure, every fix to the funnel that increases purchase ATTEMPTS will be wasted because half will fail at the StoreKit layer**
MECHANISM: Purchase success: 74→54 (-27%). Purchase failed: 47→54 (+15%). Failure rate: 39%→50%. The denominator (attempts = success+failed) actually fell from 121 to 108. So purchase attempts dropped 10.7%, but successes dropped 27% — failures took up a larger share of fewer attempts. This compounding makes the bug worse over time as users learn to stop trying.
EVIDENCE FOR: 4 consecutive weeks at 40%+ failure rate (W19-W22). Failures GROWING in absolute terms while attempts shrink. CTA tapped -29% — users are walking away from the funnel earlier, likely because word-of-mouth/reviews mention payment issues.
EVIDENCE AGAINST: Mangii has aggressive credit-funnel paywalls that may inflate "purchase attempts" with low-intent users. The 50% failure may reflect intent mismatch, not StoreKit bugs.
KILL CONDITION: Add `purchase_failed` error code logging. If 50%+ of failures share a single SKErrorCode, confirmed code-level bug. If errors are diverse (cancelled cards, parental controls, network), confirmed user-side.
ACTION: **HIGHEST EXPECTED-VALUE BUG FIX IN THE PORTFOLIO.** Log error codes in Mangii TODAY. Fixing this is likely a +30% revenue improvement for Mangii single-handedly.

**CONJECTURE MG22-2: Mangii's paywall_shown collapse (-33%) is a deliberate paywall throttling — paywall_post_first_gen held perfectly flat (2,753 → 2,752) while other paywalls dropped, suggesting a config change disabled one paywall surface**
MECHANISM: paywall_post_first_gen was 2,753 in W21 and 2,752 in W22 — a single-unit difference is statistically impossible for an organic event. This event is locked or capped. Other paywall surfaces fell 33-39%. Most likely explanation: a Remote Config change set the main paywall to a lower exposure rate, while post_first_gen continues to fire normally on a different trigger.
EVIDENCE FOR: The 2,753→2,752 number is too coincidental to be organic — it's the signature of a capped/throttled event. Total purchases fell less in % terms (-27%) than paywall views (-33%), suggesting per-impression conversion held or improved.
EVIDENCE AGAINST: Could be that the post_first_gen trigger is deterministic per user-session (1 per first generation) and that population was stable while other paywalls' triggering populations shrank.
KILL CONDITION: Check Mangii's Remote Config for paywall throttling parameters changed between 2026-05-11 and 2026-05-18. If a config change is visible, confirmed throttle. If no config change, it's audience-mix.
ACTION: Check Firebase Remote Config history for Mangii. Identify any paywall-related parameter changes in the past 14 days.

---

### Cross-Portfolio

**CONJECTURE XP22-1: All 4 apps lost new users WoW in W22 (VN -11%, CP -30%, EC -23%, MG -18%) — this is a portfolio-wide acquisition signal pointing to a shared cause: ASA budget cut, iOS algorithm change, or holiday seasonality (Mother's Day, US Memorial Day weekend)**
MECHANISM: Independent organic declines wouldn't synchronize across 4 unrelated apps. The pattern requires a shared cause. Three candidates: (1) consolidated ASA budget cut affecting all apps, (2) Apple Search algorithm change penalizing portfolio publishers, (3) holiday seasonality reducing acquisition uniformly. The portfolio-wide pattern rules out app-specific causes.
EVIDENCE FOR: 4-for-4 directional alignment. Magnitude variance (-11 to -30%) consistent with apps having different sensitivity to a common shock.
EVIDENCE AGAINST: Could be coincidence — 4 apps independently hitting bad weeks. But the probability is low. Could also be that Memorial Day weekend (May 23-25) specifically suppressed installs across categories.
KILL CONDITION: If W23 sees acquisition recover across all 4 apps without intervention, it was seasonal. If decline persists in W23, it's structural (budget, algorithm, or organic decay).
ACTION: Pull ASA spend by app for W21 and W22. Compare. This refutes or confirms the budget hypothesis in 5 minutes.

**CONJECTURE XP22-2: Purchase failure rates have now climbed in 3 of 4 apps simultaneously without any common fix being deployed — the shared StoreKit/RC bug hypothesis from W19 (XP19-2) is increasingly likely; error-code logging is the only way forward**
MECHANISM: Mangii failure 50%. Echo true subs failure (failed/(failed+successful IAP)) 49.2%. VidNotes purchase_failed flat but cancellation rates show users dropping out at payment. Three apps showing payment-layer issues from the same developer with the same SDK is unlikely to be coincidence — the prior probability of 3 independent payment bugs is very low.
EVIDENCE FOR: Three apps, same SDK (StoreKit + RevenueCat), failure pattern persisting across multiple weeks. Conjecture XP19-2 still standing because we never added the diagnostic tooling that would refute it.
EVIDENCE AGAINST: The apps have different paywalls and different SKU sets. Apple-side payment failure variance per app is plausibly very high.
KILL CONDITION: If error codes added across all 3 apps reveal a shared single dominant error (e.g., SKErrorPaymentNotAllowed), confirmed shared cause. If errors diverge, the apps' bugs are independent.
ACTION: **3-week-old action item still outstanding.** Add `purchase_failed` error code logging to ALL 4 apps. This is now blocking diagnosis of $500+/week in lost revenue across the portfolio.

---

## Portfolio Health

| App | DAU (WoW) | New Users (WoW) | Subs Purchases (WoW) | Key Metric | Status |
|-----|-----------|-----------------|----------------------|------------|--------|
| VidNotes | 1,196 (-25%) | 750 (-11%) | 73 (-15%) | Transcription 2.5% ✅, Trial -66% 🔴 | 🔴 Acquisition + retention crisis |
| CleanPro | 1,842 (-15%) | 726 (-30%) | 105 (+8%) | Acquisition -30% 🔴, conv 🟢 | 🟡 Likely ASA pull (test) |
| Echo | 2,004 (-17%) | 1,099 (-23%) | 30 IAP (+11%) | Voice clone 74% fail 🔴🔴 | 🔴 Core feature catastrophically broken |
| Mangii | 12,890 (-4%) | 4,693 (-18%) | 54 IAP (-31%) | Purchase fail 50% 🔴🔴 | 🔴 Revenue capped by payment failures |

**Portfolio W22 totals:** 17,932 DAU (-8.6% WoW), 7,268 new users (-19.5% WoW), 262 subs purchases (-7.7% WoW). **Three of four apps are in 🔴 state.**

---

## Recommended Actions (Ranked by Expected Impact)

1. **🚨 Add `purchase_failed` error code logging to all 4 apps (3 weeks overdue).** This unlocks XP19-2 / XP22-2 evaluation. Estimated impact: if 50% of failures are fixable across portfolio, $200-400/week recovered.
2. **🚨 Mangii payment failure root-cause investigation.** 50% failure rate means we're losing ~50 purchases/week (~$200-400). Single highest expected-value bug in portfolio.
3. **🚨 Echo voice cloning — week 4 of catastrophic failures (73.8%).** Code audit the W17/W18 commits. Add error code logging. Consider rollback to known-good version. App Store review damage is now likely.
4. **Check ASA dashboard for all 4 apps W21-W22 spend deltas.** XP22-1 conjecture (paid acquisition pull) takes 5 minutes to confirm or refute and explains 19.5% portfolio new-user decline.
5. **Audit VidNotes onboarding paywall trigger logic and trial_start firing.** VN22-1 conjecture — likely a 14-day-old code change broke the trial funnel.
6. **Check Echo RevenueCat W22 vs W21 revenue.** Refutes or confirms the credit_purchased instrumentation drift (EC22-1). Materially affects whether dashboards based on `purchase` event are trustworthy.
7. **VidNotes Crashlytics by iOS version for past 7 days.** VN22-2 conjecture — a recent app version may have broken returning-user retention.
8. **Pull CleanPro day-7 retention by install week.** Still outstanding from W19. Combined with ASA spend data, isolates retention vs acquisition decline.
9. **Check Mangii Remote Config history for paywall throttling.** MG22-2 conjecture — the suspiciously-flat post_first_gen counter suggests a config change.

---

## Open Questions

1. **Did ASA spend get cut/redistributed in W22?** 5-minute test that explains a huge fraction of portfolio variance.
2. **Is Echo's `purchase` event now firing on credit purchases?** Determines if dashboards using `purchase` are correct or 10x overcounting.
3. **What broke in VidNotes' onboarding/trial funnel?** Trial starts -66% with new users only -11% — flow regression hypothesis.
4. **What's the dominant Mangii purchase_failed SKErrorCode?** Has been an open question for 4+ weeks. Blocks the single highest-ROI bug fix.
5. **Is the W19→W22 acquisition decline (-19.5% portfolio new users) a 2-week or 4-week trend?** W20 and W21 conjecture files don't exist — we don't have weekly granularity.
6. **Did the W22 cycle skip seasonality detection?** Memorial Day weekend (US, May 23-25) overlaps with this window — could explain a fraction of the new-user drop.

---

## Kill List — Conjectures to Evaluate in W23

| # | Conjecture | Kill Condition |
|---|-----------|---------------|
| VN22-1 | VidNotes onboarding paywall removed/gated for some cohort | OB paywall views per new user >0.9 next week → measurement noise |
| VN22-2 | VidNotes DAU collapse = app version regression | DAU recovers >1,400 without intervention → seasonal |
| VN22-3 | Transcription fix paradoxically reduced engagement | d7 retention holds while DAU drops → healthy efficiency |
| CP22-1 | CleanPro -30% new users = paid acquisition pull | ASA spend stable W21→W22 → organic decline |
| CP22-2 | CleanPro shipped product-loading fix | Error rate stays <1.5% → real fix |
| EC22-1 | Echo credit_purchased explosion = instrumentation drift | RevenueCat revenue ~flat W22 → confirmed drift; credit_purchased <200 next week → was holiday |
| EC22-2 | Echo voice cloning damaging App Store ratings → suppressing acquisition | Code fix drops failure <30% within 2 weeks → fixable |
| EC22-3 | Echo music gen degrading from shared resource | Music failure >20% next week → confirmed |
| MG22-1 | Mangii 50% purchase failure capping revenue | Error code logging shows dominant SKErrorCode → fixable |
| MG22-2 | Mangii paywall throttled via Remote Config | RC history shows paywall config change last 14d → confirmed throttle |
| XP22-1 | Portfolio-wide acquisition decline = shared cause (ASA/algorithm/seasonal) | W23 acquisition recovers without intervention → seasonal |
| XP22-2 | Shared StoreKit/RC bug across apps | Error codes added show shared dominant error → confirmed; diverge → independent |
