# NotebookLM Integration Patterns

This document provides detailed workflow patterns for integrating NotebookLM with n8n automation and LM Studio local LLMs.

## Table of Contents

1. [Research Automation with n8n](#research-automation-with-n8n)
2. [Local LLM Analysis Pipeline](#local-llm-analysis-pipeline)
3. [Content Generation with Notifications](#content-generation-with-notifications)
4. [Hybrid RAG Pipeline](#hybrid-rag-pipeline)
5. [Daily Research Digest](#daily-research-digest)
6. [Source Sync Automation](#source-sync-automation)

---

## Research Automation with n8n

Automate research discovery and import using n8n workflows.

### n8n Workflow: Research Trigger

```json
{
  "name": "NotebookLM Research Automation",
  "nodes": [
    {
      "name": "Schedule Trigger",
      "type": "n8n-nodes-base.scheduleTrigger",
      "parameters": {
        "rule": {
          "interval": [{"field": "hours", "hoursInterval": 24}]
        }
      },
      "position": [250, 300]
    },
    {
      "name": "Set Research Topics",
      "type": "n8n-nodes-base.set",
      "parameters": {
        "assignments": {
          "assignments": [
            {"name": "topics", "value": "[\"AI trends 2025\", \"LLM optimization\"]", "type": "string"},
            {"name": "notebook_id", "value": "your-notebook-id", "type": "string"}
          ]
        }
      },
      "position": [450, 300]
    },
    {
      "name": "HTTP Request - Start Research",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://localhost:1234/v1/chat/completions",
        "method": "POST",
        "body": {
          "model": "nvidia/nemotron-3-nano",
          "messages": [
            {
              "role": "user",
              "content": "Use NotebookLM to start web research on: {{ $json.topics[0] }}"
            }
          ]
        }
      },
      "position": [650, 300]
    }
  ]
}
```

### Claude Code Orchestration

```
1. Create notebook for research topic
2. Start web research: "enterprise AI adoption 2025"
3. Poll research_status every 30 seconds until complete
4. Import top 10 most relevant sources
5. Generate notebook summary
6. Send results to Slack via n8n webhook
```

---

## Local LLM Analysis Pipeline

Extract content from NotebookLM and process with local LLM for cost savings.

### Python Implementation

```python
#!/usr/bin/env python3
"""
Extract NotebookLM sources and analyze with local LLM.
Saves ~90% on API costs by using local processing.
"""

from openai import OpenAI

# LM Studio client
lm_client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio"
)

def analyze_with_local_llm(content: str, task: str) -> str:
    """Process content with local LLM."""
    response = lm_client.chat.completions.create(
        model="nvidia/nemotron-3-nano",
        messages=[
            {"role": "system", "content": f"Task: {task}"},
            {"role": "user", "content": content}
        ],
        temperature=0.3,
        max_tokens=2000
    )
    return response.choices[0].message.content


def process_notebook_sources(sources: list) -> list:
    """
    Process multiple sources locally.

    Workflow:
    1. Use NotebookLM source_get_content to extract text
    2. Send to local LLM for analysis
    3. Aggregate results
    """
    results = []

    for source in sources:
        # Content already extracted from NotebookLM
        content = source.get("content", "")

        if not content:
            continue

        # Analyze locally
        summary = analyze_with_local_llm(
            content,
            "Summarize the key points in 3 bullet points"
        )

        key_insights = analyze_with_local_llm(
            content,
            "Extract the most important insight or finding"
        )

        results.append({
            "source_id": source["id"],
            "title": source["title"],
            "summary": summary,
            "key_insight": key_insights
        })

    return results


# Example workflow
if __name__ == "__main__":
    # After extracting sources via NotebookLM MCP:
    # sources = [result from source_get_content for each source]

    example_sources = [
        {
            "id": "src1",
            "title": "AI Trends Report",
            "content": "Artificial intelligence continues to transform..."
        }
    ]

    results = process_notebook_sources(example_sources)
    print(results)
```

### Cost Comparison

| Operation | NotebookLM | Local LLM |
|-----------|------------|-----------|
| Query notebook | 1 query (~2% daily limit) | Free |
| Summarize source | 1 query | Free |
| Extract insights | 1 query | Free |
| 10 sources full analysis | 30 queries (60% limit) | Free |

**Recommendation:** Use NotebookLM for initial research and complex multi-source reasoning. Use local LLM for repetitive analysis tasks.

---

## Content Generation with Notifications

Generate audio/video content and notify when complete.

### n8n Workflow: Generation Monitor

```json
{
  "name": "NotebookLM Generation Monitor",
  "nodes": [
    {
      "name": "Webhook Trigger",
      "type": "n8n-nodes-base.webhook",
      "parameters": {
        "path": "notebooklm-generate",
        "httpMethod": "POST"
      },
      "position": [250, 300]
    },
    {
      "name": "Start Generation",
      "type": "n8n-nodes-base.code",
      "parameters": {
        "jsCode": "// Trigger via Claude Code MCP\n// Returns job_id for polling\nreturn items;"
      },
      "position": [450, 300]
    },
    {
      "name": "Wait",
      "type": "n8n-nodes-base.wait",
      "parameters": {
        "amount": 60,
        "unit": "seconds"
      },
      "position": [650, 300]
    },
    {
      "name": "Check Status",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "={{ $json.status_url }}",
        "method": "GET"
      },
      "position": [850, 300]
    },
    {
      "name": "If Complete",
      "type": "n8n-nodes-base.if",
      "parameters": {
        "conditions": {
          "conditions": [{
            "leftValue": "={{ $json.status }}",
            "rightValue": "complete",
            "operator": {"operation": "equals"}
          }]
        }
      },
      "position": [1050, 300]
    },
    {
      "name": "Send Notification",
      "type": "n8n-nodes-base.slack",
      "parameters": {
        "channel": "#notifications",
        "text": "NotebookLM content ready: {{ $json.download_url }}"
      },
      "position": [1250, 200]
    },
    {
      "name": "Loop Back",
      "type": "n8n-nodes-base.noOp",
      "position": [1250, 400]
    }
  ]
}
```

### Claude Code Workflow

```
1. Create or select notebook with sources
2. Trigger audio_overview_create with deep_dive format
3. Save job_id
4. Poll studio_status every 60 seconds
5. When complete, extract download URL
6. POST to n8n webhook for notification
```

---

## Hybrid RAG Pipeline

Combine NotebookLM research with local embeddings for efficient retrieval.

### Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   NotebookLM    │     │   LM Studio     │     │   Application   │
│                 │     │                 │     │                 │
│ - Research      │────▶│ - Embed sources │────▶│ - Fast search   │
│ - Source import │     │ - Local storage │     │ - Query routing │
│ - Complex Q&A   │◀────│ - Quick queries │◀────│ - Response gen  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Implementation

```python
#!/usr/bin/env python3
"""
Hybrid RAG: NotebookLM for research, local LLM for retrieval.
"""

from openai import OpenAI
import numpy as np
import json

# Clients
lm_client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

# Local vector store (simple in-memory)
class LocalVectorStore:
    def __init__(self):
        self.documents = []
        self.embeddings = []
        self.metadata = []

    def add(self, text: str, embedding: list, meta: dict):
        self.documents.append(text)
        self.embeddings.append(embedding)
        self.metadata.append(meta)

    def search(self, query_embedding: list, top_k: int = 5) -> list:
        if not self.embeddings:
            return []

        # Cosine similarity
        query = np.array(query_embedding)
        scores = []
        for i, emb in enumerate(self.embeddings):
            emb = np.array(emb)
            score = np.dot(query, emb) / (np.linalg.norm(query) * np.linalg.norm(emb))
            scores.append((i, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [
            {"text": self.documents[i], "score": s, "metadata": self.metadata[i]}
            for i, s in scores[:top_k]
        ]

store = LocalVectorStore()


def embed_text(text: str) -> list:
    """Get embedding from local model."""
    response = lm_client.embeddings.create(
        model="text-embedding-nomic-embed-text-v1.5",
        input=text
    )
    return response.data[0].embedding


def ingest_from_notebooklm(sources: list):
    """
    Ingest NotebookLM sources into local vector store.

    Call after: source_get_content for each source
    """
    for source in sources:
        content = source.get("content", "")
        if not content:
            continue

        # Chunk large content
        chunks = chunk_text(content, chunk_size=1000)

        for i, chunk in enumerate(chunks):
            embedding = embed_text(chunk)
            store.add(
                text=chunk,
                embedding=embedding,
                meta={
                    "source_id": source["id"],
                    "title": source["title"],
                    "chunk": i
                }
            )

    print(f"Ingested {len(store.documents)} chunks")


def chunk_text(text: str, chunk_size: int = 1000) -> list:
    """Split text into chunks."""
    words = text.split()
    chunks = []
    current = []
    current_len = 0

    for word in words:
        if current_len + len(word) > chunk_size and current:
            chunks.append(" ".join(current))
            current = []
            current_len = 0
        current.append(word)
        current_len += len(word) + 1

    if current:
        chunks.append(" ".join(current))

    return chunks


def hybrid_query(question: str, use_notebooklm_for_complex: bool = True) -> str:
    """
    Query with hybrid approach:
    - Simple factual: local retrieval + local LLM
    - Complex reasoning: NotebookLM notebook_query
    """
    # Always do local retrieval first (fast, free)
    query_embedding = embed_text(question)
    local_results = store.search(query_embedding, top_k=3)

    # Check if we have good local matches
    if local_results and local_results[0]["score"] > 0.8:
        # High confidence local match - use local LLM
        context = "\n\n".join([r["text"] for r in local_results])

        response = lm_client.chat.completions.create(
            model="nvidia/nemotron-3-nano",
            messages=[
                {"role": "system", "content": f"Answer based on:\n{context}"},
                {"role": "user", "content": question}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content

    elif use_notebooklm_for_complex:
        # Low confidence or complex - use NotebookLM
        # This would call notebook_query via MCP
        return f"[Route to NotebookLM notebook_query: {question}]"

    else:
        # Fallback to local with lower confidence
        context = "\n\n".join([r["text"] for r in local_results]) if local_results else ""

        response = lm_client.chat.completions.create(
            model="nvidia/nemotron-3-nano",
            messages=[
                {"role": "system", "content": f"Answer based on available context:\n{context}"},
                {"role": "user", "content": question}
            ],
            temperature=0.5
        )
        return response.choices[0].message.content
```

---

## Daily Research Digest

Automated daily research with email summary.

### Workflow Steps

1. **Morning (6 AM)**: n8n Schedule Trigger
2. **Research**: NotebookLM `research_start` on configured topics
3. **Wait**: Poll `research_status` until complete
4. **Import**: `research_import` top 5 sources per topic
5. **Summarize**: `notebook_query` for key insights
6. **Format**: Local LLM formats email digest
7. **Send**: n8n sends email via Gmail/SMTP node

### n8n Workflow Configuration

```json
{
  "name": "Daily Research Digest",
  "nodes": [
    {
      "name": "Daily 6AM",
      "type": "n8n-nodes-base.scheduleTrigger",
      "parameters": {
        "rule": {"interval": [{"field": "cronExpression", "expression": "0 6 * * *"}]}
      }
    },
    {
      "name": "Research Topics",
      "type": "n8n-nodes-base.set",
      "parameters": {
        "assignments": {
          "assignments": [
            {"name": "topics", "value": "[\"AI news\", \"tech stocks\", \"climate tech\"]"}
          ]
        }
      }
    },
    {
      "name": "Format Digest",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://localhost:1234/v1/chat/completions",
        "method": "POST",
        "body": {
          "model": "nvidia/nemotron-3-nano",
          "messages": [
            {"role": "system", "content": "Format as email digest with sections"},
            {"role": "user", "content": "{{ $json.research_results }}"}
          ]
        }
      }
    },
    {
      "name": "Send Email",
      "type": "n8n-nodes-base.gmail",
      "parameters": {
        "to": "user@example.com",
        "subject": "Daily Research Digest - {{ $now.format('YYYY-MM-DD') }}",
        "body": "={{ $json.choices[0].message.content }}"
      }
    }
  ]
}
```

---

## Source Sync Automation

Keep Google Drive sources up to date automatically.

### Weekly Sync Workflow

```
1. n8n Schedule: Every Sunday at midnight
2. For each notebook with Drive sources:
   a. Call source_list_drive
   b. Filter for stale sources
   c. Call source_sync_drive with confirm=true
3. Log sync results
4. Alert if any sources failed to sync
```

### Implementation

```python
#!/usr/bin/env python3
"""
Sync stale Google Drive sources in NotebookLM notebooks.
"""

def sync_stale_sources(notebook_id: str) -> dict:
    """
    Sync all stale Drive sources in a notebook.

    This function would be called via Claude Code MCP.
    """
    results = {
        "notebook_id": notebook_id,
        "checked": 0,
        "synced": 0,
        "failed": 0,
        "errors": []
    }

    # 1. Get Drive sources with freshness status
    # drive_sources = source_list_drive(notebook_id)

    # 2. Filter stale sources
    # stale = [s for s in drive_sources if s["status"] == "stale"]

    # 3. Sync each stale source
    # for source in stale:
    #     try:
    #         source_sync_drive(notebook_id, [source["id"]], confirm=True)
    #         results["synced"] += 1
    #     except Exception as e:
    #         results["failed"] += 1
    #         results["errors"].append(str(e))

    return results
```

---

## Best Practices Summary

### Cost Optimization
1. Use local LLM for repetitive tasks (summaries, formatting)
2. Batch research operations to minimize queries
3. Cache embeddings locally for repeated searches
4. Use NotebookLM only for complex multi-source reasoning

### Reliability
1. Implement retry logic for transient failures
2. Monitor auth token expiration
3. Handle rate limits gracefully (queue and retry)
4. Log all operations for debugging

### Performance
1. Pre-embed sources for fast local retrieval
2. Use hybrid routing (local first, NotebookLM for complex)
3. Parallelize independent operations
4. Set appropriate timeouts for long-running tasks
