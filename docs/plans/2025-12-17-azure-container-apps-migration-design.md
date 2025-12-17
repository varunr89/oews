# Azure Container Apps Migration Design

## Overview

Migrate OEWS API from home server (Tailscale + Docker) to Azure Container Apps for improved reliability with scale-to-zero cost optimization.

## Goals

- **Reliability:** No dependency on home server uptime
- **Cost:** $10-15/month target (under $50 budget)
- **Scale-to-zero:** $0 compute cost when idle
- **Simplicity:** Minimal operational overhead

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Azure                                    │
│                                                                  │
│  ┌────────────────────┐      ┌────────────────────────────────┐ │
│  │  Azure Container   │      │  Container Apps Environment    │ │
│  │  Registry (Basic)  │      │                                │ │
│  │                    │      │  ┌──────────────────────────┐  │ │
│  │  oewsregistry.     │─────▶│  │     oews-api             │  │ │
│  │  azurecr.io        │      │  │                          │  │ │
│  │                    │      │  │  Python FastAPI          │  │ │
│  │  ~$5/month         │      │  │  + 2.2GB SQLite (baked)  │  │ │
│  └────────────────────┘      │  │                          │  │ │
│                              │  │  Scale: 0-1 replicas     │  │ │
│                              │  └──────────────────────────┘  │ │
│                              │                                │ │
│                              │  ~$1-5/month (usage-based)    │ │
│                              └────────────────────────────────┘ │
│                                          │                      │
│                                          │ HTTPS (managed TLS)  │
└──────────────────────────────────────────┼──────────────────────┘
                                           │
                                    api.oews.bhavanaai.com
```

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Compute platform | Azure Container Apps | Native scale-to-zero, simple, low cost |
| Database | Baked into image | Read-only, rarely changes, $0 storage cost |
| Registry | Azure Container Registry | Faster pulls, managed identity auth |
| Scaling | 0-1 replicas | Hobby project, no need for multiple instances |

## Cost Estimate

| Component | Monthly Cost |
|-----------|--------------|
| Container Apps (sporadic usage) | $1-5 |
| Container Registry (Basic) | $5 |
| Custom domain & TLS | $0 (included) |
| **Total** | **$6-10/month** |

## Container Image

Modified Dockerfile to bake database into image:

```dockerfile
FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && \
    uv pip install --system -e .

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Bake database into image (read-only, ~2.2GB)
COPY data/oews.db ./data/oews.db

# Security: non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "src.main"]
```

**Image size:** ~2.5GB (database + app + dependencies)

## Container App Configuration

```yaml
# Container settings
Container:
  Image: oewsregistry.azurecr.io/oews-api:latest
  CPU: 1.0 vCPU
  Memory: 4 GB  # Headroom for 2.2GB DB + Python

# Scaling (key for cost)
Scale:
  minReplicas: 0          # Scale to zero when idle
  maxReplicas: 1          # Cap for hobby project
  rules:
    - name: http-rule
      http:
        metadata:
          concurrentRequests: 10

# Ingress
Ingress:
  external: true
  targetPort: 8000
  transport: http
  allowInsecure: false

# Health probes
Probes:
  startup:
    path: /health
    initialDelaySeconds: 10
    periodSeconds: 5
    failureThreshold: 30   # Allow 150s for cold start
  readiness:
    path: /health
    periodSeconds: 10
```

## CI/CD Pipeline

```yaml
# .github/workflows/deploy-azure.yml
name: Build and Deploy to Azure

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  ACR_NAME: oewsregistry
  ACR_LOGIN_SERVER: oewsregistry.azurecr.io
  IMAGE_NAME: oews-api
  ACA_NAME: oews-api
  RESOURCE_GROUP: oews-rg

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Azure Login
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Login to ACR
        run: az acr login --name $ACR_NAME

      - name: Build and push image
        run: |
          docker build -t $ACR_LOGIN_SERVER/$IMAGE_NAME:${{ github.sha }} \
                       -t $ACR_LOGIN_SERVER/$IMAGE_NAME:latest .
          docker push $ACR_LOGIN_SERVER/$IMAGE_NAME --all-tags

      - name: Deploy to Container Apps
        run: |
          az containerapp update \
            --name $ACA_NAME \
            --resource-group $RESOURCE_GROUP \
            --image $ACR_LOGIN_SERVER/$IMAGE_NAME:${{ github.sha }}
```

## Authentication

```
GitHub Actions → Service Principal → ACR (push images)
Container App  → Managed Identity  → ACR (pull images)
```

No secrets stored in ACA for registry access.

## Networking

**Default endpoint:** `https://oews-api.<random>.westus2.azurecontainerapps.io`

**Custom domain setup:**
1. DNS: `api.oews.bhavanaai.com` CNAME → ACA default endpoint
2. ACA: Add custom domain, managed TLS certificate auto-provisioned

## Environment Variables

Secrets stored encrypted in ACA:

```bash
az containerapp update \
  --name oews-api \
  --resource-group oews-rg \
  --set-env-vars \
    OPENAI_API_KEY=secretref:openai-key \
    DEEPSEEK_API_KEY=secretref:deepseek-key \
    AZURE_OPENAI_API_KEY=secretref:azure-openai-key
```

## Migration Plan

### Phase 1: Azure Setup

1. Create Resource Group: `oews-rg`
2. Create Container Registry: `oewsregistry` (Basic SKU)
3. Create Container Apps Environment: `oews-env`
4. Create Service Principal for GitHub Actions
5. Store credentials in GitHub Secrets

### Phase 2: Image Preparation

1. Update Dockerfile to bake in database
2. Build and push image to ACR
3. Verify image in registry

### Phase 3: Container App Deployment

1. Create Container App with configuration above
2. Enable Managed Identity
3. Grant AcrPull role to identity
4. Configure environment variables (API keys)
5. Verify default endpoint works

### Phase 4: DNS Cutover

1. Update `api.oews.bhavanaai.com` CNAME to ACA endpoint
2. Add custom domain in ACA
3. Wait for TLS certificate provisioning
4. Verify custom domain works

### Phase 5: Decommission

1. Stop home server containers (keep for 2 weeks)
2. Monitor Azure deployment
3. Delete home server containers after validation period

## Rollback Plan

- Home server containers kept stopped (not deleted) for 2 weeks
- DNS can revert to Tailscale IP (`100.107.15.52`) if needed
- No data loss risk (database is read-only, baked into both environments)

## Cold Start Expectations

| Phase | Duration |
|-------|----------|
| ACA scheduling | 1-2 sec |
| Image pull (ACR, same region) | 5-10 sec |
| Container startup | 2-3 sec |
| Python/FastAPI init | 2-3 sec |
| **Total cold start** | **10-20 sec** |

First request after idle period will experience this delay. Subsequent requests are fast.

## Future Considerations

- **If cold starts become problematic:** Set minReplicas=1 (~$15-20/month)
- **If usage increases:** Increase maxReplicas, consider Azure SQL for database
- **Database updates:** Rebuild and redeploy image (annual BLS data refresh)
