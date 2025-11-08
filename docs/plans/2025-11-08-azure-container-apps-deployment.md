# Azure Container Apps Deployment with GitHub Actions Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deploy the OEWS Data Agent API to Azure Container Apps with automated CI/CD via GitHub Actions on every push to main branch.

**Architecture:** Containerized FastAPI application deployed to Azure Container Apps with production Azure SQL Database. GitHub Actions pipeline runs tests, builds Docker image, pushes to Azure Container Registry, and deploys to Container Apps with zero-downtime rolling updates.

**Tech Stack:** Docker (multi-stage builds), Azure Container Apps (consumption plan), Azure SQL Database (serverless), Azure Container Registry, GitHub Actions, Azure CLI, Python 3.11

---

## Task 1: Create Dockerfile for Production Deployment

**Goal:** Containerize the FastAPI application with optimized multi-stage build including Azure SQL ODBC drivers.

### Files to Create/Modify:
- **Create:** `Dockerfile`
- **Create:** `.dockerignore`

### Steps:

**Step 1: Create .dockerignore file**

Create `.dockerignore` to exclude unnecessary files from Docker build context:

```bash
# File: .dockerignore
.git
.github
.env
.env.*
.env.template
.venv
venv/
__pycache__
*.pyc
*.pyo
*.pyd
.pytest_cache
.coverage
htmlcov/
logs/*.log
*.db
.DS_Store
*.md
!README.md
tests/
scripts/
docs/
.vscode/
.idea/
```

**Verification:** Run `ls -la` and confirm `.dockerignore` exists.

**Step 2: Create Dockerfile with multi-stage build**

Create `Dockerfile` with optimized layers for production:

```dockerfile
# File: Dockerfile

# Stage 1: Build dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# Copy only requirements first for better caching
COPY requirements.txt .

# Install dependencies to user site-packages
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime image
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Azure SQL ODBC driver
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    unixodbc \
    unixodbc-dev \
    && curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-archive-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-archive-keyring.gpg] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder stage
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY data/ ./data/

# Create logs directory with proper permissions
RUN mkdir -p logs && chmod 755 logs

# Expose API port
EXPOSE 8000

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application (non-root user for security)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "src.main"]
```

**Verification:** Run `docker build -t oews-api:local .` and confirm build succeeds.

**Step 3: Test Docker image locally**

Run container locally to verify it works:

```bash
# Build image
docker build -t oews-api:local .

# Run container with dev database
docker run -p 8000:8000 \
  -e DATABASE_ENV=dev \
  -e SQLITE_DB_PATH=data/oews.db \
  -e API_RELOAD=false \
  oews-api:local
```

**Expected output:**
```
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Verification:** In another terminal, run `curl http://localhost:8000/health` and confirm response: `{"status":"healthy","workflow_loaded":true}`

**Step 4: Stop test container**

```bash
docker ps  # Get container ID
docker stop <container-id>
```

**Step 5: Commit containerization files**

```bash
git add Dockerfile .dockerignore
git commit -m "feat: add Docker containerization with multi-stage build and Azure SQL ODBC support"
```

---

## Task 2: Create GitHub Actions CI Pipeline (Test-Only)

**Goal:** Set up automated testing pipeline that runs on all pushes and pull requests.

### Files to Create/Modify:
- **Create:** `.github/workflows/ci.yml`

### Steps:

**Step 1: Create GitHub Actions workflow directory**

```bash
mkdir -p .github/workflows
```

**Step 2: Create CI workflow file**

Create `.github/workflows/ci.yml`:

```yaml
# File: .github/workflows/ci.yml
name: CI - Test and Lint

on:
  push:
    branches: ["**"]
  pull_request:
    branches: [main]

jobs:
  test:
    name: Run Tests
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run linting with flake8
        run: |
          pip install flake8
          flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics
          flake8 src/ --count --max-complexity=10 --max-line-length=127 --statistics

      - name: Run type checking with mypy
        continue-on-error: true
        run: |
          pip install mypy
          mypy src/ || echo "Type checking had errors but continuing..."

      - name: Run tests with pytest
        env:
          DATABASE_ENV: dev
          SQLITE_DB_PATH: data/oews.db
        run: |
          pip install pytest pytest-cov
          pytest tests/ -v --cov=src --cov-report=term-missing --cov-fail-under=70

      - name: Upload coverage reports
        uses: codecov/codecov-action@v4
        if: always()
        continue-on-error: true
        with:
          files: ./coverage.xml
          flags: unittests
```

**Step 3: Test workflow syntax**

```bash
# Install actionlint for workflow validation (optional but recommended)
# If available, run:
# actionlint .github/workflows/ci.yml

# Otherwise, just verify YAML is valid:
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
```

**Expected output:** No errors.

**Step 4: Commit CI workflow**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions workflow for automated testing and linting"
```

**Step 5: Push and verify workflow runs**

```bash
git push -u origin claude/brainstorm-deployment-strategy-011CUvxnTM5fjXmxfPwZ8JxH
```

**Verification:** Go to GitHub Actions tab and confirm the CI workflow runs successfully.

---

## Task 3: Create Azure Infrastructure Setup Script

**Goal:** Automate Azure resource provisioning with idempotent shell script.

### Files to Create/Modify:
- **Create:** `infra/setup-azure.sh`
- **Create:** `infra/README.md`

### Steps:

**Step 1: Create infrastructure directory**

```bash
mkdir -p infra
```

**Step 2: Create Azure setup script**

Create `infra/setup-azure.sh`:

```bash
#!/bin/bash
# File: infra/setup-azure.sh
# Purpose: Provision all Azure resources for OEWS deployment

set -euo pipefail

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-oews-rg}"
LOCATION="${LOCATION:-eastus}"
ACR_NAME="${ACR_NAME:-oewsacr}"
SQL_SERVER="${SQL_SERVER:-oews-sqlserver}"
SQL_DB="${SQL_DB:-oewsdb}"
SQL_ADMIN="${SQL_ADMIN:-oewsadmin}"
CONTAINER_ENV="${CONTAINER_ENV:-oews-env}"
CONTAINER_APP="${CONTAINER_APP:-oews-api}"
KEYVAULT_NAME="${KEYVAULT_NAME:-oews-keyvault}"

echo "🚀 Starting Azure infrastructure setup..."

# Step 1: Create Resource Group
echo "📦 Creating resource group: $RESOURCE_GROUP"
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --tags "project=oews" "environment=production"

# Step 2: Create Azure Container Registry
echo "🐳 Creating Azure Container Registry: $ACR_NAME"
az acr create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$ACR_NAME" \
  --sku Basic \
  --admin-enabled true \
  --location "$LOCATION"

# Step 3: Create Azure SQL Server
echo "💾 Creating Azure SQL Server: $SQL_SERVER"
SQL_PASSWORD=$(openssl rand -base64 32)
az sql server create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$SQL_SERVER" \
  --location "$LOCATION" \
  --admin-user "$SQL_ADMIN" \
  --admin-password "$SQL_PASSWORD"

# Configure firewall to allow Azure services
az sql server firewall-rule create \
  --resource-group "$RESOURCE_GROUP" \
  --server "$SQL_SERVER" \
  --name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0

# Step 4: Create Azure SQL Database (Serverless)
echo "💾 Creating Azure SQL Database: $SQL_DB"
az sql db create \
  --resource-group "$RESOURCE_GROUP" \
  --server "$SQL_SERVER" \
  --name "$SQL_DB" \
  --edition GeneralPurpose \
  --compute-model Serverless \
  --family Gen5 \
  --capacity 1 \
  --auto-pause-delay 60

# Step 5: Create Key Vault
echo "🔐 Creating Key Vault: $KEYVAULT_NAME"
az keyvault create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$KEYVAULT_NAME" \
  --location "$LOCATION" \
  --enable-rbac-authorization false

# Store SQL password in Key Vault
az keyvault secret set \
  --vault-name "$KEYVAULT_NAME" \
  --name "azure-sql-password" \
  --value "$SQL_PASSWORD"

# Step 6: Create Log Analytics Workspace
echo "📊 Creating Log Analytics Workspace"
WORKSPACE_NAME="${CONTAINER_ENV}-logs"
az monitor log-analytics workspace create \
  --resource-group "$RESOURCE_GROUP" \
  --workspace-name "$WORKSPACE_NAME" \
  --location "$LOCATION"

WORKSPACE_ID=$(az monitor log-analytics workspace show \
  --resource-group "$RESOURCE_GROUP" \
  --workspace-name "$WORKSPACE_NAME" \
  --query customerId -o tsv)

WORKSPACE_KEY=$(az monitor log-analytics workspace get-shared-keys \
  --resource-group "$RESOURCE_GROUP" \
  --workspace-name "$WORKSPACE_NAME" \
  --query primarySharedKey -o tsv)

# Step 7: Create Container Apps Environment
echo "🌐 Creating Container Apps Environment: $CONTAINER_ENV"
az containerapp env create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$CONTAINER_ENV" \
  --location "$LOCATION" \
  --logs-workspace-id "$WORKSPACE_ID" \
  --logs-workspace-key "$WORKSPACE_KEY"

# Step 8: Create Container App (initial deployment with placeholder image)
echo "📦 Creating Container App: $CONTAINER_APP"
az containerapp create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$CONTAINER_APP" \
  --environment "$CONTAINER_ENV" \
  --image mcr.microsoft.com/azuredocs/containerapps-helloworld:latest \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 10 \
  --cpu 0.5 \
  --memory 1.0Gi

# Step 9: Get Container App URL
CONTAINER_APP_URL=$(az containerapp show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$CONTAINER_APP" \
  --query properties.configuration.ingress.fqdn -o tsv)

# Step 10: Output summary
echo ""
echo "✅ Azure infrastructure setup complete!"
echo ""
echo "📋 Resource Summary:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Container Registry: $ACR_NAME.azurecr.io"
echo "  SQL Server: $SQL_SERVER.database.windows.net"
echo "  SQL Database: $SQL_DB"
echo "  SQL Admin: $SQL_ADMIN"
echo "  Key Vault: $KEYVAULT_NAME"
echo "  Container App URL: https://$CONTAINER_APP_URL"
echo ""
echo "🔐 Secrets stored in Key Vault:"
echo "  - azure-sql-password"
echo ""
echo "📝 Next steps:"
echo "  1. Import database schema: sqlcmd -S $SQL_SERVER.database.windows.net -d $SQL_DB -U $SQL_ADMIN -i database_schema.sql"
echo "  2. Store LLM API keys in Key Vault"
echo "  3. Configure GitHub secrets for CI/CD"
echo "  4. Run GitHub Actions workflow to deploy"
```

**Step 3: Make script executable**

```bash
chmod +x infra/setup-azure.sh
```

**Step 4: Create infrastructure README**

Create `infra/README.md`:

```markdown
# Azure Infrastructure

## Prerequisites

- Azure CLI installed and authenticated (`az login`)
- Permissions to create resources in Azure subscription
- OpenSSL for password generation

## Quick Start

1. Set environment variables (optional):
```bash
export RESOURCE_GROUP="oews-rg"
export LOCATION="eastus"
export ACR_NAME="oewsacr"
```

2. Run setup script:
```bash
./infra/setup-azure.sh
```

3. Import database schema:
```bash
# Get password from Key Vault
SQL_PASSWORD=$(az keyvault secret show --vault-name oews-keyvault --name azure-sql-password --query value -o tsv)

# Import schema
sqlcmd -S oews-sqlserver.database.windows.net -d oewsdb -U oewsadmin -P "$SQL_PASSWORD" -i database_schema.sql
```

## Resources Created

- **Resource Group:** `oews-rg`
- **Container Registry:** `oewsacr.azurecr.io`
- **SQL Server:** `oews-sqlserver.database.windows.net`
- **SQL Database:** `oewsdb` (Serverless tier)
- **Key Vault:** `oews-keyvault`
- **Log Analytics:** `oews-env-logs`
- **Container Apps Environment:** `oews-env`
- **Container App:** `oews-api`

## Cost Estimates

- Container Apps: ~$20-50/month (consumption plan)
- Azure SQL: ~$50-100/month (serverless, auto-pause enabled)
- Container Registry: $5/month (Basic tier)
- Log Analytics: ~$5-10/month
- **Total: ~$80-165/month** (excluding LLM API costs)

## Cleanup

To delete all resources:
```bash
az group delete --name oews-rg --yes --no-wait
```
```

**Step 5: Commit infrastructure scripts**

```bash
git add infra/
git commit -m "infra: add Azure resource provisioning scripts and documentation"
```

---

## Task 4: Configure GitHub Secrets for Deployment

**Goal:** Document required GitHub secrets for the deployment pipeline.

### Files to Create/Modify:
- **Create:** `docs/deployment-setup.md`

### Steps:

**Step 1: Create deployment setup documentation**

Create `docs/deployment-setup.md`:

```markdown
# Deployment Setup Guide

## GitHub Secrets Configuration

Navigate to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

### Required Secrets

1. **AZURE_CREDENTIALS**

   Create Azure Service Principal:
   ```bash
   az ad sp create-for-rbac \
     --name "github-actions-oews" \
     --role contributor \
     --scopes /subscriptions/{subscription-id}/resourceGroups/oews-rg \
     --sdk-auth
   ```

   Copy the entire JSON output and paste as secret value.

2. **ACR_USERNAME**

   Get from Azure CLI:
   ```bash
   az acr credential show --name oewsacr --query username -o tsv
   ```

3. **ACR_PASSWORD**

   Get from Azure CLI:
   ```bash
   az acr credential show --name oewsacr --query passwords[0].value -o tsv
   ```

4. **AZURE_SQL_PASSWORD**

   Get from Key Vault:
   ```bash
   az keyvault secret show --vault-name oews-keyvault --name azure-sql-password --query value -o tsv
   ```

5. **AZURE_INFERENCE_CREDENTIAL**

   Your Azure AI Inference API key from Azure AI Studio.

6. **OPENAI_API_KEY** (if using OpenAI)

   Your OpenAI API key from platform.openai.com.

7. **TAVILY_API_KEY** (optional)

   Your Tavily API key for web research agent.

### Environment Variables (set in GitHub Actions or Container App)

These are set directly in the workflow or Container App configuration:

- `DATABASE_ENV=prod`
- `AZURE_SQL_SERVER=oews-sqlserver.database.windows.net`
- `AZURE_SQL_DATABASE=oewsdb`
- `AZURE_SQL_USERNAME=oewsadmin`
- `API_HOST=0.0.0.0`
- `API_PORT=8000`
- `API_RELOAD=false`

## Deployment Workflow

1. **Initial Setup:** Run `infra/setup-azure.sh` to create all Azure resources
2. **Import Database:** Use sqlcmd to import `database_schema.sql`
3. **Configure Secrets:** Add all required secrets to GitHub
4. **Test Deployment:** Push to a feature branch and verify CI passes
5. **Deploy to Production:** Push to main branch to trigger deployment
6. **Verify:** Check Container App URL and test `/health` endpoint

## Rollback Procedure

If deployment fails:

```bash
# Get previous revision
az containerapp revision list \
  --resource-group oews-rg \
  --name oews-api \
  --query "[].name" -o tsv

# Activate previous revision
az containerapp revision activate \
  --resource-group oews-rg \
  --name oews-api \
  --revision <previous-revision-name>
```

## Monitoring

- **Application Logs:** `az containerapp logs show --name oews-api --resource-group oews-rg --follow`
- **Metrics:** Azure Portal → Container Apps → oews-api → Metrics
- **Log Analytics:** Azure Portal → Log Analytics → oews-env-logs → Logs

## Troubleshooting

### Container fails to start

Check logs:
```bash
az containerapp logs show --name oews-api --resource-group oews-rg --tail 50
```

### Database connection errors

Verify firewall rules:
```bash
az sql server firewall-rule list --resource-group oews-rg --server oews-sqlserver
```

### Image pull errors

Verify ACR credentials:
```bash
az acr credential show --name oewsacr
```
```

**Step 2: Commit documentation**

```bash
git add docs/deployment-setup.md
git commit -m "docs: add deployment setup and troubleshooting guide"
```

---

## Task 5: Create GitHub Actions Deployment Workflow

**Goal:** Implement complete CI/CD pipeline that deploys to Azure Container Apps on push to main.

### Files to Create/Modify:
- **Create:** `.github/workflows/deploy.yml`

### Steps:

**Step 1: Create deployment workflow**

Create `.github/workflows/deploy.yml`:

```yaml
# File: .github/workflows/deploy.yml
name: Deploy to Azure Container Apps

on:
  push:
    branches: [main]
  workflow_dispatch:  # Allow manual triggers

env:
  REGISTRY: oewsacr.azurecr.io
  IMAGE_NAME: oews-api
  RESOURCE_GROUP: oews-rg
  CONTAINER_APP: oews-api

jobs:
  test:
    name: Run Tests
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run tests
        env:
          DATABASE_ENV: dev
          SQLITE_DB_PATH: data/oews.db
        run: |
          pip install pytest pytest-cov
          pytest tests/ -v --cov=src --cov-report=term-missing --cov-fail-under=70

  build-and-push:
    name: Build and Push Docker Image
    needs: test
    runs-on: ubuntu-latest
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Log in to Azure Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ secrets.ACR_USERNAME }}
          password: ${{ secrets.ACR_PASSWORD }}

      - name: Extract metadata for Docker
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix={{branch}}-
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:buildcache
          cache-to: type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:buildcache,mode=max

  deploy:
    name: Deploy to Azure Container Apps
    needs: build-and-push
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://${{ steps.deploy.outputs.app-url }}

    steps:
      - name: Log in to Azure
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Deploy to Container Apps
        id: deploy
        run: |
          # Update container app with new image
          az containerapp update \
            --name ${{ env.CONTAINER_APP }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --image ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:main-${{ github.sha }} \
            --set-env-vars \
              DATABASE_ENV=prod \
              AZURE_SQL_SERVER=oews-sqlserver.database.windows.net \
              AZURE_SQL_DATABASE=oewsdb \
              AZURE_SQL_USERNAME=oewsadmin \
              AZURE_SQL_PASSWORD=secretref:azure-sql-password \
              AZURE_INFERENCE_CREDENTIAL=secretref:azure-inference-credential \
              OPENAI_API_KEY=secretref:openai-api-key \
              TAVILY_API_KEY=secretref:tavily-api-key \
              API_HOST=0.0.0.0 \
              API_PORT=8000 \
              API_RELOAD=false

          # Get app URL
          APP_URL=$(az containerapp show \
            --name ${{ env.CONTAINER_APP }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --query properties.configuration.ingress.fqdn -o tsv)

          echo "app-url=https://$APP_URL" >> $GITHUB_OUTPUT

      - name: Configure Container App secrets
        run: |
          # Set secrets from GitHub secrets
          az containerapp secret set \
            --name ${{ env.CONTAINER_APP }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --secrets \
              azure-sql-password=${{ secrets.AZURE_SQL_PASSWORD }} \
              azure-inference-credential=${{ secrets.AZURE_INFERENCE_CREDENTIAL }} \
              openai-api-key=${{ secrets.OPENAI_API_KEY }} \
              tavily-api-key=${{ secrets.TAVILY_API_KEY }}

      - name: Wait for deployment
        run: |
          echo "Waiting 30 seconds for deployment to stabilize..."
          sleep 30

      - name: Health check
        run: |
          HEALTH_URL="https://$(az containerapp show \
            --name ${{ env.CONTAINER_APP }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --query properties.configuration.ingress.fqdn -o tsv)/health"

          echo "Checking health at: $HEALTH_URL"

          for i in {1..10}; do
            if curl -f -s "$HEALTH_URL" | grep -q "healthy"; then
              echo "✅ Health check passed!"
              exit 0
            fi
            echo "Attempt $i/10 failed, retrying in 10 seconds..."
            sleep 10
          done

          echo "❌ Health check failed after 10 attempts"
          exit 1

      - name: Deployment summary
        run: |
          echo "## 🚀 Deployment Successful" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "**Application URL:** ${{ steps.deploy.outputs.app-url }}" >> $GITHUB_STEP_SUMMARY
          echo "**Image:** ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:main-${{ github.sha }}" >> $GITHUB_STEP_SUMMARY
          echo "**Commit:** ${{ github.sha }}" >> $GITHUB_STEP_SUMMARY
```

**Step 2: Verify workflow syntax**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/deploy.yml'))"
```

**Expected output:** No errors.

**Step 3: Commit deployment workflow**

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: add GitHub Actions deployment workflow for Azure Container Apps"
```

---

## Task 6: Update Production Configuration

**Goal:** Ensure application is production-ready with proper CORS, logging, and security settings.

### Files to Create/Modify:
- **Modify:** `src/main.py`

### Steps:

**Step 1: Read current main.py**

```bash
cat src/main.py | head -50
```

**Step 2: Add production environment detection**

Add at the top of `src/main.py` after imports:

```python
# Production environment detection
ENV = os.getenv("ENV", "development")
IS_PRODUCTION = ENV == "production" or os.getenv("DATABASE_ENV") == "prod"
```

**Step 3: Update CORS configuration for production**

Find the CORS middleware section and update it:

```python
# Configure CORS based on environment
if IS_PRODUCTION:
    # Production: Restrict to known domains
    allowed_origins = [
        "https://microsoftedge-spark.github.io",
        "https://*.github.io",
        # Add your production frontend domains here
    ]
    logger.info(f"Production mode: CORS restricted to {len(allowed_origins)} origins")
else:
    # Development: Allow all
    allowed_origins = ["*"]
    logger.info("Development mode: CORS allows all origins")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Step 4: Update Uvicorn configuration in src/main.py**

Find the `if __name__ == "__main__"` block and update:

```python
if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "false").lower() == "true"

    # Disable reload in production
    if IS_PRODUCTION and reload:
        logger.warning("Disabling reload in production environment")
        reload = False

    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )
```

**Step 5: Test changes locally**

```bash
# Set production env
export DATABASE_ENV=prod
python -m src.main &
PID=$!

# Check logs show production mode
sleep 3
curl http://localhost:8000/health

# Kill test server
kill $PID
```

**Step 6: Commit production configuration**

```bash
git add src/main.py
git commit -m "feat: add production environment detection and secure CORS configuration"
```

---

## Task 7: Database Schema Import Helper Script

**Goal:** Create helper script to import database schema to Azure SQL.

### Files to Create/Modify:
- **Create:** `scripts/import-schema-azure.sh`

### Steps:

**Step 1: Create schema import script**

Create `scripts/import-schema-azure.sh`:

```bash
#!/bin/bash
# File: scripts/import-schema-azure.sh
# Purpose: Import database schema to Azure SQL Database

set -euo pipefail

# Configuration
SQL_SERVER="${SQL_SERVER:-oews-sqlserver.database.windows.net}"
SQL_DB="${SQL_DB:-oewsdb}"
SQL_ADMIN="${SQL_ADMIN:-oewsadmin}"
KEYVAULT_NAME="${KEYVAULT_NAME:-oews-keyvault}"
SCHEMA_FILE="database_schema.sql"

echo "🔐 Retrieving SQL password from Key Vault..."
SQL_PASSWORD=$(az keyvault secret show \
  --vault-name "$KEYVAULT_NAME" \
  --name azure-sql-password \
  --query value -o tsv)

if [ -z "$SQL_PASSWORD" ]; then
  echo "❌ Failed to retrieve password from Key Vault"
  exit 1
fi

echo "📊 Importing schema from $SCHEMA_FILE..."

# Check if sqlcmd is available
if ! command -v sqlcmd &> /dev/null; then
  echo "❌ sqlcmd not found. Please install SQL Server command-line tools."
  echo "   Ubuntu/Debian: https://learn.microsoft.com/en-us/sql/linux/sql-server-linux-setup-tools"
  echo "   macOS: brew install mssql-tools"
  exit 1
fi

# Import schema
sqlcmd -S "$SQL_SERVER" \
  -d "$SQL_DB" \
  -U "$SQL_ADMIN" \
  -P "$SQL_PASSWORD" \
  -i "$SCHEMA_FILE" \
  -e

if [ $? -eq 0 ]; then
  echo "✅ Schema imported successfully!"
  echo ""
  echo "Verifying tables..."
  sqlcmd -S "$SQL_SERVER" \
    -d "$SQL_DB" \
    -U "$SQL_ADMIN" \
    -P "$SQL_PASSWORD" \
    -Q "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME"
else
  echo "❌ Schema import failed"
  exit 1
fi
```

**Step 2: Make script executable**

```bash
chmod +x scripts/import-schema-azure.sh
```

**Step 3: Update scripts/README.md or create if it doesn't exist**

Create or update `scripts/README.md`:

```markdown
# Scripts

## Database Management

### import-schema-azure.sh

Import database schema to Azure SQL Database.

**Prerequisites:**
- Azure CLI installed and logged in
- sqlcmd installed (SQL Server command-line tools)
- Azure infrastructure provisioned

**Usage:**
```bash
./scripts/import-schema-azure.sh
```

**Environment variables:**
- `SQL_SERVER` (default: oews-sqlserver.database.windows.net)
- `SQL_DB` (default: oewsdb)
- `SQL_ADMIN` (default: oewsadmin)
- `KEYVAULT_NAME` (default: oews-keyvault)

## Development

### start_server.sh

Start the development server locally.

**Usage:**
```bash
./scripts/start_server.sh
```
```

**Step 4: Commit database scripts**

```bash
git add scripts/import-schema-azure.sh scripts/README.md
git commit -m "feat: add Azure SQL schema import helper script"
```

---

## Task 8: Add Production Readiness Checklist

**Goal:** Create comprehensive pre-deployment checklist.

### Files to Create/Modify:
- **Create:** `docs/production-checklist.md`

### Steps:

**Step 1: Create production checklist**

Create `docs/production-checklist.md`:

```markdown
# Production Deployment Checklist

## Pre-Deployment

### Azure Infrastructure
- [ ] Azure CLI installed and authenticated
- [ ] Run `./infra/setup-azure.sh` to provision resources
- [ ] Verify all resources created successfully
- [ ] Import database schema: `./scripts/import-schema-azure.sh`
- [ ] Verify database tables created

### Secrets Management
- [ ] Store Azure SQL password in Key Vault
- [ ] Store Azure Inference API key in Key Vault
- [ ] Store OpenAI API key in Key Vault (if using)
- [ ] Store Tavily API key in Key Vault (if using)

### GitHub Configuration
- [ ] Add AZURE_CREDENTIALS secret (Service Principal JSON)
- [ ] Add ACR_USERNAME secret
- [ ] Add ACR_PASSWORD secret
- [ ] Add AZURE_SQL_PASSWORD secret
- [ ] Add AZURE_INFERENCE_CREDENTIAL secret
- [ ] Add OPENAI_API_KEY secret (if using OpenAI)
- [ ] Add TAVILY_API_KEY secret (optional)

### Application Configuration
- [ ] Review CORS allowed origins in `src/main.py`
- [ ] Add production frontend domains to allowed_origins
- [ ] Verify DATABASE_ENV=prod in deployment workflow
- [ ] Verify API_RELOAD=false in production

### Security
- [ ] Review firewall rules for Azure SQL
- [ ] Enable diagnostic logging in Container Apps
- [ ] Set up Application Insights (optional but recommended)
- [ ] Review IAM roles and permissions
- [ ] Consider adding API authentication (API keys/JWT)

## Deployment

### First Deployment
- [ ] Push code to main branch
- [ ] Monitor GitHub Actions workflow
- [ ] Verify CI tests pass
- [ ] Verify Docker build succeeds
- [ ] Verify deployment to Container Apps succeeds
- [ ] Check health endpoint: `curl https://<app-url>/health`

### Verification
- [ ] Test health endpoint returns `{"status":"healthy"}`
- [ ] Test query endpoint with sample request
- [ ] Verify database connectivity (check logs)
- [ ] Verify LLM provider connectivity
- [ ] Check response times are acceptable
- [ ] Review container logs for errors

### Monitoring Setup
- [ ] Configure Log Analytics workspace
- [ ] Set up basic alerts (health check failures)
- [ ] Set up cost alerts
- [ ] Monitor first 24 hours of traffic

## Post-Deployment

### Documentation
- [ ] Update README with production URL
- [ ] Document API endpoints for consumers
- [ ] Share API documentation (Swagger UI URL)
- [ ] Create runbook for common operations

### Operational Readiness
- [ ] Test rollback procedure
- [ ] Document incident response process
- [ ] Set up on-call rotation (if applicable)
- [ ] Schedule regular dependency updates

### Performance Tuning
- [ ] Monitor cold start times
- [ ] Adjust min/max replicas based on traffic
- [ ] Review and optimize database queries
- [ ] Consider caching for common queries
- [ ] Monitor LLM API costs

## Rollback Plan

If deployment fails:

1. Check GitHub Actions logs for errors
2. Check Container Apps logs: `az containerapp logs show --name oews-api --resource-group oews-rg`
3. Roll back to previous revision if needed
4. Fix issues in feature branch
5. Re-deploy after fixes verified

## Cost Monitoring

### Daily Tasks
- [ ] Check Azure Cost Management dashboard
- [ ] Review LLM API usage and costs
- [ ] Monitor database DTU/vCore usage

### Weekly Tasks
- [ ] Review cost trends
- [ ] Optimize underutilized resources
- [ ] Review and clean up old container images

### Monthly Tasks
- [ ] Full cost analysis and reporting
- [ ] Review scaling parameters
- [ ] Update cost forecasts
```

**Step 2: Commit checklist**

```bash
git add docs/production-checklist.md
git commit -m "docs: add comprehensive production deployment checklist"
```

---

## Task 9: Create Deployment Testing Script

**Goal:** Automated script to test deployed API endpoints.

### Files to Create/Modify:
- **Create:** `tests/test-deployment.sh`

### Steps:

**Step 1: Create deployment test script**

Create `tests/test-deployment.sh`:

```bash
#!/bin/bash
# File: tests/test-deployment.sh
# Purpose: Test deployed API endpoints

set -euo pipefail

# Configuration
API_URL="${API_URL:-}"

if [ -z "$API_URL" ]; then
  echo "Usage: API_URL=https://your-app.azurecontainerapps.io ./tests/test-deployment.sh"
  exit 1
fi

echo "🧪 Testing deployment at: $API_URL"
echo ""

# Test 1: Health Check
echo "Test 1: Health Check"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "$API_URL/health")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
BODY=$(echo "$HEALTH_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
  echo "✅ Health check passed (HTTP $HTTP_CODE)"
  echo "   Response: $BODY"
else
  echo "❌ Health check failed (HTTP $HTTP_CODE)"
  exit 1
fi
echo ""

# Test 2: API Documentation
echo "Test 2: API Documentation (Swagger)"
DOCS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/docs")

if [ "$DOCS_CODE" = "200" ]; then
  echo "✅ API docs accessible (HTTP $DOCS_CODE)"
else
  echo "❌ API docs failed (HTTP $DOCS_CODE)"
fi
echo ""

# Test 3: Models Endpoint
echo "Test 3: Models Endpoint"
MODELS_RESPONSE=$(curl -s -w "\n%{http_code}" "$API_URL/api/v1/models")
HTTP_CODE=$(echo "$MODELS_RESPONSE" | tail -n1)

if [ "$HTTP_CODE" = "200" ]; then
  echo "✅ Models endpoint passed (HTTP $HTTP_CODE)"
  MODELS_COUNT=$(echo "$MODELS_RESPONSE" | head -n-1 | grep -o "model_id" | wc -l)
  echo "   Found $MODELS_COUNT models"
else
  echo "❌ Models endpoint failed (HTTP $HTTP_CODE)"
fi
echo ""

# Test 4: Query Endpoint (Basic)
echo "Test 4: Query Endpoint (Sample Query)"
QUERY_RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST "$API_URL/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the average wage for software developers in California?", "enable_charts": false}')

HTTP_CODE=$(echo "$QUERY_RESPONSE" | tail -n1)
BODY=$(echo "$QUERY_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
  echo "✅ Query endpoint passed (HTTP $HTTP_CODE)"

  # Check response structure
  if echo "$BODY" | grep -q '"answer"'; then
    echo "   Response contains answer ✅"
  else
    echo "   Response missing answer field ⚠️"
  fi

  if echo "$BODY" | grep -q '"metadata"'; then
    echo "   Response contains metadata ✅"
  else
    echo "   Response missing metadata field ⚠️"
  fi
else
  echo "❌ Query endpoint failed (HTTP $HTTP_CODE)"
  echo "   Response: $BODY"
fi
echo ""

# Test 5: CORS Headers
echo "Test 5: CORS Configuration"
CORS_RESPONSE=$(curl -s -I -X OPTIONS "$API_URL/api/v1/query" \
  -H "Origin: https://example.com" \
  -H "Access-Control-Request-Method: POST")

if echo "$CORS_RESPONSE" | grep -q "Access-Control-Allow-Origin"; then
  echo "✅ CORS headers present"
else
  echo "⚠️  CORS headers not found (may be restricted)"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Deployment tests completed!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

**Step 2: Make script executable**

```bash
chmod +x tests/test-deployment.sh
```

**Step 3: Test script locally (optional)**

```bash
# Start local server first
# python -m src.main &

# Then test
# API_URL=http://localhost:8000 ./tests/test-deployment.sh
```

**Step 4: Commit test script**

```bash
git add tests/test-deployment.sh
git commit -m "test: add automated deployment testing script"
```

---

## Task 10: Final Documentation Update

**Goal:** Update main README with deployment information.

### Files to Create/Modify:
- **Modify:** `README.md`

### Steps:

**Step 1: Read current README**

```bash
head -30 README.md
```

**Step 2: Add deployment section to README**

Add before the "Development" section or at an appropriate location:

```markdown
## Deployment

### Production Deployment to Azure Container Apps

This application is configured for automated deployment to Azure Container Apps via GitHub Actions.

**Quick Start:**

1. **Provision Azure Infrastructure:**
   ```bash
   ./infra/setup-azure.sh
   ```

2. **Import Database Schema:**
   ```bash
   ./scripts/import-schema-azure.sh
   ```

3. **Configure GitHub Secrets:**
   See [docs/deployment-setup.md](docs/deployment-setup.md) for required secrets.

4. **Deploy:**
   Push to `main` branch to trigger automatic deployment.

**Documentation:**
- [Deployment Setup Guide](docs/deployment-setup.md)
- [Production Checklist](docs/production-checklist.md)
- [Infrastructure README](infra/README.md)

**Monitoring:**
- Health Check: `https://<your-app>.azurecontainerapps.io/health`
- API Docs: `https://<your-app>.azurecontainerapps.io/docs`
- Logs: `az containerapp logs show --name oews-api --resource-group oews-rg --follow`

### CI/CD Pipeline

Every push to `main` triggers:
1. ✅ Run tests with pytest
2. 🐳 Build Docker image
3. 📦 Push to Azure Container Registry
4. 🚀 Deploy to Azure Container Apps
5. ✅ Run health checks

See [.github/workflows/deploy.yml](.github/workflows/deploy.yml) for details.
```

**Step 3: Commit README update**

```bash
git add README.md
git commit -m "docs: add deployment information to README"
```

---

## Final Deployment Steps

After completing all tasks above, follow this sequence to deploy:

### 1. Provision Infrastructure

```bash
# Ensure you're logged into Azure
az login

# Run infrastructure setup
./infra/setup-azure.sh

# Wait for completion (5-10 minutes)
```

### 2. Import Database

```bash
# Import schema to Azure SQL
./scripts/import-schema-azure.sh
```

### 3. Configure GitHub Secrets

Follow [docs/deployment-setup.md](docs/deployment-setup.md) to add all required secrets to your GitHub repository.

### 4. Push to Main

```bash
# Merge your feature branch to main
git checkout main
git merge claude/brainstorm-deployment-strategy-011CUvxnTM5fjXmxfPwZ8JxH
git push origin main
```

### 5. Monitor Deployment

```bash
# Watch GitHub Actions
# Visit: https://github.com/<your-org>/oews/actions

# Or monitor with gh CLI
gh run watch
```

### 6. Verify Deployment

```bash
# Get your app URL
APP_URL=$(az containerapp show \
  --resource-group oews-rg \
  --name oews-api \
  --query properties.configuration.ingress.fqdn -o tsv)

# Run deployment tests
API_URL="https://$APP_URL" ./tests/test-deployment.sh
```

### 7. Test Production API

```bash
# Health check
curl "https://$APP_URL/health"

# Sample query
curl -X POST "https://$APP_URL/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the average wage for software developers?", "enable_charts": true}'
```

---

## Rollback Procedure

If something goes wrong:

```bash
# List revisions
az containerapp revision list \
  --resource-group oews-rg \
  --name oews-api \
  --query "[].{Name:name, Active:properties.active, Created:properties.createdTime}" \
  -o table

# Activate previous revision
az containerapp revision activate \
  --resource-group oews-rg \
  --name oews-api \
  --revision <previous-revision-name>
```

---

## Cost Optimization Tips

1. **Auto-pause Azure SQL:** Already configured (1-hour delay)
2. **Scale to zero:** Configure min replicas to 0 during non-business hours
3. **Image caching:** GitHub Actions workflow already uses Docker layer caching
4. **LLM costs:** Implement response caching for common queries
5. **Monitor regularly:** Set up cost alerts in Azure Cost Management

---

## Success Criteria

- ✅ All tasks completed and committed
- ✅ Infrastructure provisioned in Azure
- ✅ Database schema imported successfully
- ✅ GitHub secrets configured
- ✅ CI/CD pipeline passing
- ✅ Application deployed and healthy
- ✅ Health endpoint returns 200 OK
- ✅ Query endpoint processes requests successfully
- ✅ Monitoring and logging operational

**Estimated Total Implementation Time:** 4-6 hours
**Estimated Monthly Azure Cost:** $80-165 (excluding LLM API usage)
