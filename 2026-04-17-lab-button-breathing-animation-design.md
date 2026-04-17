# Lab Button Breathing Animation — Design Spec

**Date:** April 17, 2026
**Scope:** First 3 camera captures
**Status:** Design approved, ready for implementation planning

---

## Overview

Add a subtle breathing pulse animation to the lab button thumbnail when users are in their first three camera captures. This animation runs automatically when the camera screen appears and provides gentle visual feedback that the lab exists and is ready to use.

**Target:** iOS 14+
**Animation Framework:** Core Animation (CABasicAnimation)

## Goals

1. Draw attention to the lab button early in onboarding
2. Reinforce the lab feature without interrupting photography
3. Use understated animation that wont distract while framing
4. Align with existing animation patterns (bounce, gold glow)

## Feature Scope

**Applies to:** Users whose `totalLifetimeCaptures < ios_auto_preview_max_captures` (default: 3)
**Trigger:** Camera screen appears (viewDidAppear / onAppear)
**Stop triggers:**
- User taps the lab button
- User takes a new photo
- Camera screen disappears (viewWillDisappear / onDisappear)
**Restart behavior:** On next camera screen appearance, if still under threshold, animation restarts

## Animation Specification

### What Animates
Element: Lab button thumbnail image only (not entire button, badge, or background)

### Animation Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Type | CABasicAnimation | Aligns with existing patterns |
| Duration | 1.8 seconds | Organic breathing feel |
| Scale | 1.0 → 0.9 → 1.0 | Moderate, inviting |
| Opacity | 1.0 → 0.6 → 1.0 | Complements scale |
| Timing | easeInOut | Smooth, natural |
| Repeat | Infinite | Continuous while active |
| Key | "breathingPulse" | Unique identifier |

## Data Flow & Lifecycle

### Initialization
viewWillAppear → Check totalLifetimeCaptures < 3 → call startBreathingAnimation()

### Runtime
Animation runs on thumbnail layer with normal user interaction

### Termination
Lab button tap → stopBreathingAnimation() → proceed with navigation
Photo capture → stopBreathingAnimation() → continue post-capture flow
Screen disappears → stopBreathingAnimation() in viewWillDisappear

### Restart
On next camera screen, if under threshold, startBreathingAnimation() called again

## Implementation Details

### Methods to Add

**startBreathingAnimation()**
- Creates CABasicAnimation group for opacity and scale
- Sets repeatCount to .infinity
- Adds animation with key "breathingPulse"
- Prevents duplicate animations

**stopBreathingAnimation()**
- Calls removeAnimation(forKey: "breathingPulse")
- Safe to call even if animation not running

### Integration Points

1. Lab button container — location of animation methods
2. Lab button tap handler — add stopBreathingAnimation() call
3. Capture completion — add stopBreathingAnimation() call
4. Camera lifecycle — call start in viewWillAppear, stop in viewWillDisappear

### No Changes Required
- Feature flag system
- Lab navigation logic
- Post-capture auto-preview
- Gold glow/toast animations

## Edge Cases & Considerations

### Background/Foreground
Animation stops if camera backgrounded, restarts on return if under threshold

### Rapid Photo Taking
Animation stops after capture, restarts on next camera screen if under threshold

### External Updates
Animation continues if thumbnail updates externally (applied to layer)

### Accessibility
Visual only; respects motion reduction settings if implemented (future)

## Testing Strategy

### Unit Tests
- Verify startBreathingAnimation() called iff totalLifetimeCaptures < 3 AND camera visible
- Verify stopBreathingAnimation() called on lab tap and photo capture
- Verify animation not applied if threshold exceeded

### Integration Tests
- Animation lifecycle across screen transitions
- Animation behavior across app backgrounding

### Manual/Visual Tests
- On-device confirmation: smooth, inviting, non-intrusive feel
- Only thumbnail animates
- Clean stop behavior
- Test on iPhone SE and Pro Max for scale consistency

## Success Criteria

✅ Animates when totalLifetimeCaptures < 3 and camera screen appears
✅ Stops on lab tap, photo capture, or screen disappear
✅ Restarts on next camera screen if threshold not exceeded
✅ Only thumbnail animates
✅ 1.8s cycle with easeInOut timing
✅ No animation system conflicts
✅ No performance impact
✅ All tests pass

## Open Questions / Future Work

- Motion reduction: Respect UIAccessibility.isReduceMotionEnabled? (Defer to implementation)
- Customization: A/B test breathing duration/intensity? (Out of scope for v1)

## Files Affected

- Lab button container class (add animation methods)
- Lab button tap handler (add stopBreathingAnimation() call)
- Capture flow completion (add stopBreathingAnimation() call)
- Camera screen lifecycle (add start/stop calls)

No new files required.
