#!/bin/bash
# n8n Initialization Script
# Creates directories, generates secrets, and prepares environment

set -e

N8N_DIR="$HOME/.n8n"
DATA_DIR="$N8N_DIR/data"
ENV_FILE="$N8N_DIR/.env"

echo "=== n8n Initialization Script ==="
echo ""

# Create data directories
echo "[1/4] Creating data directories..."
mkdir -p "$DATA_DIR/n8n"
mkdir -p "$DATA_DIR/postgres"
mkdir -p "$N8N_DIR/backups"
mkdir -p "$N8N_DIR/workflows"

# Set directory permissions
chmod 700 "$DATA_DIR"
chmod 700 "$N8N_DIR/backups"

# Generate secrets if .env doesn't exist
if [ ! -f "$ENV_FILE" ]; then
    echo "[2/4] Generating secrets..."

    # Generate secure random passwords/keys
    POSTGRES_PASSWORD=$(openssl rand -hex 16)
    N8N_WEBHOOK_SECRET=$(openssl rand -hex 32)
    N8N_API_KEY=$(openssl rand -hex 32)

    # Write to .env file
    cat > "$ENV_FILE" << EOF
# n8n Environment Variables
# Generated on $(date)
# WARNING: Do not commit this file to version control

# PostgreSQL credentials
POSTGRES_PASSWORD=$POSTGRES_PASSWORD

# Webhook authentication secret
# All webhook requests must include header: X-API-Key: <this value>
N8N_WEBHOOK_SECRET=$N8N_WEBHOOK_SECRET

# n8n API key (for programmatic access)
N8N_API_KEY=$N8N_API_KEY

# Home directory (for docker-compose volume paths)
HOME=$HOME
EOF

    # Secure the env file
    chmod 600 "$ENV_FILE"

    echo "    Generated new secrets in $ENV_FILE"
else
    echo "[2/4] Using existing secrets from $ENV_FILE"
fi

# Verify Docker is running
echo "[3/4] Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo "    ERROR: Docker is not running. Please start Docker Desktop."
    exit 1
fi
echo "    Docker is running"

# Display next steps
echo "[4/4] Initialization complete!"
echo ""
echo "=== Next Steps ==="
echo ""
echo "1. Start n8n:"
echo "   cd ~/.n8n && docker-compose up -d"
echo ""
echo "2. Access n8n UI:"
echo "   http://localhost:5678"
echo ""
echo "3. Your webhook secret (save this for API calls):"
if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
    echo "   $N8N_WEBHOOK_SECRET"
fi
echo ""
echo "4. Configure credentials in n8n UI:"
echo "   - Google OAuth2 (Gmail + Calendar)"
echo "   - Anthropic API key"
echo "   - Slack Bot Token (optional)"
echo ""
echo "=== Security Notes ==="
echo "- Webhooks bound to localhost only (127.0.0.1:5678)"
echo "- All webhooks require X-API-Key header"
echo "- Never commit ~/.n8n/.env to version control"
echo ""
