## Context

VoiceVibe 是一个语音 AI 助手框架，包含 VAD（语音活动检测）、ASR（语音转文字）、LLM（大语言模型）三个核心模块。当前缺少系统化的 benchmark 工具来评估不同模块组合的性能。

现有架构：
- `VADPort` / `TranscribeClientPort` / `APIAdapter` 协议定义接口
- `AudioBroadcaster` 支持 VAD+ASR 并行处理
- `VoiceSession` 集成完整流水线

约束：
- 使用预录音频文件进行可重复测试
- 需要支持多种统计量（mean, median, std, p99）
- 输出格式为 markdown 表格

## Goals / Non-Goals

**Goals:**
- 创建可扩展的 benchmark 框架，支持任意 VAD/ASR/LLM 组合
- 测量端到端延迟和各阶段延迟
- 计算多样本统计量（mean, median, min, max, std, p99）
- 支持 WER（词错误率）和 VAD 精确率/召回率评估
- 输出简洁的 markdown 汇总报告

**Non-Goals:**
- 不支持实时麦克风输入测试
- 不生成可视化图表
- 不支持分布式 benchmark
- 不包含性能回归检测

## Decisions

### 1. Pipeline-Based 架构
选择流水线式 benchmark 而非独立模块测试。

**理由**: 
- 真实反映生产环境的端到端延迟
- 可以测试 VAD+ASR 并行执行的收益
- 更接近用户实际体验

**备选方案**: 独立模块 benchmark - 更简单但无法测量集成开销

### 2. 预录音频文件作为输入
使用 WAV 文件而非实时麦克风。

**理由**:
- 可重复测试
- 方便版本控制
- 易于分享测试数据集

### 3. 统计量在 metrics.py 中独立计算
将统计计算与数据收集分离。

**理由**:
- 单一职责原则
- 便于单元测试
- 支持后续添加新统计量

## Risks / Trade-offs

**测试音频数据集准备成本高** → 提供示例 JSON 格式，降低门槛

**LLM 调用成本** → 支持 skip LLM 模式，或使用 mock

**WebSocket ASR 延迟不稳定** → 增加运行次数取平均
