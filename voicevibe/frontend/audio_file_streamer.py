"""Audio file streamer for testing VAD+ASR pipeline without microphone."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Final

from pydub import AudioSegment  # type: ignore[import-not-found]

# Default test file from conftest.py
DEFAULT_TEST_FILE: Final[Path] = Path("/Users/didi/Downloads/audio/en/clips/common_voice_en_42696072.mp3")

# Audio conversion settings (match conftest.py)
SAMPLE_RATE: Final[int] = 16000
SAMPLE_WIDTH: Final[int] = 2  # int16 = 2 bytes
CHANNELS: Final[int] = 1  # mono
CHUNK_SAMPLES: Final[int] = 4096  # samples per chunk


class AudioFileStreamer:
    """Streams audio from a file as async chunks, simulating real-time input."""

    def __init__(
        self,
        filepath: Path | str = DEFAULT_TEST_FILE,
        chunk_delay: float = 0.1,
    ):
        """Initialize the file streamer.

        Args:
            filepath: Path to the MP3 audio file.
            chunk_delay: Delay in seconds between chunks to simulate real-time streaming.
        """
        self.filepath = Path(filepath)
        self.chunk_delay = chunk_delay

    def _load_and_convert(self) -> bytes:
        """Load MP3 and convert to PCM int16 format.

        Returns:
            Raw PCM audio data (int16, 16kHz, mono).
        """
        audio = AudioSegment.from_mp3(str(self.filepath))
        audio = audio.set_frame_rate(SAMPLE_RATE)
        audio = audio.set_channels(CHANNELS)
        audio = audio.set_sample_width(SAMPLE_WIDTH)
        return audio.raw_data

    async def audio_stream(self) -> AsyncIterator[bytes]:
        """Yield audio chunks from file, simulating real-time stream.

        Yields:
            Audio chunks of 4096 samples (8192 bytes) each.
        """
        audio_data = self._load_and_convert()
        chunk_size = CHUNK_SAMPLES * SAMPLE_WIDTH  # 4096 samples * 2 bytes

        offset = 0
        while offset < len(audio_data):
            chunk = audio_data[offset : offset + chunk_size]
            await asyncio.sleep(self.chunk_delay)
            yield chunk
            offset += chunk_size
