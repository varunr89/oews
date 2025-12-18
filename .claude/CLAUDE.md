## Production Deployment (Azure Container Apps)

The OEWS API runs on Azure Container Apps with scale-to-zero for cost optimization.

### Environment Details
- **API Endpoint:** `https://api.oews.bhavanaai.com/api/v1/`
- **Azure Resource Group:** `oews-rg`
- **Container Registry:** `oewsregistry.azurecr.io`
- **Container App:** `oews-api`
- **Region:** West US 2

### Architecture

```
GitHub (push to main)
    ↓
GitHub Actions (build & push)
    ↓
Azure Container Registry (oewsregistry.azurecr.io)
    ↓
Azure Container Apps (scale 0-1, auto-deploy)
    ↓
https://api.oews.bhavanaai.com
```

**Key features:**
- Scale-to-zero when idle ($0 compute cost)
- Database baked into container image (compressed via Git LFS)
- Managed TLS certificate (auto-renewed)
- CI/CD: Push to main → automatic deployment

### Deployment (Automatic)

Push to `main` triggers automatic deployment via GitHub Actions:

```bash
git push origin main
# Monitor: gh run watch
```

The workflow:
1. Checks out code (with LFS for database)
2. Logs into Azure
3. Builds Docker image (decompresses database during build)
4. Pushes to Azure Container Registry
5. Updates Container App with new image

### Manual Operations

**Check deployment status:**
```bash
az containerapp show --name oews-api --resource-group oews-rg --query "properties.runningStatus"
```

**View logs:**
```bash
az containerapp logs show --name oews-api --resource-group oews-rg --type console --tail 50
```

**Check revisions:**
```bash
az containerapp revision list --name oews-api --resource-group oews-rg -o table
```

**Force restart:**
```bash
az containerapp revision restart --name oews-api --resource-group oews-rg --revision <revision-name>
```

### Environment Variables

Secrets are stored in Azure Container Apps:
- `AZURE_INFERENCE_CREDENTIAL` - DeepSeek API key
- `AZURE_INFERENCE_ENDPOINT` - Azure AI endpoint
- `TAVILY_API_KEY` - Web research API
- `CORS_ORIGINS` - Allowed frontend origins

**Update secrets:**
```bash
az containerapp secret set --name oews-api --resource-group oews-rg \
  --secrets secret-name=secret-value

az containerapp update --name oews-api --resource-group oews-rg \
  --set-env-vars ENV_VAR=secretref:secret-name
```

### Testing

```bash
# Health check
curl https://api.oews.bhavanaai.com/health

# Query endpoint
curl -X POST https://api.oews.bhavanaai.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the average salary for software developers in California?"}'
```

### Common Issues

**Cold start slow (15-30 sec):**
- Normal behavior for scale-to-zero
- First request after idle triggers container startup
- Subsequent requests are fast

**Deployment fails:**
- Check GitHub Actions logs: `gh run view --log-failed`
- Verify Azure credentials: `az account show`
- Check ACR access: `az acr repository list --name oewsregistry`

**Environment variables not working:**
- Verify secrets exist: `az containerapp secret list --name oews-api --resource-group oews-rg`
- Check env vars: `az containerapp show --name oews-api --resource-group oews-rg --query "properties.template.containers[0].env"`

### Cost

Estimated ~$6-10/month:
- Container Registry (Basic): ~$5/month
- Container Apps (sporadic usage): ~$1-5/month
- Custom domain & TLS: $0 (included)

### Database Updates

The OEWS database is baked into the container image (compressed via Git LFS). To update:

1. Update `data/oews.db` locally
2. Regenerate compressed file: `gzip -c data/oews.db > data/oews.db.gz`
3. Commit and push: `git add data/oews.db.gz && git commit -m "data: update OEWS database" && git push`
4. CI/CD will rebuild and deploy automatically

---

## Legacy Home Server (Decommissioned)

Previously hosted on home server via Tailscale. Kept for reference only.

- **Server IP:** 100.107.15.52 (via Tailscale)
- **SSH:** `ssh varun@100.107.15.52`
- **Status:** Containers stopped, available for rollback if needed
