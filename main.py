"""
Voice session module - provides VoiceSession for recording and transcribing voice.

Usage:
    uv run python main.py
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from voicevibe.audio_broadcaster import AudioBroadcaster
from voicevibe.audio_recorder import AudioRecorder, RecordingMode
from voicevibe.config import TranscribeModelConfig, TranscribeProviderConfig
from voicevibe.transcribe import MistralTranscribeClient
from voicevibe.transcribe.transcribe_client_port import (
    TranscribeDone,
    TranscribeError,
    TranscribeTextDelta,
)
from voicevibe.vad import SimpleVAD, VADSilenceTimeout


class VoiceSession:
    """Voice interaction session with VAD-based silence detection.

    Integrates audio recording, voice activity detection, and transcription
    into a single cohesive session.

    Example:
        session = VoiceSession()
        text = await session.listen()
        print(f"You said: {text}")
        await session.close()
    """

    def __init__(
        self,
        silence_threshold: float = 0.02,
        silence_duration: float = 1.5,
        max_duration: float = 30.0,
        sample_rate: int = 16000,
    ) -> None:
        """Initialize VoiceSession.

        Args:
            silence_threshold: Peak level threshold (0.0-1.0) for silence detection.
            silence_duration: Seconds of silence before stopping recording.
            max_duration: Maximum recording duration in seconds.
            sample_rate: Audio sample rate in Hz.
        """
        self._recorder = AudioRecorder()
        self._silence_threshold = silence_threshold
        self._silence_duration = silence_duration
        self._max_duration = max_duration
        self._sample_rate = sample_rate
        self._transcribe_provider = TranscribeProviderConfig(
            name="mistral",
            api_base="wss://api.mistral.ai",
            api_key_env_var="MISTRAL_API_KEY",
        )
        self._transcribe_model = TranscribeModelConfig(
            name="voxtral-mini-transcribe-realtime-2602",
            provider="mistral",
            alias="voxtral-realtime",
            sample_rate=sample_rate,
        )

    async def listen(self) -> str:
        """Record audio, detect silence, and transcribe.

        Records from microphone until silence is detected (or max duration).
        Returns the transcribed text.

        Returns:
            Transcribed text string, or empty string if no speech detected.
        """
        broadcaster = AudioBroadcaster()
        vad = SimpleVAD(
            silence_threshold=self._silence_threshold,
            silence_duration=self._silence_duration,
            sample_rate=self._sample_rate,
        )
        client = MistralTranscribeClient(
            provider=self._transcribe_provider,
            model=self._transcribe_model,
        )

        # Subscribe to audio for VAD and transcription
        vad_stream = broadcaster.subscribe()
        transcribe_stream = broadcaster.subscribe()

        # Start recording
        self._recorder.start(
            mode=RecordingMode.STREAM,
            sample_rate=self._sample_rate,
            channels=1,
            max_duration=self._max_duration,
        )

        print("Listening... (speak now)")

        # Create tasks
        broadcast_task = asyncio.create_task(
            broadcaster.broadcast(self._recorder.audio_stream())
        )
        vad_task = asyncio.create_task(self._run_vad(vad, vad_stream))
        transcribe_task = asyncio.create_task(
            self._run_transcription(client, transcribe_stream)
        )

        # Wait for VAD to detect silence timeout
        await vad_task

        # Broadcast task should complete after VAD signals end
        await broadcast_task

        # Get transcription result
        result = await transcribe_task

        print("Done.")
        return result

    async def _run_vad(self, vad: SimpleVAD, audio_stream: AsyncIterator[bytes]) -> None:
        """Run VAD detection until silence timeout."""
        async for event in vad.detect(audio_stream):
            if isinstance(event, VADSilenceTimeout):
                self._recorder.stop(wait_for_queue_drained=True)
                return

    async def _run_transcription(
        self,
        client: MistralTranscribeClient,
        audio_stream: AsyncIterator[bytes],
    ) -> str:
        """Run transcription and return accumulated text."""
        print("Transcribing...")
        result = ""
        async for event in client.transcribe(audio_stream):
            if isinstance(event, TranscribeTextDelta):
                result += event.text
            elif isinstance(event, TranscribeDone):
                break
            elif isinstance(event, TranscribeError):
                print(f"Transcription error: {event.message}")
                break
        return result

    async def close(self) -> None:
        """Clean up resources."""
        if self._recorder.is_recording:
            self._recorder.cancel()
        await asyncio.sleep(0.1)


async def main() -> None:
    """Example: Record and transcribe once."""
    session = VoiceSession(
        silence_threshold=0.02,
        silence_duration=1.5,
        max_duration=30.0,
    )
    try:
        result = await session.listen()
        print(f"Result: {result if result else '(no speech detected)'}")
    except KeyboardInterrupt:
        print("\nCancelled by user")
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
