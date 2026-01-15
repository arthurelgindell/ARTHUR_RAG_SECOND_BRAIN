# Apple Notes RAG Architecture Reference

## System Overview

This document describes the architecture and patterns used in the Apple Notes
RAG system for semantic search and knowledge management.

## Components

### 1. Export Layer (JXA)

**File:** `scripts/export_notes.py`

Uses JavaScript for Automation (JXA) via `osascript` to access Apple Notes.

**Why JXA over alternatives:**
- Native macOS API with full feature access
- Handles HTML content and attachments
- More reliable than SQLite direct access (encryption issues)
- Better error handling than AppleScript

**Key JXA patterns:**
```javascript
const Notes = Application('Notes');
Notes.includeStandardAdditions = true;

// Iterate folders and notes
for (const folder of Notes.folders()) {
    for (const note of folder.notes()) {
        // Access properties
        note.id();
        note.name();
        note.body();        // HTML content
        note.plaintext();   // Text content
        note.modificationDate();
    }
}
```

### 2. Sync Layer (LanceDB)

**File:** `scripts/sync_to_rag.py`

Manages incremental synchronization between Apple Notes and the vector database.

**Change Detection Algorithm:**
```
1. Export all notes with content hashes
2. Load existing index metadata
3. Compare:
   - New: note_id not in existing → ADD
   - Modified: hash differs → UPDATE
   - Deleted: existing_id not in current → DELETE
4. Only embed changed notes
5. Atomic merge to database
```

**LanceDB Schema:**
```python
schema = pa.schema([
    pa.field("id", pa.string()),           # Apple Notes ID
    pa.field("title", pa.string()),        # Note title
    pa.field("body", pa.string()),         # HTML content
    pa.field("plaintext", pa.string()),    # Text content
    pa.field("folder", pa.string()),       # Folder name
    pa.field("created", pa.string()),      # ISO timestamp
    pa.field("modified", pa.string()),     # ISO timestamp
    pa.field("content_hash", pa.string()), # SHA-256 (16 chars)
    pa.field("vector", pa.list_(pa.float32(), 768)),  # Embedding
    pa.field("synced_at", pa.string()),    # Sync timestamp
])
```

### 3. Embedding Layer (LM Studio)

**Integration:** OpenAI-compatible API at `localhost:1234`

**Embedding strategy:**
- Concatenate title + plaintext for richer semantics
- Truncate to 8000 chars to avoid token limits
- Batch processing (10 notes per batch) for efficiency
- 768-dimensional vectors (nomic-embed-text-v1.5)

**API call:**
```python
response = requests.post(
    "http://localhost:1234/v1/embeddings",
    json={
        "model": "text-embedding-nomic-embed-text-v1.5",
        "input": "title\n\nplaintext content..."
    }
)
embedding = response.json()["data"][0]["embedding"]
```

### 4. Search Layer

**File:** `scripts/query_rag.py`

**Semantic Search:**
1. Embed the query using same model
2. Vector similarity search in LanceDB
3. Convert distance to similarity score (1 - distance)
4. Return ranked results with previews

**Hybrid Search (optional):**
1. Get semantic results (2x limit)
2. Boost scores for keyword matches
3. Re-rank by combined score
4. Return top results

### 5. Agent Layer

Two context-forked agents handle complex operations:

**notes-rag-agent:**
- Sync operations (full/incremental)
- Search with context and analysis
- Note relationship discovery

**models-expert-agent:**
- Model recommendations by task
- Performance benchmarking
- VRAM optimization advice

## Data Flow

```
┌─────────────────┐
│  Apple Notes    │
│     App         │
└────────┬────────┘
         │ JXA/osascript
         ▼
┌─────────────────┐
│ export_notes.py │ ──► JSON with metadata
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ sync_to_rag.py  │ ◄──►│   LM Studio     │
│                 │     │  (Embeddings)   │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐
│    LanceDB      │ ──► ~/.apple-notes-rag/
│  Vector Store   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  query_rag.py   │ ◄── User queries
└─────────────────┘
```

## Performance Characteristics

| Operation | Typical Time | Notes |
|-----------|--------------|-------|
| Full export (100 notes) | 5-10 sec | JXA overhead |
| Full sync (100 notes) | 2-5 min | Embedding time |
| Incremental sync (5 changes) | 10-30 sec | Only changed notes |
| Semantic search | 200-500 ms | Including embedding |

## Storage Requirements

- **Per note:** ~3-5 KB (metadata + 768 floats)
- **100 notes:** ~500 KB database
- **1000 notes:** ~5 MB database

## Best Practices

### For Sync Operations

1. **Use incremental sync** for regular updates (faster)
2. **Use full sync** when:
   - First time setup
   - Suspected index corruption
   - After changing embedding model

### For Search Quality

1. **Be specific** in queries for better results
2. **Use folder filters** to narrow scope
3. **Try hybrid search** for keyword-sensitive queries

### For Performance

1. **Keep LM Studio running** with models loaded
2. **Use GPU acceleration** for embeddings
3. **Run syncs during idle time** for large note collections

## Extension Points

### Adding New Export Sources

Implement similar pattern for other note sources:
```python
def export_from_source():
    # Return list of dicts with required fields:
    # id, name, body, folder, creationDate, modificationDate
    pass
```

### Custom Embedding Models

Change embedding model by setting environment:
```bash
export EMBEDDING_MODEL="bge-base-en-v1.5"
```
Note: Requires full re-sync when changing models.

### Alternative Vector Stores

LanceDB can be replaced with:
- Chroma (good for local)
- Qdrant (good for server deployment)
- FAISS (fastest, manual management)

Update `sync_to_rag.py` and `query_rag.py` with new store API.
