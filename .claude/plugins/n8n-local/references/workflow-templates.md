# N8N Workflow Templates

Ready-to-use workflow templates for common automation patterns.

## Table of Contents

1. [Webhook Echo](#webhook-echo)
2. [Webhook with JSON Processing](#webhook-with-json-processing)
3. [AI Agent with Local LLM](#ai-agent-with-local-llm)
4. [Scheduled Health Monitor](#scheduled-health-monitor)
5. [Error Handler Workflow](#error-handler-workflow)
6. [Batch Processor with Error Recovery](#batch-processor-with-error-recovery)
7. [Multi-Step Data Transform](#multi-step-data-transform)

---

## Webhook Echo

Simple webhook that echoes back the request body.

```json
{
  "name": "Webhook Echo",
  "nodes": [
    {
      "id": "webhook-trigger",
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 1.1,
      "position": [250, 300],
      "parameters": {
        "httpMethod": "POST",
        "path": "echo",
        "responseMode": "responseNode"
      },
      "webhookId": "echo-webhook"
    },
    {
      "id": "respond-node",
      "name": "Respond",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.1,
      "position": [450, 300],
      "parameters": {
        "respondWith": "json",
        "responseBody": "={{ $json }}"
      }
    }
  ],
  "connections": {
    "Webhook": {
      "main": [[{"node": "Respond", "type": "main", "index": 0}]]
    }
  },
  "active": false,
  "settings": {
    "executionOrder": "v1"
  }
}
```

**Endpoint:** `POST http://localhost:5678/webhook/echo`

---

## Webhook with JSON Processing

Webhook that processes incoming JSON and returns a transformed response.

```json
{
  "name": "JSON Processor",
  "nodes": [
    {
      "id": "webhook-1",
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 1.1,
      "position": [250, 300],
      "parameters": {
        "httpMethod": "POST",
        "path": "process",
        "responseMode": "responseNode"
      }
    },
    {
      "id": "code-1",
      "name": "Process Data",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [450, 300],
      "parameters": {
        "jsCode": "// Process incoming data\nconst input = items[0].json;\n\nreturn [{\n  json: {\n    processed: true,\n    timestamp: new Date().toISOString(),\n    original: input,\n    itemCount: Object.keys(input).length\n  }\n}];"
      }
    },
    {
      "id": "respond-1",
      "name": "Respond",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.1,
      "position": [650, 300],
      "parameters": {
        "respondWith": "json",
        "responseBody": "={{ $json }}"
      }
    }
  ],
  "connections": {
    "Webhook": {
      "main": [[{"node": "Process Data", "type": "main", "index": 0}]]
    },
    "Process Data": {
      "main": [[{"node": "Respond", "type": "main", "index": 0}]]
    }
  },
  "active": false,
  "settings": {
    "executionOrder": "v1"
  }
}
```

---

## AI Agent with Local LLM

AI Agent configured to use a local LLM via LM Studio or Ollama.

```json
{
  "name": "Local AI Agent",
  "nodes": [
    {
      "id": "trigger-1",
      "name": "Manual Trigger",
      "type": "n8n-nodes-base.manualTrigger",
      "typeVersion": 1,
      "position": [250, 300],
      "parameters": {}
    },
    {
      "id": "set-input",
      "name": "Set Input",
      "type": "n8n-nodes-base.set",
      "typeVersion": 3.4,
      "position": [450, 300],
      "parameters": {
        "mode": "manual",
        "assignments": {
          "assignments": [
            {
              "name": "input",
              "value": "Explain what n8n is in one sentence.",
              "type": "string"
            }
          ]
        }
      }
    },
    {
      "id": "agent-1",
      "name": "AI Agent",
      "type": "@n8n/n8n-nodes-langchain.agent",
      "typeVersion": 1.7,
      "position": [650, 300],
      "parameters": {
        "promptType": "define",
        "text": "={{ $json.input }}"
      }
    },
    {
      "id": "model-1",
      "name": "OpenAI Chat Model",
      "type": "@n8n/n8n-nodes-langchain.lmChatOpenAi",
      "typeVersion": 1.2,
      "position": [650, 520],
      "parameters": {
        "model": "deepseek-r1-distill-qwen-7b",
        "options": {
          "baseURL": "http://host.docker.internal:1234/v1",
          "timeout": 120000
        }
      },
      "credentials": {
        "openAiApi": {
          "id": "local-llm-cred",
          "name": "Local LLM"
        }
      }
    }
  ],
  "connections": {
    "Manual Trigger": {
      "main": [[{"node": "Set Input", "type": "main", "index": 0}]]
    },
    "Set Input": {
      "main": [[{"node": "AI Agent", "type": "main", "index": 0}]]
    },
    "OpenAI Chat Model": {
      "ai_languageModel": [[{"node": "AI Agent", "type": "ai_languageModel", "index": 0}]]
    }
  },
  "active": false,
  "settings": {
    "executionOrder": "v1"
  }
}
```

**Setup Requirements:**
1. Create an OpenAI API credential named "Local LLM" with any API key value
2. Start LM Studio with a model loaded on port 1234
3. Adjust the model name to match your loaded model

---

## Scheduled Health Monitor

Monitors an endpoint every 5 minutes and logs status.

```json
{
  "name": "Health Monitor",
  "nodes": [
    {
      "id": "schedule-1",
      "name": "Schedule",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1.2,
      "position": [250, 300],
      "parameters": {
        "rule": {
          "interval": [{"field": "minutes", "minutesInterval": 5}]
        }
      }
    },
    {
      "id": "http-1",
      "name": "Check Endpoint",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.1,
      "position": [450, 300],
      "parameters": {
        "url": "https://api.example.com/health",
        "method": "GET",
        "options": {
          "timeout": 10000
        }
      }
    },
    {
      "id": "if-1",
      "name": "Check Status",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [650, 300],
      "parameters": {
        "conditions": {
          "options": {
            "caseSensitive": true,
            "leftValue": "",
            "typeValidation": "strict"
          },
          "conditions": [{
            "leftValue": "={{ $response.statusCode }}",
            "rightValue": 200,
            "operator": {"type": "number", "operation": "equals"}
          }]
        }
      }
    },
    {
      "id": "set-healthy",
      "name": "Log Healthy",
      "type": "n8n-nodes-base.set",
      "typeVersion": 3.4,
      "position": [850, 200],
      "parameters": {
        "mode": "manual",
        "assignments": {
          "assignments": [
            {"name": "status", "value": "healthy", "type": "string"},
            {"name": "timestamp", "value": "={{ $now.toISO() }}", "type": "string"}
          ]
        }
      }
    },
    {
      "id": "set-unhealthy",
      "name": "Log Unhealthy",
      "type": "n8n-nodes-base.set",
      "typeVersion": 3.4,
      "position": [850, 400],
      "parameters": {
        "mode": "manual",
        "assignments": {
          "assignments": [
            {"name": "status", "value": "unhealthy", "type": "string"},
            {"name": "timestamp", "value": "={{ $now.toISO() }}", "type": "string"},
            {"name": "error", "value": "={{ $json.error || 'Non-200 response' }}", "type": "string"}
          ]
        }
      }
    }
  ],
  "connections": {
    "Schedule": {
      "main": [[{"node": "Check Endpoint", "type": "main", "index": 0}]]
    },
    "Check Endpoint": {
      "main": [[{"node": "Check Status", "type": "main", "index": 0}]]
    },
    "Check Status": {
      "main": [
        [{"node": "Log Healthy", "type": "main", "index": 0}],
        [{"node": "Log Unhealthy", "type": "main", "index": 0}]
      ]
    }
  },
  "active": false,
  "settings": {
    "executionOrder": "v1"
  }
}
```

---

## Error Handler Workflow

Global error handler that captures workflow failures.

```json
{
  "name": "Global Error Handler",
  "nodes": [
    {
      "id": "error-trigger-1",
      "name": "Error Trigger",
      "type": "n8n-nodes-base.errorTrigger",
      "typeVersion": 1,
      "position": [250, 300],
      "parameters": {}
    },
    {
      "id": "format-error",
      "name": "Format Error",
      "type": "n8n-nodes-base.set",
      "typeVersion": 3.4,
      "position": [450, 300],
      "parameters": {
        "mode": "manual",
        "assignments": {
          "assignments": [
            {"name": "workflow_name", "value": "={{ $json.workflow.name }}", "type": "string"},
            {"name": "workflow_id", "value": "={{ $json.workflow.id }}", "type": "string"},
            {"name": "error_node", "value": "={{ $json.execution.error.node.name }}", "type": "string"},
            {"name": "error_message", "value": "={{ $json.execution.error.message }}", "type": "string"},
            {"name": "execution_id", "value": "={{ $json.execution.id }}", "type": "string"},
            {"name": "timestamp", "value": "={{ $now.toISO() }}", "type": "string"}
          ]
        }
      }
    },
    {
      "id": "code-log",
      "name": "Log Error",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [650, 300],
      "parameters": {
        "jsCode": "// Log error details\nconsole.error('Workflow Error:', JSON.stringify(items[0].json, null, 2));\n\n// You can add additional error handling here:\n// - Send to Slack/Discord\n// - Write to database\n// - Send email notification\n\nreturn items;"
      }
    }
  ],
  "connections": {
    "Error Trigger": {
      "main": [[{"node": "Format Error", "type": "main", "index": 0}]]
    },
    "Format Error": {
      "main": [[{"node": "Log Error", "type": "main", "index": 0}]]
    }
  },
  "active": false,
  "settings": {
    "executionOrder": "v1"
  }
}
```

**Setup:** Go to Settings > Error Workflow and select this workflow.

---

## Batch Processor with Error Recovery

Processes items in batches with individual error handling.

```json
{
  "name": "Batch Processor",
  "nodes": [
    {
      "id": "trigger-1",
      "name": "Manual Trigger",
      "type": "n8n-nodes-base.manualTrigger",
      "typeVersion": 1,
      "position": [250, 300],
      "parameters": {}
    },
    {
      "id": "set-items",
      "name": "Set Items",
      "type": "n8n-nodes-base.set",
      "typeVersion": 3.4,
      "position": [450, 300],
      "parameters": {
        "mode": "raw",
        "jsonOutput": "[{\"id\": 1, \"url\": \"https://api.example.com/1\"}, {\"id\": 2, \"url\": \"https://api.example.com/2\"}, {\"id\": 3, \"url\": \"https://api.example.com/3\"}]"
      }
    },
    {
      "id": "batch-1",
      "name": "Loop Over Items",
      "type": "n8n-nodes-base.splitInBatches",
      "typeVersion": 3,
      "position": [650, 300],
      "parameters": {
        "batchSize": 1,
        "options": {}
      }
    },
    {
      "id": "http-process",
      "name": "Process Item",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.1,
      "position": [850, 300],
      "parameters": {
        "url": "={{ $json.url }}",
        "method": "GET",
        "options": {
          "timeout": 10000
        }
      },
      "continueOnFail": true
    },
    {
      "id": "if-error",
      "name": "Check Error",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [1050, 300],
      "parameters": {
        "conditions": {
          "options": {
            "caseSensitive": true,
            "leftValue": "",
            "typeValidation": "strict"
          },
          "conditions": [{
            "leftValue": "={{ $json.error }}",
            "rightValue": "",
            "operator": {"type": "string", "operation": "notEmpty"}
          }]
        }
      }
    },
    {
      "id": "set-error",
      "name": "Log Failed",
      "type": "n8n-nodes-base.set",
      "typeVersion": 3.4,
      "position": [1250, 200],
      "parameters": {
        "mode": "manual",
        "assignments": {
          "assignments": [
            {"name": "status", "value": "failed", "type": "string"},
            {"name": "item_id", "value": "={{ $('Loop Over Items').item.json.id }}", "type": "number"}
          ]
        }
      }
    },
    {
      "id": "set-success",
      "name": "Log Success",
      "type": "n8n-nodes-base.set",
      "typeVersion": 3.4,
      "position": [1250, 400],
      "parameters": {
        "mode": "manual",
        "assignments": {
          "assignments": [
            {"name": "status", "value": "success", "type": "string"},
            {"name": "item_id", "value": "={{ $('Loop Over Items').item.json.id }}", "type": "number"}
          ]
        }
      }
    }
  ],
  "connections": {
    "Manual Trigger": {
      "main": [[{"node": "Set Items", "type": "main", "index": 0}]]
    },
    "Set Items": {
      "main": [[{"node": "Loop Over Items", "type": "main", "index": 0}]]
    },
    "Loop Over Items": {
      "main": [
        [{"node": "Process Item", "type": "main", "index": 0}],
        []
      ]
    },
    "Process Item": {
      "main": [[{"node": "Check Error", "type": "main", "index": 0}]]
    },
    "Check Error": {
      "main": [
        [{"node": "Log Failed", "type": "main", "index": 0}],
        [{"node": "Log Success", "type": "main", "index": 0}]
      ]
    },
    "Log Failed": {
      "main": [[{"node": "Loop Over Items", "type": "main", "index": 0}]]
    },
    "Log Success": {
      "main": [[{"node": "Loop Over Items", "type": "main", "index": 0}]]
    }
  },
  "active": false,
  "settings": {
    "executionOrder": "v1"
  }
}
```

---

## Multi-Step Data Transform

Chain of transformations with merge at the end.

```json
{
  "name": "Data Transform Pipeline",
  "nodes": [
    {
      "id": "webhook-1",
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 1.1,
      "position": [250, 300],
      "parameters": {
        "httpMethod": "POST",
        "path": "transform",
        "responseMode": "responseNode"
      }
    },
    {
      "id": "extract-fields",
      "name": "Extract Fields",
      "type": "n8n-nodes-base.set",
      "typeVersion": 3.4,
      "position": [450, 300],
      "parameters": {
        "mode": "manual",
        "assignments": {
          "assignments": [
            {"name": "name", "value": "={{ $json.name || 'Unknown' }}", "type": "string"},
            {"name": "email", "value": "={{ $json.email || '' }}", "type": "string"},
            {"name": "raw_data", "value": "={{ $json }}", "type": "object"}
          ]
        }
      }
    },
    {
      "id": "validate",
      "name": "Validate Data",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [650, 300],
      "parameters": {
        "jsCode": "const item = items[0].json;\nconst errors = [];\n\nif (!item.name || item.name === 'Unknown') {\n  errors.push('Name is required');\n}\n\nif (!item.email || !item.email.includes('@')) {\n  errors.push('Valid email is required');\n}\n\nreturn [{\n  json: {\n    ...item,\n    isValid: errors.length === 0,\n    errors: errors\n  }\n}];"
      }
    },
    {
      "id": "enrich",
      "name": "Enrich Data",
      "type": "n8n-nodes-base.set",
      "typeVersion": 3.4,
      "position": [850, 300],
      "parameters": {
        "mode": "manual",
        "assignments": {
          "assignments": [
            {"name": "processed_at", "value": "={{ $now.toISO() }}", "type": "string"},
            {"name": "name_lowercase", "value": "={{ $json.name.toLowerCase() }}", "type": "string"},
            {"name": "email_domain", "value": "={{ $json.email.split('@')[1] || '' }}", "type": "string"}
          ]
        },
        "includeOtherFields": true
      }
    },
    {
      "id": "respond-1",
      "name": "Respond",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.1,
      "position": [1050, 300],
      "parameters": {
        "respondWith": "json",
        "responseBody": "={{ $json }}"
      }
    }
  ],
  "connections": {
    "Webhook": {
      "main": [[{"node": "Extract Fields", "type": "main", "index": 0}]]
    },
    "Extract Fields": {
      "main": [[{"node": "Validate Data", "type": "main", "index": 0}]]
    },
    "Validate Data": {
      "main": [[{"node": "Enrich Data", "type": "main", "index": 0}]]
    },
    "Enrich Data": {
      "main": [[{"node": "Respond", "type": "main", "index": 0}]]
    }
  },
  "active": false,
  "settings": {
    "executionOrder": "v1"
  }
}
```

**Test with:**
```bash
curl -X POST http://localhost:5678/webhook/transform \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "email": "john@example.com"}'
```

---

## Usage Notes

1. **Import Templates:** Copy JSON and use n8n's import feature or the `deploy_workflow.py` script
2. **Credentials:** AI Agent templates require credential setup before use
3. **Activation:** All templates are created inactive - activate after testing
4. **Customization:** Adjust URLs, paths, and parameters for your environment
