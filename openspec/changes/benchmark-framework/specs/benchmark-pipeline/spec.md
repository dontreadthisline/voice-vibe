## ADDED Requirements

### Requirement: Benchmark 配置
系统 SHALL 支持 VADConfig、ASRConfig、LLMConfig 三种配置类型，每种配置包含名称、实现类和参数字典。

#### Scenario: 创建默认配置
- **WHEN** 调用 `get_default_config()`
- **THEN** 返回包含 SimpleVAD、MistralASR、MistralLLM 的 BenchmarkConfig

### Requirement: 音频数据集加载
系统 SHALL 从指定目录加载 WAV 文件及其对应的 JSON 元数据文件，JSON 包含 ground_truth_text 和 vad_segments 字段。

#### Scenario: 加载测试音频
- **WHEN** AudioDataset 初始化时指定包含 sample1.wav 和 sample1.json 的目录
- **THEN** samples 列表包含一个 AudioSample，其 ground_truth_text 为 JSON 中的值

#### Scenario: 目录不存在
- **WHEN** 指定的音频目录不存在
- **THEN** samples 列表为空，不抛出异常

### Requirement: 延迟统计量计算
系统 SHALL 从延迟数据列表计算 mean、median、min、max、std、p99 六种统计量。

#### Scenario: 多样本统计
- **WHEN** 传入延迟列表 [10.0, 20.0, 30.0, 40.0, 50.0]
- **THEN** mean = 30.0, median = 30.0, min = 10.0, max = 50.0, std > 0, p99 = 50.0

#### Scenario: 空数据
- **WHEN** 传入空列表
- **THEN** 所有统计量返回 0.0

### Requirement: 流水线执行
系统 SHALL 并行执行 VAD 和 ASR 模块，记录各阶段的开始和结束时间，并收集转录结果。

#### Scenario: 运行流水线
- **WHEN** PipelineRunner.run() 被调用并传入音频数据
- **THEN** 返回 PipelineMetrics 包含 vad_duration_ms、asr_duration_ms、total_duration_ms 和 transcription_text

### Requirement: 报告生成
系统 SHALL 生成 markdown 格式的汇总报告，包含延迟表格和准确率表格，每个组合一行，使用紧凑格式。

#### Scenario: 生成报告
- **WHEN** ReportGenerator.generate() 被调用并传入 CombinationStats 列表
- **THEN** 输出包含 "## Latency Summary (ms)" 和 "## Accuracy Summary" 两个表格

### Requirement: CLI 入口
系统 SHALL 提供 `python -m benchmark` 命令行入口，支持 --audio-dir、--output、--runs 参数。

#### Scenario: 运行 benchmark
- **WHEN** 执行 `uv run python -m benchmark --audio-dir benchmark/data --runs 3`
- **THEN** 运行所有配置的组合，每个样本运行 3 次，输出 markdown 报告

### Requirement: WER 计算
系统 SHALL 计算 Word Error Rate（词错误率）来评估 ASR 准确性。

#### Scenario: 相同文本
- **WHEN** reference 和 hypothesis 相同
- **THEN** WER = 0.0

#### Scenario: 有错误
- **WHEN** reference = "hello world"，hypothesis = "hello there"
- **THEN** WER > 0
