from __future__ import annotations

import struct
from collections.abc import AsyncIterator

from voicevibe.vad.events import (
    VADEvent,
    VADSilenceTimeout,
    VADState,
    VADStateChange,
    VoiceState,
)


INT16_ABS_MAX = 2**15 - 1


class SimpleVAD:
    """Simple energy-based VAD.

    Detects silence by comparing audio peak level against threshold.
    Emits VADSilenceTimeout when silence exceeds configured duration.

    Note: Currently only supports mono audio (channels=1). The channels
    parameter is reserved for future multi-channel support.
    """

    def __init__(
        self,
        silence_threshold: float = 0.10,
        silence_duration: float = 1.5,
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> None:
        """
        Args:
            silence_threshold: Peak level threshold (0.0-1.0) for silence detection.
            silence_duration: Seconds of silence before timeout.
            sample_rate: Audio sample rate in Hz.
            channels: Number of audio channels (currently only 1 supported).
        """
        if channels != 1:
            raise NotImplementedError("Multi-channel audio is not yet supported")
        self._silence_threshold = silence_threshold
        self._silence_duration = silence_duration
        self._sample_rate = sample_rate

    async def detect(
        self, audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[VADEvent]:
        current_state = VADState(voice_state=VoiceState.SILENCE)
        silence_samples = 0

        async for chunk in audio_stream:
            peak = self._compute_peak(chunk)
            chunk_samples = len(chunk) // 2  # int16 = 2 bytes

            if peak < self._silence_threshold:
                # Silence detected
                silence_samples += chunk_samples
                silence_duration = silence_samples / self._sample_rate

                if current_state.voice_state == VoiceState.SPEAKING:
                    # State change: speaking -> silence
                    new_state = VADState(voice_state=VoiceState.SILENCE)
                    yield VADStateChange(
                        old_state=current_state,
                        new_state=new_state,
                        silence_duration=silence_duration,
                    )
                    current_state = new_state

                if silence_duration >= self._silence_duration:
                    yield VADSilenceTimeout(silence_duration=silence_duration)
                    return  # End detection
            else:
                # Speaking detected
                silence_samples = 0

                if current_state.voice_state == VoiceState.SILENCE:
                    # State change: silence -> speaking
                    new_state = VADState(voice_state=VoiceState.SPEAKING)
                    yield VADStateChange(
                        old_state=current_state,
                        new_state=new_state,
                    )
                    current_state = new_state

    def _compute_peak(self, chunk: bytes) -> float:
        """Compute normalized peak level from PCM int16 audio."""
        n_samples = len(chunk) // 2  # int16 = 2 bytes
        if n_samples == 0:
            return 0.0
        samples = struct.unpack(f"<{n_samples}h", chunk)
        return min(max(abs(s) for s in samples) / INT16_ABS_MAX, 1.0)
