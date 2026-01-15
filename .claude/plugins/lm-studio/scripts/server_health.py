#!/usr/bin/env python3
"""
Monitor LM Studio server health and loaded models.

This module provides utilities for checking server status, listing
loaded models, and monitoring inference capabilities.

Usage:
    python server_health.py
    python server_health.py --watch
    python server_health.py --model qwen2.5-7b-instruct

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
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# Default server URL
DEFAULT_URL = os.environ.get("LM_STUDIO_URL", "http://localhost:1234")


@dataclass
class ModelInfo:
    """Information about a loaded model."""
    id: str
    object: str = "model"
    owned_by: str = "local"
    capabilities: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelInfo":
        return cls(
            id=data.get("id", "unknown"),
            object=data.get("object", "model"),
            owned_by=data.get("owned_by", "local"),
            capabilities=data.get("capabilities", [])
        )


@dataclass
class ServerHealth:
    """Server health status."""
    healthy: bool
    url: str
    models: list[ModelInfo] = field(default_factory=list)
    error: str | None = None
    response_time_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "healthy": self.healthy,
            "url": self.url,
            "model_count": len(self.models),
        }
        if self.models:
            result["models"] = [
                {"id": m.id, "capabilities": m.capabilities}
                for m in self.models
            ]
        if self.error:
            result["error"] = self.error
        if self.response_time_ms is not None:
            result["response_time_ms"] = round(self.response_time_ms, 2)
        return result


class LMStudioHealthChecker:
    """Health checker for LM Studio server."""

    def __init__(self, base_url: str = DEFAULT_URL):
        self.base_url = base_url.rstrip("/")

    def _request(
        self,
        endpoint: str,
        method: str = "GET",
        timeout: int = 5
    ) -> tuple[dict[str, Any] | None, float]:
        """Make HTTP request and return response with timing."""
        url = f"{self.base_url}{endpoint}"
        request = Request(url, method=method)
        request.add_header("Accept", "application/json")

        start_time = time.time()
        try:
            with urlopen(request, timeout=timeout) as response:
                elapsed = (time.time() - start_time) * 1000
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}, elapsed
        except (HTTPError, URLError, json.JSONDecodeError):
            elapsed = (time.time() - start_time) * 1000
            return None, elapsed

    def check_health(self) -> ServerHealth:
        """Check overall server health."""
        # Try to get models list (this confirms server is running)
        data, response_time = self._request("/v1/models")

        if data is None:
            return ServerHealth(
                healthy=False,
                url=self.base_url,
                error="Server not responding. Is LM Studio running?",
                response_time_ms=response_time
            )

        models = []
        for model_data in data.get("data", []):
            models.append(ModelInfo.from_dict(model_data))

        return ServerHealth(
            healthy=True,
            url=self.base_url,
            models=models,
            response_time_ms=response_time
        )

    def get_model_details(self, model_id: str) -> dict[str, Any] | None:
        """Get details for a specific model."""
        health = self.check_health()
        if not health.healthy:
            return {"error": health.error}

        for model in health.models:
            if model.id == model_id or model_id in model.id:
                return {
                    "id": model.id,
                    "capabilities": model.capabilities,
                    "owned_by": model.owned_by
                }

        return {"error": f"Model '{model_id}' not found in loaded models"}

    def test_inference(
        self,
        model: str | None = None,
        prompt: str = "Say 'hello' and nothing else."
    ) -> dict[str, Any]:
        """Test inference with a simple prompt."""
        health = self.check_health()
        if not health.healthy:
            return {"success": False, "error": health.error}

        if not health.models:
            return {"success": False, "error": "No models loaded"}

        # Use specified model or first available
        target_model = model
        if target_model is None:
            # Prefer chat-capable models
            for m in health.models:
                if "llm.chat" in m.capabilities or not m.capabilities:
                    target_model = m.id
                    break
            if target_model is None:
                target_model = health.models[0].id

        # Make inference request
        url = f"{self.base_url}/v1/chat/completions"
        payload = json.dumps({
            "model": target_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 50,
            "temperature": 0.1
        }).encode("utf-8")

        request = Request(url, data=payload, method="POST")
        request.add_header("Content-Type", "application/json")

        start_time = time.time()
        try:
            with urlopen(request, timeout=30) as response:
                elapsed = (time.time() - start_time) * 1000
                data = json.loads(response.read().decode("utf-8"))

                return {
                    "success": True,
                    "model": target_model,
                    "response": data["choices"][0]["message"]["content"],
                    "inference_time_ms": round(elapsed, 2),
                    "usage": data.get("usage", {})
                }
        except HTTPError as e:
            return {
                "success": False,
                "error": f"HTTP {e.code}: {e.reason}",
                "model": target_model
            }
        except URLError as e:
            return {"success": False, "error": str(e.reason)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def check_embedding_capability(self) -> dict[str, Any]:
        """Check if embedding models are available."""
        health = self.check_health()
        if not health.healthy:
            return {"available": False, "error": health.error}

        embedding_models = [
            m.id for m in health.models
            if "embedding" in m.id.lower() or "embedding.text" in m.capabilities
        ]

        return {
            "available": len(embedding_models) > 0,
            "models": embedding_models
        }


def watch_health(
    checker: LMStudioHealthChecker,
    interval: int = 5,
    json_output: bool = False
) -> None:
    """Continuously monitor server health."""
    print(f"Watching LM Studio at {checker.base_url} (Ctrl+C to stop)\n")

    try:
        while True:
            health = checker.check_health()

            if json_output:
                print(json.dumps(health.to_dict()))
            else:
                timestamp = time.strftime("%H:%M:%S")
                status = "OK" if health.healthy else "DOWN"
                model_count = len(health.models)

                if health.healthy:
                    models_str = ", ".join(m.id for m in health.models[:3])
                    if model_count > 3:
                        models_str += f" (+{model_count - 3} more)"
                    print(f"[{timestamp}] {status} - {model_count} model(s): {models_str}")
                else:
                    print(f"[{timestamp}] {status} - {health.error}")

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nStopped watching.")


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Monitor LM Studio server health",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                         # Basic health check
  %(prog)s --test                  # Test inference
  %(prog)s --model qwen2.5-7b      # Get specific model info
  %(prog)s --watch                 # Continuous monitoring
  %(prog)s --url http://host:8080  # Custom server URL
        """
    )

    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"LM Studio server URL (default: {DEFAULT_URL})"
    )
    parser.add_argument(
        "--model", "-m",
        help="Get details for specific model"
    )
    parser.add_argument(
        "--test", "-t",
        action="store_true",
        help="Test inference with a simple prompt"
    )
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Continuously monitor health"
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=5,
        help="Watch interval in seconds (default: 5)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )
    parser.add_argument(
        "--embeddings",
        action="store_true",
        help="Check embedding model availability"
    )

    args = parser.parse_args()

    checker = LMStudioHealthChecker(args.url)

    # Watch mode
    if args.watch:
        watch_health(checker, args.interval, args.json)
        return 0

    # Test inference
    if args.test:
        result = checker.test_inference(args.model)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["success"]:
                print(f"Inference test: SUCCESS")
                print(f"Model: {result['model']}")
                print(f"Response: {result['response']}")
                print(f"Time: {result['inference_time_ms']}ms")
                if result.get("usage"):
                    print(f"Tokens: {result['usage']}")
            else:
                print(f"Inference test: FAILED")
                print(f"Error: {result['error']}")
                return 1
        return 0

    # Check embeddings
    if args.embeddings:
        result = checker.check_embedding_capability()
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["available"]:
                print(f"Embedding models available: {', '.join(result['models'])}")
            else:
                print("No embedding models loaded")
                if result.get("error"):
                    print(f"Error: {result['error']}")
        return 0

    # Get specific model details
    if args.model:
        result = checker.get_model_details(args.model)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if "error" in result:
                print(f"Error: {result['error']}")
                return 1
            print(f"Model: {result['id']}")
            print(f"Capabilities: {', '.join(result['capabilities']) or 'none listed'}")
            print(f"Owned by: {result['owned_by']}")
        return 0

    # Default: basic health check
    health = checker.check_health()

    if args.json:
        print(json.dumps(health.to_dict(), indent=2))
    else:
        if health.healthy:
            print(f"LM Studio is healthy")
            print(f"URL: {health.url}")
            print(f"Response time: {health.response_time_ms:.1f}ms")
            print(f"\nLoaded models ({len(health.models)}):")
            for model in health.models:
                caps = ", ".join(model.capabilities) if model.capabilities else "general"
                print(f"  - {model.id} [{caps}]")
        else:
            print(f"LM Studio is NOT healthy")
            print(f"URL: {health.url}")
            print(f"Error: {health.error}")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
