from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class VoiceState(Enum):
    """Voice activity state."""
    SILENCE = "silence"
    SPEAKING = "speaking"


@dataclass(frozen=True, slots=True)
class VADState:
    """Current VAD state."""
    voice_state: VoiceState
    confidence: float = 1.0  # 0.0 - 1.0


@dataclass(frozen=True, slots=True)
class VADStateChange:
    """Emitted when voice state changes."""
    old_state: VADState
    new_state: VADState
    silence_duration: float = 0.0  # seconds of continuous silence


@dataclass(frozen=True, slots=True)
class VADSilenceTimeout:
    """Emitted when silence exceeds configured duration."""
    silence_duration: float  # seconds


VADEvent = VADStateChange | VADSilenceTimeout
