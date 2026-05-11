from __future__ import annotations

import asyncio
import struct
from collections.abc import AsyncIterator

import pytest

from voicevibe.vad import SimpleVAD
from voicevibe.vad.events import (
    VADEvent,
    VoiceState,
    VADState,
    VADStateChange,
    VADSilenceTimeout,
)
from voicevibe.vad.vad_port import VADPort


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


class MockVAD:
    """Mock implementation for testing protocol compliance."""

    async def detect(
        self, audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[VADEvent]:
        async for chunk in audio_stream:
            pass
        yield VADSilenceTimeout(silence_duration=1.0)


def test_vad_port_protocol_compliance():
    vad = MockVAD()
    assert isinstance(vad, VADPort)


def make_silent_chunk() -> bytes:
    """Create a silent audio chunk (all zeros)."""
    return b'\x00\x00' * 1024


def make_loud_chunk(amplitude: int = 10000) -> bytes:
    """Create a loud audio chunk with specified amplitude."""
    samples = [amplitude if i % 2 == 0 else -amplitude for i in range(1024)]
    return struct.pack(f"<{len(samples)}h", *samples)


async def collect_events(vad: SimpleVAD, chunks: list[bytes]) -> list:
    """Helper to collect all VAD events from chunks."""
    async def audio_stream():
        for chunk in chunks:
            yield chunk

    events = []
    async for event in vad.detect(audio_stream()):
        events.append(event)
    return events


def test_simple_vad_silence_timeout():
    """Test that continuous silence triggers timeout."""
    vad = SimpleVAD(
        silence_threshold=0.01,
        silence_duration=0.1,  # Very short for testing
    )

    # Generate enough silent chunks to trigger timeout
    chunks = [make_silent_chunk() for _ in range(20)]

    events = asyncio.run(collect_events(vad, chunks))

    assert len(events) >= 1
    assert isinstance(events[-1], VADSilenceTimeout)


def test_simple_vad_state_change_speaking_to_silence():
    """Test state change from speaking to silence."""
    vad = SimpleVAD(
        silence_threshold=0.01,
        silence_duration=2.0,  # Long timeout so we see state changes
    )

    chunks = [
        make_loud_chunk(),      # Speaking
        make_loud_chunk(),      # Speaking
        make_silent_chunk(),    # Silence starts
        make_silent_chunk(),    # Still silence
    ]

    events = asyncio.run(collect_events(vad, chunks))

    # Should have: silence -> speaking, then speaking -> silence
    state_changes = [e for e in events if isinstance(e, VADStateChange)]
    assert len(state_changes) == 2

    # First state change: silence -> speaking
    first_change = state_changes[0]
    assert first_change.old_state.voice_state == VoiceState.SILENCE
    assert first_change.new_state.voice_state == VoiceState.SPEAKING

    # Second state change: speaking -> silence
    second_change = state_changes[1]
    assert second_change.old_state.voice_state == VoiceState.SPEAKING
    assert second_change.new_state.voice_state == VoiceState.SILENCE


def test_simple_vad_speaking_resets_silence():
    """Test that speaking resets silence timer."""
    vad = SimpleVAD(
        silence_threshold=0.01,
        silence_duration=0.3,  # Long enough that 3 chunks won't trigger timeout
    )

    chunks = [
        make_silent_chunk(),    # Silence
        make_silent_chunk(),    # More silence
        make_loud_chunk(),      # Speaking! Resets silence
        make_silent_chunk(),    # New silence starts
        make_silent_chunk(),    # More silence
        make_silent_chunk(),    # Still not enough for timeout
    ]

    events = asyncio.run(collect_events(vad, chunks))

    # Should not have timeout yet (need more silence after speaking)
    timeouts = [e for e in events if isinstance(e, VADSilenceTimeout)]
    assert len(timeouts) == 0
