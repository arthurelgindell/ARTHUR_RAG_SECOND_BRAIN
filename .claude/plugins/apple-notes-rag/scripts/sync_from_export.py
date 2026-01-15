#!/usr/bin/env python3
"""
Sync to LanceDB from pre-exported notes JSON.

For large note collections, use this after running export_by_folder.py
to avoid re-exporting during sync.

Usage:
    python3 sync_from_export.py                    # Use default export
    python3 sync_from_export.py --input notes.json # Custom export file
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

# LM Studio embedding endpoint
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5")
EMBEDDING_DIM = 768

# Default paths
DEFAULT_EXPORT = Path.home() / ".apple-notes-rag" / "export" / "all_notes.json"
DEFAULT_DB_PATH = Path.home() / ".apple-notes-rag"


def get_embedding(text: str) -> list[float]:
    """Get embedding vector from LM Studio."""
    try:
        response = requests.post(
            f"{LM_STUDIO_URL}/v1/embeddings",
            json={
                "model": EMBEDDING_MODEL,
                "input": text[:8000]
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Failed to get embedding: {e}")


def sync_from_export(
    export_file: Path,
    db_path: Path,
    batch_size: int = 10
) -> dict[str, Any]:
    """
    Create LanceDB index from exported notes.
    """
    import lancedb

    print(f"Loading notes from {export_file}...", file=sys.stderr)
    with open(export_file, 'r') as f:
        notes = json.load(f)

    print(f"Found {len(notes)} notes", file=sys.stderr)

    if not notes:
        return {"status": "empty", "total": 0}

    # Generate embeddings
    print("Generating embeddings...", file=sys.stderr)
    records = []
    synced_at = datetime.now().isoformat()
    total = len(notes)

    for i in range(0, total, batch_size):
        batch = notes[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size

        print(f"  Batch {batch_num}/{total_batches} ({i+1}-{min(i+batch_size, total)}/{total})...",
              file=sys.stderr)

        for note in batch:
            # Create embedding from title + content
            text = f"{note['name']}\n\n{note.get('plaintext', note.get('body', ''))}"
            embedding = get_embedding(text)

            records.append({
                "id": note['id'],
                "title": note['name'],
                "body": note.get('body', ''),
                "plaintext": note.get('plaintext', ''),
                "folder": note['folder'],
                "created": note.get('creationDate', ''),
                "modified": note.get('modificationDate', ''),
                "content_hash": note.get('content_hash', ''),
                "vector": embedding,
                "synced_at": synced_at,
            })

    # Create database
    print(f"Creating LanceDB at {db_path}...", file=sys.stderr)
    db_path.mkdir(parents=True, exist_ok=True)
    db = lancedb.connect(str(db_path))

    # Drop existing table if exists
    if "notes" in db.table_names():
        db.drop_table("notes")

    # Create new table with data
    db.create_table("notes", data=records)

    stats = {
        "status": "success",
        "total": len(records),
        "synced_at": synced_at,
        "db_path": str(db_path)
    }

    print(f"\nSync complete: {len(records)} notes indexed", file=sys.stderr)
    return stats


def main():
    parser = argparse.ArgumentParser(description="Sync exported notes to LanceDB")
    parser.add_argument('--input', '-i', type=str, default=str(DEFAULT_EXPORT),
                       help=f'Exported notes JSON (default: {DEFAULT_EXPORT})')
    parser.add_argument('--db-path', type=str, default=str(DEFAULT_DB_PATH),
                       help=f'Database path (default: {DEFAULT_DB_PATH})')
    parser.add_argument('--batch-size', '-b', type=int, default=10,
                       help='Batch size for embeddings (default: 10)')
    parser.add_argument('--json', action='store_true', help='JSON output')

    args = parser.parse_args()

    try:
        # Check LM Studio
        try:
            response = requests.get(f"{LM_STUDIO_URL}/v1/models", timeout=5)
            response.raise_for_status()
        except requests.exceptions.RequestException:
            print(f"Error: LM Studio not available at {LM_STUDIO_URL}", file=sys.stderr)
            return 1

        export_file = Path(args.input)
        if not export_file.exists():
            print(f"Error: Export file not found: {export_file}", file=sys.stderr)
            print("Run export_by_folder.py first.", file=sys.stderr)
            return 1

        result = sync_from_export(
            export_file=export_file,
            db_path=Path(args.db_path),
            batch_size=args.batch_size
        )

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\nStatus: {result['status']}")
            print(f"Total notes: {result['total']}")
            print(f"Database: {result['db_path']}")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
