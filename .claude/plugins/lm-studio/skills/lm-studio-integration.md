---
name: lm-studio
description: |
  LM Studio local LLM integration for running AI models locally. Use when Claude needs to:
  - Interact with local language models via OpenAI-compatible API
  - Configure LM Studio server settings and parameters
  - Manage model loading, unloading, and switching
  - Estimate VRAM requirements for model selection
  - Configure MCP servers for tool integration
  - Integrate local LLMs with frameworks like LangChain or AutoGen
  - Optimize inference parameters and GPU utilization
---

# LM Studio Local LLM Integration

This skill enables interaction with LM Studio for running local Large Language Models with full control over inference parameters, hardware utilization, and tool integration.

## Quick Reference

### Server Endpoints

| Endpoint | URL |
|----------|-----|
| Base URL | `http://localhost:1234/v1` |
| Chat Completions | `POST /v1/chat/completions` |
| Embeddings | `POST /v1/embeddings` |
| List Models | `GET /v1/models` |
| Text Completions | `POST /v1/completions` |
| Stateful Responses | `POST /v1/responses` |

### Default Configuration

- **Port:** 1234 (configurable via `--port`)
- **API Key:** Not required, but use `"lm-studio"` for clients that require one
- **CORS:** Disabled by default, enable with `--cors` flag

---

## API Reference

LM Studio provides a fully OpenAI-compatible HTTP API.

### Chat Completions

```bash
curl http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-7b-instruct",
    "messages": [{"role": "user", "content": "Hello!"}],
    "temperature": 0.7,
    "max_tokens": 2048
  }'
```

### Streaming Response

```bash
curl http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-7b-instruct",
    "messages": [{"role": "user", "content": "Explain recursion"}],
    "stream": true
  }'
```

### Generate Embeddings

```bash
curl http://localhost:1234/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nomic-embed-text-v1.5",
    "input": "Text to embed for RAG"
  }'
```

### List Loaded Models

```bash
curl http://localhost:1234/v1/models
```

Response includes capability tags:
- `llm.chat` - Chat completion capable
- `embedding.text` - Text embedding capable
- `vision` - Multimodal/vision capable

---

## CLI Commands (`lms`)

The `lms` CLI enables headless operation and automation.

### Server Management

```bash
# Start server with CORS enabled
lms server start --port 1234 --cors

# Start on custom port
lms server start --port 8080

# Stop server
lms server stop

# Check server status
lms server status
```

### Model Management

```bash
# List downloaded models
lms ls
lms ls --json  # JSON output for scripting

# List currently loaded models
lms ps
lms ps --json

# Download model from Hugging Face
lms get deepseek-r1
lms get huggingface.co/username/model-name

# Download MLX-optimized model (Apple Silicon)
lms get --mlx <model>

# Load model with configuration
lms load <model> \
  --ttl 300 \
  --gpu auto \
  --context-length 8192

# Estimate VRAM before loading (dry run)
lms load --estimate-only <model>

# Unload model
lms unload <model>
```

### Logging & Monitoring

```bash
# Stream server logs
lms log stream --source server

# Stream inference logs with statistics
lms log stream --source model --filter input,output --stats

# JSON output for parsing
lms log stream --source model --json
```

### Interactive Chat

```bash
# Start interactive chat with current model
lms chat

# Show token statistics
lms chat --stats
```

---

## Inference Parameters

### Request Parameters

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `temperature` | float | 0.0-2.0 | Randomness. Lower = deterministic |
| `max_tokens` | int | 1-context | Maximum tokens to generate |
| `top_p` | float | 0.0-1.0 | Nucleus sampling threshold |
| `top_k` | int | 1-100+ | Top-k token sampling |
| `frequency_penalty` | float | -2.0-2.0 | Penalize frequent tokens |
| `presence_penalty` | float | -2.0-2.0 | Penalize repeated tokens |
| `stop` | array | - | Stop sequences |
| `stream` | bool | - | Enable streaming |

### Recommended Settings by Task

| Task | Temperature | Top P | Notes |
|------|-------------|-------|-------|
| Code Generation | 0.2-0.3 | 0.95 | Low temp for consistency |
| Reasoning | 0.5-0.7 | 0.95 | Moderate for exploration |
| Creative Writing | 0.8-1.0 | 0.9 | Higher for variety |
| Chat/Assistant | 0.7 | 0.95 | Balanced |
| Factual Q&A | 0.1-0.3 | 0.9 | Very low for accuracy |

### Load-Time Configuration

| Parameter | Description |
|-----------|-------------|
| `contextLength` | Context window size (tokens). Smaller = faster, less VRAM |
| `gpu.ratio` | GPU offload ratio (0.0 = CPU, 1.0 = full GPU) |
| `flashAttention` | Enable Flash Attention (NVIDIA RTX only) |
| `useFp16ForKVCache` | Half-precision KV cache (saves VRAM) |
| `evalBatchSize` | Tokens processed per batch |
| `ttl` | Auto-unload after N seconds idle |

---

## VRAM Requirements

### Quantization Levels

| Format | Quality | VRAM Multiplier | Use Case |
|--------|---------|-----------------|----------|
| Q4_K_M | Good | 1x (baseline) | Consumer hardware, best balance |
| Q5_K_M | Better | 1.25x | Slight quality boost |
| Q8_0 | High | 2x | Quality-focused, more VRAM |
| FP16 | Full | 4x | Research, workstations only |

### VRAM Estimation Table

| Model Size | Q4_K_M | Q8_0 | Recommended GPU |
|------------|--------|------|-----------------|
| 1.5B-3B | 2-4 GB | 4-6 GB | GTX 1650, RTX 3050 |
| 7B-9B | 5-8 GB | 10-14 GB | RTX 3060, 4060 |
| 13B-14B | 9-12 GB | 18-22 GB | RTX 3060 Ti, 4070 |
| 30B-35B | 18-24 GB | 36-48 GB | RTX 3090, 4090 |
| 70B | 38-48 GB | 76-96 GB | Multi-GPU, A100 |

### Quick Estimation Formula

```
VRAM (GB) ≈ Parameters (B) × Bits / 8 × 1.2 (overhead)

Q4_K_M: VRAM ≈ Params × 0.6
Q8_0:   VRAM ≈ Params × 1.2
FP16:   VRAM ≈ Params × 2.4
```

**Performance Note:** Models that fit entirely in VRAM run 10-30x faster than those requiring RAM offloading.

---

## Recommended Models

### Reasoning & Logic

**DeepSeek-R1 Distillations**
- Models: `deepseek-r1-distill-qwen-7b`, `deepseek-r1-distill-qwen-32b`
- Temperature: 0.5-0.7
- Special: No system prompt; put instructions in user message
- Math format: "Please reason step by step, and put your final answer within \boxed{}."

**NVIDIA Nemotron 3 Nano**
- Model: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-GGUF`
- Temperature: 1.0, Top P: 1.0
- Special: Use `/think` or `/no_think` control tokens

### Coding & Development

**Qwen3 Coder**
- Model: `qwen3-coder-30b-a3b-instruct`
- Temperature: 0.3
- Context: Up to 256k tokens
- Best for: Code completion, refactoring, explanation

**GLM-4.7**
- Model: `zai-org/GLM-4.7`
- Best for: Web development, multi-step tool use

### Vision (Multimodal)

**Qwen2.5-VL / Qwen3-VL**
- Models: `qwen2.5-vl-7b-instruct`, `qwen3-vl-8b-instruct`
- Config: Set image resize bounds to 2048px minimum
- Best for: Document analysis, image understanding

**LFM2.5-VL**
- Model: `LiquidAI/LFM2.5-VL-1.6B`
- Best for: Edge devices, laptops (optimized size)

### Embeddings

**Nomic Embed**
- Model: `nomic-embed-text-v1.5`
- Dimensions: 768
- Best for: RAG, semantic search

---

## MCP Server Configuration

LM Studio can act as an MCP Host, connecting to external tool servers.

### Configuration File

Location: `~/.lmstudio/mcp.json`

### Remote Server (HTTP/SSE)

```json
{
  "mcpServers": {
    "huggingface": {
      "url": "https://huggingface.co/mcp",
      "headers": {
        "Authorization": "Bearer ${HF_TOKEN}"
      }
    },
    "local-tools": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

### Local Server (stdio)

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-filesystem", "/path/to/allowed"]
    },
    "database": {
      "command": "python",
      "args": ["-m", "mcp_server_sqlite", "--db", "data.db"]
    }
  }
}
```

### Tool Choice Options

| Value | Behavior |
|-------|----------|
| `"auto"` | Model decides whether to use tools |
| `"required"` | Force tool usage |
| `"none"` | Disable tools for this request |
| `{"type": "function", "function": {"name": "x"}}` | Force specific tool |

---

## Python Integration

### Basic Usage (OpenAI Client)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio"  # Required by client, any value works
)

response = client.chat.completions.create(
    model="qwen2.5-7b-instruct",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain Python decorators."}
    ],
    temperature=0.7,
    max_tokens=2048
)

print(response.choices[0].message.content)
```

### Streaming

```python
stream = client.chat.completions.create(
    model="deepseek-r1-distill-qwen-7b",
    messages=[{"role": "user", "content": "Write a sorting algorithm"}],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

### Generate Embeddings

```python
response = client.embeddings.create(
    model="nomic-embed-text-v1.5",
    input=["First document", "Second document"]
)

embeddings = [item.embedding for item in response.data]
```

---

## TypeScript SDK

```typescript
import { LMStudioClient } from "@lmstudio/sdk";

const client = new LMStudioClient();

// Load model with configuration
const model = await client.llm.load("qwen2.5-7b-instruct", {
  config: {
    contextLength: 8192,
    gpu: { ratio: 1.0 },
    flashAttention: true,
    useFp16ForKVCache: true
  }
});

// Run inference
const response = await model.respond([
  { role: "system", content: "You are a coding assistant." },
  { role: "user", content: "Write a binary search in Python." }
]);

console.log(response.content);

// Unload when done
await model.unload();
```

---

## Framework Integration

### LangChain

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio",
    model="qwen2.5-7b-instruct",
    temperature=0.7
)

response = llm.invoke("What is the capital of France?")
print(response.content)
```

### AutoGen

```python
import autogen

config_list = [{
    "model": "qwen2.5-7b-instruct",
    "base_url": "http://localhost:1234/v1",
    "api_key": "lm-studio"
}]

assistant = autogen.AssistantAgent(
    name="assistant",
    llm_config={"config_list": config_list}
)

user_proxy = autogen.UserProxyAgent(
    name="user",
    human_input_mode="NEVER"
)

user_proxy.initiate_chat(assistant, message="Write a hello world in Rust")
```

### n8n Integration

For n8n AI Agent nodes, use the OpenAI Chat Model node:
- Base URL: `http://host.docker.internal:1234/v1` (Docker)
- API Key: Any non-empty string
- Model: Exact model name from `lms ps`

See the `n8n-local` skill for detailed configuration.

---

## Performance Optimization

### Hardware Recommendations

1. **Enable Flash Attention** - NVIDIA RTX GPUs only, significant speedup
2. **Use Q4_K_M quantization** - Best speed/quality balance
3. **Set appropriate context length** - Smaller = faster, less VRAM
4. **Enable FP16 KV Cache** - Reduces memory with minimal quality loss
5. **Configure idle TTL** - Auto-unload unused models

### Speculative Decoding

Use a small "draft" model to speed up generation by 2-3x:

```json
{
  "model": "deepseek-r1-distill-qwen-32b",
  "draft_model": "deepseek-r1-distill-qwen-1.5b",
  "messages": [{"role": "user", "content": "..."}]
}
```

Requirements:
- Draft model must be same architecture family
- Draft model should be 4-8x smaller

### Batching Multiple Requests

For batch processing, use connection pooling and async requests:

```python
import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio"
)

async def process_batch(prompts: list[str]) -> list[str]:
    tasks = [
        client.chat.completions.create(
            model="qwen2.5-7b-instruct",
            messages=[{"role": "user", "content": p}]
        )
        for p in prompts
    ]
    responses = await asyncio.gather(*tasks)
    return [r.choices[0].message.content for r in responses]
```

---

## System Requirements

### macOS (Apple Silicon)

- **Chip:** M1/M2/M3/M4 required (Intel not supported)
- **OS:** macOS 13.4+ (14.0+ for MLX backend)
- **Memory:** 16GB+ unified memory recommended
- **Backend:** Metal (default), MLX (optional)

### Windows

- **CPU:** x64 with AVX2 or ARM64 (Snapdragon X Elite)
- **RAM:** 16GB+ system memory
- **GPU:** NVIDIA RTX (CUDA 12.8) or AMD (ROCm)
- **VRAM:** 4GB+ dedicated minimum, 8GB+ recommended

### Linux

- **Distro:** Ubuntu 20.04+ (via AppImage)
- **CPU:** x64 with AVX2
- **RAM:** 16GB+ system memory
- **GPU:** NVIDIA (CUDA) or AMD (ROCm)
- **VRAM:** 8GB+ recommended

---

## Bundled Scripts

Located in `${CLAUDE_PLUGIN_ROOT}/scripts/`:

| Script | Purpose |
|--------|---------|
| `check_vram.py` | Estimate VRAM requirements for models |
| `server_health.py` | Monitor server status and loaded models |
| `model_benchmark.py` | Benchmark inference performance |

### Environment Variables

```bash
export LM_STUDIO_URL="http://localhost:1234"
```

---

## Troubleshooting

### Server Won't Start

```bash
# Check if port is in use
lsof -i :1234

# Start on different port
lms server start --port 8080
```

### Model Loading Fails

```bash
# Check available VRAM
lms load --estimate-only <model>

# Try lower context length
lms load <model> --context-length 4096

# Try CPU offloading
lms load <model> --gpu 0.5
```

### Slow Inference

1. Ensure model fits in VRAM (`lms load --estimate-only`)
2. Enable Flash Attention for RTX GPUs
3. Reduce context length
4. Use Q4_K_M quantization

### Connection Refused

```bash
# Verify server is running
lms server status

# Check CORS if using browser
lms server start --cors
```
