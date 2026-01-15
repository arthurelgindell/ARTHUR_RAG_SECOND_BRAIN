#!/usr/bin/env python3
"""
NotebookLM HTTP Bridge for ARTHUR Agent

This service provides an HTTP API for NotebookLM operations,
bridging n8n workflows to the NotebookLM MCP server.

Usage:
    python notebooklm_bridge.py

Environment Variables:
    NOTEBOOKLM_MCP_URL - MCP server URL (default: http://localhost:3000)

HTTP Endpoints:
    POST /research - Start research on a topic
    POST /query - Query existing notebook
    GET /notebooks - List notebooks
    GET /health - Health check
"""

import os
import subprocess
import json
from typing import Optional
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuration
NOTEBOOKLM_MCP_URL = os.environ.get("NOTEBOOKLM_MCP_URL", "http://localhost:3000")


def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """
    Call a NotebookLM MCP tool.

    This uses the MCP protocol to invoke tools on the NotebookLM server.

    Args:
        tool_name: Name of the MCP tool
        arguments: Tool arguments

    Returns:
        Tool result dictionary
    """
    # For simplicity, we'll use subprocess to call the MCP CLI
    # In production, you'd use proper MCP client library

    try:
        # Construct MCP call
        mcp_request = {
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        # Try HTTP endpoint if MCP server exposes one
        import requests
        response = requests.post(
            f"{NOTEBOOKLM_MCP_URL}/mcp",
            json=mcp_request,
            timeout=120  # Research can take time
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"MCP call failed: {response.status_code}"}

    except Exception as e:
        return {"error": str(e)}


@app.route("/research", methods=["POST"])
def handle_research():
    """
    Start research on a topic.

    Expected JSON body:
    {
        "topic": "The research topic",
        "mode": "fast" or "deep",  // optional, default "fast"
        "notebook_id": "existing-notebook-id"  // optional
    }

    Returns:
    {
        "status": "started",
        "notebook_id": "...",
        "task_id": "...",
        "message": "Research started on topic..."
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        topic = data.get("topic")
        mode = data.get("mode", "fast")
        notebook_id = data.get("notebook_id")

        if not topic:
            return jsonify({"error": "topic is required"}), 400

        # Call research_start MCP tool
        result = call_mcp_tool("research_start", {
            "query": topic,
            "mode": mode,
            "source": "web",
            "notebook_id": notebook_id
        })

        if "error" in result:
            return jsonify(result), 500

        return jsonify({
            "status": "started",
            "message": f"Research started on: {topic}",
            "mode": mode,
            "result": result
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/query", methods=["POST"])
def handle_query():
    """
    Query an existing notebook.

    Expected JSON body:
    {
        "notebook_id": "notebook-uuid",
        "query": "What does the research say about X?"
    }

    Returns:
    {
        "answer": "Based on the sources...",
        "sources": [...]
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        notebook_id = data.get("notebook_id")
        query = data.get("query")

        if not notebook_id:
            return jsonify({"error": "notebook_id is required"}), 400

        if not query:
            return jsonify({"error": "query is required"}), 400

        # Call notebook_query MCP tool
        result = call_mcp_tool("notebook_query", {
            "notebook_id": notebook_id,
            "query": query
        })

        if "error" in result:
            return jsonify(result), 500

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/notebooks", methods=["GET"])
def list_notebooks():
    """
    List all notebooks.

    Returns:
    {
        "notebooks": [
            {"id": "...", "title": "...", "source_count": 5}
        ]
    }
    """
    try:
        result = call_mcp_tool("notebook_list", {"max_results": 50})

        if "error" in result:
            return jsonify(result), 500

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/status/<notebook_id>", methods=["GET"])
def research_status(notebook_id: str):
    """
    Check research status for a notebook.

    Returns current research progress if any.
    """
    try:
        result = call_mcp_tool("research_status", {
            "notebook_id": notebook_id,
            "max_wait": 0  # Single poll, don't block
        })

        if "error" in result:
            return jsonify(result), 500

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    # Try to list notebooks to verify connection
    mcp_ok = False
    try:
        result = call_mcp_tool("notebook_list", {"max_results": 1})
        mcp_ok = "error" not in result
    except:
        pass

    return jsonify({
        "status": "healthy" if mcp_ok else "degraded",
        "service": "notebooklm-bridge",
        "mcp_connected": mcp_ok,
        "mcp_url": NOTEBOOKLM_MCP_URL
    })


# Convenience endpoint for quick research summary
@app.route("/quick-research", methods=["POST"])
def quick_research():
    """
    Perform quick research and return summary.

    This is a convenience endpoint that:
    1. Starts fast research
    2. Waits for completion
    3. Returns the research summary

    Expected JSON body:
    {
        "topic": "Research topic"
    }

    Note: This can take 30-60 seconds to complete.
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        topic = data.get("topic")

        if not topic:
            return jsonify({"error": "topic is required"}), 400

        # Start research
        start_result = call_mcp_tool("research_start", {
            "query": topic,
            "mode": "fast",
            "source": "web"
        })

        if "error" in start_result:
            return jsonify(start_result), 500

        notebook_id = start_result.get("notebook_id")

        if not notebook_id:
            return jsonify({
                "error": "No notebook_id returned from research_start",
                "result": start_result
            }), 500

        # Poll for completion (with timeout)
        status_result = call_mcp_tool("research_status", {
            "notebook_id": notebook_id,
            "max_wait": 120,  # Wait up to 2 minutes
            "poll_interval": 10
        })

        if "error" in status_result:
            return jsonify({
                "status": "in_progress",
                "notebook_id": notebook_id,
                "message": "Research is still in progress. Check status later.",
                "error": status_result.get("error")
            })

        # Get notebook summary
        describe_result = call_mcp_tool("notebook_describe", {
            "notebook_id": notebook_id
        })

        return jsonify({
            "status": "completed",
            "notebook_id": notebook_id,
            "topic": topic,
            "summary": describe_result.get("summary", "Research completed."),
            "url": f"https://notebooklm.google.com/notebook/{notebook_id}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8766))
    print(f"Starting NotebookLM Bridge on port {port}")
    print(f"MCP URL: {NOTEBOOKLM_MCP_URL}")
    print(f"Endpoints:")
    print(f"  POST /research - Start research")
    print(f"  POST /query - Query notebook")
    print(f"  POST /quick-research - Research + wait + summarize")
    print(f"  GET  /notebooks - List notebooks")
    print(f"  GET  /status/<id> - Check research status")
    print(f"  GET  /health - Health check")

    app.run(host="0.0.0.0", port=port, debug=False)
