#!/usr/bin/env python3
"""
Service Status Checker - For UserPromptSubmit Hook Injection

This script checks the health of all ARTHUR_RAG services and outputs
a compact status line suitable for context injection.

Usage:
    python service_status.py              # Human-readable output
    python service_status.py --compact    # Single-line for hook injection
    python service_status.py --json       # Full JSON output

Exit codes:
    0 - All services healthy
    1 - Some services degraded
    2 - Critical services down
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# Service configuration
LM_STUDIO_URL = os.environ.get("LM_STUDIO_URL", "http://localhost:1234")
NOTEBOOKLM_AUTH_PATH = Path.home() / ".notebooklm-mcp" / "auth.json"


def http_get(url: str, timeout: int = 3) -> tuple[dict | None, str | None]:
    """Quick HTTP GET with timeout."""
    request = Request(url)
    request.add_header("Accept", "application/json")

    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}, None
    except HTTPError as e:
        return None, f"HTTP {e.code}"
    except URLError as e:
        return None, str(e.reason)[:30]
    except Exception as e:
        return None, str(e)[:30]


def check_lm_studio() -> dict[str, Any]:
    """Check LM Studio health and loaded models."""
    result, error = http_get(f"{LM_STUDIO_URL}/v1/models")

    if error:
        return {
            "service": "lm_studio",
            "status": "down",
            "error": error,
            "models": []
        }

    models = result.get("data", [])
    model_ids = [m.get("id", "?") for m in models]

    # Check for chat and embedding models
    has_chat = any("embed" not in m.lower() for m in model_ids)
    has_embedding = any("embed" in m.lower() for m in model_ids)

    return {
        "service": "lm_studio",
        "status": "healthy" if models else "no_models",
        "models": model_ids[:3],  # First 3 models
        "model_count": len(models),
        "has_chat": has_chat,
        "has_embedding": has_embedding
    }


def check_notebooklm_auth() -> dict[str, Any]:
    """Check NotebookLM authentication status."""
    if not NOTEBOOKLM_AUTH_PATH.exists():
        return {
            "service": "notebooklm",
            "status": "no_auth",
            "error": "Auth file not found"
        }

    try:
        with open(NOTEBOOKLM_AUTH_PATH) as f:
            auth_data = json.load(f)

        # Check if cookies exist
        cookies = auth_data.get("cookies", "")
        if not cookies:
            return {
                "service": "notebooklm",
                "status": "invalid_auth",
                "error": "No cookies in auth file"
            }

        # Check expiry if available
        expires_at = auth_data.get("expires_at")
        if expires_at:
            try:
                from datetime import datetime
                exp_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                now = datetime.now(exp_time.tzinfo)
                days_left = (exp_time - now).days

                if days_left < 0:
                    return {
                        "service": "notebooklm",
                        "status": "expired",
                        "days_expired": abs(days_left)
                    }
                elif days_left < 3:
                    return {
                        "service": "notebooklm",
                        "status": "expiring_soon",
                        "days_left": days_left
                    }
            except Exception:
                pass

        return {
            "service": "notebooklm",
            "status": "authenticated",
            "auth_file": str(NOTEBOOKLM_AUTH_PATH)
        }

    except json.JSONDecodeError:
        return {
            "service": "notebooklm",
            "status": "invalid_auth",
            "error": "Corrupt auth file"
        }
    except Exception as e:
        return {
            "service": "notebooklm",
            "status": "error",
            "error": str(e)[:50]
        }


def check_all_services() -> dict[str, Any]:
    """Check all services and return combined status."""
    lm_status = check_lm_studio()
    nb_status = check_notebooklm_auth()

    # Determine overall health
    critical_down = lm_status["status"] == "down"
    any_issues = (
        lm_status["status"] not in ("healthy",) or
        nb_status["status"] not in ("authenticated",)
    )

    if critical_down:
        overall = "critical"
    elif any_issues:
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "overall": overall,
        "timestamp": time.strftime("%H:%M:%S"),
        "services": {
            "lm_studio": lm_status,
            "notebooklm": nb_status
        }
    }


def format_compact(status: dict[str, Any]) -> str:
    """Format status as compact single line for hook injection."""
    parts = []

    lm = status["services"]["lm_studio"]
    if lm["status"] == "healthy":
        model_count = lm.get("model_count", 0)
        parts.append(f"LM:{model_count}m")
    elif lm["status"] == "no_models":
        parts.append("LM:no-models")
    else:
        parts.append("LM:DOWN")

    nb = status["services"]["notebooklm"]
    if nb["status"] == "authenticated":
        parts.append("NB:OK")
    elif nb["status"] == "expiring_soon":
        parts.append(f"NB:exp-{nb.get('days_left', '?')}d")
    elif nb["status"] == "expired":
        parts.append("NB:EXPIRED")
    else:
        parts.append("NB:NO-AUTH")

    return f"[{' | '.join(parts)}]"


def format_human(status: dict[str, Any]) -> str:
    """Format status for human reading."""
    lines = [
        f"ARTHUR_RAG Services - {status['timestamp']}",
        f"Overall: {status['overall'].upper()}",
        ""
    ]

    lm = status["services"]["lm_studio"]
    lines.append(f"LM Studio: {lm['status']}")
    if lm["status"] == "healthy":
        lines.append(f"  Models ({lm.get('model_count', 0)}): {', '.join(lm.get('models', []))}")
        lines.append(f"  Chat: {'Yes' if lm.get('has_chat') else 'No'} | Embeddings: {'Yes' if lm.get('has_embedding') else 'No'}")
    elif lm.get("error"):
        lines.append(f"  Error: {lm['error']}")

    lines.append("")

    nb = status["services"]["notebooklm"]
    lines.append(f"NotebookLM: {nb['status']}")
    if nb["status"] == "authenticated":
        lines.append("  Auth: Valid")
    elif nb["status"] == "expiring_soon":
        lines.append(f"  Warning: Expires in {nb.get('days_left', '?')} days")
    elif nb.get("error"):
        lines.append(f"  Error: {nb['error']}")

    return "\n".join(lines)


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Check ARTHUR_RAG service status"
    )
    parser.add_argument(
        "--compact", "-c",
        action="store_true",
        help="Output compact single line (for hook injection)"
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output full JSON"
    )

    args = parser.parse_args()

    status = check_all_services()

    if args.json:
        print(json.dumps(status, indent=2))
    elif args.compact:
        print(format_compact(status))
    else:
        print(format_human(status))

    # Exit codes
    if status["overall"] == "critical":
        return 2
    elif status["overall"] == "degraded":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
