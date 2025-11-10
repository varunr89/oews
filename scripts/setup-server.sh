#!/bin/bash
set -e

echo "=== OEWS Server Setup Script ==="
echo "This script sets up the deployment environment on your Linux server"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
   echo "ERROR: Don't run this script as root. Run as your regular user."
   exit 1
fi

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "→ Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "✓ Docker installed. You may need to log out and back in for group changes."
else
    echo "✓ Docker already installed"
fi

# Create deployment directory
echo "→ Creating deployment directory..."
sudo mkdir -p /opt/oews/data
sudo chown -R $USER:$USER /opt/oews
echo "✓ Created /opt/oews"

# Configure firewall
echo "→ Configuring firewall..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 22/tcp
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw --force enable
    echo "✓ Firewall configured (SSH, HTTP, HTTPS)"
else
    echo "⚠ UFW not found, skip firewall configuration"
fi

# Generate SSH key for GitHub Actions if not exists
if [ ! -f ~/.ssh/github_actions ]; then
    echo "→ Generating SSH key for GitHub Actions..."
    ssh-keygen -t ed25519 -f ~/.ssh/github_actions -N "" -C "github-actions-deploy"
    cat ~/.ssh/github_actions.pub >> ~/.ssh/authorized_keys
    chmod 600 ~/.ssh/authorized_keys
    echo "✓ SSH key generated"
    echo ""
    echo "=== IMPORTANT: Add private key to GitHub Secrets ==="
    echo "The private key is stored at: ~/.ssh/github_actions"
    echo "To view it (ONLY when ready to add to GitHub Secrets):"
    echo "  cat ~/.ssh/github_actions"
    echo ""
    echo "Add it to GitHub repository secrets as 'SSH_PRIVATE_KEY'"
    echo ""
else
    echo "✓ SSH key already exists"
fi

# Get server's SSH host key for GitHub Actions
echo "→ Getting server SSH host key for GitHub Actions..."
ssh-keyscan -H $(curl -s ifconfig.me) > /tmp/server_hostkey 2>/dev/null
SERVER_HOSTKEY=$(ssh-keygen -lf /tmp/server_hostkey | awk '{print $2}')
rm /tmp/server_hostkey
echo "✓ Server SSH host key fingerprint: $SERVER_HOSTKEY"

echo ""
echo "=== Next Steps ==="
echo "1. Add GitHub Secrets (in repository settings):"
echo "   - SERVER_HOST: $(curl -s ifconfig.me)"
echo "   - SERVER_USER: $USER"
echo "   - SSH_PRIVATE_KEY: Run 'cat ~/.ssh/github_actions' and paste"
echo "   - SSH_HOST_FINGERPRINT: $SERVER_HOSTKEY"
echo "   - AZURE_INFERENCE_ENDPOINT: <your Azure OpenAI endpoint URL>"
echo "   - AZURE_INFERENCE_CREDENTIAL: <your Azure OpenAI API key>"
echo "   - TAVILY_API_KEY: <your Tavily API key>"
echo "   - CORS_ORIGINS: https://your-frontend.com"
echo ""
echo "2. Copy deployment files to server:"
echo "   scp docker-compose.yml Caddyfile $USER@$(curl -s ifconfig.me):/opt/oews/"
echo ""
echo "3. Copy database to server:"
echo "   scp data/oews.db $USER@$(curl -s ifconfig.me):/opt/oews/data/"
echo ""
echo "4. Copy backup script to server:"
echo "   scp scripts/backup.sh $USER@$(curl -s ifconfig.me):/opt/oews/scripts/"
echo "   ssh $USER@$(curl -s ifconfig.me) 'chmod +x /opt/oews/scripts/backup.sh'"
echo ""
echo "5. Create backup directory on server:"
echo "   ssh $USER@$(curl -s ifconfig.me) 'sudo mkdir -p /backup/oews && sudo chown $USER:$USER /backup/oews'"
echo ""
echo "6. Initial container startup:"
echo "   ssh $USER@$(curl -s ifconfig.me) 'cd /opt/oews && docker compose up -d'"
echo ""
echo "7. Update DNS: Point api.bhavanaai.com -> $(curl -s ifconfig.me)"
echo ""
echo "8. Push code to trigger first deployment"
echo ""
echo "✓ Server setup complete!"
