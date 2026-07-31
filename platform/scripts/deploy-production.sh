#!/usr/bin/env bash
set -euo pipefail

echo "Deploying to production..."
kubectl apply -k "$(dirname "$0")/../kubernetes/overlays/production"
echo "Production deployment applied."
