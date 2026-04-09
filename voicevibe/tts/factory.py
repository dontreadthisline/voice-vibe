from __future__ import annotations

from voicevibe.config import TTSClient, TTSModelConfig, TTSProviderConfig
from voicevibe.tts.mistral_tts_client import MistralTTSClient
from voicevibe.tts.tts_client_port import TTSClientPort

TTS_CLIENT_MAP: dict[TTSClient, type[TTSClientPort]] = {
    TTSClient.MISTRAL: MistralTTSClient
}


def make_tts_client(
    provider: TTSProviderConfig, model: TTSModelConfig
) -> TTSClientPort:
    return TTS_CLIENT_MAP[provider.client](provider=provider, model=model)
