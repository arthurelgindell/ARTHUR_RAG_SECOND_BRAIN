# n8n Disaster Recovery Procedure

## Backup Locations

| Data | Location | Backup Script |
|------|----------|---------------|
| PostgreSQL database | `~/.n8n/backups/n8n_db_*.sql` | `~/.n8n/backup.sh` |
| n8n data | `~/.n8n/backups/n8n_data_*.tar.gz` | `~/.n8n/backup.sh` |
| Workflow JSON | `~/.claude/plugins/n8n-local/workflows/` | Git |
| Configuration | `~/.n8n/.env` | Manual |

## Automated Backups

Backups run daily at 2 AM via cron:

```cron
0 2 * * * ~/.n8n/backup.sh >> ~/.n8n/backup.log 2>&1
```

To set up cron:
```bash
(crontab -l 2>/dev/null; echo "0 2 * * * ~/.n8n/backup.sh >> ~/.n8n/backup.log 2>&1") | crontab -
```

## Recovery Scenarios

### Scenario 1: Container Crashed but Data Intact

**Symptoms:** n8n not responding, containers stopped

**Recovery:**
```bash
cd ~/.n8n
docker compose down
docker compose up -d
```

Wait 30 seconds, then verify:
```bash
curl http://localhost:5678/healthz
```

### Scenario 2: PostgreSQL Data Corrupted

**Symptoms:** n8n starts but shows database errors

**Recovery:**
```bash
# Stop containers
cd ~/.n8n && docker compose down

# Remove corrupted data
rm -rf ~/.n8n/data/postgres/*

# Restore from backup (use latest)
LATEST_BACKUP=$(ls -t ~/.n8n/backups/n8n_db_*.sql | head -1)
docker compose up -d postgres
sleep 10

# Restore database
docker exec -i n8n-postgres psql -U n8n n8n < "$LATEST_BACKUP"

# Start n8n
docker compose up -d
```

### Scenario 3: Complete Data Loss

**Symptoms:** All ~/.n8n/data/* missing

**Recovery:**
```bash
# Recreate directories
mkdir -p ~/.n8n/data/n8n ~/.n8n/data/postgres

# Restore n8n data
LATEST_DATA=$(ls -t ~/.n8n/backups/n8n_data_*.tar.gz | head -1)
tar -xzf "$LATEST_DATA" -C ~/.n8n/data/

# Restore database
docker compose up -d postgres
sleep 10
LATEST_DB=$(ls -t ~/.n8n/backups/n8n_db_*.sql | head -1)
docker exec -i n8n-postgres psql -U n8n n8n < "$LATEST_DB"

# Start n8n
docker compose up -d
```

### Scenario 4: Fresh Installation Required

**Symptoms:** Docker or system reinstalled

**Recovery:**
```bash
# Run initialization
~/.n8n/init.sh

# Start containers
cd ~/.n8n && docker compose up -d

# Wait for healthy status
sleep 30

# Restore database if backup exists
if ls ~/.n8n/backups/n8n_db_*.sql 1>/dev/null 2>&1; then
    LATEST_DB=$(ls -t ~/.n8n/backups/n8n_db_*.sql | head -1)
    docker exec -i n8n-postgres psql -U n8n n8n < "$LATEST_DB"
    echo "Database restored from $LATEST_DB"
fi

# Re-authenticate OAuth credentials
echo "Open http://localhost:5678 and re-authenticate Google credentials"
```

## Post-Recovery Checklist

After any recovery:

- [ ] Verify n8n UI accessible at http://localhost:5678
- [ ] Check container health: `docker ps`
- [ ] Test health check endpoint
- [ ] Re-authenticate OAuth credentials if needed
- [ ] Test Gmail workflow
- [ ] Test Calendar workflow
- [ ] Verify backup cron is configured

## Manual Backup Command

To create an immediate backup:
```bash
~/.n8n/backup.sh
```

## Backup Retention

- Automated backups: 7 days
- Location: `~/.n8n/backups/`
- To extend retention, edit `RETENTION_DAYS` in backup.sh

## Export Workflows (without credentials)

For version control:
```bash
source ~/.n8n/.env
for id in $(curl -s "http://localhost:5678/api/v1/workflows" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" | jq -r '.[].id'); do
    name=$(curl -s "http://localhost:5678/api/v1/workflows/$id" \
      -H "X-N8N-API-KEY: $N8N_API_KEY" | jq -r '.name' | tr ' ' '-' | tr '[:upper:]' '[:lower:]')
    curl -s "http://localhost:5678/api/v1/workflows/$id" \
      -H "X-N8N-API-KEY: $N8N_API_KEY" | \
      jq 'del(.nodes[].credentials)' > "workflows/${name}.json"
    echo "Exported: ${name}.json"
done
```

## Related

- [OAuth Re-Authentication](./OAUTH_REAUTH_PROCEDURE.md)
- [n8n Backup Documentation](https://docs.n8n.io/hosting/backup/)
