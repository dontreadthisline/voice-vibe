# VAD Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract silence detection into a standalone VAD module with pluggable algorithm interface.

**Architecture:** Port-adapter pattern with VADPort protocol. SimpleVAD implements energy-based threshold detection. AudioBroadcaster enables parallel VAD + ASR processing.

**Tech Stack:** Python 3.12+, asyncio, dataclasses, typing.Protocol

---

## File Structure

| File | Purpose |
|------|---------|
| `voicevibe/vad/events.py` | VoiceState enum, VADState, VADStateChange, VADSilenceTimeout dataclasses |
| `voicevibe/vad/vad_port.py` | VADPort Protocol interface |
| `voicevibe/vad/simple_vad.py` | SimpleVAD implementation (energy-based) |
| `voicevibe/vad/__init__.py` | Public exports |
| `voicevibe/audio_broadcaster.py` | AudioBroadcaster for stream distribution |
| `tests/test_vad.py` | Unit tests for VAD module |
| `tests/test_audio_broadcaster.py` | Unit tests for AudioBroadcaster |
| `main.py` | VoiceSession class replacing AudioBridge |

---

### Task 1: Create VAD Events Module

**Files:**
- Create: `voicevibe/vad/events.py`
- Create: `tests/test_vad.py`

- [ ] **Step 1: Write failing tests for VAD events**

Create `tests/test_vad.py`:

```python
from __future__ import annotations

from voicevibe.vad.events import (
    VoiceState,
    VADState,
    VADStateChange,
    VADSilenceTimeout,
)


def test_voice_state_enum():
    assert VoiceState.SILENCE.value == "silence"
    assert VoiceState.SPEAKING.value == "speaking"


def test_vad_state_creation():
    state = VADState(voice_state=VoiceState.SPEAKING)
    assert state.voice_state == VoiceState.SPEAKING
    assert state.confidence == 1.0


def test_vad_state_custom_confidence():
    state = VADState(voice_state=VoiceState.SILENCE, confidence=0.5)
    assert state.confidence == 0.5


def test_vad_state_change():
    old = VADState(voice_state=VoiceState.SPEAKING)
    new = VADState(voice_state=VoiceState.SILENCE)
    change = VADStateChange(old_state=old, new_state=new, silence_duration=1.5)
    assert change.old_state == old
    assert change.new_state == new
    assert change.silence_duration == 1.5


def test_vad_silence_timeout():
    event = VADSilenceTimeout(silence_duration=2.0)
    assert event.silence_duration == 2.0


def test_events_are_frozen():
    state = VADState(voice_state=VoiceState.SILENCE)
    try:
        state.voice_state = VoiceState.SPEAKING
        assert False, "Should not be able to modify frozen dataclass"
    except AttributeError:
        pass
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_vad.py -v`
Expected: FAIL with import error

- [ ] **Step 3: Create vad directory**

```bash
mkdir -p voicevibe/vad
```

- [ ] **Step 4: Create the events module**

Create `voicevibe/vad/events.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class VoiceState(Enum):
    SILENCE = auto()
    SPEAKING = auto()


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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_vad.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add voicevibe/vad/events.py tests/test_vad.py
git commit -m "feat(vad): add VAD event types"
```

---

### Task 2: Create VAD Port Protocol

**Files:**
- Create: `voicevibe/vad/vad_port.py`
- Modify: `tests/test_vad.py`

- [ ] **Step 1: Write failing test for VADPort protocol**

Add to `tests/test_vad.py`:

```python
from collections.abc import AsyncIterator
from voicevibe.vad.vad_port import VADPort
from voicevibe.vad.events import VADEvent


class MockVAD:
    """Mock implementation for testing protocol compliance."""
    
    async def detect(
        self, audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[VADEvent]:
        async for chunk in audio_stream:
            pass
        yield VADSilenceTimeout(silence_duration=1.0)


def test_vad_port_protocol_compliance():
    vad = MockVAD()
    assert isinstance(vad, VADPort)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_vad.py::test_vad_port_protocol_compliance -v`
Expected: FAIL with import error

- [ ] **Step 3: Create the vad_port module**

Create `voicevibe/vad/vad_port.py`:

```python
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from voicevibe.vad.events import VADEvent


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_vad.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add voicevibe/vad/vad_port.py tests/test_vad.py
git commit -m "feat(vad): add VADPort protocol interface"
```

---

### Task 3: Implement SimpleVAD

**Files:**
- Create: `voicevibe/vad/simple_vad.py`
- Modify: `tests/test_vad.py`

- [ ] **Step 1: Write failing tests for SimpleVAD**

Add to `tests/test_vad.py`:

```python
import asyncio
import struct

from voicevibe.vad import SimpleVAD
from voicevibe.vad.events import VoiceState, VADStateChange, VADSilenceTimeout


def make_silent_chunk() -> bytes:
    """Create a silent audio chunk (all zeros)."""
    return b'\x00\x00' * 1024


def make_loud_chunk(amplitude: int = 10000) -> bytes:
    """Create a loud audio chunk with specified amplitude."""
    samples = [amplitude if i % 2 == 0 else -amplitude for i in range(1024)]
    return struct.pack(f"<{len(samples)}h", *samples)


async def collect_events(vad: SimpleVAD, chunks: list[bytes]) -> list:
    """Helper to collect all VAD events from chunks."""
    async def audio_stream():
        for chunk in chunks:
            yield chunk
    
    events = []
    async for event in vad.detect(audio_stream()):
        events.append(event)
    return events


def test_simple_vad_silence_timeout():
    """Test that continuous silence triggers timeout."""
    vad = SimpleVAD(
        silence_threshold=0.01,
        silence_duration=0.1,  # Very short for testing
    )
    
    # Generate enough silent chunks to trigger timeout
    chunks = [make_silent_chunk() for _ in range(20)]
    
    events = asyncio.run(collect_events(vad, chunks))
    
    assert len(events) >= 1
    assert isinstance(events[-1], VADSilenceTimeout)


def test_simple_vad_state_change_speaking_to_silence():
    """Test state change from speaking to silence."""
    vad = SimpleVAD(
        silence_threshold=0.01,
        silence_duration=2.0,  # Long timeout so we see state changes
    )
    
    chunks = [
        make_loud_chunk(),      # Speaking
        make_loud_chunk(),      # Speaking
        make_silent_chunk(),    # Silence starts
        make_silent_chunk(),    # Still silence
    ]
    
    events = asyncio.run(collect_events(vad, chunks))
    
    # Should have: SPEAKING state change, then SILENCE state change
    state_changes = [e for e in events if isinstance(e, VADStateChange)]
    assert len(state_changes) >= 1
    
    # First state change should be silence -> speaking
    first_change = state_changes[0]
    assert first_change.old_state.voice_state == VoiceState.SILENCE
    assert first_change.new_state.voice_state == VoiceState.SPEAKING


def test_simple_vad_speaking_resets_silence():
    """Test that speaking resets silence timer."""
    vad = SimpleVAD(
        silence_threshold=0.01,
        silence_duration=0.1,
    )
    
    chunks = [
        make_silent_chunk(),    # Silence
        make_silent_chunk(),    # More silence
        make_loud_chunk(),      # Speaking! Resets silence
        make_silent_chunk(),    # New silence starts
        make_silent_chunk(),    # More silence
        make_silent_chunk(),    # Still not enough for timeout
    ]
    
    events = asyncio.run(collect_events(vad, chunks))
    
    # Should not have timeout yet (need more silence after speaking)
    timeouts = [e for e in events if isinstance(e, VADSilenceTimeout)]
    assert len(timeouts) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_vad.py -v`
Expected: FAIL with import errors

- [ ] **Step 3: Create the SimpleVAD implementation**

Create `voicevibe/vad/simple_vad.py`:

```python
from __future__ import annotations

import asyncio
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
    """
    
    def __init__(
        self,
        silence_threshold: float = 0.02,
        silence_duration: float = 1.5,
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> None:
        """
        Args:
            silence_threshold: Peak level threshold (0.0-1.0) for silence detection.
            silence_duration: Seconds of silence before timeout.
            sample_rate: Audio sample rate in Hz.
            channels: Number of audio channels.
        """
        self._silence_threshold = silence_threshold
        self._silence_duration = silence_duration
        self._sample_rate = sample_rate
        self._channels = channels
    
    async def detect(
        self, audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[VADEvent]:
        current_state = VADState(voice_state=VoiceState.SILENCE)
        silence_start: float | None = None
        
        async for chunk in audio_stream:
            peak = self._compute_peak(chunk)
            now = asyncio.get_event_loop().time()
            
            if peak < self._silence_threshold:
                # Silence detected
                if silence_start is None:
                    silence_start = now
                
                silence_time = now - silence_start
                
                if current_state.voice_state == VoiceState.SPEAKING:
                    # State change: speaking -> silence
                    new_state = VADState(voice_state=VoiceState.SILENCE)
                    yield VADStateChange(
                        old_state=current_state,
                        new_state=new_state,
                        silence_duration=silence_time,
                    )
                    current_state = new_state
                
                if silence_time >= self._silence_duration:
                    yield VADSilenceTimeout(silence_duration=silence_time)
                    return  # End detection
            else:
                # Speaking detected
                silence_start = None
                
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
```

- [ ] **Step 4: Create VAD __init__.py**

Create `voicevibe/vad/__init__.py`:

```python
from __future__ import annotations

from voicevibe.vad.events import (
    VADEvent,
    VADSilenceTimeout,
    VADState,
    VADStateChange,
    VoiceState,
)
from voicevibe.vad.simple_vad import SimpleVAD
from voicevibe.vad.vad_port import VADPort


__all__ = [
    "VADEvent",
    "VADPort",
    "VADSilenceTimeout",
    "VADState",
    "VADStateChange",
    "VoiceState",
    "SimpleVAD",
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_vad.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add voicevibe/vad/ tests/test_vad.py
git commit -m "feat(vad): implement SimpleVAD with energy-based detection"
```

---

### Task 4: Implement AudioBroadcaster

**Files:**
- Create: `voicevibe/audio_broadcaster.py`
- Create: `tests/test_audio_broadcaster.py`

- [ ] **Step 1: Write failing tests for AudioBroadcaster**

Create `tests/test_audio_broadcaster.py`:

```python
from __future__ import annotations

import asyncio

from voicevibe.audio_broadcaster import AudioBroadcaster


async def audio_stream(chunks: list[bytes]):
    """Helper to create async iterator from list."""
    for chunk in chunks:
        yield chunk


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


async def test_broadcaster_close():
    """Test close() signals end to subscribers."""
    broadcaster = AudioBroadcaster()
    subscriber = broadcaster.subscribe()
    
    received = []
    
    async def collect():
        async for chunk in subscriber:
            received.append(chunk)
    
    task = asyncio.create_task(collect())
    
    # Small delay then close
    await asyncio.sleep(0.01)
    broadcaster.close()
    await task
    
    assert received == []


def test_broadcaster_single_subscriber_sync():
    asyncio.run(test_broadcaster_single_subscriber())


def test_broadcaster_multiple_subscribers_sync():
    asyncio.run(test_broadcaster_multiple_subscribers())


def test_broadcaster_close_sync():
    asyncio.run(test_broadcaster_close())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_audio_broadcaster.py -v`
Expected: FAIL with import error

- [ ] **Step 3: Create AudioBroadcaster**

Create `voicevibe/audio_broadcaster.py`:

```python
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator


class AudioBroadcaster:
    """Broadcasts audio stream to multiple consumers.
    
    Each consumer gets its own async iterator of the same audio chunks.
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_audio_broadcaster.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add voicevibe/audio_broadcaster.py tests/test_audio_broadcaster.py
git commit -m "feat: add AudioBroadcaster for parallel audio stream consumers"
```

---

### Task 5: Update main.py with VoiceSession

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Rewrite main.py with VoiceSession**

Replace `main.py` with:

```python
"""
语音监听示例程序

启动后自动监听用户语音，边录边转。
当检测到用户停止说话时，输出最终识别结果。
"""

from __future__ import annotations

import asyncio
from voicevibe.audio_recorder import AudioRecorder, RecordingMode
from voicevibe.audio_broadcaster import AudioBroadcaster
from voicevibe.vad import SimpleVAD
from voicevibe.vad.events import VADSilenceTimeout, VADStateChange, VoiceState
from voicevibe.config import TranscribeProviderConfig, TranscribeModelConfig
from voicevibe.transcribe import MistralTranscribeClient
from voicevibe.transcribe.transcribe_client_port import (
    TranscribeDone,
    TranscribeError,
    TranscribeTextDelta,
)


class VoiceSession:
    """Real-time voice interaction: record + transcribe with VAD-controlled stop."""
    
    def __init__(
        self,
        silence_threshold: float = 0.02,
        silence_duration: float = 1.5,
        max_duration: float = 30.0,
    ) -> None:
        self._recorder = AudioRecorder()
        self._vad = SimpleVAD(
            silence_threshold=silence_threshold,
            silence_duration=silence_duration,
        )
        self._max_duration = max_duration
    
    async def run(self) -> str:
        """Run voice session, returns transcribed text."""
        self._recorder.start(
            mode=RecordingMode.STREAM,
            sample_rate=16000,
            channels=1,
            max_duration=self._max_duration,
        )
        print("🎤 正在聆听...（请说话）")
        
        broadcaster = AudioBroadcaster()
        vad_stream = broadcaster.subscribe()
        asr_stream = broadcaster.subscribe()
        
        # Run tasks in parallel
        vad_task = asyncio.create_task(self._vad_loop(vad_stream))
        asr_task = asyncio.create_task(self._asr_loop(asr_stream))
        broadcast_task = asyncio.create_task(
            broadcaster.broadcast(self._recorder.audio_stream())
        )
        
        try:
            await vad_task  # Wait for VAD to trigger stop
        finally:
            self._recorder.stop()
            broadcaster.close()
            await asyncio.gather(asr_task, broadcast_task, return_exceptions=True)
        
        return asr_task.result()
    
    async def _vad_loop(self, audio_stream) -> None:
        """VAD monitoring loop."""
        async for event in self._vad.detect(audio_stream):
            if isinstance(event, VADStateChange):
                if event.new_state.voice_state == VoiceState.SPEAKING:
                    print("📝 检测到语音...")
                else:
                    print(f"🔇 检测到静音 ({event.silence_duration:.1f}s)")
            elif isinstance(event, VADSilenceTimeout):
                print("⏹️  静音超时，停止录音")
                return
    
    async def _asr_loop(self, audio_stream) -> str:
        """ASR transcription loop."""
        provider = TranscribeProviderConfig(
            name="mistral",
            api_base="wss://api.mistral.ai",
            api_key_env_var="MISTRAL_API_KEY",
        )
        model = TranscribeModelConfig(
            name="voxtral-mini-transcribe-realtime-2602",
            provider="mistral",
            alias="voxtral-realtime",
            sample_rate=16000,
        )
        client = MistralTranscribeClient(provider=provider, model=model)
        
        result = ""
        try:
            async for event in client.transcribe(audio_stream):
                if isinstance(event, TranscribeTextDelta):
                    result += event.text
                    print(event.text, end="", flush=True)
                elif isinstance(event, TranscribeDone):
                    break
                elif isinstance(event, TranscribeError):
                    print(f"\n识别错误: {event.message}")
                    break
        except Exception as e:
            print(f"\nASR错误: {e}")
        
        print()  # Newline after transcription
        return result


async def main() -> None:
    session: VoiceSession | None = None
    try:
        session = VoiceSession(
            silence_threshold=0.02,
            silence_duration=1.5,
            max_duration=30.0,
        )
        result = await session.run()
        if result:
            print(f"\n识别结果: {result}")
        else:
            print("\n无内容")
    except KeyboardInterrupt:
        print("\n\n用户取消")
    except Exception as e:
        print(f"\n错误: {e}")
        raise
    finally:
        if session is not None and session._recorder.is_recording:
            session._recorder.cancel()
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Run all tests to verify no regressions**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: replace AudioBridge with VoiceSession for real-time transcription"
```

---

### Task 6: Update CLAUDE.md Documentation

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update module organization in CLAUDE.md**

Add VAD module to the architecture section. Update the module organization to include:

```markdown
voicevibe/
├── audio_recorder/          # Microphone recording via sounddevice
│   ├── audio_recorder_port.py   # Protocol/interface definitions
│   └── audio_recorder.py        # Implementation with BUFFER and STREAM modes
├── audio_broadcaster.py     # Audio stream distribution to multiple consumers
├── transcribe/              # Speech-to-text
│   ├── transcribe_client_port.py
│   └── mistral_transcribe_client.py   # Mistral realtime transcription
├── vad/                     # Voice Activity Detection
│   ├── vad_port.py          # VADPort protocol
│   ├── simple_vad.py        # Energy-based threshold VAD
│   └── events.py            # VADState, VADStateChange, VADSilenceTimeout
├── llm/                     # LLM backend abstraction
│   ├── backend/
│   │   ├── base.py          # APIAdapter protocol
│   │   ├── factory.py       # BACKEND_FACTORY mapping
│   │   ├── generic.py       # OpenAI-compatible API adapter
│   │   ├── mistral.py       # Mistral-specific backend
│   │   ├── anthropic.py     # Anthropic API adapter
│   │   └── reasoning_adapter.py
│   ├── message_utils.py
│   ├── format.py
│   ├── types.py
│   └── exceptions.py
├── config.py                # Pydantic configuration models
├── types.py                 # Core domain types (LLMMessage, ToolCall, Backend, etc.)
├── logger.py
└── utils/                   # Utility modules (retry, concurrency, display, etc.)
```

- [ ] **Step 2: Add VAD section to architecture**

Add after the Audio Pipeline section:

```markdown
### VAD (Voice Activity Detection)

VAD module detects speech activity and silence in audio streams:

- `SimpleVAD`: Energy-based detection using audio peak levels
- `VADPort`: Protocol for pluggable VAD algorithms (future: Silero, WebRTC)
- Emits `VADStateChange` on speech/silence transitions
- Emits `VADSilenceTimeout` when silence exceeds configured duration

### Audio Broadcasting

`AudioBroadcaster` enables parallel processing of audio streams:
- Single audio source → multiple consumers (VAD + ASR)
- Each subscriber gets an independent async iterator
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with VAD module and AudioBroadcaster"
```

---

### Task 7: Final Verification

- [ ] **Step 1: Run all tests**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Run linting/type checking (if configured)**

Run: `uv run python -c "from voicevibe.vad import SimpleVAD; print('Import OK')"`
Expected: "Import OK"

- [ ] **Step 3: Final commit (if any changes)**

```bash
git status
# If clean, nothing to commit
```
