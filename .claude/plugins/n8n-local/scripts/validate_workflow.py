#!/usr/bin/env python3
"""
Validate n8n workflow JSON structure.

This module provides comprehensive validation for n8n workflow files,
checking structure, connections, and common issues.

Usage:
    python validate_workflow.py workflow.json

Exit codes:
    0 - Workflow is valid
    1 - Validation errors found
    2 - File not found or invalid JSON
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Severity(Enum):
    """Validation issue severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    severity: Severity
    message: str
    location: str = ""

    def __str__(self) -> str:
        prefix = f"[{self.severity.value.upper()}]"
        if self.location:
            return f"{prefix} {self.location}: {self.message}"
        return f"{prefix} {self.message}"


@dataclass
class ValidationResult:
    """Result of workflow validation."""
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if there are no errors."""
        return not any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)

    def add_error(self, message: str, location: str = "") -> None:
        """Add an error issue."""
        self.issues.append(ValidationIssue(Severity.ERROR, message, location))

    def add_warning(self, message: str, location: str = "") -> None:
        """Add a warning issue."""
        self.issues.append(ValidationIssue(Severity.WARNING, message, location))

    def add_info(self, message: str, location: str = "") -> None:
        """Add an info issue."""
        self.issues.append(ValidationIssue(Severity.INFO, message, location))


# Required fields at each level
REQUIRED_WORKFLOW_FIELDS = {"name", "nodes", "connections"}
REQUIRED_NODE_FIELDS = {"id", "name", "type", "typeVersion", "position", "parameters"}

# Known node type prefixes
VALID_NODE_PREFIXES = (
    "n8n-nodes-base.",
    "@n8n/n8n-nodes-langchain.",
    "n8n-nodes-",
)

# Trigger node types (workflows usually need at least one)
TRIGGER_TYPES = {
    "n8n-nodes-base.webhook",
    "n8n-nodes-base.manualTrigger",
    "n8n-nodes-base.scheduleTrigger",
    "n8n-nodes-base.errorTrigger",
    "n8n-nodes-base.emailTrigger",
    "n8n-nodes-base.cron",
    "n8n-nodes-base.start",
}


class WorkflowValidator:
    """Validates n8n workflow JSON structure."""

    def __init__(self, workflow: dict[str, Any]):
        self.workflow = workflow
        self.result = ValidationResult()
        self.node_names: set[str] = set()
        self.node_ids: set[str] = set()

    def validate(self) -> ValidationResult:
        """Run all validations and return result."""
        self._validate_top_level()
        self._validate_nodes()
        self._validate_connections()
        self._validate_workflow_structure()
        return self.result

    def _validate_top_level(self) -> None:
        """Validate top-level workflow structure."""
        for field_name in REQUIRED_WORKFLOW_FIELDS:
            if field_name not in self.workflow:
                self.result.add_error(f"Missing required field: {field_name}")

        if "name" in self.workflow and not self.workflow["name"]:
            self.result.add_warning("Workflow name is empty")

        if "nodes" in self.workflow and not isinstance(self.workflow["nodes"], list):
            self.result.add_error("'nodes' must be an array")

        if "connections" in self.workflow and not isinstance(self.workflow["connections"], dict):
            self.result.add_error("'connections' must be an object")

        if "settings" in self.workflow:
            settings = self.workflow["settings"]
            if not isinstance(settings, dict):
                self.result.add_error("'settings' must be an object")
            elif "executionOrder" not in settings:
                self.result.add_info("Consider adding 'executionOrder': 'v1' to settings")

    def _validate_nodes(self) -> None:
        """Validate all nodes in the workflow."""
        nodes = self.workflow.get("nodes", [])

        if not nodes:
            self.result.add_warning("Workflow has no nodes")
            return

        for i, node in enumerate(nodes):
            self._validate_node(node, i)

    def _validate_node(self, node: dict[str, Any], index: int) -> None:
        """Validate a single node."""
        location = f"nodes[{index}]"

        if not isinstance(node, dict):
            self.result.add_error("Node must be an object", location)
            return

        # Check required fields
        for field_name in REQUIRED_NODE_FIELDS:
            if field_name not in node:
                self.result.add_error(f"Missing required field: {field_name}", location)

        # Validate node name
        if "name" in node:
            name = node["name"]
            if not name:
                self.result.add_error("Node name cannot be empty", location)
            elif name in self.node_names:
                self.result.add_error(f"Duplicate node name: '{name}'", location)
            else:
                self.node_names.add(name)

        # Validate node ID
        if "id" in node:
            node_id = node["id"]
            if node_id in self.node_ids:
                self.result.add_warning(f"Duplicate node ID: '{node_id}'", location)
            else:
                self.node_ids.add(node_id)

        # Validate node type
        if "type" in node:
            node_type = node["type"]
            if not any(node_type.startswith(prefix) for prefix in VALID_NODE_PREFIXES):
                self.result.add_warning(
                    f"Unknown node type prefix: '{node_type}'",
                    location
                )

        # Validate position
        if "position" in node:
            position = node["position"]
            if not isinstance(position, list) or len(position) != 2:
                self.result.add_error("Position must be [x, y] array", location)
            elif not all(isinstance(p, (int, float)) for p in position):
                self.result.add_error("Position values must be numbers", location)

        # Validate typeVersion
        if "typeVersion" in node:
            version = node["typeVersion"]
            if not isinstance(version, (int, float)):
                self.result.add_error("typeVersion must be a number", location)

        # Validate parameters
        if "parameters" in node and not isinstance(node["parameters"], dict):
            self.result.add_error("Parameters must be an object", location)

        # Validate credentials
        if "credentials" in node:
            creds = node["credentials"]
            if not isinstance(creds, dict):
                self.result.add_error("Credentials must be an object", location)
            else:
                for cred_type, cred_data in creds.items():
                    if not isinstance(cred_data, dict):
                        self.result.add_error(
                            f"Credential '{cred_type}' must be an object",
                            location
                        )
                    elif "id" not in cred_data and "name" not in cred_data:
                        self.result.add_warning(
                            f"Credential '{cred_type}' should have 'id' or 'name'",
                            location
                        )

    def _validate_connections(self) -> None:
        """Validate all connections in the workflow."""
        connections = self.workflow.get("connections", {})

        for source_name, outputs in connections.items():
            self._validate_connection_source(source_name, outputs)

    def _validate_connection_source(
        self,
        source_name: str,
        outputs: dict[str, Any]
    ) -> None:
        """Validate connections from a source node."""
        if source_name not in self.node_names:
            self.result.add_error(
                f"Connection source '{source_name}' not found in nodes",
                f"connections['{source_name}']"
            )

        if not isinstance(outputs, dict):
            self.result.add_error(
                "Connection outputs must be an object",
                f"connections['{source_name}']"
            )
            return

        for output_type, output_slots in outputs.items():
            if not isinstance(output_slots, list):
                self.result.add_error(
                    f"Output '{output_type}' must be an array",
                    f"connections['{source_name}']['{output_type}']"
                )
                continue

            for slot_index, slot in enumerate(output_slots):
                if not isinstance(slot, list):
                    self.result.add_error(
                        f"Output slot must be an array",
                        f"connections['{source_name}']['{output_type}'][{slot_index}]"
                    )
                    continue

                for conn_index, connection in enumerate(slot):
                    self._validate_connection_target(
                        connection,
                        f"connections['{source_name}']['{output_type}'][{slot_index}][{conn_index}]"
                    )

    def _validate_connection_target(
        self,
        connection: dict[str, Any],
        location: str
    ) -> None:
        """Validate a connection target."""
        if not isinstance(connection, dict):
            self.result.add_error("Connection must be an object", location)
            return

        if "node" not in connection:
            self.result.add_error("Connection missing 'node' field", location)
        elif connection["node"] not in self.node_names:
            self.result.add_error(
                f"Connection target '{connection['node']}' not found in nodes",
                location
            )

        if "type" not in connection:
            self.result.add_warning("Connection missing 'type' field", location)

        if "index" not in connection:
            self.result.add_warning("Connection missing 'index' field", location)
        elif not isinstance(connection["index"], int):
            self.result.add_error("Connection 'index' must be an integer", location)

    def _validate_workflow_structure(self) -> None:
        """Validate overall workflow structure and logic."""
        nodes = self.workflow.get("nodes", [])

        # Check for trigger nodes
        has_trigger = any(
            node.get("type") in TRIGGER_TYPES
            for node in nodes
        )

        if not has_trigger and nodes:
            self.result.add_warning(
                "Workflow has no trigger node. Consider adding a Manual Trigger "
                "or other trigger type for execution."
            )

        # Check for disconnected nodes
        connections = self.workflow.get("connections", {})
        connected_targets = set()

        for outputs in connections.values():
            for output_type in outputs.values():
                for slot in output_type:
                    for conn in slot:
                        if isinstance(conn, dict) and "node" in conn:
                            connected_targets.add(conn["node"])

        source_nodes = set(connections.keys())
        all_connected = source_nodes | connected_targets

        for node in nodes:
            name = node.get("name")
            if name and name not in all_connected:
                node_type = node.get("type", "")
                # Trigger nodes don't need incoming connections
                if node_type not in TRIGGER_TYPES:
                    self.result.add_info(
                        f"Node '{name}' appears disconnected from workflow"
                    )


def validate_workflow(workflow: dict[str, Any]) -> ValidationResult:
    """Validate a workflow dictionary."""
    validator = WorkflowValidator(workflow)
    return validator.validate()


def validate_file(filepath: str | Path) -> ValidationResult:
    """Validate a workflow JSON file."""
    path = Path(filepath)

    if not path.exists():
        result = ValidationResult()
        result.add_error(f"File not found: {filepath}")
        return result

    try:
        with open(path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
    except json.JSONDecodeError as e:
        result = ValidationResult()
        result.add_error(f"Invalid JSON: {e}")
        return result

    return validate_workflow(workflow)


def main() -> int:
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python validate_workflow.py <workflow.json>")
        print("\nValidates n8n workflow JSON structure.")
        return 2

    filepath = sys.argv[1]
    result = validate_file(filepath)

    if not result.issues:
        print(f"✓ Workflow '{filepath}' is valid")
        return 0

    print(f"Validation results for '{filepath}':")
    print()

    for issue in result.issues:
        print(f"  {issue}")

    print()
    print(f"Summary: {result.error_count} error(s), {result.warning_count} warning(s)")

    return 0 if result.is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
