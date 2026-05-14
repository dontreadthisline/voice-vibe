## 1. 模块结构

- [x] 1.1 创建 benchmark/ 目录结构
- [x] 1.2 创建 benchmark/__init__.py 包入口
- [x] 1.3 修改 pyproject.toml 注册 benchmark 包

## 2. 配置模块

- [x] 2.1 实现 VADConfig、ASRConfig、LLMConfig 数据类
- [x] 2.2 实现 BenchmarkConfig 主配置类
- [x] 2.3 实现 get_default_config() 获取默认配置

## 3. 数据集模块

- [x] 3.1 实现 AudioSample 数据类
- [x] 3.2 实现 AudioDataset 类加载 WAV 和 JSON 文件
- [x] 3.3 实现 read_wav_as_chunks() 读取音频数据

## 4. 指标模块

- [x] 4.1 实现 LatencyStats 统计量计算（mean/median/min/max/std/p99）
- [x] 4.2 实现 PipelineMetrics 单次运行指标
- [x] 4.3 实现 CombinationStats 组合汇总统计
- [x] 4.4 实现 calculate_wer() 词错误率计算
- [x] 4.5 实现 calculate_vad_metrics() VAD 精确率/召回率计算

## 5. 流水线模块

- [x] 5.1 实现 PipelineRunner 类
- [x] 5.2 实现并行执行 VAD 和 ASR（使用 AudioBroadcaster）
- [x] 5.3 实现各阶段时间记录

## 6. 报告模块

- [x] 6.1 实现 ReportGenerator 类
- [x] 6.2 实现 _latency_table() 生成延迟表格
- [x] 6.3 实现 _accuracy_table() 生成准确率表格
- [x] 6.4 实现 generate() 生成完整 markdown 报告

## 7. 运行器和 CLI

- [x] 7.1 实现 BenchmarkRunner 主入口类
- [x] 7.2 实现 run_all() 运行所有组合
- [x] 7.3 实现 _aggregate_metrics() 汇总统计
- [x] 7.4 实现 __main__.py CLI 入口
- [x] 7.5 添加 --audio-dir、--output、--runs 命令行参数

## 8. 测试

- [x] 8.1 创建 tests/test_benchmark.py
- [x] 8.2 编写 LatencyStats 单元测试
- [x] 8.3 编写 calculate_wer 单元测试
- [x] 8.4 编写 calculate_vad_metrics 单元测试
- [x] 8.5 运行测试验证通过
