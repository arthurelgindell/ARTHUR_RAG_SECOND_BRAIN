---
description: |
  Apple Notes RAG system for semantic search and knowledge management.
  Exports notes via JXA, syncs to LanceDB with incremental updates,
  and enables natural language search using local LLM embeddings.

  Use this skill when:
  - User wants to search their Apple Notes semantically
  - User needs to sync/export Apple Notes
  - User asks about notes organization or analysis
  - User wants RAG capabilities for their notes

  Commands available:
  - /sync-notes - Sync notes to RAG database
  - /query-notes - Semantic search
  - /models - LM Studio model management
---

# Apple Notes RAG Integration

This plugin provides a complete RAG (Retrieval-Augmented Generation) system
for Apple Notes, using local LLM embeddings via LM Studio.

## Architecture

```
Apple Notes App
       │
       ▼ (JXA/osascript)
  export_notes.py
       │
       ▼ (incremental sync)
  sync_to_rag.py ──► LM Studio Embeddings
       │                    │
       ▼                    ▼
   LanceDB ◄────────── 768-dim vectors
       │
       ▼ (semantic search)
  query_rag.py
```

## Quick Start

### 1. Prerequisites

- macOS with Apple Notes
- LM Studio running at `localhost:1234`
- Embedding model loaded (e.g., `nomic-embed-text-v1.5`)
- Python packages: `pip install lancedb pyarrow requests`

### 2. First-Time Setup

Grant Terminal automation permissions:
1. Run the sync command
2. When prompted, go to System Settings > Privacy & Security > Automation
3. Enable "Notes" for Terminal (or your terminal app)

### 3. Initial Sync

```bash
# Full sync - exports and embeds all notes
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sync_to_rag.py --full
```

Or use the command:
```
/sync-notes mode=full
```

### 4. Search Your Notes

```bash
# Search for related notes
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/query_rag.py "meeting notes about project X"
```

Or use the command:
```
/query-notes query="meeting notes about project X"
```

## Commands

### /sync-notes

Sync Apple Notes to the RAG database.

**Arguments:**
- `mode` - `full` or `incremental` (default: incremental)

**Examples:**
```
/sync-notes                    # Incremental sync (fast)
/sync-notes mode=full          # Full rebuild (thorough)
```

### /query-notes

Search notes using natural language.

**Arguments:**
- `query` - Search query (required)
- `folder` - Filter to specific folder
- `limit` - Max results (default: 10)

**Examples:**
```
/query-notes query="budget planning ideas"
/query-notes query="code snippets" folder="Development"
/query-notes query="meeting notes" limit=20
```

### /models

LM Studio model management and recommendations.

**Arguments:**
- `action` - `recommend`, `list`, `analyze`, `benchmark`, `status`
- `task` - For recommend: `embedding`, `chat`, `code`, `reasoning`
- `model` - For analyze/benchmark: model name
- `vram` - Available VRAM in GB

**Examples:**
```
/models action=status
/models action=recommend task=embedding
/models action=analyze model=nemotron-3-nano
/models action=benchmark model=nemotron-3-nano
```

## Script Reference

### export_notes.py

Export Apple Notes via JXA.

```bash
python3 export_notes.py                    # Export all notes
python3 export_notes.py --count            # Count notes only
python3 export_notes.py --folder "Work"    # Export specific folder
python3 export_notes.py --since 2025-01-01 # Modified since date
python3 export_notes.py --output notes.json
```

### sync_to_rag.py

Sync to LanceDB with change detection.

```bash
python3 sync_to_rag.py --full        # Full rebuild
python3 sync_to_rag.py --incremental # Only changes
python3 sync_to_rag.py --status      # Check status
python3 sync_to_rag.py --json        # JSON output
```

### query_rag.py

Semantic search interface.

```bash
python3 query_rag.py "search query"
python3 query_rag.py "query" --folder "Work"
python3 query_rag.py "query" --limit 5
python3 query_rag.py "query" --full  # Include full body
python3 query_rag.py --list-folders
```

### models_expert.py

Model analysis and recommendations.

```bash
python3 models_expert.py status
python3 models_expert.py list
python3 models_expert.py recommend --task chat --vram 8
python3 models_expert.py analyze MODEL_NAME
python3 models_expert.py benchmark MODEL_NAME
```

## Database Location

Default: `~/.apple-notes-rag/`

The LanceDB database stores:
- Note metadata (id, title, folder, dates)
- Full text content
- 768-dimensional embedding vectors
- Content hashes for change detection

## Incremental Sync Algorithm

1. Export all notes from Apple Notes
2. Compare content hashes with indexed notes
3. Identify: new notes, modified notes, deleted notes
4. Only embed changed notes (saves time and API calls)
5. Use LanceDB merge for atomic updates

## Troubleshooting

### "Permission denied" for Notes

Go to System Settings > Privacy & Security > Automation and enable
Notes access for your terminal application.

### "LM Studio not available"

1. Start LM Studio application
2. Load an embedding model (e.g., nomic-embed-text-v1.5)
3. Ensure server is running on port 1234

### "Database not found"

Run a full sync first:
```
/sync-notes mode=full
```

### Slow embedding performance

- Use smaller batch sizes
- Ensure GPU acceleration is enabled in LM Studio
- Consider using a smaller embedding model

## Environment Variables

```bash
LM_STUDIO_URL=http://localhost:1234      # LM Studio server
EMBEDDING_MODEL=text-embedding-nomic-embed-text-v1.5
LM_STUDIO_MODELS_DIR=/path/to/models     # Models directory
```
