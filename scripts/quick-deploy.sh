#!/bin/bash
# Ultra-fast deployment - skips build wait if already complete
# Usage: ./scripts/quick-deploy.sh

set -e

TAILSCALE_IP="100.107.15.52"
USER="varun"

echo "🚀 Quick Deploy (skipping build check)"
echo ""

# Deploy directly to server
echo "🚢 Deploying to server..."
ssh $USER@$TAILSCALE_IP 'cd /opt/oews && docker compose pull && docker compose up -d && sleep 15 && docker compose ps | grep oews-api'

# Test endpoint
echo ""
echo "🧪 Testing..."
curl -sf https://api.oews.bhavanaai.com/health && echo -e "\n✅ Live!" || echo "❌ Failed"
