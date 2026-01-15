#!/bin/bash
# n8n Backup Script
# Backs up PostgreSQL database and n8n data
# Run daily via cron: 0 2 * * * ~/.n8n/backup.sh >> ~/.n8n/backup.log 2>&1

set -e

N8N_DIR="$HOME/.n8n"
BACKUP_DIR="$N8N_DIR/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

echo "=== n8n Backup: $DATE ==="

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Check if containers are running
if ! docker ps | grep -q n8n-postgres; then
    echo "ERROR: n8n-postgres container is not running"
    exit 1
fi

# Backup PostgreSQL database
echo "[1/3] Backing up PostgreSQL database..."
docker exec n8n-postgres pg_dump -U n8n n8n > "$BACKUP_DIR/n8n_db_$DATE.sql"

if [ -f "$BACKUP_DIR/n8n_db_$DATE.sql" ]; then
    DB_SIZE=$(du -h "$BACKUP_DIR/n8n_db_$DATE.sql" | cut -f1)
    echo "    Database backup: $BACKUP_DIR/n8n_db_$DATE.sql ($DB_SIZE)"
else
    echo "ERROR: Database backup failed"
    exit 1
fi

# Backup n8n data directory
echo "[2/3] Backing up n8n data..."
if [ -d "$N8N_DIR/data/n8n" ]; then
    tar -czf "$BACKUP_DIR/n8n_data_$DATE.tar.gz" -C "$N8N_DIR/data" n8n
    DATA_SIZE=$(du -h "$BACKUP_DIR/n8n_data_$DATE.tar.gz" | cut -f1)
    echo "    Data backup: $BACKUP_DIR/n8n_data_$DATE.tar.gz ($DATA_SIZE)"
else
    echo "    WARNING: n8n data directory not found, skipping"
fi

# Clean up old backups
echo "[3/3] Cleaning up backups older than $RETENTION_DAYS days..."
DELETED=$(find "$BACKUP_DIR" -name "n8n_*" -mtime +$RETENTION_DAYS -type f -delete -print | wc -l)
echo "    Deleted $DELETED old backup files"

# Summary
echo ""
echo "=== Backup Complete ==="
echo "Location: $BACKUP_DIR"
echo "Files:"
ls -lh "$BACKUP_DIR"/n8n_*_$DATE* 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
echo ""
