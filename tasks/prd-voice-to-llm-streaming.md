# PRD: Voice-to-LLM Streaming Response

## Introduction

Add LLM-powered conversational responses to the voice reporting page. When a user finishes speaking and transcription completes, the recognized text is sent to an LLM (Mistral) for a response. The response streams in real-time on the voice panel, displaying both the user's question and the AI's answer in a Q&A format. After the response completes, the page remains static, preserving the conversation for the user to read.

## Goals

- Send transcribed text to LLM when voice transcription completes
- Stream LLM response in real-time on the voice panel
- Display Q&A format: user's question above, AI response below
- Preserve conversation content after completion
- Support optional system prompt loaded from file (for future extensibility)

## User Stories

### US-001: Add LLM backend integration to voice pipeline
**Description:** As a developer, I need to integrate the existing LLM backend (Mistral) into the voice pipeline so that transcribed text can be processed.

**Acceptance Criteria:**
- [ ] Import MistralBackend from `voicevibe.llm.backend.mistral`
- [ ] Create LLM provider/model configs using existing config patterns
- [ ] Add function to send transcript to LLM with streaming
- [ ] Use `complete_streaming` method from MistralBackend
- [ ] Handle async generator for streaming chunks
- [ ] Typecheck passes

### US-002: Add LLM configuration with system prompt file support
**Description:** As a developer, I need configurable LLM settings with optional system prompt file loading for future customization.

**Acceptance Criteria:**
- [ ] Add LLM-related reactive values (model name, system prompt path)
- [ ] Create helper function to load system prompt from file (if path provided)
- [ ] Default to no system prompt if file not specified
- [ ] Configuration uses existing `ProviderConfig` and `ModelConfig` patterns
- [ ] Typecheck passes

### US-003: Integrate LLM streaming after transcription completion
**Description:** As a user, I want my transcribed question to be answered by an AI assistant automatically after I finish speaking.

**Acceptance Criteria:**
- [ ] Modify `_run_voice_pipeline` to call LLM after transcription done
- [ ] Send `vv_llm_start` message to frontend when LLM begins
- [ ] Stream LLM chunks to frontend via `vv_llm_chunk` messages
- [ ] Send `vv_llm_done` message when streaming completes
- [ ] Handle errors gracefully with user-friendly messages
- [ ] Typecheck passes

### US-004: Update voice panel UI for Q&A display
**Description:** As a user, I want to see my question and the AI's response in a clear Q&A format.

**Acceptance Criteria:**
- [ ] Add Q&A container HTML to voice panel (below waveform area)
- [ ] Create question section with label "问题:"
- [ ] Create answer section with label "回答:"
- [ ] Answer section supports real-time text updates
- [ ] Q&A sections hidden initially, shown after transcription done
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-005: Handle LLM streaming messages in frontend
**Description:** As a user, I want to see the AI response appear word-by-word in real-time.

**Acceptance Criteria:**
- [ ] Add Shiny message handler for `vv_llm_start`
- [ ] Add Shiny message handler for `vv_llm_chunk`
- [ ] Add Shiny message handler for `vv_llm_done`
- [ ] Update answer text incrementally as chunks arrive
- [ ] Smooth visual updates without flickering
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-006: Preserve Q&A content after completion
**Description:** As a user, I want to read my question and the AI's answer after the interaction ends.

**Acceptance Criteria:**
- [ ] Q&A content remains visible after LLM done
- [ ] Waveform remains hidden (from US-005 in previous PRD)
- [ ] Close button still functional to exit voice panel
- [ ] Q&A content cleared when opening new voice session
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

## Functional Requirements

- FR-1: Use Mistral Small model (`mistral-small-latest`) for LLM responses
- FR-2: Call LLM with user's transcribed text as the prompt
- FR-3: Stream response chunks to frontend via WebSocket (Shiny custom messages)
- FR-4: Display question text (from transcription) in dedicated Q area
- FR-5: Display answer text (from LLM) in dedicated A area with streaming
- FR-6: Support optional system prompt file path configuration
- FR-7: Handle LLM errors gracefully without crashing the voice panel
- FR-8: Clear all content when user starts a new voice session

## Non-Goals

- No multi-turn conversation history (each session is single-turn)
- No automatic categorization or intent detection (future feature)
- No TTS (text-to-speech) for reading responses aloud
- No copy/share functionality for Q&A content
- No persistence of Q&A content to database

## Technical Considerations

### Backend Changes (app.py)
- Import `MistralBackend`, `ProviderConfig`, `ModelConfig` from existing modules
- Create LLM client instance in `_run_voice_pipeline`
- After transcription done, call LLM with streaming
- Use `complete_streaming` method for real-time chunks
- Send chunks via `_push(session, "vv_llm_chunk", text=chunk_text)`

### Frontend Changes (voice.js)
- Add Q&A HTML structure to voice panel body
- Add Shiny message handlers for `vv_llm_start`, `vv_llm_chunk`, `vv_llm_done`
- Update answer text element incrementally
- Handle status transitions: listening → speaking → done → llm_streaming → llm_done

### Message Flow
```
User speaks → VAD detects speech → Transcription runs
VAD silence timeout → Transcription done → vv_status="done"
Transcription text → LLM streaming → vv_llm_start
LLM chunks → vv_llm_chunk (multiple) → Frontend updates text
LLM complete → vv_llm_done → Panel stays open with Q&A visible
```

### Reuse Existing Code
- `MistralBackend.complete_streaming()` from `voicevibe/llm/backend/mistral.py`
- `ProviderConfig` and `ModelConfig` from `voicevibe/config.py`
- `_push()` helper for sending WebSocket messages
- Shiny custom message handler pattern from existing `vv_transcript`, `vv_status`

## Success Metrics

- LLM response begins within 2 seconds of transcription completion
- Streaming updates visible in real-time (not batched)
- User can read full Q&A after closing and reopening voice panel
- No visible lag or stuttering during streaming

## Open Questions

- Should we add a loading indicator while waiting for first LLM chunk?
- Should the answer area have a maximum height with scrolling?
