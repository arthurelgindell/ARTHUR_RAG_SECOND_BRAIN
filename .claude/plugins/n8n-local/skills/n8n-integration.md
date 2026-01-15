---
name: n8n-local
description: |
  Local n8n workflow automation server integration. Use when Claude needs to:
  - Create n8n workflows programmatically
  - Generate valid n8n workflow JSON
  - Manage automation pipelines
  - Configure AI agents in n8n with local LLMs
  - Execute CLI commands for workflow import/export
  - Interact with the n8n REST API
  - Set up webhook triggers and responses
  - Connect external services through n8n
---

# N8N Local Server Integration

This skill enables programmatic creation, management, and deployment of n8n workflows on a local self-hosted instance.

## Quick Reference

### Server Endpoints

| Service | URL |
|---------|-----|
| n8n Web UI | `http://localhost:5678` |
| n8n API | `http://localhost:5678/api/v1` |
| Docker internal | `http://host.docker.internal:5678` |
| Webhook base | `http://localhost:5678/webhook/` |

### Local LLM Endpoints

| Provider | URL |
|----------|-----|
| LM Studio | `http://host.docker.internal:1234/v1` |
| Ollama | `http://host.docker.internal:11434/v1` |

**Note:** Use `host.docker.internal` when n8n runs in Docker and the LLM runs on the host machine.

---

## Workflow JSON Structure

Every n8n workflow is a JSON object with this structure:

```json
{
  "name": "Workflow Name",
  "nodes": [],
  "connections": {},
  "active": false,
  "settings": {
    "executionOrder": "v1"
  }
}
```

### Node Object Schema

```json
{
  "id": "uuid-string",
  "name": "Display Name",
  "type": "n8n-nodes-base.nodeType",
  "typeVersion": 1,
  "position": [x, y],
  "parameters": {},
  "credentials": {}
}
```

### Connection Format

Connections use node **names** (not IDs) as keys:

```json
{
  "connections": {
    "Source Node Name": {
      "main": [[
        { "node": "Target Node Name", "type": "main", "index": 0 }
      ]]
    }
  }
}
```

**Important:** When a node has multiple outputs (like If/Switch nodes), use the appropriate output index in the array.

---

## Core Node Types

### Trigger Nodes

| Node | Type Identifier | Version |
|------|-----------------|---------|
| Webhook Trigger | `n8n-nodes-base.webhook` | 1.1 |
| Schedule Trigger | `n8n-nodes-base.scheduleTrigger` | 1.2 |
| Manual Trigger | `n8n-nodes-base.manualTrigger` | 1 |
| Error Trigger | `n8n-nodes-base.errorTrigger` | 1 |

### Action Nodes

| Node | Type Identifier | Version |
|------|-----------------|---------|
| HTTP Request | `n8n-nodes-base.httpRequest` | 4.1 |
| Execute Command | `n8n-nodes-base.executeCommand` | 1 |
| Code (JavaScript/Python) | `n8n-nodes-base.code` | 2 |
| Set (Edit Fields) | `n8n-nodes-base.set` | 3.4 |
| Respond to Webhook | `n8n-nodes-base.respondToWebhook` | 1.1 |

### Flow Control Nodes

| Node | Type Identifier | Version |
|------|-----------------|---------|
| If | `n8n-nodes-base.if` | 2 |
| Switch | `n8n-nodes-base.switch` | 3 |
| Merge | `n8n-nodes-base.merge` | 3 |
| Split In Batches | `n8n-nodes-base.splitInBatches` | 3 |
| Loop Over Items | `n8n-nodes-base.splitInBatches` | 3 |
| Wait | `n8n-nodes-base.wait` | 1.1 |

### AI/LangChain Nodes

| Node | Type Identifier | Version |
|------|-----------------|---------|
| AI Agent | `@n8n/n8n-nodes-langchain.agent` | 1.7 |
| OpenAI Chat Model | `@n8n/n8n-nodes-langchain.lmChatOpenAi` | 1.2 |
| Tools Agent | `@n8n/n8n-nodes-langchain.agentToolsAgent` | 1 |
| Window Buffer Memory | `@n8n/n8n-nodes-langchain.memoryBufferWindow` | 1.3 |
| HTTP Request Tool | `@n8n/n8n-nodes-langchain.toolHttpRequest` | 1.1 |
| Code Tool | `@n8n/n8n-nodes-langchain.toolCode` | 1 |

---

## CLI Commands

Execute inside Docker container:
```bash
docker exec -u node -it n8n <command>
```

### Workflow Management

```bash
# Export all workflows to single file
n8n export:workflow --all --output=workflows.json

# Export single workflow by ID
n8n export:workflow --id=<WORKFLOW_ID> --output=workflow.json

# Export for git backup (separate files per workflow)
n8n export:workflow --backup --output=./backups/

# Import workflow from file
n8n import:workflow --input=workflow.json

# Import all workflows from directory
n8n import:workflow --separate --input=./backups/
```

### Credential Management

**WARNING:** Exported credentials contain secrets in plaintext.

```bash
# Export all credentials (decrypted)
n8n export:credentials --all --decrypted --output=creds.json

# Import credentials
n8n import:credentials --input=creds.json
```

### Server Management

```bash
# Start n8n (foreground)
n8n start

# Execute workflow by ID
n8n execute --id=<WORKFLOW_ID>

# List available commands
n8n --help
```

---

## API Endpoints

**Authentication:** Include API key in header `X-N8N-API-KEY`

### Health & Info

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/healthz` | Health check (no auth required) |
| GET | `/api/v1/workflows` | List all workflows |

### Workflow Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/workflows/{id}` | Get workflow details |
| POST | `/api/v1/workflows` | Create new workflow |
| PUT | `/api/v1/workflows/{id}` | Update existing workflow |
| DELETE | `/api/v1/workflows/{id}` | Delete workflow |
| POST | `/api/v1/workflows/{id}/activate` | Activate workflow |
| POST | `/api/v1/workflows/{id}/deactivate` | Deactivate workflow |

### Execution

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/workflows/{id}/execute` | Execute workflow |
| GET | `/api/v1/executions` | List executions |
| GET | `/api/v1/executions/{id}` | Get execution details |

### Webhooks

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST/GET | `/webhook/{path}` | Trigger production webhook |
| POST/GET | `/webhook-test/{path}` | Trigger test webhook |

---

## Local LLM Configuration

To use local models (LM Studio, Ollama) with AI Agent nodes:

### Setup Steps

1. Use `@n8n/n8n-nodes-langchain.lmChatOpenAi` node (OpenAI Chat Model)
2. Create an OpenAI API credential with:
   - API Key: Any non-empty string (e.g., "lm-studio" or "not-needed")
3. In the node parameters, set:
   - Base URL: `http://host.docker.internal:1234/v1` (LM Studio) or `http://host.docker.internal:11434/v1` (Ollama)
   - Model: Exact name of the loaded model

### Timeout Considerations

**Important:** AI Agent nodes have a hardcoded 5-minute timeout. For longer operations:
- Use HTTP Request node directly with custom timeout (up to 60 minutes)
- Configure `EXECUTIONS_TIMEOUT` environment variable in Docker

### Example Configuration

```json
{
  "type": "@n8n/n8n-nodes-langchain.lmChatOpenAi",
  "parameters": {
    "model": "deepseek-r1-distil-qwen-7b",
    "options": {
      "baseURL": "http://host.docker.internal:1234/v1",
      "timeout": 300000
    }
  },
  "credentials": {
    "openAiApi": {
      "id": "your-credential-id",
      "name": "Local LLM"
    }
  }
}
```

---

## MCP Server Configuration

### n8n as MCP Server (expose workflows to Claude)

Add to Claude's MCP configuration (`~/.config/claude/mcp.json` or similar):

```json
{
  "mcpServers": {
    "n8n": {
      "command": "npx",
      "args": ["@anthropic/n8n-mcp-server"],
      "env": {
        "N8N_API_URL": "http://localhost:5678",
        "N8N_API_KEY": "${N8N_API_KEY}"
      }
    }
  }
}
```

**Note:** Ensure the n8n MCP server package is installed: `npm install -g @anthropic/n8n-mcp-server`

### n8n as MCP Client

Use the MCP Client Tool node (`@n8n/n8n-nodes-langchain.toolMcp`) with SSE endpoint of an external MCP server.

---

## Error Handling Patterns

### Global Error Workflow

1. Create a dedicated error handler workflow with Error Trigger node
2. Go to Settings > Error Workflow and select your error handler
3. All workflow errors will trigger this handler

### Node-Level Retry

Enable "Retry On Fail" in node settings:
- Attempts: 3-5 for API calls
- Wait Between Tries: 5000ms (5 seconds)
- Max Timeout: Based on expected response time

### Continue On Fail

For batch processing where individual failures shouldn't stop execution:
- Enable "Continue On Fail" on the node
- Handle errors in subsequent nodes using `$input.first().error`

### AI Agent Fallbacks

Configure fallback model in AI Agent nodes:
- Primary: Local LLM for speed
- Fallback: Cloud API for reliability

---

## Docker Compose Reference

```yaml
version: '3.8'

services:
  n8n:
    image: n8nio/n8n:latest
    container_name: n8n
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - DB_POSTGRESDB_DATABASE=n8n
      - DB_POSTGRESDB_USER=n8n
      - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
      - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
      - EXECUTIONS_TIMEOUT=3600
      - EXECUTIONS_TIMEOUT_MAX=7200
      - N8N_SECURE_COOKIE=false
      - GENERIC_TIMEZONE=America/New_York
    volumes:
      - n8n_data:/home/node/.n8n
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      - postgres

  postgres:
    image: postgres:15-alpine
    container_name: n8n-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=n8n
      - POSTGRES_USER=n8n
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  n8n_data:
  postgres_data:
```

**Linux Note:** The `extra_hosts` directive enables `host.docker.internal` on Linux. This is automatic on macOS/Windows.

---

## Bundled Scripts

Located in `${CLAUDE_PLUGIN_ROOT}/scripts/`:

| Script | Purpose |
|--------|---------|
| `generate_workflow.py` | Generate workflow JSON from specifications |
| `validate_workflow.py` | Validate workflow JSON structure |
| `deploy_workflow.py` | Deploy workflow via n8n API |

### Environment Variables

```bash
export N8N_API_URL="http://localhost:5678/api/v1"
export N8N_API_KEY="your-api-key"
```

---

## Workflow Templates

See `${CLAUDE_PLUGIN_ROOT}/references/workflow-templates.md` for ready-to-use templates:

- Webhook trigger with JSON response
- AI Agent with local LLM
- Scheduled health monitoring
- Error handling workflow
- Multi-step data transformation
- Batch processing with error recovery

---

## Common Patterns

### Webhook with Immediate Response

```json
{
  "parameters": {
    "httpMethod": "POST",
    "path": "my-endpoint",
    "responseMode": "responseNode"
  }
}
```

Connect to `respondToWebhook` node for custom response.

### Conditional Branching

If node outputs:
- Index 0: True branch
- Index 1: False branch

```json
{
  "connections": {
    "If": {
      "main": [
        [{"node": "True Handler", "type": "main", "index": 0}],
        [{"node": "False Handler", "type": "main", "index": 0}]
      ]
    }
  }
}
```

### Expression Syntax

- Access current item: `{{ $json.fieldName }}`
- Access input from specific node: `{{ $('Node Name').item.json.field }}`
- JavaScript in expressions: `{{ $json.date ? new Date($json.date).toISOString() : null }}`
- Current timestamp: `{{ $now.toISO() }}`
