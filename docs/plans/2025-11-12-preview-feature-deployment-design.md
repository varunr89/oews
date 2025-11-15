# Preview Feature Deployment Pattern

## Overview

Deploy feature branches as separate containers running in parallel with production for fast, iterative testing without adding deployment tooling.

## Architecture

- **Production container:** `oews-api` (main branch) on port 8000, accessible at root path `/`
- **Preview container:** `oews-<feature-name>` (feature branch) on port 800X, accessible at `/<feature-path>/`
- **Router:** Caddy reverse proxy routes requests by path prefix
- **Data isolation:** Each container has its own data volume to prevent cross-contamination

## Implementation Steps

### 1. Add preview service to docker-compose.yml

Copy the `oews-api` service block and modify:

```yaml
oews-trace:
  image: ghcr.io/varunr89/oews:execution-traceability  # or build from branch
  container_name: oews-trace
  restart: unless-stopped
  env_file:
    - .env
  volumes:
    - ./data-trace:/app/data  # Separate data volume
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
    interval: 30s
    timeout: 3s
    retries: 3
    start_period: 10s
  logging:
    driver: "json-file"
    options:
      max-size: "10m"
      max-file: "3"
```

Key changes:
- **Container name:** Descriptive name (e.g., `oews-trace` for execution-traceability)
- **Port:** Next available port (8001, 8002, etc.)
- **Data volume:** Separate directory (e.g., `./data-trace`)
- **Image tag:** Feature branch name or build from branch if using local Dockerfile

### 2. Configure Caddy routing

Add to Caddyfile:

```
api.oews.bhavanaai.com/trace/* {
  reverse_proxy oews-trace:8001
}
```

Placement: Add before the default catch-all route for `oews-api`.

### 3. Run the containers

```bash
# Start both production and preview
docker-compose up -d oews-api oews-trace

# Or just the preview if production is already running
docker-compose up -d oews-trace

# View logs
docker-compose logs -f oews-trace

# Stop preview
docker-compose stop oews-trace

# Clean up
docker-compose down oews-trace
```

## Naming Convention

- **Container name:** `oews-<feature-branch-name>` (lowercase, hyphens instead of underscores)
- **Port:** `800X` (8001, 8002, 8003, etc. - increment for each new preview)
- **Path prefix:** `/feature-name/` (e.g., `/trace/`, `/analytics/`)
- **Data volume:** `./data-<feature-name>` (e.g., `./data-trace`)

## Testing Strategy

1. **Spin up the preview container** with the feature branch
2. **Run tests** against the `/feature-path/` endpoint
3. **Inspect logs:** `docker-compose logs oews-trace`
4. **Compare behavior** with production API at `/`
5. **Iterate** - modify code, rebuild container, restart service
6. **Tear down** when testing complete: `docker-compose down oews-trace`

## Data Volume Management

Preview containers use separate data volumes to:
- Allow parallel testing without interference
- Keep production data untouched
- Test database schema changes in isolation

**Clean data volume between test runs (optional):**
```bash
rm -rf ./data-trace
docker-compose up -d oews-trace  # Creates fresh volume
```

## Future Features

When adding new preview features, simply follow the same pattern:
1. Copy the oews-trace service block in docker-compose.yml
2. Update container name, port, feature-branch, and data volume
3. Add one routing line to Caddyfile
4. Run with `docker-compose up -d oews-<feature>`

No additional tooling or scripts needed.

## Examples

### Example: Analytics Feature on Port 8002
```yaml
oews-analytics:
  image: ghcr.io/varunr89/oews:analytics-dashboard
  container_name: oews-analytics
  ports:
    - "8002:8000"
  volumes:
    - ./data-analytics:/app/data
  # ... rest of config
```

Caddy routing:
```
api.oews.bhavanaai.com/analytics/* {
  reverse_proxy oews-analytics:8002
}
```

Access at: `https://api.oews.bhavanaai.com/analytics/`
