# API 스펙 — mini-obs-platform

이 문서는 두 가지 유형의 "API"를 정의합니다.
1. **샘플 앱 HTTP 엔드포인트** — frontend-svc, order-svc, inventory-svc
2. **인프라 컴포넌트 설정 스펙** — Prometheus scrape 설정, Alertmanager 규칙, Grafana 프로비저닝

---

## Part 1. 샘플 앱 HTTP 엔드포인트

### 공통 사항

- 모든 응답은 `Content-Type: application/json`
- 구조화 로그 형식: `{"timestamp": "...", "level": "info", "trace_id": "...", "span_id": "...", "message": "..."}`
- OTel W3C TraceContext 헤더 (`traceparent`, `tracestate`) 전파 필수
- 헬스체크 엔드포인트는 인증 불필요

---

### frontend-svc (Go, :8080)

#### GET /api/order

**설명**: 주문 생성 요청을 order-svc에 프록시하고 결과를 반환한다.

**프로시저**:
1. 요청 수신 → OTel SDK root span 생성 (trace_id 발급)
2. W3C TraceContext 헤더(`traceparent`) 생성하여 하위 요청에 주입
3. `http_requests_total{method="GET", path="/api/order"}` 카운터 증가
4. order-svc로 `POST http://order-svc:8081/orders` 호출 (traceparent 헤더 포함)
5. order-svc 응답 수신
6. `http_request_duration_seconds{method="GET", path="/api/order"}` 히스토그램 기록
7. root span 완료 → OTel Collector로 OTLP 전송
8. 응답 반환

**요청 헤더**:
| 헤더 | 필수 | 설명 |
|------|------|------|
| `traceparent` | N | 외부 trace context (있으면 연결, 없으면 새 trace 시작) |

**성공 응답 (200)**:
```json
{
  "order_id": "ord-abc123",
  "status": "created",
  "item_id": "item-001",
  "quantity": 1,
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736"
}
```

**에러 응답**:
- `502`: order-svc 호출 실패 (연결 거부, 타임아웃)
- `503`: order-svc 서비스 불가 (파드 재시작 중)

---

#### GET /api/inventory

**설명**: 전체 재고 목록을 inventory-svc에서 조회하여 반환한다.

**프로시저**:
1. 요청 수신 → OTel SDK root span 생성
2. W3C TraceContext 헤더 주입
3. inventory-svc로 `GET http://inventory-svc:8082/items` 호출
4. 응답 수신 후 메트릭 기록
5. root span 완료 → OTLP 전송
6. 응답 반환

**성공 응답 (200)**:
```json
{
  "items": [
    {"item_id": "item-001", "name": "Widget A", "stock": 100},
    {"item_id": "item-002", "name": "Widget B", "stock": 50}
  ],
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736"
}
```

**에러 응답**:
- `502`: inventory-svc 호출 실패

---

#### GET /metrics

**설명**: Prometheus 텍스트 형식 메트릭 노출 엔드포인트 (Prometheus scrape 대상).

**프로시저**:
1. prometheus_client 레지스트리에서 현재 메트릭 스냅샷 수집
2. Prometheus 텍스트 형식으로 직렬화하여 반환

**성공 응답 (200)**:
```
Content-Type: text/plain; version=0.0.4

# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",path="/api/order",status_code="200"} 42
http_requests_total{method="GET",path="/api/inventory",status_code="200"} 15
# HELP http_request_duration_seconds HTTP request duration
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.1",method="GET",path="/api/order"} 30
```

---

#### GET /health

**설명**: 서비스 헬스체크 엔드포인트. K8s liveness/readiness probe 사용.

**프로시저**:
1. 서비스 내부 상태 확인 (메모리, 기본 연결 등)
2. 상태 JSON 반환

**성공 응답 (200)**:
```json
{"status": "ok", "service": "frontend-svc"}
```

---

### order-svc (Python FastAPI, :8081)

#### POST /orders

**설명**: 신규 주문을 생성하고 재고를 차감한다.

**프로시저**:
1. 요청 바디 유효성 검증 (item_id, quantity 필수)
2. `traceparent` 헤더에서 parent span context 추출 → child span 생성
3. `orders_created_total` 카운터 증가
4. `order_processing_duration_seconds` 히스토그램 타이머 시작
5. inventory-svc로 `PUT /items/{item_id}/stock` 호출하여 재고 차감
6. 재고 부족(409) 시 주문 실패 처리
7. 주문 ID 생성 (UUID v4)
8. 히스토그램 타이머 종료 기록
9. OTel child span 완료 → OTLP 전송
10. 구조화 로그 출력 (trace_id, span_id, order_id 포함)
11. 201 Created 응답 반환

**요청 바디**:
| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| `item_id` | string | Y | - | 주문할 아이템 ID |
| `quantity` | integer | Y | - | 주문 수량 (최소 1) |
| `customer_id` | string | N | "anonymous" | 고객 식별자 |

**요청 예시**:
```json
{
  "item_id": "item-001",
  "quantity": 2,
  "customer_id": "cust-xyz"
}
```

**성공 응답 (201)**:
```json
{
  "order_id": "ord-550e8400-e29b-41d4-a716-446655440000",
  "item_id": "item-001",
  "quantity": 2,
  "status": "created",
  "created_at": "2026-03-28T10:00:00Z",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736"
}
```

**에러 응답**:
- `400`: 요청 바디 유효성 실패 (item_id 누락, quantity < 1)
- `409`: 재고 부족 (inventory-svc에서 409 반환)
- `502`: inventory-svc 호출 실패

---

#### GET /orders/{order_id}

**설명**: 특정 주문 정보를 조회한다.

**프로시저**:
1. path parameter `order_id` 유효성 확인
2. `traceparent` 헤더에서 span context 추출 → child span 생성
3. 인메모리 주문 저장소에서 order_id 조회 (MVP: 영구 저장 없음)
4. 없으면 404 반환
5. span 완료 → OTLP 전송

**경로 파라미터**:
| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `order_id` | string | 주문 고유 ID |

**성공 응답 (200)**:
```json
{
  "order_id": "ord-550e8400-e29b-41d4-a716-446655440000",
  "item_id": "item-001",
  "quantity": 2,
  "status": "created",
  "created_at": "2026-03-28T10:00:00Z"
}
```

**에러 응답**:
- `404`: 해당 order_id가 존재하지 않음

---

#### GET /metrics

**설명**: Prometheus 텍스트 형식 메트릭 노출 (order-svc 커스텀 메트릭 포함).

**프로시저**:
1. prometheus_client 레지스트리 스냅샷 수집
2. Prometheus 텍스트 형식으로 반환

**성공 응답 (200)**:
```
# HELP orders_created_total Total number of orders created
# TYPE orders_created_total counter
orders_created_total 156
# HELP order_processing_duration_seconds Order processing time distribution
# TYPE order_processing_duration_seconds histogram
order_processing_duration_seconds_bucket{le="0.05"} 120
order_processing_duration_seconds_bucket{le="0.5"} 150
order_processing_duration_seconds_bucket{le="1.0"} 155
order_processing_duration_seconds_bucket{le="+Inf"} 156
```

---

#### GET /health

**설명**: 헬스체크.

**성공 응답 (200)**:
```json
{"status": "ok", "service": "order-svc"}
```

---

### inventory-svc (Python FastAPI, :8082)

#### GET /items

**설명**: 전체 재고 아이템 목록을 반환한다.

**프로시저**:
1. `traceparent` 헤더에서 span context 추출 → child span 생성
2. 인메모리 재고 저장소에서 전체 아이템 조회 (MVP: 초기값 하드코딩)
3. `inventory_stock_level` Gauge 현재값 포함
4. span 완료 → OTLP 전송

**성공 응답 (200)**:
```json
{
  "items": [
    {"item_id": "item-001", "name": "Widget A", "stock": 98},
    {"item_id": "item-002", "name": "Widget B", "stock": 50}
  ]
}
```

---

#### PUT /items/{item_id}/stock

**설명**: 특정 아이템의 재고를 차감한다 (주문 처리 시 order-svc에서 호출).

**프로시저**:
1. path parameter `item_id` 유효성 확인
2. `traceparent` 헤더에서 span context 추출 → child span 생성
3. 요청 바디 `delta` 값 유효성 검증 (음수 = 차감, 양수 = 증가)
4. 인메모리 재고 저장소에서 item_id 조회
5. 없으면 404 반환
6. `current_stock + delta < 0` 이면 409 (재고 부족) 반환
7. 재고 업데이트 및 `inventory_stock_level{item_id}` Gauge 갱신
8. leaf span 완료 → OTLP 전송
9. 200 OK 반환

**요청 바디**:
| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| `delta` | integer | Y | - | 재고 변화량 (음수: 차감, 양수: 증가) |

**요청 예시**:
```json
{"delta": -2}
```

**성공 응답 (200)**:
```json
{
  "item_id": "item-001",
  "previous_stock": 100,
  "current_stock": 98,
  "delta": -2
}
```

**에러 응답**:
- `400`: delta 값 누락 또는 0
- `404`: item_id가 존재하지 않음
- `409`: 재고 부족 (`current_stock + delta < 0`)

---

#### GET /metrics

**설명**: Prometheus 텍스트 형식 메트릭 노출 (inventory_stock_level Gauge 포함).

**성공 응답 (200)**:
```
# HELP inventory_stock_level Current stock level per item
# TYPE inventory_stock_level gauge
inventory_stock_level{item_id="item-001"} 98
inventory_stock_level{item_id="item-002"} 50
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",path="/items",status_code="200"} 30
```

---

#### GET /health

**설명**: 헬스체크.

**성공 응답 (200)**:
```json
{"status": "ok", "service": "inventory-svc"}
```

---

## Part 2. 인프라 컴포넌트 설정 스펙

### Prometheus Scrape 설정

#### ServiceMonitor CRD 스펙 (각 샘플 앱)

**프로시저** (Prometheus Operator가 ServiceMonitor를 처리하는 흐름):
1. Prometheus Operator가 모든 네임스페이스의 ServiceMonitor CRD watch
2. `serviceMonitorSelectorNilUsesHelmValues: false` 설정으로 레이블 제한 없이 수집
3. ServiceMonitor의 `selector.matchLabels`로 대상 Service 특정
4. `endpoints[].port`와 `path`로 scrape 대상 결정
5. Prometheus가 15초 간격으로 `GET /metrics` 요청

**frontend-svc ServiceMonitor**:
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: frontend-svc
  namespace: observability-demo
  labels:
    app: frontend-svc
spec:
  selector:
    matchLabels:
      app: frontend-svc
  endpoints:
    - port: http
      path: /metrics
      interval: 15s
  namespaceSelector:
    matchNames:
      - observability-demo
```

**order-svc ServiceMonitor** (동일 구조, port: 8081):
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: order-svc
  namespace: observability-demo
spec:
  selector:
    matchLabels:
      app: order-svc
  endpoints:
    - port: http
      path: /metrics
      interval: 15s
```

**inventory-svc ServiceMonitor** (동일 구조, port: 8082):
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: inventory-svc
  namespace: observability-demo
spec:
  selector:
    matchLabels:
      app: inventory-svc
  endpoints:
    - port: http
      path: /metrics
      interval: 15s
```

---

### Alertmanager 규칙 (PrometheusRule CRD)

**프로시저** (알림 규칙 평가 흐름):
1. Prometheus가 30초 간격으로 PrometheusRule 표현식 평가
2. 조건 만족 시 `for` 기간 동안 PENDING 상태 유지
3. PENDING 기간 경과 시 FIRING → Alertmanager로 전송
4. Alertmanager가 알림 수신 → receivers 처리 (MVP: 로그 기록)

| 규칙명 | PromQL 표현식 | for | 심각도 | 설명 |
|--------|-------------|-----|--------|------|
| `HighErrorRate` | `rate(http_requests_total{status_code=~"5..",namespace="observability-demo"}[5m]) / rate(http_requests_total{namespace="observability-demo"}[5m]) > 0.05` | 2m | critical | 에러율 5% 초과 |
| `HighP99Latency` | `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) > 1.0` | 2m | warning | P99 응답시간 1초 초과 |
| `PodNotReady` | `kube_pod_status_ready{condition="true",namespace="observability-demo"} == 0` | 1m | critical | 파드 Ready 아님 |

---

### Grafana 대시보드 프로비저닝

**프로시저** (Grafana 시작 시 대시보드 자동 로드 흐름):
1. Grafana Pod 시작 시 `/etc/grafana/provisioning/datasources/` 디렉토리 스캔
2. `datasources.yaml`에 정의된 데이터소스 자동 등록 (Prometheus, Loki, Jaeger)
3. `/etc/grafana/provisioning/dashboards/dashboards.yaml`의 provider 설정 로드
4. provider의 `path` 경로(`/var/lib/grafana/dashboards/custom`)에서 `*.json` 파일 자동 임포트
5. 재시작 없이 파일 변경 감지 후 대시보드 갱신 (`updateIntervalSeconds: 30`)

**datasources.yaml**:
```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus-operated.monitoring.svc.cluster.local:9090
    isDefault: true
    jsonData:
      timeInterval: "15s"

  - name: Loki
    type: loki
    url: http://loki.monitoring.svc.cluster.local:3100
    jsonData:
      derivedFields:
        - name: TraceID
          matcherRegex: '"trace_id":"(\w+)"'
          url: http://localhost:16686/trace/$${__value.raw}
          datasourceUid: jaeger

  - name: Jaeger
    uid: jaeger
    type: jaeger
    url: http://jaeger-query.tracing.svc.cluster.local:16686
```

**dashboards.yaml (provider)**:
```yaml
apiVersion: 1
providers:
  - name: custom
    folder: Mini-Obs-Platform
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    options:
      path: /var/lib/grafana/dashboards/custom
```

**대시보드 패널 정의**:

| 대시보드 | 파일 | 패널 | PromQL / LogQL | 설명 |
|---------|------|------|----------------|------|
| RED Metrics | `red-metrics.json` | Rate 시계열 | `rate(http_requests_total[5m])` | 서비스별 초당 요청 수 |
| RED Metrics | `red-metrics.json` | Error Rate 시계열 | `rate(http_requests_total{status_code=~"5.."}[5m]) / rate(http_requests_total[5m])` | 에러율 |
| RED Metrics | `red-metrics.json` | P99 Duration 시계열 | `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))` | P99 응답시간 |
| Service Map | `service-map.json` | Node Graph | Jaeger 데이터소스 | 서비스 토폴로지 |
| Logs Explorer | `logs-explorer.json` | Logs Panel | `{namespace="observability-demo"} \| json \| level="error"` | 에러 로그 스트림 |

---

### OTel Collector 파이프라인 스펙

**프로시저** (OTel Collector traces 처리 흐름):
1. 샘플 앱 OTel SDK에서 OTLP gRPC (`:4317`) 또는 HTTP (`:4318`)로 spans/metrics 수신
2. `memory_limiter` processor: 메모리 256MB 초과 시 데이터 드롭 (서비스 보호)
3. `batch` processor: 최대 10초 또는 8192 spans 누적 후 배치 전송 (네트워크 효율)
4. traces pipeline → Jaeger exporter (gRPC `:14250`)
5. metrics pipeline → Prometheus exporter (`:8889` HTTP scrape endpoint)
6. `health_check` extension: `/` 엔드포인트로 Collector 헬스 확인

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: "0.0.0.0:4317"
      http:
        endpoint: "0.0.0.0:4318"

processors:
  memory_limiter:
    limit_mib: 256
    spike_limit_mib: 64
    check_interval: 1s
  batch:
    timeout: 10s
    send_batch_size: 8192

exporters:
  jaeger:
    endpoint: "jaeger-collector.tracing.svc.cluster.local:14250"
    tls:
      insecure: true
  prometheus:
    endpoint: "0.0.0.0:8889"
    namespace: otelcol

extensions:
  health_check:
    endpoint: "0.0.0.0:13133"

service:
  extensions: [health_check]
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [jaeger]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [prometheus]
```

---

### Fluent Bit 로그 파이프라인 스펙

**프로시저** (로그 수집 흐름):
1. DaemonSet Pod가 각 노드의 `/var/log/containers/*.log` tail 감시
2. `multiline.parser: docker, cri` 로 멀티라인 로그 병합
3. `kubernetes` filter: K8s API 서버에서 pod_name, namespace, container_name 메타데이터 조회 후 로그에 주입
4. `Merge_Log On`: JSON 형식 stdout 로그의 필드(trace_id, level 등)를 최상위 필드로 병합
5. Loki output: namespace, pod, container 레이블로 스트림 구분하여 전송

```ini
[INPUT]
    Name              tail
    Path              /var/log/containers/*.log
    multiline.parser  docker, cri
    Tag               kube.*
    Mem_Buf_Limit     5MB
    Skip_Long_Lines   On

[FILTER]
    Name                kubernetes
    Match               kube.*
    Kube_URL            https://kubernetes.default.svc:443
    Merge_Log           On
    Keep_Log            Off
    K8S-Logging.Parser  On

[OUTPUT]
    Name   loki
    Match  kube.*
    Host   loki.monitoring.svc.cluster.local
    Port   3100
    Labels namespace=$kubernetes['namespace_name'],pod=$kubernetes['pod_name'],container=$kubernetes['container_name']
    Auto_Kubernetes_Labels On
```
