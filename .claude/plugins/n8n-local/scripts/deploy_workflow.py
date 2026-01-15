#!/usr/bin/env python3
"""
Deploy workflows to n8n via the REST API.

This module provides utilities for deploying, updating, and managing
n8n workflows through the API.

Usage:
    # Deploy a new workflow
    python deploy_workflow.py workflow.json

    # Deploy and activate
    python deploy_workflow.py workflow.json --activate

    # Update existing workflow
    python deploy_workflow.py workflow.json --update --id=123

Environment Variables:
    N8N_API_URL  - Base URL for n8n API (default: http://localhost:5678/api/v1)
    N8N_API_KEY  - API key for authentication

Exit codes:
    0 - Success
    1 - API error
    2 - Configuration or file error
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class N8nConfig:
    """Configuration for n8n API access."""
    api_url: str
    api_key: str

    @classmethod
    def from_env(cls) -> "N8nConfig":
        """Load configuration from environment variables."""
        api_url = os.environ.get("N8N_API_URL", "http://localhost:5678/api/v1")
        api_key = os.environ.get("N8N_API_KEY", "")

        if not api_key:
            raise ValueError(
                "N8N_API_KEY environment variable is required. "
                "Generate an API key in n8n Settings > API."
            )

        # Ensure URL doesn't have trailing slash
        api_url = api_url.rstrip("/")

        return cls(api_url=api_url, api_key=api_key)


class N8nApiError(Exception):
    """Error from n8n API."""

    def __init__(self, message: str, status_code: int | None = None, response: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class N8nClient:
    """Client for interacting with n8n REST API."""

    def __init__(self, config: N8nConfig):
        self.config = config
        self.headers = {
            "X-N8N-API-KEY": config.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        timeout: int = 30
    ) -> dict[str, Any]:
        """Make an API request."""
        url = f"{self.config.api_url}{endpoint}"

        body = None
        if data is not None:
            body = json.dumps(data).encode("utf-8")

        request = Request(url, data=body, headers=self.headers, method=method)

        try:
            with urlopen(request, timeout=timeout) as response:
                response_body = response.read().decode("utf-8")
                if response_body:
                    return json.loads(response_body)
                return {}
        except HTTPError as e:
            response_body = ""
            try:
                response_body = e.read().decode("utf-8")
            except Exception:
                pass
            raise N8nApiError(
                f"API request failed: {e.reason}",
                status_code=e.code,
                response=response_body
            )
        except URLError as e:
            raise N8nApiError(f"Connection failed: {e.reason}")
        except json.JSONDecodeError as e:
            raise N8nApiError(f"Invalid JSON response: {e}")

    def health_check(self) -> bool:
        """Check if n8n is accessible."""
        try:
            # Health endpoint doesn't require auth
            url = self.config.api_url.replace("/api/v1", "/healthz")
            request = Request(url, method="GET")
            with urlopen(request, timeout=5) as response:
                return response.status == 200
        except Exception:
            return False

    def list_workflows(self) -> list[dict[str, Any]]:
        """List all workflows."""
        result = self._request("GET", "/workflows")
        return result.get("data", [])

    def get_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Get a workflow by ID."""
        return self._request("GET", f"/workflows/{workflow_id}")

    def create_workflow(self, workflow: dict[str, Any]) -> dict[str, Any]:
        """Create a new workflow."""
        return self._request("POST", "/workflows", data=workflow)

    def update_workflow(
        self,
        workflow_id: str,
        workflow: dict[str, Any]
    ) -> dict[str, Any]:
        """Update an existing workflow."""
        return self._request("PUT", f"/workflows/{workflow_id}", data=workflow)

    def delete_workflow(self, workflow_id: str) -> None:
        """Delete a workflow."""
        self._request("DELETE", f"/workflows/{workflow_id}")

    def activate_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Activate a workflow."""
        return self._request("POST", f"/workflows/{workflow_id}/activate")

    def deactivate_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Deactivate a workflow."""
        return self._request("POST", f"/workflows/{workflow_id}/deactivate")

    def execute_workflow(
        self,
        workflow_id: str,
        data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a workflow."""
        return self._request(
            "POST",
            f"/workflows/{workflow_id}/execute",
            data=data or {}
        )

    def find_workflow_by_name(self, name: str) -> dict[str, Any] | None:
        """Find a workflow by name."""
        workflows = self.list_workflows()
        for workflow in workflows:
            if workflow.get("name") == name:
                return workflow
        return None


def load_workflow(filepath: str | Path) -> dict[str, Any]:
    """Load workflow from JSON file."""
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"Workflow file not found: {filepath}")

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def deploy_workflow(
    client: N8nClient,
    workflow: dict[str, Any],
    activate: bool = False,
    update_id: str | None = None
) -> dict[str, Any]:
    """Deploy a workflow to n8n."""

    if update_id:
        # Update existing workflow
        print(f"Updating workflow ID: {update_id}")
        result = client.update_workflow(update_id, workflow)
        workflow_id = update_id
    else:
        # Check if workflow with same name exists
        existing = client.find_workflow_by_name(workflow.get("name", ""))
        if existing:
            print(f"Warning: Workflow '{workflow['name']}' already exists (ID: {existing['id']})")
            print("Use --update --id=<ID> to update, or rename the workflow")

        # Create new workflow
        print(f"Creating workflow: {workflow.get('name', 'Unnamed')}")
        result = client.create_workflow(workflow)
        workflow_id = result.get("id")

    if activate and workflow_id:
        print(f"Activating workflow: {workflow_id}")
        # Small delay to ensure workflow is saved
        time.sleep(0.5)
        client.activate_workflow(workflow_id)
        result["active"] = True

    return result


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Deploy n8n workflows via API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  N8N_API_URL   Base URL for n8n API (default: http://localhost:5678/api/v1)
  N8N_API_KEY   API key for authentication (required)

Examples:
  # Deploy new workflow
  %(prog)s workflow.json

  # Deploy and activate
  %(prog)s workflow.json --activate

  # Update existing workflow
  %(prog)s workflow.json --update --id=abc123

  # List all workflows
  %(prog)s --list

  # Check n8n health
  %(prog)s --health
        """
    )

    parser.add_argument(
        "file",
        nargs="?",
        help="Workflow JSON file to deploy"
    )
    parser.add_argument(
        "--activate",
        action="store_true",
        help="Activate workflow after deployment"
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update existing workflow (requires --id)"
    )
    parser.add_argument(
        "--id",
        help="Workflow ID for update operations"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all workflows"
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Check n8n health"
    )
    parser.add_argument(
        "--delete",
        metavar="ID",
        help="Delete workflow by ID"
    )
    parser.add_argument(
        "--execute",
        metavar="ID",
        help="Execute workflow by ID"
    )

    args = parser.parse_args()

    # Health check doesn't require API key
    if args.health:
        url = os.environ.get("N8N_API_URL", "http://localhost:5678/api/v1")
        config = N8nConfig(api_url=url, api_key="")
        client = N8nClient(config)

        if client.health_check():
            print("✓ n8n is healthy")
            return 0
        else:
            print("✗ n8n is not responding")
            return 1

    # Other operations require API key
    try:
        config = N8nConfig.from_env()
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 2

    client = N8nClient(config)

    try:
        if args.list:
            workflows = client.list_workflows()
            if not workflows:
                print("No workflows found")
            else:
                print(f"Found {len(workflows)} workflow(s):\n")
                for wf in workflows:
                    status = "active" if wf.get("active") else "inactive"
                    print(f"  [{wf['id']}] {wf['name']} ({status})")
            return 0

        if args.delete:
            print(f"Deleting workflow: {args.delete}")
            client.delete_workflow(args.delete)
            print("✓ Workflow deleted")
            return 0

        if args.execute:
            print(f"Executing workflow: {args.execute}")
            result = client.execute_workflow(args.execute)
            print(json.dumps(result, indent=2))
            return 0

        if not args.file:
            parser.print_help()
            return 2

        if args.update and not args.id:
            print("Error: --update requires --id", file=sys.stderr)
            return 2

        # Load and deploy workflow
        workflow = load_workflow(args.file)
        result = deploy_workflow(
            client,
            workflow,
            activate=args.activate,
            update_id=args.id if args.update else None
        )

        print("\n✓ Deployment successful")
        print(f"  Workflow ID: {result.get('id')}")
        print(f"  Name: {result.get('name')}")
        print(f"  Active: {result.get('active', False)}")

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except N8nApiError as e:
        print(f"API Error: {e}", file=sys.stderr)
        if e.response:
            try:
                error_data = json.loads(e.response)
                if "message" in error_data:
                    print(f"  Details: {error_data['message']}", file=sys.stderr)
            except json.JSONDecodeError:
                print(f"  Response: {e.response[:200]}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in workflow file: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
