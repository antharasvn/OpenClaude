# Weekly Conjecture Cycle — 2026-W27
Period: 2026-06-22 → 2026-06-29 (ET)
Generated: 2026-06-29T12:07:30Z (08:07 ET / 19:07 ICT)

**Note:** W26 cycle was skipped (cron timed out 06-22, no conjecture file). Prior conjectures from **W25** (06-08→06-15) are evaluated against **W27** data — a 2-week gap, so "next week" kill conditions are judged against a 2-week-later snapshot. WoW comparison below is **CUR (W27: 06-22→06-29)** vs **PREV (~W26: 06-15→06-22)**. All queries scan daily + intraday tables; event taxonomy re-discovered live (it diverges from the spec's assumed names). Key real names confirmed this cycle: VidNotes `transcription_start/complete/failed`, `paywall_viewed`, `purchase`, `trial_start`; CleanPro `cleanpro_paywall_shown`, `onboarding_paywall_shown`, `purchase`, `app_initial_purchase`, `rc_trial_start`; Echo `voice_cloning_started/completed/failed`, `music_generation_started/completed`, `purchase`, `in_app_purchase`, `subscription_started`, `purchase_initiated`, `purchase_failed`, `credit_purchased`; Mangii `panel_generate_tapped/generated/blocked`, `paywall_shown`, `paywall_purchase_success/failed`, `in_app_purchase`. "DAU" column = 7-day distinct `user_pseudo_id` (weekly-active), same definition the prior files used.

⚠️ **Ratings not pulled** (no `asc` call this cycle — consistent with W25). ⚠️ **ASA spend not pulled** (not in the scripted query set; the longest-open portfolio question — see Open Questions).

---

## Prior Conjecture Results (W25 → evaluated against W27)

| # | Conjecture | Verdict | Evidence |
|---|-----------|---------|----------|
| VN25-1 | VidNotes transcription reliability regressed (backend change) | **SURVIVED ✅ (regression confirmed)** | Fail rate 11.3%(W25) → 16.0%(W26) → **16.2%**(W27), held >10% across 3 windows while volume grew +27%. Kill required <5% without a code change; it's 16%. The W19 fix is fully undone — structural regression. |
| VN25-2 | VidNotes W22 crisis was seasonal, fully reversed (healthiest growth story) | **SURVIVED ✅ (growth) — monetization diverged** | Growth accelerated: DAU +22%, new +24%, transcription starts +27%, paywall +38%. Not a blip. BUT `purchase` fell to 20 (trips the literal "<30" kill) and `trial_start` −21%. Growth thesis corroborated; monetization broke off — see **VN27-1**. |
| CP25-1 | CleanPro sustained acquisition-channel collapse (4 straight weeks) | **REFUTED ❌** | New users 437(W25) → 541 → **572**(W27), +6% WoW. The "sustained collapse" stopped and reversed. `app_initial_purchase` +16%. Decline was not sustained. (Mechanism of recovery still unconfirmed — recovered without ASA data; the channel question stays open but the *collapse* conjecture is dead.) |
| EC25-1 | Echo voice-clone fix is driving acquisition recovery | **SURVIVED ✅** | Clone fail rate 23%(W25) → **3.9%**(W27, 10 fails / 255 starts), new users 1,068 (>950 kill floor), clone starts +12%. Fix is holding and deepening; acquisition holding. |
| EC25-2 | Echo payment regression shipped with the fix | **SURVIVED ✅ (confirmed, worsening)** | `purchase_failed` 68 (kill: >60 ✓), `in_app_purchase` 10 (kill: <25 ✓), `subscription_started` −37%, `purchase_initiated` −20%, fail-rate/init 29%→**59%**. Both "confirmed" kill clauses met exactly. Real, growing revenue leak — now the #1 problem. See **EC27-1**. |
| MG25-1 | Mangii revenue capped by chronic ~46% StoreKit failure | **SURVIVED ✅** | Fail rate **43.1%** (25 fail / 58 attempts), 6th+ consecutive window ≥39%. `purchase_success` 33 (<70 → not a traffic-blip recovery). Success −41% vs funnel −5/−10% = conversion break, not just traffic. Error codes still unlogged. |
| MG25-2 | Mangii funnel contraction = acquisition propagation + mild engagement softening | **SURVIVED ✅ (decelerated)** | Funnel now −5 to −10% (vs W25's −16 to −30%). gen_tapped/DAU 1.43→1.41 — engagement-per-user **stabilized** (the "softening" resolved). New users didn't recover >4,000 but the steep contraction eased to a mild drift. |
| XP25-1 | Acquisition split along product-health lines (fix core feature → growth) | **REFUTED ❌** | VidNotes grew **+24%** while its core feature is still **16%-failing** (broken). CleanPro recovered with **no known product fix**. Growth decoupled from product health → the review-velocity-from-fixes mechanism is dead. See **XP27-2**. |
| XP25-2 | Payment failures app-specific, not a shared SDK bug | **SURVIVED ✅ (but re-opened as a watch)** | Shapes still differ — Echo regression-spike, Mangii chronic plateau, VidNotes new divergence. BUT 3 of 4 apps' conversions fell *the same window* (Echo subs −37%, Mangii success −41%, VidNotes purchase −17%/trial −21%). Coincidence or shared event? → tested by **XP27-1**. |

**Score W25→W27: 2 REFUTED, 7 SURVIVED. 9 of 9 conjectures resolved.** Two clean refutations (CleanPro collapse halted; growth-tracks-product-health killed by VidNotes growing with a broken feature). The two confirmed payment problems (Echo regression, Mangii chronic) are now the portfolio's dominant theme.

---

## Raw Data — ~W26 (PREV, 06-15→06-22) vs W27 (CUR, 06-22→06-29)

### VidNotes
| Metric | PREV | CUR | Δ |
|--------|-----|-----|---|
| DAU (7d) | 1,168 | 1,422 | **+21.7%** 🟢🟢 |
| New Users | 655 | 813 | **+24.1%** 🟢🟢 |
| Transcription Start | 899 | 1,139 | **+26.7%** 🟢🟢 |
| Transcription Complete | 555 | 671 | +20.9% 🟢 |
| Transcription Failed | 144 | 184 | +27.8% |
| **Failure Rate** (fail/start) | 16.0% | **16.2%** | flat 🔴 (W22 was 2.5%) |
| Paywall Viewed | 726 | 1,000 | **+37.7%** 🟢🟢 |
| `purchase` | 24 | 20 | **−16.7%** 🔴 |
| `trial_start` | 24 | 19 | **−20.8%** 🔴 |
| `in_app_purchase` | 8 | 8 | flat |
| **Conversion** (purchase/pw) | 3.3% | **2.0%** | −1.3pp 🔴 |

### CleanPro
| Metric | PREV | CUR | Δ |
|--------|-----|-----|---|
| DAU (7d) | 1,446 | 1,500 | +3.7% |
| New Users | 541 | 572 | +5.7% 🟢 (collapse halted) |
| Paywall (main) | 1,021 | 1,096 | +7.3% |
| OB Paywall | 500 | 551 | +10.2% |
| `purchase` | 96 | 99 | +3.1% |
| `app_initial_purchase` | 67 | 78 | **+16.4%** 🟢 |
| `rc_trial_start` | 62 | 68 | +9.7% |
| `in_app_purchase` | 15 | 15 | flat |
| **Conversion** (purchase/pw) | 9.4% | **9.0%** | −0.4pp 🟢 |

### Echo
| Metric | PREV | CUR | Δ |
|--------|-----|-----|---|
| DAU (7d) | 1,833 | 1,841 | +0.4% |
| New Users | 994 | 1,068 | +7.4% 🟢 |
| Paywall Viewed | 2,485 | 1,913 | **−23.0%** 🔴 |
| Purchase Initiated | 146 | 116 | **−20.5%** 🔴 |
| `purchase` | 50 | 49 | −2.0% |
| `in_app_purchase` (subs) | 16 | 10 | **−37.5%** 🔴🔴 |
| `subscription_started` | 35 | 22 | **−37.1%** 🔴🔴 |
| Purchase Failed | 43 | 68 | **+58.1%** 🔴🔴 |
| **Fail Rate** (fail/init) | 29.5% | **58.6%** | +29pp 🔴🔴 |
| `credit_purchased` | 15 | 27 | **+80.0%** 🟢 |
| Voice Clone Start | 228 | 255 | +11.8% 🟢 |
| Voice Clone Failed | 58 | 10 | **−82.8%** 🟢🟢 |
| **Voice Clone Fail Rate** | 25.4% | **3.9%** | −21pp 🟢🟢 |
| Music Gen Start | 1,158 | 1,325 | +14.4% |
| Music Gen Complete | 1,089 | 1,238 | +13.7% |

### Mangii
| Metric | PREV | CUR | Δ |
|--------|-----|-----|---|
| DAU (7d) | 10,453 | 10,089 | −3.5% |
| New Users | 2,854 | 2,727 | −4.5% |
| Paywall Shown | 5,828 | 5,218 | −10.5% 🔴 |
| Paywall Post-First-Gen | 2,342 | 2,111 | −9.9% |
| Gen Tapped | 14,970 | 14,266 | −4.7% |
| Gen Completed | 9,219 | 8,689 | −5.7% |
| Gen Blocked | 6,669 | 5,408 | **−18.9%** 🔴 |
| **Purchase Success** | 56 | 33 | **−41.1%** 🔴🔴 |
| Purchase Failed | 20 | 25 | +25.0% 🔴 |
| In-App Purchase | 43 | 22 | **−48.8%** 🔴🔴 |
| **Purchase Fail Rate** | 26.3% | **43.1%** | +17pp 🔴 |

**Portfolio totals PREV → CUR:** DAU(7d) 14,900 → 14,852 (flat) · New Users 5,044 → 5,180 (+2.7%). New-user signs: VN +24%, CP +6%, EC +7%, MG −4.5% (three up, one mildly down → no shared shock). **Conversion fell in 3 of 4 apps the same week.**

---

## New Conjectures

### VidNotes

**CONJECTURE VN27-1: VidNotes' monetization decoupled from its traffic this week — paywall views +38% but trials −21% and purchases −17% — because the +24% new-user surge is a low-intent acquisition spike whose marginal user converts near zero**
MECHANISM: A genuine demand increase lifts paywall views *and* purchases together. Here paywall exposure jumped +38% while the two paid outcomes (trial_start, purchase) fell ~20%. Conversion-per-paywall halved (3.3%→2.0%). The cleanest explanation: the incremental users (a broad ASA push, a featured placement, or a seasonal/viral source) are materially lower-intent than the base — they reach the paywall and bounce.
EVIDENCE FOR: Top-of-funnel (DAU/new/transcription/paywall) all +20–38%, both monetization outputs down ~20%. The decoupling is too clean to be demand-side.
EVIDENCE AGAINST: Small base (20 purchases, 19 trials) → high week-to-week noise. Alternatively a paywall change (price/copy/gating) shipped ~06-22 and broke conversion independent of user mix.
KILL CONDITION: If purchases/trials rebound to ≥25 next week with paywall views still high → noise. If conversion-per-paywall stays <2.5% for another week → real intent/paywall regression. Check new-user source mix (ASA vs organic) and D1 retention of this cohort.
ACTION: Pull VidNotes ASA spend/installs for 06-22→06-29 — did paid installs spike? Diff the paywall config for any 06-22 change. If it's low-intent paid traffic, the marginal CAC is being wasted.

**CONJECTURE VN27-2: The 16% transcription failure rate is a silent tax on VidNotes' growth — the W19 reliability fix is fully reverted and the regression is now structural, not transient (firms up VN25-1)**
MECHANISM: Fail rate sat at 16.0%→16.2% across two windows while volume rose +27% — a rate that is flat-and-elevated under rising load is a backend dependency state (model/route/timeout), not noise. ~184 failed transcriptions/week are silently degrading the core promise while the app grows on acquisition momentum.
EVIDENCE FOR: 3-window plateau at 11–16%, far above the 2.5% W19-fixed baseline. Failure *count* scales with volume (rate constant) = systematic, not input-driven spikes.
EVIDENCE AGAINST: Could be a harder input mix from the +24% new users (longer/noisier first uploads). Rate is flat not climbing, so not actively deteriorating.
KILL CONDITION: Fail rate <5% next week without a code change → transient load/input effect. Holds >10% → confirmed structural regression (already 3 windows).
ACTION: Diff VidNotes transcription backend config since 2026-05-25. Add `error_code` to `transcription_failed` to separate provider errors from bad-input rejections.

### CleanPro

**CONJECTURE CP27-1: CleanPro's acquisition collapse is over — the bleeding channel was restored or replaced — and the recovery is paid-intent-led, evidenced by initial purchases rising faster (+16%) than new users (+6%)**
MECHANISM: Four weeks of −10 to −33% new-user decline reversed to +6%, and `app_initial_purchase` (first-time subscribers) rose +16% — disproportionately to headcount. Either ASA was un-paused / a keyword rank recovered, or a new channel replaced the lost one, and the returning traffic is converting well (initial purchases growing faster than users).
EVIDENCE FOR: New-user trend inflected positive after 4 down weeks. Initial purchases +16% > new users +6% → higher-intent inbound. Conversion held at a portfolio-best 9.0%.
EVIDENCE AGAINST: +6% is within seasonal noise; could be a one-week bounce off the W25 trough (437) rather than a true channel restoration. Mechanism still unconfirmed without ASA data.
KILL CONDITION: New users fall below 520 next week → the recovery was a dead-cat bounce. Hold >550 for another week → genuine restoration.
ACTION: Confirm via ASA whether CleanPro spend resumed 06-15→06-29 (the 4-week-old open question). If spend is flat and users recovered, an organic/ranking recovery is the cause.

### Echo

**CONJECTURE EC27-1: Echo's checkout is regressing further, not recovering — a specific SKU/RevenueCat entitlement validation is failing a growing share of purchase attempts (fail-rate/init 29%→59% in two weeks) — and it is now the portfolio's #1 confirmed revenue leak**
MECHANISM: This is EC25-2 escalating. purchase_failed +58% (43→68) while purchase_initiated FELL −20% — so failures rose against a shrinking attempt base, meaning the *probability* a given checkout fails roughly doubled. subscription_started −37% and in_app_purchase −37% confirm the failures convert to lost subs, not just retries. A demand-side cause can't produce failures-up + initiations-down + subs-down simultaneously; this is a code/config break in the purchase path.
EVIDENCE FOR: Fail rate/init 29%→59% in two windows. Three independent success signals (purchase, in_app_purchase, subscription_started) all down 2–37% while failures +58%. The decoupling from paywall exposure rules out demand.
EVIDENCE AGAINST: Echo's purchase taxonomy is noisy (purchase vs in_app_purchase vs subscription_started vs credit). The `purchase` event itself was only −2% (49 vs 50) — so total *completed* purchases may be steadier than the subs-specific events suggest. Possible measurement skew between event names.
KILL CONDITION: purchase_failed <40 AND in_app_purchase >20 next week → transient. Stays >60 fails with subs <20 → confirmed escalating regression. **Decisive test: pull Echo RevenueCat revenue 06-15→06-29 — if revenue fell ~35%, it's real lost money; if flat, it's instrumentation.**
ACTION: 🚨 Diff every Echo release since the voice-clone fix for StoreKit/RevenueCat/paywall-SKU changes. Add `error_code` to `purchase_failed`. This has now persisted across the W25 and W27 evaluations — stop confirming it and fix it.

**CONJECTURE EC27-2: Echo demand is intact but routing around the broken subscription checkout into one-off credit purchases — `credit_purchased` +80% (15→27) exactly as `subscription_started` fell −37% (35→22)**
MECHANISM: If demand had simply died, both subs and credits would fall. Instead they moved in opposite directions in lockstep. The credit-purchase flow likely uses a different SKU/code path that still works; when the sub checkout fails, willing buyers fall back to buying credits. This means the EC27-1 regression is even costlier — it's converting recurring-revenue subs into lower-LTV one-off credits.
EVIDENCE FOR: Perfect anti-correlation (subs −37%, credits +80%) in the same window the sub-checkout fail rate doubled.
EVIDENCE AGAINST: Credit purchases are a small base (27); the +80% is 12 absolute purchases. Could be an unrelated credit-pack promo or pricing change. Voice-clone usage (+12%) may simply be driving organic credit demand.
KILL CONDITION: If fixing the sub checkout (per EC27-1) makes credit_purchased fall back toward 15 → displacement confirmed. If credits stay elevated after a sub fix → independent credit demand, reject.
ACTION: Check whether a credit-pack promo or price change shipped ~06-22. If not, treat the credit rise as a symptom of the sub-checkout break, raising EC27-1's revenue cost.

**CONJECTURE EC27-3: A paywall-trigger gating change cut Echo's paywall exposure −23% (2,485→1,913), independently suppressing subs on top of the checkout failures**
MECHANISM: Two things hit subs at once — fewer people *saw* the paywall (−23%) and more of those who tried *failed* (EC27-1). A −23% exposure drop with flat DAU and +7% new users implies a deliberate or accidental change to *when* the paywall fires (e.g. a softer gate, a new free allowance, an A/B variant rebalance), not a traffic effect.
EVIDENCE FOR: DAU flat, new users up, yet paywall views down 23% → the per-user paywall trigger rate fell. That's a gating change, not demand.
EVIDENCE AGAINST: Could be a session-mix shift (more returning users who already converted/dismissed and don't re-trigger). Music usage rose +14% — if music is now reachable without a paywall, exposure naturally falls.
KILL CONDITION: paywall_viewed recovers toward 2,400 next week with no code change → measurement/session-mix. Stays <2,000 → confirmed gating change.
ACTION: Diff Echo paywall-trigger config and any RC paywall A/B since 06-15. A 23% exposure cut is a big monetization lever to have moved silently.

### Mangii

**CONJECTURE MG27-1: Mangii's free-tier gate was loosened — `gen_blocked` fell −18.9% (far steeper than gen_tapped −4.7%), so fewer users are forced into the paywall, which cut paywall_shown −10.5% and purchase_success −41%**
MECHANISM: gen_blocked is the event that fires when the free quota stops a user and forces a paywall. It dropped almost 4× faster than generation volume. That decoupling means the *block rate per generation* fell — i.e. the free allowance was raised (RC change) or the gate logic softened. Fewer forced paywalls → fewer purchases. This would make the revenue drop partly self-inflicted, not a demand loss.
EVIDENCE FOR: gen_blocked −18.9% vs gen_tapped −4.7% (block rate per tap fell). paywall_shown −10.5% tracks the reduced blocking. Same pattern was flagged as an evidence-against note in MG25-2 — now it's pronounced enough to be the headline.
EVIDENCE AGAINST: Could be that fewer *new/low-credit* users (new users −4.5%) means naturally fewer blocks, not a config change. Purchase failures also rose (43%), so revenue loss isn't purely a gating story.
KILL CONDITION: Pull Mangii RC free-generation limit / gate config history. If the limit changed ~06-15→06-22 → confirmed self-inflicted. If unchanged and block-rate-per-tap still fell → user-mix effect, reject.
ACTION: Check Mangii Remote Config free-gen quota change log. If loosened, quantify the revenue trade vs retention gain (it may be intentional and net-positive — verify, don't assume).

**CONJECTURE MG27-2: Mangii's chronic StoreKit failure worsened to 43% this week (from 26%) and is the proximate cause of the −41% purchase_success drop — not just fewer attempts (firms up MG25-1)**
MECHANISM: Attempts (success+fail) fell from 76 to 58 (−24%), but purchase_success fell −41% — the gap is the rising fail rate (26%→43%). If failure had stayed flat, success would have fallen only ~24%. The extra ~17pp of loss is the payment bug eating a larger share of a smaller pie. Six+ windows at ≥39% with no error-code logging = the single longest-undiagnosed revenue bug in the portfolio.
EVIDENCE FOR: Fail rate +17pp WoW. Success decline (−41%) exceeds attempt decline (−24%). Pattern persistent since W22.
EVIDENCE AGAINST: 33 successes / 25 fails is a tiny base — a single bad day swings the rate. Mangii's aggressive credit-funnel paywalls inflate low-intent attempts, so part of "failure" may be intent mismatch (cancels), not bugs.
KILL CONDITION: Add `error_code` to `paywall_purchase_failed`. If >50% share one SKErrorCode → code bug (fixable). If diverse (cancels, parental, card declines) → user-side. If purchase_success recovers >55 next week → it was a traffic/sample blip.
ACTION: 🚨 Log `paywall_purchase_failed` error codes — open since W22. Highest-ROI unblock; gates MG25-1/MG27-2/XP27-1 simultaneously.

### Cross-Portfolio

**CONJECTURE XP27-1: Conversion softened in 3 of 4 apps the same week (Echo subs −37%, Mangii success −41%, VidNotes purchase −17%/trial −21%) while only CleanPro converted normally (+3%) — a shared App Store / StoreKit / RevenueCat payment-processing event in the 06-22→06-29 window is the prime suspect, re-opening the shared-cause question XP25-2 closed**
MECHANISM: Three apps on the same StoreKit/RevenueCat stack losing conversion in the same 7-day window is either three coincidences or one common dependency hiccup — an iOS point-release rollout, an App Store billing/receipt-validation blip, or a RevenueCat-side incident. The bold claim: it's the latter. CleanPro's immunity would then need explaining (different SDK version, different paywall, or it genuinely escaped).
EVIDENCE FOR: Temporal coincidence across 3 independent apps. All three saw *paid outputs* fall while engagement held — a payment-layer signature, not a demand one.
EVIDENCE AGAINST: The shapes still differ (Echo failures spiking, Mangii chronic, VidNotes a fresh divergence with no failure spike — VN's `purchase_failed` is only 14). VidNotes' drop looks intent-driven (paywall +38%), not payment-failure-driven, which argues *against* a shared payment outage. Small bases everywhere.
KILL CONDITION: Add error codes to Echo + Mangii + VidNotes purchase_failed. If all three spike the same SKErrorCode in the same hours → shared cause confirmed (refutes XP25-2). If codes/timing differ, or VidNotes shows no failure spike at all → three independent causes (XP25-2 holds). Also check the Apple System Status / RevenueCat status history for 06-22→06-29.
ACTION: Pull RevenueCat dashboard for all 4 apps 06-22→06-29 — a cross-app revenue dip with the same timestamp is the fastest decisive test. Check Apple/RevenueCat incident history for the window.

**CONJECTURE XP27-2: Portfolio growth is decoupled from product quality (refuting XP25-1) — VidNotes grew +24% with a 16%-failing core feature and CleanPro recovered with no product fix — so acquisition is driven by external spend/seasonality, and feature fixes should not be expected to move acquisition**
MECHANISM: XP25-1 claimed "fix the core feature → reviews → ranking → growth." Two counter-examples this week: VidNotes' core transcription is broken (16% fail) yet it's the fastest-growing app (+24%); CleanPro's acquisition recovered (+6%) with no shipped product change. If growth tracked product health, neither could happen. Therefore acquisition and product-quality are independent levers — growth is riding ASA/seasonality/store mechanics, not review velocity.
EVIDENCE FOR: VidNotes growth + broken feature is a direct contradiction of the mechanism. CleanPro recovery without a fix is a second.
EVIDENCE AGAINST: Echo *did* fit XP25-1 (fix → growth). The decoupling cases could each have a hidden product improvement we didn't measure. Review-velocity lag (>1wk) could mask a real link.
KILL CONDITION: If VidNotes growth reverses next week as its broken feature persists, AND Echo growth holds with its fix → the product-health link partially survives. If VidNotes keeps growing while broken → decoupling confirmed.
ACTION: Treat acquisition (ASA/ASO/store) and product-quality (reliability/reviews) as separate workstreams with separate owners. Stop attributing acquisition swings to feature fixes without ASA data to rule out spend.

---

## Portfolio Health

| App | DAU 7d (WoW) | New Users (WoW) | Conversion | Rating | Status |
|-----|--------------|-----------------|------------|--------|--------|
| VidNotes | 1,422 (+22%) | 813 (+24%) | 2.0% 🔴 (purchase/pw) | n/a | 🟡 Traffic booming, monetization broke + 16% transcription fail |
| CleanPro | 1,500 (+4%) | 572 (+6%) | 9.0% 🟢 | n/a | 🟢 Collapse over, best converter in portfolio |
| Echo | 1,841 (+0.4%) | 1,068 (+7%) | 0.5% 🔴 (iap/pw) | n/a | 🔴 Checkout regression worsening (fail/init 59%), subs −37% |
| Mangii | 10,089 (−3.5%) | 2,727 (−4.5%) | 0.6% 🔴 (succ/pw) | n/a | 🔴 43% StoreKit fail, revenue −41%, undiagnosed since W22 |

*Ratings not pulled (no `asc` call). Conjectured target ≥4.5. Conversion target ≥8%: only CleanPro clears it. Echo/Mangii sub-1% is structural (very high low-intent paywall volume); the meaningful signal is their **direction** (both down) and **failure rate** (both rising).*

---

## Recommended Actions (Ranked by Expected Impact)

1. **🚨 FIX Echo's checkout — stop re-confirming it (EC27-1).** Confirmed across W25 and W27; fail-rate/init doubled to 59%, subs −37%. Pull RevenueCat revenue 06-15→06-29 (if revenue −35%, it's real money); diff every release since the voice-clone fix for StoreKit/SKU changes; add `error_code` to `purchase_failed`.
2. **🚨 Log `purchase_failed` error codes on Mangii + Echo (open since W22).** Unblocks MG25-1, MG27-2, EC27-1, and XP27-1 at once. The single highest-leverage instrumentation gap in the portfolio.
3. **VidNotes monetization break (VN27-1).** +38% paywall views, −17% purchases / −21% trials. Pull ASA installs 06-22→06-29 (low-intent surge?) and diff the paywall config for a 06-22 change. The traffic is there — recovering conversion is pure upside.
4. **Test the 3-app conversion drop for a shared cause (XP27-1).** Cheapest decisive test: RevenueCat dashboard for all 4 apps + Apple/RevenueCat incident history for the window. Either kills three coincidences or finds one fixable root cause.
5. **Mangii free-tier gate check (MG27-1).** gen_blocked −19% vs gen_tapped −5% → verify the RC free-gen quota didn't loosen and silently suppress revenue. May be intentional — quantify the trade.
6. **VidNotes transcription regression (VN27-2).** 16% fail across 3 windows. Diff backend config since 2026-05-25; add `error_code` to `transcription_failed`.
7. **Pull ASA spend for all 4 apps (open 5+ weeks).** Resolves CP27-1 mechanism, VN27-1 intent question, and the acquisition-vs-product-health debate (XP27-2).

---

## Open Questions

1. **Did a shared payment event hit Echo+Mangii+VidNotes in 06-22→06-29?** RevenueCat cross-app revenue timestamps + Apple status history settle it (XP27-1).
2. **Is Echo's checkout regression costing real money?** RevenueCat revenue 06-15→06-29 vs the −37% subs signal (EC27-1).
3. **Why did VidNotes conversion halve while traffic surged +38%?** Low-intent paid surge, or a 06-22 paywall change? (VN27-1)
4. **What is Mangii's dominant `paywall_purchase_failed` error code?** Open since W22 — blocks the highest-ROI fix.
5. **What caused CleanPro's recovery?** ASA un-pause, ranking recovery, or noise? (CP27-1) — still unanswered after 5 weeks of asking for ASA data.
6. **Did Echo's paywall trigger get gated softer (−23% exposure)?** (EC27-3)
7. **Did Mangii's free-gen quota loosen?** (MG27-1)

---

## Kill List — Conjectures to Evaluate in W28

| # | Conjecture | Kill Condition |
|---|-----------|---------------|
| VN27-1 | VidNotes monetization broke on low-intent surge | Purchases/trials rebound ≥25 next week → noise; conversion stays <2.5% → real regression |
| VN27-2 | Transcription regression structural (16%) | Fail rate <5% without a code change → transient |
| CP27-1 | CleanPro acquisition collapse is over | New users <520 next week → dead-cat bounce |
| EC27-1 | Echo checkout regression worsening | purchase_failed <40 & in_app_purchase >20 → transient; RevenueCat revenue flat → instrumentation |
| EC27-2 | Demand routing subs → credits | Fixing sub checkout drops credit_purchased toward 15 → displacement confirmed |
| EC27-3 | Echo paywall exposure gated softer (−23%) | paywall_viewed recovers toward 2,400 with no code change → session-mix |
| MG27-1 | Mangii free-tier gate loosened | RC free-gen limit changed ~06-15 → confirmed; unchanged → user-mix |
| MG27-2 | Mangii StoreKit failure worsened to 43% | Dominant single SKErrorCode in logs → code bug; purchase_success >55 → blip |
| XP27-1 | Shared payment event hit 3 apps same week | Same SKErrorCode/timing across apps → shared cause; differ or VN no failure spike → coincidence |
| XP27-2 | Growth decoupled from product quality | VidNotes growth reverses while broken & Echo growth holds with fix → link partially survives |
