#!/bin/bash

# OEWS Data Agent API Server Startup Script

echo "Starting OEWS Data Agent API..."

# Check for required environment variables
if [ -z "$AZURE_AI_API_KEY" ]; then
    echo "Warning: AZURE_AI_API_KEY not set. API may not function correctly."
fi

# Set defaults
export API_HOST="${API_HOST:-0.0.0.0}"
export API_PORT="${API_PORT:-8000}"
export DATABASE_ENV="${DATABASE_ENV:-dev}"
export SQLITE_DB_PATH="${SQLITE_DB_PATH:-data/oews.db}"

# Start server
python -m src.main
