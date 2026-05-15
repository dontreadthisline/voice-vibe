# PRD: Frontend Audio File Test Mode

## Introduction

为现有的语音上报功能添加测试模式,将麦克风输入替换为本地预设音频文件流。这样可以在不依赖用户手动录音的情况下,自动化测试 VAD + ASR 管道的完整流程。测试模式复用现有的 UI 交互和后端管道,仅改变音频源。

## Goals

- 支持从预设音频文件流式读取数据,替代麦克风采集
- 实时显示转录文本,验证 VAD + ASR 集成正常工作
- 提供开发者可自测的入口,无需人工介入
- 保持现有麦克风模式不变,测试模式作为可切换选项

## User Stories

### US-001: Add file-based audio stream source
**Description:** 作为开发者,我需要一个从预设音频文件流式读取的异步生成器,以便替代麦克风输入测试 ASR 管道。

**Acceptance Criteria:**
- [ ] 在 `voicevibe/frontend/` 下创建 `audio_file_streamer.py`
- [ ] 使用 pydub 加载 MP3 并转换为 PCM int16 格式 (16kHz, mono)
- [ ] 按固定 chunk 大小 (4096 samples) 分块 yield,模拟实时音频流
- [ ] 添加可配置的 chunk 延迟模拟真实语速
- [ ] Typecheck passes

### US-002: Add test mode toggle to voice pipeline
**Description:** 作为开发者,我需要在 `_run_voice_pipeline` 中支持两种模式(麦克风/文件),以便灵活切换测试。

**Acceptance Criteria:**
- [ ] 修改 `_run_voice_pipeline` 函数签名,添加 `audio_source` 参数 ("mic" | "file")
- [ ] 当 `audio_source="file"` 时,使用 `AudioFileStreamer` 替代 `AudioRecorder`
- [ ] 文件模式下跳过 AudioRecorder 启动/停止逻辑
- [ ] 保持 broadcaster、VAD、ASR 的处理逻辑不变
- [ ] Typecheck passes

### US-003: Add hidden test trigger to frontend
**Description:** 作为开发者,我需要一个隐藏的测试入口来触发文件模式,以便快速验证管道。

**Acceptance Criteria:**
- [ ] 在 voice.js 中添加双击 FAB 触发测试模式 (500ms 内两次点击)
- [ ] 测试按钮发送 `vv_start_voice_test` 消息
- [ ] 显示测试模式指示器 "测试模式"
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-004: Wire test mode trigger to backend
**Description:** 作为开发者,我需要后端响应测试模式触发,以便启动文件流管道。

**Acceptance Criteria:**
- [ ] 添加 `vv_start_voice_test` 事件处理器
- [ ] 调用 `_run_voice_pipeline(session, audio_source="file")`
- [ ] 使用第一个预设测试文件 (common_voice_en_42696072.mp3)
- [ ] Typecheck passes

### US-005: Verify end-to-end file test flow
**Description:** 作为开发者,我需要验证文件测试模式完整运行,确保 VAD + ASR 正常协作。

**Acceptance Criteria:**
- [ ] 双击 FAB 触发测试模式
- [ ] 语音面板打开并显示 "测试模式" 指示
- [ ] 转录文本实时更新到面板
- [ ] VAD 正常检测语音/静音
- [ ] 静音超时后面板自动关闭或显示完成状态
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

## Functional Requirements

- FR-1: `AudioFileStreamer` 从 `/Users/didi/Downloads/audio/en/clips/common_voice_en_42696072.mp3` 读取
- FR-2: 音频转换使用 pydub,输出 PCM int16 (16kHz, mono)
- FR-3: 分块大小 4096 samples (8192 bytes),模拟实时流
- FR-4: `_run_voice_pipeline` 支持 `audio_source` 参数 ("mic" 默认, "file" 测试)
- FR-5: 前端通过双击 FAB (500ms 内两次点击) 触发测试模式
- FR-6: 测试模式发送 `vv_start_voice_test` 事件,后端调用文件流管道
- FR-7: 测试模式显示 "测试模式" 文字指示
- FR-8: 复用现有 VAD、broadcaster、ASR 逻辑,仅替换音频源

## Non-Goals

- 不支持用户上传自定义音频文件
- 不显示音频波形可视化
- 不显示 VAD 状态指示 (SPEAKING/SILENCE)
- 不修改现有的麦克风模式逻辑
- 不在生产环境暴露测试入口

## Technical Considerations

### File Stream Implementation
```python
# voicevibe/frontend/audio_file_streamer.py
class AudioFileStreamer:
    def __init__(self, filepath: Path, chunk_delay: float = 0.1):
        self.filepath = filepath
        self.chunk_delay = chunk_delay
    
    async def audio_stream(self) -> AsyncIterator[bytes]:
        """Yield audio chunks from file, simulating real-time stream."""
        audio_data = self._load_and_convert()
        chunk_size = 4096 * 2  # samples * bytes
        
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i + chunk_size]
            await asyncio.sleep(self.chunk_delay)
            yield chunk
```

### Pipeline Mode Selection
```python
# voicevibe/frontend/app.py
async def _run_voice_pipeline(session, audio_source: str = "mic"):
    broadcaster = AudioBroadcaster()
    
    if audio_source == "file":
        # Use file streamer instead of recorder
        streamer = AudioFileStreamer(TEST_FILE)
        audio_stream = streamer.audio_stream()
    else:
        recorder = AudioRecorder()
        recorder.start(mode=RecordingMode.STREAM, ...)
        audio_stream = recorder.audio_stream()

    # Rest of pipeline unchanged
    vad_stream = broadcaster.subscribe()
    asr_stream = broadcaster.subscribe()
    broadcast_task = asyncio.create_task(broadcaster.broadcast(audio_stream))
    ...
```

### Frontend Test Trigger
```javascript
// voice.js - Double-click FAB detection
var lastClick = 0;
document.addEventListener("click", function(e) {
    var fab = e.target.closest(".vv-fab");
    if (!fab) return;
    
    var now = Date.now();
    if (now - lastClick < 500) {
        // Double-click: trigger test mode
        e.preventDefault();
        e.stopPropagation();
        if (window.Shiny && window.Shiny.setInputValue) {
            window.Shiny.setInputValue("vv_start_voice_test", { t: now });
        }
    }
    lastClick = now;
});
```

### Default Test File
- Path: `/Users/didi/Downloads/audio/en/clips/common_voice_en_42696072.mp3` (from conftest.py AUDIO_TEST_FILES)
- Size: 44 KB, short clip suitable for quick testing

## Success Metrics

- 测试模式可在 3 秒内启动并显示转录文本
- 转录结果与直接调用 ASR API 一致
- 无需人工介入即可完成完整测试流程
- 不影响现有麦克风模式的正常功能

## Open Questions

- 是否需要在测试模式中添加模拟延迟以匹配真实语速? (当前设计有 0.1s chunk delay)
- 是否需要支持多个预设文件的切换测试?
- 测试入口是否需要密码/确认框保护?
