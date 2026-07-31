#!/usr/bin/env bash
set -euo pipefail

echo "Deploying to staging..."
kubectl apply -k "$(dirname "$0")/../kubernetes/overlays/staging"
echo "Staging deployment applied."
