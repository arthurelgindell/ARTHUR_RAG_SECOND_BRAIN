#!/usr/bin/env python3
"""
Apple Notes Export via JXA (JavaScript for Automation).

Exports notes from Apple Notes app using osascript with JXA.
Supports full export, incremental export, and folder filtering.

Usage:
    python3 export_notes.py                    # Export all notes
    python3 export_notes.py --count            # Count notes only
    python3 export_notes.py --folder "Work"    # Export from specific folder
    python3 export_notes.py --since 2025-01-01 # Export modified since date
    python3 export_notes.py --output notes.json # Save to file

Requirements:
    - macOS with Apple Notes app
    - Terminal must have automation permissions for Notes
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from typing import Any

# JXA script to export all notes with metadata
JXA_EXPORT_ALL = """
const Notes = Application('Notes');

function exportNotes() {
    const results = [];
    const folders = Notes.folders();

    for (let i = 0; i < folders.length; i++) {
        const folder = folders[i];
        const folderName = folder.name();
        const notes = folder.notes();

        for (let j = 0; j < notes.length; j++) {
            const note = notes[j];
            try {
                results.push({
                    id: note.id(),
                    name: note.name(),
                    body: note.body(),
                    plaintext: note.plaintext(),
                    folder: folderName,
                    creationDate: note.creationDate().toISOString(),
                    modificationDate: note.modificationDate().toISOString()
                });
            } catch (e) {
                // Skip notes that can't be read
                continue;
            }
        }
    }
    return JSON.stringify(results);
}
exportNotes();
"""

# JXA script to count notes
JXA_COUNT = """
const Notes = Application('Notes');

function countNotes() {
    let total = 0;
    const folders = Notes.folders();
    const folderCounts = [];

    for (let i = 0; i < folders.length; i++) {
        const folder = folders[i];
        const count = folder.notes().length;
        total += count;
        folderCounts.push({
            folder: folder.name(),
            count: count
        });
    }
    return JSON.stringify({total: total, folders: folderCounts});
}
countNotes();
"""

# JXA script to get folders
JXA_FOLDERS = """
const Notes = Application('Notes');

function getFolders() {
    const folders = Notes.folders();
    const results = [];

    for (let i = 0; i < folders.length; i++) {
        const folder = folders[i];
        results.push({
            id: folder.id(),
            name: folder.name(),
            noteCount: folder.notes().length
        });
    }
    return JSON.stringify(results);
}
getFolders();
"""


def run_jxa(script: str) -> str:
    """Execute a JXA script via osascript and return the result."""
    try:
        result = subprocess.run(
            ["osascript", "-l", "JavaScript", "-e", script],
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout for large exports (1000+ notes)
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip()
            if "not allowed" in error_msg.lower() or "permission" in error_msg.lower():
                raise PermissionError(
                    "Terminal needs permission to access Notes.\n"
                    "Go to: System Settings > Privacy & Security > Automation\n"
                    "Enable 'Notes' for your terminal app."
                )
            raise RuntimeError(f"osascript failed: {error_msg}")

        return result.stdout.strip()

    except subprocess.TimeoutExpired:
        raise TimeoutError("Export timed out. You may have too many notes.")


def compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of content for change detection."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


def export_all_notes() -> list[dict[str, Any]]:
    """
    Export all notes from Apple Notes.

    Returns:
        List of note dictionaries with id, name, body, folder, dates, and content_hash.
    """
    raw = run_jxa(JXA_EXPORT_ALL)
    notes = json.loads(raw)

    # Add content hash for change detection
    for note in notes:
        note['content_hash'] = compute_content_hash(note.get('body', ''))

    return notes


def export_notes_since(since_date: datetime) -> list[dict[str, Any]]:
    """
    Export notes modified since a specific date.

    Args:
        since_date: Only return notes modified after this date.

    Returns:
        List of notes modified since the given date.
    """
    all_notes = export_all_notes()

    filtered = []
    for note in all_notes:
        mod_date = datetime.fromisoformat(note['modificationDate'].replace('Z', '+00:00'))
        if mod_date.replace(tzinfo=None) > since_date:
            filtered.append(note)

    return filtered


def export_folder(folder_name: str) -> list[dict[str, Any]]:
    """
    Export notes from a specific folder.

    Args:
        folder_name: Name of the folder to export.

    Returns:
        List of notes from the specified folder.
    """
    all_notes = export_all_notes()
    return [n for n in all_notes if n['folder'].lower() == folder_name.lower()]


def get_note_count() -> dict[str, Any]:
    """
    Get count of notes per folder without exporting content.

    Returns:
        Dictionary with total count and per-folder counts.
    """
    raw = run_jxa(JXA_COUNT)
    return json.loads(raw)


def get_folders() -> list[dict[str, Any]]:
    """
    Get list of all folders in Apple Notes.

    Returns:
        List of folder dictionaries with id, name, and noteCount.
    """
    raw = run_jxa(JXA_FOLDERS)
    return json.loads(raw)


def main():
    parser = argparse.ArgumentParser(
        description="Export Apple Notes for RAG indexing"
    )
    parser.add_argument(
        '--count', action='store_true',
        help='Only count notes without exporting content'
    )
    parser.add_argument(
        '--folders', action='store_true',
        help='List all folders'
    )
    parser.add_argument(
        '--folder', type=str,
        help='Export only from this folder'
    )
    parser.add_argument(
        '--since', type=str,
        help='Export notes modified since date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--output', '-o', type=str,
        help='Output file path (default: stdout)'
    )
    parser.add_argument(
        '--pretty', action='store_true',
        help='Pretty-print JSON output'
    )

    args = parser.parse_args()

    try:
        if args.count:
            result = get_note_count()
            print(f"Total notes: {result['total']}")
            for f in result['folders']:
                print(f"  {f['folder']}: {f['count']}")
            return 0

        if args.folders:
            folders = get_folders()
            print(f"Found {len(folders)} folders:")
            for f in folders:
                print(f"  {f['name']} ({f['noteCount']} notes)")
            return 0

        # Export notes
        if args.folder:
            notes = export_folder(args.folder)
            print(f"Exported {len(notes)} notes from '{args.folder}'", file=sys.stderr)
        elif args.since:
            since_date = datetime.fromisoformat(args.since)
            notes = export_notes_since(since_date)
            print(f"Exported {len(notes)} notes modified since {args.since}", file=sys.stderr)
        else:
            notes = export_all_notes()
            print(f"Exported {len(notes)} notes", file=sys.stderr)

        # Output
        indent = 2 if args.pretty else None
        json_output = json.dumps(notes, indent=indent, ensure_ascii=False)

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"Saved to {args.output}", file=sys.stderr)
        else:
            print(json_output)

        return 0

    except PermissionError as e:
        print(f"Permission Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
