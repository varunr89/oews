# Docker Compose Deployment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deploy OEWS FastAPI application on single Linux machine with 1.5 hour setup time and 2-3 minute deterministic deployments

**Architecture:** Docker Compose single-machine deployment with Caddy reverse proxy, SQLite on bind-mounted volume, GitHub Actions direct SSH deployment, and atomic secrets management

**Tech Stack:** Docker Compose, Caddy 2, GitHub Actions, SQLite, FastAPI, SSH deployment

---

## Code Review Checkpoints

**IMPORTANT:** Use the `phone-a-friend` skill to get Codex review at these major milestones:

1. **After Task 5 (GitHub Actions Workflow)** - Review security of deployment pipeline, SSH configuration, and secrets handling
2. **After Task 9 (Backup Script)** - Review backup safety, database handling, and disaster recovery approach
3. **After Task 12 (End-to-End Validation)** - Final review of complete deployment before marking as production-ready

Use the phone-a-friend skill like this:
```
I've completed [milestone]. Please use phone-a-friend to get Codex's review of the implementation.
```

---

## Task 1: Fix CORS Wildcard Security Issue

**Files:**
- Modify: `src/api/endpoints.py:57-70`

**Step 1: Read current CORS configuration**

Run: `cat src/api/endpoints.py | grep -A 15 "add_middleware"`

Expected: See `allow_origins=["*"]` wildcard

**Step 2: Replace CORS wildcard with environment-based origins**

Edit `src/api/endpoints.py:57-70`:

```python
# Add CORS middleware
# Get frontend origins from environment (comma-separated)
frontend_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,  # Specific origins only (not wildcard)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

**Step 3: Verify syntax**

Run: `python -m py_compile src/api/endpoints.py`

Expected: No syntax errors

**Step 4: Test locally with restricted CORS**

```bash
export CORS_ORIGINS="http://localhost:3000"
python -m src.main &
sleep 2
curl -H "Origin: http://localhost:3000" http://localhost:8000/health
```

Expected: Returns `{"status":"healthy","workflow_loaded":true}` with CORS headers

**Step 5: Commit CORS fix**

```bash
git add src/api/endpoints.py
git commit -m "fix(cors): restrict origins from wildcard to environment-based list"
```

Expected: Commit created

---

## Task 2: Create Dockerfile

**Files:**
- Create: `Dockerfile`

**Step 1: Write Dockerfile**

Create `Dockerfile`:

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

# Copy application code (NO DATABASE - mounted as volume)
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

**Step 2: Build image locally**

Run: `docker build -t oews-api:test .`

Expected: Build completes, image size ~300MB

**Step 3: Test image locally**

```bash
docker run -d --name oews-test \
  -e AZURE_AI_API_KEY="${AZURE_AI_API_KEY}" \
  -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
  -e DATABASE_ENV=dev \
  -e SQLITE_DB_PATH=/app/data/oews.db \
  -v $(pwd)/data/oews.db:/app/data/oews.db:ro \
  -p 8000:8000 \
  oews-api:test
```

Expected: Container starts, health check passes

**Step 4: Verify health endpoint**

Run: `curl http://localhost:8000/health`

Expected: `{"status":"healthy","workflow_loaded":true}`

**Step 5: Clean up test container**

Run: `docker stop oews-test && docker rm oews-test`

**Step 6: Commit Dockerfile**

```bash
git add Dockerfile
git commit -m "feat(docker): add optimized Dockerfile with SQLite on volume"
```

Expected: Commit created

---

## Task 3: Create Docker Compose Configuration

**Files:**
- Create: `docker-compose.yml`

**Step 1: Write docker-compose.yml**

Create `docker-compose.yml`:

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

**Step 2: Validate YAML syntax**

Run: `docker compose config`

Expected: Parsed configuration displayed with no errors

**Step 3: Commit docker-compose.yml**

```bash
git add docker-compose.yml
git commit -m "feat(docker): add Docker Compose configuration with Caddy and Watchtower"
```

Expected: Commit created

---

## Task 4: Create Caddyfile

**Files:**
- Create: `Caddyfile`

**Step 1: Write Caddyfile**

Create `Caddyfile`:

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

    # Access log to stdout (Docker log driver handles rotation)
    log {
        output stdout
        format json
    }
}
```

**Step 2: Validate Caddyfile syntax**

Run: `docker run --rm -v $(pwd)/Caddyfile:/etc/caddy/Caddyfile caddy:2-alpine caddy validate --config /etc/caddy/Caddyfile`

Expected: `Valid configuration`

**Step 3: Commit Caddyfile**

```bash
git add Caddyfile
git commit -m "feat(caddy): add Caddyfile with HTTPS and security headers"
```

Expected: Commit created

---

## Task 5: Create GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/deploy.yml`

**Step 1: Create workflows directory**

Run: `mkdir -p .github/workflows`

Expected: Directory created

**Step 2: Write deploy.yml**

Create `.github/workflows/deploy.yml`:

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
          fingerprint: ${{ secrets.SSH_HOST_FINGERPRINT }}
          script: |
            cd /opt/oews

            # Write .env file atomically
            cat > .env.tmp << 'EOF'
            AZURE_AI_API_KEY=${{ secrets.AZURE_AI_API_KEY }}
            OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }}
            CORS_ORIGINS=${{ secrets.CORS_ORIGINS }}
            DATABASE_ENV=prod
            SQLITE_DB_PATH=/app/data/oews.db
            API_HOST=0.0.0.0
            API_PORT=8000
            API_RELOAD=false
            EOF

            # Set secure permissions and move atomically
            chmod 600 .env.tmp
            mv .env.tmp .env

            # Pull new image and restart (restart all services to pick up config changes)
            docker compose pull
            docker compose up -d

            echo "✓ Deployment complete"
```

**Step 3: Validate workflow syntax**

Run: `cat .github/workflows/deploy.yml | python -c "import yaml, sys; yaml.safe_load(sys.stdin)"`

Expected: No errors (Python parses YAML successfully)

**Step 4: Commit GitHub Actions workflow**

```bash
git add .github/workflows/deploy.yml
git commit -m "feat(ci): add GitHub Actions workflow for build and deploy"
```

Expected: Commit created

---

## CHECKPOINT 1: Code Review - Deployment Pipeline Security

**Use phone-a-friend skill to review:**
- GitHub Actions workflow security
- SSH host key verification implementation
- Secrets handling (atomic .env writes)
- Docker registry authentication approach

**What to share with Codex:**
- `.github/workflows/deploy.yml`
- `scripts/setup-server.sh` (SSH key generation section)
- Summary of security measures implemented

**Expected outcome:** Validation that deployment pipeline is secure and follows best practices, or specific fixes to apply.

---

## Task 6: Create .dockerignore

**Files:**
- Create: `.dockerignore`

**Step 1: Write .dockerignore**

Create `.dockerignore`:

```
# Don't copy database into image (mounted as volume)
data/
*.db

# Development files
.git/
.github/
.venv/
venv/
__pycache__/
*.pyc
.pytest_cache/
.coverage
htmlcov/

# Environment files
.env
.env.*

# Documentation
docs/
*.md
!README.md

# IDE files
.vscode/
.idea/
*.swp
*.swo

# macOS files
.DS_Store

# Logs
*.log
logs/
```

**Step 2: Verify .dockerignore works**

Run: `docker build -t oews-test . 2>&1 | grep -E "(COPY|data)"`

Expected: No "data/" directory copied

**Step 3: Commit .dockerignore**

```bash
git add .dockerignore
git commit -m "feat(docker): add .dockerignore to exclude dev files and database"
```

Expected: Commit created

---

## Task 7: Update .gitignore

**Files:**
- Modify: `.gitignore`

**Step 1: Add deployment files to .gitignore**

Append to `.gitignore`:

```
# Deployment secrets
.env
.env.*
docker-config.json

# Caddy data (volumes)
caddy_data/
caddy_config/
```

**Step 2: Verify .env is ignored**

Run: `git status`

Expected: `.env` not shown if it exists

**Step 3: Commit .gitignore update**

```bash
git add .gitignore
git commit -m "chore(git): ignore deployment secrets and Caddy volumes"
```

Expected: Commit created

---

## Task 8: Create Server Setup Script

**Files:**
- Create: `scripts/setup-server.sh`

**Step 1: Create scripts directory**

Run: `mkdir -p scripts`

Expected: Directory created

**Step 2: Write setup-server.sh**

Create `scripts/setup-server.sh`:

```bash
#!/bin/bash
set -e

echo "=== OEWS Server Setup Script ==="
echo "This script sets up the deployment environment on your Linux server"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
   echo "ERROR: Don't run this script as root. Run as your regular user."
   exit 1
fi

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "→ Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "✓ Docker installed. You may need to log out and back in for group changes."
else
    echo "✓ Docker already installed"
fi

# Create deployment directory
echo "→ Creating deployment directory..."
sudo mkdir -p /opt/oews/data
sudo chown -R $USER:$USER /opt/oews
echo "✓ Created /opt/oews"

# Configure firewall
echo "→ Configuring firewall..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 22/tcp
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw --force enable
    echo "✓ Firewall configured (SSH, HTTP, HTTPS)"
else
    echo "⚠ UFW not found, skip firewall configuration"
fi

# Generate SSH key for GitHub Actions if not exists
if [ ! -f ~/.ssh/github_actions ]; then
    echo "→ Generating SSH key for GitHub Actions..."
    ssh-keygen -t ed25519 -f ~/.ssh/github_actions -N "" -C "github-actions-deploy"
    cat ~/.ssh/github_actions.pub >> ~/.ssh/authorized_keys
    chmod 600 ~/.ssh/authorized_keys
    echo "✓ SSH key generated"
    echo ""
    echo "=== IMPORTANT: Add private key to GitHub Secrets ==="
    echo "The private key is stored at: ~/.ssh/github_actions"
    echo "To view it (ONLY when ready to add to GitHub Secrets):"
    echo "  cat ~/.ssh/github_actions"
    echo ""
    echo "Add it to GitHub repository secrets as 'SSH_PRIVATE_KEY'"
    echo ""
else
    echo "✓ SSH key already exists"
fi

# Get server's SSH host key for GitHub Actions
echo "→ Getting server SSH host key for GitHub Actions..."
ssh-keyscan -H $(curl -s ifconfig.me) > /tmp/server_hostkey 2>/dev/null
SERVER_HOSTKEY=$(ssh-keygen -lf /tmp/server_hostkey | awk '{print $2}')
rm /tmp/server_hostkey
echo "✓ Server SSH host key fingerprint: $SERVER_HOSTKEY"

echo ""
echo "=== Next Steps ==="
echo "1. Add GitHub Secrets (in repository settings):"
echo "   - SERVER_HOST: $(curl -s ifconfig.me)"
echo "   - SERVER_USER: $USER"
echo "   - SSH_PRIVATE_KEY: Run 'cat ~/.ssh/github_actions' and paste"
echo "   - SSH_HOST_FINGERPRINT: $SERVER_HOSTKEY"
echo "   - AZURE_AI_API_KEY: <your key>"
echo "   - OPENAI_API_KEY: <your key>"
echo "   - CORS_ORIGINS: https://your-frontend.com"
echo "   - GHCR_PAT: Generate read-only PAT from GitHub settings"
echo ""
echo "2. Copy deployment files to server:"
echo "   scp docker-compose.yml Caddyfile $USER@$(curl -s ifconfig.me):/opt/oews/"
echo ""
echo "3. Copy database to server:"
echo "   scp data/oews.db $USER@$(curl -s ifconfig.me):/opt/oews/data/"
echo ""
echo "4. Copy backup script to server:"
echo "   scp scripts/backup.sh $USER@$(curl -s ifconfig.me):/opt/oews/scripts/"
echo "   ssh $USER@$(curl -s ifconfig.me) 'chmod +x /opt/oews/scripts/backup.sh'"
echo ""
echo "5. Create backup directory on server:"
echo "   ssh $USER@$(curl -s ifconfig.me) 'sudo mkdir -p /backup/oews && sudo chown $USER:$USER /backup/oews'"
echo ""
echo "6. Create GHCR credentials file on server (read-only PAT):"
echo "   ssh $USER@$(curl -s ifconfig.me)"
echo "   On server: echo '{\"auths\":{\"ghcr.io\":{\"auth\":\"BASE64_OF_USERNAME:PAT\"}}}' > /opt/oews/docker-config.json"
echo "   On server: chmod 600 /opt/oews/docker-config.json"
echo ""
echo "7. Initial container startup:"
echo "   ssh $USER@$(curl -s ifconfig.me) 'cd /opt/oews && docker compose up -d'"
echo ""
echo "8. Update DNS: Point api.yourdomain.com -> $(curl -s ifconfig.me)"
echo ""
echo "9. Push code to trigger first deployment"
echo ""
echo "✓ Server setup complete!"
```

**Step 3: Make script executable**

Run: `chmod +x scripts/setup-server.sh`

Expected: Script is executable

**Step 4: Commit setup script**

```bash
git add scripts/setup-server.sh
git commit -m "feat(deploy): add server setup script for initial deployment"
```

Expected: Commit created

---

## Task 9: Create Backup Script

**Files:**
- Create: `scripts/backup.sh`

**Step 1: Write backup.sh**

Create `scripts/backup.sh`:

```bash
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
```

**Step 2: Make script executable**

Run: `chmod +x scripts/backup.sh`

Expected: Script is executable

**Step 3: Commit backup script**

```bash
git add scripts/backup.sh
git commit -m "feat(ops): add daily backup script for Caddy certs and database"
```

Expected: Commit created

---

## CHECKPOINT 2: Code Review - Backup Safety & Disaster Recovery

**Use phone-a-friend skill to review:**
- Backup script safety (container stop/start approach)
- SQLite database backup while API is running (corruption risks)
- Disaster recovery completeness
- Backup retention and cleanup logic

**What to share with Codex:**
- `scripts/backup.sh`
- Summary of backup strategy (local `/backup/oews`, 7-day retention, no off-site yet)
- Database update workflow (quarterly `scp` + restart)

**Expected outcome:** Validation that backups are safe and won't corrupt SQLite, or recommendations for improvements (e.g., SQLite .backup command for zero-downtime).

---

## Task 10: Create Documentation

**Files:**
- Create: `docs/deployment/README.md`

**Step 1: Create deployment docs directory**

Run: `mkdir -p docs/deployment`

Expected: Directory created

**Step 2: Write deployment README**

Create `docs/deployment/README.md`:

```markdown
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
   - `AZURE_AI_API_KEY`: Your Azure AI API key
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `CORS_ORIGINS`: Frontend domains (comma-separated)
   - `WATCHTOWER_URL`: (Optional) Notification webhook

3. **Copy files to server:**
   ```bash
   scp docker-compose.yml Caddyfile user@server:/opt/oews/
   scp data/oews.db user@server:/opt/oews/data/
   ```

4. **Login to GHCR on server:**
   ```bash
   ssh user@server
   docker login ghcr.io
   cp ~/.docker/config.json /opt/oews/docker-config.json
   ```

5. **Update DNS:**
   - Point `api.yourdomain.com` → server IP
   - Wait 5-10 minutes for propagation

6. **Deploy:**
   ```bash
   git push origin main
   ```
   Deployment completes in 2-3 minutes.

7. **Verify:**
   ```bash
   curl https://api.yourdomain.com/health
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
curl -X POST https://api.yourdomain.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are software developer salaries in Seattle?"}'
```

### Quarterly Database Updates

```bash
# 1. Download new BLS data locally
python scripts/download_bls_data.py

# 2. Copy to server
scp data/oews.db user@server:/opt/oews/data/oews.db

# 3. Restart API
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
```

### Check Status

```bash
# Container status
ssh user@server 'docker ps'

# Health check
curl https://api.yourdomain.com/health
```

## Backup & Recovery

### Setup Automated Backups

```bash
# On server
crontab -e

# Add this line:
0 2 * * * /opt/oews/scripts/backup.sh
```

### Manual Backup

```bash
ssh user@server '/opt/oews/scripts/backup.sh'
```

### Disaster Recovery

See full recovery procedures in `docs/plans/2025-11-09-docker-compose-deployment-design-v2.md`

## Troubleshooting

### Deployment Failed

```bash
# Check GitHub Actions logs in repository → Actions tab

# Check server logs
ssh user@server 'docker logs oews-api'

# Restart manually
ssh user@server 'cd /opt/oews && docker compose restart'
```

### SSL Certificate Issues

```bash
# Check Caddy logs
ssh user@server 'docker logs caddy'

# Verify DNS points to server
dig api.yourdomain.com

# Force certificate renewal
ssh user@server 'docker compose restart caddy'
```

### Database Not Found

```bash
# Verify database file exists
ssh user@server 'ls -lh /opt/oews/data/oews.db'

# Check mount in container
ssh user@server 'docker exec oews-api ls -lh /app/data/oews.db'

# Restart container
ssh user@server 'docker compose restart oews-api'
```

## Architecture

See design document: `docs/plans/2025-11-09-docker-compose-deployment-design-v2.md`

## Cost

- Server electricity: ~$5/month
- Domain name: ~$1/month
- GitHub Actions: $0 (free tier)
- **Total: $6/month**
```

**Step 3: Commit deployment documentation**

```bash
git add docs/deployment/README.md
git commit -m "docs(deploy): add deployment guide and troubleshooting"
```

Expected: Commit created

---

## Task 11: Push All Changes to Trigger First Deployment

**Files:**
- None (Git operation)

**Step 1: Verify all commits are ready**

Run: `git log --oneline -10`

Expected: See all 10 commits from tasks above

**Step 2: Push to main branch**

Run: `git push origin main`

Expected: Push succeeds, GitHub Actions workflow triggered

**Step 3: Monitor GitHub Actions workflow**

Go to: `https://github.com/yourusername/oews/actions`

Expected: See "Build and Deploy" workflow running

**Step 4: Wait for deployment to complete**

Expected: Workflow completes in 2-3 minutes with green checkmark

**Step 5: Verify deployment succeeded**

Run: `curl https://api.yourdomain.com/health`

Expected: `{"status":"healthy","workflow_loaded":true}`

---

## Task 12: Validate End-to-End Functionality

**Files:**
- None (Testing)

**Step 1: Test health endpoint**

Run: `curl https://api.yourdomain.com/health`

Expected: `{"status":"healthy","workflow_loaded":true}`

**Step 2: Test HTTPS certificate**

Run: `curl -vI https://api.yourdomain.com/health 2>&1 | grep "SSL certificate"`

Expected: Valid certificate from Let's Encrypt

**Step 3: Test actual query endpoint**

```bash
curl -X POST https://api.yourdomain.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the top 5 highest paying occupations?", "enable_charts": true}'
```

Expected: JSON response with answer, charts, and metadata

**Step 4: Test CORS headers**

```bash
curl -H "Origin: https://your-frontend.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -X OPTIONS \
  https://api.yourdomain.com/api/v1/query
```

Expected: CORS headers present with allowed origin

**Step 5: Verify Docker logs are clean**

Run: `ssh user@server 'docker logs --tail 50 oews-api'`

Expected: No ERROR messages, see startup logs

**Step 6: Test deployment by making trivial change**

```bash
# Add comment to src/main.py
echo "# Deployment test" >> src/main.py
git add src/main.py
git commit -m "test: verify deployment pipeline"
git push origin main
```

Expected: GitHub Actions deploys new version in 2-3 minutes

**Step 7: Verify new version deployed**

Run: `ssh user@server 'docker ps --format "{{.Image}}" | grep oews'`

Expected: See new image hash (not same as before)

---

## CHECKPOINT 3: Final Code Review - Production Readiness

**Use phone-a-friend skill for final review:**
- Complete deployment architecture (Docker Compose, Caddy, Watchtower)
- End-to-end security posture
- Operational readiness (monitoring, backups, disaster recovery)
- Production deployment checklist completeness

**What to share with Codex:**
- All created files: `Dockerfile`, `docker-compose.yml`, `Caddyfile`, `.github/workflows/deploy.yml`, `scripts/setup-server.sh`, `scripts/backup.sh`
- Summary of validation results from Task 12
- List of any remaining known issues or deferred improvements

**Expected outcome:** Final validation that deployment is production-ready, or identification of critical issues that must be addressed before production use.

**Action after review:** Address any critical findings, then mark deployment as production-ready.

---

## Success Criteria

- [ ] All 12 tasks completed
- [ ] **CHECKPOINT 1 passed:** Deployment pipeline security validated by Codex
- [ ] CORS wildcard fixed (environment-based origins)
- [ ] Dockerfile builds successfully (~300MB)
- [ ] Docker Compose validated
- [ ] GitHub Actions workflow runs without errors
- [ ] **CHECKPOINT 2 passed:** Backup safety and disaster recovery validated by Codex
- [ ] HTTPS certificate obtained from Let's Encrypt
- [ ] Health endpoint returns 200 OK
- [ ] Query endpoint processes requests successfully
- [ ] Deployment completes in 2-3 minutes (deterministic)
- [ ] Logs show no errors
- [ ] Database queries work correctly
- [ ] Backup script runs successfully
- [ ] **CHECKPOINT 3 passed:** Complete deployment validated as production-ready by Codex

## Estimated Time

- Tasks 1-10: 1 hour (writing and committing files)
- Task 11: 3 minutes (push and deploy)
- Task 12: 15 minutes (validation and testing)

**Total: ~1.5 hours**

## Notes for Engineer

- Replace `yourusername` with your GitHub username in all files
- Replace `api.yourdomain.com` with your actual domain
- Replace `your-email@domain.com` with your email for Let's Encrypt
- Ensure you have `AZURE_AI_API_KEY` and `OPENAI_API_KEY` ready
- Server must have public IP or port forwarding configured
- DNS must be configured before SSL certificate can be obtained
- Generate a **read-only** GitHub Personal Access Token (PAT) for GHCR credentials
- If using @superpowers:verification-before-completion, verify health endpoint returns 200 before claiming success

### Important Security Notes

- **Watchtower**: Configured to poll daily for base image updates only. It has Docker socket access which is a security risk if compromised. Consider disabling it for production or using a read-only Docker socket proxy.
- **SSH Host Verification**: The deployment workflow verifies the SSH host fingerprint to prevent MITM attacks. Keep the `SSH_HOST_FINGERPRINT` secret updated if you recreate the server.
- **GHCR Credentials**: Use a read-only PAT with only `read:packages` scope. Never copy your full `~/.docker/config.json` which may contain tokens for multiple registries.

### Operational Maintenance

**Monthly tasks:**
- Review disk space: `ssh server 'df -h'`
- Clean up Docker resources: `ssh server 'docker system prune -a --volumes -f'`
- Rotate SSH keys for GitHub Actions (if compromised)
- Review backup integrity: `ssh server 'ls -lh /backup/oews'`

**Quarterly tasks:**
- Update database: Stop container, copy new `oews.db`, restart
- Review and update base images if Watchtower hasn't already
- Test disaster recovery procedure

## Related Skills

- @superpowers:verification-before-completion - Run verification commands before claiming work is complete
- @superpowers:test-driven-development - If adding new features to the deployment pipeline

## Troubleshooting

### GitHub Actions fails on SSH step

- Verify `SSH_PRIVATE_KEY` matches public key on server
- Check `SERVER_HOST` is reachable: `ping $SERVER_HOST`
- Verify `SERVER_USER` has permissions for `/opt/oews`

### Docker build fails

- Check `pyproject.toml` and `uv.lock` exist
- Verify Python 3.12 is available: `docker run python:3.12-slim python --version`
- Check `.dockerignore` isn't excluding required files

### SSL certificate not obtained

- Verify DNS propagation: `dig api.yourdomain.com`
- Check ports 80/443 are open: `nmap -p 80,443 $SERVER_IP`
- Check Caddy logs: `ssh user@server 'docker logs caddy'`

### Database mount fails

- Verify `/opt/oews/data/oews.db` exists on server
- Check file permissions: `ls -l /opt/oews/data/oews.db`
- Check Docker volume mount: `docker exec oews-api ls -l /app/data/oews.db`

### Disk space running low

- Check disk usage: `ssh server 'df -h'`
- Clean up Docker resources: `ssh server 'docker system prune -a --volumes -f'`
- Review log sizes: `ssh server 'docker ps -q | xargs docker inspect --format="{{.Name}} {{.HostConfig.LogConfig}}"'`
- Consider setting up off-site backups to cloud storage (S3, Azure Blob, etc.) to free up local space

### Backup failures

- Check if `/backup/oews` directory exists and is writable
- Verify container can be stopped: `ssh server 'cd /opt/oews && docker compose stop oews-api'`
- For production with zero-downtime requirements, use SQLite's `.backup` command instead of stopping the container
- **Important**: Current backups are on the same server. Set up off-site replication to cloud storage or another machine for true disaster recovery
