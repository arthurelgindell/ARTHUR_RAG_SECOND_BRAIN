---
name: n8n-workflow
description: Create n8n workflows autonomously using the workflow agent
agent: n8n-workflow-agent
arguments:
  - name: request
    description: Description of the workflow to create
    required: true
  - name: name
    description: Name for the workflow (optional, will be auto-generated)
    required: false
  - name: deploy
    description: Whether to deploy immediately if n8n is available (default true)
    required: false
    default: "true"
  - name: output
    description: Output directory for saved workflows
    required: false
    default: "~/n8n-workflows"
---

# N8N Workflow Generator

Create the following n8n workflow:

**Request:** {{request}}

{{#if name}}
**Workflow Name:** {{name}}
{{else}}
**Workflow Name:** Auto-generate based on request
{{/if}}

**Auto-deploy:** {{deploy}}
**Output Directory:** {{output}}

## Your Mission

1. **Analyze the request** to understand what workflow is needed
   - Identify trigger type (webhook, schedule, manual)
   - Identify processing steps
   - Identify integrations needed
   - Identify error handling requirements

2. **Check n8n availability** (for potential deployment)
   ```bash
   python3 /Users/arthurdell/ARTHUR_RAG/.claude/plugins/n8n-local/scripts/deploy_workflow.py --health
   ```

3. **Generate the workflow** using Python WorkflowBuilder API or workflow_patterns.py
   - Use NodeFactory for creating nodes
   - Use WorkflowBuilder for assembling the workflow
   - Consider using pre-built patterns from workflow_patterns.py

4. **Validate the workflow** thoroughly
   ```bash
   python3 /Users/arthurdell/ARTHUR_RAG/.claude/plugins/n8n-local/scripts/validate_workflow.py <file>
   ```

5. **Deploy or save locally**
   - If n8n is running and deploy=true: Deploy via API
   - Otherwise: Save to {{output}} directory

6. **Return a comprehensive summary** to the user with:
   - Workflow name and description
   - List of nodes and their purposes
   - File location
   - Deployment status
   - Usage instructions
   - Next steps (credential setup, etc.)

Begin workflow creation now.
