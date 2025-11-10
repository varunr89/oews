#!/bin/bash
# Daily backup script for OEWS deployment with Azure Blob off-site replication
# Run via cron: 0 2 * * * /opt/oews/scripts/backup.sh
#
# Prerequisites:
# 1. Install Azure CLI: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
# 2. Set environment variables:
#    export AZURE_STORAGE_ACCOUNT="your-storage-account"
#    export AZURE_STORAGE_KEY="your-storage-key"
#    Or use: az login (for managed identity)

set -e

DATE=$(date +%Y-%m-%d)
BACKUP_DIR="/backup/oews"
CONTAINER_NAME="oews-backups"

# Create backup directory if doesn't exist
mkdir -p "$BACKUP_DIR"

echo "→ Starting backup: $DATE"

# Backup Caddy certificates (Docker volume)
echo "  → Backing up Caddy certificates..."
docker run --rm \
  -v oews_caddy_data:/data \
  -v "$BACKUP_DIR":/backup \
  alpine tar czf "/backup/caddy-$DATE.tar.gz" /data

# Backup database with zero-downtime using SQLite .backup command
echo "  → Backing up database (zero-downtime with SQLite .backup)..."
docker exec oews-api sqlite3 /app/data/oews.db ".backup '/app/data/oews-$DATE.db.tmp'"
docker cp "oews-api:/app/data/oews-$DATE.db.tmp" "$BACKUP_DIR/oews-$DATE.db"
docker exec oews-api rm "/app/data/oews-$DATE.db.tmp"

# Verify backup integrity
echo "  → Verifying backup integrity..."
if ! sqlite3 "$BACKUP_DIR/oews-$DATE.db" "PRAGMA integrity_check;" | grep -qx 'ok'; then
    echo "ERROR: Backup integrity check failed!"
    exit 1
fi
echo "  ✓ Integrity check passed"

# Backup .env (can be regenerated from GitHub Secrets, but backup anyway)
if [ -f /opt/oews/.env ]; then
    echo "  → Backing up .env..."
    cp /opt/oews/.env "$BACKUP_DIR/env-$DATE"
fi

# Sync to Azure Blob Storage (off-site backup)
if command -v az &> /dev/null && [ -n "$AZURE_STORAGE_ACCOUNT" ]; then
    echo "  → Syncing to Azure Blob Storage..."

    # Create container if it doesn't exist
    az storage container create --name "$CONTAINER_NAME" --auth-mode login 2>/dev/null || true

    # Upload today's backups
    az storage blob upload --container-name "$CONTAINER_NAME" \
        --name "caddy-$DATE.tar.gz" \
        --file "$BACKUP_DIR/caddy-$DATE.tar.gz" \
        --overwrite \
        --auth-mode login

    az storage blob upload --container-name "$CONTAINER_NAME" \
        --name "oews-$DATE.db" \
        --file "$BACKUP_DIR/oews-$DATE.db" \
        --overwrite \
        --auth-mode login

    if [ -f "$BACKUP_DIR/env-$DATE" ]; then
        az storage blob upload --container-name "$CONTAINER_NAME" \
            --name "env-$DATE" \
            --file "$BACKUP_DIR/env-$DATE" \
            --overwrite \
            --auth-mode login
    fi

    echo "  ✓ Off-site backup complete"
else
    echo "  ⚠ Azure CLI not configured, skipping off-site backup"
    echo "    Set AZURE_STORAGE_ACCOUNT and run 'az login' to enable"
fi

# Keep last 7 local backups (count-based, not age-based)
echo "  → Cleaning old local backups (keeping 7 most recent)..."
ls -1t "$BACKUP_DIR"/caddy-*.tar.gz 2>/dev/null | tail -n +8 | xargs -r rm --
ls -1t "$BACKUP_DIR"/oews-*.db 2>/dev/null | tail -n +8 | xargs -r rm --
ls -1t "$BACKUP_DIR"/env-* 2>/dev/null | tail -n +8 | xargs -r rm --

# Clean old Azure backups (keep 30 days)
if command -v az &> /dev/null && [ -n "$AZURE_STORAGE_ACCOUNT" ]; then
    echo "  → Cleaning old Azure backups (keeping 30 days)..."
    CUTOFF_DATE=$(date -d '30 days ago' +%Y-%m-%d 2>/dev/null || date -v-30d +%Y-%m-%d)

    az storage blob list --container-name "$CONTAINER_NAME" --auth-mode login --query "[?properties.creationTime<'$CUTOFF_DATE'].name" -o tsv 2>/dev/null | \
        xargs -I {} az storage blob delete --container-name "$CONTAINER_NAME" --name {} --auth-mode login 2>/dev/null || true
fi

# Report sizes
LOCAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo "✓ Backup complete: $DATE"
echo "  Local backups: $LOCAL_SIZE"

if command -v az &> /dev/null && [ -n "$AZURE_STORAGE_ACCOUNT" ]; then
    BLOB_COUNT=$(az storage blob list --container-name "$CONTAINER_NAME" --auth-mode login --query "length(@)" -o tsv 2>/dev/null || echo "0")
    echo "  Azure Blob backups: $BLOB_COUNT files"
fi
