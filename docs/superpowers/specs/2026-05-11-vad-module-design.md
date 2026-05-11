# VAD 模块设计文档

## 背景

当前静音检测逻辑耦合在 `AudioBridge` 中，使用简单的阈值判断。用户希望：
1. 将静音检测抽象为独立模块
2. 支持实验多种算法（简单阈值 + ML 模型）
3. 实现实时转录流程：边录边转，静音停止

## 目标

- 解耦静音检测与录音模块
- 提供可插拔的 VAD 算法接口
- 迁移现有简单阈值算法
- 改造 main.py 实现实时交互

## 架构设计

### 模块结构

```
voicevibe/
├── vad/                         # 新增模块
│   ├── __init__.py              # 导出公共接口
│   ├── vad_port.py              # Protocol 接口定义
│   ├── simple_vad.py            # 简单阈值实现
│   └── events.py                # 状态/事件类型
├── audio_broadcaster.py         # 新增：音频流广播器
└── ...
```

### 组件关系

```
┌─────────────────┐
│  AudioRecorder  │
│  (录音模块)      │
└────────┬────────┘
         │ bytes (audio stream)
         ▼
┌─────────────────┐
│AudioBroadcaster │ ← 新增组件
│  (流分发器)      │
└────┬───────┬────┘
     │       │
     ▼       ▼
┌───────┐ ┌───────┐
│  VAD  │ │  ASR  │
│(静音) │ │(转录) │
└───────┘ └───────┘
```

## 接口设计

### 1. VADPort (Protocol)

```python
# voicevibe/vad/vad_port.py
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

### 2. 事件类型

```python
# voicevibe/vad/events.py
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

### 3. SimpleVAD 实现

```python
# voicevibe/vad/simple_vad.py
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

### 4. AudioBroadcaster

```python
# voicevibe/audio_broadcaster.py
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

### 5. 改造后的 main.py

```python
# main.py
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
        self._stop_event = asyncio.Event()
    
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
        async for event in client.transcribe(audio_stream):
            if isinstance(event, TranscribeTextDelta):
                result += event.text
                print(event.text, end="", flush=True)
            elif isinstance(event, TranscribeDone):
                break
            elif isinstance(event, TranscribeError):
                print(f"\n识别错误: {event.message}")
                break
        
        print()  # Newline after transcription
        return result


async def main() -> None:
    session = VoiceSession(
        silence_threshold=0.02,
        silence_duration=1.5,
        max_duration=30.0,
    )
    result = await session.run()
    print(f"\n识别结果: {result}" if result else "\n无内容")


if __name__ == "__main__":
    asyncio.run(main())
```

## 实现步骤

1. 创建 `voicevibe/vad/` 模块
   - `__init__.py` - 导出公共接口
   - `events.py` - 事件类型定义
   - `vad_port.py` - Protocol 接口
   - `simple_vad.py` - 简单阈值实现

2. 创建 `voicevibe/audio_broadcaster.py`

3. 改造 `main.py`
   - 删除旧的 `AudioBridge` 类
   - 新建 `VoiceSession` 类
   - 实现并行 VAD + ASR

4. 更新 `CLAUDE.md` 文档

## 扩展性

未来添加 ML 模型 VAD 时，只需实现 `VADPort` 协议：

```python
class SileroVAD:
    def __init__(self, threshold: float = 0.5, ...) -> None:
        # Load model
    
    async def detect(
        self, audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[VADEvent]:
        # Use Silero model for detection
        ...
```
