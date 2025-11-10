#!/bin/bash
# Daily backup script for OEWS deployment
# Run via cron: 0 2 * * * /opt/oews/scripts/backup.sh

set -e

DATE=$(date +%Y-%m-%d)
BACKUP_DIR="/backup/oews"

# Create backup directory if doesn't exist
mkdir -p $BACKUP_DIR

echo "→ Starting backup: $DATE"

# Backup Caddy certificates (Docker volume)
echo "  → Backing up Caddy certificates..."
docker run --rm \
  -v oews_caddy_data:/data \
  -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/caddy-$DATE.tar.gz /data

# Backup database (stop container first to prevent corruption)
echo "  → Stopping API container for safe database backup..."
cd /opt/oews
docker compose stop oews-api

echo "  → Backing up database..."
cp /opt/oews/data/oews.db $BACKUP_DIR/oews-$DATE.db

echo "  → Restarting API container..."
docker compose start oews-api

# Backup .env (can be regenerated from GitHub Secrets, but backup anyway)
if [ -f /opt/oews/.env ]; then
    echo "  → Backing up .env..."
    cp /opt/oews/.env $BACKUP_DIR/env-$DATE
fi

# Keep last 7 backups only
echo "  → Cleaning old backups..."
find $BACKUP_DIR -name "caddy-*.tar.gz" -mtime +7 -delete
find $BACKUP_DIR -name "oews-*.db" -mtime +7 -delete
find $BACKUP_DIR -name "env-*" -mtime +7 -delete

# Report size
TOTAL_SIZE=$(du -sh $BACKUP_DIR | cut -f1)
echo "✓ Backup complete: $DATE (Total: $TOTAL_SIZE)"
