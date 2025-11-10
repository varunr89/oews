# OEWS API Deployment Design - Docker Compose for High Development Velocity

**Date:** 2025-11-09
**Status:** Design Complete
**Goal:** Deploy OEWS FastAPI application with maximum development velocity - minimal infrastructure complexity, fast iterations on agent development

## Design Priorities

1. **Development velocity first** - Spend time building the agent, not managing infrastructure
2. **Simple deployment** - Push code, wait 5 minutes, it's live
3. **Easy debugging** - Docker logs, not Kubernetes troubleshooting
4. **Low operational burden** - Set up once, forget about it

## Architecture Overview

### Single-Machine Stack

```
Internet (HTTPS)
    ↓
Caddy (reverse proxy + Let's Encrypt SSL)
    ↓
FastAPI Container (OEWS agent)
    ↓
Azure SQL Database (cloud-hosted, serverless)
```

**Key Design Decisions:**

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Orchestration | Docker Compose | Simple, fast setup, adequate for single machine |
| Reverse Proxy | Caddy | Zero-config HTTPS with Let's Encrypt |
| Database | Azure SQL Serverless | Managed, auto-pause when idle, $1-3/month |
| Secrets | GitHub Secrets → .env | Secure, version controlled, auto-deployed |
| Deployments | GitHub Actions + Watchtower | Push to main → auto-deploy in 5 min |
| Monitoring | Docker logs + health endpoint | Simple, adequate for development |

### Why Not Kubernetes?

**Complexity avoided:**
- No MetalLB, persistent volumes, ingress controllers
- No pod scheduling, node affinity, taints
- No External Secrets Operator, Helm charts
- No multi-node networking complexity

**Time saved:**
- Setup: 2 hours vs 2 days
- Debug: `docker logs` vs `kubectl describe/events/logs`
- Deploy: Automatic vs manual `kubectl set image`

**Trade-off accepted:**
- Single point of failure (one machine)
- Manual cloud migration later (if needed)
- No auto-scaling (not needed for your workload)

## Infrastructure Components

### 1. Server Setup

**Requirements:**
- 1 Linux machine (Ubuntu/Debian recommended)
- 4GB+ RAM
- 50GB+ disk
- Public IP or accessible via port forwarding
- Docker installed

**Directory structure:**
```
/opt/oews/
├── docker-compose.yml
├── .env                    # Written by GitHub Actions
├── Caddyfile
└── caddy_data/            # SSL certificates (persistent)
```

### 2. Docker Compose Stack

**docker-compose.yml:**

```yaml
version: '3.8'

services:
  oews-api:
    image: ghcr.io/yourusername/oews-api:latest
    container_name: oews-api
    restart: unless-stopped
    ports:
      - "127.0.0.1:8000:8000"  # Only localhost access
    env_file:
      - .env
    labels:
      - "com.centurylinklabs.watchtower.enable=true"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 3s
      retries: 3

  caddy:
    image: caddy:2-alpine
    container_name: caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - oews-api

  watchtower:
    image: containrrr/watchtower
    container_name: watchtower
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ~/.docker/config.json:/config.json:ro  # GHCR credentials
    command: --interval 300 --cleanup --label-enable
    environment:
      - WATCHTOWER_NOTIFICATIONS=shoutrrr
      - WATCHTOWER_NOTIFICATION_URL=${WATCHTOWER_URL}  # Optional

volumes:
  caddy_data:
  caddy_config:
```

**What each service does:**
- **oews-api:** Your FastAPI application, only accessible via Caddy
- **caddy:** Handles HTTPS, automatic SSL certificates, reverse proxy
- **watchtower:** Polls GitHub Container Registry every 5 minutes, auto-updates containers

### 3. Caddy Configuration

**Caddyfile:**

```
api.yourdomain.com {
    reverse_proxy oews-api:8000

    # Automatic HTTPS with Let's Encrypt
    # No configuration needed - Caddy handles it

    # Security headers
    header {
        X-Frame-Options "DENY"
        X-Content-Type-Options "nosniff"
        Strict-Transport-Security "max-age=31536000;"
    }

    # Optional: Rate limiting
    rate_limit {
        zone api {
            key {remote_host}
            events 100
            window 1m
        }
    }
}
```

**Features:**
- Automatic HTTPS certificate from Let's Encrypt
- Auto-renewal every 60 days
- HTTP → HTTPS redirect
- Security headers

### 4. Azure SQL Database

**Configuration:**

```bash
# Create serverless database
az sql db create \
  --resource-group oews-rg \
  --server oews-sql-server \
  --name oews \
  --edition GeneralPurpose \
  --compute-model Serverless \
  --family Gen5 \
  --capacity 1 \
  --auto-pause-delay 60 \
  --min-capacity 0.5
```

**Why Serverless:**
- Auto-pauses after 1 hour of inactivity (pay $0)
- Wakes up in <1 second on first query
- Scales automatically if traffic increases
- Perfect for development/low-traffic workloads

**Cost breakdown:**
- Storage: $0.115/GB/month × 2.2GB = $0.25/month
- Compute: ~$0.50-2.50/month (depends on usage)
- **Total: $1-3/month**

**Migration from SQLite:**

See `scripts/migrate_sqlite_to_azure_sql.py` for automated migration.

Key changes in application code:

```python
# Before (SQLite)
import sqlite3
conn = sqlite3.connect('data/oews.db')

# After (Azure SQL)
import pyodbc
conn = pyodbc.connect(os.getenv('AZURE_SQL_CONNECTION_STRING'))
```

### 5. Secrets Management

**Strategy: GitHub Secrets → .env file**

**GitHub Secrets (repository settings):**
- `AZURE_AI_API_KEY` - Azure AI API key
- `OPENAI_API_KEY` - OpenAI API key
- `AZURE_SQL_CONNECTION_STRING` - Database connection string
- `SERVER_HOST` - Server IP or hostname
- `SERVER_USER` - SSH username
- `SSH_PRIVATE_KEY` - Private key for GitHub Actions
- `WATCHTOWER_URL` - Optional notification URL

**Deployment flow:**
1. GitHub Actions builds image
2. GitHub Actions SSH to server
3. Writes `.env` file with secrets from GitHub Secrets
4. Watchtower detects new image, pulls, restarts

**Security:**
- Secrets never committed to git
- Secrets never baked into Docker image layers
- `.env` file permissions: 600 (owner read/write only)
- Rotation: Update in GitHub → next deployment picks up new value

### 6. Dockerfile

**Optimized for small image size (no 2.2GB database):**

```dockerfile
FROM python:3.14-slim

# Install SQL Server ODBC driver
RUN apt-get update && apt-get install -y \
    curl apt-transport-https gnupg2 && \
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && \
    uv pip install --system -e . && \
    uv pip install --system pyodbc

# Copy application code (NO DATABASE)
COPY src/ ./src/
COPY config/ ./config/

# Security: non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "src.main"]
```

**Image size:**
- Before (SQLite in image): 2.5GB
- After (Azure SQL): 350MB

**Build time:**
- Code change: 30 seconds
- Dependency change: 2 minutes
- No more 3-5 minute builds for database updates

## Deployment Workflow

### GitHub Actions Pipeline

**.github/workflows/deploy.yml:**

```yaml
name: Build and Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:  # Manual trigger option

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix={{branch}}-
            type=raw,value=latest

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Deploy secrets to server
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/oews

            # Write .env file with secrets
            cat > .env << 'EOF'
            AZURE_AI_API_KEY=${{ secrets.AZURE_AI_API_KEY }}
            OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }}
            AZURE_SQL_CONNECTION_STRING=${{ secrets.AZURE_SQL_CONNECTION_STRING }}
            DATABASE_ENV=prod
            API_HOST=0.0.0.0
            API_PORT=8000
            API_RELOAD=false
            EOF

            # Set secure permissions
            chmod 600 .env

            echo "✓ Secrets deployed. Watchtower will pull new image within 5 minutes."
```

### Daily Development Workflow

**Your iteration cycle (< 5 minutes total):**

```bash
# 1. Make changes to agent code
vim src/agents/planner.py

# 2. Commit and push
git add .
git commit -m "Improve planner reasoning"
git push origin main

# 3. Wait 3-5 minutes
# GitHub Actions: Build (30s) + Push (1min) + Deploy secrets (10s)
# Watchtower: Detect (0-5min) + Pull (1min) + Restart (10s)

# 4. Test
curl -X POST https://api.yourdomain.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are software developer salaries in Seattle?"}'
```

**No SSH, no kubectl, no manual deployment steps.**

### Database Updates (Quarterly)

**Old workflow (SQLite in image):**
```bash
# Download new BLS data
python scripts/download_bls_data.py

# Commit and rebuild entire image
git add data/oews.db
git commit -m "Update Q4 2025 OEWS data"
git push

# Wait 5-10 minutes for 2.5GB image rebuild + deploy
```

**New workflow (Azure SQL):**
```bash
# Download new BLS data
python scripts/download_bls_data.py

# Import directly to Azure SQL
python scripts/import_to_azure_sql.py

# Done - no deployment needed, app uses new data immediately
# Takes 2-3 minutes
```

**Import script example:**

```python
# scripts/import_to_azure_sql.py
import pyodbc
import pandas as pd
from pathlib import Path

conn_str = os.getenv('AZURE_SQL_CONNECTION_STRING')
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Truncate and reload tables
for csv_file in Path('data/csv/').glob('*.csv'):
    table_name = csv_file.stem

    print(f"Importing {table_name}...")

    # Truncate existing data
    cursor.execute(f"TRUNCATE TABLE {table_name}")

    # Load CSV
    df = pd.read_csv(csv_file)

    # Bulk insert
    for _, row in df.iterrows():
        placeholders = ','.join(['?' for _ in row])
        cursor.execute(
            f"INSERT INTO {table_name} VALUES ({placeholders})",
            tuple(row)
        )

    conn.commit()
    print(f"✓ {table_name}: {len(df)} rows")

conn.close()
```

## Monitoring & Debugging

### Built-in Monitoring (Zero Setup)

**1. Docker Logs (from your Mac):**

```bash
# Live logs
ssh server 'docker logs -f oews-api'

# Last 100 lines
ssh server 'docker logs --tail 100 oews-api'

# Search for errors
ssh server 'docker logs oews-api 2>&1 | grep ERROR'

# Container status
ssh server 'docker ps'
```

**2. Health Check Endpoint:**

```bash
# Quick status check
curl https://api.yourdomain.com/health

# Expected response:
{
  "status": "healthy",
  "workflow_loaded": true
}
```

**3. Watchtower Notifications (Optional):**

Add to GitHub Secrets:
```
WATCHTOWER_URL=discord://token@id
# or slack://token@channel
# or gotify://server/token
```

Get notified when:
- New image deployed successfully
- Deployment failed
- Container health check failed

### Optional: Prometheus + Grafana

**Add to docker-compose.yml only if needed:**

```yaml
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    ports:
      - "127.0.0.1:9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=7d'

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: unless-stopped
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "127.0.0.1:3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false

volumes:
  prometheus_data:
  grafana_data:
```

**Access via SSH tunnel:**
```bash
ssh -L 3000:localhost:3000 server
# Open http://localhost:3000
```

**Recommendation:** Start without Prometheus/Grafana. Add later only if you need dashboards.

## Security Considerations

### Network Security

**Firewall rules (UFW):**
```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
```

**Container network isolation:**
- API container: Only accessible via Caddy (127.0.0.1:8000)
- No direct internet access to API port
- All traffic flows through HTTPS

### Secrets Security

- Secrets stored in GitHub (encrypted at rest)
- `.env` file permissions: 600 (owner only)
- Secrets never in git history
- Secrets never in Docker image layers
- SSH key for GitHub Actions (rotate periodically)

### Application Security

**Current (from your design):**
- Non-root container user
- CORS restricted to frontend domains
- Parameterized SQL queries (no SQL injection)
- Read-only database access

**Additions:**
- Rate limiting (Caddy middleware)
- Security headers (CSP, XSS protection)
- HTTPS-only (HTTP → HTTPS redirect)
- Health check endpoint (public, no sensitive data)

### Azure SQL Security

- Encrypted connections (TLS 1.2+)
- Firewall rules (only your server IP)
- Read-only credentials for application
- Admin credentials separate, not in app
- Automatic backups (point-in-time restore)

## Disaster Recovery

### Backup Strategy

**What needs backup:**
1. Docker Compose files (in git)
2. Caddy certificates (in Docker volume `caddy_data`)
3. Azure SQL database (automatic backups)
4. `.env` file (can be regenerated from GitHub Secrets)

**Automated backups:**

```bash
#!/bin/bash
# /opt/oews/backup.sh

DATE=$(date +%Y-%m-%d)
BACKUP_DIR="/backup/oews"

# Backup Caddy certificates
docker run --rm \
  -v oews_caddy_data:/data \
  -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/caddy-$DATE.tar.gz /data

# Backup .env
cp /opt/oews/.env $BACKUP_DIR/env-$DATE

# Keep last 7 backups
find $BACKUP_DIR -name "caddy-*.tar.gz" -mtime +7 -delete
find $BACKUP_DIR -name "env-*" -mtime +7 -delete

echo "✓ Backup complete: $DATE"
```

**Run daily via cron:**
```bash
0 2 * * * /opt/oews/backup.sh
```

### Recovery Procedures

**Scenario 1: Container crash**
- Auto-recovered by Docker (restart: unless-stopped)
- No action needed

**Scenario 2: Server restart**
- Docker Compose auto-starts on boot (enable: `sudo systemctl enable docker`)
- All containers resume automatically
- Downtime: ~30 seconds

**Scenario 3: Complete server loss**

Recovery steps (30-60 minutes):
```bash
# 1. New server setup
curl -fsSL https://get.docker.com | sh

# 2. Restore files
git clone https://github.com/yourusername/oews.git /opt/oews
cd /opt/oews

# 3. Restore Caddy certificates (optional, will regenerate)
tar xzf /backup/caddy-latest.tar.gz -C /

# 4. Update DNS
# Point api.yourdomain.com → new server IP

# 5. Deploy
# GitHub Actions will write .env and deploy on next push
git commit --allow-empty -m "Trigger deployment"
git push

# Or manually write .env and start:
docker compose up -d
```

**Scenario 4: Azure SQL corruption**
- Point-in-time restore via Azure portal
- Restore to any point in last 7 days
- Update connection string if needed

**RTO/RPO:**
- Recovery Time Objective: 1 hour
- Recovery Point Objective: Last deployment (code) + last Azure SQL backup (data, within seconds)

## Cost Summary

| Component | Provider | Monthly Cost |
|-----------|----------|--------------|
| Azure SQL Serverless | Azure | $1-3 |
| Azure AI API | Azure | Variable (existing) |
| Domain name | Registrar | ~$1 |
| Server electricity | Self-hosted | ~$5 |
| GitHub Actions | GitHub | $0 (free tier) |
| GitHub Container Registry | GitHub | $0 (free tier) |
| Caddy | Self-hosted | $0 |
| **Total** | | **$7-10/month** |

**Compared to Kubernetes on cloud:**
- AWS EKS: $73/month (control plane) + $30/month (t3.medium worker) = $103/month
- Your setup: $7-10/month

**Compared to managed services:**
- Render/Railway/Fly.io: $20-40/month
- Your setup: $7-10/month + learning investment

## Implementation Checklist

### Phase 1: Server Setup (30 minutes)

- [ ] Install Docker on Linux machine
- [ ] Create `/opt/oews` directory
- [ ] Configure firewall (UFW)
- [ ] Generate SSH key for GitHub Actions
- [ ] Add SSH public key to server `~/.ssh/authorized_keys`
- [ ] Test SSH access from GitHub Actions

### Phase 2: Azure SQL Setup (30 minutes)

- [ ] Create Azure SQL server
- [ ] Create serverless database
- [ ] Configure firewall rules (allow server IP)
- [ ] Run migration script: `scripts/migrate_sqlite_to_azure_sql.py`
- [ ] Test connection from local machine
- [ ] Get connection string for production

### Phase 3: GitHub Configuration (20 minutes)

- [ ] Add SSH private key to GitHub Secrets
- [ ] Add server host/user to GitHub Secrets
- [ ] Add API keys to GitHub Secrets
- [ ] Add Azure SQL connection string to GitHub Secrets
- [ ] Create `.github/workflows/deploy.yml`
- [ ] Test workflow with empty commit

### Phase 4: Server Files (10 minutes)

- [ ] Copy `docker-compose.yml` to `/opt/oews/`
- [ ] Copy `Caddyfile` to `/opt/oews/`
- [ ] Login to GitHub Container Registry: `docker login ghcr.io`
- [ ] Save Docker credentials for Watchtower
- [ ] Test: `docker compose up -d`

### Phase 5: DNS & SSL (10 minutes)

- [ ] Point `api.yourdomain.com` to server public IP
- [ ] Wait for DNS propagation (5-10 minutes)
- [ ] Test: `curl https://api.yourdomain.com/health`
- [ ] Verify SSL certificate (browser shows padlock)

### Phase 6: Application Code Changes (20 minutes)

- [ ] Update `src/database/connection.py` for Azure SQL
- [ ] Add `pyodbc` to `pyproject.toml`
- [ ] Update Dockerfile with ODBC driver
- [ ] Test locally with Azure SQL connection
- [ ] Commit and push
- [ ] Verify deployment via GitHub Actions

### Phase 7: Testing & Validation (20 minutes)

- [ ] Test API endpoint with real query
- [ ] Verify database queries work
- [ ] Check Watchtower logs for auto-update
- [ ] Test deployment: Make trivial code change and push
- [ ] Verify new version deployed within 5 minutes
- [ ] Check Docker logs for errors

### Phase 8: Documentation (10 minutes)

- [ ] Document server IP and credentials (secure location)
- [ ] Create runbook for common operations
- [ ] Set up backup cron job
- [ ] Add team members to GitHub repository (if applicable)

**Total setup time: ~2 hours**

## Future Scaling Path

### When to Add Second Machine

**Indicators:**
- Consistent downtime concerns (need redundancy)
- Traffic exceeds single machine capacity
- Want zero-downtime deployments

**Migration path:**
1. Set up second machine with same Docker Compose stack
2. Add keepalived for virtual IP failover
3. Use DNS round-robin or external load balancer (Cloudflare, etc.)
4. Continue using Watchtower for auto-deployment to both

### When to Move to Kubernetes

**Indicators:**
- 5+ machines needed
- Need auto-scaling based on metrics
- Complex deployment patterns (canary, blue-green)
- Multiple applications/services to manage

**Migration path:**
1. Your Docker Compose experience translates well
2. Convert `docker-compose.yml` → Kubernetes manifests (automated tools exist)
3. Use managed k8s (EKS/AKS/GKE) to avoid bare-metal complexity
4. Keep Azure SQL (no migration needed)

### When to Use Managed Services

**Indicators:**
- No longer want to manage servers
- Need global CDN and edge functions
- Budget allows $50-100/month

**Options:**
- Render (Docker → managed hosting)
- Railway (git push → deployed)
- Fly.io (edge deployment)
- Google Cloud Run (serverless containers)

**Migration:** Your containerized app works on all these platforms with minimal changes.

## Comparison: Docker Compose vs Kubernetes

| Feature | Docker Compose (This Design) | Kubernetes (Previous Design) |
|---------|------------------------------|------------------------------|
| Setup time | 2 hours | 1-2 days |
| Initial complexity | Low | High |
| Deployment | Automatic (Watchtower) | Manual (kubectl) |
| Debugging | `docker logs` | `kubectl describe/events/logs` |
| Image size | 350MB | 2.5GB (with SQLite) or 350MB |
| Build time | 30 sec | 30 sec (code), 3-5 min (DB update) |
| Deploy time | 5 min (auto) | 2-3 min (manual) |
| DB updates | Direct import (3 min) | Rebuild image (5 min) |
| Secrets | GitHub Secrets → .env | External Secrets Operator + Azure Key Vault |
| Monitoring | Docker logs, optional Prometheus | Prometheus + Grafana on Raspberry Pi |
| Scaling | Manual (add machines) | Automatic (replicas) |
| Cloud migration | Manual reconfiguration | Overlays + manifests |
| Monthly cost | $7-10 | $10-15 (electricity + Azure) |
| Operational burden | Low | Medium-high |
| Learning value | Docker fundamentals | Kubernetes ecosystem |
| Best for | Development velocity | Production at scale |

## Conclusion

This Docker Compose design optimizes for your stated priority: **maximum development velocity for agent iteration**.

**What you gain:**
- Push code → deployed in 5 minutes, zero manual steps
- Simple debugging (Docker logs, not Kubernetes troubleshooting)
- Fast builds (350MB image, not 2.5GB)
- Database updates without deployments
- Low operational burden (set up once, forget)

**What you trade:**
- No automatic scaling (not needed for your workload)
- Single point of failure (acceptable for development)
- Manual cloud migration later (if you scale to 5+ machines)

**Next steps:**
1. Follow implementation checklist (2 hours)
2. Test deployment workflow with trivial change
3. Focus on building your agent

You can always migrate to Kubernetes later if needed - Docker Compose is excellent preparation for that transition.

---

**Ready to implement? The complete setup takes ~2 hours and requires no Kubernetes knowledge.**
