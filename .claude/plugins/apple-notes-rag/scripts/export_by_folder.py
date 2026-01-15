#!/usr/bin/env python3
"""
Folder-by-folder Apple Notes export for large note collections.

Exports notes one folder at a time to handle collections with 1000+ notes
that timeout with single-pass export.

Usage:
    python3 export_by_folder.py                    # Export all folders
    python3 export_by_folder.py --output ~/notes  # Custom output dir
    python3 export_by_folder.py --folder "Work"   # Single folder
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

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

# JXA script template to export a single folder
JXA_EXPORT_FOLDER = """
const Notes = Application('Notes');
const folders = Notes.folders();
const results = [];
const targetFolder = '{folder_name}';

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
                    body: note.body(),
                    plaintext: note.plaintext(),
                    folder: targetFolder,
                    creationDate: note.creationDate().toISOString(),
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


def run_jxa(script: str, timeout: int = 300) -> str:
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
        raise TimeoutError(f"Export timed out after {timeout} seconds")


def compute_hash(content: str) -> str:
    """Compute content hash."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


def get_folders() -> list[dict[str, Any]]:
    """Get list of all folders."""
    raw = run_jxa(JXA_GET_FOLDERS, timeout=60)
    return json.loads(raw)


def export_folder(folder_name: str, timeout: int = 300) -> list[dict[str, Any]]:
    """Export all notes from a single folder."""
    # Escape single quotes in folder name
    safe_name = folder_name.replace("'", "\\'")
    script = JXA_EXPORT_FOLDER.format(folder_name=safe_name)

    raw = run_jxa(script, timeout=timeout)
    notes = json.loads(raw)

    # Add content hashes
    for note in notes:
        note['content_hash'] = compute_hash(note.get('body', ''))

    return notes


def export_all_by_folder(output_dir: Path, timeout_per_folder: int = 300) -> dict[str, Any]:
    """
    Export all notes folder by folder.

    Returns statistics about the export.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get folder list
    print("Getting folder list...", file=sys.stderr)
    folders = get_folders()
    print(f"Found {len(folders)} folders", file=sys.stderr)

    all_notes = []
    stats = {
        "total_notes": 0,
        "folders_exported": 0,
        "folders_failed": [],
        "folder_counts": {}
    }

    for i, folder_info in enumerate(folders, 1):
        folder_name = folder_info['name']
        note_count = folder_info['count']

        if note_count == 0:
            print(f"  [{i}/{len(folders)}] {folder_name}: empty, skipping", file=sys.stderr)
            continue

        print(f"  [{i}/{len(folders)}] Exporting '{folder_name}' ({note_count} notes)...",
              file=sys.stderr, end=" ")

        try:
            # Adjust timeout based on note count
            folder_timeout = max(timeout_per_folder, note_count * 2)  # ~2 sec per note
            notes = export_folder(folder_name, timeout=folder_timeout)

            all_notes.extend(notes)
            stats["folder_counts"][folder_name] = len(notes)
            stats["folders_exported"] += 1
            stats["total_notes"] += len(notes)

            print(f"OK ({len(notes)} notes)", file=sys.stderr)

            # Save incremental progress
            progress_file = output_dir / "export_progress.json"
            with open(progress_file, 'w') as f:
                json.dump({
                    "exported_so_far": stats["total_notes"],
                    "folders_done": stats["folders_exported"],
                    "last_folder": folder_name
                }, f)

        except TimeoutError as e:
            print(f"TIMEOUT", file=sys.stderr)
            stats["folders_failed"].append({"folder": folder_name, "error": str(e)})
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            stats["folders_failed"].append({"folder": folder_name, "error": str(e)})

    # Save all notes
    output_file = output_dir / "all_notes.json"
    with open(output_file, 'w') as f:
        json.dump(all_notes, f, ensure_ascii=False)

    # Save stats
    stats_file = output_dir / "export_stats.json"
    stats["exported_at"] = datetime.now().isoformat()
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)

    print(f"\nExport complete: {stats['total_notes']} notes from {stats['folders_exported']} folders",
          file=sys.stderr)
    print(f"Saved to: {output_file}", file=sys.stderr)

    if stats["folders_failed"]:
        print(f"WARNING: {len(stats['folders_failed'])} folders failed to export", file=sys.stderr)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Export Apple Notes by folder")
    parser.add_argument('--output', '-o', type=str,
                       default=str(Path.home() / ".apple-notes-rag" / "export"),
                       help='Output directory')
    parser.add_argument('--folder', '-f', type=str,
                       help='Export only this folder')
    parser.add_argument('--timeout', '-t', type=int, default=300,
                       help='Timeout per folder in seconds (default: 300)')
    parser.add_argument('--list-folders', action='store_true',
                       help='List folders only')

    args = parser.parse_args()

    try:
        if args.list_folders:
            folders = get_folders()
            total = sum(f['count'] for f in folders)
            print(f"Found {len(folders)} folders with {total} total notes:\n")
            for f in sorted(folders, key=lambda x: x['count'], reverse=True):
                print(f"  {f['name']}: {f['count']} notes")
            return 0

        if args.folder:
            notes = export_folder(args.folder, timeout=args.timeout)
            print(json.dumps(notes, indent=2, ensure_ascii=False))
            return 0

        output_dir = Path(args.output)
        stats = export_all_by_folder(output_dir, timeout_per_folder=args.timeout)

        print(f"\nStats:")
        print(f"  Total notes: {stats['total_notes']}")
        print(f"  Folders exported: {stats['folders_exported']}")
        if stats['folders_failed']:
            print(f"  Folders failed: {len(stats['folders_failed'])}")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
