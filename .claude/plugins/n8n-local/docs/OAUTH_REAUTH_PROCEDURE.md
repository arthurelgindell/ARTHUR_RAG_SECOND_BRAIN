# OAuth Token Re-Authentication Procedure

## When to Use This Procedure

You need to re-authenticate when:
- Token health check reports "unhealthy" status
- Workflows fail with OAuth/authentication errors
- Google revokes tokens due to security concerns
- Tokens expire after extended inactivity (7+ days)

## Prerequisites

- Access to n8n UI at http://localhost:5678
- Google account credentials for the connected account
- Browser with saved Google login (recommended)

## Re-Authentication Steps

### Step 1: Access n8n Credentials

1. Open browser to **http://localhost:5678**
2. Log in if prompted
3. Navigate to **Settings** (gear icon in left sidebar)
4. Click **Credentials**

### Step 2: Re-authenticate Gmail

1. Find the credential named **"Gmail OAuth2"** (or similar)
2. Click **Edit** (pencil icon)
3. Click **Connect** or **Reconnect**
4. Complete the Google sign-in flow:
   - Select your Google account
   - Review permissions requested
   - Click **Allow**
5. Verify the credential shows as connected
6. Click **Save**

### Step 3: Re-authenticate Google Calendar

1. Find the credential named **"Google Calendar OAuth2"** (or similar)
2. Click **Edit**
3. Click **Connect** or **Reconnect**
4. Complete the Google sign-in flow
5. Verify connection
6. Click **Save**

### Step 4: Verify Token Health

Run the health check workflow:

```bash
source ~/.n8n/.env
curl -s http://localhost:5678/webhook/health-check \
  -H "X-API-Key: $N8N_WEBHOOK_SECRET" | jq
```

Expected response:
```json
{
  "overall": "healthy",
  "gmail": { "status": "healthy", "error": null },
  "calendar": { "status": "healthy", "error": null },
  "requiresAction": false
}
```

### Step 5: Test Workflows

Test Gmail:
```bash
source ~/.n8n/.env
curl -s http://localhost:5678/webhook/gmail-search \
  -H "X-API-Key: $N8N_WEBHOOK_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"query": "is:unread", "maxResults": 1}' | jq '.count'
```

Test Calendar:
```bash
source ~/.n8n/.env
curl -s http://localhost:5678/webhook/calendar-today \
  -H "X-API-Key: $N8N_WEBHOOK_SECRET" | jq '.count'
```

## Troubleshooting

### "Access denied" during Google sign-in

- Ensure you're signing in with the correct Google account
- Check that the OAuth app hasn't been revoked in Google Account settings
- Verify OAuth consent screen is configured in Google Cloud Console

### Token still shows unhealthy after re-auth

1. Delete the existing credential in n8n
2. Create a new credential with the same name
3. Update any workflows that reference the old credential ID

### Rate limit errors

- Wait 15 minutes before retrying
- Consider reducing workflow frequency
- Check Gmail API quotas in Google Cloud Console

## Prevention

To minimize re-authentication frequency:

1. **Keep workflows active**: Tokens refresh when used
2. **Run health check daily**: Catches issues early
3. **Monitor alerts**: Respond to CRITICAL notifications promptly
4. **Avoid inactivity**: Tokens expire after 7 days without use

## Related

- [Disaster Recovery](./DISASTER_RECOVERY.md)
- [n8n Google Integration Docs](https://docs.n8n.io/integrations/builtin/credentials/google/)
