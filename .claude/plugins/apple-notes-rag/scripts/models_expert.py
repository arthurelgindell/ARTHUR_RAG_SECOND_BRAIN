#!/usr/bin/env python3
"""
LM Studio Models Expert - Analysis and recommendations.

Analyzes available models, provides task-specific recommendations,
and monitors performance.

Usage:
    python3 models_expert.py list                     # List available models
    python3 models_expert.py recommend --task chat    # Get recommendations
    python3 models_expert.py analyze MODEL_NAME       # Analyze specific model
    python3 models_expert.py benchmark MODEL_NAME     # Run benchmark
    python3 models_expert.py status                   # Server status

Requirements:
    LM Studio running at localhost:1234
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

# Configuration
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234")
MODELS_DIR = Path(os.getenv("LM_STUDIO_MODELS_DIR", "/Users/arthurdell/ARTHUR/MODELS"))

# Model knowledge base
MODEL_CATEGORIES = {
    "embedding": {
        "description": "Text embedding models for semantic search and RAG",
        "recommended": [
            {
                "name": "nomic-embed-text-v1.5",
                "dimensions": 768,
                "context": 8192,
                "strengths": ["General purpose", "Good balance of speed/quality"],
                "vram_gb": 0.5
            },
            {
                "name": "bge-base-en-v1.5",
                "dimensions": 768,
                "context": 512,
                "strengths": ["Fast", "English optimized"],
                "vram_gb": 0.4
            },
            {
                "name": "e5-base-v2",
                "dimensions": 768,
                "context": 512,
                "strengths": ["Multilingual", "Good for retrieval"],
                "vram_gb": 0.4
            }
        ]
    },
    "chat": {
        "description": "Conversational models for chat and assistance",
        "recommended": [
            {
                "name": "nemotron-3-nano",
                "parameters": "4B",
                "context": 4096,
                "strengths": ["Fast", "Low VRAM", "Good reasoning"],
                "vram_gb": 3
            },
            {
                "name": "qwen2.5-7b-instruct",
                "parameters": "7B",
                "context": 32768,
                "strengths": ["Long context", "Multilingual", "Strong reasoning"],
                "vram_gb": 6
            },
            {
                "name": "llama-3.2-8b-instruct",
                "parameters": "8B",
                "context": 8192,
                "strengths": ["Balanced", "Good instruction following"],
                "vram_gb": 6
            }
        ]
    },
    "code": {
        "description": "Code generation and analysis models",
        "recommended": [
            {
                "name": "deepseek-coder-6.7b-instruct",
                "parameters": "6.7B",
                "context": 16384,
                "strengths": ["Excellent code quality", "Multiple languages"],
                "vram_gb": 5
            },
            {
                "name": "codellama-7b-instruct",
                "parameters": "7B",
                "context": 16384,
                "strengths": ["Python focused", "Good explanations"],
                "vram_gb": 5
            },
            {
                "name": "starcoder2-7b",
                "parameters": "7B",
                "context": 16384,
                "strengths": ["80+ languages", "Fill-in-middle"],
                "vram_gb": 5
            }
        ]
    },
    "reasoning": {
        "description": "Models optimized for complex reasoning tasks",
        "recommended": [
            {
                "name": "deepseek-r1-distill-qwen-7b",
                "parameters": "7B",
                "context": 32768,
                "strengths": ["Chain of thought", "Math", "Logic"],
                "vram_gb": 6
            },
            {
                "name": "phi-3-medium-128k-instruct",
                "parameters": "14B",
                "context": 128000,
                "strengths": ["Very long context", "Strong reasoning"],
                "vram_gb": 10
            }
        ]
    }
}


def get_server_status() -> dict[str, Any]:
    """Get LM Studio server status and loaded models."""
    try:
        response = requests.get(f"{LM_STUDIO_URL}/v1/models", timeout=5)
        response.raise_for_status()
        data = response.json()

        models = data.get("data", [])

        return {
            "status": "healthy",
            "url": LM_STUDIO_URL,
            "loaded_models": [m["id"] for m in models],
            "model_count": len(models)
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "offline",
            "url": LM_STUDIO_URL,
            "error": str(e)
        }


def list_local_models() -> list[dict[str, Any]]:
    """List models available in the local models directory."""
    models = []

    if not MODELS_DIR.exists():
        return models

    # Look for model directories
    for provider_dir in MODELS_DIR.iterdir():
        if provider_dir.is_dir():
            for model_dir in provider_dir.iterdir():
                if model_dir.is_dir():
                    # Check for model files
                    gguf_files = list(model_dir.glob("*.gguf"))
                    if gguf_files:
                        # Get total size
                        total_size = sum(f.stat().st_size for f in gguf_files)
                        models.append({
                            "name": model_dir.name,
                            "provider": provider_dir.name,
                            "path": str(model_dir),
                            "files": [f.name for f in gguf_files],
                            "size_gb": round(total_size / (1024**3), 2)
                        })

    return models


def recommend_model(task: str, vram_available: float = 8.0) -> dict[str, Any]:
    """
    Get model recommendations for a specific task.

    Args:
        task: Task type (embedding, chat, code, reasoning)
        vram_available: Available VRAM in GB

    Returns:
        Recommendation with primary and alternative models
    """
    if task not in MODEL_CATEGORIES:
        return {
            "error": f"Unknown task: {task}",
            "available_tasks": list(MODEL_CATEGORIES.keys())
        }

    category = MODEL_CATEGORIES[task]
    recommendations = []

    for model in category["recommended"]:
        if model.get("vram_gb", 0) <= vram_available:
            recommendations.append(model)

    if not recommendations:
        return {
            "task": task,
            "error": f"No models fit in {vram_available}GB VRAM",
            "suggestion": "Consider using quantized versions or smaller models"
        }

    return {
        "task": task,
        "description": category["description"],
        "vram_available_gb": vram_available,
        "primary": recommendations[0],
        "alternatives": recommendations[1:] if len(recommendations) > 1 else []
    }


def benchmark_model(model_name: str, prompt: str = "Explain quantum computing in simple terms.") -> dict[str, Any]:
    """
    Run a simple benchmark on a loaded model.

    Args:
        model_name: Name of the model to benchmark
        prompt: Test prompt

    Returns:
        Benchmark results including tokens/sec
    """
    # Check if model is loaded
    status = get_server_status()
    if status["status"] != "healthy":
        return {"error": "LM Studio not available"}

    if model_name not in status["loaded_models"]:
        return {
            "error": f"Model {model_name} not loaded",
            "loaded_models": status["loaded_models"]
        }

    # Run benchmark
    start_time = time.time()

    try:
        response = requests.post(
            f"{LM_STUDIO_URL}/v1/chat/completions",
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.7
            },
            timeout=60
        )
        response.raise_for_status()
        data = response.json()

        end_time = time.time()
        elapsed = end_time - start_time

        usage = data.get("usage", {})
        completion_tokens = usage.get("completion_tokens", 0)
        prompt_tokens = usage.get("prompt_tokens", 0)

        tokens_per_sec = completion_tokens / elapsed if elapsed > 0 else 0

        return {
            "model": model_name,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_time_sec": round(elapsed, 2),
            "tokens_per_sec": round(tokens_per_sec, 1),
            "response_preview": data["choices"][0]["message"]["content"][:200] + "..."
        }

    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def analyze_model(model_name: str) -> dict[str, Any]:
    """
    Analyze a model's characteristics and suitability.

    Args:
        model_name: Name of the model to analyze

    Returns:
        Model analysis including capabilities and recommendations
    """
    # Check all categories for this model
    found_in = []
    model_info = None

    for task, category in MODEL_CATEGORIES.items():
        for model in category["recommended"]:
            if model_name.lower() in model["name"].lower():
                found_in.append(task)
                model_info = model
                break

    # Check local models
    local_models = list_local_models()
    local_match = None
    for m in local_models:
        if model_name.lower() in m["name"].lower():
            local_match = m
            break

    return {
        "model_name": model_name,
        "known_info": model_info,
        "suitable_for": found_in if found_in else ["general"],
        "local_path": local_match["path"] if local_match else None,
        "local_size_gb": local_match["size_gb"] if local_match else None,
        "recommendations": {
            "use_cases": found_in if found_in else ["General chat", "Simple tasks"],
            "tips": [
                "Use Q4_K_M quantization for best quality/size balance",
                "Enable GPU offloading for better performance",
                "Monitor VRAM usage during inference"
            ]
        }
    }


def main():
    parser = argparse.ArgumentParser(
        description="LM Studio Models Expert"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List command
    list_parser = subparsers.add_parser("list", help="List available models")
    list_parser.add_argument("--local", action="store_true", help="List local models only")

    # Recommend command
    rec_parser = subparsers.add_parser("recommend", help="Get model recommendations")
    rec_parser.add_argument("--task", "-t", required=True,
                           choices=list(MODEL_CATEGORIES.keys()),
                           help="Task type")
    rec_parser.add_argument("--vram", type=float, default=8.0,
                           help="Available VRAM in GB (default: 8)")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a model")
    analyze_parser.add_argument("model", help="Model name to analyze")

    # Benchmark command
    bench_parser = subparsers.add_parser("benchmark", help="Benchmark a model")
    bench_parser.add_argument("model", help="Model name to benchmark")
    bench_parser.add_argument("--prompt", "-p", default="Explain quantum computing simply.",
                             help="Test prompt")

    # Status command
    subparsers.add_parser("status", help="Show server status")

    # JSON output
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    result = None

    if args.command == "status":
        result = get_server_status()

    elif args.command == "list":
        if args.local:
            result = {"local_models": list_local_models()}
        else:
            status = get_server_status()
            local = list_local_models()
            result = {
                "server_status": status,
                "loaded_models": status.get("loaded_models", []),
                "local_models": local
            }

    elif args.command == "recommend":
        result = recommend_model(args.task, args.vram)

    elif args.command == "analyze":
        result = analyze_model(args.model)

    elif args.command == "benchmark":
        result = benchmark_model(args.model, args.prompt)

    # Output
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if args.command == "status":
            print(f"Server: {result['url']}")
            print(f"Status: {result['status']}")
            if result['status'] == 'healthy':
                print(f"Loaded models: {', '.join(result['loaded_models'])}")
            else:
                print(f"Error: {result.get('error', 'Unknown')}")

        elif args.command == "list":
            print("\n=== LM Studio Models ===\n")
            if result.get("loaded_models"):
                print("Currently Loaded:")
                for m in result["loaded_models"]:
                    print(f"  - {m}")
            print(f"\nLocal Models ({len(result.get('local_models', []))}):")
            for m in result.get("local_models", []):
                print(f"  - {m['provider']}/{m['name']} ({m['size_gb']} GB)")

        elif args.command == "recommend":
            if "error" in result:
                print(f"Error: {result['error']}")
            else:
                print(f"\n=== Recommendations for: {result['task']} ===")
                print(f"{result['description']}\n")
                print(f"Primary Recommendation:")
                p = result['primary']
                print(f"  {p['name']}")
                print(f"    VRAM: ~{p.get('vram_gb', 'N/A')} GB")
                print(f"    Strengths: {', '.join(p.get('strengths', []))}")
                if result['alternatives']:
                    print(f"\nAlternatives:")
                    for alt in result['alternatives']:
                        print(f"  - {alt['name']} ({alt.get('vram_gb', 'N/A')} GB)")

        elif args.command == "analyze":
            print(f"\n=== Model Analysis: {result['model_name']} ===\n")
            print(f"Suitable for: {', '.join(result['suitable_for'])}")
            if result['local_path']:
                print(f"Local path: {result['local_path']}")
                print(f"Size: {result['local_size_gb']} GB")
            if result['known_info']:
                info = result['known_info']
                print(f"\nKnown specs:")
                for k, v in info.items():
                    if k != 'name':
                        print(f"  {k}: {v}")

        elif args.command == "benchmark":
            if "error" in result:
                print(f"Error: {result['error']}")
            else:
                print(f"\n=== Benchmark: {result['model']} ===\n")
                print(f"Prompt tokens: {result['prompt_tokens']}")
                print(f"Completion tokens: {result['completion_tokens']}")
                print(f"Total time: {result['total_time_sec']}s")
                print(f"Speed: {result['tokens_per_sec']} tokens/sec")
                print(f"\nResponse preview:\n{result['response_preview']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
