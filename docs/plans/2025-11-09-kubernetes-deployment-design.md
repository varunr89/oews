# OEWS API Deployment Design - Kubernetes Personal Cloud

**Date:** 2025-11-09
**Status:** Design Complete
**Goal:** Deploy OEWS FastAPI application on personal infrastructure with internet accessibility, load balancing, and zero-touch updates

## Architecture Overview

### Infrastructure Layout

**3-Node Kubernetes Cluster:**

- **Machine 1** (x86 Linux): k3s control plane + API worker + database storage
- **Machine 2** (x86 Linux): k3s worker node + API worker
- **Raspberry Pi**: Monitoring stack (Grafana, Prometheus, Kubernetes Dashboard)

**External Services:**
- **GitHub Container Registry**: Docker image storage (free private repos)
- **Azure Key Vault**: Centralized secrets management (free tier, 10k ops/month)
- **Domain DNS**: `api.yourdomain.com` → Machine 1 public IP

### Traffic Flow

```
Internet
  ↓
api.yourdomain.com (DNS → Machine 1 public IP)
  ↓
Traefik Ingress Controller (Machine 1, port 443 HTTPS)
  ↓ (automatic Let's Encrypt SSL)
Service Load Balancer
  ↓
  ├─→ Pod 1 (Machine 1:8000) → /opt/k3s/storage/oews.db (local)
  └─→ Pod 2 (Machine 2:8000) → /opt/k3s/storage/oews.db (NFS/PV)
```

**All pods connect to read-only database via Kubernetes PersistentVolume**

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Orchestration | Kubernetes (k3s) | Industry standard, extensible to cloud, supports Pi |
| Load Balancer | Traefik (built into k3s) | Automatic HTTPS with Let's Encrypt, zero config |
| Secrets | Azure Key Vault + External Secrets Operator | Centralized management, auto-rotation, no code changes |
| Container Registry | GitHub Container Registry | Free private repos, reliable, simple authentication |
| Database | Single PersistentVolume on Machine 1 | Rarely updated data, fast local access, simple updates |
| Monitoring | Prometheus + Grafana on Raspberry Pi | Dedicated monitoring node, low overhead on API workers |

## Component Details

### 1. Kubernetes Setup (k3s)

**Why k3s over standard Kubernetes:**
- Lightweight: 512MB RAM vs 2GB+ for full k8s
- Single binary installation
- Built-in Traefik ingress controller
- Perfect for edge/personal deployments

**Installation:**

```bash
# Machine 1 (control plane)
curl -sfL https://get.k3s.io | sh -s - server \
  --disable traefik  # We'll install manually for config control

# Get join token
sudo cat /var/lib/rancher/k3s/server/node-token

# Machine 2 (worker)
curl -sfL https://get.k3s.io | K3S_URL=https://machine1-ip:6443 \
  K3S_TOKEN=<token-from-above> sh -

# Raspberry Pi (worker, ARM64)
curl -sfL https://get.k3s.io | K3S_URL=https://machine1-ip:6443 \
  K3S_TOKEN=<token-from-above> sh -
```

**Verify cluster:**
```bash
kubectl get nodes
# Expected:
# machine1    Ready   control-plane,master   1m   v1.28.x
# machine2    Ready   <none>                 30s  v1.28.x
# raspberrypi Ready   <none>                 20s  v1.28.x
```

### 2. Traefik Ingress + Let's Encrypt

**Traefik Configuration:**

Create `traefik-config.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: traefik-config
  namespace: kube-system
data:
  traefik.yaml: |
    entryPoints:
      web:
        address: ":80"
        http:
          redirections:
            entryPoint:
              to: websecure
              scheme: https
      websecure:
        address: ":443"

    certificatesResolvers:
      letsencrypt:
        acme:
          email: your-email@domain.com
          storage: /data/acme.json
          httpChallenge:
            entryPoint: web

---
apiVersion: helm.cattle.io/v1
kind: HelmChartConfig
metadata:
  name: traefik
  namespace: kube-system
spec:
  valuesContent: |-
    additionalArguments:
      - "--certificatesresolvers.letsencrypt.acme.email=your-email@domain.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/data/acme.json"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
```

**SSL certificates automatically obtained and renewed every 90 days**

### 3. External Secrets Operator + Azure Key Vault

**Why External Secrets Operator:**
- Application code stays cloud-agnostic (reads env vars, not Azure SDK)
- Secrets sync automatically to all pods
- Single source of truth in Azure Key Vault
- Rotate keys in Azure → pods restart with new values

**Installation:**

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets -n external-secrets-system --create-namespace
```

**Azure Key Vault Setup:**

```bash
# Create Key Vault
az keyvault create --name oews-secrets --resource-group your-rg --location eastus

# Add secrets
az keyvault secret set --vault-name oews-secrets --name AZURE-AI-API-KEY --value "your-key"
az keyvault secret set --vault-name oews-secrets --name OPENAI-API-KEY --value "your-key"
az keyvault secret set --vault-name oews-secrets --name DATABASE-ENV --value "prod"

# Create service principal for External Secrets Operator
az ad sp create-for-rbac --name oews-external-secrets --role "Key Vault Secrets User" --scopes /subscriptions/YOUR_SUB_ID/resourceGroups/YOUR_RG/providers/Microsoft.KeyVault/vaults/oews-secrets
```

**Kubernetes Secret Store:**

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: azure-keyvault
  namespace: default
spec:
  provider:
    azurekv:
      authType: ServicePrincipal
      vaultUrl: "https://oews-secrets.vault.azure.net"
      tenantId: "your-tenant-id"
      authSecretRef:
        clientId:
          name: azure-sp-credentials
          key: client-id
        clientSecret:
          name: azure-sp-credentials
          key: client-secret

---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: oews-secrets
  namespace: default
spec:
  refreshInterval: 1h  # Sync from Azure every hour
  secretStoreRef:
    name: azure-keyvault
    kind: SecretStore
  target:
    name: oews-api-secrets
    creationPolicy: Owner
  data:
    - secretKey: AZURE_AI_API_KEY
      remoteRef:
        key: AZURE-AI-API-KEY
    - secretKey: OPENAI_API_KEY
      remoteRef:
        key: OPENAI-API-KEY
```

**Result:** Secrets from Azure appear as Kubernetes Secret `oews-api-secrets`, mounted as environment variables in pods

### 4. Database Storage Strategy

**PersistentVolume on Machine 1:**

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: oews-database-pv
spec:
  capacity:
    storage: 3Gi
  accessModes:
    - ReadOnlyMany  # Multiple pods can read simultaneously
  hostPath:
    path: /opt/k3s/storage/oews.db
    type: File
  nodeAffinity:
    required:
      nodeSelectorTerms:
        - matchExpressions:
            - key: kubernetes.io/hostname
              operator: In
              values:
                - machine1  # Database lives on Machine 1 only

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: oews-database-pvc
spec:
  accessModes:
    - ReadOnlyMany
  resources:
    requests:
      storage: 3Gi
```

**Update Process (Quarterly BLS Data Release):**

```bash
# From your dev machine
scp data/oews.db machine1:/opt/k3s/storage/oews.db

# Restart pods to pick up new database
kubectl rollout restart deployment/oews-api
```

**Why read-only:**
- Prevents accidental writes from application bugs
- Safe for concurrent access from multiple pods
- Matches your use case (data changes quarterly, not runtime)

### 5. Application Deployment

**Dockerfile (Multi-Architecture Build):**

```dockerfile
FROM python:3.14-slim

# Install dependencies
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv pip install --system -e .

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Run as non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start FastAPI
CMD ["python", "-m", "src.main"]
```

**Build & Push Multi-Arch Images:**

```bash
# One-time setup: Create buildx builder
docker buildx create --name multiarch --use

# Build for both x86 and ARM (Raspberry Pi)
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t ghcr.io/your-username/oews-api:v1.0.0 \
  -t ghcr.io/your-username/oews-api:latest \
  --push \
  .
```

**Kubernetes Deployment:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oews-api
  labels:
    app: oews-api
spec:
  replicas: 2  # One pod per x86 machine
  selector:
    matchLabels:
      app: oews-api
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1  # Zero-downtime updates
      maxSurge: 1
  template:
    metadata:
      labels:
        app: oews-api
    spec:
      affinity:
        # Don't schedule on Raspberry Pi (monitoring only)
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: kubernetes.io/arch
                    operator: In
                    values:
                      - amd64
        # Spread pods across machines for redundancy
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: oews-api
                topologyKey: kubernetes.io/hostname

      containers:
        - name: oews-api
          image: ghcr.io/your-username/oews-api:latest
          ports:
            - containerPort: 8000
              name: http

          # Environment variables from Azure Key Vault (via External Secrets)
          envFrom:
            - secretRef:
                name: oews-api-secrets

          # Additional config
          env:
            - name: API_HOST
              value: "0.0.0.0"
            - name: API_PORT
              value: "8000"
            - name: API_RELOAD
              value: "false"
            - name: SQLITE_DB_PATH
              value: "/data/oews.db"

          # Mount database (read-only)
          volumeMounts:
            - name: database
              mountPath: /data/oews.db
              subPath: oews.db
              readOnly: true

          # Resource limits
          resources:
            requests:
              memory: "512Mi"
              cpu: "250m"
            limits:
              memory: "2Gi"
              cpu: "1000m"

          # Health checks
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 30

          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10

      volumes:
        - name: database
          persistentVolumeClaim:
            claimName: oews-database-pvc

      imagePullSecrets:
        - name: ghcr-credentials

---
apiVersion: v1
kind: Service
metadata:
  name: oews-api-service
spec:
  selector:
    app: oews-api
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: ClusterIP

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: oews-api-ingress
  annotations:
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
    traefik.ingress.kubernetes.io/router.tls.certresolver: letsencrypt
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  rules:
    - host: api.yourdomain.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: oews-api-service
                port:
                  number: 80
  tls:
    - hosts:
        - api.yourdomain.com
      secretName: oews-api-tls
```

### 6. Monitoring Stack (Raspberry Pi)

**Why dedicate Raspberry Pi to monitoring:**
- Low power consumption (5W always-on)
- Doesn't impact API performance
- Single dashboard for entire cluster
- Easy to access from local network

**Installation:**

```bash
# Add Helm repos
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Install Prometheus (metrics collection)
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set prometheus.prometheusSpec.nodeSelector."kubernetes\.io/hostname"=raspberrypi \
  --set grafana.nodeSelector."kubernetes\.io/hostname"=raspberrypi

# Install Kubernetes Dashboard
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml
```

**Access Grafana:**

```bash
# Port-forward from dev machine
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Open http://localhost:3000
# Default credentials: admin / prom-operator
```

**Pre-built Dashboards:**
- Node metrics (CPU, RAM, disk per machine)
- Pod metrics (container restarts, resource usage)
- FastAPI metrics (requests/sec, latency, errors)
- Traefik metrics (HTTP traffic, SSL cert expiry)

**Kubernetes Dashboard Access:**

```bash
# Create admin user
kubectl create serviceaccount dashboard-admin -n kubernetes-dashboard
kubectl create clusterrolebinding dashboard-admin --clusterrole=cluster-admin --serviceaccount=kubernetes-dashboard:dashboard-admin

# Get login token
kubectl -n kubernetes-dashboard create token dashboard-admin

# Port-forward
kubectl port-forward -n kubernetes-dashboard svc/kubernetes-dashboard 8443:443

# Open https://localhost:8443
```

## Deployment Workflow

### Initial Setup (One-Time)

```bash
# 1. Install k3s on all machines (see Component Details #1)

# 2. Configure kubectl on dev machine
scp machine1:/etc/rancher/k3s/k3s.yaml ~/.kube/config
# Edit ~/.kube/config: Replace 127.0.0.1 with machine1-ip

# 3. Install External Secrets Operator + configure Azure Key Vault

# 4. Create GitHub Container Registry credentials
kubectl create secret docker-registry ghcr-credentials \
  --docker-server=ghcr.io \
  --docker-username=your-github-username \
  --docker-password=YOUR_GITHUB_PAT

# 5. Deploy database PersistentVolume
kubectl apply -f k8s/database-pv.yaml

# 6. Copy initial database to Machine 1
scp data/oews.db machine1:/opt/k3s/storage/oews.db
ssh machine1 'sudo chmod 444 /opt/k3s/storage/oews.db'  # Read-only

# 7. Install monitoring stack on Raspberry Pi
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring --create-namespace
```

### Regular Deployment (Push Updates)

```bash
# From your dev machine:

# 1. Make code changes
vim src/agents/planner.py

# 2. Build multi-arch image
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t ghcr.io/username/oews-api:v1.2.3 \
  -t ghcr.io/username/oews-api:latest \
  --push \
  .

# 3. Update deployment (zero-downtime rolling update)
kubectl set image deployment/oews-api oews-api=ghcr.io/username/oews-api:v1.2.3

# Watch rollout status
kubectl rollout status deployment/oews-api

# 4. Verify
curl https://api.yourdomain.com/health
```

**Rollback if needed:**
```bash
kubectl rollout undo deployment/oews-api
```

### Database Updates (Quarterly)

```bash
# 1. Update database on Machine 1
scp data/oews.db machine1:/opt/k3s/storage/oews.db

# 2. Set read-only permissions
ssh machine1 'sudo chmod 444 /opt/k3s/storage/oews.db'

# 3. Restart pods to pick up new database
kubectl rollout restart deployment/oews-api

# 4. Verify
curl -X POST https://api.yourdomain.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the latest salary statistics?", "enable_charts": false}'
```

### Secrets Rotation

```bash
# 1. Update secret in Azure Key Vault
az keyvault secret set --vault-name oews-secrets --name AZURE-AI-API-KEY --value "new-key-value"

# 2. Wait for External Secrets Operator to sync (up to 1 hour, or force)
kubectl annotate externalsecret oews-secrets force-sync=$(date +%s) --overwrite

# 3. Restart pods to pick up new secret
kubectl rollout restart deployment/oews-api
```

## Networking & DNS Configuration

### Machine 1 Firewall Rules

```bash
# Allow HTTPS (Traefik ingress)
sudo ufw allow 443/tcp

# Allow HTTP (Let's Encrypt challenge, redirects to HTTPS)
sudo ufw allow 80/tcp

# Allow k3s API (for kubectl from dev machine)
sudo ufw allow 6443/tcp

# Allow k3s internal networking
sudo ufw allow from <machine2-ip> to any port 10250  # kubelet
sudo ufw allow from <raspberrypi-ip> to any port 10250
```

### DNS Configuration

**A Record:**
```
api.yourdomain.com  →  Machine 1 Public IP
TTL: 300 seconds (5 minutes for easy troubleshooting)
```

**If using dynamic IP (home ISP):**
- Use dynamic DNS service (DuckDNS, No-IP, Cloudflare DDNS)
- Run ddclient or similar on Machine 1 to update IP changes

### Port Forwarding (Home Router)

If machines are behind NAT:
```
External Port 443 → Machine 1 IP:443 (HTTPS)
External Port 80  → Machine 1 IP:80  (HTTP for Let's Encrypt)
```

## Scaling & Future Extensions

### Adding Cloud Worker Nodes

```bash
# On AWS EC2 / Azure VM / GCP Compute
curl -sfL https://get.k3s.io | K3S_URL=https://api.yourdomain.com:6443 \
  K3S_TOKEN=<your-token> sh -

# Pod automatically schedules on new node
kubectl scale deployment/oews-api --replicas=3
```

**Considerations:**
- Database latency (cloud → home over internet)
- Solution: Migrate to cloud-hosted PostgreSQL when adding cloud nodes

### Migrating to Managed Kubernetes

When you outgrow self-hosted:

```bash
# Export manifests
kubectl get all -o yaml > backup.yaml

# Deploy to AKS/EKS/GKE
kubectl apply -f backup.yaml

# Point DNS to cloud load balancer
api.yourdomain.com → Azure Load Balancer IP
```

**Your YAML configs work unchanged on managed k8s**

### Adding More Applications

```bash
# Deploy new app to same cluster
kubectl apply -f new-app-deployment.yaml

# Reuse existing infrastructure:
# - Same External Secrets Operator (Azure Key Vault)
# - Same Traefik ingress (auto HTTPS for new-app.yourdomain.com)
# - Same monitoring (Grafana dashboards for new app)
```

## Monitoring & Observability

### kubectl Commands (Daily Operations)

```bash
# Check cluster health
kubectl get nodes
kubectl top nodes  # CPU/RAM usage

# Check pods
kubectl get pods -o wide  # See which machine each pod is on
kubectl logs deployment/oews-api --tail=100 -f  # Live logs

# Check pod restarts (should be 0)
kubectl get pods --field-selector=status.phase=Running

# Resource usage
kubectl top pods

# Ingress status
kubectl get ingress
kubectl describe ingress oews-api-ingress  # See SSL cert status
```

### Grafana Dashboards

**Access:** `kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80`

**Key Metrics to Monitor:**
- **Node CPU/Memory:** Should stay under 70% average
- **Pod Restarts:** Should be 0 (restarts indicate crashes)
- **HTTP Request Rate:** Requests/second to API
- **HTTP Latency:** P95 should be <2 seconds
- **SSL Certificate Expiry:** Should renew automatically 30 days before expiry

### k9s (Terminal Dashboard)

```bash
# Install on dev machine
brew install k9s  # macOS
# or sudo snap install k9s  # Linux

# Run
k9s

# Keyboard shortcuts:
# :pods    → View pods
# :nodes   → View nodes
# :deploy  → View deployments
# l        → View logs
# d        → Describe resource
# ctrl-d   → Delete resource
```

### External Uptime Monitoring

**UptimeRobot (Free Tier):**
1. Sign up at uptimerobot.com
2. Create HTTP(s) monitor: `https://api.yourdomain.com/health`
3. Check interval: 5 minutes
4. Alert contacts: Email/SMS

**Healthchecks.io (Alternative):**
- Ping endpoint every minute
- Alert if down >5 minutes

## Cost Summary

| Component | Provider | Monthly Cost |
|-----------|----------|--------------|
| k3s Cluster | Self-hosted | $0 (electricity ~$10-15) |
| GitHub Container Registry | GitHub | $0 (free private repos) |
| Azure Key Vault | Azure | $0 (free tier, <10k ops) |
| Domain Name | Registrar | ~$12/year (~$1/month) |
| Let's Encrypt SSL | Let's Encrypt | $0 |
| Monitoring | Self-hosted | $0 |
| External Uptime Monitoring | UptimeRobot | $0 (free tier) |
| **Total** | | **~$1-2/month** |

**Electricity estimate:**
- Machine 1 (x86): ~50W × 730hr = 36.5 kWh/month
- Machine 2 (x86): ~50W × 730hr = 36.5 kWh/month
- Raspberry Pi: ~5W × 730hr = 3.65 kWh/month
- Total: ~77 kWh/month × $0.13/kWh = ~$10/month

**Compare to Cloud:**
- AWS EKS: $73/month (control plane) + $30-60/month (2× t3.medium workers) = $100-130/month
- Your setup: $10-15/month electricity + hardware you already own

## Security Considerations

### SSL/TLS
- Automatic HTTPS via Let's Encrypt (A+ rating)
- Certificates auto-renew every 60 days
- HTTP → HTTPS redirect enforced

### Secrets Management
- API keys stored in Azure Key Vault (encrypted at rest, in transit)
- Never committed to git
- Rotatable without pod rebuilds
- Audit logs in Azure

### Network Security
- Firewall rules: Only ports 80, 443, 6443 exposed
- Internal k8s networking encrypted (TLS)
- Database read-only (prevents accidental writes)

### Container Security
- Non-root user in containers
- Health checks enforce liveness
- Resource limits prevent DoS

### Application Security
- CORS restricted to your frontend domains
- Parameterized SQL queries (no SQL injection)
- API rate limiting (add Traefik middleware if needed)

## Disaster Recovery

### Backup Strategy

**What to backup:**
1. Database: `/opt/k3s/storage/oews.db` (2.2GB, quarterly updates)
2. Kubernetes manifests: Git repository (version controlled)
3. Azure Key Vault: Managed by Azure (geo-redundant)

**Backup script (run monthly):**

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y-%m-%d)
BACKUP_DIR="/mnt/backup/oews"

# Backup database
scp machine1:/opt/k3s/storage/oews.db $BACKUP_DIR/oews-$DATE.db

# Backup k8s manifests (already in git, but snapshot current state)
kubectl get all,pv,pvc,ingress,secrets -o yaml > $BACKUP_DIR/k8s-state-$DATE.yaml

# Keep last 6 backups (6 months for quarterly data updates)
ls -t $BACKUP_DIR/oews-*.db | tail -n +7 | xargs rm -f
```

### Recovery Procedures

**Scenario 1: Single pod crash**
- Auto-recovered by Kubernetes (restarts pod)
- No action needed

**Scenario 2: Machine 1 hardware failure**
- Traffic fails (Machine 1 hosts ingress + database)
- Recovery time: 1-2 hours

**Steps:**
```bash
# 1. Restore database to new machine
scp /mnt/backup/oews-latest.db newmachine:/opt/k3s/storage/oews.db

# 2. Update DNS
api.yourdomain.com → New Machine IP

# 3. Reinstall k3s control plane on new machine
curl -sfL https://get.k3s.io | sh -

# 4. Redeploy manifests
kubectl apply -f k8s/
```

**Scenario 3: Machine 2 failure**
- No downtime (Machine 1 handles all traffic)
- Replace machine when convenient

**Scenario 4: Complete cluster loss**
- Rebuild cluster from scratch (1-2 hours)
- Database restored from backup
- Manifests reapplied from git

**RTO/RPO:**
- Recovery Time Objective: 2 hours
- Recovery Point Objective: Last quarterly BLS release (acceptable for read-only data)

## Testing Plan

Before deploying to production:

### 1. Local Testing
```bash
# Build image
docker build -t oews-api:test .

# Run locally
docker run -p 8000:8000 --env-file .env oews-api:test

# Test endpoints
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/v1/query -H "Content-Type: application/json" -d '{"query": "test"}'
```

### 2. Single-Node k3s Testing
```bash
# Install k3s on Machine 1 only
# Deploy application
# Verify ingress, SSL, database access
```

### 3. Multi-Node Testing
```bash
# Add Machine 2
# Verify pod scheduling across nodes
# Test failover: Stop pod on Machine 1, verify traffic routes to Machine 2
```

### 4. Load Testing
```bash
# Use k6 or Apache Bench
k6 run --vus 10 --duration 30s load-test.js

# Monitor with Grafana during test
# Verify no pod restarts, latency stays acceptable
```

### 5. Database Update Testing
```bash
# Copy test database
# Restart pods
# Verify queries return expected results
```

## Implementation Checklist

### Phase 1: Infrastructure Setup
- [ ] Install k3s on Machine 1 (control plane)
- [ ] Install k3s on Machine 2 (worker)
- [ ] Install k3s on Raspberry Pi (worker)
- [ ] Configure kubectl on dev machine
- [ ] Verify cluster connectivity
- [ ] Configure firewall rules on Machine 1
- [ ] Set up DNS A record for api.yourdomain.com
- [ ] Configure router port forwarding (if needed)

### Phase 2: Core Services
- [ ] Install Traefik with Let's Encrypt config
- [ ] Verify HTTPS certificate generation
- [ ] Install External Secrets Operator
- [ ] Create Azure Key Vault
- [ ] Add secrets to Azure Key Vault
- [ ] Configure External Secrets sync
- [ ] Create GitHub Container Registry credentials
- [ ] Test secret injection to test pod

### Phase 3: Database Setup
- [ ] Create database PersistentVolume YAML
- [ ] Copy oews.db to Machine 1:/opt/k3s/storage/
- [ ] Set read-only permissions (chmod 444)
- [ ] Apply PV and PVC manifests
- [ ] Verify volume mounts correctly

### Phase 4: Application Deployment
- [ ] Create Dockerfile with multi-arch support
- [ ] Build and push image to GHCR
- [ ] Create Deployment YAML
- [ ] Create Service YAML
- [ ] Create Ingress YAML
- [ ] Apply manifests to cluster
- [ ] Verify pods start successfully
- [ ] Test health endpoint via HTTPS

### Phase 5: Monitoring
- [ ] Install Prometheus on Raspberry Pi
- [ ] Install Grafana on Raspberry Pi
- [ ] Configure Grafana dashboards
- [ ] Install Kubernetes Dashboard
- [ ] Create dashboard admin user
- [ ] Set up external uptime monitoring (UptimeRobot)
- [ ] Test alerts (simulate pod failure)

### Phase 6: Testing & Validation
- [ ] Run load tests
- [ ] Test rolling updates (deploy new version)
- [ ] Test rollback procedure
- [ ] Test database update procedure
- [ ] Test secret rotation
- [ ] Simulate Machine 2 failure (verify failover)
- [ ] Document actual recovery time

### Phase 7: Documentation & Runbooks
- [ ] Document deployment procedure
- [ ] Create runbook for database updates
- [ ] Create runbook for adding new nodes
- [ ] Create runbook for disaster recovery
- [ ] Share frontend developers API endpoint

## Next Steps

1. **Start with Phase 1:** Set up k3s cluster on your 3 machines
2. **Test incrementally:** Verify each phase before proceeding
3. **Document as you go:** Note any machine-specific details (IPs, hostnames)
4. **Consider creating an implementation plan:** Use `/superpowers:write-plan` for step-by-step tasks

## Questions to Resolve Before Implementation

- [ ] What is Machine 1's public IP address?
- [ ] What is your domain name?
- [ ] What is your GitHub username (for GHCR)?
- [ ] Do you have Azure CLI access for Key Vault setup?
- [ ] Are machines on same local network or different locations?
- [ ] What Linux distribution on machines? (affects k3s install)
- [ ] What Raspberry Pi model/RAM? (affects resource limits)

---

**This design provides:**
- ✅ Internet-accessible API via HTTPS
- ✅ Zero-touch deployments from dev machine
- ✅ Load balancing across 2 workers
- ✅ Centralized secrets management
- ✅ Monitoring and observability
- ✅ Future extensibility (add cloud nodes, migrate to managed k8s)
- ✅ Low cost (~$10-15/month electricity vs $100+ cloud)
- ✅ Production-ready security (HTTPS, secret rotation, read-only DB)
