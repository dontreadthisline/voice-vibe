"""Benchmark runner - main entry point."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from benchmark.config import ASRConfig, BenchmarkConfig, LLMConfig, VADConfig
from benchmark.dataset import AudioDataset, read_wav_as_chunks
from benchmark.metrics import (
    CombinationStats,
    LatencyStats,
    PipelineMetrics,
    calculate_vad_metrics,
    calculate_wer,
)
from benchmark.pipeline import PipelineRunner
from benchmark.report import ReportGenerator

if TYPE_CHECKING:
    from voicevibe.llm.backend.base import APIAdapter
    from voicevibe.transcribe.transcribe_client_port import TranscribeClientPort
    from voicevibe.vad.vad_port import VADPort


class BenchmarkRunner:
    """Runs all VAD×ASR×LLM combinations and generates reports."""

    def __init__(self, config: BenchmarkConfig):
        """Initialize runner with configuration.

        Args:
            config: Benchmark configuration.
        """
        self._config = config
        self._report = ReportGenerator()
        self._dataset: AudioDataset | None = None

    async def run_all(self) -> list[CombinationStats]:
        """Run all combinations and return aggregated statistics.

        Returns:
            List of CombinationStats, one per combination.
        """
        # Load dataset
        self._dataset = AudioDataset(self._config.audio_dir)
        if not self._dataset:
            print(f"No audio samples found in {self._config.audio_dir}")
            return []

        results: list[CombinationStats] = []

        # Run each combination
        for vad_config in self._config.vads:
            for asr_config in self._config.asrs:
                for llm_config in self._config.llms:
                    stats = await self._run_combination(
                        vad_config, asr_config, llm_config
                    )
                    results.append(stats)

        return results

    async def _run_combination(
        self,
        vad_config: VADConfig,
        asr_config: ASRConfig,
        llm_config: LLMConfig,
    ) -> CombinationStats:
        """Run a single combination across all samples.

        Args:
            vad_config: VAD configuration.
            asr_config: ASR configuration.
            llm_config: LLM configuration.

        Returns:
            Aggregated statistics for this combination.
        """
        combination_name = f"{vad_config.name}+{asr_config.name}+{llm_config.name}"
        print(f"Running: {combination_name}")

        all_metrics: list[PipelineMetrics] = []

        for sample in self._dataset:
            for _ in range(self._config.runs_per_sample):
                # Create fresh instances for each run
                vad = self._create_vad(vad_config)
                asr = self._create_asr(asr_config)
                llm = self._create_llm(llm_config)

                # Load audio
                audio_data, sample_rate = read_wav_as_chunks(sample.file_path)

                # Create runner and execute
                runner = PipelineRunner(
                    vad=vad,
                    asr=asr,
                    llm=llm,
                    ground_truth_text=sample.ground_truth_text,
                    ground_truth_segments=sample.vad_segments,
                )

                metrics = await runner.run(audio_data, sample_rate)
                all_metrics.append(metrics)

        # Aggregate metrics
        return self._aggregate_metrics(combination_name, all_metrics)

    def _create_vad(self, config: VADConfig) -> VADPort:
        """Create VAD instance from configuration."""
        return config.cls(**config.params)

    def _create_asr(self, config: ASRConfig) -> TranscribeClientPort:
        """Create ASR instance from configuration."""
        return config.cls(**config.params)

    def _create_llm(self, config: LLMConfig) -> APIAdapter | None:
        """Create LLM instance from configuration."""
        # TODO: Implement LLM creation from factory
        return None

    def _aggregate_metrics(
        self,
        combination_name: str,
        all_metrics: list[PipelineMetrics],
    ) -> CombinationStats:
        """Aggregate metrics from multiple runs into statistics."""
        vad_durations = [m.vad_duration_ms for m in all_metrics]
        asr_durations = [m.asr_duration_ms for m in all_metrics]
        llm_durations = [m.llm_duration_ms for m in all_metrics]
        total_durations = [m.total_duration_ms for m in all_metrics]

        # Calculate WER for each run
        wers = []
        for m in all_metrics:
            if m.vad_ground_truth_segments:
                wer = calculate_wer(m.vad_ground_truth_segments[0][0] if m.vad_ground_truth_segments else "", m.transcription_text)
                wers.append(wer)

        # Calculate VAD precision/recall
        precisions = []
        recalls = []
        for m in all_metrics:
            p, r = calculate_vad_metrics(
                m.vad_detected_segments,
                m.vad_ground_truth_segments,
            )
            precisions.append(p)
            recalls.append(r)

        return CombinationStats(
            combination_name=combination_name,
            vad=LatencyStats.from_durations(vad_durations),
            asr=LatencyStats.from_durations(asr_durations),
            llm=LatencyStats.from_durations(llm_durations),
            total=LatencyStats.from_durations(total_durations),
            wer=sum(wers) / len(wers) if wers else 0.0,
            vad_precision=sum(precisions) / len(precisions) if precisions else 0.0,
            vad_recall=sum(recalls) / len(recalls) if recalls else 0.0,
        )

    def generate_report(self, results: list[CombinationStats]) -> str:
        """Generate markdown report from results."""
        sample_count = len(self._dataset) if self._dataset else 0
        return self._report.generate(
            results,
            sample_count=sample_count,
            runs_per_sample=self._config.runs_per_sample,
        )

    def save_report(self, report: str, output_path: Path | None = None) -> None:
        """Save report to file.

        Args:
            report: Markdown report content.
            output_path: Output file path (default: output_dir/benchmark_results.md).
        """
        if output_path is None:
            self._config.output_dir.mkdir(parents=True, exist_ok=True)
            output_path = self._config.output_dir / "benchmark_results.md"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report saved to: {output_path}")
