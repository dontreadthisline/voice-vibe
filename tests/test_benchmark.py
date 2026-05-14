"""Tests for benchmark framework."""

from __future__ import annotations

import pytest

from benchmark.metrics import LatencyStats, calculate_wer, calculate_vad_metrics


class TestLatencyStats:
    """Tests for LatencyStats calculations."""

    def test_from_empty_durations(self) -> None:
        """Empty durations should return zero stats."""
        stats = LatencyStats.from_durations([])
        assert stats.mean == 0.0
        assert stats.median == 0.0
        assert stats.min == 0.0
        assert stats.max == 0.0
        assert stats.std == 0.0
        assert stats.p99 == 0.0
        assert stats.samples == 0

    def test_from_single_duration(self) -> None:
        """Single duration should have zero std."""
        stats = LatencyStats.from_durations([100.0])
        assert stats.mean == 100.0
        assert stats.median == 100.0
        assert stats.min == 100.0
        assert stats.max == 100.0
        assert stats.std == 0.0
        assert stats.p99 == 100.0
        assert stats.samples == 1

    def test_from_multiple_durations(self) -> None:
        """Multiple durations should calculate all stats correctly."""
        durations = [10.0, 20.0, 30.0, 40.0, 50.0]
        stats = LatencyStats.from_durations(durations)

        assert stats.mean == 30.0
        assert stats.median == 30.0
        assert stats.min == 10.0
        assert stats.max == 50.0
        assert stats.std > 0
        assert stats.samples == 5

    def test_p99_calculation(self) -> None:
        """P99 should be close to max for small samples."""
        durations = list(range(1, 101))  # 1 to 100
        stats = LatencyStats.from_durations(durations)

        # P99 index = int(100 * 0.99) = 99, clamped to 99 (0-indexed), value = 100
        assert stats.p99 == 100

    def test_median_odd_count(self) -> None:
        """Median of odd count should be middle value."""
        stats = LatencyStats.from_durations([10.0, 20.0, 30.0])
        assert stats.median == 20.0

    def test_median_even_count(self) -> None:
        """Median of even count should be average of middle values."""
        stats = LatencyStats.from_durations([10.0, 20.0, 30.0, 40.0])
        assert stats.median == 25.0


class TestCalculateWER:
    """Tests for Word Error Rate calculation."""

    def test_identical_strings(self) -> None:
        """Identical strings should have WER of 0."""
        assert calculate_wer("hello world", "hello world") == 0.0

    def test_empty_reference(self) -> None:
        """Empty reference with hypothesis should have WER of 1."""
        assert calculate_wer("", "hello") == 1.0

    def test_empty_hypothesis(self) -> None:
        """Empty hypothesis with reference should have WER of 1."""
        assert calculate_wer("hello", "") == 1.0

    def test_both_empty(self) -> None:
        """Both empty should have WER of 0."""
        assert calculate_wer("", "") == 0.0

    def test_substitution(self) -> None:
        """One substitution should give WER of 0.5."""
        # "hello world" -> "hello there": 1 substitution out of 2 words
        wer = calculate_wer("hello world", "hello there")
        assert wer == 0.5

    def test_deletion(self) -> None:
        """Deletion should increase WER."""
        # "hello world" -> "hello": 1 deletion out of 2 words
        wer = calculate_wer("hello world", "hello")
        assert wer == 0.5

    def test_insertion(self) -> None:
        """Insertion should increase WER."""
        # "hello" -> "hello world": 1 insertion out of 1 word
        wer = calculate_wer("hello", "hello world")
        assert wer == 1.0


class TestCalculateVADMetrics:
    """Tests for VAD precision/recall calculation."""

    def test_both_empty(self) -> None:
        """Empty detected and ground truth should give perfect score."""
        precision, recall = calculate_vad_metrics([], [])
        assert precision == 1.0
        assert recall == 1.0

    def test_detected_empty(self) -> None:
        """Empty detected should give zero scores."""
        precision, recall = calculate_vad_metrics([], [(0.0, 1.0)])
        assert precision == 0.0
        assert recall == 0.0

    def test_ground_truth_empty(self) -> None:
        """Empty ground truth should give zero scores."""
        precision, recall = calculate_vad_metrics([(0.0, 1.0)], [])
        assert precision == 0.0
        assert recall == 0.0

    def test_perfect_match(self) -> None:
        """Perfect match should give 1.0 for both."""
        segments = [(0.0, 1.0), (2.0, 3.0)]
        precision, recall = calculate_vad_metrics(segments, segments)
        assert precision == 1.0
        assert recall == 1.0

    def test_partial_match(self) -> None:
        """Partial overlap should work."""
        detected = [(0.0, 1.0), (2.0, 3.0)]
        ground_truth = [(0.0, 1.0), (4.0, 5.0)]

        precision, recall = calculate_vad_metrics(detected, ground_truth)
        # 1 true positive out of 2 detected
        assert precision == 0.5
        # 1 true positive out of 2 ground truth
        assert recall == 0.5
