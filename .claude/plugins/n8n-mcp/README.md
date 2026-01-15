# n8n-MCP Plugin

MCP integration for n8n workflow automation.

## Current Status: Documentation Mode

The plugin is configured to work without an API key, providing:
- Search 800+ n8n nodes
- Validate workflow configurations
- Discover 2700+ workflow templates
- Get node documentation

## Enable Full Mode (Workflow Management)

To manage workflows (create, update, execute), you need a UI-created API key:

1. Open n8n: http://localhost:5678
2. Go to: **Settings → n8n API**
3. Click **Create an API key**
4. Copy the generated key
5. Add to `.mcp.json`:

```json
"N8N_API_KEY": "your-api-key-from-ui"
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `N8N_API_URL` | n8n instance URL | For API mode |
| `N8N_API_KEY` | API key from n8n UI | For API mode |
| `MCP_MODE` | Must be `stdio` for Claude | Yes |
| `N8N_MCP_TELEMETRY_DISABLED` | Disable telemetry | Recommended |

## Local n8n Instance

Your n8n is running at: `http://localhost:5678`
Docker container: `n8n` (healthy)
