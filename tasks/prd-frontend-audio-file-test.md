# PRD: Frontend Audio File Test Mode

## Introduction

Add a test mode to the frontend that uses a pre-recorded audio file instead of microphone input. This allows testing the VAD+ASR pipeline without needing actual microphone hardware, using audio files from the test dataset.

## Goals

- Replace microphone input with audio file streaming in test mode
- Use a single fixed audio file from `/Users/didi/Downloads/audio/en/clips`
- Display real-time transcription on the voice panel
- Toggle between test mode and normal microphone mode

## User Stories

### US-001: Create audio file streamer for frontend
**Description:** As a developer, I need a utility to stream audio file content as if it were from a microphone.

**Acceptance Criteria:**
- [ ] Create `voicevibe/frontend/audio_file_streamer.py`
- [ ] Implement `AudioFileStreamer` class that yields audio chunks from MP3 file
- [ ] Convert MP3 to PCM int16 at 16kHz (reuse conftest.py patterns)
- [ ] Support async iteration compatible with AudioBroadcaster
- [ ] Simulate real-time streaming with configurable chunk delay
- [ ] Typecheck passes

### US-002: Add test mode configuration to frontend app
**Description:** As a developer, I need a way to enable test mode in the frontend app.

**Acceptance Criteria:**
- [ ] Add `TEST_MODE` environment variable check in `app.py`
- [ ] Add `TEST_AUDIO_FILE` environment variable for specifying test file path
- [ ] Default test file: `/Users/didi/Downloads/audio/en/clips/common_voice_en_43201672.mp3`
- [ ] When test mode enabled, use AudioFileStreamer instead of AudioRecorder
- [ ] Log test mode status on startup
- [ ] Typecheck passes

### US-003: Integrate AudioFileStreamer into voice pipeline
**Description:** As a developer, I need the voice pipeline to use the file streamer in test mode.

**Acceptance Criteria:**
- [ ] Modify `_run_voice_pipeline()` to check test mode
- [ ] In test mode, create AudioFileStreamer instead of AudioRecorder
- [ ] AudioFileStreamer feeds into AudioBroadcaster same as AudioRecorder
- [ ] VAD and ASR process the file stream normally
- [ ] Test mode skips silence timeout check (file has fixed duration)
- [ ] Typecheck passes

### US-004: Add test mode indicator to UI
**Description:** As a user, I want to see when test mode is active.

**Acceptance Criteria:**
- [ ] Add `vv_test_mode` custom message handler in voice.js
- [ ] Show "测试模式" badge in voice panel when test mode active
- [ ] Badge shows test file name
- [ ] Verify in browser using dev-browser skill

### US-005: Create end-to-end test for frontend audio file mode
**Description:** As a developer, I need to verify the frontend test mode works correctly.

**Acceptance Criteria:**
- [ ] Create `tests/test_frontend_audio_file.py`
- [ ] Test AudioFileStreamer yields correct audio chunks
- [ ] Test AudioFileStreamer + AudioBroadcaster integration
- [ ] Test VAD + ASR process file stream correctly
- [ ] Test skips if MISTRAL_API_KEY not set
- [ ] Typecheck passes
- [ ] Tests pass

## Functional Requirements

- FR-1: Test mode is controlled by `VOICEVIBE_TEST_MODE=true` environment variable
- FR-2: Test audio file path is set via `VOICEVIBE_TEST_AUDIO_FILE` or defaults to first test file
- FR-3: AudioFileStreamer must yield chunks at realistic rate (not all at once)
- FR-4: In test mode, silence timeout should not auto-close the panel
- FR-5: Transcription text must display in real-time in the voice panel
- FR-6: Test mode must work without microphone hardware

## Non-Goals

- No UI for selecting test files (single fixed file)
- No recording of new audio in test mode
- No performance benchmarking
- No multi-file testing

## Technical Considerations

### Audio File Processing
- Reuse patterns from `tests/conftest.py` for MP3 to PCM conversion
- Use `pydub` for audio loading
- Chunk size: 8192 bytes (4096 samples * 2 bytes)
- Simulate real-time by adding small delay between chunks (e.g., 0.1s)

### Integration Points
- `AudioFileStreamer` replaces `AudioRecorder.audio_stream()`
- Same `AudioBroadcaster` → VAD + ASR pipeline
- Same frontend voice panel for display

### Configuration
```bash
# Enable test mode
export VOICEVIBE_TEST_MODE=true

# Optional: specify test file
export VOICEVIBE_TEST_AUDIO_FILE=/Users/didi/Downloads/audio/en/clips/common_voice_en_43201672.mp3
```

### Default Test File
- Path: `/Users/didi/Downloads/audio/en/clips/common_voice_en_43201672.mp3`
- This is one of the smaller files (~14 KB) for quick testing

## Success Metrics

- Test mode works without microphone
- Transcription displays in real-time
- All tests pass
- Can run demo without physical audio hardware

## Open Questions

- Should test mode have a configurable streaming speed (faster than real-time)?
- Should there be a UI toggle instead of environment variable?