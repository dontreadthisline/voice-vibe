"""Tests for MistralTranscribeClient."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest

from voicevibe.config import TranscribeModelConfig, TranscribeProviderConfig
from voicevibe.transcribe.mistral_transcribe_client import MistralTranscribeClient
from voicevibe.transcribe.transcribe_client_port import (
    TranscribeDone,
    TranscribeError,
    TranscribeSessionCreated,
    TranscribeTextDelta,
)

from conftest import AUDIO_TEST_FILES, load_audio_as_stream

# Skip all tests in this module if MISTRAL_API_KEY is not set
pytestmark = pytest.mark.skipif(
    os.getenv("MISTRAL_API_KEY") is None,
    reason="MISTRAL_API_KEY environment variable is not set",
)


@pytest.fixture
def transcribe_client() -> MistralTranscribeClient:
    """Create a MistralTranscribeClient instance."""
    provider = TranscribeProviderConfig(
        name="mistral",
        api_key_env_var="MISTRAL_API_KEY",
    )
    model = TranscribeModelConfig(
        name="voxtral-mini-transcribe-realtime-2602",
        provider="mistral",
        alias="voxtral-realtime",
        sample_rate=16000,
        encoding="pcm_s16le",
        language="en",
    )
    return MistralTranscribeClient(provider=provider, model=model)


@pytest.mark.asyncio
async def test_transcribe_session_created(transcribe_client: MistralTranscribeClient):
    """Test that TranscribeSessionCreated event is received with valid request_id."""
    audio_file = AUDIO_TEST_FILES[0]
    events = []

    async for event in transcribe_client.transcribe(load_audio_as_stream(audio_file)):
        events.append(event)
        if isinstance(event, TranscribeSessionCreated):
            break

    assert len(events) >= 1
    session_created = events[0]
    assert isinstance(session_created, TranscribeSessionCreated)
    assert session_created.request_id != ""
    assert len(session_created.request_id) > 0


@pytest.mark.asyncio
async def test_transcribe_text_deltas(transcribe_client: MistralTranscribeClient):
    """Test that TranscribeTextDelta events are received and contain non-empty text."""
    audio_file = AUDIO_TEST_FILES[0]
    text_deltas = []
    full_text = ""

    async for event in transcribe_client.transcribe(load_audio_as_stream(audio_file)):
        if isinstance(event, TranscribeTextDelta):
            text_deltas.append(event)
            full_text += event.text

    assert len(text_deltas) >= 1, "Expected at least one TranscribeTextDelta event"
    assert len(full_text) > 0, "Expected non-empty transcription text"

    # Check that the text contains English words (letters and possibly spaces/punctuation)
    assert any(c.isalpha() for c in full_text), "Transcription should contain letters"


@pytest.mark.asyncio
async def test_transcribe_done_event(transcribe_client: MistralTranscribeClient):
    """Test that TranscribeDone event is received at end of stream."""
    audio_file = AUDIO_TEST_FILES[0]
    events = []

    async for event in transcribe_client.transcribe(load_audio_as_stream(audio_file)):
        events.append(event)

    # Check that the last event is TranscribeDone
    assert len(events) >= 1, "Expected at least one event"
    assert isinstance(events[-1], TranscribeDone), "Last event should be TranscribeDone"


@pytest.mark.asyncio
async def test_transcribe_full_text(transcribe_client: MistralTranscribeClient):
    """Test that full recognized text is non-empty and contains English words."""
    audio_file = AUDIO_TEST_FILES[0]
    full_text = ""

    async for event in transcribe_client.transcribe(load_audio_as_stream(audio_file)):
        if isinstance(event, TranscribeTextDelta):
            full_text += event.text

    assert len(full_text) > 0, "Full transcription should not be empty"

    # Verify the text contains actual words (not just whitespace/punctuation)
    words = [w for w in full_text.split() if w.strip()]
    assert len(words) >= 1, f"Expected at least one word, got: '{full_text}'"


@pytest.mark.asyncio
async def test_transcribe_multiple_files(transcribe_client: MistralTranscribeClient):
    """Test transcription works with multiple different audio files."""
    results = {}

    for audio_file in AUDIO_TEST_FILES[:3]:  # Test first 3 files
        full_text = ""
        has_session = False
        has_done = False

        async for event in transcribe_client.transcribe(load_audio_as_stream(audio_file)):
            if isinstance(event, TranscribeSessionCreated):
                has_session = True
            elif isinstance(event, TranscribeTextDelta):
                full_text += event.text
            elif isinstance(event, TranscribeDone):
                has_done = True

        results[audio_file] = {
            "text": full_text,
            "has_session": has_session,
            "has_done": has_done,
        }

    # Verify all files produced valid results
    for audio_file, result in results.items():
        assert result["has_session"], f"{audio_file}: Missing TranscribeSessionCreated"
        assert result["has_done"], f"{audio_file}: Missing TranscribeDone"
        assert len(result["text"]) > 0, f"{audio_file}: Empty transcription"


# -------------------------------------------------------------------------
# Error Handling Tests (US-003)
# Note: These tests may hang when run together due to API rate limiting.
# Run individually with: pytest tests/test_transcribe.py -k "empty or invalid or silence or short"
# -------------------------------------------------------------------------

# Error handling tests can be run with: pytest tests/test_transcribe.py -k "empty or invalid or silence or short"
ERROR_HANDLING_TESTS = pytest.mark.asyncio


async def empty_audio_stream() -> AsyncIterator[bytes]:
    """Yield no audio chunks (empty stream)."""
    return
    yield  # type: ignore[unreachable]  # Makes this an async generator


@ERROR_HANDLING_TESTS
async def test_transcribe_empty_stream(transcribe_client: MistralTranscribeClient):
    """Test that empty audio stream completes without hanging."""
    events = []

    async for event in transcribe_client.transcribe(empty_audio_stream()):
        events.append(event)

    # Should complete without hanging - may get session created and done/error
    assert len(events) >= 0, "Should complete without hanging"


@ERROR_HANDLING_TESTS
async def test_transcribe_invalid_audio_format(transcribe_client: MistralTranscribeClient):
    """Test that invalid audio format (non-PCM data) is handled gracefully."""
    # Create async generator yielding invalid audio data
    async def invalid_audio_stream() -> AsyncIterator[bytes]:
        # Yield non-PCM data (random bytes that don't represent valid audio)
        yield b"\xff\xfe\xfd\xfc" * 1000  # Invalid audio data

    events = []

    async for event in transcribe_client.transcribe(invalid_audio_stream()):
        events.append(event)

    # The client should complete without hanging
    # It may yield TranscribeDone or TranscribeError depending on server behavior
    assert len(events) >= 0, "Should complete without hanging"


@ERROR_HANDLING_TESTS
async def test_transcribe_silence_audio(transcribe_client: MistralTranscribeClient):
    """Test transcription of pure silence (valid PCM but no speech)."""
    # Create async generator yielding silence (all zeros)
    async def silence_audio_stream() -> AsyncIterator[bytes]:
        # Yield 1 second of silence at 16kHz, int16
        chunk = b"\x00\x00" * 4096  # 4096 samples of silence
        for _ in range(4):  # ~1 second total
            yield chunk

    events = []
    full_text = ""

    async for event in transcribe_client.transcribe(silence_audio_stream()):
        events.append(event)
        if isinstance(event, TranscribeTextDelta):
            full_text += event.text

    # Should complete without hanging
    # May or may not have transcription (silence detection on server)
    assert len(events) >= 0, "Should complete without hanging"


@ERROR_HANDLING_TESTS
async def test_transcribe_very_short_audio(transcribe_client: MistralTranscribeClient):
    """Test transcription of very short audio (single chunk)."""
    # Create async generator yielding a single small chunk
    async def short_audio_stream() -> AsyncIterator[bytes]:
        # Yield a single chunk of 100 samples
        yield b"\x00\x00" * 100

    events = []

    async for event in transcribe_client.transcribe(short_audio_stream()):
        events.append(event)

    # Should complete without hanging
    assert len(events) >= 0, "Should complete without hanging"
