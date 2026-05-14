"""
VoiceVibe — main entry point.

Usage:
    # 启动前端 Shiny 应用（默认）
    uv run python main.py
    uv run python main.py --port 8080

    # 运行录音 demo
    uv run python main.py demo

    # 查看帮助
    uv run python main.py --help
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path

FRONTEND_APP = Path(__file__).parent / "voicevibe" / "frontend" / "app.py"


def _get_local_ip() -> str:
    """获取本机真实 IP（非 loopback）"""
    import socket

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


# ───────────────────────────────────────────────────────────────
# CLI
# ───────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="voicevibe",
        description="VoiceVibe — 语音 AI 路况上报系统",
    )
    sub = parser.add_subparsers(dest="command", help="可用命令")

    # frontend (default when no subcommand given)
    frontend = sub.add_parser("frontend", help="启动前端 Shiny 应用")
    frontend.add_argument("--host", default="0.0.0.0", help="监听地址 (默认: 0.0.0.0)")
    frontend.add_argument(
        "--port", type=int, default=8080, help="监听端口 (默认: 8080)"
    )
    frontend.add_argument(
        "--reload", action="store_true", help="开发模式: 文件变化自动重启"
    )

    # demo
    demo = sub.add_parser("demo", help="运行录音 + 转录 demo")
    demo.add_argument(
        "--silence-threshold", type=float, default=0.10, help="静音阈值 (默认: 0.10)"
    )
    demo.add_argument(
        "--silence-duration", type=float, default=1.5, help="静音持续秒数 (默认: 1.5)"
    )
    demo.add_argument(
        "--max-duration", type=float, default=30.0, help="最大录音时长 (默认: 30.0)"
    )

    return parser


def run_frontend(host: str = "0.0.0.0", port: int = 8080, reload: bool = False) -> int:
    """启动前端 Shiny 应用。"""
    cmd = [
        sys.executable,
        "-m",
        "shiny",
        "run",
        str(FRONTEND_APP),
        "--host",
        host,
        "--port",
        str(port),
    ]
    if reload:
        cmd.append("--reload")

    real_ip = _get_local_ip()
    print(f"🚀 启动前端应用  http://{real_ip}:{port}")
    print(f"   应用文件: {FRONTEND_APP}")
    print("   按 Ctrl+C 停止\n")

    try:
        result = subprocess.run(cmd)
        return result.returncode
    except KeyboardInterrupt:
        print("\n👋 已停止")
        return 0


# ───────────────────────────────────────────────────────────────
# Demo: VoiceSession
# ───────────────────────────────────────────────────────────────
async def run_demo(
    silence_threshold: float = 0.02,
    silence_duration: float = 1.5,
    max_duration: float = 30.0,
) -> None:
    """运行录音 + 实时转录 demo。"""
    from voicevibe.audio_broadcaster import AudioBroadcaster
    from voicevibe.audio_recorder import AudioRecorder, RecordingMode
    from voicevibe.config import TranscribeModelConfig, TranscribeProviderConfig
    from voicevibe.transcribe import MistralTranscribeClient
    from voicevibe.transcribe.transcribe_client_port import (
        TranscribeDone,
        TranscribeError,
        TranscribeTextDelta,
    )
    from voicevibe.vad import SimpleVAD, VADSilenceTimeout

    sample_rate = 16000

    recorder = AudioRecorder()
    broadcaster = AudioBroadcaster()
    vad = SimpleVAD(
        silence_threshold=silence_threshold,
        silence_duration=silence_duration,
        sample_rate=sample_rate,
    )
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
            sample_rate=sample_rate,
        ),
    )

    vad_stream = broadcaster.subscribe()
    transcribe_stream = broadcaster.subscribe()

    recorder.start(
        mode=RecordingMode.STREAM,
        sample_rate=sample_rate,
        channels=1,
        max_duration=max_duration,
    )

    print("🎤 正在聆听… (直接说话，静音后自动停止)")

    broadcast_task = asyncio.create_task(broadcaster.broadcast(recorder.audio_stream()))

    async def _run_vad() -> None:
        async for event in vad.detect(vad_stream):
            if isinstance(event, VADSilenceTimeout):
                recorder.stop(wait_for_queue_drained=True)
                return

    async def _run_transcription() -> str:
        result = ""
        async for event in client.transcribe(transcribe_stream):
            if isinstance(event, TranscribeTextDelta):
                result += event.text
            elif isinstance(event, TranscribeDone):
                break
            elif isinstance(event, TranscribeError):
                print(f"❌ 转录错误: {event.message}")
                break
        return result

    vad_task = asyncio.create_task(_run_vad())
    transcribe_task = asyncio.create_task(_run_transcription())

    try:
        await vad_task
        await broadcast_task
        text = await transcribe_task
        print(f"\n✅ 结果: {text if text else '(未检测到语音)'}")
    except Exception as e:
        recorder.cancel()
        broadcaster.close()
        raise
    finally:
        if recorder.is_recording:
            recorder.cancel()
        await asyncio.sleep(0.1)


# ───────────────────────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────────────────────
def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    command = args.command

    if command == "demo":
        asyncio.run(
            run_demo(
                silence_threshold=args.silence_threshold,
                silence_duration=args.silence_duration,
                max_duration=args.max_duration,
            )
        )
        return 0

    # Default: start frontend
    return run_frontend(
        host=getattr(args, "host", "localhost"),
        port=getattr(args, "port", 8080),
        reload=getattr(args, "reload", False),
    )


if __name__ == "__main__":
    sys.exit(main())
