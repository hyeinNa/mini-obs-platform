#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="mini-obs-platform"

echo "==> Deleting KIND cluster: ${CLUSTER_NAME}..."

if ! kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
  echo "  Cluster '${CLUSTER_NAME}' does not exist. Nothing to do."
  exit 0
fi

kind delete cluster --name "${CLUSTER_NAME}"
echo "  Cluster '${CLUSTER_NAME}' deleted."

echo "==> Cleaning up kubectl context..."
kubectl config delete-context "kind-${CLUSTER_NAME}" 2>/dev/null || true
kubectl config delete-cluster "kind-${CLUSTER_NAME}" 2>/dev/null || true

echo "==> Teardown complete."
