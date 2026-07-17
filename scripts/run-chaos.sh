#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CHAOS_DIR="${ROOT_DIR}/infra/manifests/chaos"

usage() {
  cat <<EOF
Usage: $0 <command> [experiment]

Commands:
  apply   <experiment>   Apply a chaos experiment
  delete  <experiment>   Remove a chaos experiment
  status                 Show running experiments
  list                   List available experiments

Experiments:
  network-delay    Inject 500ms latency into order-svc network traffic
  network-loss     Drop 100% of packets to inventory-svc (readiness fails)
  pod-kill         Kill one inventory-svc pod

Examples:
  $0 apply network-delay
  $0 apply pod-kill
  $0 status
  $0 delete network-delay
EOF
}

check_chaos_mesh() {
  if ! kubectl get crd networkchaos.chaos-mesh.org &>/dev/null; then
    echo "ERROR: Chaos Mesh CRDs not found. Is Chaos Mesh installed?"
    echo "Run: ./scripts/deploy-all.sh"
    exit 1
  fi
}

cmd_apply() {
  local experiment="$1"
  local file="${CHAOS_DIR}/${experiment}.yaml"

  if [ ! -f "${file}" ]; then
    echo "ERROR: Experiment file not found: ${file}"
    echo "Available: network-delay, pod-kill"
    exit 1
  fi

  check_chaos_mesh
  echo "==> Applying chaos experiment: ${experiment}"
  kubectl apply -f "${file}"
  echo ""
  echo "  Experiment applied. Monitor effects:"
  echo "  Grafana RED dashboard: http://localhost:3000"
  echo "  Jaeger traces:         http://localhost:16686"
  echo ""

  case "${experiment}" in
    network-delay)
      echo "Expected observations (within 2-3 minutes):"
      echo "  - P99 latency > 500ms in Grafana"
      echo "  - HighP99Latency alert fires (after 2m)"
      ;;
    pod-kill)
      echo "Expected observations (within 1-2 minutes):"
      echo "  - inventory-svc error rate spikes to 100%"
      echo "  - PodNotReady alert fires (after 1m)"
      echo "  - HighErrorRate alert fires (after 2m)"
      ;;
  esac
}

cmd_delete() {
  local experiment="$1"
  local file="${CHAOS_DIR}/${experiment}.yaml"

  if [ ! -f "${file}" ]; then
    echo "ERROR: Experiment file not found: ${file}"
    exit 1
  fi

  echo "==> Removing chaos experiment: ${experiment}"
  kubectl delete -f "${file}" --ignore-not-found
  echo "  Experiment removed. Services should recover within 30-60 seconds."
}

cmd_status() {
  echo "==> Running NetworkChaos experiments:"
  kubectl get networkchaos -n observability-demo 2>/dev/null || echo "  None"
  echo ""
  echo "==> Running PodChaos experiments:"
  kubectl get podchaos -n observability-demo 2>/dev/null || echo "  None"
}

cmd_list() {
  echo "Available chaos experiments:"
  for f in "${CHAOS_DIR}"/*.yaml; do
    echo "  $(basename "${f}" .yaml)"
  done
}

# Main
if [ $# -lt 1 ]; then
  usage
  exit 1
fi

COMMAND="$1"
EXPERIMENT="${2:-}"

case "${COMMAND}" in
  apply)
    [ -z "${EXPERIMENT}" ] && { echo "ERROR: Specify an experiment name."; usage; exit 1; }
    cmd_apply "${EXPERIMENT}"
    ;;
  delete)
    [ -z "${EXPERIMENT}" ] && { echo "ERROR: Specify an experiment name."; usage; exit 1; }
    cmd_delete "${EXPERIMENT}"
    ;;
  status)
    cmd_status
    ;;
  list)
    cmd_list
    ;;
  *)
    echo "ERROR: Unknown command: ${COMMAND}"
    usage
    exit 1
    ;;
esac
