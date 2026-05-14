"""Metrics collection and statistics calculation."""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Literal


@dataclass
class LatencyStats:
    """Statistics for latency measurements across multiple runs."""
    mean: float
    median: float
    min: float
    max: float
    std: float
    p99: float
    samples: int

    @classmethod
    def from_durations(cls, durations: list[float]) -> LatencyStats:
        """Calculate statistics from a list of duration measurements in milliseconds."""
        if not durations:
            return cls(mean=0.0, median=0.0, min=0.0, max=0.0, std=0.0, p99=0.0, samples=0)

        n = len(durations)
        sorted_durations = sorted(durations)

        # Calculate p99 (99th percentile)
        p99_index = int(n * 0.99)
        p99_index = min(p99_index, n - 1)  # Clamp to valid index
        p99 = sorted_durations[p99_index]

        # Calculate std, handle single sample case
        std = statistics.stdev(durations) if n > 1 else 0.0

        return cls(
            mean=statistics.mean(durations),
            median=statistics.median(durations),
            min=min(durations),
            max=max(durations),
            std=std,
            p99=p99,
            samples=n,
        )


@dataclass
class PipelineMetrics:
    """Metrics from a single pipeline run."""
    vad_duration_ms: float
    asr_duration_ms: float
    llm_duration_ms: float
    total_duration_ms: float
    transcription_text: str
    llm_response: str
    # VAD accuracy
    vad_detected_segments: list[tuple[float, float]]
    vad_ground_truth_segments: list[tuple[float, float]]


@dataclass
class CombinationStats:
    """Aggregated statistics for a VAD+ASR+LLM combination."""
    combination_name: str
    vad: LatencyStats
    asr: LatencyStats
    llm: LatencyStats
    total: LatencyStats
    wer: float  # Word Error Rate (average)
    vad_precision: float
    vad_recall: float


def calculate_wer(reference: str, hypothesis: str) -> float:
    """Calculate Word Error Rate between reference and hypothesis.

    WER = (S + D + I) / N
    where S=substitutions, D=deletions, I=insertions, N=reference words
    """
    ref_words = reference.split()
    hyp_words = hypothesis.split()

    if not ref_words:
        return 0.0 if not hyp_words else 1.0

    n = len(ref_words)
    m = len(hyp_words)

    # DP matrix for edit distance
    dp = [[0] * (m + 1) for _ in range(n + 1)]

    for i in range(n + 1):
        dp[i][0] = i  # deletions
    for j in range(m + 1):
        dp[0][j] = j  # insertions

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = min(
                    dp[i - 1][j] + 1,     # deletion
                    dp[i][j - 1] + 1,     # insertion
                    dp[i - 1][j - 1] + 1, # substitution
                )

    return dp[n][m] / n


def calculate_vad_metrics(
    detected: list[tuple[float, float]],
    ground_truth: list[tuple[float, float]],
    tolerance: float = 0.3,
) -> tuple[float, float]:
    """Calculate VAD precision and recall.

    Args:
        detected: List of (start, end) segments detected by VAD.
        ground_truth: List of (start, end) ground truth segments.
        tolerance: Tolerance in seconds for segment matching.

    Returns:
        Tuple of (precision, recall).
    """
    if not detected and not ground_truth:
        return 1.0, 1.0
    if not detected:
        return 0.0, 0.0
    if not ground_truth:
        return 0.0, 0.0

    # Count true positives: detected segments that match ground truth
    true_positives = 0
    for det_start, det_end in detected:
        for gt_start, gt_end in ground_truth:
            # Check overlap
            overlap_start = max(det_start, gt_start)
            overlap_end = min(det_end, gt_end)
            if overlap_end - overlap_start > 0:
                # Check if within tolerance
                if abs(det_start - gt_start) < tolerance and abs(det_end - gt_end) < tolerance:
                    true_positives += 1
                    break

    precision = true_positives / len(detected) if detected else 0.0
    recall = true_positives / len(ground_truth) if ground_truth else 0.0

    return precision, recall
