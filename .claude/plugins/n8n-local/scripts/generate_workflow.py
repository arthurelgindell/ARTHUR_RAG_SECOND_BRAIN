#!/usr/bin/env python3
"""
Generate n8n workflow JSON from high-level specifications.

This module provides utilities for programmatically creating valid n8n
workflow JSON files with correct node structures and connections.

Usage:
    python generate_workflow.py > workflow.json

    Or import as a module:
        from generate_workflow import WorkflowBuilder, NodeFactory
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any


def generate_node_id() -> str:
    """Generate a unique node ID."""
    return str(uuid.uuid4())


@dataclass
class Node:
    """Represents an n8n workflow node."""

    name: str
    node_type: str
    position: tuple[int, int]
    parameters: dict[str, Any] = field(default_factory=dict)
    type_version: float = 1.0
    credentials: dict[str, Any] | None = None
    id: str = field(default_factory=generate_node_id)

    def to_dict(self) -> dict[str, Any]:
        """Convert node to n8n JSON format."""
        node_dict = {
            "id": self.id,
            "name": self.name,
            "type": self.node_type,
            "typeVersion": self.type_version,
            "position": list(self.position),
            "parameters": self.parameters
        }
        if self.credentials:
            node_dict["credentials"] = self.credentials
        return node_dict


class NodeFactory:
    """Factory for creating common n8n nodes."""

    @staticmethod
    def webhook_trigger(
        name: str = "Webhook",
        position: tuple[int, int] = (250, 300),
        path: str = "webhook",
        http_method: str = "POST",
        response_mode: str = "responseNode"
    ) -> Node:
        """Create a webhook trigger node."""
        return Node(
            name=name,
            node_type="n8n-nodes-base.webhook",
            position=position,
            type_version=1.1,
            parameters={
                "httpMethod": http_method,
                "path": path,
                "responseMode": response_mode
            }
        )

    @staticmethod
    def respond_to_webhook(
        name: str = "Respond",
        position: tuple[int, int] = (450, 300),
        response_body: str = "={{ $json }}"
    ) -> Node:
        """Create a respond to webhook node."""
        return Node(
            name=name,
            node_type="n8n-nodes-base.respondToWebhook",
            position=position,
            type_version=1.1,
            parameters={
                "respondWith": "json",
                "responseBody": response_body
            }
        )

    @staticmethod
    def manual_trigger(
        name: str = "Manual Trigger",
        position: tuple[int, int] = (250, 300)
    ) -> Node:
        """Create a manual trigger node."""
        return Node(
            name=name,
            node_type="n8n-nodes-base.manualTrigger",
            position=position,
            type_version=1,
            parameters={}
        )

    @staticmethod
    def schedule_trigger(
        name: str = "Schedule",
        position: tuple[int, int] = (250, 300),
        interval_minutes: int = 5
    ) -> Node:
        """Create a schedule trigger node."""
        return Node(
            name=name,
            node_type="n8n-nodes-base.scheduleTrigger",
            position=position,
            type_version=1.2,
            parameters={
                "rule": {
                    "interval": [{"field": "minutes", "minutesInterval": interval_minutes}]
                }
            }
        )

    @staticmethod
    def http_request(
        name: str = "HTTP Request",
        position: tuple[int, int] = (450, 300),
        url: str = "",
        method: str = "GET",
        timeout: int = 10000
    ) -> Node:
        """Create an HTTP request node."""
        return Node(
            name=name,
            node_type="n8n-nodes-base.httpRequest",
            position=position,
            type_version=4.1,
            parameters={
                "url": url,
                "method": method,
                "options": {
                    "timeout": timeout
                }
            }
        )

    @staticmethod
    def code_node(
        name: str = "Code",
        position: tuple[int, int] = (450, 300),
        code: str = "return items;",
        language: str = "javaScript"
    ) -> Node:
        """Create a code node."""
        return Node(
            name=name,
            node_type="n8n-nodes-base.code",
            position=position,
            type_version=2,
            parameters={
                "jsCode": code if language == "javaScript" else "",
                "pythonCode": code if language == "python" else "",
                "mode": "runOnceForAllItems"
            }
        )

    @staticmethod
    def if_node(
        name: str = "If",
        position: tuple[int, int] = (450, 300),
        left_value: str = "",
        right_value: Any = "",
        operation: str = "equals"
    ) -> Node:
        """Create an if/conditional node."""
        return Node(
            name=name,
            node_type="n8n-nodes-base.if",
            position=position,
            type_version=2,
            parameters={
                "conditions": {
                    "options": {
                        "caseSensitive": True,
                        "leftValue": "",
                        "typeValidation": "strict"
                    },
                    "conditions": [{
                        "leftValue": left_value,
                        "rightValue": right_value,
                        "operator": {
                            "type": "string",
                            "operation": operation
                        }
                    }]
                }
            }
        )

    @staticmethod
    def set_node(
        name: str = "Set",
        position: tuple[int, int] = (450, 300),
        assignments: list[dict[str, Any]] | None = None
    ) -> Node:
        """Create a set/edit fields node."""
        return Node(
            name=name,
            node_type="n8n-nodes-base.set",
            position=position,
            type_version=3.4,
            parameters={
                "mode": "manual",
                "assignments": {
                    "assignments": assignments or []
                }
            }
        )

    @staticmethod
    def ai_agent(
        name: str = "AI Agent",
        position: tuple[int, int] = (450, 300),
        prompt_type: str = "define",
        text: str = "={{ $json.input }}"
    ) -> Node:
        """Create an AI agent node."""
        return Node(
            name=name,
            node_type="@n8n/n8n-nodes-langchain.agent",
            position=position,
            type_version=1.7,
            parameters={
                "promptType": prompt_type,
                "text": text
            }
        )

    @staticmethod
    def openai_chat_model(
        name: str = "OpenAI Chat Model",
        position: tuple[int, int] = (450, 500),
        model: str = "gpt-4",
        base_url: str | None = None,
        credential_id: str = "",
        credential_name: str = "OpenAI"
    ) -> Node:
        """Create an OpenAI chat model node (also used for local LLMs)."""
        parameters: dict[str, Any] = {"model": model}
        if base_url:
            parameters["options"] = {"baseURL": base_url}

        return Node(
            name=name,
            node_type="@n8n/n8n-nodes-langchain.lmChatOpenAi",
            position=position,
            type_version=1.2,
            parameters=parameters,
            credentials={
                "openAiApi": {
                    "id": credential_id,
                    "name": credential_name
                }
            } if credential_id else None
        )

    @staticmethod
    def error_trigger(
        name: str = "Error Trigger",
        position: tuple[int, int] = (250, 300)
    ) -> Node:
        """Create an error trigger node."""
        return Node(
            name=name,
            node_type="n8n-nodes-base.errorTrigger",
            position=position,
            type_version=1,
            parameters={}
        )


@dataclass
class Connection:
    """Represents a connection between two nodes."""

    source: str
    target: str
    source_output: int = 0
    target_input: int = 0
    connection_type: str = "main"


class WorkflowBuilder:
    """Builder for constructing n8n workflows."""

    def __init__(self, name: str):
        self.name = name
        self.nodes: list[Node] = []
        self.connections: list[Connection] = []
        self.active = False
        self.settings = {"executionOrder": "v1"}

    def add_node(self, node: Node) -> "WorkflowBuilder":
        """Add a node to the workflow."""
        self.nodes.append(node)
        return self

    def connect(
        self,
        source: str,
        target: str,
        source_output: int = 0,
        target_input: int = 0,
        connection_type: str = "main"
    ) -> "WorkflowBuilder":
        """Connect two nodes."""
        self.connections.append(Connection(
            source=source,
            target=target,
            source_output=source_output,
            target_input=target_input,
            connection_type=connection_type
        ))
        return self

    def connect_ai_model(
        self,
        model_node: str,
        agent_node: str
    ) -> "WorkflowBuilder":
        """Connect an AI model node to an agent node."""
        self.connections.append(Connection(
            source=model_node,
            target=agent_node,
            connection_type="ai_languageModel"
        ))
        return self

    def connect_ai_memory(
        self,
        memory_node: str,
        agent_node: str
    ) -> "WorkflowBuilder":
        """Connect a memory node to an agent node."""
        self.connections.append(Connection(
            source=memory_node,
            target=agent_node,
            connection_type="ai_memory"
        ))
        return self

    def connect_ai_tool(
        self,
        tool_node: str,
        agent_node: str
    ) -> "WorkflowBuilder":
        """Connect a tool node to an agent node."""
        self.connections.append(Connection(
            source=tool_node,
            target=agent_node,
            connection_type="ai_tool"
        ))
        return self

    def set_active(self, active: bool = True) -> "WorkflowBuilder":
        """Set the workflow active state."""
        self.active = active
        return self

    def _build_connections(self) -> dict[str, Any]:
        """Build the connections dict in n8n format."""
        connections_dict: dict[str, Any] = {}

        for conn in self.connections:
            if conn.source not in connections_dict:
                connections_dict[conn.source] = {}

            conn_type = conn.connection_type
            if conn_type not in connections_dict[conn.source]:
                connections_dict[conn.source][conn_type] = []

            # Ensure we have enough output slots
            while len(connections_dict[conn.source][conn_type]) <= conn.source_output:
                connections_dict[conn.source][conn_type].append([])

            connections_dict[conn.source][conn_type][conn.source_output].append({
                "node": conn.target,
                "type": conn_type,
                "index": conn.target_input
            })

        return connections_dict

    def build(self) -> dict[str, Any]:
        """Build the complete workflow JSON."""
        return {
            "name": self.name,
            "nodes": [node.to_dict() for node in self.nodes],
            "connections": self._build_connections(),
            "active": self.active,
            "settings": self.settings
        }

    def to_json(self, indent: int = 2) -> str:
        """Export workflow as JSON string."""
        return json.dumps(self.build(), indent=indent)

    def save(self, filepath: str) -> None:
        """Save workflow to file."""
        with open(filepath, 'w') as f:
            f.write(self.to_json())


def create_webhook_echo_workflow() -> WorkflowBuilder:
    """Create a simple webhook echo workflow."""
    builder = WorkflowBuilder("Webhook Echo")

    webhook = NodeFactory.webhook_trigger(path="echo")
    respond = NodeFactory.respond_to_webhook()

    builder.add_node(webhook)
    builder.add_node(respond)
    builder.connect("Webhook", "Respond")

    return builder


def create_local_ai_agent_workflow(
    model_name: str = "deepseek-r1-distil-qwen-7b",
    base_url: str = "http://host.docker.internal:1234/v1"
) -> WorkflowBuilder:
    """Create an AI agent workflow using a local LLM."""
    builder = WorkflowBuilder("Local AI Agent")

    trigger = NodeFactory.manual_trigger()
    agent = NodeFactory.ai_agent()
    model = NodeFactory.openai_chat_model(
        model=model_name,
        base_url=base_url,
        credential_id="local-llm",
        credential_name="Local LLM"
    )

    builder.add_node(trigger)
    builder.add_node(agent)
    builder.add_node(model)

    builder.connect("Manual Trigger", "AI Agent")
    builder.connect_ai_model("OpenAI Chat Model", "AI Agent")

    return builder


def create_health_check_workflow(
    url: str,
    interval_minutes: int = 5
) -> WorkflowBuilder:
    """Create a scheduled health check workflow."""
    builder = WorkflowBuilder("Health Monitor")

    schedule = NodeFactory.schedule_trigger(interval_minutes=interval_minutes)
    http = NodeFactory.http_request(
        name="Check Endpoint",
        url=url,
        position=(450, 300)
    )
    check = NodeFactory.if_node(
        name="Check Status",
        position=(650, 300),
        left_value="{{ $json.statusCode }}",
        right_value=200,
        operation="equals"
    )

    builder.add_node(schedule)
    builder.add_node(http)
    builder.add_node(check)

    builder.connect("Schedule", "Check Endpoint")
    builder.connect("Check Endpoint", "Check Status")

    return builder


if __name__ == "__main__":
    # Example: Create and print a webhook echo workflow
    workflow = create_webhook_echo_workflow()
    print(workflow.to_json())
