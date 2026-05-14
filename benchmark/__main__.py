"""CLI entry point for benchmark."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from benchmark.config import BenchmarkConfig, get_default_config
from benchmark.runner import BenchmarkRunner


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="VoiceVibe Benchmark - Compare VAD+ASR+LLM combinations"
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to benchmark config file (YAML)",
    )
    parser.add_argument(
        "--audio-dir",
        type=Path,
        default=Path("benchmark/data"),
        help="Directory containing audio samples (default: benchmark/data)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output report file path (default: benchmark/results/benchmark_results.md)",
    )
    parser.add_argument(
        "--runs",
        "-n",
        type=int,
        default=1,
        help="Number of runs per sample (default: 1)",
    )
    return parser.parse_args()


async def main() -> None:
    """Run benchmark and generate report."""
    args = parse_args()

    # Load configuration
    if args.config:
        # TODO: Support YAML config loading
        print(f"Config file loading not yet implemented, using defaults")
        config = get_default_config()
    else:
        config = get_default_config()

    # Override with CLI args
    config.audio_dir = args.audio_dir
    config.runs_per_sample = args.runs

    # Run benchmark
    runner = BenchmarkRunner(config)
    results = await runner.run_all()

    if not results:
        print("No results to report")
        return

    # Generate and save report
    report = runner.generate_report(results)
    runner.save_report(report, args.output)

    # Also print to console
    print("\n" + "=" * 60)
    print(report)


if __name__ == "__main__":
    asyncio.run(main())
