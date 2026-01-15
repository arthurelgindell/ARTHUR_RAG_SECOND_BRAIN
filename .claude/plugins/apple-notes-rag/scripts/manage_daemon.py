#!/usr/bin/env python3
"""
Manage Apple Notes RAG Sync Daemon (launchd)

Commands:
    install     Install and start the daemon
    uninstall   Stop and remove the daemon
    start       Start the daemon
    stop        Stop the daemon
    restart     Restart the daemon
    status      Show daemon status
    logs        Show recent logs
    run-now     Trigger immediate sync

Usage:
    python3 manage_daemon.py install
    python3 manage_daemon.py status
    python3 manage_daemon.py logs --tail 50
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Paths
PLIST_SOURCE = Path(__file__).parent.parent / "launchd" / "com.arthur.apple-notes-rag.plist"
PLIST_DEST = Path.home() / "Library" / "LaunchAgents" / "com.arthur.apple-notes-rag.plist"
LOG_DIR = Path.home() / ".apple-notes-rag" / "logs"
LABEL = "com.arthur.apple-notes-rag"


def run_cmd(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return result."""
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def is_installed() -> bool:
    """Check if plist is installed."""
    return PLIST_DEST.exists()


def is_running() -> bool:
    """Check if daemon is currently running."""
    result = run_cmd(["launchctl", "list"], check=False)
    return LABEL in result.stdout


def get_daemon_info() -> dict:
    """Get detailed daemon info from launchctl."""
    result = run_cmd(["launchctl", "list", LABEL], check=False)
    if result.returncode != 0:
        return {"loaded": False}

    info = {"loaded": True}
    for line in result.stdout.strip().split("\n"):
        if "=" in line:
            key, _, value = line.partition("=")
            info[key.strip().strip('"')] = value.strip().strip('";')

    return info


def cmd_install():
    """Install and start the daemon."""
    print("Installing Apple Notes RAG Sync Daemon...")

    # Check source plist exists
    if not PLIST_SOURCE.exists():
        print(f"Error: Plist not found at {PLIST_SOURCE}")
        return 1

    # Create LaunchAgents directory if needed
    PLIST_DEST.parent.mkdir(parents=True, exist_ok=True)

    # Create log directory
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Stop if already running
    if is_running():
        print("Stopping existing daemon...")
        run_cmd(["launchctl", "unload", str(PLIST_DEST)], check=False)

    # Copy plist
    shutil.copy2(PLIST_SOURCE, PLIST_DEST)
    print(f"Installed plist to {PLIST_DEST}")

    # Load the daemon
    result = run_cmd(["launchctl", "load", str(PLIST_DEST)], check=False)
    if result.returncode != 0:
        print(f"Warning: Failed to load daemon: {result.stderr}")
        return 1

    print("Daemon installed and loaded successfully!")
    print(f"\nSync will run every 10 minutes")
    print(f"Logs: {LOG_DIR}")
    print("\nTo check status: python3 manage_daemon.py status")
    print("To trigger now:   python3 manage_daemon.py run-now")

    return 0


def cmd_uninstall():
    """Stop and remove the daemon."""
    print("Uninstalling Apple Notes RAG Sync Daemon...")

    if is_running():
        print("Stopping daemon...")
        run_cmd(["launchctl", "unload", str(PLIST_DEST)], check=False)

    if PLIST_DEST.exists():
        PLIST_DEST.unlink()
        print(f"Removed {PLIST_DEST}")
    else:
        print("Plist not found (already uninstalled?)")

    print("Daemon uninstalled.")
    print(f"\nNote: Logs preserved at {LOG_DIR}")

    return 0


def cmd_start():
    """Start the daemon."""
    if not is_installed():
        print("Daemon not installed. Run 'install' first.")
        return 1

    if is_running():
        print("Daemon is already running.")
        return 0

    result = run_cmd(["launchctl", "load", str(PLIST_DEST)], check=False)
    if result.returncode != 0:
        print(f"Failed to start: {result.stderr}")
        return 1

    print("Daemon started.")
    return 0


def cmd_stop():
    """Stop the daemon."""
    if not is_installed():
        print("Daemon not installed.")
        return 1

    if not is_running():
        print("Daemon is not running.")
        return 0

    result = run_cmd(["launchctl", "unload", str(PLIST_DEST)], check=False)
    if result.returncode != 0:
        print(f"Failed to stop: {result.stderr}")
        return 1

    print("Daemon stopped.")
    return 0


def cmd_restart():
    """Restart the daemon."""
    cmd_stop()
    return cmd_start()


def cmd_status():
    """Show daemon status."""
    print("\n=== Apple Notes RAG Daemon Status ===\n")

    # Installation status
    print(f"Installed: {'Yes' if is_installed() else 'No'}")
    print(f"Running:   {'Yes' if is_running() else 'No'}")

    if is_installed():
        print(f"Plist:     {PLIST_DEST}")

    # Get launchctl info
    if is_running():
        info = get_daemon_info()
        if info.get("PID"):
            print(f"PID:       {info['PID']}")
        if info.get("LastExitStatus"):
            status = info["LastExitStatus"]
            print(f"Last Exit: {status} {'(OK)' if status == '0' else '(Error)'}")

    # Check LM Studio
    try:
        import requests
        resp = requests.get("http://localhost:1234/v1/models", timeout=2)
        lm_status = "Running" if resp.status_code == 200 else "Error"
    except Exception:
        lm_status = "Not available"
    print(f"\nLM Studio: {lm_status}")

    # Show sync state
    state_file = Path.home() / ".apple-notes-rag" / "sync_state.json"
    if state_file.exists():
        import json
        with open(state_file) as f:
            state = json.load(f)
        print(f"\nLast sync:    {state.get('last_sync', 'Never')}")
        print(f"Last success: {state.get('last_success', 'Never')}")
        print(f"Notes count:  {state.get('notes_count', 0)}")
        if state.get('consecutive_failures', 0) > 0:
            print(f"Failures:     {state['consecutive_failures']} consecutive")

    # Show recent log entries
    today_log = LOG_DIR / f"sync_{__import__('datetime').datetime.now().strftime('%Y-%m-%d')}.log"
    if today_log.exists():
        print(f"\nRecent activity ({today_log.name}):")
        with open(today_log) as f:
            lines = f.readlines()
            for line in lines[-5:]:
                print(f"  {line.rstrip()}")

    print()
    return 0


def cmd_logs(tail: int = 20, follow: bool = False):
    """Show daemon logs."""
    # Find most recent log file
    if not LOG_DIR.exists():
        print("No logs found.")
        return 1

    log_files = sorted(LOG_DIR.glob("sync_*.log"), reverse=True)
    if not log_files:
        print("No sync logs found.")
        return 1

    log_file = log_files[0]
    print(f"=== {log_file.name} ===\n")

    if follow:
        # Use tail -f
        subprocess.run(["tail", "-f", str(log_file)])
    else:
        # Show last N lines
        with open(log_file) as f:
            lines = f.readlines()
            for line in lines[-tail:]:
                print(line.rstrip())

    return 0


def cmd_run_now():
    """Trigger immediate sync."""
    print("Triggering immediate sync...")

    # Run the sync daemon directly
    sync_script = Path(__file__).parent / "sync_daemon.py"
    result = subprocess.run(
        [sys.executable, str(sync_script)],
        cwd=sync_script.parent
    )

    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Manage Apple Notes RAG Sync Daemon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  install     Install and start the daemon (runs every 10 minutes)
  uninstall   Stop and remove the daemon
  start       Start the daemon
  stop        Stop the daemon
  restart     Restart the daemon
  status      Show daemon status
  logs        Show recent logs
  run-now     Trigger immediate sync
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Install
    subparsers.add_parser("install", help="Install and start the daemon")

    # Uninstall
    subparsers.add_parser("uninstall", help="Stop and remove the daemon")

    # Start
    subparsers.add_parser("start", help="Start the daemon")

    # Stop
    subparsers.add_parser("stop", help="Stop the daemon")

    # Restart
    subparsers.add_parser("restart", help="Restart the daemon")

    # Status
    subparsers.add_parser("status", help="Show daemon status")

    # Logs
    logs_parser = subparsers.add_parser("logs", help="Show recent logs")
    logs_parser.add_argument("--tail", "-n", type=int, default=20, help="Number of lines")
    logs_parser.add_argument("--follow", "-f", action="store_true", help="Follow log output")

    # Run now
    subparsers.add_parser("run-now", help="Trigger immediate sync")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "install": cmd_install,
        "uninstall": cmd_uninstall,
        "start": cmd_start,
        "stop": cmd_stop,
        "restart": cmd_restart,
        "status": cmd_status,
        "logs": lambda: cmd_logs(args.tail, args.follow) if hasattr(args, 'tail') else cmd_logs(),
        "run-now": cmd_run_now,
    }

    return commands[args.command]()


if __name__ == "__main__":
    sys.exit(main())
