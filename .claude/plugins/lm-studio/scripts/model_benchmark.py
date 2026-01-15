#!/usr/bin/env python3
"""
Benchmark LM Studio model inference performance.

This module provides utilities for measuring inference latency,
tokens per second, and throughput for loaded models.

Usage:
    python model_benchmark.py
    python model_benchmark.py --model qwen2.5-7b-instruct --iterations 10
    python model_benchmark.py --prompt "Write a haiku" --max-tokens 100

Environment Variables:
    LM_STUDIO_URL - Base URL (default: http://localhost:1234)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from statistics import mean, median, stdev
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# Default server URL
DEFAULT_URL = os.environ.get("LM_STUDIO_URL", "http://localhost:1234")

# Benchmark prompts for different tasks
BENCHMARK_PROMPTS = {
    "short": "Write a haiku about programming.",
    "medium": "Explain the difference between a list and a tuple in Python. Be concise.",
    "long": "Write a detailed explanation of how binary search works, including its time complexity, space complexity, and when to use it.",
    "code": "Write a Python function that implements merge sort. Include comments.",
    "reasoning": "A farmer has 15 sheep. All but 8 run away. How many sheep does the farmer have left? Think step by step.",
}


@dataclass
class InferenceResult:
    """Single inference result."""
    success: bool
    latency_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    tokens_per_second: float = 0.0
    error: str | None = None


@dataclass
class BenchmarkResult:
    """Aggregated benchmark results."""
    model: str
    iterations: int
    prompt_type: str
    max_tokens: int
    successful_runs: int
    failed_runs: int
    latencies_ms: list[float] = field(default_factory=list)
    tokens_per_second: list[float] = field(default_factory=list)
    completion_tokens: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        if not self.latencies_ms:
            return {
                "model": self.model,
                "error": "No successful runs",
                "failed_runs": self.failed_runs
            }

        return {
            "model": self.model,
            "iterations": self.iterations,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "prompt_type": self.prompt_type,
            "max_tokens": self.max_tokens,
            "latency_ms": {
                "mean": round(mean(self.latencies_ms), 2),
                "median": round(median(self.latencies_ms), 2),
                "min": round(min(self.latencies_ms), 2),
                "max": round(max(self.latencies_ms), 2),
                "stdev": round(stdev(self.latencies_ms), 2) if len(self.latencies_ms) > 1 else 0
            },
            "tokens_per_second": {
                "mean": round(mean(self.tokens_per_second), 2) if self.tokens_per_second else 0,
                "median": round(median(self.tokens_per_second), 2) if self.tokens_per_second else 0,
                "min": round(min(self.tokens_per_second), 2) if self.tokens_per_second else 0,
                "max": round(max(self.tokens_per_second), 2) if self.tokens_per_second else 0,
            },
            "completion_tokens": {
                "mean": round(mean(self.completion_tokens), 1) if self.completion_tokens else 0,
                "total": sum(self.completion_tokens)
            }
        }


class ModelBenchmark:
    """Benchmark runner for LM Studio models."""

    def __init__(self, base_url: str = DEFAULT_URL):
        self.base_url = base_url.rstrip("/")

    def _get_models(self) -> list[str]:
        """Get list of loaded models."""
        url = f"{self.base_url}/v1/models"
        request = Request(url, method="GET")
        request.add_header("Accept", "application/json")

        try:
            with urlopen(request, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
                return [m["id"] for m in data.get("data", [])]
        except Exception:
            return []

    def run_inference(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.7
    ) -> InferenceResult:
        """Run a single inference and measure performance."""
        url = f"{self.base_url}/v1/chat/completions"
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }).encode("utf-8")

        request = Request(url, data=payload, method="POST")
        request.add_header("Content-Type", "application/json")

        start_time = time.time()
        try:
            with urlopen(request, timeout=120) as response:
                elapsed_ms = (time.time() - start_time) * 1000
                data = json.loads(response.read().decode("utf-8"))

                usage = data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)

                # Calculate tokens per second (generation only)
                elapsed_sec = elapsed_ms / 1000
                tps = completion_tokens / elapsed_sec if elapsed_sec > 0 else 0

                return InferenceResult(
                    success=True,
                    latency_ms=elapsed_ms,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    tokens_per_second=tps
                )

        except HTTPError as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return InferenceResult(
                success=False,
                latency_ms=elapsed_ms,
                error=f"HTTP {e.code}: {e.reason}"
            )
        except URLError as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return InferenceResult(
                success=False,
                latency_ms=elapsed_ms,
                error=str(e.reason)
            )
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return InferenceResult(
                success=False,
                latency_ms=elapsed_ms,
                error=str(e)
            )

    def run_benchmark(
        self,
        model: str | None = None,
        prompt: str | None = None,
        prompt_type: str = "short",
        iterations: int = 5,
        max_tokens: int = 100,
        temperature: float = 0.7,
        warmup: int = 1,
        verbose: bool = False
    ) -> BenchmarkResult:
        """Run benchmark with multiple iterations."""

        # Get model if not specified
        if model is None:
            models = self._get_models()
            if not models:
                return BenchmarkResult(
                    model="unknown",
                    iterations=0,
                    prompt_type=prompt_type,
                    max_tokens=max_tokens,
                    successful_runs=0,
                    failed_runs=1
                )
            model = models[0]

        # Get prompt
        if prompt is None:
            prompt = BENCHMARK_PROMPTS.get(prompt_type, BENCHMARK_PROMPTS["short"])

        result = BenchmarkResult(
            model=model,
            iterations=iterations,
            prompt_type=prompt_type,
            max_tokens=max_tokens,
            successful_runs=0,
            failed_runs=0
        )

        # Warmup runs
        if warmup > 0 and verbose:
            print(f"Running {warmup} warmup iteration(s)...")

        for i in range(warmup):
            self.run_inference(model, prompt, max_tokens, temperature)

        # Benchmark runs
        if verbose:
            print(f"Running {iterations} benchmark iteration(s)...")

        for i in range(iterations):
            inference = self.run_inference(model, prompt, max_tokens, temperature)

            if inference.success:
                result.successful_runs += 1
                result.latencies_ms.append(inference.latency_ms)
                result.tokens_per_second.append(inference.tokens_per_second)
                result.completion_tokens.append(inference.completion_tokens)

                if verbose:
                    print(f"  [{i+1}/{iterations}] {inference.latency_ms:.0f}ms, "
                          f"{inference.tokens_per_second:.1f} tok/s, "
                          f"{inference.completion_tokens} tokens")
            else:
                result.failed_runs += 1
                if verbose:
                    print(f"  [{i+1}/{iterations}] FAILED: {inference.error}")

        return result

    def compare_models(
        self,
        models: list[str] | None = None,
        prompt_type: str = "short",
        iterations: int = 3,
        max_tokens: int = 100
    ) -> list[BenchmarkResult]:
        """Compare performance across multiple models."""

        if models is None:
            models = self._get_models()

        if not models:
            return []

        results = []
        for model in models:
            print(f"\nBenchmarking: {model}")
            result = self.run_benchmark(
                model=model,
                prompt_type=prompt_type,
                iterations=iterations,
                max_tokens=max_tokens,
                verbose=True
            )
            results.append(result)

        return results


def format_benchmark_result(result: BenchmarkResult) -> str:
    """Format benchmark result for display."""
    data = result.to_dict()

    if "error" in data:
        return f"Model: {data['model']}\n  Error: {data['error']}"

    lines = [
        f"Model: {data['model']}",
        f"Prompt: {data['prompt_type']} ({data['max_tokens']} max tokens)",
        f"Iterations: {data['successful_runs']}/{data['iterations']} successful",
        "",
        "Latency (ms):",
        f"  Mean: {data['latency_ms']['mean']:.1f}",
        f"  Median: {data['latency_ms']['median']:.1f}",
        f"  Min/Max: {data['latency_ms']['min']:.1f} / {data['latency_ms']['max']:.1f}",
        f"  Std Dev: {data['latency_ms']['stdev']:.1f}",
        "",
        "Tokens per Second:",
        f"  Mean: {data['tokens_per_second']['mean']:.1f}",
        f"  Median: {data['tokens_per_second']['median']:.1f}",
        f"  Min/Max: {data['tokens_per_second']['min']:.1f} / {data['tokens_per_second']['max']:.1f}",
        "",
        f"Completion Tokens: {data['completion_tokens']['mean']:.0f} avg ({data['completion_tokens']['total']} total)"
    ]

    return "\n".join(lines)


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark LM Studio model performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Prompt types:
  short    - Write a haiku (quick test)
  medium   - Explain Python data structures
  long     - Detailed algorithm explanation
  code     - Write merge sort implementation
  reasoning - Math word problem with step-by-step

Examples:
  %(prog)s                                    # Quick benchmark
  %(prog)s --model qwen2.5-7b --iterations 10
  %(prog)s --prompt-type code --max-tokens 500
  %(prog)s --compare                          # Compare all loaded models
        """
    )

    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"LM Studio server URL (default: {DEFAULT_URL})"
    )
    parser.add_argument(
        "--model", "-m",
        help="Model to benchmark (default: first loaded model)"
    )
    parser.add_argument(
        "--prompt", "-p",
        help="Custom prompt to use"
    )
    parser.add_argument(
        "--prompt-type", "-t",
        choices=list(BENCHMARK_PROMPTS.keys()),
        default="short",
        help="Benchmark prompt type (default: short)"
    )
    parser.add_argument(
        "--iterations", "-n",
        type=int,
        default=5,
        help="Number of benchmark iterations (default: 5)"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=100,
        help="Maximum tokens to generate (default: 100)"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature (default: 0.7)"
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=1,
        help="Warmup iterations before benchmark (default: 1)"
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare all loaded models"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show progress for each iteration"
    )

    args = parser.parse_args()

    benchmark = ModelBenchmark(args.url)

    # Compare mode
    if args.compare:
        results = benchmark.compare_models(
            prompt_type=args.prompt_type,
            iterations=args.iterations,
            max_tokens=args.max_tokens
        )

        if not results:
            print("No models available for comparison")
            return 1

        if args.json:
            print(json.dumps([r.to_dict() for r in results], indent=2))
        else:
            print("\n" + "=" * 60)
            print("COMPARISON RESULTS")
            print("=" * 60)

            # Sort by mean tokens per second
            sorted_results = sorted(
                results,
                key=lambda r: mean(r.tokens_per_second) if r.tokens_per_second else 0,
                reverse=True
            )

            for i, result in enumerate(sorted_results):
                print(f"\n#{i+1}")
                print(format_benchmark_result(result))

        return 0

    # Single model benchmark
    result = benchmark.run_benchmark(
        model=args.model,
        prompt=args.prompt,
        prompt_type=args.prompt_type,
        iterations=args.iterations,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        warmup=args.warmup,
        verbose=args.verbose
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print("\n" + "=" * 40)
        print("BENCHMARK RESULTS")
        print("=" * 40 + "\n")
        print(format_benchmark_result(result))

    return 0 if result.successful_runs > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
