---
name: models
description: Get LM Studio model recommendations and analysis
agent: models-expert-agent
arguments:
  - name: action
    description: Action to perform - 'recommend', 'list', 'analyze', 'benchmark', or 'status'
    required: false
    default: "recommend"
  - name: task
    description: Task type for recommendations - 'embedding', 'chat', 'code', or 'reasoning'
    required: false
    default: "chat"
  - name: model
    description: Model name for analyze/benchmark actions
    required: false
  - name: vram
    description: Available VRAM in GB for recommendations
    required: false
    default: "8"
---

# LM Studio Models Expert

{{#if (eq action "recommend")}}
## Get Model Recommendations

Find the best model for: **{{task}}** tasks
Available VRAM: **{{vram}} GB**

Analyze available options and provide:
- Primary recommendation with reasoning
- Alternative options
- Configuration tips
- Download instructions if needed

{{else if (eq action "list")}}
## List Available Models

Inventory all models:
- Currently loaded in LM Studio
- Available in local models directory
- With sizes and specifications

{{else if (eq action "analyze")}}
## Analyze Model

{{#if model}}
Deep analysis of: **{{model}}**
{{else}}
Please specify a model name with `model=MODEL_NAME`
{{/if}}

Provide:
- Model specifications
- Suitable use cases
- Performance characteristics
- Optimization suggestions

{{else if (eq action "benchmark")}}
## Benchmark Model

{{#if model}}
Performance test: **{{model}}**
{{else}}
Please specify a model name with `model=MODEL_NAME`
{{/if}}

Run benchmark and report:
- Tokens per second
- Response latency
- Quality assessment

{{else if (eq action "status")}}
## LM Studio Status

Check server health and configuration:
- Server connectivity
- Loaded models
- Resource usage

{{/if}}

## Your Task

1. **Check LM Studio status** first
2. **Execute the requested action**: {{action}}
3. **Provide comprehensive results** with actionable recommendations

Begin analysis now.
