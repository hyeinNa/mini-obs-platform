# 기능명세서 — mini-obs-platform

**프로젝트명**: mini-obs-platform
**버전**: 1.0.0 (MVP)
**작성일**: 2026-03-29
**목적**: Instana Observability 파이프라인을 오픈소스 스택으로 재현한 미니 관측성 플랫폼

---

## 1. 시스템 구성

### 1-1. 샘플 마이크로서비스 (3개)

| ID | 서비스명 | 언어/프레임워크 | 포트 | 역할 |
|----|----------|----------------|------|------|
| SVC-01 | frontend-svc | Go 1.22 + net/http | 8080 | HTTP 게이트웨이, 클라이언트 요청을 하위 서비스로 프록시 |
| SVC-02 | order-svc | Python 3.11 + FastAPI | 8081 | 주문 생성/조회, inventory-svc 호출로 재고 차감 |
| SVC-03 | inventory-svc | Python 3.11 + FastAPI | 8082 | 재고 조회 및 차감 (인메모리 저장소) |

### 1-2. 인프라 컴포넌트 (8개)

| ID | 컴포넌트 | 버전 | 네임스페이스 | 역할 |
|----|----------|------|-------------|------|
| INFRA-01 | Prometheus | kube-prometheus-stack | monitoring | 메트릭 수집 (15초 scrape interval, 24h retention) |
| INFRA-02 | Grafana | 10.x | monitoring | 대시보드 시각화 (3개 대시보드) |
| INFRA-03 | Alertmanager | kube-prometheus-stack | monitoring | 알림 라우팅 (3개 PrometheusRule) |
| INFRA-04 | OTel Collector | otelcol-contrib | tracing | 트레이스/메트릭 라우팅 게이트웨이 |
| INFRA-05 | Jaeger | 1.x (all-in-one) | tracing | 분산 트레이스 저장 및 UI |
| INFRA-06 | Loki | 3.x | logging | 로그 저장 (168h retention) |
| INFRA-07 | Fluent Bit | 2.x (DaemonSet) | logging | 로그 수집 및 K8s 메타데이터 주입 |
| INFRA-08 | Chaos Mesh | 2.x | chaos-mesh | K8s CRD 기반 장애 주입 |

### 1-3. CI/CD 컴포넌트 (2개)

| ID | 컴포넌트 | 역할 |
|----|----------|------|
| CICD-01 | GitHub Actions | CI(lint+test+build) + CD(push+tag update) |
| CICD-02 | ArgoCD 2.x | GitOps 자동 배포 (App of Apps 패턴) |

---

## 2. 기능 목록

### FN-100: 샘플 앱 HTTP API

#### FN-101: 주문 생성

| 항목 | 내용 |
|------|------|
| 경로 | `POST /orders` (order-svc) |
| 진입점 | `GET /api/order` (frontend-svc → order-svc 프록시) |
| 요청 본문 | `{"item_id": "string", "quantity": int}` |
| 처리 절차 | 1. UUID 기반 order_id 생성 2. inventory-svc `PUT /items/{item_id}/stock` 호출 (delta=-quantity) 3. 재고 차감 성공 시 주문 저장 (인메모리) 4. 응답 반환 |
| 성공 응답 | `201 Created` `{"order_id": "uuid", "item_id": "...", "quantity": N, "status": "completed"}` |
| 실패 응답 | `409 Conflict` (재고 부족), `502 Bad Gateway` (inventory-svc 연결 실패) |
| OTel 계측 | trace span 생성, traceparent 헤더 하위 전파, 구조화 로그에 trace_id 포함 |

#### FN-102: 주문 조회

| 항목 | 내용 |
|------|------|
| 경로 | `GET /orders/{order_id}` (order-svc) |
| 성공 응답 | `200 OK` `{"order_id": "...", "item_id": "...", "quantity": N, "status": "..."}` |
| 실패 응답 | `404 Not Found` |

#### FN-103: 재고 조회

| 항목 | 내용 |
|------|------|
| 경로 | `GET /items` (inventory-svc) |
| 진입점 | `GET /api/inventory` (frontend-svc → inventory-svc 프록시) |
| 성공 응답 | `200 OK` `[{"item_id": "item-001", "name": "...", "stock": N}, ...]` |
| 초기 시드 데이터 | item-001(100), item-002(50), item-003(200) |

#### FN-104: 재고 차감

| 항목 | 내용 |
|------|------|
| 경로 | `PUT /items/{item_id}/stock` (inventory-svc) |
| 요청 본문 | `{"delta": int}` (음수: 차감, 양수: 추가) |
| 성공 응답 | `200 OK` `{"item_id": "...", "previous_stock": N, "current_stock": N, "delta": N}` |
| 실패 응답 | `404 Not Found` (존재하지 않는 아이템), `409 Conflict` (재고 부족), `400 Bad Request` (delta=0) |

#### FN-105: 헬스체크

| 항목 | 내용 |
|------|------|
| 경로 | `GET /health` (모든 서비스 공통) |
| 응답 | `200 OK` `{"status": "healthy", "service": "서비스명"}` |
| 용도 | K8s liveness/readiness probe |

#### FN-106: 메트릭 엔드포인트

| 항목 | 내용 |
|------|------|
| 경로 | `GET /metrics` (모든 서비스 공통) |
| 응답 | Prometheus exposition format (text/plain) |
| 수집 메트릭 | `http_requests_total{method, path, status_code}`, `http_request_duration_seconds{method, path}`, `orders_created_total` (order-svc), `inventory_stock_level{item_id}` (inventory-svc) |

---

### FN-200: Observability 파이프라인

#### FN-201: 메트릭 수집 파이프라인

| 항목 | 내용 |
|------|------|
| 수집 방식 | Prometheus ServiceMonitor CRD + Pod annotation |
| Scrape 대상 | frontend-svc, order-svc, inventory-svc, kube-state-metrics, node-exporter, OTel Collector |
| Scrape 간격 | 15초 |
| 보존 기간 | 24시간 |
| 커스텀 메트릭 | `orders_created_total` (Counter), `inventory_stock_level` (Gauge), `order_processing_duration_seconds` (Histogram) |

#### FN-202: 분산 트레이싱 파이프라인

| 항목 | 내용 |
|------|------|
| 계측 방식 | OpenTelemetry SDK (Go: otelhttp, Python: opentelemetry-instrumentation-fastapi) |
| 전송 프로토콜 | OTLP gRPC (:4317) |
| 경로 | 앱 → OTel Collector → Jaeger |
| 컨텍스트 전파 | W3C TraceContext (traceparent 헤더) |
| trace_id 형식 | 32자 hex string |
| span_id 형식 | 16자 hex string |
| Collector 프로세서 | batch, memory_limiter (256MiB) |
| 최대 저장 | 10,000 traces (Jaeger 메모리) |

#### FN-203: 로그 수집 파이프라인

| 항목 | 내용 |
|------|------|
| 수집 방식 | Fluent Bit DaemonSet (tail /var/log/containers/*.log) |
| 필터 | kubernetes filter (pod_name, namespace, container_name 메타데이터 주입) |
| 파서 | JSON (구조화 로그에서 trace_id, level, message 추출) |
| 전송 | Loki HTTP (:3100) |
| 라벨 | namespace, pod, container |
| 보존 기간 | 168시간 (7일) |
| 로그↔트레이스 연결 | Grafana Loki Derived Fields (trace_id regex → Jaeger URL) |

#### FN-204: 알림 규칙 (3개)

| 규칙 ID | 규칙명 | PromQL 조건 | for | 심각도 |
|---------|--------|------------|-----|--------|
| ALERT-01 | HighErrorRate | `rate(http_requests_total{status_code=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05` | 2분 | critical |
| ALERT-02 | HighP99Latency | `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) > 1.0` | 2분 | warning |
| ALERT-03 | PodNotReady | `kube_pod_status_ready{condition="true"} == 0` | 1분 | critical |

#### FN-205: Grafana 대시보드 (3개)

| 대시보드 ID | 이름 | 패널 수 | 주요 시각화 |
|------------|------|---------|------------|
| DASH-01 | RED Metrics | 10 | Request Rate/Error Rate/P99 Stat 패널 + 시계열 그래프 (서비스별) |
| DASH-02 | Service Map | 3 | Jaeger nodeGraph (서비스 토폴로지) + 레이턴시/요청률 시계열 |
| DASH-03 | Logs Explorer | 4 | Loki 로그볼륨/레벨 시계열 + 로그 스트림 + 에러 필터 (trace_id → Jaeger 링크) |

---

### FN-300: 장애 시뮬레이션 (Chaos Engineering)

#### FN-301: 네트워크 지연 주입

| 항목 | 내용 |
|------|------|
| CRD | NetworkChaos |
| 대상 | order-svc (observability-demo 네임스페이스) |
| 설정 | 500ms +/- 100ms 지연 |
| 지속시간 | 5분 |
| 관찰 포인트 | Grafana RED 대시보드 P99 레이턴시 상승, HighP99Latency 알림 트리거 |

#### FN-302: 파드 종료

| 항목 | 내용 |
|------|------|
| CRD | PodChaos (pod-kill) |
| 대상 | inventory-svc 파드 1개 |
| 지속시간 | 1분 |
| 관찰 포인트 | PodNotReady 알림 트리거, K8s 자동 복구 (ReplicaSet), Error Rate 일시 상승 후 정상화 |

---

### FN-400: CI/CD 파이프라인

#### FN-401: CI (Pull Request)

| 단계 | 내용 |
|------|------|
| 1. Python lint | `ruff check apps/order-svc/ apps/inventory-svc/` |
| 2. Python test | `pytest apps/order-svc/ apps/inventory-svc/` |
| 3. Go lint | `go vet ./...` (apps/frontend-svc) |
| 4. Go test | `go test ./...` (apps/frontend-svc) |
| 5. Helm lint | `helm lint infra/helm/*` |
| 6. Docker build | 3개 서비스 빌드 (push 없음) |

#### FN-402: CD (main push)

| 단계 | 내용 |
|------|------|
| 1. Docker build+push | `ghcr.io/<owner>/mini-obs-<svc>:<commit-sha>` |
| 2. 매니페스트 업데이트 | sed로 이미지 태그를 commit SHA로 교체 |
| 3. Git commit+push | 매니페스트 변경 자동 커밋 |
| 4. ArgoCD sync | 자동 감지 → 클러스터 sync (prune + selfHeal) |

#### FN-403: GitOps (ArgoCD)

| 항목 | 내용 |
|------|------|
| 패턴 | App of Apps |
| 최상위 Application | `infra/argocd/app-of-apps.yaml` |
| 하위 Application | 7개 (kube-prometheus-stack, otel-collector, jaeger, loki, fluent-bit, chaos-mesh, sample-apps) |
| Sync 정책 | automated (prune: true, selfHeal: true) |

---

### FN-500: 운영 스크립트

| ID | 스크립트 | 기능 |
|----|---------|------|
| SCR-01 | `scripts/setup-cluster.sh` | KIND 클러스터 생성 (idempotent), 사전 요구사항 체크 |
| SCR-02 | `scripts/teardown-cluster.sh` | 클러스터 삭제 + kubectl context 정리 |
| SCR-03 | `scripts/deploy-all.sh` | 전체 스택 순차 배포 (6단계) |
| SCR-04 | `scripts/port-forward.sh` | 4개 서비스 포트 포워딩 + Ctrl+C 정리 |
| SCR-05 | `scripts/run-chaos.sh` | Chaos 실험 apply/delete/status/list |
| SCR-06 | `scripts/e2e-test.sh` | curl 기반 E2E (헬스체크/메트릭/요청/trace_id 검증) |

---

## 3. 서비스 호출 체인

```
Client
  │
  ▼
frontend-svc (Go :8080)
  ├── GET /api/order
  │     └── order-svc (Python :8081) POST /orders
  │           └── inventory-svc (Python :8082) PUT /items/{id}/stock
  └── GET /api/inventory
        └── inventory-svc (Python :8082) GET /items
```

**trace 전파:**
```
frontend-svc [root span] ──traceparent──► order-svc [child span] ──traceparent──► inventory-svc [leaf span]
     │                                        │                                       │
     └─── trace_id: 32자 hex (동일) ──────────┴───────────────────────────────────────┘
```

---

## 4. 접근 포트

| 서비스 | K8s 내부 포트 | 외부 접근 (NodePort/port-forward) |
|--------|-------------|----------------------------------|
| frontend-svc | 8080 | localhost:8080 (port-forward) |
| order-svc | 8081 | localhost:8081 (port-forward) |
| inventory-svc | 8082 | localhost:8082 (port-forward) |
| Prometheus | 9090 | localhost:9090 (port-forward) |
| Grafana | 3000 | localhost:3000 (NodePort 30000) |
| Jaeger UI | 16686 | localhost:16686 (NodePort 30001) |
| ArgoCD UI | 8090 | localhost:8090 (NodePort 30002) |
| OTel Collector | 4317 (gRPC) | 클러스터 내부 전용 |
| Loki | 3100 | 클러스터 내부 전용 |

---

## 5. 네임스페이스 구조

| 네임스페이스 | 용도 | 포함 리소스 |
|-------------|------|------------|
| observability-demo | 샘플 앱 | frontend-svc, order-svc, inventory-svc (Deployment+Service+ServiceMonitor) |
| monitoring | 메트릭/시각화/알림 | Prometheus, Grafana, Alertmanager, PrometheusRule |
| tracing | 트레이싱 | OTel Collector, Jaeger |
| logging | 로그 | Loki, Fluent Bit |
| chaos-mesh | 장애 시뮬레이션 | Chaos Mesh Controller, NetworkChaos, PodChaos |

---

## 6. 제외 범위 (Out of Scope)

| 기능 | 제외 사유 |
|------|----------|
| 영구 데이터 저장 (PV) | MVP 단순화, emptyDir 사용 |
| Slack/PagerDuty 알림 연동 | PrometheusRule 작성 역량 증명으로 충분 |
| Istio 서비스 메시 | OTel SDK 계측으로 충분 |
| Thanos/Cortex 장기 저장 | 24h retention으로 시연 가능 |
| k6/Locust 부하 생성 | bash curl 루프로 대체 |
| 사용자 인증/권한 | 인프라 프로젝트, 앱 보안 범위 외 |
| Grafana Tempo | Jaeger 선택 (독립 UI 제공) |
| 프로덕션 멀티 환경 | 로컬 KIND 단일 환경 |
