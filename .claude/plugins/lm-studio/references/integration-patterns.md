# LM Studio Integration Patterns

Ready-to-use code patterns for integrating LM Studio with various frameworks and use cases.

## Table of Contents

1. [RAG Pipeline with Local Embeddings](#rag-pipeline-with-local-embeddings)
2. [Multi-Model Orchestration](#multi-model-orchestration)
3. [Async Batch Processing](#async-batch-processing)
4. [IDE Integration (Continue.dev)](#ide-integration-continuedev)
5. [Streaming with Progress](#streaming-with-progress)
6. [Tool Use / Function Calling](#tool-use--function-calling)
7. [Vision Model Integration](#vision-model-integration)
8. [Auto-Eviction Batch Processing](#auto-eviction-batch-processing)

---

## RAG Pipeline with Local Embeddings

Complete RAG implementation using local embedding and chat models.

```python
#!/usr/bin/env python3
"""RAG pipeline with LM Studio local models."""

from openai import OpenAI
import numpy as np
from typing import Any

# Initialize client
client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio"
)

# Configuration
EMBEDDING_MODEL = "nomic-embed-text-v1.5"
CHAT_MODEL = "qwen2.5-7b-instruct"


def get_embedding(text: str) -> list[float]:
    """Generate embedding for text using local model."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a_np, b_np = np.array(a), np.array(b)
    return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))


class SimpleVectorStore:
    """Simple in-memory vector store for demonstration."""

    def __init__(self):
        self.documents: list[str] = []
        self.embeddings: list[list[float]] = []

    def add_documents(self, docs: list[str]) -> None:
        """Add documents to the store."""
        for doc in docs:
            embedding = get_embedding(doc)
            self.documents.append(doc)
            self.embeddings.append(embedding)

    def search(self, query: str, top_k: int = 3) -> list[tuple[str, float]]:
        """Search for similar documents."""
        query_embedding = get_embedding(query)

        similarities = [
            (doc, cosine_similarity(query_embedding, emb))
            for doc, emb in zip(self.documents, self.embeddings)
        ]

        return sorted(similarities, key=lambda x: x[1], reverse=True)[:top_k]


def rag_query(store: SimpleVectorStore, query: str) -> str:
    """Perform RAG query."""
    # Retrieve relevant documents
    relevant_docs = store.search(query, top_k=3)
    context = "\n\n".join([doc for doc, score in relevant_docs])

    # Generate response with context
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": f"Answer based on the following context:\n\n{context}"
            },
            {"role": "user", "content": query}
        ],
        temperature=0.3,
        max_tokens=500
    )

    return response.choices[0].message.content


# Example usage
if __name__ == "__main__":
    # Create and populate vector store
    store = SimpleVectorStore()
    store.add_documents([
        "Python is a high-level programming language known for its readability.",
        "JavaScript is the language of the web, running in browsers.",
        "Rust provides memory safety without garbage collection.",
        "Go was designed at Google for building scalable systems.",
    ])

    # Query
    answer = rag_query(store, "Which language is best for web development?")
    print(f"Answer: {answer}")
```

---

## Multi-Model Orchestration

Use specialized models for different tasks in a pipeline.

```python
#!/usr/bin/env python3
"""Multi-model orchestration for complex tasks."""

from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio"
)

# Model assignments
MODELS = {
    "reasoning": "deepseek-r1-distill-qwen-32b",
    "coding": "qwen3-coder-30b-a3b-instruct",
    "general": "qwen2.5-7b-instruct",
}


def reasoning_agent(prompt: str) -> str:
    """Use reasoning model for complex logic."""
    response = client.chat.completions.create(
        model=MODELS["reasoning"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=2000
    )
    return response.choices[0].message.content


def coding_agent(prompt: str) -> str:
    """Use coding model for implementation."""
    response = client.chat.completions.create(
        model=MODELS["coding"],
        messages=[
            {
                "role": "system",
                "content": "You are an expert programmer. Write clean, well-documented code."
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=2000
    )
    return response.choices[0].message.content


def summarizer_agent(text: str) -> str:
    """Use general model for summarization."""
    response = client.chat.completions.create(
        model=MODELS["general"],
        messages=[
            {
                "role": "system",
                "content": "Summarize the following text concisely."
            },
            {"role": "user", "content": text}
        ],
        temperature=0.3,
        max_tokens=500
    )
    return response.choices[0].message.content


def solve_coding_problem(problem: str) -> dict:
    """
    Orchestrate multiple models to solve a coding problem.

    1. Reasoning model plans the approach
    2. Coding model implements the solution
    3. General model summarizes the solution
    """
    # Step 1: Plan
    print("Planning approach...")
    plan = reasoning_agent(
        f"Plan how to solve this coding problem step by step:\n\n{problem}"
    )

    # Step 2: Implement
    print("Implementing solution...")
    code = coding_agent(
        f"Based on this plan:\n{plan}\n\nImplement the solution in Python."
    )

    # Step 3: Summarize
    print("Summarizing...")
    summary = summarizer_agent(
        f"Problem: {problem}\n\nSolution:\n{code}"
    )

    return {
        "problem": problem,
        "plan": plan,
        "code": code,
        "summary": summary
    }


if __name__ == "__main__":
    result = solve_coding_problem(
        "Implement a thread-safe rate limiter that allows N requests per second"
    )

    print("\n" + "=" * 60)
    print("SOLUTION SUMMARY")
    print("=" * 60)
    print(result["summary"])

    print("\n" + "=" * 60)
    print("CODE")
    print("=" * 60)
    print(result["code"])
```

---

## Async Batch Processing

Process multiple requests concurrently for better throughput.

```python
#!/usr/bin/env python3
"""Async batch processing with LM Studio."""

import asyncio
from openai import AsyncOpenAI
from typing import Any

# Initialize async client
client = AsyncOpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio"
)

MODEL = "qwen2.5-7b-instruct"


async def process_single(
    prompt: str,
    index: int,
    max_tokens: int = 200
) -> dict[str, Any]:
    """Process a single prompt asynchronously."""
    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.7
        )
        return {
            "index": index,
            "prompt": prompt[:50] + "...",
            "response": response.choices[0].message.content,
            "tokens": response.usage.completion_tokens if response.usage else 0,
            "success": True
        }
    except Exception as e:
        return {
            "index": index,
            "prompt": prompt[:50] + "...",
            "error": str(e),
            "success": False
        }


async def process_batch(
    prompts: list[str],
    max_concurrent: int = 5,
    max_tokens: int = 200
) -> list[dict[str, Any]]:
    """Process batch of prompts with concurrency limit."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def limited_process(prompt: str, index: int) -> dict[str, Any]:
        async with semaphore:
            return await process_single(prompt, index, max_tokens)

    tasks = [
        limited_process(prompt, i)
        for i, prompt in enumerate(prompts)
    ]

    results = await asyncio.gather(*tasks)
    return list(results)


async def main():
    """Example batch processing."""
    prompts = [
        "What is the capital of France?",
        "Explain recursion in one sentence.",
        "Name three programming languages.",
        "What is 25 * 4?",
        "Define machine learning briefly.",
        "What color is the sky?",
        "Name a famous scientist.",
        "What is HTTP?",
    ]

    print(f"Processing {len(prompts)} prompts...")

    results = await process_batch(prompts, max_concurrent=3)

    print("\nResults:")
    print("-" * 60)

    successful = sum(1 for r in results if r["success"])
    print(f"Success rate: {successful}/{len(results)}")

    for result in results:
        if result["success"]:
            print(f"\n[{result['index']}] {result['prompt']}")
            print(f"    Response: {result['response'][:100]}...")
        else:
            print(f"\n[{result['index']}] FAILED: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## IDE Integration (Continue.dev)

Configuration for Continue.dev VS Code extension.

**File: `~/.continue/config.json`**

```json
{
  "models": [
    {
      "title": "LM Studio - Qwen 7B",
      "provider": "openai",
      "model": "qwen2.5-7b-instruct",
      "apiBase": "http://localhost:1234/v1",
      "apiKey": "lm-studio",
      "contextLength": 32768
    },
    {
      "title": "LM Studio - DeepSeek R1",
      "provider": "openai",
      "model": "deepseek-r1-distill-qwen-7b",
      "apiBase": "http://localhost:1234/v1",
      "apiKey": "lm-studio",
      "contextLength": 32768
    }
  ],
  "tabAutocompleteModel": {
    "title": "LM Studio Autocomplete",
    "provider": "openai",
    "model": "qwen2.5-coder-7b-instruct",
    "apiBase": "http://localhost:1234/v1",
    "apiKey": "lm-studio"
  },
  "embeddingsProvider": {
    "provider": "openai",
    "model": "nomic-embed-text-v1.5",
    "apiBase": "http://localhost:1234/v1",
    "apiKey": "lm-studio"
  },
  "contextProviders": [
    {"name": "code", "params": {}},
    {"name": "docs", "params": {}},
    {"name": "diff", "params": {}},
    {"name": "terminal", "params": {}},
    {"name": "problems", "params": {}},
    {"name": "codebase", "params": {}}
  ],
  "slashCommands": [
    {"name": "edit", "description": "Edit selected code"},
    {"name": "comment", "description": "Add comments to code"},
    {"name": "share", "description": "Export conversation"}
  ]
}
```

---

## Streaming with Progress

Display real-time streaming output with progress tracking.

```python
#!/usr/bin/env python3
"""Streaming responses with progress display."""

import sys
import time
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio"
)


def stream_with_progress(
    prompt: str,
    model: str = "qwen2.5-7b-instruct",
    max_tokens: int = 500
) -> str:
    """Stream response with live token count."""

    print(f"Model: {model}")
    print(f"Prompt: {prompt[:50]}...")
    print("-" * 40)

    start_time = time.time()
    token_count = 0
    full_response = ""

    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        stream=True
    )

    for chunk in stream:
        if chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            full_response += content
            token_count += 1

            # Print content
            print(content, end="", flush=True)

    # Final stats
    elapsed = time.time() - start_time
    tps = token_count / elapsed if elapsed > 0 else 0

    print("\n" + "-" * 40)
    print(f"Tokens: {token_count}")
    print(f"Time: {elapsed:.2f}s")
    print(f"Speed: {tps:.1f} tok/s")

    return full_response


def stream_with_thinking(
    prompt: str,
    model: str = "deepseek-r1-distill-qwen-7b"
) -> tuple[str, str]:
    """Stream response that includes thinking/reasoning tokens."""

    thinking = ""
    answer = ""
    in_thinking = False

    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        stream=True
    )

    print("Thinking: ", end="", flush=True)

    for chunk in stream:
        if chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content

            # Detect thinking tags (varies by model)
            if "<think>" in content:
                in_thinking = True
                content = content.replace("<think>", "")
            if "</think>" in content:
                in_thinking = False
                content = content.replace("</think>", "")
                print("\n\nAnswer: ", end="", flush=True)

            if in_thinking:
                thinking += content
                print(".", end="", flush=True)  # Show progress
            else:
                answer += content
                print(content, end="", flush=True)

    print("\n")
    return thinking, answer


if __name__ == "__main__":
    # Simple streaming
    response = stream_with_progress(
        "Explain the concept of recursion in programming."
    )

    print("\n" + "=" * 60 + "\n")

    # Streaming with thinking (for reasoning models)
    thinking, answer = stream_with_thinking(
        "What is 15% of 340? Show your work."
    )

    print("Full thinking process:")
    print(thinking)
```

---

## Tool Use / Function Calling

Implement function calling with LM Studio.

```python
#!/usr/bin/env python3
"""Function calling / tool use with LM Studio."""

import json
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio"
)

# Define available tools
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name, e.g., 'San Francisco'"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Temperature unit"
                    }
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Perform mathematical calculations",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Math expression to evaluate"
                    }
                },
                "required": ["expression"]
            }
        }
    }
]


def execute_tool(name: str, arguments: dict) -> str:
    """Execute a tool and return result."""
    if name == "get_weather":
        # Simulated weather data
        location = arguments.get("location", "Unknown")
        unit = arguments.get("unit", "celsius")
        temp = 22 if unit == "celsius" else 72
        return json.dumps({
            "location": location,
            "temperature": temp,
            "unit": unit,
            "condition": "Sunny"
        })

    elif name == "calculate":
        expression = arguments.get("expression", "0")
        try:
            # WARNING: eval is dangerous in production!
            result = eval(expression)
            return json.dumps({"result": result})
        except Exception as e:
            return json.dumps({"error": str(e)})

    return json.dumps({"error": "Unknown tool"})


def chat_with_tools(
    user_message: str,
    model: str = "qwen2.5-7b-instruct"
) -> str:
    """Chat with tool use support."""

    messages = [{"role": "user", "content": user_message}]

    # First call: model decides whether to use tools
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto"
    )

    assistant_message = response.choices[0].message

    # Check if model wants to use tools
    if assistant_message.tool_calls:
        messages.append(assistant_message)

        # Execute each tool call
        for tool_call in assistant_message.tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            print(f"Calling tool: {function_name}({arguments})")

            result = execute_tool(function_name, arguments)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

        # Get final response with tool results
        final_response = client.chat.completions.create(
            model=model,
            messages=messages
        )

        return final_response.choices[0].message.content

    # No tool use, return direct response
    return assistant_message.content


if __name__ == "__main__":
    # Test tool use
    queries = [
        "What's the weather like in Tokyo?",
        "Calculate 15 * 23 + 47",
        "What's 2 to the power of 10?",
    ]

    for query in queries:
        print(f"\nUser: {query}")
        response = chat_with_tools(query)
        print(f"Assistant: {response}")
```

---

## Vision Model Integration

Use multimodal models for image understanding.

```python
#!/usr/bin/env python3
"""Vision model integration with LM Studio."""

import base64
from pathlib import Path
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio"
)

VISION_MODEL = "qwen2.5-vl-7b-instruct"


def encode_image(image_path: str) -> str:
    """Encode image to base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_image(
    image_path: str,
    prompt: str = "Describe this image in detail."
) -> str:
    """Analyze an image using vision model."""

    # Determine image type
    suffix = Path(image_path).suffix.lower()
    media_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp"
    }.get(suffix, "image/jpeg")

    base64_image = encode_image(image_path)

    response = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{base64_image}"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ],
        max_tokens=1000
    )

    return response.choices[0].message.content


def analyze_image_url(
    image_url: str,
    prompt: str = "Describe this image."
) -> str:
    """Analyze an image from URL."""

    response = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url}
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ],
        max_tokens=1000
    )

    return response.choices[0].message.content


def compare_images(
    image_path1: str,
    image_path2: str,
    prompt: str = "Compare these two images."
) -> str:
    """Compare two images."""

    base64_image1 = encode_image(image_path1)
    base64_image2 = encode_image(image_path2)

    response = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image1}"
                        }
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image2}"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ],
        max_tokens=1000
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    # Example usage (requires actual image files)
    print("Vision model examples:")
    print("1. analyze_image('photo.jpg', 'What objects are in this image?')")
    print("2. analyze_image_url('https://example.com/image.jpg')")
    print("3. compare_images('before.jpg', 'after.jpg')")
```

---

## Auto-Eviction Batch Processing

Process batches with automatic model eviction for resource management.

```python
#!/usr/bin/env python3
"""Batch processing with TTL-based auto-eviction."""

import time
from openai import OpenAI
from typing import Generator, Any

client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio"
)


def process_with_ttl(
    items: list[str],
    model: str = "qwen2.5-7b-instruct",
    ttl_seconds: int = 120,
    batch_size: int = 10
) -> Generator[dict[str, Any], None, None]:
    """
    Process items in batches with TTL for automatic cleanup.

    TTL ensures model is unloaded after idle period,
    freeing VRAM for other tasks.
    """

    total = len(items)
    processed = 0

    for i in range(0, total, batch_size):
        batch = items[i:i + batch_size]

        for j, item in enumerate(batch):
            try:
                # Include TTL in request for auto-eviction
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": item}],
                    max_tokens=200,
                    extra_body={"ttl": ttl_seconds}  # Auto-unload after idle
                )

                processed += 1
                yield {
                    "index": i + j,
                    "input": item[:50] + "...",
                    "output": response.choices[0].message.content,
                    "success": True,
                    "progress": f"{processed}/{total}"
                }

            except Exception as e:
                processed += 1
                yield {
                    "index": i + j,
                    "input": item[:50] + "...",
                    "error": str(e),
                    "success": False,
                    "progress": f"{processed}/{total}"
                }

        # Small delay between batches to prevent overwhelming
        if i + batch_size < total:
            time.sleep(0.5)


def bulk_summarize(
    documents: list[str],
    model: str = "qwen2.5-7b-instruct"
) -> list[dict[str, Any]]:
    """Summarize multiple documents efficiently."""

    prompts = [
        f"Summarize this in one sentence:\n\n{doc}"
        for doc in documents
    ]

    results = []
    for result in process_with_ttl(prompts, model, ttl_seconds=60):
        results.append(result)
        print(f"Progress: {result['progress']}")

    return results


if __name__ == "__main__":
    # Example documents
    documents = [
        "Python is a versatile programming language...",
        "Machine learning enables computers to learn...",
        "Cloud computing provides on-demand resources...",
        # Add more documents...
    ]

    print("Starting batch summarization...")
    summaries = bulk_summarize(documents)

    print("\nResults:")
    for s in summaries:
        if s["success"]:
            print(f"  [{s['index']}] {s['output'][:80]}...")
        else:
            print(f"  [{s['index']}] ERROR: {s['error']}")
```

---

## Usage Notes

1. **Model Availability**: Ensure required models are loaded in LM Studio before running
2. **VRAM Management**: For multi-model workflows, consider VRAM requirements
3. **Error Handling**: All examples include basic error handling; enhance for production
4. **Rate Limiting**: LM Studio handles requests sequentially; async batching helps throughput
5. **TTL Configuration**: Use TTL for automatic resource cleanup in batch processing
