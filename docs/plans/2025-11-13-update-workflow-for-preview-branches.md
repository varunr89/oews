# Update GitHub Actions Workflow for Preview Branches Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Update the GitHub Actions workflow to automatically build Docker images for `main`, `execution-traceability`, and `preview/*` branches with proper tagging.

**Architecture:** Modify the existing deploy.yml workflow to use conditional branch detection and dynamic image tagging that changes the tag based on which branch is being built.

**Tech Stack:** GitHub Actions, Docker Buildx, GitHub Container Registry

---

## Task 1: Update GitHub Actions workflow to support preview branches

**Files:**
- Modify: `/Users/varunr/projects/oews/.github/workflows/deploy.yml`

**Step 1: View current workflow**

Run: `cat /Users/varunr/projects/oews/.github/workflows/deploy.yml`

Expected: See current workflow that only builds on push to `main`

**Step 2: Replace the entire deploy.yml with updated version**

Replace the entire file with this updated workflow:

```yaml
name: Build Docker Image

on:
  push:
    branches: [main, execution-traceability, 'preview/**']
  schedule:
    - cron: '0 2 * * 0'  # Weekly rebuild (Sunday 2am UTC) for base image security patches
  workflow_dispatch:  # Manual trigger option

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

# Prevent overlapping deployments
concurrency:
  group: deploy-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout code
        uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@9780b0c442fbb1117ed29e0efdff1e18412f7567 # v3.3.0
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@c47758b77c9736f4b2ef4073d4d51994fabfe349 # v3.7.1

      - name: Determine image tag
        id: tag
        run: |
          if [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
            TAG="latest"
            BRANCH_TAG="main-${{ github.sha }}"
          elif [[ "${{ github.ref }}" == "refs/heads/execution-traceability" ]]; then
            TAG="execution-traceability"
            BRANCH_TAG="execution-traceability-${{ github.sha }}"
          elif [[ "${{ github.ref }}" =~ ^refs/heads/preview/ ]]; then
            # Extract branch name from refs/heads/preview/feature-name -> feature-name
            BRANCH_NAME="${{ github.ref }}"
            BRANCH_NAME="${BRANCH_NAME#refs/heads/preview/}"
            TAG="preview-${BRANCH_NAME}"
            BRANCH_TAG="preview-${BRANCH_NAME}-${{ github.sha }}"
          else
            # For other branches (manual workflow_dispatch), use branch name
            BRANCH_NAME="${{ github.ref_name }}"
            TAG="${BRANCH_NAME}"
            BRANCH_TAG="${BRANCH_NAME}-${{ github.sha }}"
          fi

          echo "TAG=${TAG}" >> $GITHUB_OUTPUT
          echo "BRANCH_TAG=${BRANCH_TAG}" >> $GITHUB_OUTPUT

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@8e5442c4ef9f78752691e2d8f8d19755c6f78e81 # v5.5.1
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=raw,value=${{ steps.tag.outputs.TAG }}
            type=raw,value=${{ steps.tag.outputs.BRANCH_TAG }}

      - name: Build and push Docker image
        uses: docker/build-push-action@4f58ea79222b3b9dc2c8bbdd6debcef730109a75 # v6.9.0
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build summary
        run: |
          echo "✅ Docker image built and pushed successfully"
          echo ""
          echo "📦 Images:"
          echo "   ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ steps.tag.outputs.TAG }}"
          echo "   ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ steps.tag.outputs.BRANCH_TAG }}"
          echo ""
          if [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
            echo "🚀 To deploy production, run:"
            echo "   ./scripts/deploy.sh"
          else
            BRANCH_NAME="${{ github.ref_name }}"
            echo "🧪 To deploy preview, add to docker-compose.yml:"
            echo "   image: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ steps.tag.outputs.TAG }}"
          fi
```

**Step 3: Validate YAML syntax**

Run: `python3 -c "import yaml; yaml.safe_load(open('/Users/varunr/projects/oews/.github/workflows/deploy.yml'))"`

Expected: No output (valid YAML)

**Step 4: Commit the changes**

Run:
```bash
cd /Users/varunr/projects/oews
git add .github/workflows/deploy.yml
git commit -m "feat(ci): enable auto-build for execution-traceability and preview/* branches"
```

Expected: `1 file changed, X insertions(+), Y deletions(-)`

**Step 5: Verify commit**

Run: `git log --oneline -1`

Expected: Shows the commit message about enabling auto-build

---

## Task 2: Test the workflow with execution-traceability branch

**Step 1: Check current branch**

Run: `git branch`

Expected: Shows you're on `execution-traceability` branch

**Step 2: Push the updated workflow to trigger a build**

Run: `git push origin execution-traceability`

Expected: Output shows the branch is being pushed

**Step 3: Monitor GitHub Actions build**

Go to https://github.com/varunr89/oews/actions and watch for the new build to start.

Expected: A new workflow run appears for the `execution-traceability` branch

**Step 4: Wait for build to complete (2-5 minutes)**

The GitHub Actions page will show:
- "In progress" while building
- "✓ Passed" when complete

**Step 5: Verify image was published**

Once build completes, verify the image exists in GitHub Container Registry:

Run:
```bash
# This will show if the image was successfully published
gh api repos/varunr89/oews/packages --query '.[] | select(.name=="execution-traceability") | .latest_version.name'
```

Or check manually at: https://github.com/varunr89/oews/pkgs/container/oews

Expected: See image tagged `execution-traceability` and `execution-traceability-<git-sha>`

**Step 6: Record successful build**

Once confirmed, note the image tag for use in Task 3:
- Tag: `execution-traceability`
- Full image: `ghcr.io/varunr89/oews:execution-traceability`

---

## Task 3: Update docker-compose.yml to use published image

**Files:**
- Modify: `/Users/varunr/projects/oews/docker-compose.yml` (oews-trace service)

**Step 1: Verify current image tag**

Run: `grep -A 1 "oews-trace:" /Users/varunr/projects/oews/docker-compose.yml`

Expected: Shows `image: ghcr.io/varunr89/oews:execution-traceability`

**Step 2: No changes needed!**

The docker-compose.yml already points to the correct image tag. The image will now be available after GitHub Actions builds it.

---

## Success Criteria

- ✅ Workflow now builds on pushes to `main`, `execution-traceability`, and `preview/**` branches
- ✅ Images are tagged appropriately based on branch
- ✅ `execution-traceability` image is built and published to ghcr.io
- ✅ Image is available for pulling in docker-compose.yml
- ✅ Future `preview/*` branches will auto-build with the same pattern
- ✅ All changes committed to git
