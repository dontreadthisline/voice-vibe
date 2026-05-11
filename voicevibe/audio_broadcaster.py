from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator


class AudioBroadcaster:
    """Broadcasts audio stream to multiple consumers.

    Each consumer gets its own async iterator of the same audio chunks.

    Note: Designed for short-lived sessions where all consumers process at
    similar speeds. Slow consumers will block broadcast() for all subscribers.
    """

    def __init__(self) -> None:
        self._queues: list[asyncio.Queue[bytes | None]] = []

    def subscribe(self) -> AsyncIterator[bytes]:
        """Subscribe to the broadcast, returns an async iterator."""
        queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._queues.append(queue)
        return self._consume(queue)

    async def _consume(self, queue: asyncio.Queue[bytes | None]) -> AsyncIterator[bytes]:
        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield chunk

    async def broadcast(self, audio_stream: AsyncIterator[bytes]) -> None:
        """Broadcast audio stream to all subscribers."""
        async for chunk in audio_stream:
            for queue in self._queues:
                await queue.put(chunk)
        # Signal end to all subscribers
        for queue in self._queues:
            await queue.put(None)

    def close(self) -> None:
        """Signal end to all subscribers without waiting."""
        for queue in self._queues:
            try:
                queue.put_nowait(None)
            except asyncio.QueueFull:
                pass
