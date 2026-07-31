#!/usr/bin/env bash
set -euo pipefail

echo "Starting local DataHub AI Chatbot platform..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/../.."

docker compose -f "$PROJECT_DIR/platform/docker/compose.yaml" up --build -d
echo "Platform started. API available at http://localhost:8000"
