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
from voicevibe.config import TranscribeModelConfig, TranscribeProviderConfig
from voicevibe.transcribe import MistralTranscribeClient
from voicevibe.transcribe.transcribe_client_port import (
    TranscribeDone,
    TranscribeError,
    TranscribeTextDelta,
)
from voicevibe.vad import SimpleVAD, VADSilenceTimeout, VADStateChange, VoiceState

# ------------------------------------------------------------------
# App config
# ------------------------------------------------------------------
app_opts(static_assets=Path(__file__).parent / "www")

# Load CSS + JS only.  ALL UI panels are created dynamically in voice.js.
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
async def _push(kind: str, **data) -> None:
    """Send a custom message to the frontend via Shiny WebSocket."""
    try:
        session = get_current_session()
        if session is not None:
            await session.send_custom_message(kind, data)
    except Exception:
        pass


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
    await _push("vv_status", state="listening")

    # Launch pipeline in background (pass session via closure)
    _voice_task = asyncio.create_task(_run_voice_pipeline())


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
# Voice Pipeline: AudioRecorder → Broadcaster → VAD + ASR (parallel)
# ------------------------------------------------------------------
async def _run_voice_pipeline():
    SAMPLE_RATE = 16000
    SILENCE_DURATION = 3.0
    MAX_DURATION = 30.0

    recorder = AudioRecorder()
    broadcaster = AudioBroadcaster()

    actual_rate = SAMPLE_RATE
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

    vad = SimpleVAD(
        silence_threshold=0.02,
        silence_duration=SILENCE_DURATION,
        sample_rate=actual_rate,
    )

    api_key = os.environ.get("MISTRAL_API_KEY", "")
    if not api_key:
        await _push("vv_transcript", text="错误: 未配置 MISTRAL_API_KEY")
        await _push("vv_status", state="error")
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

    broadcast_task = asyncio.create_task(broadcaster.broadcast(recorder.audio_stream()))
    vad_task = asyncio.create_task(_consume_vad(vad, vad_stream))
    asr_task = asyncio.create_task(_consume_asr(client, asr_stream))

    try:
        # Wait for VAD to decide
        await vad_task

        # VAD finished — stop recording gracefully
        if recorder.is_recording:
            recorder.stop(wait_for_queue_drained=True)

        # Wait for remaining tasks to finish
        await broadcast_task
        await asr_task

    except asyncio.CancelledError:
        if recorder.is_recording:
            recorder.cancel()
        broadcaster.close()
        raise

    except Exception as exc:
        await _push("vv_transcript", text=f"识别出错: {exc}")
        await _push("vv_status", state="error")

    finally:
        if recorder.is_recording:
            recorder.cancel()
        broadcaster.close()
        await asyncio.sleep(0.1)


# —— VAD consumer ——
class _NoSpeech(Exception):
    pass


class _SilenceAfterSpeech(Exception):
    pass


async def _consume_vad(vad: SimpleVAD, audio_stream: AsyncIterator[bytes]) -> None:
    speech_detected = False

    async for event in vad.detect(audio_stream):
        if isinstance(event, VADStateChange):
            if event.new_state.voice_state == VoiceState.SPEAKING:
                speech_detected = True
                await _push("vv_status", state="speaking")

        elif isinstance(event, VADSilenceTimeout):
            if not speech_detected:
                await _push("vv_status", state="timeout")
                await _push("vv_close_voice")
                raise _NoSpeech()
            else:
                await _push("vv_status", state="done")
                raise _SilenceAfterSpeech()

    if not speech_detected:
        await _push("vv_status", state="timeout")
        await _push("vv_close_voice")
        raise _NoSpeech()
    await _push("vv_status", state="done")
    raise _SilenceAfterSpeech()


# —— ASR consumer ——
async def _consume_asr(
    client: MistralTranscribeClient,
    audio_stream: AsyncIterator[bytes],
) -> str:
    result = ""
    async for event in client.transcribe(audio_stream):
        if isinstance(event, TranscribeTextDelta):
            result += event.text
            transcript_result.set(result)
            await _push("vv_transcript", text=result)
        elif isinstance(event, TranscribeDone):
            break
        elif isinstance(event, TranscribeError):
            await _push("vv_transcript", text=f"转录错误: {event.message}")
            break
    return result


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
