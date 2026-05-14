"""Benchmark configuration definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class VADConfig:
    """VAD implementation configuration."""
    name: str
    cls: type
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ASRConfig:
    """ASR/Transcribe implementation configuration."""
    name: str
    cls: type
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMConfig:
    """LLM backend configuration."""
    name: str
    backend: str
    model: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkConfig:
    """Benchmark configuration."""
    vads: list[VADConfig] = field(default_factory=list)
    asrs: list[ASRConfig] = field(default_factory=list)
    llms: list[LLMConfig] = field(default_factory=list)
    audio_dir: Path = Path("benchmark/data")
    output_dir: Path = Path("benchmark/results")
    runs_per_sample: int = 1


def get_default_config() -> BenchmarkConfig:
    """Get default benchmark configuration with current implementations."""
    from voicevibe.vad import SimpleVAD
    from voicevibe.transcribe import MistralTranscribeClient
    from voicevibe.config import TranscribeProviderConfig, TranscribeModelConfig
    from voicevibe.types import Backend

    return BenchmarkConfig(
        vads=[
            VADConfig(
                name="SimpleVAD",
                cls=SimpleVAD,
                params={
                    "silence_threshold": 0.02,
                    "silence_duration": 1.5,
                    "sample_rate": 16000,
                },
            ),
        ],
        asrs=[
            ASRConfig(
                name="MistralASR",
                cls=MistralTranscribeClient,
                params={
                    "provider": TranscribeProviderConfig(
                        name="mistral",
                        api_base="wss://api.mistral.ai",
                        api_key_env_var="MISTRAL_API_KEY",
                    ),
                    "model": TranscribeModelConfig(
                        name="voxtral-mini-transcribe-realtime-2602",
                        provider="mistral",
                        alias="voxtral-realtime",
                        sample_rate=16000,
                    ),
                },
            ),
        ],
        llms=[
            LLMConfig(
                name="MistralLLM",
                backend=Backend.MISTRAL.value,
                model="mistral-small-latest",
                params={},
            ),
        ],
    )
