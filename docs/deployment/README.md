# OEWS Deployment Guide

## Quick Start

### Initial Setup (1.5 hours)

1. **Run server setup script on Linux machine:**
   ```bash
   ./scripts/setup-server.sh
   ```

2. **Add GitHub Secrets** (repository Settings → Secrets and variables → Actions):
   - `SERVER_HOST`: Your server IP
   - `SERVER_USER`: SSH username
   - `SSH_PRIVATE_KEY`: Private key from setup script
   - `SSH_HOST_FINGERPRINT`: Host fingerprint from setup script
   - `AZURE_AI_API_KEY`: Your Azure AI API key
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `CORS_ORIGINS`: Frontend domains (comma-separated, e.g., `https://app.bhavanaai.com,http://localhost:3000`)

3. **Copy files to server:**
   ```bash
   SERVER_IP="your-server-ip"
   scp docker-compose.yml Caddyfile user@$SERVER_IP:/opt/oews/
   scp data/oews.db user@$SERVER_IP:/opt/oews/data/
   scp scripts/backup.sh user@$SERVER_IP:/opt/oews/scripts/
   ssh user@$SERVER_IP 'chmod +x /opt/oews/scripts/backup.sh'
   ```

4. **Setup Azure Blob Storage for backups:**
   ```bash
   ssh user@$SERVER_IP
   # Install Azure CLI
   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

   # Login to Azure
   az login

   # Set storage account (add to ~/.bashrc or cron environment)
   export AZURE_STORAGE_ACCOUNT="your-storage-account-name"
   ```

5. **Create backup directory:**
   ```bash
   ssh user@$SERVER_IP 'sudo mkdir -p /backup/oews && sudo chown $USER:$USER /backup/oews'
   ```

6. **Setup automated backups:**
   ```bash
   ssh user@$SERVER_IP
   crontab -e
   # Add this line:
   0 2 * * * AZURE_STORAGE_ACCOUNT=your-account /opt/oews/scripts/backup.sh >> /var/log/oews-backup.log 2>&1
   ```

7. **Update DNS:**
   - Point `api.bhavanaai.com` → server IP
   - Wait 5-10 minutes for propagation

8. **Deploy:**
   ```bash
   git push origin main
   ```
   Deployment completes in 2-3 minutes.

9. **Verify:**
   ```bash
   curl https://api.bhavanaai.com/health
   ```

### Daily Development Workflow

```bash
# 1. Make changes
vim src/agents/planner.py

# 2. Commit and push
git add .
git commit -m "Improve planner reasoning"
git push origin main

# 3. Wait 2-3 minutes (GitHub Actions deploys automatically)

# 4. Test immediately
curl -X POST https://api.bhavanaai.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are software developer salaries in Seattle?"}'
```

### Quarterly Database Updates

```bash
# 1. Download new BLS data locally
python scripts/download_bls_data.py

# 2. Copy to server
scp data/oews.db user@server:/opt/oews/data/oews.db

# 3. Restart API (will pick up new database)
ssh user@server 'cd /opt/oews && docker compose restart oews-api'
```

## Monitoring

### View Logs

```bash
# Live logs
ssh user@server 'docker logs -f oews-api'

# Last 100 lines
ssh user@server 'docker logs --tail 100 oews-api'

# Search for errors
ssh user@server 'docker logs oews-api 2>&1 | grep ERROR'

# Caddy logs (HTTPS/access logs)
ssh user@server 'docker logs caddy'
```

### Check Status

```bash
# Container status
ssh user@server 'docker ps'

# Health check
curl https://api.bhavanaai.com/health

# Check disk space
ssh user@server 'df -h'
```

## Backup & Recovery

### Backup Strategy

**Automated Daily Backups:**
- **Local:** 7 most recent backups on server (`/backup/oews`)
- **Off-site:** 30 days retention in Azure Blob Storage
- **What's backed up:** SQLite database, Caddy TLS certificates, .env file
- **Special features:**
  - Zero-downtime backups (API stays running)
  - Integrity verification after each backup
  - Runs at 2am daily via cron

### Manual Backup

```bash
ssh user@server '/opt/oews/scripts/backup.sh'
```

### Restore from Backup

**Restore from local backup:**
```bash
ssh user@server
cd /opt/oews
docker compose stop oews-api

# List available backups
ls -lt /backup/oews/oews-*.db

# Restore database
cp /backup/oews/oews-2025-11-10.db data/oews.db

# Restore Caddy certificates if needed
docker run --rm \
  -v oews_caddy_data:/data \
  -v /backup/oews:/backup \
  alpine tar xzf /backup/caddy-2025-11-10.tar.gz -C /

# Restart
docker compose start oews-api
```

**Restore from Azure Blob Storage:**
```bash
ssh user@server

# List available backups
az storage blob list --container-name oews-backups --auth-mode login --output table

# Download database backup
az storage blob download \
  --container-name oews-backups \
  --name oews-2025-11-10.db \
  --file /opt/oews/data/oews.db \
  --auth-mode login

# Restart API
cd /opt/oews && docker compose restart oews-api
```

### Disaster Recovery

**Complete server rebuild:**

1. **Setup new server:**
   ```bash
   # On new server
   ./scripts/setup-server.sh
   ```

2. **Restore from Azure:**
   ```bash
   # Install Azure CLI
   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
   az login

   # Download latest backups
   az storage blob download --container-name oews-backups --name oews-latest.db --file /opt/oews/data/oews.db --auth-mode login
   az storage blob download --container-name oews-backups --name caddy-latest.tar.gz --file /tmp/caddy.tar.gz --auth-mode login
   az storage blob download --container-name oews-backups --name env-latest --file /opt/oews/.env --auth-mode login
   chmod 600 /opt/oews/.env
   ```

3. **Copy deployment files:**
   ```bash
   # From local machine
   scp docker-compose.yml Caddyfile user@new-server:/opt/oews/
   ```

4. **Start services:**
   ```bash
   ssh user@new-server 'cd /opt/oews && docker compose up -d'
   ```

5. **Update DNS to point to new server IP**

**RTO (Recovery Time Objective):** ~30 minutes
**RPO (Recovery Point Objective):** Up to 24 hours (daily backups)

## Troubleshooting

### Deployment Failed

```bash
# Check GitHub Actions logs in repository → Actions tab

# Check server logs
ssh user@server 'docker logs oews-api'

# Check recent errors
ssh user@server 'docker logs --tail 50 oews-api 2>&1 | grep -i error'

# Restart manually
ssh user@server 'cd /opt/oews && docker compose restart'
```

### SSL Certificate Issues

```bash
# Check Caddy logs
ssh user@server 'docker logs caddy'

# Verify DNS points to server
dig api.bhavanaai.com

# Force certificate renewal (restart Caddy)
ssh user@server 'docker compose restart caddy'

# Check ports are open
nmap -p 80,443 your-server-ip
```

### Database Not Found

```bash
# Verify database file exists
ssh user@server 'ls -lh /opt/oews/data/oews.db'

# Check mount in container
ssh user@server 'docker exec oews-api ls -lh /app/data/oews.db'

# Check database integrity
ssh user@server 'sqlite3 /opt/oews/data/oews.db "PRAGMA integrity_check;"'

# Restart container
ssh user@server 'docker compose restart oews-api'
```

### Backup Failures

```bash
# Check backup logs
ssh user@server 'tail -50 /var/log/oews-backup.log'

# Verify Azure CLI is configured
ssh user@server 'az account show'

# Test backup manually
ssh user@server '/opt/oews/scripts/backup.sh'

# Verify backup directory exists and is writable
ssh user@server 'ls -ld /backup/oews'
```

### Disk Space Running Low

```bash
# Check disk usage
ssh user@server 'df -h'

# Check Docker disk usage
ssh user@server 'docker system df'

# Clean up Docker resources
ssh user@server 'docker system prune -a --volumes -f'

# Check backup directory size
ssh user@server 'du -sh /backup/oews'

# Check log sizes
ssh user@server 'docker ps -q | xargs docker inspect --format="{{.Name}} {{.HostConfig.LogConfig}}"'
```

### High Memory/CPU Usage

```bash
# Check container resource usage
ssh user@server 'docker stats --no-stream'

# Check system resources
ssh user@server 'free -h && top -bn1 | head -20'

# Restart API if needed
ssh user@server 'docker compose restart oews-api'
```

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────┐
│ Internet                                                 │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ├─ HTTPS (443)
                      ├─ HTTP (80) → Redirect to HTTPS
                      │
┌─────────────────────▼───────────────────────────────────┐
│ Linux Server                                             │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Caddy (Reverse Proxy)                              │ │
│  │ - Automatic HTTPS (Let's Encrypt)                  │ │
│  │ - Security headers                                 │ │
│  │ - Access logging                                   │ │
│  └──────────────────┬─────────────────────────────────┘ │
│                     │ Port 8000                          │
│  ┌──────────────────▼─────────────────────────────────┐ │
│  │ OEWS API Container                                 │ │
│  │ - FastAPI application                              │ │
│  │ - Multi-agent workflow                             │ │
│  │ - Read-only SQLite database (bind mount)           │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Backup System                                      │ │
│  │ - Daily cron job (2am)                             │ │
│  │ - Zero-downtime SQLite backup                      │ │
│  │ - Local retention: 7 days                          │ │
│  │ - Azure Blob: 30 days                              │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ GitHub Actions (CI/CD)                                   │
│ - Builds Docker image on push to main                   │
│ - Weekly rebuild for base image patches (Sunday 2am)    │
│ - Pushes to GHCR                                         │
│ - SSH deployment to server                              │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ Azure Blob Storage                                       │
│ - Off-site backups                                       │
│ - 30-day retention                                       │
│ - Disaster recovery                                      │
└──────────────────────────────────────────────────────────┘
```

### Security Features

- **HTTPS:** Automatic with Let's Encrypt (Caddy)
- **Security Headers:** HSTS, X-Frame-Options, CSP, Referrer-Policy
- **CORS:** Environment-based origin restrictions
- **Secrets:** GitHub Secrets → .env file with 600 permissions
- **Non-root:** Application runs as non-root user in container
- **Read-only:** Database mounted read-only in container
- **SSH:** Key-based auth with host fingerprint verification
- **Supply Chain:** All GitHub Actions pinned to commit SHAs
- **Weekly Rebuilds:** Automatic base image security patches

## Cost

- **Server electricity:** ~$5/month (home server)
- **Domain name:** ~$1/month (Porkbun)
- **Azure Blob Storage:** ~$0.50/month (estimated for backups)
- **GitHub Actions:** $0 (free tier)
- **Total: ~$6.50/month**

## Performance

- **Build time:** ~2 minutes (with caching)
- **Deployment time:** ~1 minute (image pull + restart)
- **Total deployment:** **2-3 minutes** (push to production)
- **Zero downtime:** Health checks ensure smooth transitions

## Security Best Practices Implemented

✅ **Eliminated Watchtower** - Removed Docker socket access vulnerability
✅ **Pinned GitHub Actions** - All actions use commit SHAs
✅ **Weekly rebuilds** - Automatic base image security patches
✅ **Enhanced TLS headers** - HSTS, CSP, Referrer-Policy
✅ **Zero-downtime backups** - SQLite .backup API
✅ **Integrity verification** - Every backup validated
✅ **Off-site replication** - Azure Blob Storage
✅ **Environment-based CORS** - No wildcard origins

## Maintenance Tasks

**Weekly (automated):**
- GitHub Actions rebuild (Sunday 2am) - base image patches

**Daily (automated):**
- Backups to local + Azure (2am)
- Log rotation (Docker handles)

**Monthly (manual):**
- Review disk space: `ssh server 'df -h'`
- Review backup logs: `ssh server 'tail -100 /var/log/oews-backup.log'`
- Check container health: `ssh server 'docker ps'`

**Quarterly (manual):**
- Update database: Download new BLS data, copy to server, restart
- Test disaster recovery: Restore from Azure backup to test environment
- Review and rotate SSH keys if needed
- Review Azure Blob costs

**Annually:**
- Review and update dependencies in pyproject.toml
- Review security practices
- Update documentation

## Related Documentation

- Design: `docs/plans/2025-11-09-docker-compose-deployment-design-v2.md`
- Security Reviews: `.claude/phone-a-friend/2025-11-10-*-review.md`
