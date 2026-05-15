"""Test fixtures and utilities for audio testing."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Final

from pydub import AudioSegment  # type: ignore[import-not-found]

# Path to audio test files directory
AUDIO_TEST_DIR: Final[Path] = Path("/Users/didi/Downloads/audio/en/clips")

# Representative audio test files for testing
AUDIO_TEST_FILES: Final[list[str]] = [
    "common_voice_en_42696072.mp3",  # 44 KB
    "common_voice_en_42696165.mp3",  # 41 KB
    "common_voice_en_42696166.mp3",  # 27 KB
    "common_voice_en_42696402.mp3",  # 40 KB
    "common_voice_en_42698957.mp3",  # 42 KB
    "common_voice_en_42698961.mp3",  # 78 KB (longer file)
    "common_voice_en_42698982.mp3",  # 34 KB
    "common_voice_en_42698985.mp3",  # 25 KB
]

# Audio conversion settings
SAMPLE_RATE: Final[int] = 16000
SAMPLE_WIDTH: Final[int] = 2  # int16 = 2 bytes
CHANNELS: Final[int] = 1  # mono
CHUNK_SAMPLES: Final[int] = 4096  # samples per chunk


def load_audio_file(filename: str) -> bytes:
    """Load an MP3 audio file and convert to PCM int16 format.

    Args:
        filename: Name of the MP3 file in AUDIO_TEST_DIR.

    Returns:
        Raw PCM audio data as bytes (int16, 16kHz, mono).
    """
    file_path = AUDIO_TEST_DIR / filename

    # Load MP3 and convert to desired format
    audio = AudioSegment.from_mp3(str(file_path))
    audio = audio.set_frame_rate(SAMPLE_RATE)
    audio = audio.set_channels(CHANNELS)
    audio = audio.set_sample_width(SAMPLE_WIDTH)

    return audio.raw_data


async def audio_chunk_stream(audio_data: bytes) -> AsyncIterator[bytes]:
    """Yield audio data in chunks of 4096 samples.

    Args:
        audio_data: Raw PCM audio bytes (int16 format).

    Yields:
        Audio chunks of 4096 samples (8192 bytes) each.
    """
    chunk_size = CHUNK_SAMPLES * SAMPLE_WIDTH  # 4096 samples * 2 bytes

    offset = 0
    while offset < len(audio_data):
        chunk = audio_data[offset : offset + chunk_size]
        yield chunk
        offset += chunk_size


async def load_audio_as_stream(filename: str) -> AsyncIterator[bytes]:
    """Load audio file and return as async iterator of chunks.

    Convenience function combining load_audio_file and audio_chunk_stream.

    Args:
        filename: Name of the MP3 file in AUDIO_TEST_DIR.

    Yields:
        Audio chunks of 4096 samples each.
    """
    audio_data = load_audio_file(filename)
    async for chunk in audio_chunk_stream(audio_data):
        yield chunk
