# OEWS Server Setup Guide

Complete guide to deploying the OEWS Data Agent on a Linux server from scratch.

## Prerequisites

- Linux server (Ubuntu/Debian recommended)
- Home router with admin access (if server is behind NAT)
- Domain name (e.g., bhavanaai.com)
- GitHub account with repository access

## Part 1: Initial Server Setup

### 1. Install Docker

```bash
# Update package index
sudo apt update

# Install required packages
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Add Docker GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add your user to docker group (avoid sudo for docker commands)
sudo usermod -aG docker $USER

# Verify installation
docker --version
docker compose version
```

Log out and back in for group changes to take effect.

### 2. Install Tailscale

Tailscale provides secure remote access to your server.

```bash
# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Start Tailscale
sudo tailscale up

# Verify status
tailscale status
```

Follow the authentication link to connect your server to your Tailscale network.

### 3. Configure Tailscale for Management

Set your user as Tailscale operator to avoid sudo:

```bash
sudo tailscale set --operator=$USER
```

## Part 2: Network Configuration

### Configure Router Port Forwarding

Access your router admin panel (typically http://192.168.1.1 or http://192.168.0.1).

**Add these port forwarding rules:**

| Service Type | Internal IP | Internal Port | External Port | Protocol |
|-------------|-------------|---------------|---------------|----------|
| Custom      | [Server IP] | 80            | 80            | TCP      |
| Custom      | [Server IP] | 443           | 443           | TCP      |

Replace `[Server IP]` with your server's local IP address (find with `ip addr`).

**Note:** Some routers require the range format (80-80, 443-443).

### Configure DNS

At your DNS provider (e.g., Porkbun):

**Add A record:**
- Host: `api.oews` (or your subdomain)
- Type: `A`
- Answer: [Your public IP - find with `curl ifconfig.me`]
- TTL: `600` (10 minutes)

Verify DNS propagation:
```bash
dig api.oews.bhavanaai.com
```

## Part 3: Application Deployment

### 1. Create Deployment Directory

```bash
sudo mkdir -p /opt/oews/data
sudo chown -R $USER:$USER /opt/oews
cd /opt/oews
```

### 2. Copy Deployment Files

From your local machine, copy these files to the server:

```bash
# Using scp via Tailscale (replace SERVER_TAILSCALE_IP)
scp docker-compose.yml varun@[SERVER_TAILSCALE_IP]:/opt/oews/
scp Caddyfile varun@[SERVER_TAILSCALE_IP]:/opt/oews/

# Copy database
scp data/oews.db varun@[SERVER_TAILSCALE_IP]:/opt/oews/data/
```

**Or copy from existing location on server:**
```bash
# If database exists elsewhere on server
cp ~/projects/oews/data/oews.db /opt/oews/data/
```

### 3. Create Environment File

Create `/opt/oews/.env`:

```bash
cat > /opt/oews/.env << 'EOF'
AZURE_INFERENCE_ENDPOINT=https://your-endpoint.services.ai.azure.com/models
AZURE_INFERENCE_CREDENTIAL=your-credential-here
TAVILY_API_KEY=your-tavily-key-here
CORS_ORIGINS=https://app.bhavanaai.com,http://localhost:3000,https://microsoftedge-spark.github.io,https://*.github.io
DATABASE_ENV=dev
SQLITE_DB_PATH=/app/data/oews.db
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false
EOF

chmod 600 /opt/oews/.env
```

Replace placeholder values with your actual credentials.

### 4. Verify File Structure

Your `/opt/oews` directory should contain:

```
/opt/oews/
├── docker-compose.yml
├── Caddyfile
├── .env
└── data/
    └── oews.db
```

### 5. Start Services

```bash
cd /opt/oews

# Pull Docker images
docker compose pull

# Start containers
docker compose up -d

# Verify containers are running
docker compose ps
```

Expected output:
```
NAME       IMAGE                          COMMAND                  SERVICE    CREATED          STATUS
caddy      caddy:2-alpine                 "caddy run --config …"   caddy      X seconds ago    Up X seconds   0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
oews-api   ghcr.io/varunr89/oews:latest   "python -m src.main"     oews-api   X seconds ago    Up X seconds (healthy)
```

### 6. Monitor Logs

```bash
# View all logs
docker compose logs -f

# View API logs only
docker compose logs -f oews-api

# View Caddy logs only
docker compose logs -f caddy
```

### 7. Verify SSL Certificate

Caddy automatically obtains Let's Encrypt certificates. Check logs:

```bash
docker compose logs caddy | grep -i certificate
```

Look for: `"certificate obtained successfully"`

## Part 4: Verification

### Test API Health

```bash
# From any machine
curl https://api.oews.bhavanaai.com/health
```

Expected response:
```json
{"status":"healthy","workflow_loaded":true}
```

### Test Query Endpoint

```bash
curl -X POST https://api.oews.bhavanaai.com/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the median software engineer salary?"}'
```

## Part 5: GitHub Actions Setup (Optional)

For automated deployments, configure GitHub Secrets.

### Install GitHub CLI

```bash
# On your local machine (macOS)
brew install gh

# Authenticate
gh auth login --web
```

### Add Repository Secrets

```bash
# Navigate to your project
cd ~/projects/oews

# Add secrets
gh secret set SERVER_HOST --body "67.168.88.187"
gh secret set SERVER_USER --body "varun"
gh secret set SSH_PRIVATE_KEY < ~/.ssh/github_actions
gh secret set SSH_HOST_FINGERPRINT --body "$(ssh-keyscan -t ed25519 67.168.88.187)"
gh secret set AZURE_INFERENCE_ENDPOINT --body "your-endpoint"
gh secret set AZURE_INFERENCE_CREDENTIAL --body "your-credential"
gh secret set TAVILY_API_KEY --body "your-key"
gh secret set CORS_ORIGINS --body "https://app.bhavanaai.com,http://localhost:3000,https://microsoftedge-spark.github.io,https://*.github.io"
```

**Note:** GitHub Actions deployment requires SSH access on port 22. Either:
1. Add port 22 to router port forwarding (less secure)
2. Use Tailscale GitHub Actions (recommended but more complex)
3. Deploy manually via Tailscale SSH (current approach)

## Part 6: Maintenance

### Update Application

```bash
cd /opt/oews

# Pull latest images
docker compose pull

# Restart with new images
docker compose up -d

# Verify health
curl https://api.oews.bhavanaai.com/health
```

### View Container Status

```bash
docker compose ps
```

### Restart Services

```bash
# Restart all services
docker compose restart

# Restart specific service
docker compose restart oews-api
docker compose restart caddy
```

### Stop Services

```bash
docker compose down
```

### Backup Database

```bash
# Create backup
cp /opt/oews/data/oews.db /opt/oews/data/oews.db.backup.$(date +%Y%m%d)

# Or copy to safe location
scp /opt/oews/data/oews.db user@backup-server:/backups/
```

## Troubleshooting

### Certificate Acquisition Fails

**Symptom:** Caddy logs show "Timeout during connect (likely firewall problem)"

**Solutions:**
1. Verify port 80 is accessible: `curl -v http://api.oews.bhavanaai.com`
2. Check router port forwarding rules
3. Verify DNS resolves correctly: `dig api.oews.bhavanaai.com`
4. Wait 5-10 minutes for DNS propagation
5. Restart Caddy: `docker compose restart caddy`

### API Not Responding

```bash
# Check container status
docker compose ps

# View API logs
docker compose logs oews-api

# Verify health check
docker exec oews-api curl -f http://localhost:8000/health
```

### Port Already in Use

```bash
# Find what's using port 80 or 443
sudo ss -tulpn | grep -E ':(80|443) '

# Stop conflicting service
sudo systemctl stop apache2  # or nginx, etc.
```

### Database Permission Issues

```bash
# Fix ownership
sudo chown -R 1000:1000 /opt/oews/data

# Fix permissions
chmod 644 /opt/oews/data/oews.db
```

## Security Considerations

1. **Environment File:** Keep `.env` secure with `chmod 600`
2. **Firewall:** Only expose ports 80 and 443 externally
3. **SSH Access:** Use Tailscale for remote access, avoid exposing port 22
4. **Updates:** Regularly update Docker images and system packages
5. **Backups:** Schedule regular database backups
6. **Monitoring:** Set up uptime monitoring for your API endpoint

## Architecture Overview

```
Internet
    ↓
Router (Port Forward 80, 443)
    ↓
Linux Server (192.168.x.x)
    ↓
Docker Compose
    ├── Caddy (Port 80, 443)
    │   ├── Automatic HTTPS/TLS
    │   ├── Reverse Proxy
    │   └── Security Headers
    └── OEWS API (Port 8000)
        ├── FastAPI Application
        ├── Azure OpenAI Integration
        ├── Tavily Search
        └── SQLite Database
```

## Quick Reference

| Task | Command |
|------|---------|
| Start services | `cd /opt/oews && docker compose up -d` |
| Stop services | `cd /opt/oews && docker compose down` |
| View logs | `docker compose logs -f` |
| Restart service | `docker compose restart oews-api` |
| Check health | `curl https://api.oews.bhavanaai.com/health` |
| Update deployment | `docker compose pull && docker compose up -d` |
| Backup database | `cp /opt/oews/data/oews.db /opt/oews/data/oews.db.backup.$(date +%Y%m%d)` |

## Support

For issues or questions:
- Check logs: `docker compose logs`
- Review GitHub Actions: `gh run list`
- Verify DNS: `dig api.oews.bhavanaai.com`
- Test connectivity: `curl -v https://api.oews.bhavanaai.com/health`
