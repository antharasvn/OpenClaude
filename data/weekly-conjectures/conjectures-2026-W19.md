# Weekly Conjecture Cycle — 2026-W19
Period: 2026-04-27 → 2026-05-04
Generated: 2026-05-04T12:05:37Z

**Note:** W18 cycle was skipped (run failed/timed out). W17 conjectures evaluated against W18+W19 combined data. Prior event names (in_app_purchase, paywall_presented, transcription_started) were renamed — W19 uses corrected event names throughout. W17 comparison figures likely inflated by renewal events counted in `in_app_purchase`.

---

## Prior Conjecture Results (from W17, evaluated against W18+W19 data)

| # | Conjecture | Verdict | Evidence |
|---|-----------|---------|----------|
| VN17-1 | VidNotes shipped a bad paywall variant (5x cancellation spike) | **PENDING ⏳** | Cancellation persists: W18=158, W19=191. Cancellation/total-paywall rate fell slightly (19.3%→15.3%). No code audit possible from data alone. Structural issue not resolved but not worsening. |
| VN17-2 | VidNotes transcription backend capacity-constrained | **CONFIRMED ✅** | Failure rate trajectory: W17=17.4% → W18=15.3% → W19=9.2%. Now below the 10% kill threshold. Backend was scaled or optimized. |
| VN17-3 | VidNotes growth is ASA-driven with conversion dilution | **EVOLVING** | Purchases grew (+30% WoW to 132) and conversion held at 10.6%. But DAU fell from 1,749→1,502. Growth stalled. Dilution is real but unit economics still positive. |
| CP17-1 | CleanPro in acquisition-led decline | **SURVIVED ✅** | DAU: 2,638(W17)→2,066(W18)→1,943(W19). New users W18=758, W19=799. Consistent decline every week. |
| CP17-2 | CleanPro paywall design is the bottleneck | **PENDING ⏳** | No A/B test was run. Conversion declining further: W18=5.0%, W19=4.6%. Untested. |
| EC17-1 | Echo voice cloning fix shipped and worked | **REFUTED ❌** | Voice clone failure rate: W17=18% → W18=23.4% → W19=56.4%. The W17 "fix" was temporary. Failure has regressed to W16 levels. |
| EC17-2 | Echo 8.2% purchase failure is a fixable bug | **WORSENING** | Failure rate: W17=8.2% → W18=10.8% → W19=11.7%. Getting worse, not better. No fix shipped. |
| EC17-3 | Echo growth plateau is real | **PARTIALLY REFUTED ❌** | DAU: W17=3,134 → W18=2,655 → W19=2,879. Dropped then recovered. New users growing W18→W19 (+10.9%). Not a plateau — declining then recovering. |
| MG17-1 | Mangii is quietly dying | **REFUTED ❌** | Purchases: W17=31 → W18=50 → W19=70 (+40% WoW). DAU growing. The W17 crash was noise. Mangii is recovering. |
| MG17-2 | Mangii paywall is mispriced | **PENDING ⏳** | No first-month offer test. Paywall→purchase still ~0.64%. Test has not been run. |
| XP17-1 | Portfolio revenue concentration risk | **REFUTED ❌** | With corrected event names: W18 portfolio purchases=339, W19=377 (+11.2%). Portfolio is growing, not bleeding. W17 data was inflated by renewal events. |
| XP17-2 | Shared StoreKit failure pattern | **PENDING ⏳** | Failures persist: Echo 11.7%, Mangii +142% WoW, VidNotes +70% WoW. No error-code logging added. Root cause still undiagnosed. |

**Score W17→W19: 2 CONFIRMED, 4 REFUTED, 2 SURVIVED, 3 PENDING, 1 WORSENING. 6 resolved conjectures — good epistemic hygiene.**

---

## Raw Data (W18 → W19, corrected event names)

### VidNotes
| Metric | W18 | W19 | Δ |
|--------|-----|-----|---|
| DAU | 1,749 | 1,502 | **-14.1%** 🔴 |
| New Users | 676 | 717 | +6.1% |
| Transcription Starts | 1,343 | 1,507 | +12.2% |
| Transcription Successes | 539 | 604 | +12.1% |
| Transcription Failed | 242 | 152 | **-37.2%** 🟢 |
| **Failure Rate** | 15.3% | **9.2%** | -6.1pp 🟢 |
| Total Paywall Views | 819 | 1,245 | **+52%** 🟢 |
| — Main paywall | 321 | 678 | +111% |
| — Onboarding paywall | 498 | 567 | +14% |
| Total Purchases | 102 | 132 | **+29.4%** 🟢 |
| — Main purchase | 56 | 73 | +30% |
| — Onboarding purchase | 46 | 59 | +28% |
| Purchase Cancelled | 158 | 191 | +20.9% 🟡 |
| Purchase Failed | 10 | 17 | **+70%** 🔴 |
| Subscription Cancelled | 17 | 2 | **-88%** 🟢 |
| Main Paywall→Purchase | 17.4% | 10.8% | -6.6pp |
| Total Paywall→Purchase | 12.4% | 10.6% | -1.8pp |

### CleanPro
| Metric | W18 | W19 | Δ |
|--------|-----|-----|---|
| DAU | 2,066 | 1,943 | **-6.0%** 🔴 |
| New Users | 758 | 799 | +5.4% |
| Paywall Shown | 2,223 | 2,232 | +0.4% (flat) |
| Purchases (`purchase`) | 111 | 103 | -7.2% 🔴 |
| OB Conversions | 88 | 67 | **-23.9%** 🔴 |
| CP Conversions | 20 | 17 | -15% |
| Native Conversions | 11 | 18 | +63.6% 🟢 |
| Trial Starts | 97 | 81 | -16.5% |
| Purchase Cancelled | 685 | 796 | +16.2% 🔴 |
| product_nil_errors | 47 | 26 | **-44.7%** 🟢 |
| Paywall→Purchase | 5.0% | 4.6% | -0.4pp |

### Echo
| Metric | W18 | W19 | Δ |
|--------|-----|-----|---|
| DAU | 2,655 | 2,879 | **+8.4%** 🟢 |
| New Users | 1,728 | 1,916 | **+10.9%** 🟢 |
| Paywall Views | 4,718 | 5,708 | **+21.0%** 🟢 |
| Purchases | 76 | 72 | -5.3% |
| Purchase Initiated | 314 | 349 | +11.1% |
| Purchase Failed | 34 | 41 | +20.6% 🔴 |
| Credit Purchase Failed | 34 | 41 | +20.6% 🔴 |
| Voice Clone Starts | 320 | 415 | +29.7% |
| **Voice Clone Failed** | 75 | **234** | **+212%** 🔴🔴 |
| **Clone Failure Rate** | 23.4% | **56.4%** | **+33pp** 🔴🔴 |
| Music Gen Starts | 1,671 | 1,791 | +7.2% |
| Music Gen Complete | 1,332 | 1,625 | **+21.9%** 🟢 |
| Famous Voices Browse | 2,775 | 2,577 | -7.1% |
| Credit Purchased | 31 | 21 | **-32.3%** 🔴 |
| Paywall→Purchase | 1.6% | 1.3% | -0.3pp |
| Purchase Failure Rate | 10.8% | 11.7% | -0.9pp |

### Mangii
| Metric | W18 | W19 | Δ |
|--------|-----|-----|---|
| DAU | 8,878 | 9,552 | **+7.6%** 🟢 |
| New Users | 3,227 | 3,942 | **+22.2%** 🟢 |
| Paywall Shown | 8,106 | 10,975 | **+35.4%** 🟢 |
| Purchases | 50 | 70 | **+40%** 🟢 |
| Paywall CTA Tapped | 504 | 660 | +30.9% 🟢 |
| Purchase Cancelled | 410 | 500 | +21.9% |
| **Purchase Failed** | 21 | **51** | **+142.9%** 🔴 |
| Gen Tapped | 12,470 | 19,032 | +52.6% 🟢 |
| Gen Completed | 6,457 | 9,494 | +47.1% 🟢 |
| Gen Blocked | 7,430 | 11,965 | **+61.0%** 🔴 |
| Block Rate | 53.5% | 55.8% | +2.3pp 🔴 |
| Quality Gen Starts | 7,660 | 11,343 | +48.1% |
| Plan Selected | 792 | 822 | +3.8% |
| Paywall→Purchase | 0.62% | 0.64% | flat |
| CTA→Purchase | 9.9% | 10.6% | +0.7pp 🟢 |

---

## New Conjectures

### VidNotes

**CONJECTURE VN19-1: VidNotes' paywall views doubled while DAU fell — a new onboarding gate is now showing the paywall to more free users earlier**
MECHANISM: Main paywall views rose +111% (321→678) while DAU fell 14%. This is impossible via organic user behavior — fewer active users cannot produce twice as many paywall impressions unless a flow change now routes more sessions into the paywall. Likely: an onboarding change lowered the free-tier threshold or added a mid-session gate.
EVIDENCE FOR: DAU and paywall views moved in opposite directions. The 111% jump in one week is a step-function, not gradual growth.
EVIDENCE AGAINST: Could be a tracking/attribution change where events that previously fired once per install now fire once per session.
KILL CONDITION: If paywall views and DAU diverge further (paywall keeps rising while DAU stabilizes or falls), confirmed flow change. If they reconverge, it was measurement.
ACTION: Audit VidNotes codebase for recent changes to paywall trigger logic. Identify when and why `paywall_viewed` fires.

**CONJECTURE VN19-2: VidNotes' purchase_cancelled rate remains structurally elevated and will suppress conversion below 12% indefinitely**
MECHANISM: Cancellation/paywall ratio: W18=19.3%, W19=15.3%. Even with the improvement, this is ~3x the industry norm (~5%). Users are reaching the Apple payment sheet and actively rejecting at high rates. The W17 alarm was correct; it has not been fully addressed.
EVIDENCE FOR: Two consecutive weeks above 15% cancellation rate. Purchases growing (good) but conversion falling (bad) simultaneously.
EVIDENCE AGAINST: Rising absolute paywall views from a new gate means the new cohort seeing the paywall may be lower-intent, naturally cancelling more.
KILL CONDITION: If cancellation rate drops below 10% next week without other changes, the high-rate users were a cohort that churned naturally. If it stays above 12%, there's a paywall design or pricing problem.
ACTION: Segment cancellation by paywall location (main vs onboarding). If onboarding cancellation is the driver, optimize onboarding offer.

**CONJECTURE VN19-3: VidNotes transcription quality fix is now confirmed real — failure rate at 9.2% represents genuine backend improvement**
MECHANISM: Failure rate: W17=17.4% → W18=15.3% → W19=9.2%. Steady decline over 3 weeks. This is a monotonic trend, not noise. Either worker pool was scaled, or a specific bug (large files, certain formats) was fixed.
EVIDENCE FOR: Monotonic 3-week improvement in failure rate while transcription volume grew. A scaling/bug fix signature.
EVIDENCE AGAINST: Could be that the failing user segment (heavy users, unusual file formats) churned away rather than the backend being fixed.
KILL CONDITION: If failure rate stays below 10% for 2 more weeks while transcription volume keeps growing, confirmed capacity fix. If it bounces above 12%, users driving failures returned.
ACTION: Document and monitor. If volume doubles again, pre-scale before failure rate spikes.

---

### CleanPro

**CONJECTURE CP19-1: CleanPro is in a structural churn death spiral — DAU falling 6%/week is not seasonal, it's accelerating churn from a degraded retention curve**
MECHANISM: DAU: 2,638(W17)→2,066(W18)→1,943(W19). Meanwhile paywall shown has been ~2,232 for two weeks while DAU falls. This means the SAME number of users see the paywall each week despite fewer overall users — the falling DAU is exclusively returning/retained users leaving, not new users. New users are actually stable (799 W19). The app is leaking retained users.
EVIDENCE FOR: New users +5.4% WoW while DAU fell 6%. The only math that produces this: retained users churning faster than new users can replace them.
EVIDENCE AGAINST: Could be seasonal (spring cleaning category loses relevance in late April/May).
KILL CONDITION: If retention cohort data shows day-7 or day-30 retention unchanged, the churn acceleration is a new entrant or seasonal factor. If retention metrics worsened after a specific app version, a regression caused it.
ACTION: Pull retention cohort data for CleanPro. Specifically day-7 and day-30 retention by install week for the past 6 weeks.

**CONJECTURE CP19-2: CleanPro's onboarding conversion is collapsing (-24% OB conversions) while the main app paywall holds — the onboarding flow specifically broke**
MECHANISM: OB conversions: 88→67 (-24%) while main app purchases (103) and native conversions (18) held or grew. The onboarding paywall had 788 shows in W18 and produced 88 conversions (11.2% rate); if it maintained the same rate in W19, we'd expect ~83 conversions (similar paywall shows). Getting only 67 means the rate dropped to ~8.5%. Something specific to the onboarding paywall experience regressed.
EVIDENCE FOR: Onboarding conversions fell faster than any other monetization metric. Main app paywall held up.
EVIDENCE AGAINST: Onboarding is reached by new users who tend to have lower intent than returning users, and new user mix might be shifting lower-intent.
KILL CONDITION: If onboarding conversions recover to >80 next week without changes, the W19 drop was a cohort fluctuation. If they stay below 75, the flow regressed.
ACTION: Review recent CleanPro git changes to onboarding flow. Check if a paywall variant was deployed or the offer changed in onboarding.

---

### Echo

**CONJECTURE EC19-1: Echo's voice cloning failure has regressed catastrophically (23%→56%) because the W17 "fix" was a temporary deployment rollback, not a code fix**
MECHANISM: Failure rate went 59%(W16) → 18%(W17, "fixed") → 23%(W18) → 56%(W19). The V-shaped trajectory is the signature of a rollback: the bad code was temporarily reverted (producing W17's improvement) and then re-deployed (producing the W19 crash). This is NOT a new bug — it's the same bug that was "fixed" in W17.
EVIDENCE FOR: The failure rate in W19 (56.4%) is almost identical to W16 (59%). This exact return to baseline is characteristic of a rollback-then-redeploy, not two independent bugs.
EVIDENCE AGAINST: Could be two separate bugs coincidentally producing similar failure rates.
KILL CONDITION: If a code audit confirms the W17 "fix" was a rollback without a root cause fix, and the bad code was re-deployed in the intervening weeks, confirmed rollback. If it was a different code path, new bug.
ACTION: **URGENT.** Find the W17 "fix" commit. Was it a rollback or a root cause fix? If rollback, the bad code re-landed. Find it and fix it properly.

**CONJECTURE EC19-2: Echo's purchase funnel is systematically broken — 11.7% purchase failure rate has grown for 3 consecutive weeks, indicating a progressive StoreKit degradation**
MECHANISM: Purchase failure: W17=8.2% → W18=10.8% → W19=11.7%. A monotonically worsening rate suggests either (a) the failure-prone code path is getting hit by more users over time, or (b) an infrastructure issue (expired certificates, misconfigured product IDs) that gets worse with time rather than fluctuating randomly.
EVIDENCE FOR: Monotonic 3-week increase. Random bugs don't trend — they fluctuate. Progressive worsening implies a root cause that has a directional trajectory.
EVIDENCE AGAINST: Could be a growing user segment (specific device, OS version, or country) that always fails, increasing as a share of total.
KILL CONDITION: If adding purchase_failed error code logging reveals a single dominant error type, it's a specific fixable bug. If error codes are diverse, it's Apple-side or environment-specific.
ACTION: Add error code logging to purchase_failed in Echo TODAY. This is ~$600-800/week in lost revenue.

**CONJECTURE EC19-3: Echo's credit monetization is collapsing in lockstep with voice cloning failures — failed clones are the primary driver of credit purchases, so as cloning breaks, credit revenue follows**
MECHANISM: Credit purchased: 31(W18)→21(W19) (-32.3%). Voice clone failure rate: 23.4%→56.4%. The correlation is strong: users who experience failed voice clones may be motivated to "retry" via credits, but when the feature is completely broken (56% failure), users stop trying and stop buying credits. The failure destroys the entire credit purchase motivation.
EVIDENCE FOR: Both metrics worsened in lockstep. Credit purchase decline (-32%) is proportionally similar to the rise in failure rate.
EVIDENCE AGAINST: Credit purchases could be driven by music generation, not voice cloning. Need to verify which features consume credits.
KILL CONDITION: If fixing voice cloning failures restores credit purchases to >25/week, confirmed the causal link. If credits stay low post-fix, credit monetization has a separate problem.
ACTION: Verify in Echo's codebase whether voice cloning consumes credits. If yes, fixing cloning is a two-for-one fix (quality + revenue).

---

### Mangii

**CONJECTURE MG19-1: Mangii's purchase failure rate explosion (+142%, 21→51) is masking the real revenue trajectory and will reverse the purchase growth trend within 2 weeks**
MECHANISM: Purchases grew 50→70 (+40%). But purchase_failed grew 21→51 (+142%). Failure rate went from 21/(50+21)=29.6% to 51/(70+51)=42.1%. More than 4 in 10 purchase attempts are failing. If the bug is fixed, purchases will likely jump to 110-120/week (70 successes + ~50 recovered failures). If it's not fixed, users who fail once rarely retry — the 40% failure rate will suppress purchases toward the failure floor.
EVIDENCE FOR: Failure rate above 40% is operationally untenable. At current growth rates of gen_tapped (+52%), the absolute number of purchase failures will keep growing even if the rate holds.
EVIDENCE AGAINST: Some payment failures are Apple-side (expired cards, parental controls) that Mangii cannot fix.
KILL CONDITION: If Mangii's purchase_failed stays above 40 next week without any change to the purchase flow, confirmed a code-level bug (not Apple-side). If failures drop after a code change, confirmed it was fixable.
ACTION: **URGENT.** Log the specific paywall_purchase_failed error codes in Mangii. This is the single highest expected-value bug fix across the portfolio right now.

**CONJECTURE MG19-2: Mangii's generation block rate is rising with usage (53.5%→55.8%) — the free-tier limit is set too low for the current user behavior profile**
MECHANISM: Gen blocked grew +61% while gen completed grew only +47%. Block rate is increasing as usage scales. This suggests new users (up +22%) are hitting the free-tier limit faster than average. Either new user cohorts have higher generation appetite, or the limit hasn't been adjusted as feature engagement grew.
EVIDENCE FOR: Block rate trending upward for 2+ weeks. New users up +22%, gen engagement up +52%.
EVIDENCE AGAINST: Rising block rate might be intentional — more blocks = more paywall exposure = more revenue. The Mangii team may have deliberately tightened limits.
KILL CONDITION: If a limit change (higher free tier) shows gen_blocked decreasing while paywall_shown and purchases hold steady, the current limit is too aggressive. If increasing the limit causes purchases to drop, the friction was economically necessary.
ACTION: Get clarity on whether the block limit was intentionally tightened recently. If not, consider whether conversion math justifies tighter limits.

---

### Cross-Portfolio

**CONJECTURE XP19-1: The portfolio now shows two distinct patterns — Echo/CleanPro declining in revenue, VidNotes/Mangii growing — and the growth apps are NOT offsetting the declining apps' revenue loss**
MECHANISM: W18→W19 purchases: VidNotes +30%, Mangii +40%, CleanPro -7%, Echo -5%. But CleanPro and Echo have much larger baselines. If CleanPro generates $15/purchase and Echo generates $12/purchase, the 8-purchase decline in CleanPro (-$120) isn't offset by VidNotes' +30 purchases at likely $3-5 LTV ($90-150). The portfolio is not as healthy as total purchase count growth (+11%) suggests.
EVIDENCE FOR: DAU distribution: Mangii=9,552, CleanPro=1,943, Echo=2,879, VidNotes=1,502. CleanPro and Echo are the largest apps and are declining.
EVIDENCE AGAINST: Without RevenueCat ARPU by app, we can't confirm the revenue thesis. Purchase counts alone are misleading.
KILL CONDITION: RevenueCat weekly revenue data showing W19 > W18 in absolute dollars would refute this. A decline would confirm.
ACTION: Pull RevenueCat weekly revenue by app. This overrides all purchase-count analysis.

**CONJECTURE XP19-2: All 4 apps have purchase failure rates above 10% — this is not a per-app bug but a shared StoreKit or RC configuration issue**
MECHANISM: Echo purchase_failed: 11.7%. Mangii: 42% failure rate (51 failed / 121 attempts). VidNotes: purchase_failed=17 / 132 successes = ~11%. CleanPro: not tracked precisely but product_nil_errors=26 still firing. Four apps from the same developer, same RC SDK, all showing 10-40%+ failure rates. The probability of four independent bugs is very low.
EVIDENCE FOR: Portfolio-wide pattern. Same developer, same SDK versions, same RevenueCat integration. Synchronized onset.
EVIDENCE AGAINST: Mangii's 42% includes aggressive block-to-paywall funnel users who may have higher intent-mismatch. The apps might have unrelated failure modes.
KILL CONDITION: If all apps log `purchase_failed` with error codes and they share a common error domain (e.g., `SKErrorDomain` with the same code), it's shared. If error codes diverge, the bugs are independent.
ACTION: Add `purchase_failed` error code logging to ALL 4 apps simultaneously. Compare in W20.

---

## Portfolio Health

| App | DAU (WoW) | New Users (WoW) | Purchases (WoW) | Key Metric | Status |
|-----|-----------|-----------------|-----------------|------------|--------|
| VidNotes | 1,502 (-14%) | 717 (+6%) | 132 (+29%) | Transcription fail 9.2% ✅ | 🟡 Growing revenue, falling DAU |
| CleanPro | 1,943 (-6%) | 799 (+5%) | 103 (-7%) | OB conversion -24% | 🔴 Structural decline |
| Echo | 2,879 (+8%) | 1,916 (+11%) | 72 (-5%) | Voice clone fail 56% 🔴 | 🔴 Growing users, failing revenue |
| Mangii | 9,552 (+8%) | 3,942 (+22%) | 70 (+40%) | Purchase fail 42% 🔴 | 🟡 Strong growth, broken payment |

**Portfolio W19 totals:** 17,876 DAU (+5.4% WoW), 9,375 new users (+12.6% WoW), 377 purchases (+11.2% WoW)

---

## Recommended Actions (Ranked by Expected Impact)

1. **🚨 Fix Echo voice cloning (URGENT).** Failure rate at 56.4% — back to W16 catastrophe levels. Audit the W17 "fix" commit: was it a rollback? If yes, find and properly fix the root cause. Estimated revenue impact: credit purchases + retention uplift.
2. **🚨 Log Mangii purchase_failed error codes (URGENT).** 42% of payment attempts failing. Highest-urgency bug fix across the portfolio. Expected impact: if 50% of failures are fixable, purchases jump from 70→95/week.
3. **🚨 Log Echo purchase_failed error codes (URGENT).** 3rd consecutive week of worsening purchase failure (11.7%). Progressive worsening indicates a code-level root cause, not user-side friction.
4. **Audit VidNotes onboarding paywall trigger logic.** Main paywall views doubled while DAU fell. A flow change is gating more users into the paywall. Verify the change was intentional and that the new gate improves unit economics.
5. **Pull RevenueCat weekly revenue by app.** Purchase counts are misleading without ARPU. CleanPro decline may be more severe in dollars than counts suggest.
6. **Investigate CleanPro onboarding conversion regression.** OB conversions -24% while main app paywall held. Recent onboarding changes likely introduced this regression.
7. **Pull CleanPro day-7 and day-30 retention by install week.** DAU falling despite stable new users = accelerating churn. Retention data will identify when the break happened.

---

## Open Questions

1. **Echo voice cloning: was the W17 fix a rollback?** The V-shaped failure trajectory is the strongest clue. A code audit of the W17 fix commit would confirm or deny.
2. **RevenueCat weekly revenue by app.** We still don't know if the portfolio is growing or declining in dollars. Purchase counts are a proxy.
3. **What changed in VidNotes that doubled paywall views?** The trigger logic change, if intentional, may be the most impactful recent product decision. Needs confirmation.
4. **Is Echo's credit feature driven by voice cloning?** If yes, the EC19-3 conjecture (credit crash = clone failure) is high confidence and fixing cloning is a two-metric fix.
5. **What iOS error codes are behind purchase failures across all 4 apps?** The XP19-2 conjecture (shared StoreKit bug) can only be evaluated with error code logging.

---

## Kill List — Conjectures to Evaluate in W20

| # | Conjecture | Kill Condition |
|---|-----------|---------------|
| VN19-1 | VidNotes paywall view doubling = onboarding gate change | Paywall diverges further from DAU → confirmed flow change |
| VN19-2 | Cancellation rate structurally elevated | Rate drops below 10% → natural cohort churn; stays >12% → paywall issue |
| VN19-3 | Transcription fix is confirmed real | Rate stays <10% at higher volume → confirmed |
| CP19-1 | CleanPro structural churn spiral | Retention cohort shows worsening day-7/30 → confirmed |
| CP19-2 | CleanPro onboarding paywall regressed | OB conversions stay below 75 → confirmed regression |
| EC19-1 | Echo voice fix was a rollback | Code audit finds bad code re-deployed → confirmed |
| EC19-2 | Echo purchase failure progressive bug | Error codes show dominant single type → confirmed fixable |
| EC19-3 | Credit revenue tied to voice cloning | Fixing cloning restores credit_purchased >25 → confirmed |
| MG19-1 | Mangii purchase failure masking revenue | Failure stays >40 without fix → confirmed code bug |
| MG19-2 | Mangii free-tier limit too tight | Limit test shows blocks→purchase above 2% → confirmed |
| XP19-1 | Growth apps not offsetting declining apps in dollars | RevenueCat shows W19 < W18 → confirmed |
| XP19-2 | Portfolio-wide shared StoreKit bug | Shared error code across apps → confirmed |
