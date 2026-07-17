#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="mini-obs-platform"

echo "==> Pulling and loading images into KIND cluster '${CLUSTER_NAME}'..."

# Images required by the stack
IMAGES=(
  "quay.io/argoproj/argocd:v2.10.1"
  "ghcr.io/dexidp/dex:v2.37.0"
  "redis:7.0.14-alpine"
  "fluent/fluent-bit:2.2.2"
  "jaegertracing/all-in-one:1.55"
  "otel/opentelemetry-collector-contrib:0.96.0"
)

# Pull images on host
for img in "${IMAGES[@]}"; do
  echo "  Pulling ${img}..."
  docker pull "${img}" --quiet
done

# Build sample apps
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "  Building sample apps..."
docker build -t ghcr.io/owner/mini-obs-frontend-svc:latest "${ROOT_DIR}/apps/frontend-svc/" --quiet
docker build -t ghcr.io/owner/mini-obs-order-svc:latest "${ROOT_DIR}/apps/order-svc/" --quiet
docker build -t ghcr.io/owner/mini-obs-inventory-svc:latest "${ROOT_DIR}/apps/inventory-svc/" --quiet

# Load all into KIND
ALL_IMAGES=(
  "${IMAGES[@]}"
  "ghcr.io/owner/mini-obs-frontend-svc:latest"
  "ghcr.io/owner/mini-obs-order-svc:latest"
  "ghcr.io/owner/mini-obs-inventory-svc:latest"
)

echo "  Loading into KIND..."
kind load docker-image "${ALL_IMAGES[@]}" --name "${CLUSTER_NAME}"

echo ""
echo "==> All images loaded successfully."
