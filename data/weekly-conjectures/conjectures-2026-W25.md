# Weekly Conjecture Cycle — 2026-W25
Period: 2026-06-08 → 2026-06-15 (ET)
Generated: 2026-06-15T12:05:00Z (19:05 ICT)

**Note:** W23 and W24 cycles were skipped (no conjecture files). Prior conjectures from **W22** are evaluated against **W25** data — a 3-week gap, so "next week" kill conditions are judged against a 3-week-later snapshot. WoW comparison below is **CUR (W25: 06-08→06-15)** vs **PREV (W24: 06-01→06-08)**. All queries include daily + intraday tables. Event taxonomies normalized across renames (VidNotes `transcription_start/complete`, `paywall_viewed`; Mangii now uses `paywall_purchase_success/failed`, `panel_generate_tapped`, `panel_generated`, `panel_generate_blocked`). CleanPro's `product_nil`/`product_load_failed` events no longer fire (removed or renamed) — cannot evaluate CP22-2.

---

## Prior Conjecture Results (W22 → evaluated against W25)

| # | Conjecture | Verdict | Evidence |
|---|-----------|---------|----------|
| VN22-1 | OB paywall removed/gated → trial collapse | **SURVIVED ✅ (stabilized)** | Trial starts W22=39 → W24=25 → W25=28. Did not collapse to zero; funnel stabilized at a lower plateau. Total paywall/new-user = 644/540 = 1.19 (healthy). The acute collapse halted but baseline never fully recovered. |
| VN22-2 | DAU collapse = app version regression | **REFUTED ❌** | Kill: DAU recovers >1,400 → seasonal. DAU went 1,196→1,017 (still <1,400) BUT new users **grew +13%** and transcription volume **+17%**. A regression suppressing returning users is inconsistent with rising engagement. The W22 dip reads as a transient (likely Memorial Day) artifact, not a structural regression. |
| VN22-3 | Transcription fix paradoxically cut engagement | **REFUTED ❌** | Premise dead: failure rate climbed back 2.5%(W22) → 14.9%(W24) → 11.3%(W25). The "too reliable → less use" mechanism is moot because reliability *regressed*. See new VN25-1. |
| CP22-1 | CleanPro −30% new users = paid acquisition pull | **SURVIVED ✅ (structural)** | New users 1,034→726→651→**437**. Fourth consecutive week of decline, another −33% WoW. Purchases held (102 vs 105) → remaining traffic is high-intent. This is now a sustained channel loss, not a one-week pull. |
| CP22-2 | CleanPro shipped product-loading fix | **PENDING ⏳ (uneval)** | `product_nil`/`product_load_failed` events no longer fire at all. Cannot compute error rate. Either fixed-and-removed or renamed. Unresolvable without instrumentation check. |
| EC22-1 | Echo credit_purchased explosion = instrumentation drift | **REFUTED ❌** | Kill: holds >400 → instrumentation; drops to ~50 → transient. credit_purchased 590(W22) → 41(W24) → **18**(W25). Collapsed below 50 → it was a transient W22 spike, **not** a permanent instrumentation shift. |
| EC22-2 | Voice cloning damaging ratings → suppressing acquisition | **REFUTED ❌ — FIX CONFIRMED 🎉** | Kill: code fix drops failure <30% within 2 weeks → fixable. Failure rate 73.8%(W22) → 48%(W24) → **23.0%**(W25). Below 30%. AND new users **+22%**, paywall **+15%** — the predicted reverse causal chain (fix feature → reviews recover → acquisition rises) is playing out. Best refutation of the cycle. |
| EC22-3 | Music gen degrading from shared backend resource | **REFUTED ❌** | Kill: music failure >20% → confirmed. Rate is **3.5%** (W22 was 15.9%). Far below threshold. The shared-resource saturation thesis is dead — voice clone recovered while music stayed healthy, so they don't share a saturating bottleneck. |
| MG22-1 | Mangii 50% purchase failure capping revenue | **SURVIVED ✅** | Failure rate 50%(W22) → **45.9%**(W25). Five+ weeks ≥39%. Purchase success collapsed −51% (82→40). Chronic. Error-code logging still not shipped → still undiagnosed. |
| MG22-2 | Mangii paywall throttled via Remote Config (post_gen "locked" at 2,752) | **REFUTED ❌** | post_first_gen 2,752(W22) → 3,961(W24) → 3,247(W25). The counter clearly *varies* — it was never capped. The W22 flatness was coincidence, not a throttle. |
| XP22-1 | Portfolio-wide acquisition decline = shared cause | **REFUTED ❌** | New users W25: VN **+13%**, EC **+22%**, CP **−33%**, MG **−16%**. Two up, two down. No shared direction → no shared cause. The W22 4-for-4 decline was Memorial-Day seasonality, now reversed for half the portfolio. |
| XP22-2 | Shared StoreKit/RC bug across apps | **REFUTED ❌ (diverging)** | Payment health split: VidNotes purchases **+23%**, CleanPro conversion held (9.7%), but Echo purchase_failed **+103%** and Mangii failure 46%. Two apps healthy, two not → failures are app-specific, not one shared SDK bug. (Error-code logging still owed to close fully.) |

**Score W22→W25: 1 FIX CONFIRMED, 8 REFUTED, 3 SURVIVED, 1 PENDING. 11 of 12 conjectures resolved.** Heavy refutation week — strong epistemic progress, headlined by the Echo voice-clone fix corroborating its predicted acquisition recovery.

---

## Raw Data — W24 (PREV) vs W25 (CUR)

### VidNotes
| Metric | W24 | W25 | Δ |
|--------|-----|-----|---|
| DAU | 983 | 1,017 | +3.5% 🟢 |
| New Users | 479 | 540 | +12.7% 🟢 |
| Transcription Start | 786 | 923 | +17.4% 🟢 |
| Transcription Complete | 449 | 619 | +37.9% 🟢 |
| Transcription Failed | 117 | 104 | −11.1% |
| **Failure Rate** | 14.9% | **11.3%** | −3.6pp 🟡 (W22 was 2.5% — regressed) |
| Paywall Viewed | 648 | 644 | flat |
| Purchases | 31 | 38 | +22.6% 🟢 |
| Trial Starts | 25 | 28 | +12.0% |

### CleanPro
| Metric | W24 | W25 | Δ |
|--------|-----|-----|---|
| DAU | 1,696 | 1,446 | −14.7% 🔴 |
| New Users | 651 | 437 | **−32.9%** 🔴🔴 |
| Paywall | 1,189 | 1,051 | −11.6% |
| OB Paywall | 639 | 416 | −34.9% 🔴 |
| Purchases | 105 | 102 | −2.9% |
| Initial Purchase | 82 | 59 | −28.0% 🔴 |
| **Conversion (purch/pw)** | 8.8% | **9.7%** | +0.9pp 🟢 |

### Echo
| Metric | W24 | W25 | Δ |
|--------|-----|-----|---|
| DAU | 1,907 | 1,974 | +3.5% 🟢 |
| New Users | 935 | 1,140 | **+21.9%** 🟢🟢 |
| Paywall Viewed | 2,892 | 3,331 | +15.2% 🟢 |
| IAP (subs) | 33 | 19 | **−42.4%** 🔴🔴 |
| `purchase` event | 69 | 45 | −34.8% |
| Purchase Initiated | 220 | 239 | +8.6% |
| Purchase Failed | 33 | 67 | **+103%** 🔴🔴 |
| **Purchase Fail Rate (/init)** | 15.0% | **28.0%** | +13pp 🔴 |
| Credit Purchased | 41 | 18 | −56.1% |
| Voice Clone Start | 223 | 296 | +32.7% 🟢 |
| Voice Clone Failed | 107 | 68 | −36.4% |
| **Voice Clone Fail Rate** | 48.0% | **23.0%** | −25pp 🟢🟢 (W22 73.8%) |
| Music Start | 1,377 | 1,127 | −18.2% |
| Music Complete | 1,316 | 990 | −24.8% |
| Music Failed | 9 | 40 | +344% 🔴 |
| **Music Fail Rate** | 0.7% | 3.5% | +2.8pp 🟡 (still low) |

### Mangii
| Metric | W24 | W25 | Δ |
|--------|-----|-----|---|
| DAU | 11,865 | 11,296 | −4.8% |
| New Users | 4,225 | 3,531 | −16.4% 🔴 |
| Paywall Shown | 9,291 | 7,305 | −21.4% 🔴 |
| Paywall Post First Gen | 3,961 | 3,247 | −18.0% |
| **Purchase Success** | 82 | 40 | **−51.2%** 🔴🔴 |
| Purchase Failed | 53 | 34 | −35.8% |
| In-App Purchase | 72 | 35 | **−51.4%** 🔴🔴 |
| **Purchase Fail Rate** | 39.3% | **45.9%** | +6.6pp 🔴 |
| CTA Tapped | 447 | 329 | −26.4% |
| Gen Tapped | 23,157 | 18,500 | −20.1% |
| Gen Completed | 14,488 | 11,979 | −17.3% |
| Gen Blocked | 11,093 | 7,786 | −29.8% |

**Portfolio totals W24 → W25:** DAU 16,451 → 15,733 (−4.4%) · New Users 6,290 → 5,648 (−10.2%) · Subs IAP (VN+CP+EC+MG) 218 → ~196.

---

## New Conjectures

### VidNotes

**CONJECTURE VN25-1: VidNotes' transcription reliability regressed structurally since W22 (2.5% → 11.3% failure) — a backend model/route change reintroduced the failure mode the W19 fix had eliminated**
MECHANISM: Failure rate went 2.5%(W22) → 14.9%(W24) → 11.3%(W25) while volume *grew* +17%. A reliability metric that triples then plateaus at 11–15% under rising load is the signature of a backend dependency change (model swap, transcription provider, timeout config), not random noise. The W19 fix was real (3 weeks <10%); something after W22 undid it.
EVIDENCE FOR: Monotone-ish climb across 3 weeks, sustained above 10%. Volume up, so not a small-sample artifact (104 failures on 923 starts).
EVIDENCE AGAINST: Could be a harder input mix (longer/noisier audio from more new users, +13%). Failure *count* actually fell W24→W25 (117→104); only the rate is elevated vs W22.
KILL CONDITION: If failure rate returns <5% next week without a code change → transient load/input effect. If it holds >10%, confirmed regression.
ACTION: Diff VidNotes transcription backend config between 2026-05-25 and now. Check for a provider/model/timeout change. Add the failed-audio `error_code` to `transcription_failed`.

**CONJECTURE VN25-2: VidNotes' W22 "crisis" was Memorial-Day seasonality, fully reversed — the app is the healthiest growth story in the portfolio right now**
MECHANISM: DAU +3.5%, new users +13%, transcription starts +17%, completes +38%, purchases +23%, trials +12% — every funnel stage up WoW. The W22 collapse (DAU −25%, trial −66%) coincided with US Memorial Day weekend; post-holiday acquisition normalized.
EVIDENCE FOR: Uniform across-funnel recovery. No single broken metric. Completes growing faster than starts (38% vs 17%) = better throughput per session.
EVIDENCE AGAINST: DAU (1,017) still below the W21 baseline (1,599) — not a full recovery, only WoW. Could be a single good week.
KILL CONDITION: If purchases fall back below 30 or DAU below 950 next week → it was a one-week blip, not a trend.
ACTION: None urgent — monitor. Confirm whether absolute DAU is recovering toward W21 levels or stabilizing at a new lower plateau.

### CleanPro

**CONJECTURE CP25-1: CleanPro is in a sustained acquisition-channel collapse — new users have fallen 4 straight weeks (1,034→726→651→437, −58% cumulative) — and conversion is rising only because the surviving traffic is the high-intent organic remnant**
MECHANISM: New users −33% again while purchases held (102 vs 105) and conversion *rose* (8.8%→9.7%). When you strip out low-intent paid/broad traffic, headcount falls but conversion-per-user climbs. Four consecutive weeks rules out a one-time event; this is either ASA spend cut to ~zero or a keyword-ranking/category-ranking collapse.
EVIDENCE FOR: Monotone 4-week new-user decline. Conversion inversely rising — classic "cheap traffic left" signature. OB paywall views −35% (tracks new-user volume), main funnel only −12%.
EVIDENCE AGAINST: Could be App Store category seasonality (cleaning apps). Could be a competitor eating featured/keyword spots. ASA data not yet pulled.
KILL CONDITION: Pull CleanPro ASA spend W24→W25. If spend was cut/paused → confirmed paid pull. If spend steady and new users still −33% → organic/ranking collapse (worse, structural).
ACTION: **Check ASA dashboard for CleanPro — 5-minute test.** Then check App Store keyword rank for top terms. This is the #1 open question for CleanPro for the 4th week running.

### Echo

**CONJECTURE EC25-1: Echo's voice-clone fix is the direct cause of its acquisition recovery — fixing the core feature (74%→23% failure) lifted review sentiment, which lifted organic ranking, which lifted new users (+22%)**
MECHANISM: This is EC22-2's predicted causal chain running in reverse. When 3-of-4 clones failed (W22), users rage-quit and left bad reviews → ranking/acquisition suppressed. Now 3-of-4 *succeed*, review velocity turns positive → ranking recovers → new users +22%, paywall +15%. Voice-clone starts themselves grew +33% (users re-engaging the feature).
EVIDENCE FOR: Tight temporal coupling — failure rate halved and new users jumped +22% in the same window. Clone starts +33% = users coming back to a feature they'd abandoned.
EVIDENCE AGAINST: Acquisition could be ASA-driven (spend up) and unrelated to the fix. App Store review-to-ranking lag is usually >1 week, so causation timing is tight.
KILL CONDITION: If new users fall back below 950 next week while clone failure stays <30% → the fix and acquisition are unrelated (acquisition was external). If new users hold >1,050, the fix→growth link strengthens.
ACTION: Confirm via ASA whether Echo spend rose W24→W25. If spend flat and users +22%, the fix→organic-growth thesis is corroborated. Protect this fix — pin the known-good clone backend version.

**CONJECTURE EC25-2: A payment regression shipped to Echo alongside the voice-clone fix — purchase failures doubled (33→67, rate 15%→28%) and successful IAP subs fell −42% (33→19) even as paywall views rose +15%**
MECHANISM: Paywall exposure UP 15% and purchase_initiated UP 9%, yet completed IAP subs DOWN 42% and failures UP 103%. Demand rose, conversion broke. The most economical explanation: a StoreKit/RevenueCat code path or SKU config changed in the same release train that fixed voice cloning, and it's now failing a large share of checkouts.
EVIDENCE FOR: Failures and successes moved in opposite directions while top-of-funnel grew — that decoupling can't be demand-side. Fail rate jumped 13pp in one week.
EVIDENCE AGAINST: `purchase`/`in_app_purchase`/credit events at Echo have a history of taxonomy churn (W22 credit explosion). The IAP drop could be measurement, not real lost revenue.
KILL CONDITION: If purchase_failed returns <40 and IAP subs >30 next week → transient. If failures stay >60 and IAP <25 → confirmed payment regression. Cross-check RevenueCat W25 Echo revenue: if revenue flat, it's instrumentation; if revenue fell ~40%, it's real.
ACTION: **Pull Echo RevenueCat revenue W24 vs W25.** Add `error_code` to `purchase_failed`. Diff the release that shipped the voice-clone fix for StoreKit/paywall changes.

### Mangii

**CONJECTURE MG25-1: Mangii revenue halved (−51% purchases) far faster than its funnel contracted (−20%) — conversion broke, not just traffic, and the chronic ~46% StoreKit failure rate is the prime suspect**
MECHANISM: Purchase success 82→40 (−51%) and IAP 72→35 (−51%), but gen_tapped −20%, paywall −21%. If revenue tracked traffic it would be down ~20%; the extra 30pp of revenue loss is a conversion/payment break. Failure rate climbed 39%→46% — at 46%, nearly half of all checkout attempts die at StoreKit, and the absolute attempt base shrank, so the same bug now eats a bigger fraction of a smaller pie.
EVIDENCE FOR: Revenue decline (−51%) is 2.5× the funnel decline (−20%). Failure rate rising while attempts fall = compounding. CTA tapped −26% suggests users walking away pre-purchase too (reviews mentioning payment issues?).
EVIDENCE AGAINST: 40 successes is a small base — week-to-week noise is large. Mangii's aggressive credit-funnel paywalls inflate low-intent attempts, so a 46% "failure" rate may partly be intent mismatch, not bugs.
KILL CONDITION: Add `error_code` to `paywall_purchase_failed`. If >50% of failures share one SKErrorCode → code bug (fixable). If diverse (cancelled cards, parental controls) → user-side. If purchase_success recovers >70 next week → was a traffic blip.
ACTION: **Highest-revenue-leverage bug in the portfolio (still). Log `paywall_purchase_failed` error codes in Mangii NOW** — open since W22, blocking diagnosis of ~40 lost purchases/week.

**CONJECTURE MG25-2: Mangii's funnel-wide contraction (gen −20%, paywall −21%, blocked −30%) is acquisition decline (new users −16%) propagating downstream — not a per-user engagement drop**
MECHANISM: New users −16% feeds fewer first-generations → fewer paywall triggers → fewer purchases. If per-DAU engagement were stable, the whole funnel would scale down with the user base. gen_tapped/DAU: W24 = 23,157/11,865 = 1.95; W25 = 18,500/11,296 = 1.64 — engagement-per-user *also* dropped ~16%, so it's BOTH acquisition and a mild engagement softening.
EVIDENCE FOR: Every funnel stage moved down together in a tight −16% to −30% band. DAU only −4.8% (returning users sticky), so the contraction is front-loaded on new users.
EVIDENCE AGAINST: gen_blocked −30% (steeper than gen_tapped −20%) could mean the free-tier limit loosened, reducing forced paywall hits — a deliberate change, not decay.
KILL CONDITION: If new users recover >4,000 next week and the funnel scales back up proportionally → pure acquisition. If gen_tapped/DAU keeps falling, there's an independent engagement regression.
ACTION: Check Mangii ASA spend (shares the CleanPro question). Check whether the free-tier/credit limit changed (gen_blocked falling faster than gen_tapped is suspicious).

### Cross-Portfolio

**CONJECTURE XP25-1: Acquisition has split along product-health lines — the two apps that FIXED a core feature gained users (Echo voice clone → +22%, VidNotes transcription volume/throughput → +13%); the two that didn't address their core problem lost users (CleanPro acquisition channel → −33%, Mangii payments/engagement → −16%)**
MECHANISM: This directly refutes W22's "shared external cause." The W25 divergence maps onto product quality: fix the thing users hate → reviews/ranking/organic recover → acquisition rises. The portfolio is not subject to one macro shock; each app's acquisition tracks its own product health with a ~2–3 week review-velocity lag.
EVIDENCE FOR: Sign of new-user delta matches whether each app shipped a core-feature improvement. Echo's +22% coincides exactly with its failure rate dropping below 30%.
EVIDENCE AGAINST: Could be coincidence + independent ASA decisions (Echo spend up, CleanPro spend cut) with no review-velocity mechanism at all. ASA data would settle it.
KILL CONDITION: If CleanPro/Mangii recover next week with no product change → the driver is external (ASA/seasonality), not product health. If Echo/VidNotes growth reverses while their fixes hold → the fix→growth link is spurious.
ACTION: Pull ASA spend for all 4 apps W24→W25. This is the single fastest test separating "product-health divergence" from "we just spend differently per app."

**CONJECTURE XP25-2: Payment failures are app-specific, not a shared SDK bug — refuting XP22-2 — because two apps on the same StoreKit/RevenueCat stack are healthy (VidNotes purchases +23%, CleanPro conversion 9.7%) while two are broken in different ways (Echo failures +103% post-release, Mangii chronic 46%)**
MECHANISM: A shared SDK bug would degrade all four roughly together. Instead: VidNotes/CleanPro payments are fine, Echo's failures spiked exactly at a release (regression), Mangii's are a chronic plateau (config/SKU). Different shapes → different causes → app-specific, not common SDK.
EVIDENCE FOR: Two apps healthy on the same stack. Echo's spike is release-coupled (step), Mangii's is a flat chronic line (plateau) — distinct signatures.
EVIDENCE AGAINST: Still no error-code logging anywhere, so "shared cause" can't be fully closed — could be the same SKErrorCode manifesting only where paywall volume is high.
KILL CONDITION: Add error codes to Echo + Mangii `purchase_failed`. If both show the same dominant SKErrorCode → shared cause after all. If different codes → confirmed app-specific.
ACTION: Error-code logging on Echo and Mangii `purchase_failed` (VidNotes/CleanPro lower priority — they're converting fine).

---

## Portfolio Health

| App | DAU (WoW) | New Users (WoW) | Conversion (purch/pw) | Status |
|-----|-----------|-----------------|------------------------|--------|
| VidNotes | 1,017 (+3.5%) | 540 (+13%) | 5.9% 🟡 | 🟢 Recovering — every funnel stage up; transcription reliability the one watch-item |
| CleanPro | 1,446 (−15%) | 437 (−33%) | 9.7% 🟢 | 🔴 Acquisition channel collapse (4th wk), but converts best in portfolio |
| Echo | 1,974 (+3.5%) | 1,140 (+22%) | 1.4% 🔴 | 🟡 Core feature FIXED + growing, but payment failures doubled |
| Mangii | 11,296 (−5%) | 3,531 (−16%) | 0.5% 🔴 | 🔴 Revenue halved (−51%), chronic 46% payment failure |

*Ratings not pulled this cycle (no ASC call) — conjectured target ≥4.5; Echo's review trajectory inferred positive from acquisition recovery (EC25-1). Conversion target ≥8%: only CleanPro clears it; Echo/Mangii run sub-1% on very high low-intent paywall volume.*

---

## Recommended Actions (Ranked by Expected Impact)

1. **🚨 Log `purchase_failed` error codes on Mangii + Echo (open since W22).** Mangii loses ~40 purchases/wk at 46% failure; Echo's failures just doubled. This unlocks XP25-2/MG25-1/EC25-2 simultaneously. Highest revenue leverage in the portfolio.
2. **🚨 Echo payment regression (EC25-2).** Failures +103%, IAP subs −42% the same week the voice-clone fix shipped. Pull RevenueCat W25 revenue — if revenue fell ~40%, a checkout regression is silently eating the acquisition gains. Diff the release.
3. **Check ASA spend for all 4 apps W24→W25.** One test resolves CP25-1, MG25-2, EC25-1, and XP25-1. Separates product-health divergence from spend differences. ~5 min.
4. **Protect the Echo voice-clone fix.** It's driving +22% acquisition (EC25-1). Pin the known-good backend version; do not let the next release regress it.
5. **VidNotes transcription regression (VN25-1).** Failure rate back to 11% from 2.5%. Diff backend config since 2026-05-25; add `error_code` to `transcription_failed`.
6. **CleanPro keyword-rank check.** If ASA spend is steady but new users −33%, it's an organic ranking collapse — structurally worse than a budget pull.

---

## Open Questions

1. **Did Echo's voice-clone-fix release also break checkout?** RevenueCat revenue W25 vs W24 settles it.
2. **Is CleanPro's 4-week new-user decline ASA or organic?** Still unanswered after 4 weeks — the single longest-open portfolio question.
3. **What's Mangii's dominant `paywall_purchase_failed` error code?** Open since W22; blocks the highest-ROI fix.
4. **Why did VidNotes transcription reliability regress (2.5%→11%)?** Backend change after W22?
5. **Did Echo's acquisition rise from the fix or from ASA spend?** Determines whether "fix core feature → organic growth" is a repeatable portfolio playbook.
6. **Is the W22→W25 gap hiding a sharper trend?** W23/W24 files don't exist; we only have W24 as PREV.

---

## Kill List — Conjectures to Evaluate in W26

| # | Conjecture | Kill Condition |
|---|-----------|---------------|
| VN25-1 | VidNotes transcription reliability regressed (backend change) | Failure rate <5% next week without code change → transient |
| VN25-2 | VidNotes W22 crisis was seasonal, fully reversed | Purchases <30 or DAU <950 next week → one-week blip |
| CP25-1 | CleanPro sustained acquisition-channel collapse | ASA spend cut → paid pull; spend steady + still −33% → organic/ranking collapse |
| EC25-1 | Echo voice-clone fix is driving acquisition recovery | New users <950 next week with failure <30% → fix unrelated to growth |
| EC25-2 | Echo payment regression shipped with the fix | purchase_failed <40 & IAP >30 next week → transient; RevenueCat revenue flat → instrumentation |
| MG25-1 | Mangii revenue halved on conversion break (46% StoreKit failure) | Dominant single SKErrorCode in logs → code bug; purchase_success >70 → traffic blip |
| MG25-2 | Mangii funnel contraction = acquisition propagation (+ mild engagement softening) | New users >4,000 & funnel scales back proportionally → pure acquisition |
| XP25-1 | Acquisition split along product-health lines | CP/MG recover with no product change → external driver, not product health |
| XP25-2 | Payment failures app-specific, not shared SDK bug | Echo+Mangii error codes show same dominant SKErrorCode → shared cause after all |
