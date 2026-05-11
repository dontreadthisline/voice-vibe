from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from voicevibe.vad.events import VADEvent


@runtime_checkable
class VADPort(Protocol):
    """Voice Activity Detection interface.

    VAD modules consume audio stream and yield state events.
    """

    def detect(
        self, audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[VADEvent]:
        """Consume audio stream, yield VAD events.

        Args:
            audio_stream: Async iterator of raw PCM audio chunks (int16).

        Yields:
            VADEvent: State changes or periodic updates.
        """
        ...
