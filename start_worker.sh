#!/bin/bash

# Celery worker startup script

echo "🔧 Starting Celery Worker..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Run ./start.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Please configure .env before starting worker."
    exit 1
fi

# Export environment variables
export $(cat .env | grep -v '^#' | xargs)

# Start Celery worker
echo "✅ Starting Celery worker with 4 concurrent processes..."
celery -A app.tasks.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --max-tasks-per-child=1000 \
    --time-limit=3600 \
    --soft-time-limit=3000 \
    --pool=prefork
