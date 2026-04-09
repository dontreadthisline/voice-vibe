"""
语音监听示例程序

启动后自动监听用户语音，当检测到用户停止说话时，
输出语音识别结果。
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from voicevibe.audio_recorder import AudioRecorder, RecordingMode
from voicevibe.config import TranscribeProviderConfig, TranscribeModelConfig
from voicevibe.transcribe import MistralTranscribeClient
from voicevibe.transcribe.transcribe_client_port import (
    TranscribeDone,
    TranscribeError,
    TranscribeTextDelta,
)


class AudioBridge:
    def __init__(
        self,
        silence_threshold: float = 0.02,
        silence_duration: float = 1.5,
        max_duration: float = 30.0,
    ) -> None:
        self._recorder = AudioRecorder()
        self._queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._silence_threshold = silence_threshold
        self._silence_duration = silence_duration
        self._max_duration = max_duration  # 最大录音时长
        self._is_recording = False

    async def _record_task(self) -> None:
        stream_gen = None
        try:
            self._recorder.start(
                mode=RecordingMode.STREAM,
                sample_rate=16000,
                channels=1,
                max_duration=self._max_duration,
            )
            self._is_recording = True
            print("🎤 正在聆听...（请说话）")
            stream_gen = self._recorder.audio_stream()
            async for chunk in stream_gen:
                await self._queue.put(chunk)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"录音错误: {e}")
        finally:
            self._is_recording = False
            await self._queue.put(None)
            # 确保生成器被正确关闭
            if stream_gen is not None:
                try:
                    await stream_gen.aclose()
                except Exception:
                    pass

    async def _vad_task(self) -> None:
        silence_start: float | None = None

        while self._is_recording:
            await asyncio.sleep(0.1)

            if not self._recorder.is_recording:
                break

            peak = self._recorder.peak

            if peak < self._silence_threshold:
                # 检测到静音
                if silence_start is None:
                    silence_start = asyncio.get_event_loop().time()
                else:
                    silent_time = asyncio.get_event_loop().time() - silence_start
                    if silent_time >= self._silence_duration:
                        self._recorder.stop(wait_for_queue_drained=True)
                        break
            else:
                # 有语音活动，重置静音计时
                silence_start = None

        # 确保队列结束信号被放入
        await self._queue.put(None)

    async def audio_stream(self) -> AsyncIterator[bytes]:
        while True:
            chunk = await self._queue.get()
            if chunk is None:
                break
            yield chunk

    async def record_and_transcribe(self) -> str:
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
        record_task = asyncio.create_task(self._record_task())
        await asyncio.sleep(0.5)
        vad_task = asyncio.create_task(self._vad_task())
        try:
            await asyncio.gather(record_task, vad_task, return_exceptions=True)
        except Exception:
            pass

        print("📝 正在识别...")
        result_text = ""

        audio_gen = self.audio_stream()
        try:
            transcribe_gen = client.transcribe(audio_gen)
            try:
                async for event in transcribe_gen:
                    if isinstance(event, TranscribeTextDelta):
                        result_text += event.text
                        # print(event.text, end="", flush=True)
                    elif isinstance(event, TranscribeDone):
                        break
                    elif isinstance(event, TranscribeError):
                        print(f"\n识别错误: {event.message}")
                        break
            finally:
                # 确保转录生成器被正确关闭
                try:
                    await transcribe_gen.aclose()
                except Exception:
                    pass
        finally:
            try:
                await audio_gen.aclose()
            except Exception:
                pass

        return result_text


async def main() -> None:
    bridge: AudioBridge | None = None
    try:
        bridge = AudioBridge(
            silence_threshold=0.02,
            silence_duration=1.5,
            max_duration=30.0,
        )
        result = await bridge.record_and_transcribe()
        print(result if result else "（无内容）")

    except KeyboardInterrupt:
        print("\n\n用户取消")
    except Exception as e:
        print(f"\n错误: {e}")
        raise
    finally:
        if bridge is not None and bridge._recorder.is_recording:
            bridge._recorder.cancel()
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    asyncio.run(main())
