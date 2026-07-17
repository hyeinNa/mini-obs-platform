#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="mini-obs-platform"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Checking prerequisites..."

if ! command -v kind &>/dev/null; then
  echo "ERROR: kind is not installed. Install from https://kind.sigs.k8s.io/docs/user/quick-start/"
  exit 1
fi

if ! command -v kubectl &>/dev/null; then
  echo "ERROR: kubectl is not installed."
  exit 1
fi

if ! command -v helm &>/dev/null; then
  echo "ERROR: helm is not installed. Install from https://helm.sh/docs/intro/install/"
  exit 1
fi

echo "==> Creating KIND cluster: ${CLUSTER_NAME}..."
if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
  echo "  Cluster '${CLUSTER_NAME}' already exists. Skipping creation."
else
  kind create cluster \
    --name "${CLUSTER_NAME}" \
    --config "${SCRIPT_DIR}/kind-config.yaml" \
    --wait 120s
  echo "  Cluster created successfully."
fi

echo "==> Switching kubectl context to kind-${CLUSTER_NAME}..."
kubectl config use-context "kind-${CLUSTER_NAME}"

echo "==> Verifying cluster nodes..."
kubectl get nodes -o wide

echo ""
echo "==> KIND cluster '${CLUSTER_NAME}' is ready."
echo "  Control plane + 2 workers configured."
echo "  Port mappings:"
echo "    localhost:3000   -> Grafana      (NodePort 30000)"
echo "    localhost:16686  -> Jaeger UI    (NodePort 30001)"
echo "    localhost:8090   -> ArgoCD UI    (NodePort 30002)"
