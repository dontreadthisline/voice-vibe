from __future__ import annotations

import pytest

from voicevibe.vad.events import (
    VoiceState,
    VADState,
    VADStateChange,
    VADSilenceTimeout,
)


def test_voice_state_enum():
    assert VoiceState.SILENCE.value == "silence"
    assert VoiceState.SPEAKING.value == "speaking"


def test_vad_state_creation():
    state = VADState(voice_state=VoiceState.SPEAKING)
    assert state.voice_state == VoiceState.SPEAKING
    assert state.confidence == 1.0


def test_vad_state_custom_confidence():
    state = VADState(voice_state=VoiceState.SILENCE, confidence=0.5)
    assert state.confidence == 0.5


def test_vad_state_change():
    old = VADState(voice_state=VoiceState.SPEAKING)
    new = VADState(voice_state=VoiceState.SILENCE)
    change = VADStateChange(old_state=old, new_state=new, silence_duration=1.5)
    assert change.old_state == old
    assert change.new_state == new
    assert change.silence_duration == 1.5


def test_vad_silence_timeout():
    event = VADSilenceTimeout(silence_duration=2.0)
    assert event.silence_duration == 2.0


def test_events_are_frozen():
    state = VADState(voice_state=VoiceState.SILENCE)
    with pytest.raises(AttributeError):
        state.voice_state = VoiceState.SPEAKING
