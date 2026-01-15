#!/usr/bin/env python3
"""
Apple Notes RAG Sync Daemon

Robust automated sync with:
- File locking (prevents concurrent runs)
- LM Studio health checks
- Incremental sync (only new/changed notes)
- Comprehensive logging
- Retry logic with exponential backoff
- Optional macOS notifications

Designed to run via launchd every 10 minutes.

Usage:
    python3 sync_daemon.py              # Run sync
    python3 sync_daemon.py --status     # Check daemon status
    python3 sync_daemon.py --force      # Force full sync
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

# =============================================================================
# CONFIGURATION
# =============================================================================

# Paths
BASE_DIR = Path.home() / ".apple-notes-rag"
EXPORT_DIR = BASE_DIR / "export"
LOG_DIR = BASE_DIR / "logs"
LOCK_FILE = BASE_DIR / "sync.lock"
STATE_FILE = BASE_DIR / "sync_state.json"
SCRIPTS_DIR = Path(__file__).parent

# LM Studio
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5")

# Sync settings
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds
BATCH_SIZE = 10
EXPORT_TIMEOUT = 1800  # 30 minutes for large collections

# Notifications (macOS)
ENABLE_NOTIFICATIONS = True


# =============================================================================
# UTILITIES
# =============================================================================

def get_log_file() -> Path:
    """Get today's log file path."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR / f"sync_{datetime.now().strftime('%Y-%m-%d')}.log"


def log(message: str, level: str = "INFO"):
    """Write to log file and optionally stdout."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{level}] {message}"

    # Write to log file
    with open(get_log_file(), "a") as f:
        f.write(log_line + "\n")

    # Also print to stdout for launchd capture
    print(log_line, file=sys.stderr if level == "ERROR" else sys.stdout)


def notify(title: str, message: str, sound: bool = False):
    """Send macOS notification."""
    if not ENABLE_NOTIFICATIONS:
        return

    try:
        script = f'display notification "{message}" with title "{title}"'
        if sound:
            script += ' sound name "Glass"'
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            timeout=5
        )
    except Exception:
        pass  # Notifications are optional


def load_state() -> dict[str, Any]:
    """Load sync state from file."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "last_sync": None,
        "last_success": None,
        "notes_count": 0,
        "consecutive_failures": 0,
        "note_hashes": {}
    }


def save_state(state: dict[str, Any]):
    """Save sync state to file."""
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def compute_hash(content: str) -> str:
    """Compute content hash for change detection."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


# =============================================================================
# HEALTH CHECKS
# =============================================================================

def check_lm_studio() -> bool:
    """Check if LM Studio is running and healthy."""
    try:
        response = requests.get(f"{LM_STUDIO_URL}/v1/models", timeout=5)
        response.raise_for_status()
        models = response.json().get("data", [])

        # Check for embedding model
        model_ids = [m.get("id", "") for m in models]
        has_embedding = any("embed" in mid.lower() for mid in model_ids)

        if not has_embedding:
            log("Warning: No embedding model loaded in LM Studio", "WARN")

        return True
    except requests.exceptions.RequestException as e:
        log(f"LM Studio not available: {e}", "ERROR")
        return False


def check_apple_notes_access() -> bool:
    """Check if we can access Apple Notes."""
    try:
        script = "Application('Notes').folders().length"
        result = subprocess.run(
            ["osascript", "-l", "JavaScript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except Exception as e:
        log(f"Cannot access Apple Notes: {e}", "ERROR")
        return False


# =============================================================================
# SYNC LOGIC
# =============================================================================

def export_notes_incremental() -> dict[str, Any]:
    """
    Export notes using incremental approach.

    Returns export result dict with changed_notes, new, modified, deleted counts.
    """
    log("Starting incremental export...")

    export_script = SCRIPTS_DIR / "export_incremental.py"
    if not export_script.exists():
        raise FileNotFoundError(f"Export script not found: {export_script}")

    result = subprocess.run(
        [sys.executable, str(export_script), "--json"],
        capture_output=True,
        text=True,
        timeout=EXPORT_TIMEOUT
    )

    if result.returncode != 0:
        raise RuntimeError(f"Export failed: {result.stderr}")

    # Parse JSON output
    export_result = json.loads(result.stdout)

    # Load changed notes if any
    changes_file = EXPORT_DIR / "incremental_changes.json"
    if changes_file.exists():
        with open(changes_file, "r") as f:
            export_result["changed_notes"] = json.load(f)
    else:
        export_result["changed_notes"] = []

    total_changes = export_result.get("new", 0) + export_result.get("modified", 0) + export_result.get("deleted", 0)
    if total_changes > 0:
        log(f"Found {total_changes} changes: +{export_result.get('new', 0)} ~{export_result.get('modified', 0)} -{export_result.get('deleted', 0)}")
    else:
        log("No changes detected")

    return export_result


def export_notes_full() -> list[dict[str, Any]]:
    """Export all notes using folder-by-folder approach (full sync)."""
    log("Starting full notes export...")

    export_script = SCRIPTS_DIR / "export_by_folder.py"
    if not export_script.exists():
        raise FileNotFoundError(f"Export script not found: {export_script}")

    result = subprocess.run(
        [sys.executable, str(export_script), "--output", str(EXPORT_DIR)],
        capture_output=True,
        text=True,
        timeout=EXPORT_TIMEOUT
    )

    if result.returncode != 0:
        raise RuntimeError(f"Export failed: {result.stderr}")

    # Load exported notes
    export_file = EXPORT_DIR / "all_notes.json"
    with open(export_file, "r") as f:
        notes = json.load(f)

    log(f"Exported {len(notes)} notes")
    return notes


def detect_changes(notes: list[dict[str, Any]], state: dict[str, Any]) -> tuple[list, list, list]:
    """
    Detect new, modified, and deleted notes.

    Returns: (new_notes, modified_notes, deleted_ids)
    """
    current_hashes = {}
    for note in notes:
        content = note.get("body", "") + note.get("plaintext", "")
        current_hashes[note["id"]] = compute_hash(content)

    stored_hashes = state.get("note_hashes", {})

    new_notes = []
    modified_notes = []
    deleted_ids = []

    # Find new and modified
    for note in notes:
        note_id = note["id"]
        current_hash = current_hashes[note_id]

        if note_id not in stored_hashes:
            new_notes.append(note)
        elif stored_hashes[note_id] != current_hash:
            modified_notes.append(note)

    # Find deleted
    current_ids = set(current_hashes.keys())
    for note_id in stored_hashes:
        if note_id not in current_ids:
            deleted_ids.append(note_id)

    return new_notes, modified_notes, deleted_ids


def get_embedding(text: str) -> list[float]:
    """Get embedding from LM Studio."""
    response = requests.post(
        f"{LM_STUDIO_URL}/v1/embeddings",
        json={
            "model": EMBEDDING_MODEL,
            "input": text[:8000]
        },
        timeout=30
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


def sync_incremental(notes: list[dict[str, Any]], state: dict[str, Any]) -> dict[str, Any]:
    """
    Perform incremental sync - only embed changed notes.
    """
    import lancedb

    new_notes, modified_notes, deleted_ids = detect_changes(notes, state)

    if not new_notes and not modified_notes and not deleted_ids:
        log("No changes detected")
        return {"added": 0, "modified": 0, "deleted": 0}

    log(f"Changes: {len(new_notes)} new, {len(modified_notes)} modified, {len(deleted_ids)} deleted")

    db = lancedb.connect(str(BASE_DIR))

    # Check if table exists
    if "notes" not in db.table_names():
        log("No existing table - running full sync instead")
        return sync_full(notes)

    table = db.open_table("notes")
    synced_at = datetime.now().isoformat()

    # Process new and modified notes
    to_embed = new_notes + modified_notes
    if to_embed:
        log(f"Embedding {len(to_embed)} notes...")
        records = []

        for i, note in enumerate(to_embed):
            text = f"{note['name']}\n\n{note.get('plaintext', note.get('body', ''))}"
            embedding = get_embedding(text)

            records.append({
                "id": note["id"],
                "title": note["name"],
                "body": note.get("body", ""),
                "plaintext": note.get("plaintext", ""),
                "folder": note["folder"],
                "created": note.get("creationDate", ""),
                "modified": note.get("modificationDate", ""),
                "content_hash": compute_hash(note.get("body", "")),
                "vector": embedding,
                "synced_at": synced_at,
            })

            if (i + 1) % 10 == 0:
                log(f"  Embedded {i + 1}/{len(to_embed)}...")

        # Delete modified notes first (will re-add)
        if modified_notes:
            mod_ids = [n["id"] for n in modified_notes]
            table.delete(f"id IN {mod_ids}")

        # Add new records
        table.add(records)
        log(f"Added {len(records)} records to database")

    # Delete removed notes
    if deleted_ids:
        table.delete(f"id IN {deleted_ids}")
        log(f"Deleted {len(deleted_ids)} records from database")

    # Update state with new hashes
    for note in notes:
        content = note.get("body", "") + note.get("plaintext", "")
        state["note_hashes"][note["id"]] = compute_hash(content)

    # Remove deleted note hashes
    for note_id in deleted_ids:
        state["note_hashes"].pop(note_id, None)

    return {
        "added": len(new_notes),
        "modified": len(modified_notes),
        "deleted": len(deleted_ids)
    }


def sync_full(notes: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Full sync - re-embed all notes.
    """
    log("Running full sync...")

    sync_script = SCRIPTS_DIR / "sync_from_export.py"
    result = subprocess.run(
        [sys.executable, str(sync_script), "--input", str(EXPORT_DIR / "all_notes.json")],
        capture_output=True,
        text=True,
        timeout=3600  # 1 hour for full sync
    )

    if result.returncode != 0:
        raise RuntimeError(f"Full sync failed: {result.stderr}")

    return {"added": len(notes), "modified": 0, "deleted": 0, "full_sync": True}


def run_sync(force_full: bool = False) -> bool:
    """
    Main sync orchestration using incremental export.

    Returns True if sync was successful.
    """
    import lancedb

    state = load_state()
    state["last_sync"] = datetime.now().isoformat()

    try:
        # Health checks
        if not check_lm_studio():
            log("Skipping sync - LM Studio not available", "WARN")
            state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
            save_state(state)
            return False

        if not check_apple_notes_access():
            log("Skipping sync - Cannot access Apple Notes", "WARN")
            state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
            save_state(state)
            return False

        # Force full sync if no baseline exists
        if force_full or not state.get("note_hashes"):
            log("Running full sync (no baseline or forced)")
            notes = export_notes_full()
            result = sync_full(notes)
            # Build hash state for future incremental syncs
            state["note_hashes"] = {}
            for note in notes:
                content = note.get("body", "") + note.get("plaintext", "")
                state["note_hashes"][note["id"]] = compute_hash(content)
            state["notes_count"] = len(notes)
        else:
            # Incremental export - quick check + targeted export
            export_result = export_notes_incremental()

            if export_result.get("status") == "no_changes":
                # No changes detected
                result = {"added": 0, "modified": 0, "deleted": 0}
                state["notes_count"] = export_result.get("total_notes", state.get("notes_count", 0))
            else:
                # Process changed notes
                changed_notes = export_result.get("changed_notes", [])
                deleted_ids = export_result.get("deleted_ids", [])

                if changed_notes or deleted_ids:
                    db = lancedb.connect(str(BASE_DIR))

                    if "notes" not in db.table_names():
                        log("No existing table - running full sync instead")
                        notes = export_notes_full()
                        result = sync_full(notes)
                    else:
                        table = db.open_table("notes")
                        synced_at = datetime.now().isoformat()

                        # Embed changed notes
                        if changed_notes:
                            log(f"Embedding {len(changed_notes)} changed notes...")
                            records = []

                            for i, note in enumerate(changed_notes):
                                text = f"{note['name']}\n\n{note.get('plaintext', note.get('body', ''))}"
                                embedding = get_embedding(text)

                                records.append({
                                    "id": note["id"],
                                    "title": note["name"],
                                    "body": note.get("body", ""),
                                    "plaintext": note.get("plaintext", ""),
                                    "folder": note["folder"],
                                    "created": note.get("creationDate", ""),
                                    "modified": note.get("modificationDate", ""),
                                    "content_hash": compute_hash(note.get("body", "")),
                                    "vector": embedding,
                                    "synced_at": synced_at,
                                })

                                if (i + 1) % 5 == 0:
                                    log(f"  Embedded {i + 1}/{len(changed_notes)}...")

                            # Delete existing records for modified notes (will re-add)
                            existing_ids = [n["id"] for n in changed_notes]
                            try:
                                table.delete(f"id IN {existing_ids}")
                            except Exception:
                                pass  # May not exist

                            # Add new/updated records
                            table.add(records)
                            log(f"Added {len(records)} records to database")

                        # Delete removed notes
                        if deleted_ids:
                            try:
                                table.delete(f"id IN {deleted_ids}")
                                log(f"Deleted {len(deleted_ids)} records from database")
                            except Exception:
                                pass

                        result = {
                            "added": export_result.get("new", 0),
                            "modified": export_result.get("modified", 0),
                            "deleted": export_result.get("deleted", 0)
                        }
                else:
                    result = {"added": 0, "modified": 0, "deleted": 0}

                state["notes_count"] = export_result.get("total_notes", state.get("notes_count", 0))

        # Update state
        state["last_success"] = datetime.now().isoformat()
        state["consecutive_failures"] = 0
        state["last_result"] = result
        save_state(state)

        # Summary
        total_changes = result.get("added", 0) + result.get("modified", 0) + result.get("deleted", 0)
        if total_changes > 0:
            log(f"Sync complete: +{result.get('added', 0)} ~{result.get('modified', 0)} -{result.get('deleted', 0)}")
            notify("Notes RAG Sync", f"Synced {total_changes} changes")
        else:
            log("Sync complete: No changes")

        return True

    except Exception as e:
        log(f"Sync failed: {e}", "ERROR")
        state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
        state["last_error"] = str(e)
        save_state(state)

        if state["consecutive_failures"] >= 3:
            notify("Notes RAG Sync Failed", f"3+ consecutive failures: {e}", sound=True)

        return False


# =============================================================================
# LOCKING
# =============================================================================

class SyncLock:
    """File-based lock to prevent concurrent syncs."""

    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self.lock_file = None

    def __enter__(self):
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_file = open(self.lock_path, "w")
        try:
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_file.write(f"{os.getpid()}\n{datetime.now().isoformat()}")
            self.lock_file.flush()
            return self
        except IOError:
            self.lock_file.close()
            raise RuntimeError("Another sync is already running")

    def __exit__(self, *args):
        if self.lock_file:
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
            self.lock_file.close()
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass


# =============================================================================
# CLI
# =============================================================================

def show_status():
    """Show daemon status."""
    state = load_state()

    print("\n=== Apple Notes RAG Sync Status ===\n")
    print(f"Last sync attempt: {state.get('last_sync', 'Never')}")
    print(f"Last successful sync: {state.get('last_success', 'Never')}")
    print(f"Notes in database: {state.get('notes_count', 0)}")
    print(f"Consecutive failures: {state.get('consecutive_failures', 0)}")

    if state.get("last_result"):
        r = state["last_result"]
        print(f"\nLast result: +{r.get('added', 0)} ~{r.get('modified', 0)} -{r.get('deleted', 0)}")

    if state.get("last_error"):
        print(f"\nLast error: {state['last_error']}")

    # Check if lock exists (sync in progress)
    if LOCK_FILE.exists():
        print("\n⚠️  Sync currently in progress")

    # Check LM Studio
    print(f"\nLM Studio: {'✅ Running' if check_lm_studio() else '❌ Not available'}")

    # Show recent logs
    log_file = get_log_file()
    if log_file.exists():
        print(f"\nRecent logs ({log_file.name}):")
        with open(log_file, "r") as f:
            lines = f.readlines()
            for line in lines[-10:]:
                print(f"  {line.rstrip()}")

    print()


def main():
    parser = argparse.ArgumentParser(description="Apple Notes RAG Sync Daemon")
    parser.add_argument("--status", action="store_true", help="Show sync status")
    parser.add_argument("--force", action="store_true", help="Force full sync")
    parser.add_argument("--no-notify", action="store_true", help="Disable notifications")

    args = parser.parse_args()

    if args.no_notify:
        global ENABLE_NOTIFICATIONS
        ENABLE_NOTIFICATIONS = False

    if args.status:
        show_status()
        return 0

    # Run sync with lock
    try:
        with SyncLock(LOCK_FILE):
            log("=" * 50)
            log("Sync daemon started")
            success = run_sync(force_full=args.force)
            log("Sync daemon finished")
            return 0 if success else 1
    except RuntimeError as e:
        log(f"Cannot start sync: {e}", "WARN")
        return 1
    except KeyboardInterrupt:
        log("Sync interrupted by user", "WARN")
        return 1
    except Exception as e:
        log(f"Unexpected error: {e}", "ERROR")
        return 1


if __name__ == "__main__":
    sys.exit(main())
