#!/usr/bin/env python3
"""
NotebookLM MCP Server Setup Script.

This script handles installation and authentication for the NotebookLM MCP server.

Usage:
    python setup.py              # Full setup (install + auth)
    python setup.py --check      # Check installation status only
    python setup.py --install    # Install only (skip auth)
    python setup.py --auth       # Auth only (skip install)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


# Configuration
AUTH_FILE = Path.home() / ".notebooklm-mcp" / "auth.json"
PACKAGE_NAME = "notebooklm-mcp-server"


@dataclass
class SetupStatus:
    """Setup status information."""
    package_installed: bool = False
    auth_configured: bool = False
    auth_file_exists: bool = False
    uv_available: bool = False
    pip_available: bool = False
    errors: list[str] | None = None

    def to_dict(self) -> dict:
        return {
            "package_installed": self.package_installed,
            "auth_configured": self.auth_configured,
            "auth_file_exists": self.auth_file_exists,
            "uv_available": self.uv_available,
            "pip_available": self.pip_available,
            "errors": self.errors
        }


def check_command_exists(cmd: str) -> bool:
    """Check if a command exists in PATH."""
    return shutil.which(cmd) is not None


def check_package_installed() -> bool:
    """Check if notebooklm-mcp-server is installed."""
    # Check if the command exists
    if check_command_exists("notebooklm-mcp"):
        return True

    # Also check via pip
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", PACKAGE_NAME],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except Exception:
        return False


def check_auth_status() -> tuple[bool, dict | None]:
    """Check authentication status."""
    if not AUTH_FILE.exists():
        return False, None

    try:
        with open(AUTH_FILE) as f:
            auth_data = json.load(f)

        # Check if we have required fields
        has_cookies = bool(auth_data.get("cookies"))
        has_tokens = bool(auth_data.get("tokens") or auth_data.get("csrf_token"))

        return has_cookies or has_tokens, auth_data
    except (json.JSONDecodeError, IOError):
        return False, None


def get_setup_status() -> SetupStatus:
    """Get current setup status."""
    status = SetupStatus()

    status.uv_available = check_command_exists("uv")
    status.pip_available = check_command_exists("pip") or check_command_exists("pip3")
    status.package_installed = check_package_installed()
    status.auth_file_exists = AUTH_FILE.exists()
    status.auth_configured, _ = check_auth_status()

    return status


def install_package(use_uv: bool = True) -> bool:
    """Install the notebooklm-mcp-server package."""
    print(f"\nInstalling {PACKAGE_NAME}...")

    if use_uv and check_command_exists("uv"):
        print("Using uv for installation...")
        cmd = ["uv", "tool", "install", PACKAGE_NAME]
    else:
        print("Using pip for installation...")
        cmd = [sys.executable, "-m", "pip", "install", PACKAGE_NAME]

    try:
        result = subprocess.run(
            cmd,
            capture_output=False,
            text=True,
            timeout=300
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("Installation timed out")
        return False
    except Exception as e:
        print(f"Installation failed: {e}")
        return False


def run_authentication(auto_mode: bool = True) -> bool:
    """Run the authentication process."""
    print("\nStarting authentication...")

    if not check_command_exists("notebooklm-mcp-auth"):
        print("Error: notebooklm-mcp-auth command not found")
        print("Make sure the package is installed correctly")
        return False

    cmd = ["notebooklm-mcp-auth"]
    if not auto_mode:
        cmd.append("--file")

    print("\nThis will open a browser window for Google authentication.")
    print("Please log in to your Google account when prompted.\n")

    try:
        result = subprocess.run(
            cmd,
            timeout=600  # 10 minutes for auth
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("Authentication timed out")
        return False
    except KeyboardInterrupt:
        print("\nAuthentication cancelled")
        return False
    except Exception as e:
        print(f"Authentication failed: {e}")
        return False


def print_status(status: SetupStatus) -> None:
    """Print current setup status."""
    print("\n" + "=" * 50)
    print("NotebookLM MCP Setup Status")
    print("=" * 50)

    def status_icon(ok: bool) -> str:
        return "[OK]" if ok else "[  ]"

    print(f"\n{status_icon(status.uv_available)} uv available")
    print(f"{status_icon(status.pip_available)} pip available")
    print(f"{status_icon(status.package_installed)} Package installed ({PACKAGE_NAME})")
    print(f"{status_icon(status.auth_file_exists)} Auth file exists ({AUTH_FILE})")
    print(f"{status_icon(status.auth_configured)} Authentication configured")

    if status.package_installed and status.auth_configured:
        print("\n[OK] Setup complete! The MCP server is ready to use.")
        print("\nNext steps:")
        print("  1. Restart Claude Code to load the MCP server")
        print("  2. Try: 'List my NotebookLM notebooks'")
    elif status.package_installed and not status.auth_configured:
        print("\n[!!] Package installed but authentication needed.")
        print("\nRun: python setup.py --auth")
    elif not status.package_installed:
        print("\n[!!] Package not installed.")
        print("\nRun: python setup.py --install")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Setup NotebookLM MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s              # Full setup (install + auth)
  %(prog)s --check      # Check status only
  %(prog)s --install    # Install package only
  %(prog)s --auth       # Run authentication only
  %(prog)s --json       # Output status as JSON
        """
    )

    parser.add_argument(
        "--check",
        action="store_true",
        help="Check installation status only"
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install package only (skip auth)"
    )
    parser.add_argument(
        "--auth",
        action="store_true",
        help="Run authentication only"
    )
    parser.add_argument(
        "--manual-auth",
        action="store_true",
        help="Use manual cookie extraction instead of auto mode"
    )
    parser.add_argument(
        "--use-pip",
        action="store_true",
        help="Use pip instead of uv for installation"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output status as JSON"
    )

    args = parser.parse_args()

    # Get current status
    status = get_setup_status()

    # JSON output mode
    if args.json:
        print(json.dumps(status.to_dict(), indent=2))
        return 0 if status.package_installed and status.auth_configured else 1

    # Check only mode
    if args.check:
        print_status(status)
        return 0 if status.package_installed and status.auth_configured else 1

    # Install only mode
    if args.install:
        if status.package_installed:
            print(f"{PACKAGE_NAME} is already installed")
            return 0

        success = install_package(use_uv=not args.use_pip)
        if success:
            print("\nInstallation successful!")
            print("\nNext: Run 'python setup.py --auth' to authenticate")
            return 0
        else:
            print("\nInstallation failed")
            return 1

    # Auth only mode
    if args.auth:
        success = run_authentication(auto_mode=not args.manual_auth)
        if success:
            print("\nAuthentication successful!")
            status = get_setup_status()
            print_status(status)
            return 0
        else:
            print("\nAuthentication failed")
            return 1

    # Full setup mode
    print("=" * 50)
    print("NotebookLM MCP Server Setup")
    print("=" * 50)

    # Step 1: Install if needed
    if not status.package_installed:
        print("\nStep 1: Installing package...")
        if not install_package(use_uv=not args.use_pip):
            print("\nInstallation failed. Please try manually:")
            print(f"  uv tool install {PACKAGE_NAME}")
            print("  or")
            print(f"  pip install {PACKAGE_NAME}")
            return 1
        print("Package installed successfully!")
    else:
        print("\nStep 1: Package already installed")

    # Step 2: Authenticate if needed
    if not status.auth_configured:
        print("\nStep 2: Authentication required...")
        if not run_authentication(auto_mode=not args.manual_auth):
            print("\nAuthentication failed. Please try manually:")
            print("  notebooklm-mcp-auth")
            return 1
        print("Authentication successful!")
    else:
        print("\nStep 2: Already authenticated")

    # Final status
    status = get_setup_status()
    print_status(status)

    return 0 if status.package_installed and status.auth_configured else 1


if __name__ == "__main__":
    sys.exit(main())
