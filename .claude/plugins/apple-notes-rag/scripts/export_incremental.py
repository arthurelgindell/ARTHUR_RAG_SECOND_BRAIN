#!/usr/bin/env python3
"""
Incremental Apple Notes Export

Only exports notes modified since the last sync, making it suitable
for frequent automated syncs (every 10-20 minutes).

Strategy:
1. Query Apple Notes for modification dates (fast - metadata only)
2. Compare against stored modification dates
3. Only export full content for changed notes

Usage:
    python3 export_incremental.py                    # Export changes since last sync
    python3 export_incremental.py --since 2025-01-01 # Export changes since date
    python3 export_incremental.py --full             # Force full export (rebuild baseline)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Paths
BASE_DIR = Path.home() / ".apple-notes-rag"
EXPORT_DIR = BASE_DIR / "export"
STATE_FILE = BASE_DIR / "sync_state.json"
METADATA_CACHE = BASE_DIR / "notes_metadata.json"

# JXA script to get folder list
JXA_GET_FOLDERS = """
const Notes = Application('Notes');
const folders = Notes.folders();
const result = [];
for (let i = 0; i < folders.length; i++) {
    result.push({
        name: folders[i].name(),
        count: folders[i].notes().length
    });
}
JSON.stringify(result);
"""

# JXA script template to get metadata for a single folder (fast)
JXA_GET_FOLDER_METADATA = """
const Notes = Application('Notes');
const folders = Notes.folders();
const targetFolder = '{folder_name}';
const results = [];

for (let i = 0; i < folders.length; i++) {{
    const folder = folders[i];
    if (folder.name() === targetFolder) {{
        const notes = folder.notes();
        for (let j = 0; j < notes.length; j++) {{
            const note = notes[j];
            try {{
                results.push({{
                    id: note.id(),
                    name: note.name(),
                    folder: targetFolder,
                    modificationDate: note.modificationDate().toISOString()
                }});
            }} catch (e) {{
                continue;
            }}
        }}
        break;
    }}
}}
JSON.stringify(results);
"""

# JXA script template to export specific notes by ID
JXA_EXPORT_BY_IDS = """
const Notes = Application('Notes');
const folders = Notes.folders();
const targetIds = new Set({target_ids});
const results = [];

for (let i = 0; i < folders.length; i++) {{
    const folder = folders[i];
    const folderName = folder.name();
    const notes = folder.notes();

    for (let j = 0; j < notes.length; j++) {{
        const note = notes[j];
        try {{
            const noteId = note.id();
            if (targetIds.has(noteId)) {{
                results.push({{
                    id: noteId,
                    name: note.name(),
                    body: note.body(),
                    plaintext: note.plaintext(),
                    folder: folderName,
                    creationDate: note.creationDate().toISOString(),
                    modificationDate: note.modificationDate().toISOString()
                }});
                targetIds.delete(noteId);
                if (targetIds.size === 0) break;
            }}
        }} catch (e) {{
            continue;
        }}
    }}
    if (targetIds.size === 0) break;
}}
JSON.stringify(results);
"""


def run_jxa(script: str, timeout: int = 120) -> str:
    """Execute a JXA script via osascript."""
    try:
        result = subprocess.run(
            ["osascript", "-l", "JavaScript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode != 0:
            raise RuntimeError(f"osascript failed: {result.stderr.strip()}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"JXA script timed out after {timeout} seconds")


def compute_hash(content: str) -> str:
    """Compute content hash."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


def load_state() -> dict[str, Any]:
    """Load sync state."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"note_hashes": {}, "note_mod_dates": {}}


def save_state(state: dict[str, Any]):
    """Save sync state."""
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def load_metadata_cache() -> dict[str, dict]:
    """Load cached note metadata."""
    if METADATA_CACHE.exists():
        try:
            with open(METADATA_CACHE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_metadata_cache(metadata: dict[str, dict]):
    """Save note metadata cache."""
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    with open(METADATA_CACHE, 'w') as f:
        json.dump(metadata, f)


def get_folders() -> list[dict[str, Any]]:
    """Get list of all folders with note counts."""
    raw = run_jxa(JXA_GET_FOLDERS, timeout=60)
    return json.loads(raw)


def quick_change_check() -> dict[str, Any]:
    """
    Quick check for changes (~14 seconds).

    Compares folder counts against baseline to detect added/deleted notes.
    Returns dict with changed folder info.
    """
    state = load_state()
    stored_folder_counts = state.get("folder_counts", {})

    folders = get_folders()
    current_counts = {f["name"]: f["count"] for f in folders}
    total_notes = sum(f["count"] for f in folders)

    # Compare counts
    changed_folders = []
    new_folders = []
    deleted_folders = []

    for name, count in current_counts.items():
        if name not in stored_folder_counts:
            new_folders.append(name)
        elif stored_folder_counts[name] != count:
            changed_folders.append({
                "name": name,
                "old_count": stored_folder_counts[name],
                "new_count": count,
                "delta": count - stored_folder_counts[name]
            })

    for name in stored_folder_counts:
        if name not in current_counts:
            deleted_folders.append(name)

    has_changes = bool(changed_folders or new_folders or deleted_folders)

    return {
        "has_changes": has_changes,
        "total_notes": total_notes,
        "stored_total": sum(stored_folder_counts.values()) if stored_folder_counts else 0,
        "changed_folders": changed_folders,
        "new_folders": new_folders,
        "deleted_folders": deleted_folders,
        "current_counts": current_counts
    }


def get_folder_metadata(folder_name: str, timeout: int = 120) -> list[dict[str, Any]]:
    """Get metadata for all notes in a single folder."""
    safe_name = folder_name.replace("'", "\\'")
    script = JXA_GET_FOLDER_METADATA.format(folder_name=safe_name)
    raw = run_jxa(script, timeout=timeout)
    return json.loads(raw)


def get_all_metadata() -> list[dict[str, Any]]:
    """
    Get metadata for all notes, folder by folder.

    Returns list of {id, name, folder, modificationDate}
    """
    print("Fetching note metadata...", file=sys.stderr)

    folders = get_folders()
    all_metadata = []

    for i, folder_info in enumerate(folders, 1):
        folder_name = folder_info['name']
        note_count = folder_info['count']

        if note_count == 0:
            continue

        # Dynamic timeout based on folder size
        timeout = max(30, note_count * 1)  # ~1 sec per note for metadata

        try:
            metadata = get_folder_metadata(folder_name, timeout=timeout)
            all_metadata.extend(metadata)
            print(f"  [{i}/{len(folders)}] {folder_name}: {len(metadata)} notes", file=sys.stderr)
        except Exception as e:
            print(f"  [{i}/{len(folders)}] {folder_name}: ERROR - {e}", file=sys.stderr)

    return all_metadata


def export_notes_by_ids(note_ids: list[str]) -> list[dict[str, Any]]:
    """
    Export full content for specific notes by ID.

    Args:
        note_ids: List of note IDs to export

    Returns:
        List of full note objects
    """
    if not note_ids:
        return []

    print(f"Exporting {len(note_ids)} notes...", file=sys.stderr)

    # Format IDs for JavaScript Set
    ids_js = json.dumps(note_ids)
    script = JXA_EXPORT_BY_IDS.format(target_ids=ids_js)

    # Timeout scales with number of notes
    timeout = max(60, len(note_ids) * 3)
    raw = run_jxa(script, timeout=timeout)

    notes = json.loads(raw)

    # Add content hashes
    for note in notes:
        note['content_hash'] = compute_hash(note.get('body', ''))

    return notes


def detect_changes(
    current_metadata: list[dict],
    state: dict[str, Any]
) -> tuple[list[str], list[str], list[str]]:
    """
    Detect new, modified, and deleted notes by comparing metadata.

    Returns: (new_ids, modified_ids, deleted_ids)
    """
    stored_mod_dates = state.get("note_mod_dates", {})

    current_ids = set()
    new_ids = []
    modified_ids = []

    for note in current_metadata:
        note_id = note["id"]
        current_ids.add(note_id)
        mod_date = note["modificationDate"]

        if note_id not in stored_mod_dates:
            new_ids.append(note_id)
        elif stored_mod_dates[note_id] != mod_date:
            modified_ids.append(note_id)

    # Find deleted notes
    deleted_ids = [
        note_id for note_id in stored_mod_dates
        if note_id not in current_ids
    ]

    return new_ids, modified_ids, deleted_ids


def export_incremental(since: datetime | None = None, force_full_scan: bool = False) -> dict[str, Any]:
    """
    Perform incremental export using two-tier strategy:

    1. Quick check (~14 sec): Compare folder counts to detect obvious changes
    2. If changes detected, scan only affected folders
    3. Export full content only for truly changed notes

    Args:
        since: Only consider notes modified after this time (unused currently)
        force_full_scan: Force scanning all folders

    Returns:
        Dictionary with export results and statistics
    """
    state = load_state()

    # Step 1: Quick change check
    print("Checking for changes...", file=sys.stderr)
    check_result = quick_change_check()

    if not check_result["has_changes"] and not force_full_scan:
        print("No changes detected (folder counts unchanged)", file=sys.stderr)
        state["last_sync"] = datetime.now().isoformat()
        save_state(state)
        return {
            "status": "no_changes",
            "total_notes": check_result["total_notes"],
            "new": 0,
            "modified": 0,
            "deleted": 0,
            "changed_notes": [],
            "exported_at": datetime.now().isoformat()
        }

    # Step 2: Scan only changed folders (or all if forced)
    print(f"Changes detected in {len(check_result['changed_folders'])} folders", file=sys.stderr)

    folders_to_scan = []
    if force_full_scan:
        folders_to_scan = list(check_result["current_counts"].keys())
    else:
        # Scan changed folders + new folders
        folders_to_scan = [f["name"] for f in check_result["changed_folders"]]
        folders_to_scan.extend(check_result["new_folders"])

    # Get metadata for affected folders only
    current_metadata = []
    for folder_name in folders_to_scan:
        count = check_result["current_counts"].get(folder_name, 0)
        if count == 0:
            continue

        print(f"  Scanning '{folder_name}' ({count} notes)...", file=sys.stderr)
        timeout = max(60, count * 2)  # 2 sec per note
        try:
            metadata = get_folder_metadata(folder_name, timeout=timeout)
            current_metadata.extend(metadata)
        except Exception as e:
            print(f"    ERROR: {e}", file=sys.stderr)

    print(f"Scanned {len(current_metadata)} notes from {len(folders_to_scan)} folders", file=sys.stderr)

    # Detect changes within scanned notes
    new_ids, modified_ids, deleted_ids = detect_changes(current_metadata, state)

    # Handle deleted folders
    for folder_name in check_result["deleted_folders"]:
        # Find notes from this folder in state and mark as deleted
        for note_id, mod_date in list(state.get("note_mod_dates", {}).items()):
            # We'd need folder info in state to do this properly
            pass

    print(f"Changes: {len(new_ids)} new, {len(modified_ids)} modified, {len(deleted_ids)} deleted",
          file=sys.stderr)

    # Export only changed notes (if any)
    changed_ids = new_ids + modified_ids
    changed_notes = []

    if changed_ids:
        changed_notes = export_notes_by_ids(changed_ids)

    # Update state with new metadata
    for note in current_metadata:
        state.setdefault("note_mod_dates", {})[note["id"]] = note["modificationDate"]

    # Update folder counts
    state["folder_counts"] = check_result["current_counts"]

    # Remove deleted notes from state
    for note_id in deleted_ids:
        state.get("note_mod_dates", {}).pop(note_id, None)
        state.get("note_hashes", {}).pop(note_id, None)

    # Update hashes for changed notes
    for note in changed_notes:
        state.setdefault("note_hashes", {})[note["id"]] = note.get("content_hash", "")

    state["last_sync"] = datetime.now().isoformat()
    save_state(state)

    # Save metadata cache for reference
    metadata_dict = {n["id"]: n for n in current_metadata}
    save_metadata_cache(metadata_dict)

    # Save changed notes to export file (for sync_daemon to process)
    if changed_notes:
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        export_file = EXPORT_DIR / "incremental_changes.json"
        with open(export_file, 'w') as f:
            json.dump(changed_notes, f, ensure_ascii=False)

    return {
        "status": "success",
        "total_notes": check_result["total_notes"],
        "folders_scanned": len(folders_to_scan),
        "new": len(new_ids),
        "modified": len(modified_ids),
        "deleted": len(deleted_ids),
        "deleted_ids": deleted_ids,
        "changed_notes": changed_notes,
        "exported_at": datetime.now().isoformat()
    }


def export_full() -> dict[str, Any]:
    """
    Force full export - rebuilds baseline.

    Uses the existing export_by_folder.py for robustness with large collections.
    """
    print("Running full export...", file=sys.stderr)

    export_script = Path(__file__).parent / "export_by_folder.py"
    result = subprocess.run(
        [sys.executable, str(export_script), "--output", str(EXPORT_DIR)],
        capture_output=True,
        text=True,
        timeout=3600
    )

    if result.returncode != 0:
        raise RuntimeError(f"Full export failed: {result.stderr}")

    # Load and update state with all notes
    export_file = EXPORT_DIR / "all_notes.json"
    with open(export_file, 'r') as f:
        notes = json.load(f)

    state = load_state()
    state["note_mod_dates"] = {}
    state["note_hashes"] = {}

    for note in notes:
        state["note_mod_dates"][note["id"]] = note.get("modificationDate", "")
        content = note.get("body", "") + note.get("plaintext", "")
        state["note_hashes"][note["id"]] = compute_hash(content)

    state["last_sync"] = datetime.now().isoformat()
    state["last_full_export"] = datetime.now().isoformat()
    save_state(state)

    return {
        "status": "success",
        "total_notes": len(notes),
        "full_export": True,
        "exported_at": datetime.now().isoformat()
    }


def main():
    parser = argparse.ArgumentParser(
        description="Incremental Apple Notes export"
    )
    parser.add_argument(
        '--since', type=str,
        help='Export changes since date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--full', action='store_true',
        help='Force full export'
    )
    parser.add_argument(
        '--json', action='store_true',
        help='JSON output'
    )
    parser.add_argument(
        '--check-only', action='store_true',
        help='Only check for changes, do not export'
    )

    args = parser.parse_args()

    try:
        if args.full:
            result = export_full()
        else:
            since = None
            if args.since:
                since = datetime.strptime(args.since, "%Y-%m-%d")

            if args.check_only:
                # Just get metadata and detect changes
                metadata = get_all_metadata()
                state = load_state()
                new_ids, mod_ids, del_ids = detect_changes(metadata, state)
                result = {
                    "total": len(metadata),
                    "new": len(new_ids),
                    "modified": len(mod_ids),
                    "deleted": len(del_ids),
                    "has_changes": bool(new_ids or mod_ids or del_ids)
                }
            else:
                result = export_incremental(since)

        if args.json:
            # Don't include full notes in JSON output (too large)
            output = {k: v for k, v in result.items() if k != "changed_notes"}
            output["changed_count"] = len(result.get("changed_notes", []))
            print(json.dumps(output, indent=2))
        else:
            print(f"\nExport complete:")
            print(f"  Total notes: {result.get('total_notes', result.get('total', 0))}")
            print(f"  New: {result.get('new', 0)}")
            print(f"  Modified: {result.get('modified', 0)}")
            print(f"  Deleted: {result.get('deleted', 0)}")
            if result.get('full_export'):
                print(f"  (Full export)")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
