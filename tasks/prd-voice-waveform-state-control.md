# PRD: Voice Waveform State Control

## Introduction

Modify the voice upload panel's waveform animation to respond to actual sound detection states. Currently, the waveform animates continuously when the voice panel is open. The new behavior: animate only when sound is detected, stay static when idle, and disappear when transcription completes.

## Goals

- Waveform animates only when user is actively speaking (VAD detects sound)
- Waveform stays static (CSS-defined heights) when system is listening but no sound detected
- Waveform disappears when transcription ends, leaving only the transcript text
- Improve user feedback clarity about voice detection state

## User Stories

### US-001: Stop waveform animation on voice panel open
**Description:** As a user, when I open the voice panel, the waveform should be static (not animating) to indicate the system is ready but waiting for my voice.

**Acceptance Criteria:**
- [ ] When voice panel opens, waveform bars show at static CSS-defined heights (24px, 48px, 72px, 96px, 120px, etc.)
- [ ] No animation plays initially
- [ ] The CSS class `vv-waveform` does NOT have animation by default
- [ ] Typecheck passes

### US-002: Start waveform animation when sound detected
**Description:** As a user, when I start speaking, the waveform should animate to provide visual feedback that my voice is being detected.

**Acceptance Criteria:**
- [ ] Backend sends `vv_status` with `state="speaking"` when VAD detects speech
- [ ] Frontend adds animation class (e.g., `vv-waveform-animate`) to waveform when receiving "speaking" status
- [ ] Waveform bars animate with the existing wave animation
- [ ] Typecheck passes
- [ ] Verify in browser using playwright-cli skill: confirm CSS animation is running

### US-003: Stop animation when silence detected during speech
**Description:** As a user, when I pause speaking, the waveform should stop animating but remain visible, indicating the system is still listening.

**Acceptance Criteria:**
- [ ] Backend sends `vv_status` with `state="listening"` when VAD detects silence after speech (`VADStateChange` with `VoiceState.SILENCE`)
- [ ] Frontend removes animation class when receiving "listening" status
- [ ] Waveform returns to static state (CSS-defined heights)
- [ ] Typecheck passes
- [ ] Verify in browser using playwright-cli skill: confirm animation is paused

### US-004: Hide waveform when transcription ends
**Description:** As a user, when transcription completes (silence timeout after speech), the waveform should disappear and only the transcript text should remain visible.

**Acceptance Criteria:**
- [ ] Backend sends `vv_status` with `state="done"` when transcription finishes
- [ ] Frontend hides waveform container (e.g., adds `hidden` class or sets `display: none`)
- [ ] Transcript text remains visible in `#transcript-box`
- [ ] Typecheck passes
- [ ] Verify in browser using playwright-cli skill: confirm waveform DOM element has `display: none` or equivalent

### US-005: Show waveform again when re-opening voice panel
**Description:** As a user, if I close and reopen the voice panel after a previous transcription, the waveform should be visible and static again.

**Acceptance Criteria:**
- [ ] When voice panel opens, waveform is visible and in static state
- [ ] Previous transcript is cleared
- [ ] Typecheck passes
- [ ] Verify in browser using playwright-cli skill

## Functional Requirements

- FR-1: Modify CSS to have two waveform states: static (default) and animated (with class)
- FR-2: Frontend JS must handle `vv_status` messages: "listening", "speaking", "done", "timeout"
- FR-3: On "speaking" status: add animation class to `.vv-waveform`
- FR-4: On "listening" status: remove animation class from `.vv-waveform`
- FR-5: On "done" status: hide `.vv-waveform` element entirely
- FR-6: On "timeout" status: same behavior as "done"
- FR-7: On voice panel open: show waveform, ensure static state, clear transcript
- FR-8: Backend VAD must emit "listening" state when silence is detected during active session (if not already)

## Non-Goals

- No changes to VAD detection algorithm
- No changes to transcription logic
- No changes to waveform bar heights or colors
- No additional status text or badges

## Technical Considerations

### CSS Changes (styles.css)
```css
/* Default: static waveform */
.vv-waveform .vv-wave-bar {
  animation: none;
}

/* Animated state */
.vv-waveform.animating .vv-wave-bar {
  animation: wave 1.2s ease-in-out infinite;
}
```

### JavaScript Changes (voice.js)
Add state handling in `vv_status` message handler:
```javascript
Shiny.addCustomMessageHandler("vv_status", function (msg) {
  var waveform = qs(".vv-waveform");
  if (msg.state === "speaking") {
    waveform.classList.add("animating");
  } else if (msg.state === "listening") {
    waveform.classList.remove("animating");
    waveform.style.display = "";
  } else if (msg.state === "done" || msg.state === "timeout") {
    waveform.classList.remove("animating");
    waveform.style.display = "none";
    // ... existing timeout logic
  }
});
```

### Backend Changes (app.py)
The VAD already emits `VADStateChange` with `VoiceState.SILENCE` when silence is detected during speech. However, `_consume_vad()` only sends `vv_status="speaking"` on SPEAKING transition, but does NOT send `vv_status="listening"` on SILENCE transition.

**Change needed:** In `_consume_vad()`, add handler for SILENCE state change:
```python
if isinstance(event, VADStateChange):
    if event.new_state.voice_state == VoiceState.SPEAKING:
        speech_detected = True
        await _push(session, "vv_status", state="speaking")
    elif event.new_state.voice_state == VoiceState.SILENCE:
        await _push(session, "vv_status", state="listening")
```

## Success Metrics

- User can visually distinguish between "waiting for voice" and "voice detected" states
- Waveform animation directly correlates with actual sound detection
- No false visual feedback (animation without sound)

## Open Questions

None. Technical investigation complete.
