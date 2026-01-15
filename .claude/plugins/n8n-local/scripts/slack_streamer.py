#!/usr/bin/env python3
"""
Slack Text Streaming Bridge for ARTHUR Agent

This service receives responses from n8n and streams them to Slack
token-by-token for a real-time typing effect.

Uses Slack's chat.startStream, chat.appendStream, chat.stopStream APIs.

Usage:
    python slack_streamer.py

Environment Variables:
    SLACK_BOT_TOKEN - Bot token (xoxb-...)
    SLACK_APP_TOKEN - App token for Socket Mode (xapp-...)
    SLACK_SIGNING_SECRET - Signing secret for request verification

HTTP Endpoint:
    POST /stream
    Body: {
        "channel": "C123...",
        "thread_ts": "1234567890.123456",
        "text": "The full response text to stream"
    }
"""

import os
import asyncio
import time
from typing import Optional
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

app = Flask(__name__)

# Configuration
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
CHUNK_SIZE = 20  # Characters per chunk
CHUNK_DELAY = 0.05  # Seconds between chunks


def get_slack_client() -> WebClient:
    """Get Slack WebClient instance."""
    if not SLACK_BOT_TOKEN:
        raise ValueError("SLACK_BOT_TOKEN environment variable not set")
    return WebClient(token=SLACK_BOT_TOKEN)


def stream_message(
    channel: str,
    text: str,
    thread_ts: Optional[str] = None
) -> dict:
    """
    Stream a message to Slack using the streaming API.

    Args:
        channel: Slack channel ID
        text: Full text to stream
        thread_ts: Thread timestamp for reply threading

    Returns:
        dict with success status and message timestamp
    """
    client = get_slack_client()

    try:
        # Start the stream
        start_response = client.api_call(
            "chat.startStream",
            json={
                "channel": channel,
                "thread_ts": thread_ts
            }
        )

        if not start_response.get("ok"):
            # Fallback to regular message if streaming not supported
            return post_regular_message(client, channel, text, thread_ts)

        stream_id = start_response.get("stream_id")

        # Stream the text in chunks
        for i in range(0, len(text), CHUNK_SIZE):
            chunk = text[i:i + CHUNK_SIZE]

            client.api_call(
                "chat.appendStream",
                json={
                    "stream_id": stream_id,
                    "text": chunk
                }
            )

            time.sleep(CHUNK_DELAY)

        # Stop the stream
        stop_response = client.api_call(
            "chat.stopStream",
            json={
                "stream_id": stream_id
            }
        )

        return {
            "ok": True,
            "ts": stop_response.get("ts"),
            "streamed": True
        }

    except SlackApiError as e:
        # If streaming API not available, fall back to regular message
        if "method_not_supported" in str(e) or "not_allowed" in str(e):
            return post_regular_message(client, channel, text, thread_ts)
        raise


def post_regular_message(
    client: WebClient,
    channel: str,
    text: str,
    thread_ts: Optional[str] = None
) -> dict:
    """
    Fallback: Post a regular message without streaming.

    Args:
        client: Slack WebClient instance
        channel: Slack channel ID
        text: Message text
        thread_ts: Thread timestamp for reply threading

    Returns:
        dict with success status and message timestamp
    """
    response = client.chat_postMessage(
        channel=channel,
        text=text,
        thread_ts=thread_ts,
        mrkdwn=True
    )

    return {
        "ok": response.get("ok", False),
        "ts": response.get("ts"),
        "streamed": False
    }


@app.route("/stream", methods=["POST"])
def handle_stream():
    """
    HTTP endpoint for streaming messages to Slack.

    Expected JSON body:
    {
        "channel": "C123...",
        "thread_ts": "1234567890.123456",  # optional
        "text": "The message to stream"
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        channel = data.get("channel")
        text = data.get("text")
        thread_ts = data.get("thread_ts")

        if not channel:
            return jsonify({"error": "channel is required"}), 400

        if not text:
            return jsonify({"error": "text is required"}), 400

        result = stream_message(channel, text, thread_ts)

        return jsonify(result)

    except SlackApiError as e:
        return jsonify({
            "error": str(e),
            "slack_error": e.response.get("error")
        }), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "slack-streamer",
        "token_configured": bool(SLACK_BOT_TOKEN)
    })


@app.route("/post", methods=["POST"])
def handle_post():
    """
    Alternative endpoint for regular (non-streaming) messages.
    Useful when you want to send the full message at once.

    Expected JSON body:
    {
        "channel": "C123...",
        "thread_ts": "1234567890.123456",  # optional
        "text": "The message to post"
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        channel = data.get("channel")
        text = data.get("text")
        thread_ts = data.get("thread_ts")

        if not channel:
            return jsonify({"error": "channel is required"}), 400

        if not text:
            return jsonify({"error": "text is required"}), 400

        client = get_slack_client()
        result = post_regular_message(client, channel, text, thread_ts)

        return jsonify(result)

    except SlackApiError as e:
        return jsonify({
            "error": str(e),
            "slack_error": e.response.get("error")
        }), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8767))
    print(f"Starting Slack Streamer service on port {port}")
    print(f"Endpoints:")
    print(f"  POST /stream - Stream message to Slack")
    print(f"  POST /post   - Post message without streaming")
    print(f"  GET  /health - Health check")

    app.run(host="0.0.0.0", port=port, debug=False)
