#!/bin/bash
CONTAINER_NAME="finally-app"
echo "Stopping FinAlly..."
docker stop "$CONTAINER_NAME" 2>/dev/null || true
docker rm "$CONTAINER_NAME" 2>/dev/null || true
echo "Stopped. Data volume 'finally-data' preserved."
