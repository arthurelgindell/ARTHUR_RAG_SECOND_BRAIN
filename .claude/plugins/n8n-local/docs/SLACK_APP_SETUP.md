# ARTHUR Slack App Setup Guide

Complete setup guide for creating and configuring the ARTHUR Slack bot.

## Prerequisites

- Slack workspace with admin access
- n8n running at `localhost:5678`
- Anthropic API key

---

## Step 1: Create Slack App

1. Go to https://api.slack.com/apps
2. Click **Create New App**
3. Select **From scratch**
4. App Name: `ARTHUR`
5. Select your workspace
6. Click **Create App**

---

## Step 2: Enable Socket Mode

Socket Mode allows the bot to receive events without a public URL.

1. Go to **Settings** → **Socket Mode**
2. Toggle **Enable Socket Mode** to ON
3. Click **Generate Token**
4. Name: `arthur-socket-token`
5. Save the `xapp-...` token (App-Level Token)

---

## Step 3: Enable Agents & AI Apps

This unlocks streaming, Chat tab, and suggested prompts.

1. Go to **Settings** → **Basic Information**
2. Scroll to **App-Level Tokens & Features**
3. Find **Agents & AI Apps** toggle
4. Enable it

---

## Step 4: Configure Bot Token Scopes

1. Go to **Features** → **OAuth & Permissions**
2. Scroll to **Scopes** → **Bot Token Scopes**
3. Add these scopes:

| Scope | Purpose |
|-------|---------|
| `app_mentions:read` | Receive @mentions |
| `channels:history` | Read channel messages for context |
| `chat:write` | Send messages |
| `im:history` | Read DM history |
| `im:read` | Access DM channels |
| `im:write` | Send DMs |
| `users:read` | Get user info |

---

## Step 5: Configure Event Subscriptions

1. Go to **Features** → **Event Subscriptions**
2. Toggle **Enable Events** to ON
3. Under **Subscribe to bot events**, add:
   - `app_mention` - When bot is @mentioned in channels
   - `message.im` - Direct messages to the bot

---

## Step 6: Configure App Home

1. Go to **Features** → **App Home**
2. Enable **Home Tab** (optional, for dashboard)
3. Enable **Messages Tab** → Will show as "Chat" with AI Apps enabled
4. Check **Allow users to send Slash commands and messages from the messages tab**

---

## Step 7: Install App to Workspace

1. Go to **Settings** → **Install App**
2. Click **Install to Workspace**
3. Authorize the requested permissions
4. Copy the **Bot User OAuth Token** (`xoxb-...`)

---

## Step 8: Configure Suggested Prompts (Optional)

If using the AI Apps interface:

1. Go to **Features** → **App Home**
2. Under **Suggested Prompts**, add:
   - "What's on my calendar today?"
   - "Search my notes for [topic]"
   - "Research [topic] for me"
   - "Check my recent emails"

---

## Step 9: Get Credentials for n8n

You need these values for n8n configuration:

| Credential | Location | Example |
|------------|----------|---------|
| Bot Token | OAuth & Permissions | `xoxb-123456789-...` |
| Signing Secret | Basic Information | `abc123def456...` |
| App Token | Socket Mode | `xapp-1-A0...` |

---

## Step 10: Configure n8n Slack Credentials

1. Open n8n at `http://localhost:5678`
2. Go to **Settings** → **Credentials**
3. Click **Add Credential** → **Slack API**
4. Enter:
   - **Access Token**: Your Bot Token (`xoxb-...`)
5. Save

For Socket Mode triggers, also create:
- **Slack App Token** credential with the `xapp-...` token

---

## Environment Variables

Add to your `.env` or n8n environment:

```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_APP_TOKEN=xapp-your-app-token
```

---

## Testing the Connection

1. In Slack, find the ARTHUR bot in Apps
2. Send a DM: "Hello"
3. Check n8n executions to verify the trigger fired

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Bot not responding | Check Socket Mode is enabled |
| "missing_scope" error | Add required scope in OAuth & Permissions, reinstall app |
| Events not received | Verify Event Subscriptions are enabled |
| Can't DM bot | Enable Messages Tab in App Home |

---

## Next Steps

After setup, deploy the `slack-agent.json` workflow in n8n to enable full conversational capabilities.
