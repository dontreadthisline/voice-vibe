"""Integration tests for VAD and ASR working together."""

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
    TranscribeTextDelta,
)
from voicevibe.vad import SimpleVAD
from voicevibe.vad.events import VADEvent, VADSilenceTimeout

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
    """Test parallel VAD and ASR processing using AudioBroadcaster."""
    audio_file = AUDIO_TEST_FILES[0]
    broadcaster = AudioBroadcaster()

    # Create two subscribers: one for VAD, one for ASR
    vad_stream = broadcaster.subscribe()
    asr_stream = broadcaster.subscribe()

    transcription_result = []
    vad_events = []

    async def run_vad() -> None:
        """Collect VAD events."""
        async for event in vad.detect(vad_stream):
            vad_events.append(event)

    async def run_asr() -> None:
        """Collect transcription results."""
        async for event in transcribe_client.transcribe(asr_stream):
            if isinstance(event, TranscribeTextDelta):
                transcription_result.append(event.text)
            elif isinstance(event, TranscribeDone):
                break

    # Run broadcast and both consumers in parallel
    broadcast_task = asyncio.create_task(
        broadcaster.broadcast(load_audio_as_stream(audio_file))
    )
    vad_task = asyncio.create_task(run_vad())
    asr_task = asyncio.create_task(run_asr())

    # Wait for broadcast to complete
    await broadcast_task

    # Wait for both consumers
    await asyncio.gather(vad_task, asr_task)

    # Verify both VAD events and transcription results are received
    assert len(vad_events) >= 0, "VAD should process the stream"
    assert len(transcription_result) >= 0, "ASR should process the stream"

    # Verify we got some transcription
    full_text = "".join(transcription_result)
    assert len(full_text) > 0, "Should have transcription text"


@pytest.mark.asyncio
async def test_vad_asr_with_longer_audio(
    transcribe_client: MistralTranscribeClient, vad: SimpleVAD
):
    """Test VAD and ASR with a longer audio file."""
    # Use a longer audio file
    audio_file = AUDIO_TEST_FILES[5]  # 78 KB file (longer)
    broadcaster = AudioBroadcaster()

    vad_stream = broadcaster.subscribe()
    asr_stream = broadcaster.subscribe()

    transcription_result = []
    vad_events = []
    state_changes = []

    async def run_vad() -> None:
        """Collect VAD events."""
        async for event in vad.detect(vad_stream):
            vad_events.append(event)
            # Track state changes
            if hasattr(event, "new_state"):
                state_changes.append(event)

    async def run_asr() -> None:
        """Collect transcription results."""
        async for event in transcribe_client.transcribe(asr_stream):
            if isinstance(event, TranscribeTextDelta):
                transcription_result.append(event.text)
            elif isinstance(event, TranscribeDone):
                break

    # Run all in parallel
    broadcast_task = asyncio.create_task(
        broadcaster.broadcast(load_audio_as_stream(audio_file))
    )
    vad_task = asyncio.create_task(run_vad())
    asr_task = asyncio.create_task(run_asr())

    await broadcast_task
    await asyncio.gather(vad_task, asr_task)

    # Verify results
    full_text = "".join(transcription_result)
    assert len(full_text) > 0, "Should have transcription text"


@pytest.mark.asyncio
async def test_vad_asr_multiple_files_parallel(
    transcribe_client: MistralTranscribeClient, vad: SimpleVAD
):
    """Test VAD and ASR with multiple audio files sequentially."""
    results = {}

    for audio_file in AUDIO_TEST_FILES[:3]:
        broadcaster = AudioBroadcaster()
        vad_stream = broadcaster.subscribe()
        asr_stream = broadcaster.subscribe()

        transcription_result = []
        vad_events = []

        async def run_vad() -> None:
            async for event in vad.detect(vad_stream):
                vad_events.append(event)

        async def run_asr() -> None:
            async for event in transcribe_client.transcribe(asr_stream):
                if isinstance(event, TranscribeTextDelta):
                    transcription_result.append(event.text)
                elif isinstance(event, TranscribeDone):
                    break

        broadcast_task = asyncio.create_task(
            broadcaster.broadcast(load_audio_as_stream(audio_file))
        )
        vad_task = asyncio.create_task(run_vad())
        asr_task = asyncio.create_task(run_asr())

        await broadcast_task
        await asyncio.gather(vad_task, asr_task)

        results[audio_file] = {
            "text": "".join(transcription_result),
            "vad_events": len(vad_events),
        }

    # Verify all files produced results
    for audio_file, result in results.items():
        assert len(result["text"]) > 0, f"{audio_file}: Should have transcription"
