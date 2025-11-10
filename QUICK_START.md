# OEWS Quick Start Guide

## Local Testing (Already Done ✅)

```bash
# Activate virtual environment
source venv/bin/activate

# Run the API
python -m src.main

# Test in another terminal
curl http://localhost:8000/health
```

## Deploy to Production (Do This Next)

### Prerequisites
- Linux server with SSH access
- Domain: bhavanaai.com (configured at Porkbun)
- Azure Blob Storage account

### Quick Setup

1. **Run setup script on server:**
   ```bash
   ssh your-server
   git clone https://github.com/varunr89/oews.git
   cd oews
   ./scripts/setup-server.sh
   ```

2. **Add GitHub Secrets** from setup script output

3. **Copy files to server:**
   ```bash
   SERVER_IP="your-ip"
   scp docker-compose.yml Caddyfile data/oews.db scripts/backup.sh user@$SERVER_IP:/opt/oews/
   ```

4. **Configure DNS** at Porkbun:
   - Point `api.bhavanaai.com` → server IP

5. **Deploy:**
   ```bash
   git push origin main
   ```

6. **Verify:**
   ```bash
   curl https://api.bhavanaai.com/health
   ```

### Full Instructions

See: `DEPLOYMENT_CHECKLIST.md`

### Documentation

- **Full deployment guide**: `docs/deployment/README.md`
- **Implementation plan**: `docs/plans/2025-11-09-docker-compose-deployment-implementation-plan.md`
- **Design document**: `docs/plans/2025-11-09-docker-compose-deployment-design-v2.md`

## Daily Workflow (After Deployment)

```bash
# Make changes
vim src/agents/planner.py

# Commit and push
git add .
git commit -m "Improve planner reasoning"
git push origin main

# Wait 2-3 minutes (automatic deployment)

# Test
curl -X POST https://api.bhavanaai.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are software developer salaries in Seattle?"}'
```

## Cost

- Server: ~$5/month (home server electricity)
- Domain: ~$1/month (Porkbun)
- Azure Blob: ~$0.50/month (backups)
- **Total: ~$6.50/month**

## Support

Need help? Check:
1. `DEPLOYMENT_CHECKLIST.md` - Step-by-step guide
2. `docs/deployment/README.md` - Full documentation with troubleshooting
3. GitHub Actions logs - https://github.com/varunr89/oews/actions
