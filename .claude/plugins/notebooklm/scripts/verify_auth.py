#!/usr/bin/env python3
"""
Verify NotebookLM MCP authentication status.

This script checks if authentication is configured correctly and
provides information about token status.

Usage:
    python verify_auth.py           # Check auth status
    python verify_auth.py --json    # Output as JSON
    python verify_auth.py --test    # Test API connection
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


# Configuration
AUTH_FILE = Path.home() / ".notebooklm-mcp" / "auth.json"
AUTH_DIR = Path.home() / ".notebooklm-mcp"


@dataclass
class AuthStatus:
    """Authentication status information."""
    auth_file_exists: bool = False
    auth_valid: bool = False
    has_cookies: bool = False
    has_csrf_token: bool = False
    cookie_count: int = 0
    last_modified: str | None = None
    expires_estimate: str | None = None
    errors: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "auth_file_exists": self.auth_file_exists,
            "auth_valid": self.auth_valid,
            "has_cookies": self.has_cookies,
            "has_csrf_token": self.has_csrf_token,
            "cookie_count": self.cookie_count,
            "last_modified": self.last_modified,
            "expires_estimate": self.expires_estimate,
            "errors": self.errors
        }


def get_auth_status() -> AuthStatus:
    """Check authentication status."""
    status = AuthStatus()
    errors = []

    # Check if auth directory exists
    if not AUTH_DIR.exists():
        errors.append(f"Auth directory not found: {AUTH_DIR}")
        status.errors = errors
        return status

    # Check if auth file exists
    if not AUTH_FILE.exists():
        errors.append(f"Auth file not found: {AUTH_FILE}")
        status.errors = errors
        return status

    status.auth_file_exists = True

    # Get file modification time
    try:
        mtime = AUTH_FILE.stat().st_mtime
        mod_time = datetime.fromtimestamp(mtime)
        status.last_modified = mod_time.isoformat()

        # Estimate expiration (cookies typically last 2-4 weeks)
        from datetime import timedelta
        expires = mod_time + timedelta(weeks=2)
        status.expires_estimate = expires.isoformat()

        # Check if likely expired
        if datetime.now() > expires:
            errors.append("Authentication may have expired (>2 weeks old)")
    except Exception as e:
        errors.append(f"Could not read file stats: {e}")

    # Parse auth file
    try:
        with open(AUTH_FILE) as f:
            auth_data = json.load(f)

        # Check for cookies
        cookies = auth_data.get("cookies", [])
        if cookies:
            status.has_cookies = True
            status.cookie_count = len(cookies) if isinstance(cookies, list) else 1

        # Check for CSRF token
        if auth_data.get("csrf_token") or auth_data.get("csrfToken"):
            status.has_csrf_token = True

        # Determine if auth is valid
        status.auth_valid = status.has_cookies

        if not status.has_cookies:
            errors.append("No cookies found in auth file")

    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in auth file: {e}")
    except IOError as e:
        errors.append(f"Could not read auth file: {e}")

    if errors:
        status.errors = errors

    return status


def test_mcp_connection() -> dict[str, Any]:
    """Test the MCP server connection."""
    result = {
        "success": False,
        "mcp_command_exists": False,
        "error": None
    }

    # Check if command exists
    import shutil
    if not shutil.which("notebooklm-mcp"):
        result["error"] = "notebooklm-mcp command not found"
        return result

    result["mcp_command_exists"] = True

    # Try to start the MCP server briefly
    try:
        proc = subprocess.Popen(
            ["notebooklm-mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Send a simple initialize request
        init_request = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"}
            }
        }) + "\n"

        try:
            stdout, stderr = proc.communicate(input=init_request, timeout=10)

            if stdout:
                # Try to parse response
                for line in stdout.strip().split('\n'):
                    if line:
                        try:
                            response = json.loads(line)
                            if "result" in response:
                                result["success"] = True
                                result["server_info"] = response.get("result", {}).get("serverInfo")
                            elif "error" in response:
                                result["error"] = response["error"].get("message", "Unknown error")
                        except json.JSONDecodeError:
                            pass

            if stderr and not result["success"]:
                result["error"] = stderr[:200]

        except subprocess.TimeoutExpired:
            proc.kill()
            result["error"] = "Connection test timed out"

    except Exception as e:
        result["error"] = str(e)

    return result


def print_status(status: AuthStatus) -> None:
    """Print authentication status."""
    print("\n" + "=" * 50)
    print("NotebookLM MCP Authentication Status")
    print("=" * 50)

    def icon(ok: bool) -> str:
        return "[OK]" if ok else "[  ]"

    print(f"\n{icon(status.auth_file_exists)} Auth file exists")
    print(f"   Path: {AUTH_FILE}")

    if status.auth_file_exists:
        print(f"\n{icon(status.has_cookies)} Cookies present ({status.cookie_count} cookies)")
        print(f"{icon(status.has_csrf_token)} CSRF token present")

        if status.last_modified:
            print(f"\n   Last modified: {status.last_modified}")
        if status.expires_estimate:
            print(f"   Estimated expiry: {status.expires_estimate}")

    print(f"\n{icon(status.auth_valid)} Authentication valid")

    if status.errors:
        print("\nWarnings/Errors:")
        for error in status.errors:
            print(f"   - {error}")

    if status.auth_valid:
        print("\n[OK] Authentication is configured correctly.")
    else:
        print("\n[!!] Authentication needs to be configured.")
        print("\nTo authenticate, run:")
        print("   notebooklm-mcp-auth")
        print("\nOr use the setup script:")
        print("   python setup.py --auth")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify NotebookLM MCP authentication status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s              # Check auth status
  %(prog)s --json       # Output as JSON
  %(prog)s --test       # Test MCP server connection
  %(prog)s --reauth     # Show re-authentication instructions
        """
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output status as JSON"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test MCP server connection"
    )
    parser.add_argument(
        "--reauth",
        action="store_true",
        help="Show re-authentication instructions"
    )

    args = parser.parse_args()

    # Get auth status
    status = get_auth_status()

    # Re-auth instructions
    if args.reauth:
        print("\nRe-authentication Instructions")
        print("=" * 40)
        print("\nMethod 1: Auto mode (recommended)")
        print("   notebooklm-mcp-auth")
        print("   - Opens Chrome for Google login")
        print("   - Automatically extracts cookies")
        print("\nMethod 2: Manual mode")
        print("   notebooklm-mcp-auth --file")
        print("   - Extract cookies manually from DevTools")
        print("   - Follow the prompts")
        print("\nMethod 3: Setup script")
        print("   python setup.py --auth")
        return 0

    # Test MCP connection
    if args.test:
        print("Testing MCP server connection...")
        test_result = test_mcp_connection()

        if args.json:
            output = {
                "auth_status": status.to_dict(),
                "connection_test": test_result
            }
            print(json.dumps(output, indent=2))
        else:
            print_status(status)
            print("\n" + "-" * 50)
            print("Connection Test Results")
            print("-" * 50)

            if test_result["success"]:
                print("\n[OK] MCP server connection successful!")
                if test_result.get("server_info"):
                    print(f"   Server: {test_result['server_info']}")
            else:
                print("\n[!!] MCP server connection failed")
                if test_result.get("error"):
                    print(f"   Error: {test_result['error']}")

        return 0 if test_result["success"] else 1

    # JSON output
    if args.json:
        print(json.dumps(status.to_dict(), indent=2))
        return 0 if status.auth_valid else 1

    # Default: print status
    print_status(status)
    return 0 if status.auth_valid else 1


if __name__ == "__main__":
    sys.exit(main())
