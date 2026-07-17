# 서비스 플로우 — mini-obs-platform

---

## 1. 인프라 구성 다이어그램

```mermaid
graph TB
    subgraph KIND["KIND 클러스터 (1 control-plane, 2 worker)"]
        subgraph NS_DEMO["namespace: observability-demo"]
            FE["frontend-svc\n(Go 1.22)\n:8080"]
            ORD["order-svc\n(Python FastAPI)\n:8081"]
            INV["inventory-svc\n(Python FastAPI)\n:8082"]
        end

        subgraph NS_MONITORING["namespace: monitoring"]
            PROM["Prometheus\n:9090"]
            AM["Alertmanager\n:9093"]
            GRAFANA["Grafana\n:3000"]
            LOKI["Loki\n:3100"]
            FB["Fluent Bit\n(DaemonSet)"]
        end

        subgraph NS_TRACING["namespace: tracing"]
            OTEL["OTel Collector\nOTLP gRPC :4317\nOTLP HTTP :4318\nProm :8889"]
            JAEGER["Jaeger All-in-one\nUI :16686\ngRPC :14250"]
        end

        subgraph NS_CHAOS["namespace: chaos-mesh"]
            CHAOS["Chaos Mesh Controller"]
        end

        subgraph NS_ARGOCD["namespace: argocd"]
            ARGOCD["ArgoCD\n:8090"]
        end
    end

    USER["사용자 / Load Generator\n(localhost)"]
    GH["GitHub\n(Source of Truth)"]
    GHCR["ghcr.io\n(Container Registry)"]

    USER -->|":8080"| FE
    FE -->|"HTTP"| ORD
    ORD -->|"HTTP"| INV

    FE -->|"OTLP gRPC :4317"| OTEL
    ORD -->|"OTLP gRPC :4317"| OTEL
    INV -->|"OTLP gRPC :4317"| OTEL

    OTEL -->|"traces (gRPC :14250)"| JAEGER
    OTEL -->|"metrics scrape :8889"| PROM

    PROM -->|"scrape /metrics"| FE
    PROM -->|"scrape /metrics"| ORD
    PROM -->|"scrape /metrics"| INV
    PROM -->|"alert"| AM

    FB -->|"tail /var/log/containers"| FE
    FB -->|"tail /var/log/containers"| ORD
    FB -->|"tail /var/log/containers"| INV
    FB -->|"push logs"| LOKI

    GRAFANA -->|"PromQL"| PROM
    GRAFANA -->|"LogQL"| LOKI
    GRAFANA -->|"trace query"| JAEGER

    CHAOS -->|"NetworkChaos / PodChaos"| ORD
    CHAOS -->|"NetworkChaos / PodChaos"| INV

    GH -->|"Git poll / webhook"| ARGOCD
    ARGOCD -->|"K8s Apply"| NS_DEMO
    ARGOCD -->|"K8s Apply"| NS_MONITORING
    ARGOCD -->|"K8s Apply"| NS_TRACING

    GHCR -->|"image pull"| FE
    GHCR -->|"image pull"| ORD
    GHCR -->|"image pull"| INV
```

---

## 2. 전체 서비스 플로우차트

```mermaid
flowchart TD
    A[사용자 / 부하 생성기] --> B["GET http://localhost:8080/api/order"]
    B --> C[frontend-svc\nGo HTTP 게이트웨이]
    C -->|"OTel root span 생성\nW3C TraceContext 헤더 주입"| D["POST http://order-svc:8081/orders"]
    D --> E[order-svc\nPython FastAPI]
    E -->|"child span 생성"| F["GET http://inventory-svc:8082/items"]
    F --> G[inventory-svc\nPython FastAPI]
    G -->|"leaf span 완료 → 응답"| E
    E -->|"응답 + span 완료"| C
    C -->|"200 OK"| A

    C -->|"OTLP gRPC"| H[OTel Collector]
    E -->|"OTLP gRPC"| H
    G -->|"OTLP gRPC"| H

    H -->|"traces"| I[Jaeger]
    H -->|"metrics"| J[Prometheus]

    K[Fluent Bit DaemonSet] -->|"tail 수집"| L[파드 stdout/stderr]
    L --> K
    K -->|"push"| M[Loki]

    J -->|"scrape /metrics\n15초 간격"| C
    J -->|"scrape /metrics"| E
    J -->|"scrape /metrics"| G

    J --> N{알림 조건 평가}
    N -->|"임계값 초과"| O[Alertmanager]
    O -->|"알림 기록"| P[로그 파일]

    J --> Q[Grafana]
    M --> Q
    I --> Q
    Q --> R[RED 대시보드\n서비스맵\n로그 탐색기]
```

---

## 3. 시나리오별 시퀀스 다이어그램

### 3-1. 정상 요청 흐름 (Traces + Metrics 생성)

```mermaid
sequenceDiagram
    participant U as 사용자
    participant FE as frontend-svc (Go)
    participant ORD as order-svc (Python)
    participant INV as inventory-svc (Python)
    participant OTEL as OTel Collector
    participant JAEGER as Jaeger
    participant PROM as Prometheus
    participant FB as Fluent Bit
    participant LOKI as Loki

    U->>FE: GET /api/order
    FE->>FE: root span 생성 (trace_id 발급)
    FE->>FE: W3C TraceContext 헤더 주입
    FE->>ORD: POST /orders (traceparent 헤더 포함)
    ORD->>ORD: child span 생성 (parent span 연결)
    ORD->>INV: GET /items (traceparent 전파)
    INV->>INV: leaf span 생성
    INV-->>ORD: 200 OK (재고 정보)
    INV->>OTEL: OTLP gRPC (leaf span 전송)
    ORD-->>FE: 200 OK (주문 생성 결과)
    ORD->>OTEL: OTLP gRPC (child span + 메트릭 전송)
    FE-->>U: 200 OK
    FE->>OTEL: OTLP gRPC (root span + 메트릭 전송)

    OTEL->>JAEGER: traces (gRPC :14250)
    OTEL->>PROM: metrics expose (:8889 scrape endpoint)

    Note over FE,INV: 각 서비스 stdout에 trace_id 포함 구조화 로그 출력
    FB->>FB: /var/log/containers/*.log tail
    FB->>LOKI: push (namespace, pod, container 레이블 + trace_id)

    PROM->>FE: scrape GET /metrics
    PROM->>ORD: scrape GET /metrics
    PROM->>INV: scrape GET /metrics
```

---

### 3-2. 장애 감지 흐름 (Chaos → Alert → 분석)

```mermaid
sequenceDiagram
    participant ENG as 엔지니어
    participant CHAOS as Chaos Mesh
    participant ORD as order-svc
    participant PROM as Prometheus
    participant AM as Alertmanager
    participant GRAFANA as Grafana
    participant LOKI as Loki
    participant JAEGER as Jaeger

    ENG->>CHAOS: scripts/run-chaos.sh network-delay
    CHAOS->>ORD: NetworkChaos CRD 적용\n(500ms delay, 5분)

    Note over ORD: order-svc 응답 지연 시작

    PROM->>PROM: http_request_duration_seconds 상승 감지
    Note over PROM: 2분 경과 후 HighP99Latency 조건 만족
    PROM->>AM: alert 전송 (HighP99Latency: critical)
    AM->>AM: 알림 로그 기록

    ENG->>GRAFANA: RED 대시보드 확인
    GRAFANA->>PROM: histogram_quantile(0.99, ...) 쿼리
    PROM-->>GRAFANA: P99 레이턴시 스파이크 데이터
    ENG->>GRAFANA: 해당 시간대 로그 패널 드릴다운
    GRAFANA->>LOKI: LogQL 쿼리 (namespace="observability-demo", level="error")
    LOKI-->>GRAFANA: 느린 요청 로그 (trace_id 포함)
    ENG->>GRAFANA: trace_id 클릭 → Jaeger 연결
    GRAFANA->>JAEGER: trace 조회 (trace_id)
    JAEGER-->>GRAFANA: 전체 span 트리 (order-svc 지연 확인)

    ENG->>CHAOS: kubectl delete networkchaos --all
    Note over ORD: 네트워크 지연 해제
    PROM->>GRAFANA: 메트릭 정상화 확인
```

---

### 3-3. Chaos Engineering 흐름 (파드 종료 → 재스케줄링 관찰)

```mermaid
sequenceDiagram
    participant ENG as 엔지니어
    participant CHAOS as Chaos Mesh
    participant K8S as K8s Controller
    participant INV as inventory-svc
    participant PROM as Prometheus
    participant AM as Alertmanager
    participant GRAFANA as Grafana
    participant JAEGER as Jaeger

    ENG->>CHAOS: scripts/run-chaos.sh pod-kill
    CHAOS->>INV: PodChaos CRD 적용 (pod-kill)
    INV-->>INV: 파드 강제 종료

    K8S->>K8S: Deployment 컨트롤러 감지\n새 파드 스케줄링 시작

    Note over INV: 재시작 기간 (10~30초)\ninventory-svc 호출 실패 발생

    PROM->>PROM: kube_pod_status_ready{app="inventory-svc"} == 0 감지
    PROM->>PROM: http_requests_total{status_code=~"5.."} 상승 감지
    PROM->>AM: PodNotReady alert 전송
    PROM->>AM: HighErrorRate alert 전송
    AM->>AM: 알림 로그 기록

    ENG->>GRAFANA: inventory-svc 에러율 확인
    GRAFANA->>PROM: 에러율 쿼리
    PROM-->>GRAFANA: 에러율 100% 데이터

    K8S->>INV: 새 파드 Ready 상태 전환
    PROM->>PROM: 알림 조건 해소 감지
    GRAFANA->>JAEGER: 실패 trace span 확인
    JAEGER-->>GRAFANA: 에러 status code, 예외 메시지
    ENG->>GRAFANA: 자동 복구 후 메트릭 정상화 확인
```

---

### 3-4. GitOps 배포 흐름 (코드 push → CI → ArgoCD → K8s)

```mermaid
sequenceDiagram
    participant DEV as 개발자
    participant GH as GitHub
    participant CI as GitHub Actions (CI)
    participant CD as GitHub Actions (CD)
    participant GHCR as ghcr.io
    participant ARGOCD as ArgoCD
    participant K8S as Kubernetes

    DEV->>GH: git push (main 브랜치)

    GH->>CI: PR 트리거 (ci.yaml)
    CI->>CI: Python ruff lint + pytest
    CI->>CI: Go vet + go test ./...
    CI->>CI: Docker build (push 없음, 빌드 검증)
    CI->>CI: helm lint infra/helm/*/

    GH->>CD: main push 트리거 (cd.yaml)
    CD->>GHCR: docker build + push\nghcr.io/<owner>/mini-obs-order-svc:<commit-sha>
    CD->>GH: infra/helm/sample-apps/values.yaml\norderSvc.image.tag 자동 업데이트 (commit)

    Note over ARGOCD: Git polling (3분 주기) 또는 webhook
    ARGOCD->>GH: values.yaml 변경 감지
    ARGOCD->>GHCR: 새 이미지 pull
    ARGOCD->>K8S: order-svc Deployment 롤링 업데이트 적용
    K8S-->>ARGOCD: Synced / Healthy 상태 반환

    DEV->>ARGOCD: ArgoCD UI 배포 상태 확인 (http://localhost:8090)
    DEV->>ARGOCD: Grafana 배포 전후 메트릭 비교
```

---

## 4. 데이터 모델 ERD (인프라 컴포넌트 관계)

```mermaid
erDiagram
    KIND_CLUSTER ||--o{ NAMESPACE : contains
    NAMESPACE ||--o{ DEPLOYMENT : contains
    NAMESPACE ||--o{ SERVICE : contains
    NAMESPACE ||--o{ CONFIGMAP : contains
    NAMESPACE ||--o{ SECRET : contains
    DEPLOYMENT ||--o{ POD : manages
    POD ||--|| SERVICE : "exposed by"
    SERVICE ||--o{ SERVICE_MONITOR : "monitored by"
    SERVICE_MONITOR ||--|| PROMETHEUS : "scraped by"
    PROMETHEUS ||--o{ PROMETHEUS_RULE : evaluates
    PROMETHEUS_RULE ||--|| ALERTMANAGER : "triggers"
    POD ||--|| OTEL_COLLECTOR : "exports traces/metrics to"
    OTEL_COLLECTOR ||--|| JAEGER : "exports traces to"
    OTEL_COLLECTOR ||--|| PROMETHEUS : "exposes metrics for"
    POD ||--|| FLUENT_BIT : "logs collected by"
    FLUENT_BIT ||--|| LOKI : "pushes logs to"
    GRAFANA ||--|| PROMETHEUS : "queries"
    GRAFANA ||--|| LOKI : "queries"
    GRAFANA ||--|| JAEGER : "queries"
    ARGOCD_APPLICATION ||--|| GIT_REPO : "watches"
    ARGOCD_APPLICATION ||--|| NAMESPACE : "deploys to"
    CHAOS_EXPERIMENT ||--|| POD : "targets"

    KIND_CLUSTER {
        string name
        string apiVersion
        string k8s_version
        int control_plane_count
        int worker_count
    }

    NAMESPACE {
        string name
        string purpose
    }

    DEPLOYMENT {
        string name
        string namespace
        string image
        string image_tag
        int replicas
        map resource_limits
        map resource_requests
    }

    SERVICE_MONITOR {
        string name
        string namespace
        string scrape_interval
        string metrics_path
        int port
    }

    PROMETHEUS_RULE {
        string name
        string alert_name
        string expr
        string severity
        string for_duration
    }

    OTEL_COLLECTOR {
        string receiver_otlp_grpc_endpoint
        string receiver_otlp_http_endpoint
        string exporter_jaeger_endpoint
        string exporter_prometheus_endpoint
        int memory_limit_mib
    }
```
