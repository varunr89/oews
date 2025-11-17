# Production Deployment: Execution Traceability Feature

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Merge execution-traceability branch to main, trigger production container build, deploy to production server, and validate end-to-end functionality.

**Architecture:** This plan handles the full production deployment lifecycle: pre-merge validation, merge execution, GitHub Actions CI/CD trigger, Docker container deployment, network configuration, and comprehensive API testing to verify execution traces are exposed correctly.

**Tech Stack:** Git, GitHub Actions, Docker, FastAPI, pytest, curl

---

## Pre-Deployment Validation

### Task 1: Commit Pending Changes

**Files:**
- Modify: `.gitignore`

**Step 1: Review changes**

Run: `git diff .gitignore`
Expected: See what was added to gitignore

**Step 2: Stage and commit changes**

```bash
git add .gitignore
git commit -m "chore: update .gitignore"
```

Expected: Clean working directory

**Step 3: Verify clean state**

Run: `git status`
Expected: "nothing to commit, working tree clean"

---

### Task 2: Run Full Test Suite Locally

**Files:**
- Test: All test files in `tests/`

**Step 1: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS (no failures, no errors)

**Step 2: Check for test coverage gaps**

Run: `pytest tests/test_trace_extraction.py tests/test_trace_utils.py tests/test_api_endpoints.py -v`
Expected: Execution traceability tests all PASS

**Step 3: Verify test output**

Expected output should include:
- `test_api_endpoints.py::test_query_endpoint_returns_execution_details` - PASS
- `test_trace_extraction.py` - All tests PASS
- `test_trace_utils.py` - All tests PASS

If any tests FAIL, STOP and fix before proceeding.

---

### Task 3: Verify Docker Build Locally

**Files:**
- Read: `Dockerfile`

**Step 1: Build Docker image locally**

Run: `docker build -t oews-test:local .`
Expected: Build completes successfully without errors

**Step 2: Run container locally**

```bash
docker run -d --name oews-test-local -p 8001:8000 --env-file .env oews-test:local
```

Expected: Container starts successfully

**Step 3: Test health endpoint**

Run: `curl http://localhost:8001/api/v1/health`
Expected: `{"status": "healthy"}`

**Step 4: Clean up test container**

```bash
docker stop oews-test-local
docker rm oews-test-local
```

---

## Merge to Main

### Task 4: Merge execution-traceability to main

**Files:**
- Branch: `execution-traceability` → `main`

**Step 1: Switch to main branch**

Run: `git checkout main`
Expected: Switch to main branch successfully

**Step 2: Pull latest main**

Run: `git pull origin main`
Expected: Main is up to date or fast-forwards

**Step 3: Merge execution-traceability**

Run: `git merge execution-traceability --no-ff -m "feat: merge execution traceability feature to production"`
Expected: Merge completes successfully

**Step 4: Push to origin**

Run: `git push origin main`
Expected: Push successful, triggers GitHub Actions

---

## GitHub Actions Validation

### Task 5: Monitor GitHub Actions Build

**Files:**
- Workflow: `.github/workflows/deploy.yml`

**Step 1: Check build status**

Run: `gh run list --branch main --limit 1`
Expected: See latest workflow run for main branch

**Step 2: Monitor build progress**

Run: `gh run watch`
Expected: Build completes successfully

**Step 3: Verify build output**

Run: `gh run view --log`

Expected output should include:
- ✅ Docker image built and pushed successfully
- 📦 Images:
  - `ghcr.io/varunr89/oews:latest`
  - `ghcr.io/varunr89/oews:main-<sha>`

If build FAILS, check logs and fix issues before proceeding.

**Step 4: Verify image tags**

Expected image tags created:
- `latest` (main production tag)
- `main-<git-sha>` (versioned backup tag)

---

## Production Deployment

### Task 6: SSH to Production Server

**Files:**
- Server: `100.107.15.52`

**Step 1: Connect to server**

Run: `ssh varun@100.107.15.52`
Expected: SSH connection successful

**Step 2: Navigate to project directory**

Run: `cd /home/varun/projects/oews`
Expected: Directory exists

**Step 3: Verify environment file exists**

Run: `ls -lh .env`
Expected: `.env` file present with correct permissions

**Step 4: Verify database file exists**

Run: `ls -lh data/oews.db`
Expected: `data/oews.db` file present (read-only mount)

---

### Task 7: Pull Latest Production Image

**Step 1: Pull latest Docker image**

Run: `docker pull ghcr.io/varunr89/oews:latest`

Expected:
- Download layers
- "Status: Downloaded newer image for ghcr.io/varunr89/oews:latest"

**Step 2: Verify image downloaded**

Run: `docker images | grep oews`
Expected: See `ghcr.io/varunr89/oews` with `latest` tag and recent timestamp

---

### Task 8: Stop and Remove Old Production Container

**Step 1: Check if old container is running**

Run: `docker ps | grep oews`
Expected: See old production container (if any)

**Step 2: Stop old container**

Run: `docker stop oews-prod`
Expected: Container stopped gracefully

**Step 3: Remove old container**

Run: `docker rm oews-prod`
Expected: Container removed

**Step 4: Verify cleanup**

Run: `docker ps -a | grep oews-prod`
Expected: No output (container removed)

---

### Task 9: Start New Production Container

**Step 1: Run new production container**

```bash
docker run -d \
  --name oews-prod \
  -p 8000:8000 \
  -v /home/varun/projects/oews/data:/app/data:ro \
  --env-file /home/varun/projects/oews/.env \
  ghcr.io/varunr89/oews:latest
```

Expected: Container ID printed, container starts successfully

**Step 2: Verify container is running**

Run: `docker ps | grep oews-prod`
Expected: Container running, shows port mapping `8000->8000`

**Step 3: Check container logs**

Run: `docker logs oews-prod --tail 50`

Expected output should include:
- FastAPI startup messages
- "Application startup complete"
- "Uvicorn running on http://0.0.0.0:8000"
- No errors or exceptions

---

### Task 10: Connect Container to Caddy Network

**Step 1: Verify Caddy network exists**

Run: `docker network ls | grep oews_default`
Expected: `oews_default` network exists

**Step 2: Connect container to network**

Run: `docker network connect oews_default oews-prod`
Expected: Connection successful (no output)

**Step 3: Verify network connection**

Run: `docker inspect oews-prod | grep -A 10 Networks`

Expected output should show:
- Both `bridge` and `oews_default` networks
- IP addresses assigned for both networks

If `oews_default` is NOT present:
- This is CRITICAL - Caddy cannot reach the container
- Repeat Step 2 and verify again

---

## Production Validation

### Task 11: Test Health Endpoint

**Step 1: Test health from server**

Run: `curl http://localhost:8000/api/v1/health`
Expected: `{"status": "healthy"}`

**Step 2: Test health via Caddy (from server)**

Run: `curl https://api.oews.bhavanaai.com/api/v1/health`
Expected: `{"status": "healthy"}`

If you get 502 Bad Gateway:
- STOP - container not on correct network
- Go back to Task 10 and verify network connection

**Step 3: Test health from local machine**

Run (from local machine): `curl https://api.oews.bhavanaai.com/api/v1/health`
Expected: `{"status": "healthy"}`

---

### Task 12: Test Models Endpoint

**Step 1: Test models endpoint**

Run: `curl https://api.oews.bhavanaai.com/api/v1/models`

Expected JSON response with available models:
```json
{
  "models": {
    "gpt-4o": {...},
    "deepseek-v3": {...},
    ...
  }
}
```

**Step 2: Verify model registry loaded**

Expected: No errors, models list returned

---

### Task 13: Test Query Endpoint with Execution Traces

**Step 1: Test simple query**

```bash
curl -X POST https://api.oews.bhavanaai.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the average software developer salary in Seattle?",
    "enable_charts": false
  }'
```

Expected response structure:
```json
{
  "answer": "...",
  "data_sources": [
    {
      "step": 1,
      "agent": "planner",
      "type": "planning",
      "plan": {...},
      "reasoning_model": "..."
    },
    {
      "step": 2,
      "agent": "cortex",
      "type": "oews_database",
      "sql": "SELECT ...",
      "row_count": N,
      "sample_data": [...]
    }
  ]
}
```

**Step 2: Verify execution traces present**

Check response contains:
- ✅ `data_sources` array is NOT empty
- ✅ At least one trace with `"agent": "planner"` and `"type": "planning"`
- ✅ At least one trace with `"agent": "cortex"` and `"type": "oews_database"`
- ✅ SQL trace includes `sql`, `row_count`, `sample_data`

If `data_sources` is empty or missing:
- CRITICAL BUG - execution tracing not working
- Check container logs for errors
- Review response_formatter.py trace extraction

---

### Task 14: Test Query with Charts and Full Execution Details

**Step 1: Test complex query with charts**

```bash
curl -X POST https://api.oews.bhavanaai.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Compare software developer salaries in Seattle vs San Francisco with charts",
    "enable_charts": true
  }' | jq .
```

**Step 2: Verify response structure**

Expected response includes:
```json
{
  "answer": "...",
  "charts": [...],
  "data_sources": [
    {
      "step": 1,
      "agent": "planner",
      "type": "planning",
      "plan": {...}
    },
    {
      "step": 2,
      "agent": "cortex",
      "type": "oews_database",
      "sql": "...",
      "row_count": N
    },
    {
      "step": 3,
      "agent": "chart_generator",
      "type": "chart_generation",
      "implementation_model": "..."
    }
  ]
}
```

**Step 3: Validate all execution traces**

Verify:
- ✅ Planning trace includes full plan with steps
- ✅ SQL trace includes actual query and results
- ✅ Chart generation trace present (if charts enabled)
- ✅ All traces have correct `step` numbering (sequential)
- ✅ All traces have `agent` and `type` fields

---

### Task 15: Test Model Override Functionality

**Step 1: Test with reasoning model override**

```bash
curl -X POST https://api.oews.bhavanaai.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the top 5 highest paying occupations?",
    "reasoning_model": "deepseek-r1",
    "enable_charts": false
  }' | jq '.data_sources[] | select(.agent == "planner") | .reasoning_model'
```

Expected: `"deepseek-r1"`

**Step 2: Test with implementation model override**

```bash
curl -X POST https://api.oews.bhavanaai.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Compare software developer salaries across top 10 tech cities with charts",
    "implementation_model": "gpt-4o",
    "enable_charts": true
  }' | jq '.data_sources[] | select(.type == "chart_generation") | .implementation_model'
```

Expected: `"gpt-4o"`

---

### Task 16: Test Error Handling

**Step 1: Test invalid query**

```bash
curl -X POST https://api.oews.bhavanaai.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "ab"
  }'
```

Expected: 422 Unprocessable Entity (query too short)

**Step 2: Test invalid model override**

```bash
curl -X POST https://api.oews.bhavanaai.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are software salaries?",
    "reasoning_model": "invalid-model"
  }'
```

Expected: 422 Unprocessable Entity with error about invalid model

---

## Post-Deployment Verification

### Task 17: Run Integration Tests Against Production

**Files:**
- Test: `tests/test_api_endpoints.py`

**Step 1: Set production endpoint**

Run (from local machine):
```bash
export API_BASE_URL=https://api.oews.bhavanaai.com
```

**Step 2: Run API tests against production**

Run: `pytest tests/test_api_endpoints.py -v --tb=short`

Expected: All tests PASS

If tests fail:
- Check which specific test failed
- Review container logs on server
- Check execution trace extraction logic

---

### Task 18: Monitor Production Logs

**Step 1: Tail production logs**

Run (on server): `docker logs oews-prod -f --tail 100`

**Step 2: Make a few test queries**

From local machine, execute 3-5 varied queries

**Step 3: Verify log output**

Expected in logs:
- ✅ No Python exceptions or stack traces
- ✅ Request logging shows successful queries
- ✅ No database connection errors
- ✅ No model loading errors

**Step 4: Check for warnings**

Acceptable warnings:
- Azure SQL connection failures (fallback to SQLite)

Unacceptable errors:
- Stack traces
- 500 Internal Server Errors
- Database file not found
- Missing environment variables

---

### Task 19: Performance Validation

**Step 1: Test query response time**

```bash
time curl -X POST https://api.oews.bhavanaai.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are software developer salaries in Seattle?",
    "enable_charts": false
  }'
```

Expected: Response in < 30 seconds (depends on LLM API)

**Step 2: Test concurrent requests**

Run 3 queries in parallel:
```bash
for i in {1..3}; do
  curl -X POST https://api.oews.bhavanaai.com/api/v1/query \
    -H "Content-Type: application/json" \
    -d '{"query": "Test query '$i'", "enable_charts": false}' &
done
wait
```

Expected: All complete successfully, no timeouts

---

## Cleanup and Documentation

### Task 20: Clean Up Preview Branch Artifacts

**Step 1: Remove execution-traceability preview container (if exists)**

Run (on server):
```bash
docker stop oews-trace 2>/dev/null || true
docker rm oews-trace 2>/dev/null || true
```

**Step 2: Verify only production container running**

Run: `docker ps | grep oews`
Expected: Only `oews-prod` container running

---

### Task 21: Update Production Documentation

**Files:**
- Update: `docs/PRODUCTION_READINESS.md`

**Step 1: Read current production readiness**

Run: `cat docs/PRODUCTION_READINESS.md | grep "Overall Score"`
Expected: Current score shown

**Step 2: Update score to 10/10**

Update the following sections in `docs/PRODUCTION_READINESS.md`:

```markdown
**Overall Score: 10/10** ✅ Production Ready

## 8. Execution Traceability ✅ COMPLETE

- ✅ Full execution traces implemented
- ✅ Deployed to production
- ✅ All tests passing
- ✅ API endpoints validated
- ✅ Model overrides working
- ✅ Error handling verified
```

**Step 3: Commit documentation**

```bash
git add docs/PRODUCTION_READINESS.md
git commit -m "docs: update production readiness to 10/10 after deployment"
git push origin main
```

---

### Task 22: Create Deployment Success Summary

**Step 1: Generate deployment summary**

Create file: `docs/deployments/2025-11-15-execution-traceability-production.md`

```markdown
# Production Deployment: Execution Traceability Feature

**Date:** 2025-11-15
**Branch:** execution-traceability → main
**Status:** ✅ SUCCESS

## Deployment Summary

- **Build:** GitHub Actions successful
- **Container:** ghcr.io/varunr89/oews:latest
- **Endpoint:** https://api.oews.bhavanaai.com/api/v1/
- **Server:** 100.107.15.52 (oews-prod container)

## Features Deployed

1. Execution traceability for all agents (planner, cortex, web research, chart generator)
2. Model override support (reasoning_model, implementation_model)
3. Enhanced API response with data_sources field
4. SQL validation and security improvements
5. Comprehensive test coverage

## Validation Results

- ✅ All tests passing
- ✅ Health endpoint: OK
- ✅ Models endpoint: OK
- ✅ Query endpoint with execution traces: OK
- ✅ Chart generation: OK
- ✅ Model overrides: OK
- ✅ Error handling: OK

## Performance

- Query response time: < 30s
- Concurrent requests: Handled successfully
- No errors in production logs

## Next Steps

- Monitor production logs for 24 hours
- Gather user feedback on execution traces
- Plan next feature enhancements
```

**Step 2: Commit deployment record**

```bash
git add docs/deployments/2025-11-15-execution-traceability-production.md
git commit -m "docs: add deployment record for execution traceability feature"
git push origin main
```

---

## Rollback Plan (If Needed)

### Task 23: Emergency Rollback Procedure

**Only execute if critical issues found in production**

**Step 1: Identify previous working image**

Run: `docker images | grep oews`
Find previous tag (e.g., `main-<previous-sha>`)

**Step 2: Stop failing container**

```bash
docker stop oews-prod
docker rm oews-prod
```

**Step 3: Deploy previous version**

```bash
docker run -d \
  --name oews-prod \
  -p 8000:8000 \
  -v /home/varun/projects/oews/data:/app/data:ro \
  --env-file /home/varun/projects/oews/.env \
  ghcr.io/varunr89/oews:main-<previous-sha>

docker network connect oews_default oews-prod
```

**Step 4: Verify rollback**

Run: `curl https://api.oews.bhavanaai.com/api/v1/health`
Expected: `{"status": "healthy"}`

**Step 5: Revert main branch**

```bash
git revert HEAD~1
git push origin main
```

---

## Success Criteria

✅ All tasks completed successfully
✅ GitHub Actions build passed
✅ Production container running on correct network
✅ Health endpoint returns healthy status
✅ Query endpoint returns execution traces
✅ Charts generation working
✅ Model overrides functional
✅ All tests passing against production
✅ No errors in production logs
✅ Documentation updated

**Deployment is complete when all success criteria are met.**
