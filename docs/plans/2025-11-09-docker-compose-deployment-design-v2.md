# OEWS API Deployment Design - Docker Compose for High Development Velocity (v2 - Revised)

**Date:** 2025-11-09
**Status:** Design Complete - Revised after Codex review
**Goal:** Deploy OEWS FastAPI application with maximum development velocity - minimal infrastructure complexity, fast iterations on agent development

**Revision Notes:**
- Simplified database strategy: SQLite on volume (not Azure SQL) for faster setup
- Direct deployment via GitHub Actions (not Watchtower polling) for deterministic deploys
- Fixed critical bugs identified in code review
- Deferred Azure SQL migration to Phase 2 (when actually needed)

## Design Priorities

1. **Development velocity first** - Spend time building the agent, not managing infrastructure
2. **Simple deployment** - Push code, deployed in 2-3 minutes, deterministic
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
SQLite Database (bind-mounted volume, read-only)
```

**Key Design Decisions:**

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Orchestration | Docker Compose | Simple, fast setup, adequate for single machine |
| Reverse Proxy | Caddy | Zero-config HTTPS with Let's Encrypt |
| Database | SQLite on volume | Zero migration, fast local access, simple updates |
| Secrets | GitHub Secrets → .env (atomic) | Secure, version controlled, auto-deployed |
| Deployments | GitHub Actions (direct SSH) | Push to main → deployed in 2-3 min (deterministic) |
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
- Deploy: 2-3 min (deterministic) vs manual `kubectl set image`

**Trade-offs accepted:**
- Single point of failure (one machine) - acceptable for development
- Manual cloud migration later (if needed)
- No auto-scaling (not needed for your workload)

### Why SQLite on Volume (Not Azure SQL)?

**Deferred Azure SQL to Phase 2 because:**
- **Zero migration effort** - Use existing SQLite database as-is
- **Simple local development** - Same database locally and in production
- **No driver complexity** - Avoid ODBC/pyodbc installation issues
- **Fast setup** - No Azure provisioning, firewall rules, connection strings
- **Solves image size problem** - Docker image: 300MB (not 2.5GB)

**When to migrate to Azure SQL:**
- Need multi-writer capabilities (concurrent updates)
- SQLite performance becomes bottleneck (unlikely for read-heavy workload)
- Adding second machine (need shared database)

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
├── .env                    # Written by GitHub Actions (atomic)
├── Caddyfile
├── docker-config.json      # GHCR credentials for Watchtower
├── data/
│   └── oews.db            # 2.2GB SQLite database (bind-mounted)
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
    # No port mapping needed - Caddy uses Docker network
    env_file:
      - .env
    volumes:
      - ./data/oews.db:/app/data/oews.db:ro  # Read-only bind mount
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 10s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

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
      oews-api:
        condition: service_healthy  # Wait for API to be healthy
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  watchtower:
    image: containrrr/watchtower
    container_name: watchtower
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./docker-config.json:/config.json:ro  # GHCR credentials
    command: --interval 86400 --cleanup  # Daily, for base image updates only
    environment:
      - WATCHTOWER_NOTIFICATIONS=${WATCHTOWER_URL}
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  caddy_data:
  caddy_config:
```

**Key changes from original:**
- **No port mapping** for `oews-api` (Caddy uses Docker network)
- **Bind-mount database** (not baked into image)
- **Health-based depends_on** (Caddy waits for API)
- **Log rotation** configured for all services
- **Watchtower interval: 86400s (daily)** - only for base image CVE updates, not primary deployment
- **Fixed docker-config path** (not `~/.docker/config.json`)

### 3. Caddy Configuration

**Caddyfile:**

```
api.yourdomain.com {
    reverse_proxy oews-api:8000

    # Automatic HTTPS with Let's Encrypt
    # Recommended: Add email for renewal notifications
    tls your-email@domain.com

    # Security headers
    header {
        X-Frame-Options "DENY"
        X-Content-Type-Options "nosniff"
        Strict-Transport-Security "max-age=31536000;"
    }

    # Simple access log
    log {
        output file /data/access.log
        format json
    }
}
```

**Changes from original:**
- **Removed `rate_limit` directive** (requires plugin not in default Caddy image)
- **Added `tls` email** for Let's Encrypt renewal notifications
- **Added logging** for debugging

**Features:**
- Automatic HTTPS certificate from Let's Encrypt
- Auto-renewal every 60 days
- HTTP → HTTPS redirect
- Security headers

### 4. Database Strategy

**SQLite on bind-mounted volume:**

```yaml
volumes:
  - ./data/oews.db:/app/data/oews.db:ro  # Read-only
```

**Benefits:**
- Docker image: 300MB (not 2.5GB)
- Build time: 30 seconds (always fast)
- Zero migration from current setup
- Simple quarterly updates

**Quarterly update workflow:**

```bash
# From your Mac
scp data/oews.db server:/opt/oews/data/oews.db

# Restart API to pick up new data
ssh server 'cd /opt/oews && docker compose restart oews-api'
```

**Why read-only:**
- Prevents accidental writes from application bugs
- Safe for concurrent access if you add second machine later
- Matches your use case (data changes quarterly, not at runtime)

### 5. Secrets Management

**Strategy: GitHub Secrets → .env file (atomic writes)**

**GitHub Secrets (repository settings):**
- `SERVER_HOST` - Server IP or hostname
- `SERVER_USER` - SSH username
- `SSH_PRIVATE_KEY` - Private key for GitHub Actions
- `AZURE_AI_API_KEY` - Azure AI API key
- `OPENAI_API_KEY` - OpenAI API key
- `WATCHTOWER_URL` - Optional notification URL

**Deployment flow (atomic):**
1. GitHub Actions builds image
2. GitHub Actions SSH to server
3. Writes `.env.tmp` with secrets
4. Atomic `mv .env.tmp .env`
5. Pulls new image and restarts containers

**Security:**
- Secrets never committed to git
- Secrets never baked into Docker image layers
- `.env` file permissions: 600 (owner read/write only)
- Atomic writes prevent partial reads during restart
- Rotation: Update in GitHub → next deployment picks up new value

### 6. Dockerfile

**Optimized for fast builds (no database):**

```dockerfile
FROM python:3.12-slim

# Install curl for health checks
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && \
    uv pip install --system -e .

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

**Key changes:**
- **Use `python:3.12-slim`** (not 3.14-slim, which doesn't exist)
- **No ODBC drivers** (not needed for SQLite)
- **Install curl** for health checks
- **No database copy** (mounted as volume)

**Image size:**
- Before (SQLite in image): 2.5GB
- After (SQLite on volume): 300MB

**Build time:**
- Code change: 30 seconds (always)
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

      - name: Deploy to server
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/oews

            # Write .env file atomically
            cat > .env.tmp << 'EOF'
            AZURE_AI_API_KEY=${{ secrets.AZURE_AI_API_KEY }}
            OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }}
            DATABASE_ENV=prod
            SQLITE_DB_PATH=/app/data/oews.db
            API_HOST=0.0.0.0
            API_PORT=8000
            API_RELOAD=false
            EOF

            # Set secure permissions and move atomically
            chmod 600 .env.tmp
            mv .env.tmp .env

            # Pull new image and restart
            docker compose pull oews-api
            docker compose up -d oews-api

            echo "✓ Deployment complete"
```

**Key improvements:**
- **Atomic `.env` write** (temp file + mv)
- **Direct deployment** via SSH (no Watchtower delay)
- **Deterministic timing** (2-3 minutes total)
- **Explicit restart** of only changed service

### Daily Development Workflow

**Your iteration cycle (2-3 minutes total):**

```bash
# 1. Make changes to agent code
vim src/agents/planner.py

# 2. Commit and push
git add .
git commit -m "Improve planner reasoning"
git push origin main

# 3. Wait 2-3 minutes (deterministic)
# GitHub Actions: Build (30s) + Push (30s) + Deploy (60s)

# 4. Test immediately
curl -X POST https://api.yourdomain.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are software developer salaries in Seattle?"}'
```

**No SSH, no kubectl, no manual deployment steps. Deterministic 2-3 minute deploys.**

### Database Updates (Quarterly)

**Workflow:**
```bash
# 1. Download new BLS data on your Mac
python scripts/download_bls_data.py

# 2. Copy to server
scp data/oews.db server:/opt/oews/data/oews.db

# 3. Restart API to pick up new data
ssh server 'cd /opt/oews && docker compose restart oews-api'

# Done - takes 2-3 minutes
```

**No image rebuild, no deployment pipeline, just copy and restart.**

## Application Code Fixes

### Fix CORS Wildcard

**Current issue in `src/api/endpoints.py:65`:**
```python
allow_origins=["*"]  # Allows any origin!
```

**Fix:**
```python
# Get frontend origins from environment
frontend_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,  # Specific origins only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

**Add to `.env` via GitHub Secrets:**
```bash
CORS_ORIGINS=https://your-frontend.vercel.app,https://yourdomain.com
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
```

Get notified when base images are updated.

### Optional: Prometheus + Grafana

Add later only if needed. Start with Docker logs.

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
- API container: Only accessible via Caddy (no exposed port)
- No direct internet access to API
- All traffic flows through HTTPS

### Secrets Security

- Secrets stored in GitHub (encrypted at rest)
- `.env` file permissions: 600 (owner only)
- Atomic writes prevent partial reads
- Secrets never in git history
- Secrets never in Docker image layers
- SSH key for GitHub Actions (rotate periodically)

### Application Security

**Current (from your code):**
- Non-root container user ✅
- Parameterized SQL queries ✅
- Read-only database access ✅

**To fix:**
- CORS restricted to frontend domains (fix wildcard)
- Security headers (already in Caddy)
- HTTPS-only (already enforced)
- Health check endpoint (public, no sensitive data)

## Disaster Recovery

### Backup Strategy

**What needs backup:**
1. Docker Compose files (in git) ✅
2. Caddy certificates (in Docker volume `caddy_data`)
3. SQLite database (`/opt/oews/data/oews.db`)
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

# Backup database
cp /opt/oews/data/oews.db $BACKUP_DIR/oews-$DATE.db

# Backup .env
cp /opt/oews/.env $BACKUP_DIR/env-$DATE

# Keep last 7 backups
find $BACKUP_DIR -name "caddy-*.tar.gz" -mtime +7 -delete
find $BACKUP_DIR -name "oews-*.db" -mtime +7 -delete
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
- Docker Compose auto-starts on boot
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

# 3. Restore database
scp backup-server:/backup/oews-latest.db /opt/oews/data/oews.db

# 4. Restore Caddy certificates (optional, will regenerate)
tar xzf /backup/caddy-latest.tar.gz -C /

# 5. Update DNS
# Point api.yourdomain.com → new server IP

# 6. Deploy
# GitHub Actions will deploy on next push
git commit --allow-empty -m "Trigger deployment"
git push

# Or manually start:
docker compose up -d
```

**RTO/RPO:**
- Recovery Time Objective: 1 hour
- Recovery Point Objective: Last deployment (code) + last DB backup (quarterly data)

## Cost Summary

| Component | Provider | Monthly Cost |
|-----------|----------|--------------|
| Server electricity | Self-hosted | ~$5 |
| Azure AI API | Azure | Variable (existing) |
| Domain name | Registrar | ~$1 |
| GitHub Actions | GitHub | $0 (free tier) |
| GitHub Container Registry | GitHub | $0 (free tier) |
| Caddy | Self-hosted | $0 |
| SQLite | Self-hosted | $0 |
| **Total** | | **$6/month** |

**Compared to original design:**
- Original (with Azure SQL): $7-10/month
- Revised (SQLite on volume): $6/month
- Saved: $1-4/month + eliminated migration complexity

## Implementation Checklist

### Phase 1: Server Setup (20 minutes)

- [ ] Install Docker on Linux machine
- [ ] Create `/opt/oews` directory
- [ ] Create `/opt/oews/data` directory
- [ ] Configure firewall (UFW)
- [ ] Generate SSH key for GitHub Actions
- [ ] Add SSH public key to server `~/.ssh/authorized_keys`
- [ ] Test SSH access from local machine

### Phase 2: GitHub Configuration (15 minutes)

- [ ] Add SSH private key to GitHub Secrets
- [ ] Add server host/user to GitHub Secrets
- [ ] Add API keys to GitHub Secrets
- [ ] Add CORS origins to GitHub Secrets
- [ ] Create `.github/workflows/deploy.yml`

### Phase 3: Server Files (15 minutes)

- [ ] Copy `docker-compose.yml` to `/opt/oews/`
- [ ] Copy `Caddyfile` to `/opt/oews/`
- [ ] Copy `data/oews.db` to `/opt/oews/data/`
- [ ] Login to GitHub Container Registry: `docker login ghcr.io`
- [ ] Save Docker credentials: `cp ~/.docker/config.json /opt/oews/docker-config.json`

### Phase 4: DNS & SSL (10 minutes)

- [ ] Point `api.yourdomain.com` to server public IP
- [ ] Wait for DNS propagation (5-10 minutes)

### Phase 5: First Deployment (10 minutes)

- [ ] Fix CORS wildcard in `src/api/endpoints.py`
- [ ] Commit and push to trigger deployment
- [ ] Monitor GitHub Actions workflow
- [ ] Test: `curl https://api.yourdomain.com/health`
- [ ] Verify SSL certificate (browser shows padlock)

### Phase 6: Testing & Validation (10 minutes)

- [ ] Test API endpoint with real query
- [ ] Verify database queries work
- [ ] Check Docker logs for errors
- [ ] Test deployment: Make trivial code change and push
- [ ] Verify new version deployed within 2-3 minutes

### Phase 7: Backup Setup (10 minutes)

- [ ] Create backup script at `/opt/oews/backup.sh`
- [ ] Make executable: `chmod +x backup.sh`
- [ ] Add to cron: `crontab -e`
- [ ] Test backup script manually

**Total setup time: ~1.5 hours**

## Future Scaling Path

### Phase 2: Migrate to Azure SQL (When Needed)

**Migrate when:**
- Need multi-writer capabilities
- SQLite performance becomes bottleneck
- Adding second machine (need shared database)

**Migration steps:**
1. Create Azure SQL Serverless database
2. Run migration script: `scripts/migrate_sqlite_to_azure_sql.py`
3. Update `src/database/connection.py` for Azure SQL
4. Add `pyodbc` to dependencies
5. Update Dockerfile with ODBC drivers
6. Deploy

**Time: 2-3 hours**

### When to Add Second Machine

**Indicators:**
- Consistent downtime concerns (need redundancy)
- Traffic exceeds single machine capacity
- Want zero-downtime deployments

**Migration path:**
1. Migrate to Azure SQL (shared database)
2. Set up second machine with same Docker Compose stack
3. Use DNS round-robin or external load balancer (Cloudflare)
4. Continue using GitHub Actions for deployment to both

### When to Move to Kubernetes

**Indicators:**
- 5+ machines needed
- Need auto-scaling based on metrics
- Complex deployment patterns (canary, blue-green)

**Migration path:**
1. Your Docker Compose experience translates well
2. Convert `docker-compose.yml` → Kubernetes manifests
3. Use managed k8s (EKS/AKS/GKE)
4. Keep database (Azure SQL or managed Postgres)

## Comparison: Revised vs Original Design

| Feature | Revised (v2) | Original (v1) |
|---------|--------------|---------------|
| Database | SQLite on volume | Azure SQL Serverless |
| Image size | 300MB | 350MB |
| Build time | 30 sec (always) | 30 sec (code), 3-5 min (DB) |
| Deploy time | 2-3 min (deterministic) | 5-10 min (Watchtower polling) |
| DB updates | scp + restart (2 min) | SQL import (3 min) |
| Setup time | 1.5 hours | 2 hours |
| Migration effort | Zero | SQLite → SQL Server |
| Monthly cost | $6 | $7-10 |
| Operational complexity | Low | Low-Medium |
| ODBC drivers | Not needed | Required (fragile) |
| Local dev | Same as prod | Different driver/DB |

## Conclusion

This revised Docker Compose design optimizes for your stated priority: **maximum development velocity for agent iteration**.

**What you gain vs original:**
- **Faster setup:** 1.5 hours vs 2 hours
- **Simpler:** No Azure SQL migration, no ODBC drivers
- **Deterministic deploys:** 2-3 minutes vs 0-10 minutes
- **Cheaper:** $6/month vs $7-10/month
- **Same local & prod:** SQLite everywhere, no driver switching

**What you gain vs Kubernetes:**
- Setup: 1.5 hours vs 2 days
- Debugging: `docker logs` vs `kubectl describe/events/logs`
- Complexity: Docker fundamentals vs Kubernetes ecosystem

**What you still trade:**
- Single point of failure (acceptable for development)
- Manual cloud migration later (if you scale to 5+ machines)
- No auto-scaling (not needed for your workload)

**Critical fixes from Codex review:**
- ✅ Atomic `.env` writes (prevent race conditions)
- ✅ Direct deployment (deterministic timing)
- ✅ Removed Caddy `rate_limit` (requires plugin)
- ✅ Fixed CORS wildcard (security issue)
- ✅ Log rotation configured (prevent disk fill)
- ✅ Health-based startup ordering

**Next steps:**
1. Follow implementation checklist (1.5 hours)
2. Test deployment workflow with trivial change
3. Focus on building your agent
4. Migrate to Azure SQL in Phase 2 (only if/when needed)

---

**Ready to implement? The complete setup takes ~1.5 hours and requires no Kubernetes knowledge.**
