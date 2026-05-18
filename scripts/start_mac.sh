#!/bin/bash
set -e

IMAGE_NAME="finally-app"
CONTAINER_NAME="finally-app"
PORT=8000

# Check if already running
if docker ps --filter "name=$CONTAINER_NAME" --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo "FinAlly is already running at http://localhost:$PORT"
    exit 0
fi

# Determine if we need to build
BUILD=false
[[ "${1:-}" == "--build" ]] && BUILD=true
if ! docker images --format "{{.Repository}}" | grep -q "^${IMAGE_NAME}$"; then
    BUILD=true
fi

if $BUILD; then
    echo "Building Docker image (this takes a few minutes)..."
    docker build -t "$IMAGE_NAME" .
fi

# Remove stopped container if exists
docker rm "$CONTAINER_NAME" 2>/dev/null || true

# Check .env
if [[ ! -f ".env" ]]; then
    echo "Warning: .env not found. Copying from .env.example..."
    if [[ -f ".env.example" ]]; then
        cp .env.example .env
    else
        echo "Error: .env.example not found. Please create .env manually."
        exit 1
    fi
fi

echo "Starting FinAlly..."
docker run -d \
    --name "$CONTAINER_NAME" \
    -v finally-data:/app/db \
    -p "$PORT:8000" \
    --env-file .env \
    "$IMAGE_NAME"

echo ""
echo "FinAlly is running! Open: http://localhost:$PORT"
