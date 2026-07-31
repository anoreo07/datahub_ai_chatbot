#!/usr/bin/env bash
set -euo pipefail

echo "Stopping local platform..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/../.."

docker compose -f "$PROJECT_DIR/platform/docker/compose.yaml" down
echo "Platform stopped."
