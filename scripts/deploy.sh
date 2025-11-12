#!/bin/bash
# Quick deployment script for OEWS via Tailscale
# Usage: ./scripts/deploy.sh

set -e

TAILSCALE_IP="100.107.15.52"
USER="varun"
LATEST_RUN=""

echo "🚀 OEWS Deployment Script"
echo ""

# Step 1: Push code if there are uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "⚠️  You have uncommitted changes. Commit and push first:"
    echo "    git add ."
    echo "    git commit -m 'your message'"
    echo "    git push"
    exit 1
fi

# Step 2: Check GitHub Actions status
echo "📦 Checking GitHub Actions build status..."
LATEST_RUN=$(gh run list --limit 1 --json databaseId,status,conclusion --jq '.[0]')
RUN_ID=$(echo "$LATEST_RUN" | jq -r '.databaseId')
STATUS=$(echo "$LATEST_RUN" | jq -r '.status')
CONCLUSION=$(echo "$LATEST_RUN" | jq -r '.conclusion')

if [ "$STATUS" == "completed" ] && [ "$CONCLUSION" == "failure" ]; then
    echo "❌ Latest build failed. Check logs: gh run view $RUN_ID --log-failed"
    exit 1
fi

if [ "$STATUS" == "in_progress" ] || [ "$STATUS" == "queued" ]; then
    echo "⏳ Build in progress... Waiting for completion..."
    gh run watch $RUN_ID --exit-status
fi

echo "✅ Build complete!"
echo ""

# Step 3: Deploy to server
echo "🚢 Deploying to server via Tailscale..."
ssh $USER@$TAILSCALE_IP << 'ENDSSH'
cd /opt/oews

# Pull latest image
echo "  → Pulling latest image..."
docker compose pull

# Restart services
echo "  → Restarting services..."
docker compose up -d

# Wait for health check
echo "  → Waiting for health check..."
sleep 15

# Verify deployment
if docker compose ps | grep -q "oews-api.*healthy"; then
    echo "  ✅ Deployment successful!"
else
    echo "  ❌ Deployment failed - container not healthy"
    docker compose logs --tail=30 oews-api
    exit 1
fi
ENDSSH

# Step 4: Test endpoint
echo ""
echo "🧪 Testing production endpoint..."
if curl -sf https://api.oews.bhavanaai.com/health > /dev/null; then
    echo "✅ Health check passed!"
    echo ""
    echo "🎉 Deployment complete! API live at:"
    echo "   https://api.oews.bhavanaai.com"
else
    echo "❌ Health check failed!"
    exit 1
fi
