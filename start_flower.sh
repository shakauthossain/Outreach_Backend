#!/bin/bash

# Celery Flower monitoring startup script

echo "🌸 Starting Celery Flower (Task Monitoring UI)..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Run ./start.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Please configure .env before starting Flower."
    exit 1
fi

# Export environment variables
export $(cat .env | grep -v '^#' | xargs)

# Start Flower
echo "✅ Starting Flower on http://localhost:5555..."
celery -A app.tasks.celery_app flower \
    --port=5555 \
    --broker="${CELERY_BROKER_URL}" \
    --broker_api="${CELERY_BROKER_URL}/api/"
