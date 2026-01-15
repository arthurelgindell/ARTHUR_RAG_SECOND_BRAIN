#!/usr/bin/env python3
"""
Incremental sync of Apple Notes to LanceDB vector database.

Efficiently syncs notes by:
1. Detecting changes via content hashing
2. Only embedding new/modified notes
3. Using LanceDB merge for atomic updates
4. Tracking deletions

Usage:
    python3 sync_to_rag.py --full              # Full sync (rebuild index)
    python3 sync_to_rag.py --incremental       # Incremental sync (default)
    python3 sync_to_rag.py --status            # Show sync status
    python3 sync_to_rag.py --db-path ~/rag     # Custom database path

Requirements:
    pip install lancedb pyarrow requests
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

# Add scripts directory to path for import
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from export_notes import export_all_notes

# LM Studio embedding endpoint
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5")
EMBEDDING_DIM = 768  # nomic-embed-text dimensions

# Default database path
DEFAULT_DB_PATH = Path.home() / ".apple-notes-rag"


def get_embedding(text: str) -> list[float]:
    """Get embedding vector from LM Studio."""
    try:
        response = requests.post(
            f"{LM_STUDIO_URL}/v1/embeddings",
            json={
                "model": EMBEDDING_MODEL,
                "input": text[:8000]  # Truncate to avoid token limits
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Failed to get embedding from LM Studio: {e}")


def get_embeddings_batch(texts: list[str], batch_size: int = 10) -> list[list[float]]:
    """Get embeddings for multiple texts in batches."""
    embeddings = []
    total = len(texts)

    for i in range(0, total, batch_size):
        batch = texts[i:i + batch_size]
        print(f"  Embedding batch {i // batch_size + 1}/{(total + batch_size - 1) // batch_size}...",
              file=sys.stderr)

        for text in batch:
            emb = get_embedding(text)
            embeddings.append(emb)

    return embeddings


def init_database(db_path: Path):
    """Initialize LanceDB database with notes table."""
    import lancedb
    import pyarrow as pa

    db = lancedb.connect(str(db_path))

    # Check if table exists
    if "notes" in db.table_names():
        return db

    # Create schema
    schema = pa.schema([
        pa.field("id", pa.string()),
        pa.field("title", pa.string()),
        pa.field("body", pa.string()),
        pa.field("plaintext", pa.string()),
        pa.field("folder", pa.string()),
        pa.field("created", pa.string()),
        pa.field("modified", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), EMBEDDING_DIM)),
        pa.field("synced_at", pa.string()),
    ])

    # Create empty table
    db.create_table("notes", schema=schema)
    print(f"Created new database at {db_path}", file=sys.stderr)

    return db


def load_existing_metadata(db) -> dict[str, dict[str, str]]:
    """Load existing note metadata for change detection."""
    try:
        table = db.open_table("notes")
        df = table.to_pandas()

        metadata = {}
        for _, row in df.iterrows():
            metadata[row['id']] = {
                'hash': row['content_hash'],
                'modified': row['modified']
            }
        return metadata
    except Exception:
        return {}


def sync_full(db_path: Path) -> dict[str, Any]:
    """
    Perform full sync - exports all notes and rebuilds the index.

    Returns:
        Sync statistics dictionary.
    """
    import lancedb

    print("Starting full sync...", file=sys.stderr)

    # Export all notes
    print("Exporting notes from Apple Notes...", file=sys.stderr)
    notes = export_all_notes()
    print(f"  Found {len(notes)} notes", file=sys.stderr)

    if not notes:
        return {"status": "empty", "total": 0}

    # Get embeddings for all notes
    print("Generating embeddings...", file=sys.stderr)
    texts = [f"{n['name']}\n\n{n.get('plaintext', n.get('body', ''))}" for n in notes]
    embeddings = get_embeddings_batch(texts)

    # Prepare records
    records = []
    synced_at = datetime.now().isoformat()

    for note, embedding in zip(notes, embeddings):
        records.append({
            "id": note['id'],
            "title": note['name'],
            "body": note.get('body', ''),
            "plaintext": note.get('plaintext', ''),
            "folder": note['folder'],
            "created": note['creationDate'],
            "modified": note['modificationDate'],
            "content_hash": note['content_hash'],
            "vector": embedding,
            "synced_at": synced_at,
        })

    # Recreate database
    db = lancedb.connect(str(db_path))
    if "notes" in db.table_names():
        db.drop_table("notes")

    db.create_table("notes", data=records)

    stats = {
        "status": "success",
        "mode": "full",
        "total": len(notes),
        "added": len(notes),
        "updated": 0,
        "deleted": 0,
        "synced_at": synced_at
    }

    print(f"Full sync complete: {len(notes)} notes indexed", file=sys.stderr)
    return stats


def sync_incremental(db_path: Path) -> dict[str, Any]:
    """
    Perform incremental sync - only process changed notes.

    Returns:
        Sync statistics dictionary.
    """
    import lancedb
    import pyarrow as pa

    print("Starting incremental sync...", file=sys.stderr)

    # Initialize or open database
    db = init_database(db_path)

    # Load existing metadata
    existing = load_existing_metadata(db)
    print(f"  Existing index: {len(existing)} notes", file=sys.stderr)

    # Export current notes
    print("Exporting notes from Apple Notes...", file=sys.stderr)
    current_notes = export_all_notes()
    print(f"  Found {len(current_notes)} notes", file=sys.stderr)

    # Detect changes
    to_add = []
    to_update = []
    current_ids = set()

    for note in current_notes:
        note_id = note['id']
        current_ids.add(note_id)

        if note_id not in existing:
            to_add.append(note)
        elif note['content_hash'] != existing[note_id]['hash']:
            to_update.append(note)

    # Detect deletions
    to_delete = [id for id in existing if id not in current_ids]

    print(f"  Changes: {len(to_add)} new, {len(to_update)} modified, {len(to_delete)} deleted",
          file=sys.stderr)

    # Handle deletions
    if to_delete:
        table = db.open_table("notes")
        for note_id in to_delete:
            table.delete(f"id = '{note_id}'")
        print(f"  Deleted {len(to_delete)} notes", file=sys.stderr)

    # Handle additions and updates
    changed_notes = to_add + to_update
    if changed_notes:
        print("Generating embeddings for changed notes...", file=sys.stderr)
        texts = [f"{n['name']}\n\n{n.get('plaintext', n.get('body', ''))}" for n in changed_notes]
        embeddings = get_embeddings_batch(texts)

        synced_at = datetime.now().isoformat()
        records = []

        for note, embedding in zip(changed_notes, embeddings):
            records.append({
                "id": note['id'],
                "title": note['name'],
                "body": note.get('body', ''),
                "plaintext": note.get('plaintext', ''),
                "folder": note['folder'],
                "created": note['creationDate'],
                "modified": note['modificationDate'],
                "content_hash": note['content_hash'],
                "vector": embedding,
                "synced_at": synced_at,
            })

        table = db.open_table("notes")

        # Delete notes that will be updated
        for note in to_update:
            table.delete(f"id = '{note['id']}'")

        # Add all new/updated records
        table.add(records)
        print(f"  Added/updated {len(records)} notes", file=sys.stderr)

    stats = {
        "status": "success",
        "mode": "incremental",
        "total": len(current_notes),
        "added": len(to_add),
        "updated": len(to_update),
        "deleted": len(to_delete),
        "synced_at": datetime.now().isoformat()
    }

    if not changed_notes and not to_delete:
        print("No changes detected", file=sys.stderr)
        stats["status"] = "no_changes"
    else:
        print("Incremental sync complete", file=sys.stderr)

    return stats


def get_status(db_path: Path) -> dict[str, Any]:
    """Get current sync status and statistics."""
    import lancedb

    if not db_path.exists():
        return {
            "status": "not_initialized",
            "db_path": str(db_path),
            "total_notes": 0
        }

    db = lancedb.connect(str(db_path))

    if "notes" not in db.table_names():
        return {
            "status": "empty",
            "db_path": str(db_path),
            "total_notes": 0
        }

    table = db.open_table("notes")
    df = table.to_pandas()

    # Get folder distribution
    folder_counts = df.groupby('folder').size().to_dict()

    # Get latest sync time
    latest_sync = df['synced_at'].max() if not df.empty else None

    return {
        "status": "ready",
        "db_path": str(db_path),
        "total_notes": len(df),
        "folders": folder_counts,
        "last_sync": latest_sync,
        "db_size_mb": round(sum(f.stat().st_size for f in db_path.rglob('*') if f.is_file()) / 1024 / 1024, 2)
    }


def main():
    parser = argparse.ArgumentParser(
        description="Sync Apple Notes to LanceDB for RAG"
    )
    parser.add_argument(
        '--full', action='store_true',
        help='Full sync (rebuild entire index)'
    )
    parser.add_argument(
        '--incremental', action='store_true',
        help='Incremental sync (default)'
    )
    parser.add_argument(
        '--status', action='store_true',
        help='Show sync status'
    )
    parser.add_argument(
        '--db-path', type=str, default=str(DEFAULT_DB_PATH),
        help=f'Database path (default: {DEFAULT_DB_PATH})'
    )
    parser.add_argument(
        '--json', action='store_true',
        help='Output results as JSON'
    )

    args = parser.parse_args()
    db_path = Path(args.db_path)

    try:
        # Check LM Studio availability
        try:
            response = requests.get(f"{LM_STUDIO_URL}/v1/models", timeout=5)
            response.raise_for_status()
        except requests.exceptions.RequestException:
            print("Error: LM Studio not available at", LM_STUDIO_URL, file=sys.stderr)
            print("Please start LM Studio with an embedding model loaded.", file=sys.stderr)
            return 1

        if args.status:
            result = get_status(db_path)
        elif args.full:
            result = sync_full(db_path)
        else:
            # Default to incremental
            result = sync_incremental(db_path)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\nStatus: {result.get('status', 'unknown')}")
            if 'total_notes' in result or 'total' in result:
                print(f"Total notes: {result.get('total_notes', result.get('total', 0))}")
            if 'added' in result:
                print(f"Added: {result['added']}, Updated: {result['updated']}, Deleted: {result['deleted']}")
            if 'folders' in result:
                print("Folders:")
                for folder, count in result['folders'].items():
                    print(f"  {folder}: {count}")
            if 'last_sync' in result and result['last_sync']:
                print(f"Last sync: {result['last_sync']}")

        return 0

    except ConnectionError as e:
        print(f"Connection Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
