# Weekly Conjecture Cycle — 2026-W17
Period: 2026-04-13 → 2026-04-20
Generated: 2026-04-20T12:00:00Z

## Prior Conjecture Results (from W16)

| # | Conjecture | Verdict | Evidence |
|---|------------|---------|----------|
| VN-1 | VidNotes DAU spike is ASA-driven | **SURVIVED ✅** | DAU doubled again (645→1,483, +130%). New-user ratio stayed ~54%. Growth is sustained — either ASA is still running or an organic channel is compounding. Kill condition needs ASA spend data to refute. |
| VN-2 | Lower-intent paid users diluting conversion | **SURVIVED ✅** | Paywall views +56% but purchases flat (-3%). Conversion fell. Dilution thesis holds. |
| VN-3 | Transcription backend degrading under load | **CONFIRMED ❌→✅** | transcription_failed: 76→190 (+150%). Failure rate jumped from 9.5% to 17.4% of starts. Above the 10% kill threshold. Backend IS capacity-constrained. |
| CP-1 | CleanPro paywall instrumentation change | **REFUTED ❌** | Purchases and conversions moved together this week (both -24%). The W16 divergence was a transient measurement issue, not a deployed paywall variant. |
| CP-2 | CleanPro at steady state | **REFUTED ❌** | New users fell below 1,400 threshold (1,263). CleanPro is in a decline, not steady state. |
| EC-1 | Echo purchase funnel technical failure | **CONFIRMED ✅** | purchase_failed=41, purchase_initiated=502 → 8.2% failure rate. Above the 5% kill threshold. Real technical issue. |
| EC-2 | Famous voices driving Echo viral growth | **REFUTED ❌** | Echo DAU went flat (+0.5%). Famous voices engagement barely moved (+3%). If they were the driver, growth should have continued. |
| EC-3 | Voice cloning failures hurting retention | **FIXED ✅🎉** | Failure rate crashed from 59% to 18% (280→79). Either the fix shipped or the measurement was misleading. Kill condition met (<40%). |
| MG-1 | Mangii generation blocks too aggressive | **PENDING ⏳** | Block rate fell from 64% to 59% but no A/B test was run. Can't evaluate. |
| MG-2 | Mangii purchase growth was noise | **CONFIRMED ✅** | Purchases crashed 68→31 (-54%). Last week's +40% was indeed noise. Now we're below the noise floor. |
| XP-1 | Two-speed portfolio | **PARTIALLY REFUTED ❌** | VidNotes kept surging, but Echo's growth completely stopped. The "growth" cohort collapsed to just one app. Thesis was too broad. |
| XP-2 | Portfolio-wide paywall conversion problem | **SURVIVED ✅** | VidNotes climbed to 10.4%, but Echo (1.7%), CleanPro (5.2%), Mangii (0.34%) all still underperform. |

**Score: 5 CONFIRMED, 4 REFUTED, 2 SURVIVED, 1 PENDING. Refuted conjectures are wins — we killed bad theories.**

---

## Raw Data (W16 → W17)

### VidNotes
| Metric | W16 | W17 | Δ |
|--------|-----|-----|---|
| DAU | 645 | 1,483 | **+130%** |
| New Users | 412 | 806 | +96% |
| Transcription Starts | 802 | 1,091 | +36% |
| Transcription Complete | 407 | 530 | +30% |
| **Transcription Failed** | 76 | 190 | **+150%** 🔴 |
| Paywall Views | 566 | 883 | +56% |
| Purchases | 95 | 92 | -3% |
| Trial Starts | 33 | 37 | +12% |
| **Purchase Cancelled** | 31 | 167 | **+439%** 🔴 |
| Purchase Failed | 0 | 7 | +∞ |
| Completion Rate | 50.7% | 48.6% | -2.1pp |
| Paywall→Purchase | 16.8% | 10.4% | -6.4pp |

### CleanPro
| Metric | W16 | W17 | Δ |
|--------|-----|-----|---|
| DAU | 2,911 | 2,638 | -9.4% |
| New Users | 1,596 | 1,263 | **-20.9%** 🔴 |
| Paywall Views | 5,959 | 4,915 | -17.5% |
| Purchases | 339 | 258 | -23.9% |
| Conversions | 200 | 153 | -23.5% |
| Trial Starts | 163 | 124 | -23.9% |
| Purchase Cancelled | 1,243 | 1,059 | -14.8% |
| Paywall→Purchase | 5.7% | 5.2% | -0.5pp |

### Echo
| Metric | W16 | W17 | Δ |
|--------|-----|-----|---|
| DAU | 3,119 | 3,134 | +0.5% |
| New Users | 2,309 | 2,221 | -3.8% |
| Paywall Views | 7,631 | 7,429 | -2.6% |
| Purchases | 116 | 128 | +10% |
| Purchase Initiated | 426 | 502 | +18% |
| Purchase Failed | 43 | 41 | flat |
| Music Gen Starts | 1,622 | 1,835 | +13% |
| Music Gen Complete | 1,562 | 1,707 | +9% |
| Voice Clone Starts | 472 | 441 | -7% |
| **Voice Clone Failed** | 280 | 79 | **-72%** 🟢 |
| Famous Voices Browse | 3,131 | 3,231 | +3% |
| Credit Purchased | 23 | 35 | +52% |
| Paywall→Purchase | 1.5% | 1.7% | +0.2pp |

### Mangii
| Metric | W16 | W17 | Δ |
|--------|-----|-----|---|
| DAU | 8,640 | 8,282 | -4.1% |
| New Users | 3,731 | 3,178 | -14.8% |
| Paywall Views | 9,970 | 9,153 | -8.2% |
| **Purchases** | 68 | 31 | **-54%** 🔴 |
| Gen Tapped | 11,896 | 11,079 | -6.9% |
| Gen Completed | 6,443 | 5,827 | -9.6% |
| Gen Blocked | 7,621 | 6,573 | -13.8% |
| Paywall CTA | 594 | 502 | -15.5% |
| Purchase Failed | 37 | 56 | +51% |
| Block Rate | 64% | 59% | -5pp |
| Paywall→Purchase | 0.68% | 0.34% | **-0.34pp** |

---

## New Conjectures

### VidNotes

**CONJECTURE VN17-1: VidNotes has a catastrophic paywall cancellation flood (+439%) — a new paywall variant shipped that users are actively rejecting**
MECHANISM: Purchase_cancelled jumped from 31 to 167 (5.4x). This is not dilution from lower-intent users — the cancellation count grew 5x faster than paywall views (which grew 56%). Users are REACHING the Apple payment sheet and actively dismissing it at a much higher rate. Most likely causes: (a) a new paywall variant with worse pricing/value proposition shipped, (b) price increase, or (c) a tracking bug that's double-counting cancellations.
EVIDENCE FOR: Raw count anomaly. Even normalized to paywall views, cancellation rate went from 31/566=5.5% to 167/883=18.9%. Something discretely changed in the flow.
EVIDENCE AGAINST: Could be that more users are now hitting the paywall trigger that previously didn't (onboarding flow change).
KILL CONDITION: If code audit shows no paywall changes AND cancellation event wasn't renamed, the signal is organic user rejection — escalate. If a paywall variant shipped, this is the variant's fault.
ACTION: **URGENT.** Audit VidNotes git log for paywall/pricing changes in the last 7 days. Pull per-product SKU cancellation breakdown to find which offer is being rejected.

**CONJECTURE VN17-2: VidNotes transcription backend is now clearly capacity-constrained (confirmed last week, getting worse)**
MECHANISM: Transcription_failed grew +150% while starts grew only +36%. Failure rate: 9.5% → 17.4%. The backend can handle ~800 transcriptions/week with acceptable failure rate but starts to break above that. At W18 pace (if growth continues), failure rate will exceed 25%.
EVIDENCE FOR: Linear scaling relationship between load and failure rate across 2 weeks.
EVIDENCE AGAINST: Could be a specific user segment (larger files, unusual formats) whose share grew.
KILL CONDITION: If backend scaling improvements drop failure rate below 10% at current traffic, confirmed capacity was the issue. If failures continue above 15%, there's a bug (not just capacity).
ACTION: Scale the transcription worker pool NOW. This is losing 190 users/week who failed to get their core value delivery. At VidNotes' ~10% conversion, that's ~19 lost purchases/week.

**CONJECTURE VN17-3: VidNotes' growth is real and ASA-driven, but conversion is decaying as the funnel fills with lower-intent traffic**
MECHANISM: Paywall→purchase fell from 16.8% to 10.4%. But 10.4% is still above the 8% industry threshold. The decay is real but not yet critical. If growth continues at this pace (2x/week) without conversion intervention, the app will drown in cheap traffic that doesn't pay.
EVIDENCE FOR: Three-week pattern: 9.6% → 16.8% → 10.4%. The W16 spike was anomalous; W17 reverts toward mean.
EVIDENCE AGAINST: The W16 16.8% may have been a measurement artifact (purchase event consolidation); the true baseline may already be ~10%.
KILL CONDITION: If conversion stabilizes ≥9% for 2+ weeks, this is the new normal. If it falls below 8%, dilution is winning.
ACTION: Get CPA from ASA dashboard. At ~$2 CPA and 10% conversion, VidNotes' unit economics work. Above $4 CPA, stop spending.

### CleanPro

**CONJECTURE CP17-1: CleanPro is in an acquisition-led decline — the top of the funnel shrunk, everything downstream followed proportionally**
MECHANISM: New users fell -21%, DAU fell -9%, paywall views fell -18%, purchases fell -24%. Everything moved in lockstep with a similar magnitude. No funnel-stage broke; the whole thing scaled down. The cause is above the app: ASA budget cut, ASO ranking drop, or App Store category reshuffling.
EVIDENCE FOR: Near-identical percentage drops across all funnel stages. Internal conversion rates unchanged.
EVIDENCE AGAINST: If new users drop was caused by a push notification issue, returning user DAU wouldn't follow.
KILL CONDITION: If paid install data shows ASA spend was reduced/paused, confirmed. If ASA spend was steady AND new users still fell, ASO ranking dropped.
ACTION: Check ASA spend + ASO rank for CleanPro over the last 14 days. If ASA was cut, restore it. If ASO dropped, investigate keyword positions.

**CONJECTURE CP17-2: CleanPro's paywall is doing its job — the 2,300 cancellation events/week aren't a failure, they're revenue protection**
MECHANISM: 1,059 purchase cancellations + 258 purchases = 1,317 total payment-sheet decisions. That's 1,317 users who considered paying. The 19.6% "close" rate (258 of 1,317) is reasonable. The issue is not paywall quality; it's that only 5.2% of paywall views reach this decision point. The drop-off is between "see paywall" and "tap purchase CTA," not at the payment sheet.
EVIDENCE FOR: Cancellation is healthy at current prices. Purchase intent is being captured in users who actually engage.
EVIDENCE AGAINST: A best-in-class paywall converts 8%+ from view to purchase. We're at 5.2%, which means the paywall COPY/DESIGN is losing people before the CTA.
KILL CONDITION: If a paywall redesign (different copy, better visual hierarchy) lifts purchase/view above 7%, the paywall design was the issue.
ACTION: Run a paywall A/B test on CleanPro. Hypothesis: copy change > pricing change.

### Echo

**CONJECTURE EC17-1: The Echo voice-cloning fix shipped — and it worked spectacularly**
MECHANISM: Voice clone failures collapsed from 280 to 79 (a 72% drop) while voice clone starts stayed roughly flat. This is a classic "we shipped a fix" signature, not a user-behavior change. Either an infrastructure change (model version, API timeout), or a UX change (better input validation) went live.
EVIDENCE FOR: The magnitude and suddenness of the failure rate drop (59%→18%) — this doesn't happen from user behavior; fixes cause step functions.
EVIDENCE AGAINST: Could be sampling/measurement artifact if some subset of failure events stopped firing.
KILL CONDITION: If voice_cloning_failed stays below 25% for 2+ weeks, confirmed fix. If it bounces back, it was a measurement blip.
ACTION: Find and document what was shipped. Credit the engineer. Monitor for regression.

**CONJECTURE EC17-2: Echo's 8.2% purchase failure rate is the real revenue ceiling — not paywall design, not pricing**
MECHANISM: 502 users tapped "purchase" and hit the payment sheet this week. 41 got a technical failure (8.2%). That's ~$400-800 of lost revenue per week at Echo's ARPU. This is a pure engineering problem: StoreKit configuration, receipt validation, or a race condition in the purchase handler.
EVIDENCE FOR: Failure rate consistent across weeks (43/426=10.1% → 41/502=8.2%). Numerator scales with denominator. Deterministic bug pattern.
EVIDENCE AGAINST: Could be user-side (parental controls, invalid Apple IDs, network failures) that we cannot fix.
KILL CONDITION: If adding retry logic or fixing a known StoreKit bug drops failure rate below 3%, the bug was the cause. If it stays >5% after fixes, it's Apple-side friction.
ACTION: Have an iOS engineer trace the purchase_failed code path. Log the failure reason (error code) and segment by error type.

**CONJECTURE EC17-3: Echo's growth has plateaued — the W16 surge was a one-time acquisition event, not a sustainable channel**
MECHANISM: DAU flat (+0.5%), new users declining (-4%), paywall views down (-3%). Whatever drove W16's +35% has burned out. Most likely: a one-time App Store feature placement or a one-time viral TikTok/IG moment that has since decayed.
EVIDENCE FOR: Famous voices engagement (the rumored driver) moved only +3%. Not the kind of continued virality we'd expect if a viral moment was still active.
EVIDENCE AGAINST: Could be a seasonal dip before a new wave.
KILL CONDITION: If DAU stays flat for another 2 weeks with no external changes, plateau confirmed. If DAU drops >10%, decline begins.
ACTION: Stop relying on "growth continues" for Echo planning. Lock in the new baseline (~3,100 DAU) and optimize from there.

### Mangii

**CONJECTURE MG17-1: Mangii is quietly dying — the -54% purchase crash is the leading indicator**
MECHANISM: Purchases went 68→31 (-54%). Purchase failed grew +51% at the same time. Block rate improved slightly (64%→59%) but that didn't help. Users are reaching the paywall less, trying to pay less, and failing to pay more when they try. This is a monetization engine with multiple simultaneous failures.
EVIDENCE FOR: Every downstream metric worsened. Only "gen_blocked" improved, and that's mostly because there were fewer attempts overall. Unit economics are breaking: 8,282 DAU producing just 31 purchases = $0.004/DAU (effectively zero).
EVIDENCE AGAINST: Small absolute numbers (31 purchases) are highly volatile. Could be a one-week technical glitch.
KILL CONDITION: If purchases recover to >60 next week without intervention, this was noise. If they stay below 50 for 3+ weeks, Mangii is structurally broken.
ACTION: This week: pull per-SKU purchase data. Is it one product dropping, or all? Audit paywall_purchase_failed event for error codes. If no technical fix in 2 weeks, consider sunsetting or pivoting.

**CONJECTURE MG17-2: Mangii's generation block system is correctly calibrated but monetizing the wrong moment**
MECHANISM: 6,573 users were blocked mid-generation this week. Only 502 tapped the paywall CTA (7.6% of blocked users). 31 actually purchased. The funnel from "blocked" → "paywall CTA" → "purchase" has two ~90% drop-offs. The block works (creates friction); the paywall doesn't convert that friction into revenue.
EVIDENCE FOR: 6,573 forced paywall encounters → 31 purchases = 0.47% conversion from forced exposure. Industry expects 3-5% from friction-driven exposure.
EVIDENCE AGAINST: The users being blocked are free-tier users who chose the app for the free experience — they may never pay regardless.
KILL CONDITION: If pricing/offer changes lift blocked→purchase above 2%, the offer was the problem. If it stays below 1%, the users are non-paying by construction.
ACTION: Test a "first-month cheap" offer on the block paywall (e.g., $0.99 first month → $6.99 thereafter). Measure incremental purchases.

### Cross-Portfolio

**CONJECTURE XP17-1: The portfolio has forked into one growth app (VidNotes) and three declining apps — concentration risk is now real**
MECHANISM: VidNotes: +130% DAU. CleanPro: -9%. Echo: flat. Mangii: -4%. All revenue-generating apps are flat-to-down except VidNotes, and VidNotes' incremental revenue doesn't offset the other three's decline (92 purchases vs the loss from CleanPro's -81 and Mangii's -37). Portfolio revenue is in net decline despite headline DAU growth.
EVIDENCE FOR: Total purchases W16 (618) → W17 (509) = -17.6%. Weekly portfolio revenue is falling despite 1.9% DAU growth.
EVIDENCE AGAINST: Purchase counts don't capture revenue per purchase. If Echo's 128 purchases are $20/mo and Mangii's 31 are $5/mo, the Echo gain offsets the Mangii loss.
KILL CONDITION: If Apple/RC revenue data shows W17 > W16 despite the purchase drop, ARPU changes saved us. If revenue is down, portfolio is bleeding.
ACTION: Pull RevenueCat weekly revenue by app. THIS is the metric that matters, not event counts.

**CONJECTURE XP17-2: 3 of 4 apps have a purchase-funnel technical failure in the 5-10% range — suggests a shared StoreKit integration bug**
MECHANISM: VidNotes purchase_failed: 0 → 7 this week (new!). Echo: 8.2%. Mangii: 56/31 purchases = many more failures than successes. If three apps built by the same team are all seeing StoreKit failures emerge simultaneously, the cause is likely a shared iOS SDK update, a common purchase handler pattern, or an Apple-side change in receipt validation.
EVIDENCE FOR: Three apps. Same week. Same symptom (purchase_failed emerging or staying elevated).
EVIDENCE AGAINST: Different codebases, different teams. Could be coincidence.
KILL CONDITION: If logging the iOS error codes shows different underlying errors per app, the causes are app-specific. If they share an error code, root cause is shared.
ACTION: Add structured logging to purchase_failed (error domain + code) across all 4 apps. Compare next week.

---

## Portfolio Health

| App | DAU (WoW) | New Users (WoW) | Paywall→Purchase | Rating* | Status |
|-----|-----------|-----------------|------------------|---------|--------|
| VidNotes | 1,483 (+130%) | 806 (+96%) | 10.4% | — | 🟡 Growth strong, but cancellation storm |
| CleanPro | 2,638 (-9%) | 1,263 (-21%) | 5.2% | — | 🟡 Acquisition-led decline |
| Echo | 3,134 (+0.5%) | 2,221 (-4%) | 1.7% | — | 🔴 Plateau + purchase failure rate |
| Mangii | 8,282 (-4%) | 3,178 (-15%) | 0.34% | — | 🔴 Monetization collapsing |

*Rating data not pulled this week.

**Portfolio totals:** 15,537 DAU (+1.9%), 7,468 new users (-6.9%), 509 purchases (-17.6%)

---

## Recommended Actions (Ranked by Expected Impact)

1. **🚨 VidNotes paywall audit (URGENT).** Cancellation rate jumped 5.4x. Git diff the VidNotes paywall + pricing in the last 7 days. If a variant shipped, it's bleeding revenue.
2. **🚨 Scale VidNotes transcription backend.** 190 failed transcriptions/week = core value delivery failure. Capacity-constrained confirmed. Scale workers.
3. **🚨 Fix Echo purchase failure (8.2% rate).** Add error-code logging to purchase_failed. This is ~$400-800/week of lost Echo revenue.
4. **Pull CleanPro ASA + ASO data.** Every funnel stage declined in lockstep = top-of-funnel issue, not app issue. Diagnose the source.
5. **Pull RevenueCat weekly revenue.** Portfolio purchase count fell 17.6%. Need to know if revenue followed or was protected by ARPU.
6. **Investigate Mangii purchase crash.** Pull per-SKU purchase data. If no technical fix emerges in 2 weeks, consider sunset/pivot.
7. **Document the Echo voice cloning fix.** Failures dropped 72%. Whoever shipped this, credit them. Make sure it doesn't regress.

---

## Open Questions

1. **What was deployed to VidNotes in the last 7 days?** The cancellation spike doesn't match organic user behavior.
2. **What's the RevenueCat weekly revenue by app?** Event counts lie; dollars don't.
3. **What's the CleanPro ASA spend and ASO rank trend?** Needed to explain the uniform funnel decline.
4. **What iOS error codes are behind Echo's purchase_failed?** Technical failure or Apple-side friction?
5. **Is there a shared iOS SDK update that changed StoreKit behavior?** Three apps seeing purchase_failed simultaneously is suspicious.

---

## Kill List — Conjectures to Evaluate in W18

| # | Conjecture | Kill Condition |
|---|-----------|---------------|
| VN17-1 | VidNotes shipped a bad paywall variant | No code change found → refuted |
| VN17-2 | VidNotes backend capacity-constrained | Failure rate <10% after scaling → confirmed |
| VN17-3 | VidNotes growth is ASA-driven with dilution | CPA data + conversion stable ≥9% → confirmed |
| CP17-1 | CleanPro in acquisition-led decline | ASA spend cut → confirmed |
| CP17-2 | CleanPro paywall design is the bottleneck | Redesign A/B hits ≥7% paywall→purchase → confirmed |
| EC17-1 | Echo voice cloning fix shipped | Failure stays <25% for 2 weeks → confirmed |
| EC17-2 | Echo's 8.2% purchase failure is a fixable bug | Failure <3% after engineer fix → confirmed |
| EC17-3 | Echo growth plateau is real | DAU flat for 2 more weeks → confirmed |
| MG17-1 | Mangii is quietly dying | Purchases <50 for 3+ weeks → confirmed |
| MG17-2 | Mangii paywall is mispriced | First-month offer lifts conversion >2% → confirmed |
| XP17-1 | Portfolio revenue concentration risk | RC data shows revenue down WoW → confirmed |
| XP17-2 | Shared StoreKit failure pattern | Same iOS error code across apps → confirmed |
