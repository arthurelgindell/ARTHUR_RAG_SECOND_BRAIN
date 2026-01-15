#!/usr/bin/env python3
"""
Estimate VRAM requirements for LM Studio models.

This module provides utilities for estimating VRAM requirements before
loading models, helping users select appropriate quantization levels
and hardware configurations.

Usage:
    python check_vram.py <model-identifier>
    python check_vram.py --params 7 --quant q4_k_m

Environment Variables:
    LM_STUDIO_URL - Base URL (default: http://localhost:1234)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Any


@dataclass
class VRAMEstimate:
    """VRAM estimation result."""
    model: str
    quantization: str
    estimated_vram_gb: float
    recommended_gpu: str
    fits_in_vram: bool | None = None
    available_vram_gb: float | None = None
    notes: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "model": self.model,
            "quantization": self.quantization,
            "estimated_vram_gb": self.estimated_vram_gb,
            "recommended_gpu": self.recommended_gpu,
        }
        if self.fits_in_vram is not None:
            result["fits_in_vram"] = self.fits_in_vram
        if self.available_vram_gb is not None:
            result["available_vram_gb"] = self.available_vram_gb
        if self.notes:
            result["notes"] = self.notes
        return result


# Quantization multipliers (GB per billion parameters)
QUANT_MULTIPLIERS = {
    "q4_k_m": 0.55,
    "q4_k_s": 0.50,
    "q5_k_m": 0.70,
    "q5_k_s": 0.65,
    "q6_k": 0.85,
    "q8_0": 1.10,
    "fp16": 2.20,
    "bf16": 2.20,
}

# GPU VRAM specifications
GPU_VRAM = {
    "GTX 1650": 4,
    "RTX 3050": 8,
    "RTX 3060": 12,
    "RTX 3060 Ti": 8,
    "RTX 3070": 8,
    "RTX 3070 Ti": 8,
    "RTX 3080": 10,
    "RTX 3080 Ti": 12,
    "RTX 3090": 24,
    "RTX 3090 Ti": 24,
    "RTX 4060": 8,
    "RTX 4060 Ti": 8,
    "RTX 4070": 12,
    "RTX 4070 Ti": 12,
    "RTX 4070 Ti Super": 16,
    "RTX 4080": 16,
    "RTX 4080 Super": 16,
    "RTX 4090": 24,
    "RTX A4000": 16,
    "RTX A5000": 24,
    "RTX A6000": 48,
    "A100 40GB": 40,
    "A100 80GB": 80,
    "H100": 80,
    "M1 8GB": 8,
    "M1 16GB": 16,
    "M1 Pro 16GB": 16,
    "M1 Pro 32GB": 32,
    "M1 Max 32GB": 32,
    "M1 Max 64GB": 64,
    "M2 8GB": 8,
    "M2 16GB": 16,
    "M2 24GB": 24,
    "M2 Pro 16GB": 16,
    "M2 Pro 32GB": 32,
    "M2 Max 32GB": 32,
    "M2 Max 64GB": 64,
    "M2 Max 96GB": 96,
    "M3 8GB": 8,
    "M3 16GB": 16,
    "M3 24GB": 24,
    "M3 Pro 18GB": 18,
    "M3 Pro 36GB": 36,
    "M3 Max 36GB": 36,
    "M3 Max 48GB": 48,
    "M3 Max 64GB": 64,
    "M3 Max 96GB": 96,
    "M3 Max 128GB": 128,
    "M4 16GB": 16,
    "M4 24GB": 24,
    "M4 32GB": 32,
}


def estimate_vram(
    param_count_b: float,
    quantization: str = "q4_k_m",
    context_length: int = 8192
) -> float:
    """
    Estimate VRAM requirements for a model.

    Args:
        param_count_b: Parameter count in billions
        quantization: Quantization format
        context_length: Context window size

    Returns:
        Estimated VRAM in GB
    """
    quant = quantization.lower()
    multiplier = QUANT_MULTIPLIERS.get(quant, 0.55)

    # Base model size
    base_vram = param_count_b * multiplier

    # KV cache overhead (rough estimate)
    # ~0.5GB per 4096 context for 7B model, scales with params
    kv_overhead = (context_length / 4096) * (param_count_b / 7) * 0.5

    # General overhead (CUDA kernels, etc.)
    overhead = 0.5

    return round(base_vram + kv_overhead + overhead, 2)


def get_recommended_gpu(vram_needed: float) -> str:
    """Get recommended GPU based on VRAM requirements."""
    suitable_gpus = []

    for gpu, vram in sorted(GPU_VRAM.items(), key=lambda x: x[1]):
        if vram >= vram_needed:
            suitable_gpus.append((gpu, vram))

    if not suitable_gpus:
        return "Multi-GPU setup required (2x RTX 3090 or better)"

    # Return cheapest suitable option
    return suitable_gpus[0][0]


def run_lms_estimate(model_identifier: str) -> dict[str, Any]:
    """Run lms load --estimate-only to get official estimate."""
    try:
        result = subprocess.run(
            ["lms", "load", "--estimate-only", model_identifier],
            capture_output=True,
            text=True,
            timeout=30
        )

        output = {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }

        # Parse VRAM info if present
        for line in result.stdout.split('\n'):
            line_lower = line.lower()
            if 'vram' in line_lower or 'memory' in line_lower:
                output["vram_info"] = line.strip()

        return output

    except FileNotFoundError:
        return {"success": False, "error": "lms CLI not found. Is LM Studio installed?"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout waiting for lms command"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def parse_model_size(model_name: str) -> float | None:
    """Try to parse parameter count from model name."""
    import re

    # Common patterns: 7b, 7B, 7.5b, 7.5B, 70b, etc.
    patterns = [
        r'(\d+\.?\d*)[bB](?:-|_|$)',  # 7b, 7B, 7.5b
        r'(\d+\.?\d*)(?:billion|B)(?:-|_|$)',  # 7billion
    ]

    for pattern in patterns:
        match = re.search(pattern, model_name)
        if match:
            return float(match.group(1))

    return None


def estimate_for_model(
    model_identifier: str,
    quantization: str = "q4_k_m",
    context_length: int = 8192,
    use_lms: bool = True
) -> VRAMEstimate:
    """
    Estimate VRAM requirements for a model.

    Args:
        model_identifier: Model name or path
        quantization: Quantization format
        context_length: Context window size
        use_lms: Whether to try lms CLI first

    Returns:
        VRAMEstimate object
    """
    notes = []

    # Try to get official estimate from LM Studio
    if use_lms:
        lms_result = run_lms_estimate(model_identifier)
        if lms_result.get("success") and lms_result.get("vram_info"):
            notes.append(f"LMS estimate: {lms_result['vram_info']}")

    # Parse parameter count from name
    param_count = parse_model_size(model_identifier)

    if param_count is None:
        # Default estimates for common model families
        if "qwen" in model_identifier.lower():
            if "32b" in model_identifier.lower():
                param_count = 32
            elif "14b" in model_identifier.lower():
                param_count = 14
            elif "7b" in model_identifier.lower():
                param_count = 7
            elif "3b" in model_identifier.lower():
                param_count = 3
            else:
                param_count = 7  # Default
        elif "deepseek" in model_identifier.lower():
            if "32b" in model_identifier.lower():
                param_count = 32
            else:
                param_count = 7
        elif "llama" in model_identifier.lower():
            if "70b" in model_identifier.lower():
                param_count = 70
            elif "13b" in model_identifier.lower():
                param_count = 13
            else:
                param_count = 7
        else:
            param_count = 7  # Default assumption
            notes.append("Could not determine model size, assuming 7B")

    vram_needed = estimate_vram(param_count, quantization, context_length)
    recommended_gpu = get_recommended_gpu(vram_needed)

    return VRAMEstimate(
        model=model_identifier,
        quantization=quantization,
        estimated_vram_gb=vram_needed,
        recommended_gpu=recommended_gpu,
        notes=notes if notes else None
    )


def get_all_quantization_estimates(param_count_b: float) -> dict[str, float]:
    """Get VRAM estimates for all quantization levels."""
    return {
        quant: estimate_vram(param_count_b, quant)
        for quant in QUANT_MULTIPLIERS
    }


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Estimate VRAM requirements for LM Studio models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s qwen2.5-7b-instruct
  %(prog)s --params 32 --quant q4_k_m
  %(prog)s --params 7 --all-quants
  %(prog)s deepseek-r1-distill-qwen-7b --context 16384
        """
    )

    parser.add_argument(
        "model",
        nargs="?",
        help="Model identifier or name"
    )
    parser.add_argument(
        "--params", "-p",
        type=float,
        help="Parameter count in billions (e.g., 7 for 7B model)"
    )
    parser.add_argument(
        "--quant", "-q",
        default="q4_k_m",
        choices=list(QUANT_MULTIPLIERS.keys()),
        help="Quantization format (default: q4_k_m)"
    )
    parser.add_argument(
        "--context", "-c",
        type=int,
        default=8192,
        help="Context length (default: 8192)"
    )
    parser.add_argument(
        "--all-quants",
        action="store_true",
        help="Show estimates for all quantization levels"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )
    parser.add_argument(
        "--no-lms",
        action="store_true",
        help="Don't try to use lms CLI"
    )

    args = parser.parse_args()

    if not args.model and not args.params:
        parser.print_help()
        return 2

    # Direct parameter estimation
    if args.params:
        if args.all_quants:
            estimates = get_all_quantization_estimates(args.params)
            if args.json:
                print(json.dumps({
                    "param_count_b": args.params,
                    "context_length": args.context,
                    "estimates": estimates
                }, indent=2))
            else:
                print(f"VRAM estimates for {args.params}B model (context: {args.context}):\n")
                for quant, vram in sorted(estimates.items(), key=lambda x: x[1]):
                    gpu = get_recommended_gpu(vram)
                    print(f"  {quant:8s}: {vram:6.2f} GB  ->  {gpu}")
            return 0

        vram = estimate_vram(args.params, args.quant, args.context)
        gpu = get_recommended_gpu(vram)

        if args.json:
            print(json.dumps({
                "param_count_b": args.params,
                "quantization": args.quant,
                "context_length": args.context,
                "estimated_vram_gb": vram,
                "recommended_gpu": gpu
            }, indent=2))
        else:
            print(f"Model: {args.params}B parameters")
            print(f"Quantization: {args.quant}")
            print(f"Context: {args.context}")
            print(f"Estimated VRAM: {vram:.2f} GB")
            print(f"Recommended GPU: {gpu}")
        return 0

    # Model-based estimation
    estimate = estimate_for_model(
        args.model,
        args.quant,
        args.context,
        use_lms=not args.no_lms
    )

    if args.json:
        print(json.dumps(estimate.to_dict(), indent=2))
    else:
        print(f"Model: {estimate.model}")
        print(f"Quantization: {estimate.quantization}")
        print(f"Estimated VRAM: {estimate.estimated_vram_gb:.2f} GB")
        print(f"Recommended GPU: {estimate.recommended_gpu}")
        if estimate.notes:
            print("\nNotes:")
            for note in estimate.notes:
                print(f"  - {note}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
