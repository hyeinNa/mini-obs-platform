#!/usr/bin/env bash
set -euo pipefail

# E2E test script: curl-based tests against the mini-obs-platform
# Tests: normal requests -> metric validation -> trace validation

FRONTEND_URL="${FRONTEND_URL:-http://localhost:8080}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
# Tempo is queried through Grafana's datasource proxy (KIND NodePort 3000)
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
GRAFANA_AUTH="${GRAFANA_AUTH:-admin:admin}"

PASS=0
FAIL=0

run_test() {
  local name="$1"
  local result="$2"  # "pass" or "fail"
  local detail="${3:-}"

  if [ "${result}" = "pass" ]; then
    echo "  [PASS] ${name}"
    PASS=$((PASS + 1))
  else
    echo "  [FAIL] ${name}"
    [ -n "${detail}" ] && echo "         ${detail}"
    FAIL=$((FAIL + 1))
  fi
}

assert_http_status() {
  local url="$1"
  local expected_status="$2"
  local description="$3"
  local extra_args="${4:-}"

  # shellcheck disable=SC2086
  actual_status=$(curl -s -o /dev/null -w "%{http_code}" ${extra_args} "${url}" 2>/dev/null || echo "000")

  if [ "${actual_status}" = "${expected_status}" ]; then
    run_test "${description}" "pass"
    return 0
  else
    run_test "${description}" "fail" "Expected HTTP ${expected_status}, got ${actual_status}"
    return 1
  fi
}

assert_json_field() {
  local url="$1"
  local field="$2"
  local expected_value="$3"
  local description="$4"

  local response
  response=$(curl -s "${url}" 2>/dev/null || echo "{}")
  local actual_value
  actual_value=$(echo "${response}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('${field}',''))" 2>/dev/null || echo "")

  if [ "${actual_value}" = "${expected_value}" ]; then
    run_test "${description}" "pass"
  else
    run_test "${description}" "fail" "Expected '${field}'='${expected_value}', got '${actual_value}'"
  fi
}

assert_prometheus_metric() {
  local metric="$1"
  local description="$2"

  local response
  response=$(curl -s "${PROMETHEUS_URL}/api/v1/query?query=${metric}" 2>/dev/null || echo '{"status":"error"}')
  local status
  status=$(echo "${response}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','error'))" 2>/dev/null || echo "error")
  local result_count
  result_count=$(echo "${response}" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('data',{}).get('result',[])))" 2>/dev/null || echo "0")

  if [ "${status}" = "success" ] && [ "${result_count}" -gt "0" ]; then
    run_test "${description}" "pass"
  else
    run_test "${description}" "fail" "Metric '${metric}' not found or Prometheus unreachable"
  fi
}

echo "======================================="
echo " mini-obs-platform E2E Test Suite"
echo "======================================="
echo ""
echo "Targets:"
echo "  Frontend:   ${FRONTEND_URL}"
echo "  Prometheus: ${PROMETHEUS_URL}"
echo "  Tempo:      ${GRAFANA_URL} (via Grafana datasource proxy)"
echo ""

# Section 1: Health checks
echo "--- [1] Health Checks ---"
assert_http_status "${FRONTEND_URL}/health" "200" "frontend-svc /health returns 200"
assert_json_field  "${FRONTEND_URL}/health" "status" "ok" "frontend-svc /health returns status=ok"

# Section 2: Metrics endpoints
echo ""
echo "--- [2] Metrics Endpoints ---"
assert_http_status "${FRONTEND_URL}/metrics" "200" "frontend-svc /metrics returns 200"
METRICS_CONTENT=$(curl -s "${FRONTEND_URL}/metrics" 2>/dev/null || echo "")
if echo "${METRICS_CONTENT}" | grep -q "http_requests_total"; then
  run_test "frontend-svc /metrics contains http_requests_total" "pass"
else
  run_test "frontend-svc /metrics contains http_requests_total" "fail" "Metric not found in response"
fi

# Section 3: Normal request flow
echo ""
echo "--- [3] Normal Request Flow ---"
ORDER_RESPONSE=$(curl -s -w "\n%{http_code}" "${FRONTEND_URL}/api/order" 2>/dev/null || echo -e "\n000")
ORDER_STATUS=$(echo "${ORDER_RESPONSE}" | tail -1)
ORDER_BODY=$(echo "${ORDER_RESPONSE}" | head -1)

if [ "${ORDER_STATUS}" = "200" ]; then
  run_test "GET /api/order returns 200" "pass"

  # Verify trace_id is present in response
  TRACE_ID=$(echo "${ORDER_BODY}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('trace_id',''))" 2>/dev/null || echo "")
  if [ ${#TRACE_ID} -eq 32 ]; then
    run_test "GET /api/order response contains 32-char trace_id" "pass"
  else
    run_test "GET /api/order response contains 32-char trace_id" "fail" "trace_id='${TRACE_ID}' (length: ${#TRACE_ID})"
  fi
else
  run_test "GET /api/order returns 200" "fail" "Status: ${ORDER_STATUS}"
  run_test "GET /api/order response contains 32-char trace_id" "fail" "Skipped (request failed)"
fi

INV_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${FRONTEND_URL}/api/inventory" 2>/dev/null || echo "000")
if [ "${INV_STATUS}" = "200" ]; then
  run_test "GET /api/inventory returns 200" "pass"
else
  run_test "GET /api/inventory returns 200" "fail" "Status: ${INV_STATUS}"
fi

# Section 4: Prometheus metric validation (requires traffic to have been generated)
echo ""
echo "--- [4] Prometheus Metrics ---"
sleep 5  # Allow Prometheus to scrape

assert_prometheus_metric "http_requests_total" "Prometheus has http_requests_total metric"
assert_prometheus_metric "http_request_duration_seconds_count" "Prometheus has request duration histogram"

# Section 5: Tempo trace validation (via Grafana datasource proxy)
echo ""
echo "--- [5] Tempo Trace Validation ---"
TRACEQL=$(python3 -c "import urllib.parse; print(urllib.parse.quote('{resource.service.name=\"frontend-svc\"}'))")
TEMPO_SEARCH=$(curl -s -u "${GRAFANA_AUTH}" "${GRAFANA_URL}/api/datasources/proxy/uid/tempo/api/search?q=${TRACEQL}&limit=1" 2>/dev/null || echo '{"traces":[]}')
FRONTEND_IN_TEMPO=$(echo "${TEMPO_SEARCH}" | python3 -c "import sys,json; print('yes' if json.load(sys.stdin).get('traces') else 'no')" 2>/dev/null || echo "no")

if [ "${FRONTEND_IN_TEMPO}" = "yes" ]; then
  run_test "frontend-svc traces found in Tempo" "pass"
else
  run_test "frontend-svc traces found in Tempo" "fail" "No traces found (traces may not have been sent yet)"
fi

# Section 6: Summary
echo ""
echo "======================================="
echo " Test Results: ${PASS} passed, ${FAIL} failed"
echo "======================================="

if [ "${FAIL}" -gt 0 ]; then
  echo ""
  echo "Some tests failed. Common causes:"
  echo "  - Services not yet deployed (run: ./scripts/deploy-all.sh)"
  echo "  - Port-forwards not active (run: ./scripts/port-forward.sh)"
  echo "  - Prometheus scrape interval not elapsed (wait 15-30s and retry)"
  exit 1
fi

echo "All tests passed."
