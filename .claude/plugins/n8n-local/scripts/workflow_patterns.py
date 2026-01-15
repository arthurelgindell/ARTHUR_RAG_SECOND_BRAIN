#!/usr/bin/env python3
"""
Extended workflow patterns for complex n8n automations.

Provides higher-level workflow builders for common patterns:
- API monitoring with notifications
- Data pipelines with error handling
- AI agent workflows with local LLM
- Batch processing

Usage:
    from workflow_patterns import (
        create_api_monitor_workflow,
        create_ai_pipeline_workflow,
        create_data_pipeline_workflow,
        create_notification_workflow
    )

    workflow = create_api_monitor_workflow(
        name="API Health Monitor",
        url="https://api.example.com/health",
        interval_minutes=5
    )
    workflow.save("api_monitor.json")
"""

from __future__ import annotations

import json
from typing import Any

from generate_workflow import WorkflowBuilder, NodeFactory, Node


def create_api_monitor_workflow(
    name: str,
    url: str,
    interval_minutes: int = 5,
    success_webhook: str | None = None,
    failure_webhook: str | None = None,
    timeout_ms: int = 10000
) -> WorkflowBuilder:
    """
    Create an API health monitoring workflow.

    Monitors an endpoint at regular intervals and optionally sends
    notifications on success or failure.

    Args:
        name: Workflow name
        url: URL to monitor
        interval_minutes: Check interval in minutes (default: 5)
        success_webhook: Optional webhook URL for success notifications
        failure_webhook: Optional webhook URL for failure notifications
        timeout_ms: Request timeout in milliseconds (default: 10000)

    Returns:
        WorkflowBuilder configured for API monitoring
    """
    builder = WorkflowBuilder(name)

    # Schedule trigger
    schedule = NodeFactory.schedule_trigger(
        name="Schedule",
        interval_minutes=interval_minutes,
        position=(250, 300)
    )
    builder.add_node(schedule)

    # HTTP Request to check endpoint
    http = NodeFactory.http_request(
        name="Check API",
        url=url,
        method="GET",
        position=(450, 300),
        timeout=timeout_ms
    )
    builder.add_node(http)

    # Check if response is healthy (status 200)
    check = NodeFactory.if_node(
        name="Is Healthy",
        position=(650, 300),
        left_value="{{ $response.statusCode }}",
        right_value=200,
        operation="equals"
    )
    builder.add_node(check)

    # Success handler
    success = NodeFactory.set_node(
        name="Log Success",
        position=(850, 200),
        assignments=[
            {"name": "status", "value": "healthy", "type": "string"},
            {"name": "timestamp", "value": "={{ $now.toISO() }}", "type": "string"},
            {"name": "url", "value": url, "type": "string"},
            {"name": "response_time_ms", "value": "={{ $response.responseTime }}", "type": "number"}
        ]
    )
    builder.add_node(success)

    # Failure handler
    failure = NodeFactory.set_node(
        name="Log Failure",
        position=(850, 400),
        assignments=[
            {"name": "status", "value": "unhealthy", "type": "string"},
            {"name": "timestamp", "value": "={{ $now.toISO() }}", "type": "string"},
            {"name": "url", "value": url, "type": "string"},
            {"name": "error", "value": "={{ $json.error || 'Non-200 response: ' + $response.statusCode }}", "type": "string"}
        ]
    )
    builder.add_node(failure)

    # Connections
    builder.connect("Schedule", "Check API")
    builder.connect("Check API", "Is Healthy")
    builder.connect("Is Healthy", "Log Success", source_output=0)
    builder.connect("Is Healthy", "Log Failure", source_output=1)

    # Optional success notification
    if success_webhook:
        notify_success = NodeFactory.http_request(
            name="Notify Success",
            url=success_webhook,
            method="POST",
            position=(1050, 200)
        )
        builder.add_node(notify_success)
        builder.connect("Log Success", "Notify Success")

    # Optional failure notification
    if failure_webhook:
        notify_failure = NodeFactory.http_request(
            name="Notify Failure",
            url=failure_webhook,
            method="POST",
            position=(1050, 400)
        )
        builder.add_node(notify_failure)
        builder.connect("Log Failure", "Notify Failure")

    return builder


def create_ai_pipeline_workflow(
    name: str,
    trigger_type: str = "webhook",
    model_name: str = "deepseek-r1-distill-qwen-7b",
    base_url: str = "http://host.docker.internal:1234/v1",
    system_prompt: str = "You are a helpful assistant.",
    webhook_path: str = "ai-process"
) -> WorkflowBuilder:
    """
    Create an AI processing pipeline workflow.

    Processes input through an AI agent using a local LLM.

    Args:
        name: Workflow name
        trigger_type: 'webhook', 'manual', or 'schedule'
        model_name: LLM model name (must match loaded model in LM Studio)
        base_url: LLM API base URL (default: LM Studio)
        system_prompt: System prompt for the AI agent
        webhook_path: Path for webhook trigger (if webhook type)

    Returns:
        WorkflowBuilder configured for AI processing
    """
    builder = WorkflowBuilder(name)

    # Create trigger based on type
    if trigger_type == "webhook":
        trigger = NodeFactory.webhook_trigger(
            name="Webhook",
            path=webhook_path,
            position=(250, 300)
        )
        # Add respond node for webhook
        respond = NodeFactory.respond_to_webhook(
            name="Respond",
            position=(1050, 300),
            response_body="={{ $json }}"
        )
        builder.add_node(respond)
    elif trigger_type == "schedule":
        trigger = NodeFactory.schedule_trigger(
            name="Schedule",
            interval_minutes=60,
            position=(250, 300)
        )
    else:  # manual
        trigger = NodeFactory.manual_trigger(
            name="Manual Trigger",
            position=(250, 300)
        )

    builder.add_node(trigger)

    # Input preparation
    set_input = NodeFactory.set_node(
        name="Prepare Input",
        position=(450, 300),
        assignments=[
            {
                "name": "input",
                "value": "={{ $json.query || $json.input || $json.message || $json.prompt || 'Hello' }}",
                "type": "string"
            }
        ]
    )
    builder.add_node(set_input)

    # AI Agent
    agent = NodeFactory.ai_agent(
        name="AI Agent",
        position=(650, 300),
        text="={{ $json.input }}"
    )
    # Add system message if provided
    if system_prompt:
        agent.parameters["systemMessage"] = system_prompt
    builder.add_node(agent)

    # Language model (local LLM via LM Studio)
    model = NodeFactory.openai_chat_model(
        name="LLM Model",
        position=(650, 520),
        model=model_name,
        base_url=base_url,
        credential_id="local-llm",
        credential_name="Local LLM"
    )
    builder.add_node(model)

    # Connections
    builder.connect(trigger.name, "Prepare Input")
    builder.connect("Prepare Input", "AI Agent")
    builder.connect_ai_model("LLM Model", "AI Agent")

    if trigger_type == "webhook":
        builder.connect("AI Agent", "Respond")

    return builder


def create_data_pipeline_workflow(
    name: str,
    source_url: str,
    transform_code: str = "// Transform data\nreturn items;",
    destination_url: str | None = None,
    include_error_handling: bool = True,
    batch_size: int = 10
) -> WorkflowBuilder:
    """
    Create a data pipeline workflow with optional error handling.

    Fetches data from a source, transforms it, and optionally sends to destination.

    Args:
        name: Workflow name
        source_url: URL to fetch data from
        transform_code: JavaScript code for data transformation
        destination_url: Optional URL to send processed data
        include_error_handling: Whether to include error handling (default: True)
        batch_size: Batch size for processing (default: 10)

    Returns:
        WorkflowBuilder configured for data pipeline
    """
    builder = WorkflowBuilder(name)

    # Manual trigger
    trigger = NodeFactory.manual_trigger(
        name="Manual Trigger",
        position=(250, 300)
    )
    builder.add_node(trigger)

    # Fetch data
    fetch = NodeFactory.http_request(
        name="Fetch Data",
        url=source_url,
        method="GET",
        position=(450, 300)
    )
    builder.add_node(fetch)

    # Transform data
    transform = NodeFactory.code_node(
        name="Transform Data",
        position=(650, 300),
        code=transform_code
    )
    builder.add_node(transform)

    builder.connect("Manual Trigger", "Fetch Data")
    builder.connect("Fetch Data", "Transform Data")

    current_node = "Transform Data"
    x_pos = 850

    if include_error_handling:
        # Batch processing node
        batch = Node(
            name="Process Batches",
            node_type="n8n-nodes-base.splitInBatches",
            position=(x_pos, 300),
            type_version=3,
            parameters={"batchSize": batch_size}
        )
        builder.add_node(batch)
        builder.connect(current_node, "Process Batches")

        x_pos += 200

        # Process each item with error tolerance
        process = NodeFactory.code_node(
            name="Process Item",
            position=(x_pos, 300),
            code="// Process each item\nreturn items;"
        )
        process.parameters["continueOnFail"] = True
        builder.add_node(process)

        x_pos += 200

        # Error check
        check = NodeFactory.if_node(
            name="Has Error",
            position=(x_pos, 300),
            left_value="{{ $json.error }}",
            right_value="",
            operation="notEmpty"
        )
        builder.add_node(check)

        # Log nodes
        log_error = NodeFactory.set_node(
            name="Log Error",
            position=(x_pos + 200, 200),
            assignments=[
                {"name": "error_logged", "value": "true", "type": "boolean"},
                {"name": "timestamp", "value": "={{ $now.toISO() }}", "type": "string"}
            ]
        )
        builder.add_node(log_error)

        log_success = NodeFactory.set_node(
            name="Log Success",
            position=(x_pos + 200, 400),
            assignments=[
                {"name": "success", "value": "true", "type": "boolean"},
                {"name": "timestamp", "value": "={{ $now.toISO() }}", "type": "string"}
            ]
        )
        builder.add_node(log_success)

        # Connect batch processing flow
        builder.connect("Process Batches", "Process Item", source_output=0)
        builder.connect("Process Item", "Has Error")
        builder.connect("Has Error", "Log Error", source_output=0)
        builder.connect("Has Error", "Log Success", source_output=1)
        builder.connect("Log Error", "Process Batches")
        builder.connect("Log Success", "Process Batches")

        current_node = "Process Batches"

    # Optional destination
    if destination_url:
        x_pos += 400
        send = NodeFactory.http_request(
            name="Send Results",
            url=destination_url,
            method="POST",
            position=(x_pos, 300)
        )
        builder.add_node(send)

        if include_error_handling:
            # Connect from batch done output (index 1)
            builder.connect("Process Batches", "Send Results", source_output=1)
        else:
            builder.connect(current_node, "Send Results")

    return builder


def create_notification_workflow(
    name: str,
    trigger_type: str = "webhook",
    webhook_path: str = "notify",
    slack_webhook: str | None = None,
    discord_webhook: str | None = None,
    message_template: str = "={{ $json.message }}"
) -> WorkflowBuilder:
    """
    Create a notification workflow that sends to multiple channels.

    Args:
        name: Workflow name
        trigger_type: 'webhook' or 'error' (for error handler)
        webhook_path: Path for webhook trigger
        slack_webhook: Optional Slack incoming webhook URL
        discord_webhook: Optional Discord webhook URL
        message_template: Template for the notification message

    Returns:
        WorkflowBuilder configured for notifications
    """
    builder = WorkflowBuilder(name)

    # Create trigger
    if trigger_type == "error":
        trigger = NodeFactory.error_trigger(
            name="Error Trigger",
            position=(250, 300)
        )
    else:
        trigger = NodeFactory.webhook_trigger(
            name="Webhook",
            path=webhook_path,
            position=(250, 300)
        )
    builder.add_node(trigger)

    # Format message
    format_msg = NodeFactory.set_node(
        name="Format Message",
        position=(450, 300),
        assignments=[
            {"name": "message", "value": message_template, "type": "string"},
            {"name": "timestamp", "value": "={{ $now.toISO() }}", "type": "string"},
            {"name": "source", "value": "={{ $json.source || 'n8n' }}", "type": "string"}
        ]
    )
    builder.add_node(format_msg)
    builder.connect(trigger.name, "Format Message")

    x_pos = 650
    y_offset = 0

    if slack_webhook:
        slack = NodeFactory.http_request(
            name="Send to Slack",
            url=slack_webhook,
            method="POST",
            position=(x_pos, 300 + y_offset)
        )
        # Slack expects specific JSON format
        slack.parameters["sendBody"] = True
        slack.parameters["specifyBody"] = "json"
        slack.parameters["jsonBody"] = '{"text": "{{ $json.message }}"}'
        builder.add_node(slack)
        builder.connect("Format Message", "Send to Slack")
        y_offset += 200

    if discord_webhook:
        discord = NodeFactory.http_request(
            name="Send to Discord",
            url=discord_webhook,
            method="POST",
            position=(x_pos, 300 + y_offset)
        )
        # Discord webhook format
        discord.parameters["sendBody"] = True
        discord.parameters["specifyBody"] = "json"
        discord.parameters["jsonBody"] = '{"content": "{{ $json.message }}"}'
        builder.add_node(discord)
        builder.connect("Format Message", "Send to Discord")

    return builder


def create_webhook_echo_workflow(
    name: str = "Webhook Echo",
    webhook_path: str = "echo"
) -> WorkflowBuilder:
    """
    Create a simple webhook that echoes back the received data.

    Args:
        name: Workflow name
        webhook_path: Webhook endpoint path

    Returns:
        WorkflowBuilder configured for echo
    """
    builder = WorkflowBuilder(name)

    webhook = NodeFactory.webhook_trigger(
        name="Webhook",
        path=webhook_path,
        position=(250, 300)
    )
    builder.add_node(webhook)

    respond = NodeFactory.respond_to_webhook(
        name="Respond",
        position=(450, 300),
        response_body="={{ $json }}"
    )
    builder.add_node(respond)

    builder.connect("Webhook", "Respond")

    return builder


if __name__ == "__main__":
    import sys

    # Demo: Create and print various workflow patterns
    print("=" * 60)
    print("N8N Workflow Patterns Demo")
    print("=" * 60)

    # 1. API Monitor
    print("\n1. API Monitor Workflow:")
    api_monitor = create_api_monitor_workflow(
        name="API Health Monitor",
        url="https://api.example.com/health",
        interval_minutes=5,
        failure_webhook="https://hooks.slack.com/services/xxx"
    )
    print(f"   Nodes: {len(api_monitor.nodes)}")
    print(f"   Connections: {len(api_monitor.connections)}")

    # 2. AI Pipeline
    print("\n2. AI Pipeline Workflow:")
    ai_pipeline = create_ai_pipeline_workflow(
        name="AI Chat Handler",
        trigger_type="webhook",
        model_name="deepseek-r1-distill-qwen-7b",
        webhook_path="chat"
    )
    print(f"   Nodes: {len(ai_pipeline.nodes)}")
    print(f"   Connections: {len(ai_pipeline.connections)}")

    # 3. Data Pipeline
    print("\n3. Data Pipeline Workflow:")
    data_pipeline = create_data_pipeline_workflow(
        name="ETL Pipeline",
        source_url="https://api.example.com/data",
        include_error_handling=True
    )
    print(f"   Nodes: {len(data_pipeline.nodes)}")
    print(f"   Connections: {len(data_pipeline.connections)}")

    # Save demo workflow
    if len(sys.argv) > 1 and sys.argv[1] == "--save":
        api_monitor.save("/tmp/demo_api_monitor.json")
        print("\nSaved demo workflow to /tmp/demo_api_monitor.json")
