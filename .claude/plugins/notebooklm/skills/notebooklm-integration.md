---
name: notebooklm
description: |
  Google NotebookLM integration for research, content generation, and knowledge management.
  Use when Claude needs to:
  - Create and manage NotebookLM notebooks
  - Add sources (URLs, YouTube, Google Drive, text)
  - Run AI-powered research and discovery
  - Generate audio podcasts, video explainers, infographics, and slide decks
  - Query notebooks for AI-powered answers
  - Extract and analyze source content
---

# NotebookLM Integration

This skill provides access to Google NotebookLM through the MCP protocol, enabling programmatic control over notebooks, sources, research, and content generation.

## Quick Reference

### Authentication
- Auth tokens stored at `~/.notebooklm-mcp/auth.json`
- Cookies expire every 2-4 weeks
- Run `notebooklm-mcp-auth` to refresh authentication

### Rate Limits
- Free tier: ~50 queries/day
- Content generation counts against limits
- Research operations are query-intensive

### Context Note
This plugin provides 31 tools which consume significant context. Consider disabling when not actively using NotebookLM features.

---

## Notebook Management Tools

### notebook_list
List all notebooks in your account.

**Parameters:** None

**Returns:** Array of notebook objects with:
- `id` - Notebook identifier
- `title` - Notebook name
- `created_at` - Creation timestamp
- `source_count` - Number of sources

**Example:**
```
List all my notebooks
```

---

### notebook_create
Create a new notebook.

**Parameters:**
- `title` (required) - Name for the new notebook

**Returns:** New notebook object with ID

**Example:**
```
Create a notebook called "AI Research 2025"
```

---

### notebook_get
Get detailed information about a specific notebook including all sources.

**Parameters:**
- `notebook_id` (required) - ID of the notebook

**Returns:** Notebook details with:
- Full metadata
- List of all sources with IDs
- Source summaries

**Example:**
```
Get details for notebook abc123
```

---

### notebook_rename
Rename an existing notebook.

**Parameters:**
- `notebook_id` (required) - ID of the notebook
- `title` (required) - New name

**Returns:** Updated notebook object

---

### notebook_delete
Delete a notebook permanently.

**Parameters:**
- `notebook_id` (required) - ID of the notebook
- `confirm` (required) - Must be `true` to confirm deletion

**Warning:** This action is irreversible.

---

### notebook_describe
Get an AI-generated summary of the notebook's contents.

**Parameters:**
- `notebook_id` (required) - ID of the notebook

**Returns:** AI-generated description including:
- Main topics covered
- Key themes
- Source overview

---

### notebook_query
Ask questions about the notebook content with AI-powered answers.

**Parameters:**
- `notebook_id` (required) - ID of the notebook
- `query` (required) - Question to ask

**Returns:** AI-generated answer with:
- Response text
- Source citations
- Confidence indicators

**Example:**
```
Query notebook abc123: "What are the main arguments presented?"
```

---

## Source Management Tools

### notebook_add_url
Add a URL or YouTube video as a source.

**Parameters:**
- `notebook_id` (required) - Target notebook ID
- `url` (required) - URL to add (web page or YouTube)

**Returns:** New source object

**Supported URLs:**
- Web articles
- YouTube videos (auto-transcribed)
- PDF documents (if publicly accessible)

**Example:**
```
Add https://example.com/article to notebook abc123
```

---

### notebook_add_text
Add plain text as a source.

**Parameters:**
- `notebook_id` (required) - Target notebook ID
- `title` (required) - Title for the text source
- `content` (required) - Text content to add

**Returns:** New source object

**Example:**
```
Add text source titled "Meeting Notes" with content "..." to notebook abc123
```

---

### notebook_add_drive
Add Google Drive documents as sources.

**Parameters:**
- `notebook_id` (required) - Target notebook ID
- `file_ids` (required) - Array of Google Drive file IDs

**Returns:** Array of new source objects

**Supported formats:**
- Google Docs
- Google Slides
- PDFs in Drive
- Text files

---

### source_describe
Get an AI-generated summary and keywords for a source.

**Parameters:**
- `notebook_id` (required) - Notebook containing the source
- `source_id` (required) - ID of the source

**Returns:**
- Summary text
- Keywords/topics
- Key points

---

### source_get_content
Extract the raw text content from a source.

**Parameters:**
- `notebook_id` (required) - Notebook containing the source
- `source_id` (required) - ID of the source

**Returns:** Raw text content of the source

**Use case:** Extract content for local LLM processing via LM Studio.

---

### source_list_drive
List Google Drive sources with freshness status.

**Parameters:**
- `notebook_id` (required) - Notebook ID

**Returns:** Drive sources with:
- Source metadata
- Last synced timestamp
- Freshness status (stale/fresh)

---

### source_sync_drive
Sync stale Google Drive sources with latest content.

**Parameters:**
- `notebook_id` (required) - Notebook ID
- `source_ids` (optional) - Specific sources to sync (or all if omitted)
- `confirm` (required) - Must be `true` to confirm

**Returns:** Sync status for each source

---

### source_delete
Delete a source from a notebook.

**Parameters:**
- `notebook_id` (required) - Notebook ID
- `source_id` (required) - Source to delete
- `confirm` (required) - Must be `true` to confirm

**Warning:** This action is irreversible.

---

## Research & Discovery Tools

### research_start
Start an AI-powered research session to discover relevant sources.

**Parameters:**
- `notebook_id` (required) - Target notebook
- `query` (required) - Research topic/question
- `mode` (required) - `"web"` or `"drive"`

**Returns:** Research session ID for status polling

**Example:**
```
Start web research on "enterprise AI adoption trends 2025" in notebook abc123
```

---

### research_status
Check the progress of an ongoing research session.

**Parameters:**
- `notebook_id` (required) - Notebook ID
- `research_id` (required) - Research session ID

**Returns:**
- Status (pending/running/complete)
- Discovered sources count
- Preview of found sources

---

### research_import
Import discovered sources from a research session into the notebook.

**Parameters:**
- `notebook_id` (required) - Notebook ID
- `research_id` (required) - Research session ID
- `source_ids` (optional) - Specific sources to import (or all if omitted)
- `limit` (optional) - Maximum sources to import

**Returns:** Imported source objects

**Example:**
```
Import top 10 sources from research session xyz789
```

---

## Content Generation (Studio) Tools

### audio_overview_create
Generate an AI podcast discussing the notebook content.

**Parameters:**
- `notebook_id` (required) - Notebook ID
- `format` (optional) - `"deep_dive"` | `"briefing"` | `"conversation"`
- `confirm` (required) - Must be `true` to confirm

**Returns:** Generation job ID

**Formats:**
- `deep_dive` - Detailed exploration (longer)
- `briefing` - Quick summary (shorter)
- `conversation` - Casual discussion style

**Note:** Generation takes 5-15 minutes. Use `studio_status` to poll.

---

### video_overview_create
Generate a video explainer about the notebook content.

**Parameters:**
- `notebook_id` (required) - Notebook ID
- `style` (optional) - Visual style preference
- `confirm` (required) - Must be `true` to confirm

**Returns:** Generation job ID

---

### infographic_create
Generate an infographic summarizing notebook content.

**Parameters:**
- `notebook_id` (required) - Notebook ID
- `orientation` (optional) - `"portrait"` | `"landscape"`
- `confirm` (required) - Must be `true` to confirm

**Returns:** Generation job ID

---

### slide_deck_create
Generate a presentation slide deck from notebook content.

**Parameters:**
- `notebook_id` (required) - Notebook ID
- `slide_count` (optional) - Target number of slides
- `confirm` (required) - Must be `true` to confirm

**Returns:** Generation job ID

---

### studio_status
Check the status of content generation jobs.

**Parameters:**
- `notebook_id` (required) - Notebook ID

**Returns:** Status of all generation jobs:
- Job type (audio/video/infographic/slides)
- Status (pending/processing/complete/failed)
- Download URL (when complete)

---

### studio_delete
Delete generated content artifacts.

**Parameters:**
- `notebook_id` (required) - Notebook ID
- `artifact_id` (required) - Artifact to delete
- `confirm` (required) - Must be `true` to confirm

---

## Configuration Tools

### chat_configure
Configure chat behavior for notebook queries.

**Parameters:**
- `notebook_id` (required) - Notebook ID
- `goal` (optional) - Chat goal (e.g., "learning guide", "research assistant")
- `style` (optional) - Response style
- `response_length` (optional) - `"short"` | `"medium"` | `"long"`

**Returns:** Updated configuration

---

### refresh_auth
Reload authentication tokens from disk.

**Parameters:** None

**Returns:** Auth status

**Use when:** Auth tokens were updated externally.

---

### save_auth_tokens
Save current cookies to persistent storage.

**Parameters:**
- `cookies` (required) - Cookie data to save

**Returns:** Save status

---

## Best Practices

### Efficient Querying
1. Use `notebook_describe` for overview before detailed queries
2. Batch related queries together
3. Use local LLM (LM Studio) for follow-up analysis

### Research Workflow
1. Start research with specific, focused queries
2. Poll status every 10-30 seconds
3. Review discovered sources before bulk import
4. Limit imports to most relevant sources

### Content Generation
1. Ensure notebook has sufficient sources (3+ recommended)
2. Use `notebook_query` to validate content before generation
3. Allow 5-15 minutes for generation
4. Download artifacts promptly (may expire)

### Cost Management
1. Monitor daily query usage
2. Extract source content for local processing
3. Use local LLM for summarization tasks
4. Batch research operations

---

## Integration with Other Plugins

### With LM Studio
Extract source content and process locally:
```
1. source_get_content → extract text
2. Send to LM Studio for analysis
3. Use local embeddings for search
```

### With n8n
Automate research workflows:
```
1. n8n Schedule Trigger → research_start
2. Poll research_status
3. research_import → notebook_query
4. Send results via webhook
```

See `references/workflow-patterns.md` for detailed examples.

---

## Troubleshooting

### Authentication Errors
```bash
# Re-authenticate
notebooklm-mcp-auth

# Or use the slash command
/notebooklm-auth
```

### Rate Limit Exceeded
- Wait until daily reset
- Use local LLM for processing
- Batch operations efficiently

### Source Import Failures
- Verify URL is accessible
- Check file permissions for Drive sources
- Ensure content isn't paywalled

### Generation Stuck
- Check `studio_status` for error details
- Try regenerating with different parameters
- Ensure sufficient source content
