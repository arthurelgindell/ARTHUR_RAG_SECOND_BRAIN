---
name: deep-research
description: Run comprehensive NotebookLM research in a forked context
context: fork
allowed_tools:
  - mcp__notebooklm-mcp__*
  - Read
  - Write
  - Bash
arguments:
  - name: topic
    description: The research topic or question
    required: true
  - name: notebook
    description: Specific notebook to research (optional, defaults to all)
    required: false
  - name: depth
    description: Research depth - quick, standard, or deep
    required: false
    default: standard
---

# Deep Research Command

You are performing deep research on: **{{topic}}**

{{#if notebook}}
Focus on notebook: **{{notebook}}**
{{/if}}

Research depth: **{{depth}}**

## Your Task

Execute comprehensive research following this workflow:

### 1. Discovery Phase
- List available notebooks with `notebook_list`
- Get descriptions of relevant notebooks with `notebook_describe`
- Identify the most relevant sources for "{{topic}}"

### 2. Extraction Phase
- For key sources, use `source_get_content` to get raw text
- Save important content to `/tmp/research_{{timestamp}}/` for local processing
- Note: This step may involve many tool calls - that's fine, we're in a forked context

### 3. Analysis Phase
- Query notebooks with `notebook_query` for AI-powered insights
- Use multiple targeted queries to explore different angles
- Cross-reference findings across sources

### 4. Synthesis Phase
Create a final report with this structure:

```markdown
# Research Report: {{topic}}

## Executive Summary
[2-3 sentences capturing the key takeaway]

## Key Findings
1. [Most important finding with source]
2. [Second finding with source]
3. [Third finding with source]

## Detailed Analysis
[Organized analysis by theme]

## Sources Consulted
- [List of notebooks and sources used]

## Recommendations
[Actionable next steps based on findings]
```

## Depth Guidelines

**quick**:
- Query 1-2 notebooks
- 3-5 targeted queries
- Brief summary output

**standard** (default):
- Query relevant notebooks
- 5-10 queries across sources
- Full structured report

**deep**:
- Query all potentially relevant notebooks
- 15+ queries exploring multiple angles
- Comprehensive report with extensive citations
- Include extracted quotes and specific references

## Important Notes

1. You are running in a FORKED CONTEXT - feel free to make many tool calls
2. Only your final report will be shown to the user
3. Prioritize quality insights over quantity of sources
4. Always cite which notebook/source each finding comes from
5. If a notebook query times out, retry once then move on

Begin your research now.
