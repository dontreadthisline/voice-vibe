"""Audio dataset management for benchmarking."""

from __future__ import annotations

import json
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class AudioSample:
    """Single audio sample with ground truth metadata."""
    file_path: Path
    ground_truth_text: str
    vad_segments: list[tuple[float, float]]  # (start, end) seconds
    duration: float
    metadata: dict[str, Any]


class AudioDataset:
    """Manages test audio samples for benchmarking."""

    def __init__(self, audio_dir: Path):
        """Initialize dataset from a directory of audio files.

        Expects:
        - sample1.wav, sample2.wav, ... (audio files)
        - sample1.json, sample2.json, ... (ground truth metadata)
        """
        self.audio_dir = audio_dir
        self.samples: list[AudioSample] = []
        self._load_samples()

    def _load_samples(self) -> None:
        """Load all audio samples from the directory."""
        if not self.audio_dir.exists():
            return

        wav_files = sorted(self.audio_dir.glob("*.wav"))

        for wav_path in wav_files:
            json_path = wav_path.with_suffix(".json")

            # Load ground truth metadata
            if json_path.exists():
                with open(json_path, encoding="utf-8") as f:
                    meta = json.load(f)
            else:
                meta = {}

            # Get audio duration
            duration = self._get_wav_duration(wav_path)

            sample = AudioSample(
                file_path=wav_path,
                ground_truth_text=meta.get("ground_truth_text", ""),
                vad_segments=[tuple(seg) for seg in meta.get("vad_segments", [])],
                duration=duration,
                metadata=meta.get("metadata", {}),
            )
            self.samples.append(sample)

    def _get_wav_duration(self, wav_path: Path) -> float:
        """Get duration of a WAV file in seconds."""
        with wave.open(str(wav_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate)

    def __len__(self) -> int:
        return len(self.samples)

    def __iter__(self):
        return iter(self.samples)

    def __getitem__(self, index: int) -> AudioSample:
        return self.samples[index]


def read_wav_as_chunks(
    wav_path: Path,
    chunk_size: int = 4096,
) -> tuple[bytes, int]:
    """Read WAV file and return raw PCM data and sample rate.

    Args:
        wav_path: Path to WAV file.
        chunk_size: Chunk size for reading (not used, kept for compatibility).

    Returns:
        Tuple of (raw_pcm_bytes, sample_rate).
    """
    with wave.open(str(wav_path), "rb") as wf:
        sample_rate = wf.getframerate()
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()

        # Read all frames
        raw_data = wf.readframes(wf.getnframes())

        # Convert to mono if stereo
        if n_channels == 2 and sample_width == 2:
            import struct
            samples = struct.unpack(f"<{len(raw_data) // 2}h", raw_data)
            mono_samples = samples[::2]  # Take left channel only
            raw_data = struct.pack(f"<{len(mono_samples)}h", *mono_samples)

        return raw_data, sample_rate
