#!/usr/bin/env python3
"""
Apple Notes RAG HTTP Bridge for ARTHUR Agent

This service provides an HTTP API for the Apple Notes RAG system,
allowing n8n workflows to query the semantic search database.

Usage:
    python notes_rag_bridge.py

Environment Variables:
    LANCEDB_PATH - Path to LanceDB database (default: ~/Library/Application Support/AppleNotesRAG)
    LM_STUDIO_URL - LM Studio API URL (default: http://localhost:1234/v1)
    EMBEDDING_MODEL - Model name for embeddings (default: nomic-embed-text-v1.5)

HTTP Endpoints:
    POST /query - Semantic search
    GET /health - Health check
    GET /stats - Database statistics
"""

import os
import sys
from pathlib import Path
from typing import Optional
from flask import Flask, request, jsonify

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apple-notes-rag" / "scripts"))

try:
    import lancedb
    import requests
    DEPENDENCIES_OK = True
except ImportError as e:
    DEPENDENCIES_OK = False
    IMPORT_ERROR = str(e)

app = Flask(__name__)

# Configuration
LANCEDB_PATH = os.environ.get(
    "LANCEDB_PATH",
    os.path.expanduser("~/Library/Application Support/AppleNotesRAG")
)
LM_STUDIO_URL = os.environ.get("LM_STUDIO_URL", "http://localhost:1234/v1")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text-v1.5")
TABLE_NAME = "notes"


def get_embedding(text: str) -> list:
    """Get embedding vector from LM Studio."""
    response = requests.post(
        f"{LM_STUDIO_URL}/embeddings",
        json={
            "input": text,
            "model": EMBEDDING_MODEL
        },
        timeout=30
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


def search_notes(query: str, limit: int = 5) -> list:
    """
    Search notes using semantic similarity.

    Args:
        query: Search query text
        limit: Maximum number of results

    Returns:
        List of matching notes with scores
    """
    db = lancedb.connect(LANCEDB_PATH)

    if TABLE_NAME not in db.table_names():
        return []

    table = db.open_table(TABLE_NAME)

    # Get query embedding
    query_embedding = get_embedding(query)

    # Search
    results = (
        table.search(query_embedding)
        .limit(limit)
        .to_list()
    )

    # Format results
    formatted = []
    for r in results:
        formatted.append({
            "title": r.get("title", "Untitled"),
            "content": r.get("content", "")[:500],  # Truncate content
            "folder": r.get("folder", "Unknown"),
            "score": float(r.get("_distance", 0)),
            "modified": r.get("modified", "")
        })

    return formatted


@app.route("/query", methods=["POST"])
def handle_query():
    """
    Semantic search endpoint.

    Expected JSON body:
    {
        "query": "search query text",
        "limit": 5  // optional, default 5
    }

    Returns:
    {
        "results": [
            {
                "title": "Note Title",
                "content": "Note content preview...",
                "folder": "Folder Name",
                "score": 0.85,
                "modified": "2026-01-15"
            }
        ],
        "count": 3
    }
    """
    if not DEPENDENCIES_OK:
        return jsonify({
            "error": "Dependencies not installed",
            "details": IMPORT_ERROR
        }), 500

    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        query = data.get("query")
        limit = data.get("limit", 5)

        if not query:
            return jsonify({"error": "query is required"}), 400

        results = search_notes(query, limit)

        # Format for LLM consumption
        if results:
            summary = f"Found {len(results)} relevant notes:\n\n"
            for i, r in enumerate(results, 1):
                summary += f"{i}. **{r['title']}** ({r['folder']})\n"
                summary += f"   {r['content'][:200]}...\n\n"
        else:
            summary = "No matching notes found for this query."

        return jsonify({
            "results": results,
            "count": len(results),
            "summary": summary
        })

    except requests.exceptions.ConnectionError:
        return jsonify({
            "error": "LM Studio not available",
            "details": "Cannot connect to embedding service"
        }), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    # Check LM Studio
    lm_studio_ok = False
    try:
        response = requests.get(f"{LM_STUDIO_URL}/models", timeout=5)
        lm_studio_ok = response.status_code == 200
    except:
        pass

    # Check database
    db_ok = False
    note_count = 0
    try:
        if DEPENDENCIES_OK:
            db = lancedb.connect(LANCEDB_PATH)
            if TABLE_NAME in db.table_names():
                db_ok = True
                table = db.open_table(TABLE_NAME)
                note_count = table.count_rows()
    except:
        pass

    return jsonify({
        "status": "healthy" if (lm_studio_ok and db_ok) else "degraded",
        "service": "notes-rag-bridge",
        "lm_studio": lm_studio_ok,
        "database": db_ok,
        "note_count": note_count,
        "dependencies": DEPENDENCIES_OK
    })


@app.route("/stats", methods=["GET"])
def get_stats():
    """Get database statistics."""
    if not DEPENDENCIES_OK:
        return jsonify({
            "error": "Dependencies not installed"
        }), 500

    try:
        db = lancedb.connect(LANCEDB_PATH)

        if TABLE_NAME not in db.table_names():
            return jsonify({
                "note_count": 0,
                "status": "no_data"
            })

        table = db.open_table(TABLE_NAME)

        return jsonify({
            "note_count": table.count_rows(),
            "database_path": LANCEDB_PATH,
            "status": "ready"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8765))
    print(f"Starting Notes RAG Bridge on port {port}")
    print(f"Database: {LANCEDB_PATH}")
    print(f"LM Studio: {LM_STUDIO_URL}")
    print(f"Endpoints:")
    print(f"  POST /query - Semantic search")
    print(f"  GET  /health - Health check")
    print(f"  GET  /stats - Database statistics")

    if not DEPENDENCIES_OK:
        print(f"\nWARNING: Missing dependencies - {IMPORT_ERROR}")
        print("Install with: pip install lancedb requests flask")

    app.run(host="0.0.0.0", port=port, debug=False)
