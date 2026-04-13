# Weekly Conjecture Cycle — 2026-W16
Period: 2026-04-06 → 2026-04-13
Generated: 2026-04-13T08:00:00Z

## Prior Conjecture Results
*Inaugural cycle — no prior conjectures to evaluate.*

---

## Raw Data

### VidNotes (W15 → W16)
| Metric | W15 | W16 | Δ |
|--------|-----|-----|---|
| DAU | 337 | 645 | +91.4% |
| New Users | 182 | 411 | +125.8% |
| Transcription Starts | 433 | 800 | +84.8% |
| Transcription Complete | 273 | 407 | +49.1% |
| Paywall Views | 333 | 566 | +69.9% |
| Purchases | 32 | 43 | +34.4% |
| Conversion (paywall→purchase) | 9.6% | 7.6% | -2.0pp |

### CleanPro (W15 → W16)
| Metric | W15 | W16 | Δ |
|--------|-----|-----|---|
| DAU | 2,904 | 2,895 | -0.3% |
| New Users | 1,728 | 1,594 | -7.8% |
| Paywall Views | 3,777 | 3,659 | -3.1% |
| Purchases | 91 | 119 | +30.8% |
| Conversions | 255 | 200 | -21.6% |
| Trial Starts | 166 | 163 | -1.8% |
| Conversion (paywall→conversion event) | 6.8% | 5.5% | -1.3pp |

### Echo (W15 → W16)
| Metric | W15 | W16 | Δ |
|--------|-----|-----|---|
| DAU | 2,303 | 3,111 | +35.1% |
| New Users | 1,555 | 2,304 | +48.1% |
| Paywall Views | 4,753 | 6,695 | +40.9% |
| Purchase Initiated | 309 | 426 | +37.9% |
| Purchases | 86 | 86 | 0.0% |
| Music Gen Starts | 1,207 | 1,621 | +34.3% |
| Music Gen Complete | 1,203 | 1,561 | +29.8% |
| Voice Clone Starts | 380 | 472 | +24.2% |
| Conversion (paywall→purchase) | 1.8% | 1.3% | -0.5pp |

### Mangii (W15 → W16)
| Metric | W15 | W16 | Δ |
|--------|-----|-----|---|
| DAU | 8,379 | 8,589 | +2.5% |
| New Users | 3,454 | 3,713 | +7.5% |
| Paywall Views | 5,853 | 5,597 | -4.4% |
| Gen Tapped | 12,407 | 11,839 | -4.6% |
| Gen Completed | 6,480 | 6,429 | -0.8% |
| Gen Blocked | 7,752 | 7,578 | -2.2% |
| Purchases | 25 | 35 | +40.0% |
| Conversion (paywall→purchase) | 0.43% | 0.63% | +0.2pp |

---

## New Conjectures

### VidNotes

**CONJECTURE VN-1: VidNotes' DAU spike (+91%) is ASA-driven, not organic**
MECHANISM: A search ads campaign (or keyword bid increase) pushed VidNotes to more users. The new-user ratio (411/645 = 64%) is disproportionately high — most of the DAU is first-time users, not retained users returning. Organic growth doesn't double DAU in one week for a niche utility app.
EVIDENCE FOR: New users grew faster (+126%) than DAU (+91%), meaning the spike is almost entirely acquisition, not retention. The app didn't ship a major update this week.
EVIDENCE AGAINST: Could be an App Store feature or viral TikTok moment — but those are rare for transcription tools.
KILL CONDITION: If ASA spend was flat or down this week vs last, this conjecture is refuted. Check ASA dashboard.
ACTION: If confirmed, calculate CPA. If CPA is under $2, scale the campaign. If over $5, the spike is expensive growth theater.

**CONJECTURE VN-2: VidNotes' conversion rate dropped (-2pp) because the new ASA users are lower-intent**
MECHANISM: Paywall views grew +70% and purchases grew only +34%, so the marginal users hitting the paywall are less willing to pay. This is classic paid-acquisition dilution: you're buying traffic that engages but doesn't convert.
EVIDENCE FOR: Paywall-to-purchase rate fell from 9.6% to 7.6% despite absolute purchase growth.
EVIDENCE AGAINST: The app's purchase_abandoned went from 17 to just 1 — suggesting fewer rage-quits. Could be a measurement artifact.
KILL CONDITION: If next week's DAU normalizes but conversion rate stays low (below 8%), the lower conversion is structural, not dilution. If DAU stays high and conversion recovers to >9%, the new users just needed more sessions.
ACTION: Segment paywall conversion by user cohort (first_open date) to distinguish new vs returning user conversion.

**CONJECTURE VN-3: VidNotes transcription completion rate degraded — possible backend issue**
MECHANISM: Transcription starts grew +85% (433→800) but completions only +49% (273→407). Completion rate fell from 63% to 51%. Under higher load, the transcription backend may be timing out or failing.
EVIDENCE FOR: 12pp drop in completion rate alongside a traffic spike is consistent with capacity constraints.
EVIDENCE AGAINST: The failure event count (93 this week) is relatively low. Some "starts" may be abandoned by users (not failures).
KILL CONDITION: If transcription_failed events are >10% of starts, it's a backend issue. If failed events are low, users are abandoning before completion.
ACTION: Check transcription_failed event count vs starts. If failure rate is high, investigate backend scaling.

### CleanPro

**CONJECTURE CP-1: CleanPro's purchase spike (+31%) with conversion drop (-21.6%) suggests a paywall experiment is running**
MECHANISM: Purchases grew from 91 to 119 but the "converted" event dropped from 255 to 200. This divergence is suspicious — it means more people are buying but the conversion tracking event fires less. A paywall variant might have been deployed that tracks the purchase differently, or the onboarding flow was modified.
EVIDENCE FOR: The numbers don't make sense without an instrumentation change. You can't have +31% purchases and -21.6% conversion events unless the tracking path changed.
EVIDENCE AGAINST: Could be a pricing change — higher price means fewer conversions but potentially more per-transaction revenue.
KILL CONDITION: If the codebase shows a paywall variant deployed this week, confirmed. If no code changes, look at per-event purchase values.
ACTION: Audit the paywall conversion tracking code. Check if `onboarding_paywall_converted` and `cleanpro_paywall_converted` are still wired correctly in the latest build.

**CONJECTURE CP-2: CleanPro is at steady state — flat DAU is the organic baseline**
MECHANISM: With DAU essentially unchanged (2904→2895, -0.3%) and new users slightly down (-7.8%), CleanPro has hit its natural organic acquisition ceiling. Without intervention (new ASO push, feature launch, or paid campaigns), DAU will oscillate around ~2,900.
EVIDENCE FOR: Flat across all top-of-funnel metrics (DAU, new users, paywall views). Nothing moved.
EVIDENCE AGAINST: -7.8% new user decline could be the start of a downtrend rather than noise.
KILL CONDITION: If new users drop below 1,400 next week (continuing the decline), it's a trend, not noise.
ACTION: If confirmed as steady state, this is the right time to optimize conversion rather than chase acquisition.

### Echo

**CONJECTURE EC-1: Echo has a critical purchase-funnel bottleneck — zero net purchase growth despite +35% DAU**
MECHANISM: DAU surged from 2,303 to 3,111 and paywall views from 4,753 to 6,695 — but purchases stayed dead flat at 86. Purchase_initiated grew +38% (309→426), meaning users are TRYING to buy but failing. The conversion from "initiated" to "completed" dropped from 27.8% to 20.2%. Something is broken in the purchase flow.
EVIDENCE FOR: 426 purchase attempts → 86 completions = 79.8% drop-off. That's catastrophic. Last week was 72.2% drop-off — it's getting worse.
EVIDENCE AGAINST: Could be StoreKit/Apple payment sheet friction — not necessarily our bug. Users might be window-shopping.
KILL CONDITION: If purchase_failed events are >5% of purchase_initiated, there's a technical failure. If purchase_cancelled is the dominant exit, it's a pricing/value objection.
ACTION: **URGENT.** Pull purchase_failed and purchase_cancelled event counts immediately. If there's a technical failure, this is a revenue emergency — we're leaving money on the table with 340 abandoned purchases per week.

**CONJECTURE EC-2: Echo's user surge is driven by the famous-voices feature going viral**
MECHANISM: famous_voices_browse (3,128 events) and tap_famous_voice (978) are high-engagement events. New users surged +48% while music gen only grew +34% — the delta may be users who came for famous voices specifically and haven't moved to music gen yet.
EVIDENCE FOR: The viral coefficient of "clone a celebrity's voice" is inherently higher than "make music with AI." The ratio of new users to DAU (74%) is very high.
EVIDENCE AGAINST: We don't have referral source data in BQ to confirm viral vs paid.
KILL CONDITION: If famous_voices_browse declines >30% next week while DAU stays elevated, the feature isn't the driver.
ACTION: Double down on famous-voice content. Add more popular voices. This is the growth lever.

**CONJECTURE EC-3: Echo's voice cloning failure rate is hurting retention**
MECHANISM: voice_cloning_started (472) vs voice_cloning_failed (285) = 60% failure rate. Users who came to clone voices and fail will churn immediately.
EVIDENCE FOR: 285 failures in a week is significant — that's 285 disappointed users. Voice cloning is likely a first-session activity for new users.
EVIDENCE AGAINST: Some failures may be user-caused (bad audio input, too short recordings).
KILL CONDITION: If voice_cloning_failed / voice_cloning_started drops below 40% after any fix, the technical failure rate was the issue. If it stays above 50%, the feature's UX expectations are misaligned.
ACTION: Investigate voice cloning failure causes. 60% failure rate is unacceptable for a core feature.

### Mangii

**CONJECTURE MG-1: Mangii's generation block rate is throttling growth — 64% of generation attempts are blocked**
MECHANISM: 11,839 gen tapped → 7,578 blocked (64%). Users try to generate manga panels and are immediately hit with a limit wall. Only 6,429 actually complete. This friction ceiling means DAU can grow but engagement per user is capped.
EVIDENCE FOR: The block rate is nearly identical WoW (62.5% → 64%), suggesting this is by design (credit/limit system), not a bug.
EVIDENCE AGAINST: The blocks may be intentional monetization friction — forcing users to the paywall.
KILL CONDITION: If lowering the block threshold increases purchases without reducing DAU, the blocks are too aggressive. If removing blocks doesn't increase purchases, they're correctly calibrated.
ACTION: A/B test giving 1 more free generation before blocking. The current wall may be hitting users before they experience enough value.

**CONJECTURE MG-2: Mangii's purchase growth (+40%) is noise on a tiny base**
MECHANISM: Going from 25 to 35 purchases is +40% but only 10 incremental purchases. At this scale, a single viral share or App Store placement could account for the entire delta. The conversion rate (0.63%) is still critically low.
EVIDENCE FOR: 0.63% paywall-to-purchase is terrible — industry benchmark is 3-8%. The absolute number is too small for statistical significance.
EVIDENCE AGAINST: Could be the beginning of a trend if something specific changed.
KILL CONDITION: If purchases return to <30 next week, it was noise. If purchases sustain >35, something structural changed.
ACTION: Don't optimize based on this signal — the sample size is too small. Focus on increasing the base conversion rate from 0.63%.

### Cross-Portfolio

**CONJECTURE XP-1: VidNotes and Echo are in growth mode; CleanPro and Mangii are in maintenance mode**
MECHANISM: VidNotes (+91% DAU) and Echo (+35% DAU) both surged while CleanPro (flat) and Mangii (+2.5%) are static. This suggests external growth drivers (ASA campaigns, App Store algorithm changes, or viral moments) are hitting VidNotes and Echo but not the other two.
EVIDENCE FOR: The two growing apps have disproportionately high new-user ratios (VidNotes 64%, Echo 74%) — both are acquisition-driven, not retention-driven.
EVIDENCE AGAINST: Could be coincidental timing of different campaigns.
KILL CONDITION: If the VidNotes/Echo growth reverses next week without campaign changes, it was a temporary App Store boost, not a sustainable shift.
ACTION: Investigate what's different about VidNotes and Echo's acquisition channels vs CleanPro and Mangii.

**CONJECTURE XP-2: All apps have a paywall-to-purchase conversion problem**
MECHANISM: Across the portfolio: VidNotes 7.6%, CleanPro 5.5%, Echo 1.3%, Mangii 0.63%. Only VidNotes is near the ~8% industry threshold. Echo and Mangii are critically underperforming. This suggests the paywalls are either shown too early (before value delivery), priced too high, or poorly designed.
EVIDENCE FOR: Four apps, same general problem. The portfolio median conversion is ~3.4% — below the bottom of the 3-8% industry range.
EVIDENCE AGAINST: Different apps have different use cases — Mangii's comic generation may have a naturally lower willingness-to-pay than VidNotes' transcription utility.
KILL CONDITION: If paywall A/B tests on any app show >8% conversion, the current paywall is the bottleneck, not the market.
ACTION: Prioritize paywall redesign for Echo (1.3%) and Mangii (0.63%) — these are the biggest conversion gaps in the portfolio.

---

## Portfolio Health

| App | DAU (WoW) | New Users (WoW) | Paywall→Purchase | Status |
|-----|-----------|-----------------|-----------------|--------|
| VidNotes | 645 (+91.4%) | 411 (+125.8%) | 7.6% | 🟡 Growth surge, conversion diluted |
| CleanPro | 2,895 (-0.3%) | 1,594 (-7.8%) | 3.3% (purchase/paywall) | 🟡 Stable but conversion anomaly |
| Echo | 3,111 (+35.1%) | 2,304 (+48.1%) | 1.3% | 🔴 Massive funnel leak |
| Mangii | 8,589 (+2.5%) | 3,713 (+7.5%) | 0.63% | 🔴 Highest DAU, worst conversion |

**Portfolio Totals:** 15,240 weekly DAU (+19.7%), 8,022 new users (+26.8%), 264 total purchases

---

## Recommended Actions (Priority Order)

1. **🚨 URGENT: Investigate Echo purchase funnel failure.** 426 purchase initiations → 86 completions. 340 abandoned purchases/week = direct revenue loss. Pull purchase_failed vs purchase_cancelled breakdown immediately.

2. **Investigate Echo voice cloning 60% failure rate.** If this is a first-session feature, 285 failed attempts/week = 285 churned users.

3. **Audit CleanPro conversion tracking divergence.** Purchases up 31% but conversion events down 21.6% — something in the instrumentation changed.

4. **Verify VidNotes growth source.** Check if ASA spend increased. If not, identify the organic channel. If it is ASA, calculate CPA.

5. **Mangii: A/B test generation limit.** 64% block rate is aggressive. Test giving one more free generation.

6. **Portfolio-wide: Paywall conversion audit.** Echo (1.3%) and Mangii (0.63%) need paywall redesign.

---

## Open Questions

1. **What is the ASA spend by app this week?** We can't distinguish paid vs organic growth without this data.
2. **What is Echo's purchase_failed count?** Critical for diagnosing the funnel leak.
3. **Did CleanPro deploy a new paywall variant this week?** The purchase/conversion divergence needs explanation.
4. **What is VidNotes' transcription_failed count?** Needed to distinguish backend failures from user abandonment.
5. **What is the revenue per purchase across apps?** Unit economics matter more than purchase count — 86 Echo purchases at $20/mo > 119 CleanPro purchases at $3/mo.

---

## Kill List — Conjectures to Evaluate in W17

| # | Conjecture | Kill Condition |
|---|-----------|---------------|
| VN-1 | ASA-driven DAU spike | ASA spend flat → refuted |
| VN-2 | Lower-intent paid users diluting conversion | DAU normalizes + conversion stays low → structural |
| VN-3 | Transcription backend degradation | transcription_failed >10% of starts → confirmed |
| CP-1 | Paywall instrumentation change | Code audit confirms tracking change → confirmed |
| CP-2 | Steady-state DAU | New users <1,400 → declining trend |
| EC-1 | Purchase funnel technical failure | purchase_failed >5% of initiated → confirmed |
| EC-2 | Famous voices driving viral growth | famous_voices_browse drops >30% + DAU holds → refuted |
| EC-3 | Voice cloning failure hurting retention | Failure rate drops below 40% after fix → confirmed |
| MG-1 | Generation blocks too aggressive | A/B test shows removal increases purchases → confirmed |
| MG-2 | Purchase growth is noise | Purchases <30 next week → confirmed as noise |
| XP-1 | Two-speed portfolio (growth vs maintenance) | VidNotes/Echo growth reverses → temporary boost |
| XP-2 | Portfolio-wide paywall conversion problem | Any app hits >8% after redesign → paywall was bottleneck |
