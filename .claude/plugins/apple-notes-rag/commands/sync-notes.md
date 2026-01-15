---
name: sync-notes
description: Sync Apple Notes to RAG database for semantic search
agent: notes-rag-agent
arguments:
  - name: mode
    description: Sync mode - 'full' rebuilds entire index, 'incremental' only syncs changes (default)
    required: false
    default: "incremental"
---

# Sync Apple Notes to RAG Database

Sync your Apple Notes to the local RAG database using {{mode}} mode.

## Your Task

1. **Check prerequisites**:
   - Verify LM Studio is running with embedding model
   - Check current database status

2. **Run the sync**:
   {{#if (eq mode "full")}}
   - Perform FULL sync: Export all notes and rebuild the entire index
   - This will re-embed all notes (slower but ensures consistency)
   {{else}}
   - Perform INCREMENTAL sync: Only process new/modified/deleted notes
   - Uses content hashing for efficient change detection
   {{/if}}

3. **Report results**:
   - Number of notes added/updated/deleted
   - Total notes in database
   - Folders indexed
   - Any errors or warnings

## Expected Output

Provide a summary like:

```
## Sync Complete

- Mode: {{mode}}
- Notes added: X
- Notes updated: Y
- Notes deleted: Z
- Total indexed: N
- Folders: [list]
```

Begin sync operation now.
