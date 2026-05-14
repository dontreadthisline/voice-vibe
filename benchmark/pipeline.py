"""Pipeline runner for executing VAD+ASR+LLM combinations."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from voicevibe.audio_broadcaster import AudioBroadcaster
from voicevibe.transcribe.transcribe_client_port import (
    TranscribeDone,
    TranscribeError,
    TranscribeTextDelta,
)
from voicevibe.vad import VADSilenceTimeout

from benchmark.metrics import PipelineMetrics

if TYPE_CHECKING:
    from voicevibe.llm.backend.base import APIAdapter
    from voicevibe.transcribe.transcribe_client_port import TranscribeClientPort
    from voicevibe.vad.vad_port import VADPort


class PipelineRunner:
    """Executes a single VAD+ASR+LLM combination and collects metrics."""

    def __init__(
        self,
        vad: VADPort,
        asr: TranscribeClientPort,
        llm: APIAdapter | None = None,
        ground_truth_text: str = "",
        ground_truth_segments: list[tuple[float, float]] | None = None,
    ):
        """Initialize pipeline runner.

        Args:
            vad: VAD implementation instance.
            asr: ASR/Transcribe implementation instance.
            llm: LLM backend instance (optional, skip LLM if None).
            ground_truth_text: Expected transcription for WER calculation.
            ground_truth_segments: Expected VAD segments for precision/recall.
        """
        self._vad = vad
        self._asr = asr
        self._llm = llm
        self._ground_truth_text = ground_truth_text
        self._ground_truth_segments = ground_truth_segments or []

    async def run(self, audio_data: bytes, sample_rate: int = 16000) -> PipelineMetrics:
        """Run the pipeline and return metrics.

        Args:
            audio_data: Raw PCM audio data (int16).
            sample_rate: Audio sample rate.

        Returns:
            PipelineMetrics with timing and results.
        """
        total_start = time.monotonic()

        # Create audio stream from data
        broadcaster = AudioBroadcaster()
        vad_stream = broadcaster.subscribe()
        asr_stream = broadcaster.subscribe()

        # Timing storage
        vad_start = 0.0
        vad_end = 0.0
        asr_start = 0.0
        asr_end = 0.0
        llm_start = 0.0
        llm_end = 0.0

        transcription_text = ""
        llm_response = ""
        vad_detected_segments: list[tuple[float, float]] = []

        async def audio_generator() -> AsyncIterator[bytes]:
            """Yield audio chunks from pre-loaded data."""
            chunk_size = 4096
            for i in range(0, len(audio_data), chunk_size):
                yield audio_data[i:i + chunk_size]

        async def run_vad() -> list[tuple[float, float]]:
            """Run VAD and track timing."""
            nonlocal vad_start, vad_end
            vad_start = time.monotonic()
            segments = []
            async for event in self._vad.detect(vad_stream):
                if isinstance(event, VADSilenceTimeout):
                    vad_end = time.monotonic()
                    break
            vad_end = time.monotonic()
            return segments

        async def run_asr() -> str:
            """Run ASR and track timing."""
            nonlocal asr_start, asr_end
            asr_start = time.monotonic()
            result = ""
            async for event in self._asr.transcribe(asr_stream):
                if isinstance(event, TranscribeTextDelta):
                    result += event.text
                elif isinstance(event, TranscribeDone):
                    break
                elif isinstance(event, TranscribeError):
                    break
            asr_end = time.monotonic()
            return result

        # Run VAD and ASR in parallel
        broadcast_task = asyncio.create_task(broadcaster.broadcast(audio_generator()))
        vad_task = asyncio.create_task(run_vad())
        asr_task = asyncio.create_task(run_asr())

        # Wait for both to complete
        await asyncio.gather(vad_task, asr_task, broadcast_task)

        transcription_text = asr_task.result()

        # Run LLM if available
        if self._llm and transcription_text:
            llm_start = time.monotonic()
            # TODO: Implement LLM call
            llm_end = time.monotonic()

        total_end = time.monotonic()

        return PipelineMetrics(
            vad_duration_ms=(vad_end - vad_start) * 1000,
            asr_duration_ms=(asr_end - asr_start) * 1000,
            llm_duration_ms=(llm_end - llm_start) * 1000 if llm_start > 0 else 0.0,
            total_duration_ms=(total_end - total_start) * 1000,
            transcription_text=transcription_text,
            llm_response=llm_response,
            vad_detected_segments=vad_detected_segments,
            vad_ground_truth_segments=self._ground_truth_segments,
        )
