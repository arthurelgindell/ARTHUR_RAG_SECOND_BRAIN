---
name: notebooklm-auth
description: Authenticate or re-authenticate with Google NotebookLM
arguments:
  - name: mode
    description: "Authentication mode: 'auto' (default) or 'manual'"
    required: false
---

# NotebookLM Authentication

This command helps you authenticate with Google NotebookLM for the MCP integration.

## Instructions

Based on the requested mode, guide the user through authentication:

### Auto Mode (Default)

1. Run the authentication command:
   ```bash
   notebooklm-mcp-auth
   ```

2. A Chrome browser window will open automatically

3. Log in to your Google account when prompted

4. Once logged in, cookies will be extracted automatically

5. The browser will close and tokens will be saved to `~/.notebooklm-mcp/auth.json`

### Manual Mode

1. Run the authentication command with --file flag:
   ```bash
   notebooklm-mcp-auth --file
   ```

2. Open Chrome and navigate to https://notebooklm.google.com

3. Open Chrome DevTools (F12 or Cmd+Option+I)

4. Go to Application > Cookies > notebooklm.google.com

5. Copy the required cookies as instructed by the tool

6. Paste the cookies when prompted

## Verification

After authentication, verify the setup:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/verify_auth.py
```

Or test the MCP connection:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/verify_auth.py --test
```

## Troubleshooting

### Cookies Expired
Cookies typically expire every 2-4 weeks. Re-run this command to refresh.

### Chrome Not Found
Auto mode requires Chrome to be installed. Use manual mode as alternative.

### Authentication Failed
1. Ensure you're logged into the correct Google account
2. Check that NotebookLM is accessible at https://notebooklm.google.com
3. Try manual mode if auto mode fails

## After Authentication

Once authenticated, restart Claude Code to load the MCP server with the new credentials.

Then try listing your notebooks:
```
List my NotebookLM notebooks
```
