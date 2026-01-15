---
name: query-notes
description: Search Apple Notes using semantic search
agent: notes-rag-agent
arguments:
  - name: query
    description: Natural language search query
    required: true
  - name: folder
    description: Optional folder to filter results
    required: false
  - name: limit
    description: Maximum number of results (default 10)
    required: false
    default: "10"
---

# Search Apple Notes

Search your Apple Notes for: **{{query}}**

{{#if folder}}
Filtering to folder: **{{folder}}**
{{/if}}

Returning up to **{{limit}}** results.

## Your Task

1. **Verify database exists**:
   - Check if RAG database has been initialized
   - If not, suggest running `/sync-notes` first

2. **Run semantic search**:
   - Use the query: "{{query}}"
   {{#if folder}}
   - Filter to folder: "{{folder}}"
   {{/if}}
   - Return top {{limit}} results

3. **Present results** with:
   - Note titles and folders
   - Relevance scores (higher = more relevant)
   - Content previews
   - Modification dates

4. **Provide insights**:
   - Suggest related queries if helpful
   - Note any patterns in results
   - Recommend follow-up actions

## Expected Output

```markdown
## Search Results for: "{{query}}"

Found X relevant notes:

1. **[Note Title]** (Folder: X, Score: 0.XX)
   Preview of content...

2. **[Note Title]** (Folder: Y, Score: 0.XX)
   Preview of content...

### Related Searches
- [suggestion 1]
- [suggestion 2]
```

Begin search now.
