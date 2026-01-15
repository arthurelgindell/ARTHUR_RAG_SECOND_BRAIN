#!/usr/bin/env python3
"""
Semantic search for Apple Notes RAG database with freshness scoring.

Query your notes using natural language and get relevant results
ranked by semantic similarity AND temporal relevance.

Query Types:
    current    - Prioritize recent notes (contact info, current status)
    balanced   - Moderate freshness weight (default)
    historical - No freshness penalty (research, audit trails)
    auto       - Auto-detect based on query keywords

Usage:
    python3 query_rag.py "my current email address" --query-type current
    python3 query_rag.py "meeting notes about project X"
    python3 query_rag.py "ideas for the new feature" --limit 5
    python3 query_rag.py "old address history" --query-type historical
    python3 query_rag.py "python code snippets" --full

Requirements:
    pip install lancedb requests
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

# LM Studio embedding endpoint
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5")

# Default database path
DEFAULT_DB_PATH = Path.home() / ".apple-notes-rag"

# =============================================================================
# FRESHNESS SCORING CONFIGURATION
# =============================================================================

# Query type presets: (freshness_weight, decay_rate, description)
# - freshness_weight: 0.0-1.0, how much freshness affects final score
# - decay_rate: how quickly old notes lose freshness (higher = faster decay)
QUERY_TYPE_PRESETS = {
    "current": {
        "freshness_weight": 0.4,
        "decay_rate": 0.02,  # ~35 days to 50% freshness
        "description": "Prioritize recent notes (contact info, current status)"
    },
    "balanced": {
        "freshness_weight": 0.2,
        "decay_rate": 0.005,  # ~139 days to 50% freshness
        "description": "Moderate freshness weight (default)"
    },
    "historical": {
        "freshness_weight": 0.0,
        "decay_rate": 0.0,
        "description": "No freshness penalty (research, audit trails)"
    }
}

# Keywords that trigger "current" mode in auto-detection
CURRENT_KEYWORDS = [
    r"\bcurrent\b", r"\bnow\b", r"\btoday\b", r"\blatest\b", r"\brecent\b",
    r"\bactive\b", r"\bpresent\b", r"\bup.?to.?date\b", r"\bmodern\b"
]

# Keywords that trigger "historical" mode in auto-detection
HISTORICAL_KEYWORDS = [
    r"\bold\b", r"\bprevious\b", r"\bformer\b", r"\bhistory\b", r"\bpast\b",
    r"\barchive\b", r"\boriginal\b", r"\bbackup\b", r"\blegacy\b"
]


def calculate_freshness_score(modified_date: str, decay_rate: float) -> float:
    """
    Calculate freshness score using exponential decay.

    Args:
        modified_date: ISO format date string
        decay_rate: Controls decay speed (0.01 = gentle, 0.1 = aggressive)

    Returns:
        Freshness score between 0.0 and 1.0
    """
    if decay_rate == 0:
        return 1.0  # No decay = always fresh

    try:
        # Parse modification date
        if isinstance(modified_date, str):
            # Handle various date formats
            mod_date = modified_date[:10]  # Get YYYY-MM-DD
            modified = datetime.strptime(mod_date, "%Y-%m-%d")
        else:
            modified = modified_date

        # Calculate days since modification
        days_old = (datetime.now() - modified).days
        days_old = max(0, days_old)  # Ensure non-negative

        # Exponential decay: e^(-decay_rate * days)
        freshness = math.exp(-decay_rate * days_old)

        return freshness
    except (ValueError, TypeError):
        return 0.5  # Default to neutral if date parsing fails


def detect_query_type(query: str) -> str:
    """
    Auto-detect query type based on keywords.

    Returns: 'current', 'historical', or 'balanced'
    """
    query_lower = query.lower()

    # Check for current indicators
    for pattern in CURRENT_KEYWORDS:
        if re.search(pattern, query_lower):
            return "current"

    # Check for historical indicators
    for pattern in HISTORICAL_KEYWORDS:
        if re.search(pattern, query_lower):
            return "historical"

    # Default to balanced
    return "balanced"


def combine_scores(
    semantic_score: float,
    freshness_score: float,
    freshness_weight: float
) -> float:
    """
    Combine semantic similarity and freshness into final score.

    Formula: (1 - weight) * semantic + weight * freshness
    """
    return (1 - freshness_weight) * semantic_score + freshness_weight * freshness_score


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
        raise ConnectionError(f"Failed to get embedding from LM Studio: {e}")


def search(
    query: str,
    db_path: Path = DEFAULT_DB_PATH,
    limit: int = 10,
    folder: str | None = None,
    include_body: bool = False,
    query_type: str = "auto",
    freshness_weight: float | None = None
) -> list[dict[str, Any]]:
    """
    Perform semantic search on the notes database with freshness scoring.

    Args:
        query: Natural language search query
        db_path: Path to LanceDB database
        limit: Maximum number of results
        folder: Optional folder filter
        include_body: Include full note body in results
        query_type: 'current', 'balanced', 'historical', or 'auto'
        freshness_weight: Override preset freshness weight (0.0-1.0)

    Returns:
        List of matching notes with combined scores
    """
    import lancedb

    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}. Run sync first.")

    db = lancedb.connect(str(db_path))

    if "notes" not in db.table_names():
        raise ValueError("Notes table not found. Run sync first.")

    # Determine query type (auto-detect if needed)
    effective_query_type = query_type
    if query_type == "auto":
        effective_query_type = detect_query_type(query)

    # Get preset settings
    preset = QUERY_TYPE_PRESETS.get(effective_query_type, QUERY_TYPE_PRESETS["balanced"])
    effective_freshness_weight = freshness_weight if freshness_weight is not None else preset["freshness_weight"]
    decay_rate = preset["decay_rate"]

    # Get query embedding
    query_embedding = get_embedding(query)

    # Search - get more results than needed for re-ranking
    table = db.open_table("notes")
    fetch_limit = limit * 3 if effective_freshness_weight > 0 else limit
    search_query = table.search(query_embedding).limit(fetch_limit)

    # Apply folder filter if specified
    if folder:
        search_query = search_query.where(f"folder = '{folder}'")

    results = search_query.to_list()

    # Calculate combined scores and re-rank
    scored_results = []
    for r in results:
        semantic_score = 1 - r["_distance"]  # Convert distance to similarity
        freshness_score = calculate_freshness_score(r["modified"], decay_rate)
        combined_score = combine_scores(semantic_score, freshness_score, effective_freshness_weight)

        scored_results.append({
            "data": r,
            "semantic_score": semantic_score,
            "freshness_score": freshness_score,
            "combined_score": combined_score
        })

    # Sort by combined score (descending)
    scored_results.sort(key=lambda x: x["combined_score"], reverse=True)

    # Format results
    formatted = []
    for item in scored_results[:limit]:
        r = item["data"]
        result = {
            "title": r["title"],
            "folder": r["folder"],
            "score": round(item["combined_score"], 4),
            "semantic_score": round(item["semantic_score"], 4),
            "freshness_score": round(item["freshness_score"], 4),
            "modified": r["modified"],
            "query_type": effective_query_type,
            "preview": r["plaintext"][:300] + "..." if len(r["plaintext"]) > 300 else r["plaintext"]
        }
        if include_body:
            result["body"] = r["body"]
            result["plaintext"] = r["plaintext"]
        formatted.append(result)

    return formatted


def search_hybrid(
    query: str,
    keywords: list[str],
    db_path: Path = DEFAULT_DB_PATH,
    limit: int = 10,
    query_type: str = "auto",
    freshness_weight: float | None = None
) -> list[dict[str, Any]]:
    """
    Hybrid search combining semantic similarity, keyword matching, and freshness.

    Args:
        query: Natural language search query
        keywords: List of keywords to boost
        db_path: Path to LanceDB database
        limit: Maximum number of results
        query_type: 'current', 'balanced', 'historical', or 'auto'
        freshness_weight: Override preset freshness weight (0.0-1.0)

    Returns:
        List of matching notes with combined scores
    """
    import lancedb

    db = lancedb.connect(str(db_path))
    table = db.open_table("notes")

    # Determine query type (auto-detect if needed)
    effective_query_type = query_type
    if query_type == "auto":
        effective_query_type = detect_query_type(query)

    # Get preset settings
    preset = QUERY_TYPE_PRESETS.get(effective_query_type, QUERY_TYPE_PRESETS["balanced"])
    effective_freshness_weight = freshness_weight if freshness_weight is not None else preset["freshness_weight"]
    decay_rate = preset["decay_rate"]

    # Get semantic results
    query_embedding = get_embedding(query)
    semantic_results = table.search(query_embedding).limit(limit * 3).to_list()

    # Score and re-rank with keyword boost + freshness
    scored = []
    for r in semantic_results:
        semantic_score = 1 - r["_distance"]
        freshness_score = calculate_freshness_score(r["modified"], decay_rate)
        keyword_score = 0

        # Check for keyword matches in title and body
        text = f"{r['title']} {r['plaintext']}".lower()
        for keyword in keywords:
            if keyword.lower() in text:
                keyword_score += 0.1  # Boost per keyword match

        # Combine all scores
        base_score = combine_scores(semantic_score, freshness_score, effective_freshness_weight)
        combined_score = base_score + keyword_score

        scored.append({
            "data": r,
            "semantic_score": semantic_score,
            "freshness_score": freshness_score,
            "keyword_score": keyword_score,
            "combined_score": combined_score
        })

    # Sort by combined score
    scored.sort(key=lambda x: x["combined_score"], reverse=True)

    # Format results
    formatted = []
    for item in scored[:limit]:
        r = item["data"]
        formatted.append({
            "title": r["title"],
            "folder": r["folder"],
            "score": round(item["combined_score"], 4),
            "semantic_score": round(item["semantic_score"], 4),
            "freshness_score": round(item["freshness_score"], 4),
            "modified": r["modified"],
            "query_type": effective_query_type,
            "preview": r["plaintext"][:300] + "..." if len(r["plaintext"]) > 300 else r["plaintext"]
        })

    return formatted


def get_folders(db_path: Path = DEFAULT_DB_PATH) -> list[str]:
    """Get list of all folders in the database."""
    import lancedb

    db = lancedb.connect(str(db_path))
    table = db.open_table("notes")
    df = table.to_pandas()
    return sorted(df['folder'].unique().tolist())


def main():
    parser = argparse.ArgumentParser(
        description="Semantic search for Apple Notes with freshness scoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Query Types:
  current     Prioritize recent notes (contact info, current status)
  balanced    Moderate freshness weight (default)
  historical  No freshness penalty (research, audit trails)
  auto        Auto-detect based on query keywords (default)

Examples:
  python3 query_rag.py "my current email"              # Auto-detects 'current' mode
  python3 query_rag.py "email address" --query-type current
  python3 query_rag.py "old project notes" --query-type historical
  python3 query_rag.py "Arthur contact" --freshness-weight 0.5
        """
    )
    parser.add_argument(
        'query', nargs='?',
        help='Search query'
    )
    parser.add_argument(
        '--limit', '-n', type=int, default=10,
        help='Maximum number of results (default: 10)'
    )
    parser.add_argument(
        '--folder', '-f', type=str,
        help='Filter by folder name'
    )
    parser.add_argument(
        '--full', action='store_true',
        help='Include full note body in results'
    )
    parser.add_argument(
        '--keywords', '-k', type=str, nargs='+',
        help='Keywords for hybrid search boosting'
    )
    parser.add_argument(
        '--query-type', '-t', type=str, default='auto',
        choices=['current', 'balanced', 'historical', 'auto'],
        help='Query type preset for freshness scoring (default: auto)'
    )
    parser.add_argument(
        '--freshness-weight', '-w', type=float,
        help='Override freshness weight (0.0-1.0). Higher = more recent bias'
    )
    parser.add_argument(
        '--db-path', type=str, default=str(DEFAULT_DB_PATH),
        help=f'Database path (default: {DEFAULT_DB_PATH})'
    )
    parser.add_argument(
        '--json', action='store_true',
        help='Output as JSON'
    )
    parser.add_argument(
        '--list-folders', action='store_true',
        help='List available folders'
    )
    parser.add_argument(
        '--explain', action='store_true',
        help='Show detailed scoring breakdown'
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
            return 1

        if args.list_folders:
            folders = get_folders(db_path)
            print("Available folders:")
            for f in folders:
                print(f"  - {f}")
            return 0

        if not args.query:
            parser.print_help()
            return 1

        # Perform search
        if args.keywords:
            results = search_hybrid(
                args.query,
                args.keywords,
                db_path=db_path,
                limit=args.limit,
                query_type=args.query_type,
                freshness_weight=args.freshness_weight
            )
        else:
            results = search(
                args.query,
                db_path=db_path,
                limit=args.limit,
                folder=args.folder,
                include_body=args.full,
                query_type=args.query_type,
                freshness_weight=args.freshness_weight
            )

        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            if not results:
                print("No results found.")
                return 0

            # Show query mode info
            query_type_used = results[0].get("query_type", "balanced") if results else "balanced"
            preset = QUERY_TYPE_PRESETS.get(query_type_used, {})
            effective_weight = args.freshness_weight if args.freshness_weight is not None else preset.get("freshness_weight", 0.2)

            print(f"\nFound {len(results)} results for: \"{args.query}\"")
            print(f"Mode: {query_type_used} (freshness weight: {effective_weight})")
            print("-" * 70)

            for i, r in enumerate(results, 1):
                print(f"\n{i}. {r['title']}")

                # Show scoring breakdown if --explain flag or include scores in compact format
                if args.explain:
                    print(f"   Folder: {r['folder']}")
                    print(f"   Modified: {r['modified'][:10]}")
                    print(f"   Combined Score: {r['score']}")
                    print(f"   - Semantic: {r.get('semantic_score', 'N/A')}")
                    print(f"   - Freshness: {r.get('freshness_score', 'N/A')}")
                else:
                    freshness_indicator = ""
                    fs = r.get('freshness_score', 1.0)
                    if fs >= 0.8:
                        freshness_indicator = " [FRESH]"
                    elif fs < 0.3:
                        freshness_indicator = " [OLD]"

                    print(f"   Folder: {r['folder']} | Score: {r['score']} | Modified: {r['modified'][:10]}{freshness_indicator}")

                print(f"   {r['preview']}")

                if args.full and 'body' in r:
                    print(f"\n   --- Full Content ---")
                    print(f"   {r['plaintext'][:1000]}")

            print("\n" + "-" * 70)

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Run 'python3 sync_to_rag.py --full' to create the index.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
