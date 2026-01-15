# Session State - January 14, 2026 (Updated)

## Last Action
Installed **n8n-mcp** plugin from https://github.com/czlonkowski/n8n-mcp

## Immediate Next Step
**Restart Claude Code** to load the new n8n-mcp MCP server, then test the tools.

---

## ARTHUR_RAG Project Architecture

### Plugin Structure
```
/Users/arthurdell/ARTHUR_RAG/.claude/plugins/
├── apple-notes-rag/       # Semantic search for Apple Notes (LanceDB + embeddings)
│   ├── export_notes.py    # JXA export from Apple Notes
│   ├── sync_to_rag.py     # Incremental sync with hash detection
│   ├── query_rag.py       # Semantic + freshness search
│   └── models_expert.py   # LM Studio model recommendations
├── notebooklm/            # Google NotebookLM integration
│   ├── batch_processor.py # Token optimization (extract once, query locally)
│   ├── service_status.py  # Health monitoring
│   └── verify_auth.py     # OAuth verification
├── lm-studio/             # Local LLM inference
│   ├── server_health.py   # Server monitoring
│   ├── model_benchmark.py # Performance testing
│   └── check_vram.py      # VRAM estimation
├── n8n-local/             # Workflow automation scripts
│   ├── deploy_workflow.py # REST API deployment
│   └── workflows/         # JSON workflow files
├── n8n-mcp/               # [NEW] N8N MCP integration
│   ├── .mcp.json          # MCP server config
│   ├── plugin.json        # Plugin metadata
│   └── README.md          # Setup documentation
└── adversarial-validator/ # Proposal validation framework
    ├── validate_proposal.py
    └── pre_mortem.py
```

### External Services
| Service | URL | Status | Purpose |
|---------|-----|--------|---------|
| LM Studio | http://localhost:1234 | Check on restart | Local embeddings + chat |
| n8n | http://localhost:5678 | Running (Docker) | Workflow automation |
| n8n-postgres | Docker container | Running | n8n database |

---

## n8n-mcp Installation (NEW)

### Configuration
File: `/Users/arthurdell/ARTHUR_RAG/.claude/plugins/n8n-mcp/.mcp.json`
```json
{
  "n8n-mcp": {
    "command": "npx",
    "args": ["n8n-mcp"],
    "env": {
      "MCP_MODE": "stdio",
      "LOG_LEVEL": "error",
      "DISABLE_CONSOLE_OUTPUT": "true",
      "N8N_API_URL": "http://localhost:5678",
      "N8N_MCP_TELEMETRY_DISABLED": "true"
    }
  }
}
```

### Current Mode: Documentation Only
Available tools after restart:
- Search 800+ n8n nodes
- Validate workflow configurations
- Discover 2700+ workflow templates

### To Enable Full Workflow Management
n8n v2.x requires UI-created API keys:
1. Open http://localhost:5678
2. Settings → n8n API → Create API key
3. Add `"N8N_API_KEY": "your-key"` to `.mcp.json`

---

## Apple Notes RAG System

### Database
- Location: `~/.apple-notes-rag/`
- Engine: LanceDB (serverless)
- Embeddings: 768-dim (nomic-embed-text-v1.5)

### Key Methods
| Method | File | Purpose |
|--------|------|---------|
| `search()` | query_rag.py | Semantic similarity search |
| `search_hybrid()` | query_rag.py | Semantic + keyword + freshness |
| `sync_incremental()` | sync_to_rag.py | SHA-256 hash change detection |
| `calculate_freshness_score()` | query_rag.py | Exponential decay: e^(-λ*days) |
| `detect_query_type()` | query_rag.py | Auto-detect current/balanced/historical |

### Query Type Presets
| Type | Freshness Weight | Decay Rate | Use Case |
|------|-----------------|------------|----------|
| current | 0.4 | 0.02 | Contact info, recent updates |
| balanced | 0.2 | 0.005 | General search |
| historical | 0.0 | N/A | Research, old content |

### Commands
- `/sync-notes mode=full|incremental`
- `/query-notes query="..." folder="..." limit=10`
- `/models action=status|recommend|analyze`

---

## NotebookLM Token Optimization

### Strategy
```
WITHOUT OPTIMIZATION:          WITH BATCH PROCESSOR:
10 queries × 1000 tokens       1 extract × 500 tokens
= 10,000 tokens                + 10 local × 0 tokens
                               = 500 tokens (95% savings)
```

### Key Methods
- `extract_notebook_content()` - One-time cloud extraction
- `batch_summarize()` - Local summarization
- `batch_query()` - Multiple queries on extracted content
- `local_llm_process()` - Process via LM Studio (free)

---

## AI Daily Briefing Workflow (Previously Built)

### Status: FULLY OPERATIONAL

### Workflow ID
- `I01VLCz9d5gLdqSn` - AI Daily Briefing

### Architecture
```
Webhook (GET /webhook/briefing)
    │ [Header Auth: X-API-Key]
    ▼
Initialize → Gmail Unread → Calendar Today → Aggregate
    ▼
Build Prompt → OpenRouter API (Claude 3.5 Haiku) → Format → Respond
```

### Credentials in n8n
| Credential | ID | Type |
|------------|-----|------|
| Gmail account | 7g2mqiKshJ33stiG | gmailOAuth2 |
| Google Calendar | aS0fUlg6K3GiQib1 | googleCalendarOAuth2Api |
| Webhook API Key | 6190621fcc051461 | httpHeaderAuth |
| OpenRouter API | ab21ae1595524265 | httpHeaderAuth |

### Test Command
```bash
WEBHOOK_SECRET=$(grep N8N_WEBHOOK_SECRET ~/.n8n/.env | cut -d'=' -f2)
curl -s "http://localhost:5678/webhook/briefing" \
  -H "X-API-Key: ${WEBHOOK_SECRET}" | jq '.'
```

---

## Environment Variables

### Location: `/Users/arthurdell/.n8n/.env`
```
POSTGRES_PASSWORD=da5744d12ac79ea88730e8f4dd0e6cd3
N8N_WEBHOOK_SECRET=5b01deb51f6dd71cb04f6db57ec8a28cfa8da9e49a01ec916b59c8481e4deedc
N8N_API_KEY=f1f79894bfe96f3416c08929d3fe4372dca8fd34f14e157e1eacd8ae50b113a2
OPENROUTER_API_KEY=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
```

Note: `N8N_API_KEY` is for internal/webhook auth. REST API requires UI-created key.

---

## Docker Commands

```bash
# Start n8n
cd ~/.n8n && docker-compose up -d

# Check status
docker ps | grep n8n

# View logs
docker logs n8n --tail 50

# Restart
docker restart n8n
```

---

## After Restart Checklist

- [ ] Verify n8n-mcp tools are available (`mcp__n8n-mcp__*`)
- [ ] Test node search: "search for Gmail node"
- [ ] Test workflow validation
- [ ] (Optional) Create API key in n8n UI for workflow management
- [ ] Check LM Studio is running for embedding operations

---

## Session History Summary

1. **Project Overview Request** - Documented all 5 plugins with methods and workflows
2. **Architecture Diagrams** - Created workflow diagrams for data flow
3. **n8n-mcp Installation** - Installed from github.com/czlonkowski/n8n-mcp
   - Configured for local n8n at localhost:5678
   - Set up documentation mode (API key optional)
   - Disabled telemetry
4. **Session State Save** - This document for context continuity
