# ============================================================
# VoiceVibe Frontend — Road Incident Reporter
# ============================================================
# Shiny Express app.  ALL audio/VAD/ASR lives in Python backend.
# Frontend (JS) is UI-only — zero microphone / audio logic.
#
# Flow:
#   User taps "语音上报"  →  JS opens voice panel, sends vv_start_voice
#   Backend starts AudioRecorder → Broadcaster → VAD + ASR (parallel)
#   If no speech in 3s  →  vv_status="timeout"  →  JS auto-closes panel
#   If speech detected  →  realtime transcript updates, until silence
#   Silence detected    →  vv_status="done", recording stops, panel stays
#   User taps close     →  JS sends vv_stop_voice, panel closes
# ============================================================

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path

from maplibre import Map, MapOptions, render_maplibregl
from maplibre.basemaps import Carto
from maplibre.controls import GeolocateControl, NavigationControl
from shiny import reactive
from shiny.express import app_opts, input, ui
from shiny.session import get_current_session

from voicevibe.audio_broadcaster import AudioBroadcaster
from voicevibe.audio_recorder import AudioRecorder, RecordingMode
from voicevibe.audio_recorder.audio_recorder_port import IncompatibleSampleRateError
from voicevibe.config import ModelConfig, ProviderConfig, TranscribeModelConfig, TranscribeProviderConfig
from voicevibe.frontend.audio_file_streamer import AudioFileStreamer
from voicevibe.llm.backend.mistral import MistralBackend
from voicevibe.transcribe import MistralTranscribeClient
from voicevibe.transcribe.transcribe_client_port import (
    TranscribeDone,
    TranscribeError,
    TranscribeTextDelta,
)
from voicevibe.types import LLMMessage, Role
from voicevibe.vad import SimpleVAD, VADSilenceTimeout, VADStateChange, VoiceState

# ------------------------------------------------------------------
# App config
# ------------------------------------------------------------------
app_opts(static_assets=Path(__file__).parent / "www")

# Load CSS in head
ui.head_content(
    ui.tags.link(rel="stylesheet", href="styles.css"),
    ui.tags.script(src="voice.js"),
)

# ------------------------------------------------------------------
# UI: Map (full-screen)
# ------------------------------------------------------------------
@render_maplibregl
def map_container():
    m = Map(
        MapOptions(
            style=Carto.VOYAGER,
            center=(116.4074, 39.9042),
            zoom=12,
        )
    )
    m.add_control(NavigationControl())
    m.add_control(GeolocateControl(track_user_location=True))
    return m


# ------------------------------------------------------------------
# Reactive state
# ------------------------------------------------------------------
transcript_result = reactive.Value("")
selected_category_val = reactive.Value("")
report_status = reactive.Value("")
_voice_task: asyncio.Task | None = None


# ------------------------------------------------------------------
# Helpers: push messages to connected frontend
# ------------------------------------------------------------------
async def _push(session, kind: str, **data) -> None:
    """Send a custom message to the frontend via Shiny WebSocket."""
    if session is not None:
        await session.send_custom_message(kind, data)


# ------------------------------------------------------------------
# Server: start voice pipeline
# ------------------------------------------------------------------
@reactive.Effect
@reactive.event(input.vv_start_voice)
async def handle_start_voice():
    global _voice_task

    # Cancel any running pipeline
    if _voice_task is not None and not _voice_task.done():
        _voice_task.cancel()
        try:
            await _voice_task
        except asyncio.CancelledError:
            pass

    # Reset state
    transcript_result.set("")

    # Capture session before launching background task
    session = get_current_session()
    await _push(session, "vv_transcript", text="")  # Clear any previous text
    await _push(session, "vv_status", state="listening")

    # Launch pipeline in background, passing session explicitly
    _voice_task = asyncio.create_task(_run_voice_pipeline(session))


# ------------------------------------------------------------------
# Server: stop voice pipeline (user clicked close)
# ------------------------------------------------------------------
@reactive.Effect
@reactive.event(input.vv_stop_voice)
def handle_stop_voice():
    global _voice_task
    if _voice_task is not None and not _voice_task.done():
        _voice_task.cancel()
    _voice_task = None


# ------------------------------------------------------------------
# Server: start voice pipeline in test mode (file-based)
# ------------------------------------------------------------------
@reactive.Effect
@reactive.event(input.vv_start_voice_test)
async def handle_start_voice_test():
    global _voice_task

    # Cancel any running pipeline
    if _voice_task is not None and not _voice_task.done():
        _voice_task.cancel()
        try:
            await _voice_task
        except asyncio.CancelledError:
            pass

    # Reset state
    transcript_result.set("")

    # Capture session before launching background task
    session = get_current_session()
    await _push(session, "vv_transcript", text="")  # Clear any previous text
    await _push(session, "vv_status", state="listening")

    # Launch pipeline in test mode (file-based audio)
    _voice_task = asyncio.create_task(_run_voice_pipeline(session, audio_source="file"))


# ------------------------------------------------------------------
# Voice Pipeline: AudioRecorder → Broadcaster → VAD + ASR (parallel)
# ------------------------------------------------------------------
async def _run_voice_pipeline(session, audio_source: str = "mic"):
    SAMPLE_RATE = 16000
    SILENCE_DURATION = 3.0
    MAX_DURATION = 30.0

    broadcaster = AudioBroadcaster()
    recorder: AudioRecorder | None = None

    actual_rate = SAMPLE_RATE

    # Create audio stream based on source type
    if audio_source == "file":
        # File mode: use AudioFileStreamer
        streamer = AudioFileStreamer()
        audio_stream = streamer.audio_stream()
    else:
        # Mic mode: use AudioRecorder
        recorder = AudioRecorder()
        try:
            recorder.start(
                mode=RecordingMode.STREAM,
                sample_rate=SAMPLE_RATE,
                channels=1,
                max_duration=MAX_DURATION,
            )
        except IncompatibleSampleRateError as exc:
            actual_rate = exc.fallback_sample_rate
            recorder.start(
                mode=RecordingMode.STREAM,
                sample_rate=actual_rate,
                channels=1,
                max_duration=MAX_DURATION,
            )
        audio_stream = recorder.audio_stream()

    vad = SimpleVAD(
        silence_threshold=0.10,  # Must be above ambient noise (~0.05)
        silence_duration=SILENCE_DURATION,
        sample_rate=actual_rate,
    )

    api_key = os.environ.get("MISTRAL_API_KEY", "")
    if not api_key:
        await _push(session, "vv_transcript", text="错误: 未配置 MISTRAL_API_KEY")
        await _push(session, "vv_status", state="error")
        return

    client = MistralTranscribeClient(
        provider=TranscribeProviderConfig(
            name="mistral",
            api_base="wss://api.mistral.ai",
            api_key_env_var="MISTRAL_API_KEY",
        ),
        model=TranscribeModelConfig(
            name="voxtral-mini-transcribe-realtime-2602",
            provider="mistral",
            alias="voxtral-realtime",
            sample_rate=actual_rate,
        ),
    )

    vad_stream = broadcaster.subscribe()
    asr_stream = broadcaster.subscribe()

    broadcast_task = asyncio.create_task(broadcaster.broadcast(audio_stream))
    vad_task = asyncio.create_task(_consume_vad(session, vad, vad_stream))
    asr_task = asyncio.create_task(_consume_asr(session, client, asr_stream))

    transcript = ""
    try:
        # Wait for VAD to decide
        await vad_task

        # VAD finished — stop recording gracefully (mic mode only)
        if recorder is not None and recorder.is_recording:
            recorder.stop(wait_for_queue_drained=True)

        # Wait for remaining tasks to finish
        await broadcast_task
        transcript = await asr_task

    except asyncio.CancelledError:
        if recorder is not None and recorder.is_recording:
            recorder.cancel()
        broadcaster.close()
        raise

    except _NoSpeech:
        # No speech detected - no error to display
        pass

    except _SilenceAfterSpeech:
        # Speech completed - wait for ASR to finish then call LLM
        await broadcast_task
        transcript = await asr_task

        if transcript:
            await _push(session, "vv_status", state="llm_streaming")
            await _call_llm_streaming(session, transcript)
            await _push(session, "vv_status", state="llm_done")

    except Exception as exc:
        await _push(session, "vv_transcript", text=f"识别出错: {exc}")
        await _push(session, "vv_status", state="error")

    finally:
        if recorder is not None and recorder.is_recording:
            recorder.cancel()
        broadcaster.close()
        await asyncio.sleep(0.1)


# —— VAD consumer ——
class _NoSpeech(Exception):
    pass


class _SilenceAfterSpeech(Exception):
    pass


async def _consume_vad(session, vad: SimpleVAD, audio_stream: AsyncIterator[bytes]) -> None:
    speech_detected = False

    async for event in vad.detect(audio_stream):
        if isinstance(event, VADStateChange):
            if event.new_state.voice_state == VoiceState.SPEAKING:
                speech_detected = True
                await _push(session, "vv_status", state="speaking")

        elif isinstance(event, VADSilenceTimeout):
            if not speech_detected:
                await _push(session, "vv_status", state="timeout")
                await _push(session, "vv_close_voice")
                raise _NoSpeech()
            else:
                await _push(session, "vv_status", state="done")
                raise _SilenceAfterSpeech()

    if not speech_detected:
        await _push(session, "vv_status", state="timeout")
        await _push(session, "vv_close_voice")
        raise _NoSpeech()
    await _push(session, "vv_status", state="done")
    raise _SilenceAfterSpeech()


# —— ASR consumer ——
async def _consume_asr(
    session,
    client: MistralTranscribeClient,
    audio_stream: AsyncIterator[bytes],
) -> str:
    result = ""
    async for event in client.transcribe(audio_stream):
        if isinstance(event, TranscribeTextDelta):
            result += event.text
            transcript_result.set(result)
            await _push(session, "vv_transcript", text=result)
        elif isinstance(event, TranscribeDone):
            break
        elif isinstance(event, TranscribeError):
            await _push(session, "vv_transcript", text=f"转录错误: {event.message}")
            break
    return result


# —— LLM streaming ——
async def _call_llm_streaming(session, transcript: str) -> None:
    """Send transcript to LLM and stream response to frontend."""
    api_key = os.environ.get("MISTRAL_API_KEY", "")
    if not api_key:
        await _push(session, "vv_llm_error", text="错误: 未配置 MISTRAL_API_KEY")
        return

    provider = ProviderConfig(
        name="mistral",
        api_base="https://api.mistral.ai",
        api_key_env_var="MISTRAL_API_KEY",
    )
    model = ModelConfig(
        name="mistral-small-latest",
        provider="mistral",
        alias="mistral-small",
    )

    async with MistralBackend(provider=provider) as backend:
        messages = [LLMMessage(role=Role.user, content=transcript)]

        try:
            await _push(session, "vv_llm_start", question=transcript)

            async for chunk in backend.complete_streaming(
                model=model,
                messages=messages,
                temperature=0.7,
                tools=None,
                max_tokens=1024,
                tool_choice=None,
                extra_headers=None,
            ):
                if chunk.message.content:
                    await _push(session, "vv_llm_chunk", text=chunk.message.content)

            await _push(session, "vv_llm_done")

        except Exception as exc:
            await _push(session, "vv_llm_error", text=f"LLM错误: {exc}")


# ------------------------------------------------------------------
# Server: category selection
# ------------------------------------------------------------------
@reactive.Effect
@reactive.event(input.selected_category)
def handle_category():
    data = input.selected_category()
    if data and isinstance(data, dict):
        selected_category_val.set(data.get("category", ""))
        report_status.set("")


# ------------------------------------------------------------------
# Server: report submission
# ------------------------------------------------------------------
@reactive.Effect
@reactive.event(input.submit_report)
def handle_submit():
    cat = selected_category_val.get()
    text = transcript_result.get()
    if not cat and not text:
        report_status.set("请选择分类或进行语音描述")
        return
    report_status.set(f"上报成功！分类: {cat or '未分类'}, 描述: {text or '无'}")
    selected_category_val.set("")
    transcript_result.set("")
