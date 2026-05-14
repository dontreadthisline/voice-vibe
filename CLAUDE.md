# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VoiceVibe is a Python framework for building voice AI assistants. It provides modular components for audio recording, voice activity detection (VAD), speech-to-text (STT), and LLM interactions with support for multiple providers.

## Development Commands

This project uses `uv` for dependency management:

```bash
# Install dependencies
uv sync

# Run the example voice recorder/transcriber
uv run python main.py

# Run tests
uv run pytest tests/ -v

# Add a new dependency
uv add <package>
```

## Architecture

### Module Organization

The `voicevibe` package follows a port-adapter pattern with clear separation of interfaces and implementations:

```
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

### Key Design Patterns

**Port-Adapter Pattern**: Each major component defines a Protocol (port) in `*_port.py` files with concrete implementations. Example: `AudioRecorderPort` defines the interface, `AudioRecorder` implements it.

**Async Streaming**: Audio and LLM interactions use async generators for real-time streaming:
- `AudioRecorder.audio_stream()` yields audio chunks
- `MistralTranscribeClient.transcribe()` yields transcription events
- `SimpleVAD.detect()` yields VAD events
- LLM backends yield `LLMChunk` objects

**Recording Modes**: `AudioRecorder` supports two modes:
- `BUFFER`: Records to internal buffer, returns WAV bytes on stop
- `STREAM`: Yields chunks via async generator for real-time processing

**Backend Factory**: LLM backends are registered in `BACKEND_FACTORY` dict (in `llm/backend/factory.py`) mapping `Backend` enum to backend classes. Backends are instantiated with a `provider` parameter.

**Configuration**: All service configurations use Pydantic models in `config.py`:
- `ProviderConfig` / `ModelConfig` for LLM providers
- `TranscribeProviderConfig` / `TranscribeModelConfig` for transcription

### Audio Pipeline

The typical voice interaction flow:

1. **Recording**: `AudioRecorder` captures audio from microphone
   - Uses `sounddevice` with callback-based streaming
   - Provides peak level monitoring for VAD (voice activity detection)
   - Supports max duration timeouts

2. **VAD Processing**: `SimpleVAD` detects speech activity in real-time
   - Energy-based threshold detection using audio peak levels
   - Emits `VADStateChange` on speech/silence transitions
   - Emits `VADSilenceTimeout` when silence exceeds configured duration

3. **Transcription**: `MistralTranscribeClient` streams audio to Mistral's realtime API
   - WebSocket-based streaming
   - Emits events: `TranscribeSessionCreated`, `TranscribeTextDelta`, `TranscribeDone`

4. **LLM Processing**: Backend adapters handle chat completions
   - `GenericBackend` for OpenAI-compatible APIs (requires `provider` in constructor)
   - `MistralBackend` for Mistral-specific features
   - Support for tool calling, reasoning content, streaming

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
- Designed for short-lived sessions where all consumers process at similar speeds

### Key Types

- `LLMMessage` (in `types.py`): Unified message format supporting content, reasoning_content, tool_calls
- `LLMChunk`: Streaming chunk containing message delta and usage info
- `MessageList`: Observable list with silent context manager for batch updates
- `AgentStats`: Tracks token usage, costs, and performance metrics
- `Backend`: Enum for backend types (`MISTRAL`, `GENERIC`)
- `RecordingMode`: `BUFFER` or `STREAM` for audio recording
- `VoiceState`: Enum for VAD states (`SILENCE`, `SPEAKING`)
- `VADState`, `VADStateChange`, `VADSilenceTimeout`: VAD event types

### Environment Variables

API keys are configured via environment variables referenced in config:
- `MISTRAL_API_KEY` for Mistral services
- Configurable via `api_key_env_var` field in provider configs

## Dependencies

Key external libraries:
- `mistralai` - Mistral AI SDK including realtime transcription
- `sounddevice` - PortAudio bindings for audio I/O
- `httpx` - HTTP client for API calls
- `pydantic` / `pydantic-settings` - Configuration and validation
- `gradio` - UI framework (dependency present)

## Entry Points

- `main.py` - Example CLI demonstrating real-time voice recording with VAD and transcription

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues. See `docs/agents/issue-tracker.md`.

### Triage labels

Using default labels: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: CONTEXT.md and docs/adr/ at repo root. See `docs/agents/domain.md`.
