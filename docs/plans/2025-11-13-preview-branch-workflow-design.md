# Preview Branch Auto-Build Workflow Design

## Overview

Enable automatic Docker image building for feature/preview branches to maximize development velocity. Developers create branches, push code, and images are automatically built and tagged for deployment testing.

## Architecture

**Git Workflow:**
- `main` branch: Production code, always tested and deployable
- `preview/*` branches: Feature branches that auto-build (e.g., `preview/execution-traceability`, `preview/analytics`)
- Other branches: No auto-build (keep CI costs low)

**Image Tagging Strategy:**
- `main` branch builds → tagged as `latest` and `main-<git-sha>`
- `preview/*` branches → tagged as `preview-<branch-name>` and `<branch-name>-<git-sha>`
- Examples:
  - `execution-traceability` → `execution-traceability-a1b2c3d`
  - `preview/analytics` → `preview-analytics-x9y8z7w`

**Deployment Pattern:**
- Each preview branch image gets its own container in docker-compose.yml
- Caddy routes `/<preview-name>/` to that container
- Multiple previews can run simultaneously for comparison testing

## Special Cases

**Execution Traceability Branch:**
- Currently exists as `execution-traceability` (not following `preview/*` pattern)
- Decision: Keep as-is to avoid disruption
- Workflow update will build this branch explicitly by name
- Future branches should follow `preview/*` pattern

## CI/CD Implementation

**Updated GitHub Actions Workflow (`deploy.yml`):**
- Build triggers:
  - Push to `main` → tag as `latest`
  - Push to `execution-traceability` → tag as `execution-traceability`
  - Push to `preview/*` → tag as `preview-<branch-name>`
  - Manual `workflow_dispatch` on any branch

**Image Registry:**
- All images published to GitHub Container Registry (ghcr.io)
- Accessible to any service with pull permissions

## Developer Workflow

**For new preview features:**

```bash
# 1. Create feature branch following the pattern
git checkout -b preview/new-feature

# 2. Make changes
git add .
git commit -m "feat: add new feature"

# 3. Push to GitHub
git push -u origin preview/new-feature

# 4. GitHub Actions automatically:
#    - Builds Docker image
#    - Tags as preview-new-feature
#    - Publishes to ghcr.io

# 5. Add to docker-compose.yml and Caddyfile on server
# 6. Deploy: docker-compose up -d oews-preview-new-feature

# 7. Test at https://api.oews.bhavanaai.com/new-feature/

# 8. When ready: merge to main
git checkout main
git pull
git merge preview/new-feature
git push
```

## Success Criteria

- ✅ Push to `main` builds image tagged `latest`
- ✅ Push to `execution-traceability` builds image tagged `execution-traceability`
- ✅ Push to `preview/*` branches builds images tagged `preview-<branch-name>`
- ✅ Images automatically published to ghcr.io
- ✅ Images available for pulling in docker-compose.yml
- ✅ Developers can start new preview branches without manual workflow triggers
- ✅ No additional configuration needed per branch

## Cost Considerations

- **Build frequency:** Only branches with pushes trigger builds (efficient)
- **Storage:** Old branch images kept in registry; can be cleaned periodically with GitHub cleanup policies
- **Minutes:** GitHub provides 2000 free CI/CD minutes/month; typical builds take 3-5 minutes

## Future Enhancements

- Automated cleanup of old preview images after branch deletion
- Slack notifications when preview images build successfully
- Automated PR comments with preview deployment instructions
