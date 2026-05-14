"""Markdown report generation for benchmark results."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from benchmark.metrics import CombinationStats


class ReportGenerator:
    """Generates markdown reports from benchmark results."""

    def generate(
        self,
        results: list[CombinationStats],
        sample_count: int,
        runs_per_sample: int,
    ) -> str:
        """Generate full markdown report.

        Args:
            results: List of CombinationStats for each combination.
            sample_count: Number of audio samples tested.
            runs_per_sample: Number of runs per sample.

        Returns:
            Markdown formatted report string.
        """
        lines = [
            "# Benchmark Results",
            "",
            f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Samples**: {sample_count}",
            f"**Runs per sample**: {runs_per_sample}",
            "",
            "## Latency Summary (ms)",
            "",
            self._latency_table(results),
            "",
            "## Accuracy Summary",
            "",
            self._accuracy_table(results),
        ]
        return "\n".join(lines)

    def _latency_table(self, results: list[CombinationStats]) -> str:
        """Generate latency comparison table."""
        header = "| Combination | VAD Mean | VAD P99 | ASR Mean | ASR P99 | LLM Mean | LLM P99 | Total Mean | Total P99 |"
        separator = "|-------------|----------|---------|----------|---------|----------|---------|------------|-----------|"

        rows = []
        for r in results:
            row = (
                f"| {r.combination_name} "
                f"| {r.vad.mean:.1f} "
                f"| {r.vad.p99:.1f} "
                f"| {r.asr.mean:.1f} "
                f"| {r.asr.p99:.1f} "
                f"| {r.llm.mean:.1f} "
                f"| {r.llm.p99:.1f} "
                f"| {r.total.mean:.1f} "
                f"| {r.total.p99:.1f} |"
            )
            rows.append(row)

        return "\n".join([header, separator] + rows)

    def _accuracy_table(self, results: list[CombinationStats]) -> str:
        """Generate accuracy comparison table."""
        header = "| Combination | WER (%) | VAD Precision | VAD Recall |"
        separator = "|-------------|---------|---------------|------------|"

        rows = []
        for r in results:
            row = (
                f"| {r.combination_name} "
                f"| {r.wer * 100:.1f} "
                f"| {r.vad_precision:.2f} "
                f"| {r.vad_recall:.2f} |"
            )
            rows.append(row)

        return "\n".join([header, separator] + rows)
