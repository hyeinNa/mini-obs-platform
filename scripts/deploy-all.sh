#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

CLUSTER_NAME="mini-obs-platform"
ARGOCD_VERSION="2.10.1"

echo "======================================"
echo " mini-obs-platform — Full Stack Deploy"
echo "======================================"

# Step 0: verify cluster is running
if ! kubectl config get-contexts "kind-${CLUSTER_NAME}" &>/dev/null; then
  echo "ERROR: KIND cluster '${CLUSTER_NAME}' not found."
  echo "Run: ./scripts/setup-cluster.sh"
  exit 1
fi
kubectl config use-context "kind-${CLUSTER_NAME}"

# Step 0.5: Fix DNS on KIND nodes (Rancher Desktop workaround)
echo ""
echo "==> [0/6] Fixing DNS on KIND nodes (append Google DNS)..."
for node in ${CLUSTER_NAME}-control-plane ${CLUSTER_NAME}-worker ${CLUSTER_NAME}-worker2; do
  if docker exec "${node}" cat /etc/resolv.conf 2>/dev/null | grep -q "8.8.8.8"; then
    echo "  ${node}: DNS already fixed"
  else
    docker exec "${node}" bash -c 'echo "nameserver 8.8.8.8" >> /etc/resolv.conf' 2>/dev/null || true
    echo "  ${node}: DNS appended"
  fi
done

# Step 1: namespaces
echo ""
echo "==> [1/6] Creating namespaces..."
kubectl apply -f "${ROOT_DIR}/infra/manifests/namespace.yaml"
echo "  Namespaces created. Verifying..."
kubectl get namespaces observability-demo monitoring tracing logging chaos-mesh --no-headers

# Step 2: ArgoCD installation
echo ""
echo "==> [2/6] Installing ArgoCD..."
if ! kubectl get namespace argocd &>/dev/null; then
  kubectl create namespace argocd
fi

ARGOCD_INSTALLED=$(kubectl get deployment argocd-server -n argocd --ignore-not-found -o name)
if [ -z "${ARGOCD_INSTALLED}" ]; then
  kubectl apply -n argocd \
    -f "https://raw.githubusercontent.com/argoproj/argo-cd/v${ARGOCD_VERSION}/manifests/install.yaml"
  echo "  Waiting for ArgoCD pods to be ready (this may take 2-3 min)..."
  echo "  Patching ArgoCD imagePullPolicy to IfNotPresent (KIND workaround)..."
  for deploy in argocd-applicationset-controller argocd-dex-server argocd-notifications-controller argocd-redis argocd-repo-server argocd-server; do
    kubectl patch deployment "${deploy}" -n argocd --type='json' \
      -p='[{"op":"replace","path":"/spec/template/spec/containers/0/imagePullPolicy","value":"IfNotPresent"}]' 2>/dev/null || true
    kubectl patch deployment "${deploy}" -n argocd --type='json' \
      -p='[{"op":"replace","path":"/spec/template/spec/initContainers/0/imagePullPolicy","value":"IfNotPresent"}]' 2>/dev/null || true
  done
  kubectl patch statefulset argocd-application-controller -n argocd --type='json' \
    -p='[{"op":"replace","path":"/spec/template/spec/containers/0/imagePullPolicy","value":"IfNotPresent"}]' 2>/dev/null || true
  kubectl wait --for=condition=available deployment/argocd-server -n argocd --timeout=180s
else
  echo "  ArgoCD already installed."
fi

# Step 3: Helm repos
echo ""
echo "==> [3/6] Adding Helm chart repositories..."
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>/dev/null || true
helm repo add grafana              https://grafana.github.io/helm-charts             2>/dev/null || true
helm repo add fluent               https://fluent.github.io/helm-charts              2>/dev/null || true
helm repo add open-telemetry       https://open-telemetry.github.io/opentelemetry-helm-charts 2>/dev/null || true
helm repo add chaos-mesh           https://charts.chaos-mesh.org                     2>/dev/null || true
helm repo update

# Step 4: Install observability stack via Helm
echo ""
echo "==> [4/6] Installing observability stack via Helm..."

echo "  Installing kube-prometheus-stack..."
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values "${ROOT_DIR}/infra/helm/kube-prometheus-stack/values.yaml" \
  --version "57.2.0" \
  --wait --timeout 300s

echo "  Installing Loki..."
helm upgrade --install loki grafana/loki-stack \
  --namespace monitoring \
  --values "${ROOT_DIR}/infra/helm/loki/values.yaml" \
  --version "2.10.2" \
  --wait --timeout 120s

echo "  Installing Fluent Bit..."
helm upgrade --install fluent-bit fluent/fluent-bit \
  --namespace monitoring \
  --values "${ROOT_DIR}/infra/helm/fluent-bit/values.yaml" \
  --version "0.43.0" \
  --wait --timeout 120s

echo "  Installing Tempo..."
helm upgrade --install tempo grafana/tempo \
  --namespace tracing \
  --values "${ROOT_DIR}/infra/helm/tempo/values.yaml" \
  --version "1.24.4" \
  --wait --timeout 180s

echo "  Installing OTel Collector..."
helm upgrade --install otel-collector open-telemetry/opentelemetry-collector \
  --namespace tracing \
  --values "${ROOT_DIR}/infra/helm/otel-collector/values.yaml" \
  --version "0.87.0" \
  --wait --timeout 120s

echo "  Installing Chaos Mesh..."
helm upgrade --install chaos-mesh chaos-mesh/chaos-mesh \
  --namespace chaos-mesh \
  --values "${ROOT_DIR}/infra/helm/chaos-mesh/values.yaml" \
  --version "2.6.3" \
  --wait --timeout 120s

# Step 5: Apply K8s manifests
echo ""
echo "==> [5/6] Applying Kubernetes manifests..."
kubectl apply -f "${ROOT_DIR}/infra/manifests/monitoring/prometheus-rules.yaml"
kubectl apply -f "${ROOT_DIR}/infra/manifests/monitoring/grafana-dashboards.yaml"
kubectl apply -f "${ROOT_DIR}/infra/manifests/apps/"

# Patch ArgoCD server service to NodePort 30002 for KIND port mapping
echo "  Patching argocd-server to NodePort 30002..."
kubectl patch svc argocd-server -n argocd \
  -p '{"spec":{"type":"NodePort","ports":[{"port":443,"targetPort":8080,"nodePort":30002}]}}' \
  2>/dev/null || echo "  (ArgoCD patch skipped — service not ready yet)"

# Step 6: ArgoCD App of Apps
echo ""
echo "==> [6/6] Deploying ArgoCD App of Apps..."
kubectl apply -f "${ROOT_DIR}/infra/argocd/app-of-apps.yaml"

echo ""
echo "======================================"
echo " Deployment complete!"
echo "======================================"
echo ""
echo "Access services:"
echo "  Grafana:  http://localhost:3000  (admin/admin, traces via Tempo datasource)"
echo "  ArgoCD:   http://localhost:8090"
echo ""
echo "To port-forward sample apps:"
echo "  ./scripts/port-forward.sh"
