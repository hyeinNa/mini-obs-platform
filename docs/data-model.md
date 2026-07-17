# 인프라 구성 모델 — mini-obs-platform

이 문서는 전통적인 데이터베이스 스키마 대신 **K8s 리소스 구성 모델**과 **인프라 컴포넌트 설정 구조**를 정의합니다.

---

## 1. 네임스페이스 구성 모델

| 네임스페이스 | 용도 | 주요 리소스 |
|-------------|------|------------|
| `observability-demo` | 샘플 마이크로서비스 | frontend-svc, order-svc, inventory-svc Deployments, Services, ServiceMonitors |
| `monitoring` | 메트릭/로그/알림 스택 | Prometheus, Alertmanager, Grafana, Loki, Fluent Bit |
| `tracing` | 분산 트레이싱 스택 | Jaeger, OTel Collector |
| `chaos-mesh` | 장애 시뮬레이션 | Chaos Mesh Controller, NetworkChaos/PodChaos CRDs |
| `argocd` | GitOps 배포 자동화 | ArgoCD Server, Application Controller, Repo Server |

---

## 2. K8s 리소스 정의

### 2-1. Deployment 리소스 모델

#### frontend-svc Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend-svc
  namespace: observability-demo
  labels:
    app: frontend-svc
    version: "1.0.0"
spec:
  replicas: 1
  selector:
    matchLabels:
      app: frontend-svc
  template:
    metadata:
      labels:
        app: frontend-svc
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      containers:
        - name: frontend-svc
          image: ghcr.io/<owner>/mini-obs-frontend-svc:<tag>
          ports:
            - name: http
              containerPort: 8080
          env:
            - name: ORDER_SVC_URL
              value: "http://order-svc.observability-demo.svc.cluster.local:8081"
            - name: INVENTORY_SVC_URL
              value: "http://inventory-svc.observability-demo.svc.cluster.local:8082"
            - name: OTEL_EXPORTER_OTLP_ENDPOINT
              value: "http://otel-collector.tracing.svc.cluster.local:4317"
            - name: OTEL_SERVICE_NAME
              value: "frontend-svc"
          resources:
            requests:
              cpu: "100m"
              memory: "64Mi"
            limits:
              cpu: "200m"
              memory: "128Mi"
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 15
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
```

#### order-svc Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-svc
  namespace: observability-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: order-svc
  template:
    metadata:
      labels:
        app: order-svc
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8081"
        prometheus.io/path: "/metrics"
    spec:
      containers:
        - name: order-svc
          image: ghcr.io/<owner>/mini-obs-order-svc:<tag>
          ports:
            - name: http
              containerPort: 8081
          env:
            - name: INVENTORY_SVC_URL
              value: "http://inventory-svc.observability-demo.svc.cluster.local:8082"
            - name: OTEL_EXPORTER_OTLP_ENDPOINT
              value: "http://otel-collector.tracing.svc.cluster.local:4317"
            - name: OTEL_SERVICE_NAME
              value: "order-svc"
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "300m"
              memory: "256Mi"
```

#### inventory-svc Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inventory-svc
  namespace: observability-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: inventory-svc
  template:
    metadata:
      labels:
        app: inventory-svc
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8082"
        prometheus.io/path: "/metrics"
    spec:
      containers:
        - name: inventory-svc
          image: ghcr.io/<owner>/mini-obs-inventory-svc:<tag>
          ports:
            - name: http
              containerPort: 8082
          env:
            - name: OTEL_EXPORTER_OTLP_ENDPOINT
              value: "http://otel-collector.tracing.svc.cluster.local:4317"
            - name: OTEL_SERVICE_NAME
              value: "inventory-svc"
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "300m"
              memory: "256Mi"
```

---

### 2-2. Service 리소스 모델

| Service명 | 네임스페이스 | 포트 | 타입 | 용도 |
|----------|------------|------|------|------|
| `frontend-svc` | observability-demo | 8080 | ClusterIP | 내부 접근 (port-forward 또는 Ingress) |
| `order-svc` | observability-demo | 8081 | ClusterIP | 내부 서비스 간 통신 |
| `inventory-svc` | observability-demo | 8082 | ClusterIP | 내부 서비스 간 통신 |
| `otel-collector` | tracing | 4317 (gRPC), 4318 (HTTP) | ClusterIP | OTel 수집 엔드포인트 |
| `jaeger-query` | tracing | 16686 (UI) | NodePort 30001 | Jaeger UI 외부 접근 |
| `loki` | monitoring | 3100 | ClusterIP | Loki HTTP API |
| `prometheus-operated` | monitoring | 9090 | ClusterIP | Prometheus API |
| `grafana` | monitoring | 3000 | NodePort 30000 | Grafana UI 외부 접근 |
| `argocd-server` | argocd | 80/443 | NodePort 30002 | ArgoCD UI 외부 접근 |

---

### 2-3. ConfigMap 리소스 모델

| ConfigMap명 | 네임스페이스 | 내용 | 용도 |
|------------|------------|------|------|
| `otel-collector-config` | tracing | receivers/processors/exporters/pipelines 설정 | OTel Collector 파이프라인 구성 |
| `fluent-bit-config` | monitoring | INPUT/FILTER/OUTPUT 설정 | 로그 수집 파이프라인 |
| `grafana-datasources` | monitoring | datasources.yaml | Grafana 데이터소스 자동 등록 |
| `grafana-dashboards-provider` | monitoring | dashboards.yaml | 대시보드 프로비저닝 경로 설정 |
| `grafana-dashboard-red-metrics` | monitoring | red-metrics.json | RED 메트릭 대시보드 정의 |
| `grafana-dashboard-service-map` | monitoring | service-map.json | 서비스 토폴로지 대시보드 |
| `grafana-dashboard-logs-explorer` | monitoring | logs-explorer.json | 로그+트레이스 탐색 대시보드 |

---

### 2-4. ArgoCD Application 리소스 모델

#### App of Apps 구조

```
app-of-apps (Application)
├── kube-prometheus-stack (Application) → infra/helm/kube-prometheus-stack/
├── loki-stack (Application)            → infra/helm/loki-stack/
├── fluent-bit (Application)            → infra/helm/fluent-bit/
├── jaeger (Application)                → infra/helm/jaeger/
├── otel-collector (Application)        → infra/helm/otel-collector/
├── chaos-mesh (Application)            → infra/helm/chaos-mesh/
└── sample-apps (Application)           → infra/manifests/sample-apps/
```

**Application CRD 공통 설정**:
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/<owner>/mini-obs-platform
    targetRevision: HEAD
  destination:
    server: https://kubernetes.default.svc
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

---

### 2-5. Chaos Experiment 리소스 모델

#### NetworkChaos

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: order-svc-network-delay
  namespace: observability-demo
spec:
  action: delay
  mode: all
  selector:
    namespaces:
      - observability-demo
    labelSelectors:
      app: order-svc
  delay:
    latency: "500ms"
    jitter: "100ms"
    correlation: "25"
  duration: "5m"
```

#### PodChaos

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: inventory-svc-pod-kill
  namespace: observability-demo
spec:
  action: pod-kill
  mode: one
  selector:
    namespaces:
      - observability-demo
    labelSelectors:
      app: inventory-svc
  duration: "1m"
  gracePeriod: 0
```

---

## 3. Helm Values 구조

### 3-1. kube-prometheus-stack values.yaml 구조

```
kube-prometheus-stack/values.yaml
├── grafana
│   ├── enabled: true
│   ├── adminPassword: admin
│   ├── persistence.enabled: false
│   ├── additionalDataSources[]        # Loki, Jaeger 데이터소스
│   └── dashboardProviders             # custom provider 경로
├── prometheus
│   └── prometheusSpec
│       ├── serviceMonitorSelectorNilUsesHelmValues: false
│       ├── ruleSelectorNilUsesHelmValues: false
│       └── retention: 24h
└── alertmanager
    └── config
        ├── receivers[]: [{name: default}]
        └── route.receiver: default
```

### 3-2. sample-apps values.yaml 구조 (이미지 태그 관리)

```yaml
frontendSvc:
  image:
    repository: ghcr.io/<owner>/mini-obs-frontend-svc
    tag: "latest"          # CD 파이프라인이 commit SHA로 자동 업데이트
  replicas: 1
  port: 8080

orderSvc:
  image:
    repository: ghcr.io/<owner>/mini-obs-order-svc
    tag: "latest"
  replicas: 1
  port: 8081

inventorySvc:
  image:
    repository: ghcr.io/<owner>/mini-obs-inventory-svc
    tag: "latest"
  replicas: 1
  port: 8082

otelEndpoint: "http://otel-collector.tracing.svc.cluster.local:4317"
```

### 3-3. otel-collector values.yaml 구조

```
otel-collector/values.yaml
├── config
│   ├── receivers.otlp.protocols
│   │   ├── grpc.endpoint: "0.0.0.0:4317"
│   │   └── http.endpoint: "0.0.0.0:4318"
│   ├── processors
│   │   ├── batch.timeout: 10s
│   │   └── memory_limiter.limit_mib: 256
│   ├── exporters
│   │   ├── jaeger.endpoint: "jaeger-collector.tracing...:14250"
│   │   └── prometheus.endpoint: "0.0.0.0:8889"
│   └── service.pipelines
│       ├── traces: {receivers:[otlp], processors:[memory_limiter,batch], exporters:[jaeger]}
│       └── metrics: {receivers:[otlp], processors:[memory_limiter,batch], exporters:[prometheus]}
└── ports
    ├── 4317: otlp-grpc
    ├── 4318: otlp-http
    └── 8889: prometheus
```

---

## 4. OTel 계측 모델

### 4-1. 트레이스 컨텍스트 전파 구조

```
외부 요청 (traceparent 없음)
  → frontend-svc: trace_id="abc123", span_id="span-001" (root span)
      → traceparent: "00-abc123-span-001-01" 헤더에 주입
      → order-svc: span_id="span-002" (child span, parent="span-001")
          → traceparent: "00-abc123-span-002-01" 헤더에 주입
          → inventory-svc: span_id="span-003" (child span, parent="span-002")
              → leaf span 완료
```

### 4-2. 메트릭 레이블 구조

**공통 메트릭 (모든 서비스)**:
| 메트릭명 | 타입 | 레이블 | 설명 |
|---------|------|--------|------|
| `http_requests_total` | Counter | `method`, `path`, `status_code`, `service` | HTTP 요청 수 |
| `http_request_duration_seconds` | Histogram | `method`, `path`, `service` | 응답시간 분포 |

**order-svc 커스텀 메트릭**:
| 메트릭명 | 타입 | 레이블 | 설명 |
|---------|------|--------|------|
| `orders_created_total` | Counter | - | 생성된 총 주문 수 |
| `order_processing_duration_seconds` | Histogram | - | 주문 처리 시간 분포 |

**inventory-svc 커스텀 메트릭**:
| 메트릭명 | 타입 | 레이블 | 설명 |
|---------|------|--------|------|
| `inventory_stock_level` | Gauge | `item_id` | 아이템별 현재 재고 수준 |

### 4-3. 구조화 로그 형식

모든 서비스가 출력하는 JSON 구조화 로그:

```json
{
  "timestamp": "2026-03-28T10:00:00.000Z",
  "level": "info",
  "service": "order-svc",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "message": "Order created successfully",
  "order_id": "ord-550e8400",
  "item_id": "item-001",
  "duration_ms": 45
}
```

Fluent Bit `Merge_Log On` 설정으로 위 JSON 필드가 Loki 로그 레코드 최상위 필드로 병합됨.

---

## 5. 포트 매핑 요약

### KIND 클러스터 포트 매핑

| 호스트 포트 | 컨테이너 포트 | 서비스 | 용도 |
|-----------|------------|-------|------|
| 80 | 80 | NGINX Ingress | HTTP Ingress |
| 443 | 443 | NGINX Ingress | HTTPS Ingress |
| 3000 | 30000 | Grafana | Grafana UI |
| 16686 | 30001 | Jaeger | Jaeger UI |
| 8090 | 30002 | ArgoCD | ArgoCD UI |

### 서비스 내부 포트

| 서비스 | 네임스페이스 | 포트 | 프로토콜 |
|-------|------------|------|---------|
| frontend-svc | observability-demo | 8080 | HTTP |
| order-svc | observability-demo | 8081 | HTTP |
| inventory-svc | observability-demo | 8082 | HTTP |
| otel-collector | tracing | 4317 | gRPC (OTLP) |
| otel-collector | tracing | 4318 | HTTP (OTLP) |
| otel-collector | tracing | 8889 | HTTP (Prometheus scrape) |
| jaeger-collector | tracing | 14250 | gRPC |
| jaeger-query | tracing | 16686 | HTTP |
| loki | monitoring | 3100 | HTTP |
| prometheus-operated | monitoring | 9090 | HTTP |
| alertmanager-operated | monitoring | 9093 | HTTP |
| grafana | monitoring | 3000 | HTTP |

---

## 6. GitHub Actions 워크플로우 구성 모델

### CI (ci.yaml) — PR 트리거

| 단계 | 언어/도구 | 명령 | 성공 조건 |
|-----|---------|------|---------|
| Python lint | ruff | `ruff check apps/order-svc/ apps/inventory-svc/` | 0 violations |
| Python test | pytest | `pytest apps/order-svc/ apps/inventory-svc/` | 모든 테스트 통과 |
| Go vet | go | `go vet ./...` (apps/frontend-svc/) | 0 errors |
| Go test | go | `go test ./...` (apps/frontend-svc/) | 모든 테스트 통과 |
| Docker build | Docker | `docker build` (push 없음) | 이미지 빌드 성공 |
| Helm lint | helm | `helm lint infra/helm/*/` | 0 errors |

### CD (cd.yaml) — main push 트리거

| 단계 | 도구 | 결과물 |
|-----|------|-------|
| Docker build + push | Docker | `ghcr.io/<owner>/mini-obs-<svc>:<commit-sha>` |
| values.yaml 업데이트 | git | `infra/helm/sample-apps/values.yaml` 이미지 태그 업데이트 |
| ArgoCD sync (자동) | ArgoCD | K8s 롤링 업데이트 완료 |
