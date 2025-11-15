# Deploy Execution Traceability Preview Container Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deploy the execution-traceability branch as a separate container alongside production to enable parallel testing without affecting the main API.

**Architecture:** Add a new `oews-trace` service to docker-compose.yml running the traceability branch on port 8001, with Caddy routing `/trace/` traffic to it. Use separate data volume for isolation. Both containers run simultaneously.

**Tech Stack:** Docker, Docker Compose, Caddy 2, Python FastAPI

---

## Task 1: Add oews-trace service to docker-compose.yml

**Files:**
- Modify: `/Users/varunr/projects/oews/docker-compose.yml:46-end`
- Reference: Existing `oews-api` service (lines 2-21)

**Step 1: View current docker-compose.yml**

Run: `cat /Users/varunr/projects/oews/docker-compose.yml`

Expected: See the current single `oews-api` service and volumes section

**Step 2: Add oews-trace service to docker-compose.yml**

After the `oews-api` service block (after line 21) and before the `caddy` service, add:

```yaml
  oews-trace:
    image: ghcr.io/varunr89/oews:execution-traceability
    container_name: oews-trace
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data-trace:/app/data  # Separate data volume for preview
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

**Complete resulting file should look like:**

```yaml
services:
  oews-api:
    image: ghcr.io/varunr89/oews:latest
    container_name: oews-api
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/app/data
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

  oews-trace:
    image: ghcr.io/varunr89/oews:execution-traceability
    container_name: oews-trace
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data-trace:/app/data
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
        condition: service_healthy
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  caddy_data:
  caddy_config:
```

**Step 3: Validate the YAML syntax**

Run: `python3 -c "import yaml; yaml.safe_load(open('/Users/varunr/projects/oews/docker-compose.yml'))"`

Expected: No output (valid YAML)

**Step 4: Commit docker-compose.yml changes**

Run:
```bash
cd /Users/varunr/projects/oews
git add docker-compose.yml
git commit -m "feat(docker): add oews-trace preview container for execution-traceability testing"
```

Expected: `1 file changed, 20 insertions(+)`

---

## Task 2: Update Caddyfile to route /trace/ to oews-trace

**Files:**
- Modify: `/Users/varunr/projects/oews/Caddyfile` (exact line depends on file structure)

**Step 1: View current Caddyfile**

Run: `cat /Users/varunr/projects/oews/Caddyfile`

Expected: See current routing configuration with api.oews.bhavanaai.com blocks

**Step 2: Find the position to add trace routing**

The trace routing block should be added BEFORE the default catch-all for oews-api, so it takes precedence. Typically this is before the main `api.oews.bhavanaai.com` block or before any wildcard matching.

**Step 3: Add trace routing block to Caddyfile**

Add this block (adjust the position based on your Caddyfile structure):

```
api.oews.bhavanaai.com/trace/* {
  reverse_proxy oews-trace:8001 {
    # Preserve original request path minus /trace prefix
    header_up Host {http.request.host}
  }
}
```

**Step 4: Validate Caddyfile syntax**

Run: `docker run --rm -v /Users/varunr/projects/oews/Caddyfile:/etc/caddy/Caddyfile:ro caddy:2-alpine caddy validate`

Expected: `Valid configuration`

**Step 5: Commit Caddyfile changes**

Run:
```bash
cd /Users/varunr/projects/oews
git add Caddyfile
git commit -m "feat(caddy): add /trace routing for execution-traceability preview container"
```

Expected: `1 file changed, X insertions(+)`

---

## Task 3: Build and start both containers

**Step 1: Pull the execution-traceability image**

Since the execution-traceability branch may not have a published image yet, you may need to build it locally. Run:

```bash
cd /Users/varunr/projects/oews
docker build -t ghcr.io/varunr89/oews:execution-traceability -f Dockerfile .
```

Expected: Build completes successfully with message "Successfully tagged..."

**Step 2: Start both containers**

Run: `docker-compose up -d oews-api oews-trace`

Expected:
```
Creating oews-api ... done
Creating oews-trace ... done
```

**Step 3: Wait for healthchecks to pass**

Run: `docker-compose ps`

Expected: Both `oews-api` and `oews-trace` show status `Up (healthy)` after 10-15 seconds. Wait if needed and rerun.

**Step 4: Verify oews-api is responding**

Run: `curl http://localhost:8000/health`

Expected: `{"status":"ok"}` or similar health response

**Step 5: Verify oews-trace is responding**

Run: `curl http://localhost:8001/health`

Expected: `{"status":"ok"}` or similar health response

**Step 6: Verify Caddy is up**

Run: `docker-compose logs caddy | tail -5`

Expected: No error messages, should show successful startup

**Step 7: Restart Caddy to reload config**

Run: `docker-compose restart caddy`

Wait 5 seconds for Caddy to reload.

**Step 8: Test routing through Caddy**

Test the main API through Caddy (assuming you have DNS or local /etc/hosts entry):

```bash
# If you have DNS setup, use your domain
curl https://api.oews.bhavanaai.com/health

# Or test locally with direct request
curl -H "Host: api.oews.bhavanaai.com" http://localhost/health
```

Expected: Health response from main API

**Step 9: Test /trace routing through Caddy**

```bash
# Test trace endpoint
curl -H "Host: api.oews.bhavanaai.com" http://localhost/trace/health
```

Expected: Health response from trace container (should be identical to main API health, confirming it's routing correctly)

**Step 10: View logs to confirm routing**

Run:
```bash
docker-compose logs oews-api | tail -3
docker-compose logs oews-trace | tail -3
```

Expected: Both show recent access logs confirming requests are being routed correctly

---

## Task 4: Verify data isolation

**Step 1: Check data volumes exist**

Run: `ls -la /Users/varunr/projects/oews/ | grep data`

Expected:
```
drwxr-xr-x  data
drwxr-xr-x  data-trace
```

**Step 2: Verify databases are separate**

Run:
```bash
ls -la /Users/varunr/projects/oews/data/
ls -la /Users/varunr/projects/oews/data-trace/
```

Expected: Both directories exist and contain SQLite database files (should be different instances)

**Step 3: Create a test entry in main API**

Run a request to the main API to create some data (exact endpoint depends on your API):

```bash
curl -X POST -H "Host: api.oews.bhavanaai.com" http://localhost/api/test -d '{"test":"data"}'
```

(Adjust the endpoint and payload to match your API)

**Step 4: Verify data does NOT appear in trace container**

Query the same endpoint on the trace container:

```bash
curl -H "Host: api.oews.bhavanaai.com" http://localhost/trace/api/test
```

Expected: Empty result or missing data (since databases are isolated)

---

## Task 5: Final verification and commit

**Step 1: Verify both containers are healthy**

Run: `docker-compose ps`

Expected: Both `oews-api` and `oews-trace` show `Up (healthy)`

**Step 2: Create a summary of what was deployed**

Run:
```bash
docker-compose config | grep -A 10 "oews-trace"
```

Expected: Shows the oews-trace service configuration

**Step 3: Document deployment in git**

Run:
```bash
cd /Users/varunr/projects/oews
git log --oneline -3
```

Expected: Shows your recent commits for docker-compose.yml and Caddyfile changes

**Step 4: Verify all changes are committed**

Run: `git status`

Expected: `On branch execution-traceability ... nothing to commit, working tree clean`

---

## Rollback Procedure (if needed)

If something breaks and you need to roll back:

```bash
# Stop the preview container
docker-compose stop oews-trace

# Remove the container
docker-compose rm oews-trace

# Revert the docker-compose.yml and Caddyfile changes
git revert HEAD~1  # or manually edit the files

# Restart Caddy
docker-compose restart caddy
```

---

## Success Criteria

- ✅ `docker-compose ps` shows both `oews-api` and `oews-trace` as healthy
- ✅ `curl http://localhost:8000/health` returns success
- ✅ `curl http://localhost:8001/health` returns success
- ✅ `/trace/` routing through Caddy works correctly
- ✅ Main API and preview container have separate data volumes
- ✅ Both containers can run simultaneously without interference
- ✅ All changes committed to git
