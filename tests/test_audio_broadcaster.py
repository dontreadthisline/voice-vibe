from __future__ import annotations

import asyncio

import pytest

from voicevibe.audio_broadcaster import AudioBroadcaster


async def audio_stream(chunks: list[bytes]):
    """Helper to create async iterator from list."""
    for chunk in chunks:
        yield chunk


@pytest.mark.asyncio
async def test_broadcaster_single_subscriber():
    """Test broadcasting to a single subscriber."""
    broadcaster = AudioBroadcaster()
    subscriber = broadcaster.subscribe()

    chunks = [b"chunk1", b"chunk2", b"chunk3"]

    received = []

    async def collect():
        async for chunk in subscriber:
            received.append(chunk)

    async def send():
        await broadcaster.broadcast(audio_stream(chunks))

    collect_task = asyncio.create_task(collect())
    await send()
    await collect_task

    assert received == chunks


@pytest.mark.asyncio
async def test_broadcaster_multiple_subscribers():
    """Test broadcasting to multiple subscribers."""
    broadcaster = AudioBroadcaster()
    sub1 = broadcaster.subscribe()
    sub2 = broadcaster.subscribe()

    chunks = [b"a", b"b", b"c"]

    received1 = []
    received2 = []

    async def collect(sub, received):
        async for chunk in sub:
            received.append(chunk)

    async def send():
        await broadcaster.broadcast(audio_stream(chunks))

    task1 = asyncio.create_task(collect(sub1, received1))
    task2 = asyncio.create_task(collect(sub2, received2))
    await send()
    await asyncio.gather(task1, task2)

    assert received1 == chunks
    assert received2 == chunks


@pytest.mark.asyncio
async def test_broadcaster_close():
    """Test close() signals end to subscribers."""
    broadcaster = AudioBroadcaster()
    subscriber = broadcaster.subscribe()

    received = []

    async def collect():
        async for chunk in subscriber:
            received.append(chunk)

    task = asyncio.create_task(collect())

    # Yield control to let the collector start waiting
    await asyncio.sleep(0)
    broadcaster.close()
    await task

    assert received == []
