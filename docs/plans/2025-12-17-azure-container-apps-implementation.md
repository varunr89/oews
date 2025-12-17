# Azure Container Apps Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate OEWS API from home server to Azure Container Apps with scale-to-zero.

**Architecture:** Azure Container Registry holds the image (~2.5GB with baked-in database). Azure Container Apps pulls from ACR via managed identity, scales 0-1 replicas based on HTTP traffic.

**Tech Stack:** Azure CLI, Docker, GitHub Actions, Azure Container Apps, Azure Container Registry

---

## Prerequisites

- Azure CLI installed (`az --version`)
- Docker installed and running
- GitHub CLI installed (`gh --version`)
- Azure subscription with billing enabled
- Logged into Azure CLI (`az login`)

---

## Task 1: Create Azure Resource Group

**Step 1: Create the resource group**

```bash
az group create \
  --name oews-rg \
  --location westus2
```

Expected output:
```json
{
  "id": "/subscriptions/.../resourceGroups/oews-rg",
  "location": "westus2",
  "name": "oews-rg",
  "properties": {
    "provisioningState": "Succeeded"
  }
}
```

**Step 2: Verify resource group exists**

```bash
az group show --name oews-rg --query "name"
```

Expected: `"oews-rg"`

---

## Task 2: Create Azure Container Registry

**Step 1: Create the registry (Basic SKU)**

```bash
az acr create \
  --resource-group oews-rg \
  --name oewsregistry \
  --sku Basic \
  --admin-enabled false
```

Expected output includes:
```json
{
  "name": "oewsregistry",
  "loginServer": "oewsregistry.azurecr.io",
  "sku": { "name": "Basic" }
}
```

**Step 2: Verify registry is accessible**

```bash
az acr show --name oewsregistry --query "loginServer"
```

Expected: `"oewsregistry.azurecr.io"`

**Note:** If `oewsregistry` is taken, try `oewsreg` or `oewsacr`. Registry names must be globally unique.

---

## Task 3: Create Container Apps Environment

**Step 1: Install/update Container Apps extension**

```bash
az extension add --name containerapp --upgrade
```

**Step 2: Register required providers**

```bash
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
```

**Step 3: Create the environment**

```bash
az containerapp env create \
  --name oews-env \
  --resource-group oews-rg \
  --location westus2
```

This takes 1-2 minutes. Expected output includes:
```json
{
  "name": "oews-env",
  "provisioningState": "Succeeded"
}
```

**Step 4: Verify environment**

```bash
az containerapp env show \
  --name oews-env \
  --resource-group oews-rg \
  --query "properties.provisioningState"
```

Expected: `"Succeeded"`

---

## Task 4: Create Service Principal for GitHub Actions

**Step 1: Get subscription ID**

```bash
az account show --query "id" -o tsv
```

Save this value as `SUBSCRIPTION_ID`.

**Step 2: Create service principal with Contributor role**

```bash
az ad sp create-for-rbac \
  --name "oews-github-actions" \
  --role Contributor \
  --scopes /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/oews-rg \
  --sdk-auth
```

Expected output (SAVE THIS - shown only once):
```json
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "clientSecret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "subscriptionId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  ...
}
```

**Step 3: Grant ACR push permission**

```bash
az role assignment create \
  --assignee <clientId from above> \
  --role AcrPush \
  --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/oews-rg/providers/Microsoft.ContainerRegistry/registries/oewsregistry
```

---

## Task 5: Add GitHub Secrets

**Step 1: Add Azure credentials secret**

```bash
gh secret set AZURE_CREDENTIALS --body '<entire JSON from Task 4 Step 2>'
```

Or via GitHub UI: Settings → Secrets and variables → Actions → New repository secret

**Step 2: Verify secret exists**

```bash
gh secret list
```

Expected: `AZURE_CREDENTIALS` appears in list.

---

## Task 6: Update Dockerfile to Bake Database

**Files:**
- Modify: `Dockerfile`

**Step 1: Update Dockerfile**

Replace contents of `Dockerfile` with:

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

**Step 2: Commit the change**

```bash
git add Dockerfile
git commit -m "feat: bake database into container image for ACA deployment"
```

---

## Task 7: Create GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/deploy-azure.yml`

**Step 1: Create the workflow file**

```yaml
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
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          lfs: true  # In case database is in LFS

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
          docker push $ACR_LOGIN_SERVER/$IMAGE_NAME:${{ github.sha }}
          docker push $ACR_LOGIN_SERVER/$IMAGE_NAME:latest

      - name: Deploy to Container Apps
        run: |
          az containerapp update \
            --name $ACA_NAME \
            --resource-group $RESOURCE_GROUP \
            --image $ACR_LOGIN_SERVER/$IMAGE_NAME:${{ github.sha }}
```

**Step 2: Commit the workflow**

```bash
git add .github/workflows/deploy-azure.yml
git commit -m "ci: add Azure Container Apps deployment workflow"
```

---

## Task 8: Build and Push Initial Image Manually

The Container App needs an image to exist before creation. Build and push manually first.

**Step 1: Login to ACR**

```bash
az acr login --name oewsregistry
```

Expected: `Login Succeeded`

**Step 2: Build the image (this takes several minutes due to 2.2GB database)**

```bash
docker build -t oewsregistry.azurecr.io/oews-api:initial .
```

**Step 3: Push to ACR**

```bash
docker push oewsregistry.azurecr.io/oews-api:initial
```

**Step 4: Verify image in registry**

```bash
az acr repository list --name oewsregistry
```

Expected: `["oews-api"]`

```bash
az acr repository show-tags --name oewsregistry --repository oews-api
```

Expected: `["initial"]`

---

## Task 9: Create Container App

**Step 1: Create the container app**

```bash
az containerapp create \
  --name oews-api \
  --resource-group oews-rg \
  --environment oews-env \
  --image oewsregistry.azurecr.io/oews-api:initial \
  --registry-server oewsregistry.azurecr.io \
  --registry-identity system \
  --target-port 8000 \
  --ingress external \
  --cpu 1.0 \
  --memory 4.0Gi \
  --min-replicas 0 \
  --max-replicas 1 \
  --scale-rule-name http-rule \
  --scale-rule-type http \
  --scale-rule-http-concurrency 10
```

This takes 1-2 minutes. Expected output includes:
```json
{
  "name": "oews-api",
  "properties": {
    "configuration": {
      "ingress": {
        "fqdn": "oews-api.<random>.westus2.azurecontainerapps.io"
      }
    }
  }
}
```

**Step 2: Get the app URL**

```bash
az containerapp show \
  --name oews-api \
  --resource-group oews-rg \
  --query "properties.configuration.ingress.fqdn" -o tsv
```

Save this URL (e.g., `oews-api.happyflower-12345.westus2.azurecontainerapps.io`).

---

## Task 10: Grant ACR Pull Permission to Container App

**Step 1: Get the Container App's managed identity principal ID**

```bash
az containerapp identity show \
  --name oews-api \
  --resource-group oews-rg \
  --query "principalId" -o tsv
```

Save this as `PRINCIPAL_ID`.

**Step 2: Get ACR resource ID**

```bash
az acr show --name oewsregistry --query "id" -o tsv
```

Save this as `ACR_ID`.

**Step 3: Assign AcrPull role**

```bash
az role assignment create \
  --assignee <PRINCIPAL_ID> \
  --role AcrPull \
  --scope <ACR_ID>
```

---

## Task 11: Configure Environment Variables

**Step 1: Set API key secrets**

```bash
az containerapp secret set \
  --name oews-api \
  --resource-group oews-rg \
  --secrets \
    openai-key=<your-openai-api-key> \
    deepseek-key=<your-deepseek-api-key>
```

**Step 2: Set environment variables referencing secrets**

```bash
az containerapp update \
  --name oews-api \
  --resource-group oews-rg \
  --set-env-vars \
    OPENAI_API_KEY=secretref:openai-key \
    DEEPSEEK_API_KEY=secretref:deepseek-key
```

**Note:** Add any other environment variables your app needs (check your current `.env` file on the home server).

---

## Task 12: Configure Health Probes

**Step 1: Update container app with proper probes**

```bash
az containerapp update \
  --name oews-api \
  --resource-group oews-rg \
  --yaml - <<EOF
properties:
  template:
    containers:
      - name: oews-api
        probes:
          - type: startup
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
            failureThreshold: 30
          - type: readiness
            httpGet:
              path: /health
              port: 8000
            periodSeconds: 10
            failureThreshold: 3
EOF
```

---

## Task 13: Test the Deployment

**Step 1: Get the app URL**

```bash
ACA_URL=$(az containerapp show \
  --name oews-api \
  --resource-group oews-rg \
  --query "properties.configuration.ingress.fqdn" -o tsv)
echo "App URL: https://$ACA_URL"
```

**Step 2: Test health endpoint (first request triggers cold start, wait ~30 sec)**

```bash
curl -v https://$ACA_URL/health
```

Expected: HTTP 200 with health response.

**Step 3: Test API endpoint**

```bash
curl -X POST https://$ACA_URL/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the average salary for software developers?"}'
```

Expected: JSON response with query results.

**Step 4: Check logs if something fails**

```bash
az containerapp logs show \
  --name oews-api \
  --resource-group oews-rg \
  --type console \
  --tail 50
```

---

## Task 14: Push Changes and Verify CI/CD

**Step 1: Push commits to main**

```bash
git push origin main
```

**Step 2: Watch the GitHub Actions workflow**

```bash
gh run watch
```

Expected: Workflow completes successfully, deploys new image to ACA.

**Step 3: Verify new image deployed**

```bash
az containerapp revision list \
  --name oews-api \
  --resource-group oews-rg \
  --query "[].{name:name, active:properties.active, created:properties.createdTime}" -o table
```

---

## Task 15: Configure Custom Domain (Optional)

**Step 1: Get the ACA default domain for CNAME**

```bash
az containerapp show \
  --name oews-api \
  --resource-group oews-rg \
  --query "properties.configuration.ingress.fqdn" -o tsv
```

**Step 2: In your DNS provider, add CNAME record:**

```
api.oews.bhavanaai.com  CNAME  <fqdn from above>
```

**Step 3: Add custom domain to ACA**

```bash
az containerapp hostname add \
  --name oews-api \
  --resource-group oews-rg \
  --hostname api.oews.bhavanaai.com
```

**Step 4: Bind managed certificate**

```bash
az containerapp hostname bind \
  --name oews-api \
  --resource-group oews-rg \
  --hostname api.oews.bhavanaai.com \
  --environment oews-env \
  --validation-method CNAME
```

**Step 5: Verify custom domain works**

```bash
curl https://api.oews.bhavanaai.com/health
```

---

## Task 16: Decommission Home Server (After Validation)

**Step 1: Stop containers on home server**

```bash
ssh varun@100.107.15.52 "docker stop oews-api oews-trace; docker ps -a | grep oews"
```

**Step 2: Keep containers for 2 weeks as rollback**

Don't delete yet. If issues arise, can restart with:
```bash
ssh varun@100.107.15.52 "docker start oews-api"
```

**Step 3: After 2 weeks of stable operation, remove containers**

```bash
ssh varun@100.107.15.52 "docker rm oews-api oews-trace"
```

---

## Verification Checklist

- [ ] Resource group created
- [ ] ACR created and accessible
- [ ] Container Apps environment created
- [ ] Service principal created with correct permissions
- [ ] GitHub secret configured
- [ ] Dockerfile updated with database copy
- [ ] GitHub Actions workflow created
- [ ] Initial image pushed to ACR
- [ ] Container App created and running
- [ ] ACR pull permissions granted
- [ ] Environment variables configured
- [ ] Health endpoint responding
- [ ] API queries working
- [ ] CI/CD pipeline working
- [ ] Custom domain configured (optional)
- [ ] Home server decommissioned

---

## Troubleshooting

### Cold start taking too long
Check startup probe settings. Increase `failureThreshold` if needed.

### 502 errors
Check container logs: `az containerapp logs show --name oews-api --resource-group oews-rg --type console`

### Image pull failures
Verify managed identity has AcrPull role. Check: `az role assignment list --assignee <principal-id>`

### Environment variables not set
List current env vars: `az containerapp show --name oews-api --resource-group oews-rg --query "properties.template.containers[0].env"`

### Scale-to-zero not working
Verify min replicas is 0: `az containerapp show --name oews-api --resource-group oews-rg --query "properties.template.scale"`
