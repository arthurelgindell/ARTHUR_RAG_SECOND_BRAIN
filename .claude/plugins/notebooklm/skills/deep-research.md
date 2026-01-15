---
name: deep-research
description: |
  Perform deep research on a topic using NotebookLM without polluting the main conversation.
  This skill runs in a forked context - all intermediate tool calls (queries, source fetching,
  analysis) happen in isolation. Only the final research report returns to the main chat.

  Use when you need comprehensive research that would otherwise flood the chat with
  hundreds of tool outputs.
context: fork
tools:
  - mcp__notebooklm-mcp__*
  - Read
  - Write
  - Bash
---

# Deep Research Skill (Context-Forked)

This skill performs comprehensive NotebookLM research in an isolated context.
The main conversation receives only the final summary, not the intermediate noise.

## How Context Forking Works

When this skill activates:
1. A sub-session inherits the current conversation context
2. Research operations run in isolation (queries, extractions, analysis)
3. Hundreds of tool calls execute without cluttering main chat
4. Only the final report returns to the user

## Research Workflow

### Phase 1: Discovery
1. Identify relevant notebooks using `notebook_list`
2. Get notebook summaries with `notebook_describe`
3. Determine which sources are most relevant

### Phase 2: Deep Extraction
1. Use `source_get_content` to extract raw text from key sources
2. Save extracted content to local files for efficiency
3. Build a local knowledge base

### Phase 3: Analysis (Local LLM)
1. Process extracted content with LM Studio (token-free)
2. Generate summaries, identify themes, find connections
3. Cross-reference across multiple sources

### Phase 4: Synthesis
1. Combine findings into a coherent report
2. Include citations to original sources
3. Highlight key insights and recommendations

## Usage Examples

**Basic research:**
```
/deep-research: What are the best practices for Claude Code plugin development?
```

**Targeted notebook research:**
```
/deep-research: Analyze the CLAUDE CODE notebook for advanced hook patterns
```

**Cross-notebook analysis:**
```
/deep-research: Compare approaches to local LLM integration across my notebooks
```

## Output Format

The skill produces a structured research report:

```markdown
# Research Report: [Topic]

## Executive Summary
[2-3 sentence overview]

## Key Findings
1. [Finding with source citation]
2. [Finding with source citation]
...

## Detailed Analysis
[Organized by theme/topic]

## Sources Consulted
- [Notebook: Source Name]
- ...

## Recommendations
[Actionable next steps]
```

## Token Optimization

This skill is designed for maximum token efficiency:

1. **Context Isolation**: Intermediate tool outputs don't consume main context
2. **Local Processing**: Heavy analysis offloaded to LM Studio
3. **Batch Extraction**: Content extracted once, queried locally multiple times
4. **Selective Querying**: Only relevant notebooks/sources are queried

## Integration with Batch Processor

For very large research tasks, this skill can leverage the batch processor:

```bash
# Extract content locally first
python3 .claude/plugins/notebooklm/scripts/batch_processor.py extract \
  --notebook "CLAUDE CODE" \
  --output ./research_cache/

# Then query locally (essentially free)
python3 .claude/plugins/notebooklm/scripts/batch_processor.py query \
  --input ./research_cache/ \
  --queries "What are hooks?" "How do skills work?" \
  --output findings.json
```

## Error Handling

If NotebookLM is unavailable or rate-limited:
1. Fall back to any locally cached content
2. Use LM Studio for analysis of available data
3. Report partial findings with clear indication of limitations

## Best Practices

1. **Be specific**: Narrow research questions yield better results
2. **Name notebooks**: Reference notebooks by name when possible
3. **Set scope**: Indicate if you want single-notebook or cross-notebook research
4. **Request format**: Specify if you need bullet points, narrative, or structured data
