## Why

VoiceVibe 需要一个 benchmark 框架来评估语音处理流水线（VAD + ASR + LLM）的性能和效果。当前缺少系统化的工具来对比不同模块组合的延迟和准确率，无法数据驱动地选择最佳方案。

## What Changes

- 新增 `benchmark/` 模块，提供完整的 benchmark 框架
- 支持多种 VAD/ASR/LLM 实现的组合测试
- 测量端到端延迟、各阶段延迟、WER、VAD 精确率/召回率
- 输出 markdown 格式的汇总报告

## Capabilities

### New Capabilities

- `benchmark-pipeline`: 评估 VAD+ASR+LLM 流水线性能的 benchmark 框架，支持多样本、多组合、多运行次数的测试，输出延迟统计（mean/median/std/p99）和准确率指标

### Modified Capabilities

<!-- 无现有 capability 需要修改 -->

## Impact

- 新增 `benchmark/` 目录及 8 个模块文件
- 新增 `tests/test_benchmark.py` 单元测试
- 修改 `pyproject.toml` 注册 benchmark 包
- 不影响现有 voicevibe 功能
