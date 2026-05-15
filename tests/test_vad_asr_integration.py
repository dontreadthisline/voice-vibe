"""Integration tests for VAD and ASR working together with AudioBroadcaster."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator

import pytest

from voicevibe.audio_broadcaster import AudioBroadcaster
from voicevibe.config import TranscribeModelConfig, TranscribeProviderConfig
from voicevibe.transcribe.mistral_transcribe_client import MistralTranscribeClient
from voicevibe.transcribe.transcribe_client_port import (
    TranscribeDone,
    TranscribeSessionCreated,
    TranscribeTextDelta,
)
from voicevibe.vad import SimpleVAD
from voicevibe.vad.events import VADStateChange, VADSilenceTimeout

from conftest import AUDIO_TEST_FILES, load_audio_file, audio_chunk_stream

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


@pytest.fixture
def vad() -> SimpleVAD:
    """Create a SimpleVAD instance with default config."""
    return SimpleVAD(
        silence_threshold=0.10,
        silence_duration=1.5,
        sample_rate=16000,
    )


@pytest.mark.asyncio
async def test_vad_asr_parallel_processing(
    transcribe_client: MistralTranscribeClient, vad: SimpleVAD
):
    """Test VAD and ASR process audio in parallel using AudioBroadcaster."""
    audio_file = AUDIO_TEST_FILES[0]
    audio_data = load_audio_file(audio_file)

    broadcaster = AudioBroadcaster()

    # Subscribe both VAD and ASR to the broadcast
    vad_stream = broadcaster.subscribe()
    asr_stream = broadcaster.subscribe()

    vad_events: list[VADStateChange | VADSilenceTimeout] = []
    transcription_events: list[object] = []
    full_text = ""

    async def run_vad() -> None:
        """Process audio stream with VAD and collect events."""
        async for event in vad.detect(vad_stream):
            vad_events.append(event)

    async def run_asr() -> None:
        """Process audio stream with ASR and collect events."""
        nonlocal full_text
        async for event in transcribe_client.transcribe(asr_stream):
            transcription_events.append(event)
            if isinstance(event, TranscribeTextDelta):
                full_text += event.text

    async def broadcast_audio() -> None:
        """Broadcast audio chunks to all subscribers."""
        await broadcaster.broadcast(audio_chunk_stream(audio_data))

    # Run all three tasks concurrently using asyncio.gather
    await asyncio.gather(
        broadcast_audio(),
        run_vad(),
        run_asr(),
    )

    # Verify VAD events were received
    assert len(vad_events) >= 1, "Expected at least one VAD event"

    # Verify transcription events were received
    assert len(transcription_events) >= 1, "Expected at least one transcription event"

    # Check for TranscribeSessionCreated
    session_created = any(
        isinstance(e, TranscribeSessionCreated) for e in transcription_events
    )
    assert session_created, "Expected TranscribeSessionCreated event"

    # Check for TranscribeDone
    has_done = any(isinstance(e, TranscribeDone) for e in transcription_events)
    assert has_done, "Expected TranscribeDone event"

    # Verify transcription produced text
    assert len(full_text) > 0, "Expected non-empty transcription"


@pytest.mark.asyncio
async def test_vad_asr_with_longer_audio(
    transcribe_client: MistralTranscribeClient, vad: SimpleVAD
):
    """Test VAD and ASR with a longer audio file using asyncio.gather."""
    # Use a longer audio file (78 KB)
    audio_file = AUDIO_TEST_FILES[5]
    audio_data = load_audio_file(audio_file)

    broadcaster = AudioBroadcaster()

    vad_stream = broadcaster.subscribe()
    asr_stream = broadcaster.subscribe()

    vad_events: list[VADStateChange | VADSilenceTimeout] = []
    transcription_events: list[object] = []
    full_text = ""

    async def run_vad() -> None:
        """Process audio stream with VAD and collect events."""
        async for event in vad.detect(vad_stream):
            vad_events.append(event)

    async def run_asr() -> None:
        """Process audio stream with ASR and collect events."""
        nonlocal full_text
        async for event in transcribe_client.transcribe(asr_stream):
            transcription_events.append(event)
            if isinstance(event, TranscribeTextDelta):
                full_text += event.text

    async def broadcast_audio() -> None:
        """Broadcast audio chunks to all subscribers."""
        await broadcaster.broadcast(audio_chunk_stream(audio_data))

    # Run all three tasks concurrently using asyncio.gather
    await asyncio.gather(
        broadcast_audio(),
        run_vad(),
        run_asr(),
    )

    # Verify results
    assert len(vad_events) >= 1, "Expected at least one VAD event"
    assert len(transcription_events) >= 1, "Expected at least one transcription event"
    assert len(full_text) > 0, "Expected non-empty transcription"


@pytest.mark.asyncio
async def test_vad_asr_multiple_files(
    transcribe_client: MistralTranscribeClient, vad: SimpleVAD
):
    """Test parallel VAD and ASR processing with multiple audio files."""
    results = []

    for audio_file in AUDIO_TEST_FILES[:3]:  # Test first 3 files
        audio_data = load_audio_file(audio_file)
        broadcaster = AudioBroadcaster()

        vad_stream = broadcaster.subscribe()
        asr_stream = broadcaster.subscribe()

        vad_events: list[VADStateChange | VADSilenceTimeout] = []
        transcription_events: list[object] = []
        full_text = ""

        async def run_vad() -> None:
            async for event in vad.detect(vad_stream):
                vad_events.append(event)

        async def run_asr() -> None:
            nonlocal full_text
            async for event in transcribe_client.transcribe(asr_stream):
                transcription_events.append(event)
                if isinstance(event, TranscribeTextDelta):
                    full_text += event.text

        async def broadcast_audio() -> None:
            await broadcaster.broadcast(audio_chunk_stream(audio_data))

        await asyncio.gather(
            broadcast_audio(),
            run_vad(),
            run_asr(),
        )

        results.append({
            "file": audio_file,
            "vad_events": len(vad_events),
            "transcription_events": len(transcription_events),
            "text": full_text,
        })

    # Verify all files produced results
    for result in results:
        assert result["vad_events"] >= 1, f"{result['file']}: Expected VAD events"
        assert result["transcription_events"] >= 1, f"{result['file']}: Expected transcription events"
        text: str = result["text"]
        assert len(text) > 0, f"{result['file']}: Expected transcription text"


@pytest.mark.asyncio
async def test_vad_detects_speech_state_changes(
    transcribe_client: MistralTranscribeClient, vad: SimpleVAD
):
    """Test that VAD correctly detects speech state changes during audio."""
    audio_file = AUDIO_TEST_FILES[0]
    audio_data = load_audio_file(audio_file)

    broadcaster = AudioBroadcaster()
    vad_stream = broadcaster.subscribe()
    asr_stream = broadcaster.subscribe()

    vad_events: list[VADStateChange | VADSilenceTimeout] = []

    async def run_vad() -> None:
        async for event in vad.detect(vad_stream):
            vad_events.append(event)

    async def run_asr() -> None:
        async for _ in transcribe_client.transcribe(asr_stream):
            pass  # Just consume the stream

    async def broadcast_audio() -> None:
        await broadcaster.broadcast(audio_chunk_stream(audio_data))

    await asyncio.gather(
        broadcast_audio(),
        run_vad(),
        run_asr(),
    )

    # Verify we got VADStateChange events
    state_changes = [e for e in vad_events if isinstance(e, VADStateChange)]
    assert len(state_changes) >= 1, "Expected at least one VADStateChange"

    # The audio file should have speech, so we expect SPEAKING state at some point
    has_speaking = any(
        sc.new_state.voice_state.value == "speaking" for sc in state_changes
    )
    assert has_speaking, "Expected SPEAKING state to be detected"
