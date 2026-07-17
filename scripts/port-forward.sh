#!/usr/bin/env bash
set -euo pipefail

# Port-forward all services for local development access.
# NodePort services (Grafana 30000, Jaeger 30001, ArgoCD 30002) are mapped
# via KIND extraPortMappings, so they are already accessible.
# This script additionally port-forwards the sample apps.

CLUSTER_NAME="mini-obs-platform"

echo "==> Switching to kind-${CLUSTER_NAME} context..."
kubectl config use-context "kind-${CLUSTER_NAME}"

echo ""
echo "NodePort services accessible via KIND port mappings (no action needed):"
echo "  Grafana:  http://localhost:3000"

echo "  ArgoCD:   http://localhost:8090"
echo ""
echo "==> Starting port-forwards for sample apps..."
echo "  frontend-svc: http://localhost:8080"
echo "  (Press Ctrl+C to stop all port-forwards)"
echo ""

# Kill any existing port-forwards on these ports
for PORT in 8080 8081 8082 9090; do
  lsof -ti tcp:"${PORT}" | xargs kill -9 2>/dev/null || true
done

# Port-forward sample apps in background
kubectl port-forward -n observability-demo svc/frontend-svc 8080:8080 &
PF_FRONTEND=$!

kubectl port-forward -n observability-demo svc/order-svc 8081:8081 &
PF_ORDER=$!

kubectl port-forward -n observability-demo svc/inventory-svc 8082:8082 &
PF_INVENTORY=$!

kubectl port-forward -n monitoring svc/prometheus-operated 9090:9090 &
PF_PROMETHEUS=$!

echo "Port-forwards started:"
echo "  frontend-svc  -> http://localhost:8080  (PID: ${PF_FRONTEND})"
echo "  order-svc     -> http://localhost:8081  (PID: ${PF_ORDER})"
echo "  inventory-svc -> http://localhost:8082  (PID: ${PF_INVENTORY})"
echo "  prometheus    -> http://localhost:9090  (PID: ${PF_PROMETHEUS})"
echo ""
echo "Press Ctrl+C to stop all port-forwards."

# Wait and clean up on Ctrl+C
trap 'echo ""; echo "Stopping port-forwards..."; kill ${PF_FRONTEND} ${PF_ORDER} ${PF_INVENTORY} ${PF_PROMETHEUS} 2>/dev/null || true; echo "Done."' INT TERM
wait
