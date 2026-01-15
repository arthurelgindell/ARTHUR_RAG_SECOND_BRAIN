#!/usr/bin/env python3
"""
NotebookLM utility functions.

This module provides helper utilities for working with NotebookLM data,
including content extraction, formatting, and integration helpers.

Usage:
    from notebook_utils import extract_sources, format_for_lm_studio
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class NotebookSource:
    """Represents a source from a NotebookLM notebook."""
    id: str
    title: str
    source_type: str
    content: str | None = None
    url: str | None = None
    summary: str | None = None
    keywords: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "id": self.id,
            "title": self.title,
            "type": self.source_type
        }
        if self.content:
            result["content"] = self.content
        if self.url:
            result["url"] = self.url
        if self.summary:
            result["summary"] = self.summary
        if self.keywords:
            result["keywords"] = self.keywords
        return result


@dataclass
class NotebookInfo:
    """Represents a NotebookLM notebook."""
    id: str
    title: str
    sources: list[NotebookSource]
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "source_count": len(self.sources),
            "sources": [s.to_dict() for s in self.sources]
        }


def clean_text(text: str) -> str:
    """Clean extracted text content."""
    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)

    # Remove common artifacts
    text = re.sub(r'\[.*?\]', '', text)  # Remove bracketed references

    return text.strip()


def chunk_text(
    text: str,
    chunk_size: int = 4000,
    overlap: int = 200
) -> list[str]:
    """
    Split text into chunks for processing.

    Args:
        text: Text to chunk
        chunk_size: Target size per chunk
        overlap: Overlap between chunks

    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence end within last 200 chars
            search_start = max(end - 200, start)
            sentence_end = -1

            for pattern in ['. ', '.\n', '? ', '!\n']:
                pos = text.rfind(pattern, search_start, end)
                if pos > sentence_end:
                    sentence_end = pos + 1

            if sentence_end > start:
                end = sentence_end

        chunks.append(text[start:end].strip())
        start = end - overlap

    return chunks


def format_for_embedding(
    sources: list[NotebookSource],
    include_metadata: bool = True
) -> list[dict[str, Any]]:
    """
    Format sources for embedding with LM Studio.

    Args:
        sources: List of NotebookSource objects
        include_metadata: Include source metadata

    Returns:
        List of documents ready for embedding
    """
    documents = []

    for source in sources:
        if not source.content:
            continue

        # Chunk large content
        chunks = chunk_text(source.content)

        for i, chunk in enumerate(chunks):
            doc = {
                "text": chunk,
                "source_id": source.id,
                "chunk_index": i,
                "total_chunks": len(chunks)
            }

            if include_metadata:
                doc["metadata"] = {
                    "title": source.title,
                    "type": source.source_type,
                    "url": source.url
                }

            documents.append(doc)

    return documents


def format_for_lm_studio(
    content: str,
    system_prompt: str | None = None,
    max_context: int = 8000
) -> dict[str, Any]:
    """
    Format content for LM Studio API request.

    Args:
        content: Content to process
        system_prompt: Optional system prompt
        max_context: Maximum context length

    Returns:
        Request body for LM Studio
    """
    messages = []

    if system_prompt:
        messages.append({
            "role": "system",
            "content": system_prompt
        })

    # Truncate content if needed
    if len(content) > max_context:
        content = content[:max_context] + "\n\n[Content truncated...]"

    messages.append({
        "role": "user",
        "content": content
    })

    return {
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2000
    }


def create_research_summary(
    query: str,
    sources: list[NotebookSource],
    max_sources: int = 5
) -> str:
    """
    Create a formatted research summary.

    Args:
        query: Original research query
        sources: Discovered sources
        max_sources: Maximum sources to include

    Returns:
        Formatted summary string
    """
    lines = [
        f"# Research Summary: {query}",
        "",
        f"Found {len(sources)} sources.",
        "",
        "## Top Sources",
        ""
    ]

    for i, source in enumerate(sources[:max_sources]):
        lines.append(f"### {i+1}. {source.title}")
        if source.url:
            lines.append(f"URL: {source.url}")
        if source.summary:
            lines.append(f"\n{source.summary}")
        lines.append("")

    return "\n".join(lines)


def create_n8n_webhook_payload(
    event_type: str,
    data: dict[str, Any]
) -> dict[str, Any]:
    """
    Create a payload for n8n webhook integration.

    Args:
        event_type: Type of event (research_complete, generation_complete, etc.)
        data: Event data

    Returns:
        Webhook payload
    """
    from datetime import datetime

    return {
        "event": event_type,
        "timestamp": datetime.now().isoformat(),
        "source": "notebooklm",
        "data": data
    }


def parse_notebook_response(response: dict[str, Any]) -> NotebookInfo | None:
    """
    Parse a notebook response from the MCP server.

    Args:
        response: Raw MCP response

    Returns:
        NotebookInfo object or None
    """
    try:
        # Handle different response formats
        notebook_data = response.get("notebook") or response

        sources = []
        for src in notebook_data.get("sources", []):
            sources.append(NotebookSource(
                id=src.get("id", ""),
                title=src.get("title", "Untitled"),
                source_type=src.get("type", "unknown"),
                url=src.get("url"),
                summary=src.get("summary")
            ))

        return NotebookInfo(
            id=notebook_data.get("id", ""),
            title=notebook_data.get("title", "Untitled"),
            sources=sources,
            description=notebook_data.get("description")
        )
    except Exception:
        return None


def estimate_query_cost(operation: str, count: int = 1) -> dict[str, Any]:
    """
    Estimate query cost for operations.

    Args:
        operation: Type of operation
        count: Number of operations

    Returns:
        Cost estimate
    """
    # Rough estimates based on free tier limits (~50/day)
    costs = {
        "notebook_query": 1,
        "notebook_describe": 1,
        "source_describe": 1,
        "research_start": 3,
        "audio_overview_create": 5,
        "video_overview_create": 5,
        "infographic_create": 3,
        "slide_deck_create": 3,
        "other": 1
    }

    cost_per_op = costs.get(operation, costs["other"])
    total_cost = cost_per_op * count

    return {
        "operation": operation,
        "count": count,
        "estimated_queries": total_cost,
        "daily_limit": 50,
        "percentage_of_limit": round((total_cost / 50) * 100, 1)
    }


# Export main utilities
__all__ = [
    "NotebookSource",
    "NotebookInfo",
    "clean_text",
    "chunk_text",
    "format_for_embedding",
    "format_for_lm_studio",
    "create_research_summary",
    "create_n8n_webhook_payload",
    "parse_notebook_response",
    "estimate_query_cost"
]
