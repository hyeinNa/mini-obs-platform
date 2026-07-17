# 프로젝트 요구사항

---

## 1. 프로젝트 개요

**프로젝트명**: mini-obs-platform
**한 줄 설명**: Instana가 내부적으로 처리하는 Observability 파이프라인을 오픈소스 스택(Prometheus, Grafana, OpenTelemetry, Jaeger, Loki)으로 직접 재현한 미니 관측성 플랫폼
**목적**: IBM Instana Engineer로서 축적한 Observability 도메인 지식을 바탕으로, 오픈소스 스택을 직접 설계·구현·운영하여 클라우드/K8s 인프라 및 모니터링 직무 역량을 증명한다.

**포트폴리오 스토리라인**:
> Instana Engineer로 근무하며 APM이 내부적으로 어떻게 메트릭을 수집하고, 트레이스를 연결하며, 로그를 구조화하는지 깊이 이해하게 되었다.
> 이 지식을 기반으로, Instana가 상용 제품으로 추상화한 것들을 오픈소스 컴포넌트로 직접 조립하여
> "내가 이 도구들의 작동 원리를 안다"는 것을 코드로 증명하는 프로젝트를 만들었다.
> 샘플 마이크로서비스에 OTel SDK를 계측하고, Chaos Engineering으로 장애를 직접 주입한 뒤,
> Grafana 대시보드에서 RED 메트릭 변화를 실시간으로 관찰하고 Alertmanager 알림이 트리거되는 전체 흐름을 구현했다.

**증명하는 직무 역량**:
- 클라우드 및 Kubernetes 기반 인프라 구축 및 운영
- CI/CD 파이프라인 구축 (IaC, GitOps via ArgoCD)
- 모니터링 및 로그 기반 인프라 장애 원인 분석
- Prometheus, Grafana 등 모니터링 도구 직접 운영
- 인프라 성능 지표 모니터링을 통한 최적화 시뮬레이션

---

## 2. 기술 스택

| 항목 | 기술 | 선택 근거 |
|------|------|-----------|
| 컨테이너 오케스트레이션 | Kubernetes (KIND 1.29) | 로컬 K8s 클러스터, 이직 타겟 기술 스택과 일치 |
| 패키지 배포 | Helm 3.x | K8s 애플리케이션 표준 패키지 관리자 |
| GitOps | ArgoCD 2.x | 선언적 K8s 배포 자동화, GitOps 역량 증명 |
| CI/CD | GitHub Actions | 코드 push → 이미지 빌드 → ArgoCD sync 트리거 |
| 메트릭 수집 | Prometheus (kube-prometheus-stack Helm chart) | K8s 모니터링 업계 표준, Instana 비교 포인트 |
| 메트릭 시각화/대시보드 | Grafana 10.x | 다중 데이터소스 통합 시각화, RED 메트릭 대시보드 |
| 알림 | Alertmanager (kube-prometheus-stack 포함) | PrometheusRule CRD로 선언적 알림 규칙 관리 |
| 분산 트레이싱 SDK | OpenTelemetry SDK (Python, Go) | 벤더 중립 계측 표준, Instana의 오픈소스 대응점 |
| 트레이싱 백엔드 | Jaeger 1.x (All-in-one) | CNCF 프로젝트, OTel Collector OTLP 수신 지원 |
| OTel 파이프라인 | OpenTelemetry Collector (otelcol-contrib) | 트레이스/메트릭 라우팅 게이트웨이 |
| 로그 수집 | Fluent Bit (DaemonSet) | 경량, K8s 메타데이터 자동 주입, Helm chart 제공 |
| 로그 백엔드 | Grafana Loki 3.x | Prometheus-like 로그 쿼리(LogQL), Grafana 네이티브 통합 |
| 장애 시뮬레이션 | Chaos Mesh 2.x | K8s CRD 기반 선언적 카오스 실험, NetworkChaos/PodChaos |
| 샘플 앱 언어 | Go 1.22 (frontend-svc), Python 3.11 (order-svc, inventory-svc) | 이직 타겟 직무 주요 언어, OTel SDK 모두 지원 |
| 컨테이너 이미지 | Docker + GitHub Container Registry (ghcr.io) | CI/CD 파이프라인 이미지 빌드·배포 연동 |
| IaC | Helm values.yaml + K8s manifests (선언적 관리) | GitOps 원칙 준수 |

---

## 3. 프로젝트 구조

```
mini-obs-platform/
├── apps/                              # 샘플 마이크로서비스 소스코드
│   ├── frontend-svc/                  # Go 기반 HTTP 게이트웨이 서비스
│   │   ├── main.go
│   │   ├── handler.go                 # /api/order, /api/inventory 프록시
│   │   ├── otel.go                    # OTel SDK 초기화 (trace + metric)
│   │   ├── Dockerfile
│   │   └── go.mod
│   ├── order-svc/                     # Python FastAPI 주문 서비스
│   │   ├── main.py
│   │   ├── otel_setup.py              # OTel SDK 초기화
│   │   ├── metrics.py                 # prometheus_client 커스텀 메트릭
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── inventory-svc/                 # Python FastAPI 재고 서비스
│       ├── main.py
│       ├── otel_setup.py
│       ├── metrics.py
│       ├── requirements.txt
│       └── Dockerfile
│
├── infra/                             # 인프라 선언 (GitOps 소스)
│   ├── argocd/                        # ArgoCD App of Apps 구성
│   │   ├── apps/                      # 각 컴포넌트 ArgoCD Application manifest
│   │   │   ├── app-of-apps.yaml       # 최상위 Application (하위 앱 관리)
│   │   │   ├── kube-prometheus-stack.yaml
│   │   │   ├── loki-stack.yaml
│   │   │   ├── fluent-bit.yaml
│   │   │   ├── jaeger.yaml
│   │   │   ├── otel-collector.yaml
│   │   │   ├── chaos-mesh.yaml
│   │   │   └── sample-apps.yaml
│   │   └── install/                   # ArgoCD 최초 설치 manifest
│   │       └── argocd-install.yaml
│   │
│   ├── helm/                          # Helm values 오버라이드 파일
│   │   ├── kube-prometheus-stack/
│   │   │   └── values.yaml            # Prometheus + Alertmanager + Grafana 설정
│   │   ├── loki-stack/
│   │   │   └── values.yaml            # Loki 설정
│   │   ├── fluent-bit/
│   │   │   └── values.yaml            # Fluent Bit DaemonSet 설정
│   │   ├── jaeger/
│   │   │   └── values.yaml            # Jaeger all-in-one 설정
│   │   ├── otel-collector/
│   │   │   └── values.yaml            # OTel Collector 파이프라인 설정
│   │   └── chaos-mesh/
│   │       └── values.yaml
│   │
│   ├── manifests/                     # 커스텀 K8s 리소스
│   │   ├── namespaces.yaml            # observability-demo, monitoring, tracing 네임스페이스
│   │   ├── sample-apps/               # 샘플 앱 Deployment + Service + ServiceMonitor
│   │   │   ├── frontend-svc.yaml
│   │   │   ├── order-svc.yaml
│   │   │   └── inventory-svc.yaml
│   │   ├── prometheus-rules/          # PrometheusRule CRD (알림 규칙)
│   │   │   └── app-alerts.yaml
│   │   └── chaos-experiments/         # Chaos Mesh CRD 실험 정의
│   │       ├── network-delay.yaml     # order-svc 네트워크 지연 주입
│   │       └── pod-kill.yaml          # inventory-svc 파드 종료
│   │
│   └── grafana/                       # Grafana 프로비저닝 파일
│       ├── provisioning/
│       │   ├── datasources/
│       │   │   └── datasources.yaml   # Prometheus + Loki + Jaeger 데이터소스
│       │   └── dashboards/
│       │       └── dashboards.yaml    # 대시보드 자동 로드 설정
│       └── dashboards/
│           ├── red-metrics.json       # RED 메트릭 대시보드
│           ├── service-map.json       # 서비스 토폴로지 대시보드
│           └── logs-explorer.json     # 로그 + 트레이스 연동 대시보드
│
├── .github/
│   └── workflows/
│       ├── ci.yaml                    # PR: lint + test + docker build (push 없음)
│       └── cd.yaml                   # main push: docker build + push + ArgoCD sync
│
├── scripts/
│   ├── cluster-setup.sh               # KIND 클러스터 + Ingress 초기 설정
│   ├── deploy-observability.sh        # observability 스택 ArgoCD 동기화
│   └── run-chaos.sh                   # 장애 시뮬레이션 실험 실행 헬퍼
│
├── docs/
│   ├── architecture.md               # 전체 아키텍처 설명
│   └── chaos-runbook.md              # 장애 시뮬레이션 시나리오 및 관찰 포인트
│
├── kind-config.yaml                   # KIND 클러스터 설정 (포트 매핑 포함)
└── README.md
```

---

## 4. 핵심 기능

### 4-1. 샘플 마이크로서비스 앱

3개 서비스로 구성된 최소 마이크로서비스 아키텍처. 모든 서비스는 OTel SDK로 계측된다.

| 서비스 | 언어 | 역할 | 포트 | 엔드포인트 |
|--------|------|------|------|-----------|
| frontend-svc | Go 1.22 | HTTP 게이트웨이, 클라이언트 요청 수신 후 하위 서비스 호출 | 8080 | `GET /api/order`, `GET /api/inventory`, `GET /metrics`, `GET /health` |
| order-svc | Python 3.11 + FastAPI | 주문 처리 로직, inventory-svc 호출 | 8081 | `POST /orders`, `GET /orders/{id}`, `GET /metrics`, `GET /health` |
| inventory-svc | Python 3.11 + FastAPI | 재고 조회 및 차감 로직 | 8082 | `GET /items`, `PUT /items/{id}/stock`, `GET /metrics`, `GET /health` |

**OTel 계측 범위**:
- HTTP 요청/응답 trace span 자동 생성 (opentelemetry-instrumentation-fastapi, otelhttp)
- 서비스 간 trace context 전파 (W3C TraceContext 헤더)
- 구조화 로그에 `trace_id`, `span_id` 자동 주입
- 커스텀 메트릭: `http_requests_total{method, path, status_code}`, `http_request_duration_seconds{method, path}`

### 4-2. 메트릭 수집 파이프라인

- **Prometheus scrape 대상**: 샘플 앱 3개 (`/metrics`), kube-state-metrics, node-exporter
- **ServiceMonitor CRD**: 각 서비스별 ServiceMonitor로 Prometheus Operator에 scrape 대상 선언
- **Pod annotation 방식 병행**: `prometheus.io/scrape: "true"`, `prometheus.io/port: "8080"`, `prometheus.io/path: "/metrics"`
- **커스텀 exporter**: order-svc와 inventory-svc에 `prometheus_client` 라이브러리로 비즈니스 메트릭 추가
  - `orders_created_total` (Counter): 생성된 주문 수
  - `inventory_stock_level{item_id}` (Gauge): 현재 재고 수준
  - `order_processing_duration_seconds` (Histogram): 주문 처리 시간 분포

### 4-3. 분산 트레이싱 파이프라인

```
샘플 앱 (OTel SDK)
  → OTLP gRPC (4317)
  → OTel Collector (otelcol-contrib)
      ├── processors: batch, memory_limiter, resource (service.name 주입)
      ├── exporters: jaeger (14250), prometheus (8889)
      └── extensions: health_check, pprof
  → Jaeger (16686 UI, 14250 gRPC 수신)
```

- Jaeger All-in-one 배포 (메모리 저장, MVP 단순화)
- OTel Collector가 traces → Jaeger, metrics → Prometheus 분기 처리
- Grafana Jaeger 데이터소스 연결로 대시보드 내 trace 드릴다운 가능

### 4-4. 로그 수집 파이프라인

```
Pod stdout/stderr (/var/log/containers/*.log)
  → Fluent Bit DaemonSet (tail input)
      ├── Kubernetes Filter: pod_name, namespace, container_name 메타데이터 주입
      ├── Parser: JSON 구조화 로그 파싱 (trace_id, level 필드 추출)
      └── Loki output: labels = namespace, pod, container
  → Loki (3100)
  → Grafana LogQL 쿼리
```

- Fluent Bit ConfigMap: `[INPUT] tail`, `[FILTER] kubernetes`, `[OUTPUT] loki`
- Loki 레이블: `{namespace="observability-demo", pod="order-svc-xxx", container="order-svc"}`
- OTel SDK 주입 `trace_id`를 Loki 레이블에 포함 → Grafana에서 로그 라인 클릭 → Jaeger 트레이스 직접 이동

### 4-5. Grafana 대시보드

총 3개의 사전 구성 대시보드를 Provisioning으로 자동 로드.

**대시보드 1: RED Metrics Overview** (`red-metrics.json`)
- Rate: `rate(http_requests_total[5m])` — 서비스별 초당 요청 수
- Errors: `rate(http_requests_total{status_code=~"5.."}[5m]) / rate(http_requests_total[5m])` — 에러율
- Duration: `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))` — P99 응답시간
- 패널 구성: 시계열 그래프 3개 + 현재값 Stat 패널 3개

**대시보드 2: Service Map** (`service-map.json`)
- Grafana Node Graph 패널로 서비스 토폴로지 시각화
- 노드: 서비스명, 엣지: 서비스 간 호출 관계 + 레이턴시
- 데이터 소스: Jaeger (tracing 기반 서비스 맵)

**대시보드 3: Logs & Traces Explorer** (`logs-explorer.json`)
- Loki 로그 스트림 + 필터(namespace, pod, level)
- trace_id 클릭 → Jaeger UI 자동 연결 (Derived Fields 설정)
- 에러 로그 강조 (`level="error"` 필터)

### 4-6. 알림 규칙 (Alertmanager)

PrometheusRule CRD로 3개 알림 규칙 정의. kube-prometheus-stack이 자동으로 로드.

| 규칙명 | PromQL 조건 | 심각도 | 의미 |
|--------|-------------|--------|------|
| `HighErrorRate` | `rate(http_requests_total{status_code=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05` | critical | 서비스 에러율 5% 초과 |
| `HighP99Latency` | `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) > 1.0` | warning | P99 응답시간 1초 초과 |
| `PodNotReady` | `kube_pod_status_ready{condition="true"} == 0` | critical | 파드 Ready 상태 아님 |

Alertmanager 수신자: 로그 파일 기록 (MVP 단계; Slack webhook은 제외 범위)

### 4-7. 장애 시뮬레이션 (Chaos Engineering)

Chaos Mesh CRD 기반 선언적 실험 2개.

**실험 1: 네트워크 지연 주입** (`chaos-experiments/network-delay.yaml`)
```yaml
kind: NetworkChaos
spec:
  selector:
    namespaces: [observability-demo]
    labelSelectors:
      app: order-svc
  action: delay
  delay:
    latency: "500ms"
    jitter: "100ms"
  duration: "5m"
```
관찰 포인트: Grafana RED 대시보드에서 order-svc P99 레이턴시 상승, `HighP99Latency` 알림 트리거

**실험 2: 파드 강제 종료** (`chaos-experiments/pod-kill.yaml`)
```yaml
kind: PodChaos
spec:
  selector:
    namespaces: [observability-demo]
    labelSelectors:
      app: inventory-svc
  action: pod-kill
  duration: "1m"
```
관찰 포인트: Grafana에서 inventory-svc 요청 에러율 상승, `PodNotReady` + `HighErrorRate` 알림 트리거

### 4-8. GitOps (ArgoCD)

- **App of Apps 패턴**: `infra/argocd/apps/app-of-apps.yaml`가 최상위 Application으로 하위 7개 Application 관리
- **자동 동기화**: `syncPolicy.automated: {prune: true, selfHeal: true}`
- **환경 분리**: `infra/helm/*/values.yaml`에 환경별 오버라이드 (local 단일 환경)
- ArgoCD UI: KIND 클러스터 포트포워드로 접근 (`http://localhost:8090`)

### 4-9. CI/CD (GitHub Actions)

**ci.yaml (PR 트리거)**:
1. Python 서비스: `ruff` lint + `pytest` 단위 테스트
2. Go 서비스: `go vet` + `go test ./...`
3. Docker build (push 없음, 이미지 빌드 검증만)
4. Helm lint: `helm lint infra/helm/*/`

**cd.yaml (main 브랜치 push 트리거)**:
1. Docker build + push → `ghcr.io/<owner>/mini-obs-<service>:<commit-sha>`
2. `infra/helm/sample-apps/values.yaml`의 이미지 태그 자동 업데이트 (commit + PR)
3. ArgoCD 자동 동기화 (values.yaml 변경 감지 → K8s 배포)

---

## 5. 인프라 구성

### 5-1. KIND 클러스터 설정 (`kind-config.yaml`)

```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
    extraPortMappings:
      - containerPort: 80    # NGINX Ingress HTTP
        hostPort: 80
      - containerPort: 443   # NGINX Ingress HTTPS
        hostPort: 443
      - containerPort: 30000 # Grafana NodePort
        hostPort: 3000
      - containerPort: 30001 # Jaeger UI NodePort
        hostPort: 16686
      - containerPort: 30002 # ArgoCD UI NodePort
        hostPort: 8090
  - role: worker
  - role: worker
```

### 5-2. 네임스페이스 구성

| 네임스페이스 | 용도 |
|-------------|------|
| `observability-demo` | 샘플 마이크로서비스 앱 3개 |
| `monitoring` | Prometheus, Alertmanager, Grafana, Loki, Fluent Bit |
| `tracing` | Jaeger, OTel Collector |
| `chaos-mesh` | Chaos Mesh 컨트롤러 |
| `argocd` | ArgoCD 컴포넌트 |

### 5-3. 서비스 접근 포트

| 서비스 | 접근 방법 | URL |
|--------|-----------|-----|
| Grafana | NodePort 30000 | `http://localhost:3000` (admin/admin) |
| Jaeger UI | NodePort 30001 | `http://localhost:16686` |
| ArgoCD UI | NodePort 30002 | `http://localhost:8090` |
| frontend-svc | Port-forward 또는 Ingress | `http://localhost:8080` |
| Prometheus UI | Port-forward | `kubectl port-forward -n monitoring svc/prometheus-operated 9090:9090` |

---

## 6. 서비스 플로우

### 시나리오 1: 정상 요청 흐름 (Traces + Metrics 생성)

1. 사용자(또는 부하 생성기)가 `GET http://localhost:8080/api/order` 요청
2. frontend-svc(Go)가 요청 수신 → OTel SDK가 root span 생성, W3C TraceContext 헤더 주입
3. frontend-svc → order-svc로 HTTP 호출 (`POST http://order-svc:8081/orders`)
4. order-svc(Python)가 span 이어받아 child span 생성 → inventory-svc 재고 확인 호출
5. inventory-svc(Python)가 재고 조회 후 응답, leaf span 완료
6. 각 서비스의 OTel SDK가 완료된 span을 OTLP gRPC로 OTel Collector(4317)에 전송
7. OTel Collector가 traces → Jaeger(14250), metrics → Prometheus(8889) 라우팅
8. Fluent Bit가 각 파드의 stdout 로그(trace_id 포함) 수집 → Loki 저장
9. Prometheus가 15초 간격으로 각 서비스 `/metrics` scrape
10. Grafana RED 대시보드에서 Rate/Errors/Duration 실시간 업데이트 확인

### 시나리오 2: 장애 감지 흐름 (Chaos → Alert → 분석)

1. `scripts/run-chaos.sh network-delay` 실행 → Chaos Mesh `NetworkChaos` CRD 적용
2. order-svc 파드에 500ms 네트워크 지연 주입 시작
3. Prometheus가 `http_request_duration_seconds` 메트릭 상승 감지
4. 2분 후 `HighP99Latency` PrometheusRule 조건 만족 → Alertmanager에 알림 전송
5. Alertmanager가 알림 기록 (MVP: 로그 파일 저장)
6. 엔지니어가 Grafana → RED 대시보드 확인 → P99 레이턴시 그래프 스파이크 확인
7. 대시보드 패널에서 해당 시간대 로그 드릴다운 → Loki에서 느린 요청 로그 조회
8. 로그의 `trace_id` 클릭 → Jaeger에서 전체 trace 분석 → order-svc span 지연 원인 확인
9. `kubectl delete networkchaos --all -n observability-demo`로 장애 해제
10. Grafana에서 메트릭 정상화 확인

### 시나리오 3: 장애 시뮬레이션 흐름 (파드 종료 → 재스케줄링 관찰)

1. `scripts/run-chaos.sh pod-kill` 실행 → Chaos Mesh `PodChaos` CRD 적용
2. inventory-svc 파드 강제 종료
3. K8s Deployment 컨트롤러가 새 파드 자동 스케줄링 시작
4. 파드 재시작 기간(약 10~30초) 동안 frontend-svc → inventory-svc 호출 실패 발생
5. Prometheus가 `kube_pod_status_ready{app="inventory-svc"} == 0` 감지
6. `PodNotReady` + `HighErrorRate` 알림 동시 트리거
7. Grafana에서 inventory-svc 에러율 100% 상승 → 자동 복구 후 정상화 확인
8. Jaeger에서 실패한 trace span 확인 (에러 status code, 예외 메시지)

### 시나리오 4: GitOps 배포 흐름

1. 개발자가 order-svc 코드 수정 후 main 브랜치에 push
2. GitHub Actions cd.yaml 워크플로우 트리거
3. Docker 이미지 빌드 → `ghcr.io/<owner>/mini-obs-order-svc:<commit-sha>` push
4. `infra/helm/sample-apps/values.yaml`의 `orderSvc.image.tag` 값을 새 commit SHA로 자동 업데이트 (Git commit)
5. ArgoCD가 Git 리포 변경 감지 (3분 polling 또는 webhook)
6. ArgoCD가 새 Helm values로 order-svc Deployment 자동 sync → K8s 롤링 업데이트
7. ArgoCD UI에서 배포 상태 확인 (Synced / Healthy)
8. Grafana에서 배포 전후 메트릭 변화 확인

---

## 7. 설정 파일 구조

### Helm values 핵심 설정

**kube-prometheus-stack values.yaml 핵심 항목**:
```yaml
grafana:
  enabled: true
  adminPassword: admin
  persistence:
    enabled: false        # MVP: 영구 저장 없음
  additionalDataSources:
    - name: Loki
      type: loki
      url: http://loki.monitoring.svc.cluster.local:3100
    - name: Jaeger
      type: jaeger
      url: http://jaeger-query.tracing.svc.cluster.local:16686
  dashboardProviders:
    dashboardproviders.yaml:
      providers:
        - name: custom
          folder: Mini-Obs-Platform
          type: file
          options:
            path: /var/lib/grafana/dashboards/custom

prometheus:
  prometheusSpec:
    serviceMonitorSelectorNilUsesHelmValues: false  # 모든 네임스페이스 ServiceMonitor 수집
    ruleSelectorNilUsesHelmValues: false             # 모든 네임스페이스 PrometheusRule 수집
    retention: 24h                                   # MVP: 24시간 메트릭 보존

alertmanager:
  config:
    receivers:
      - name: default
        # MVP: 알림 로그 기록만 (Slack 제외)
    route:
      receiver: default
```

**OTel Collector values.yaml 핵심 항목**:
```yaml
config:
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: "0.0.0.0:4317"
        http:
          endpoint: "0.0.0.0:4318"
  processors:
    batch:
      timeout: 10s
    memory_limiter:
      limit_mib: 256
  exporters:
    jaeger:
      endpoint: "jaeger-collector.tracing.svc.cluster.local:14250"
      tls:
        insecure: true
    prometheus:
      endpoint: "0.0.0.0:8889"
  service:
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

**Fluent Bit values.yaml 핵심 항목**:
```yaml
config:
  inputs: |
    [INPUT]
        Name              tail
        Path              /var/log/containers/*.log
        multiline.parser  docker, cri
        Tag               kube.*
        Mem_Buf_Limit     5MB
        Skip_Long_Lines   On

  filters: |
    [FILTER]
        Name                kubernetes
        Match               kube.*
        Kube_URL            https://kubernetes.default.svc:443
        Kube_CA_File        /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        Kube_Token_File     /var/run/secrets/kubernetes.io/serviceaccount/token
        Merge_Log           On
        Keep_Log            Off
        K8S-Logging.Parser  On
        K8S-Logging.Exclude On

  outputs: |
    [OUTPUT]
        Name              loki
        Match             kube.*
        Host              loki.monitoring.svc.cluster.local
        Port              3100
        Labels            namespace=$kubernetes['namespace_name'],pod=$kubernetes['pod_name'],container=$kubernetes['container_name']
        Auto_Kubernetes_Labels On
```

### PrometheusRule 알림 규칙 (`prometheus-rules/app-alerts.yaml`)

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: mini-obs-app-alerts
  namespace: observability-demo
  labels:
    prometheus: kube-prometheus
    role: alert-rules
spec:
  groups:
    - name: mini-obs.application
      interval: 30s
      rules:
        - alert: HighErrorRate
          expr: |
            (
              rate(http_requests_total{status_code=~"5..", namespace="observability-demo"}[5m])
              / rate(http_requests_total{namespace="observability-demo"}[5m])
            ) > 0.05
          for: 2m
          labels:
            severity: critical
          annotations:
            summary: "High error rate on {{ $labels.service }}"
            description: "Error rate is {{ $value | humanizePercentage }} (threshold: 5%)"

        - alert: HighP99Latency
          expr: |
            histogram_quantile(0.99,
              rate(http_request_duration_seconds_bucket{namespace="observability-demo"}[5m])
            ) > 1.0
          for: 2m
          labels:
            severity: warning
          annotations:
            summary: "High P99 latency on {{ $labels.service }}"
            description: "P99 latency is {{ $value }}s (threshold: 1s)"

        - alert: PodNotReady
          expr: |
            kube_pod_status_ready{
              condition="true",
              namespace="observability-demo"
            } == 0
          for: 1m
          labels:
            severity: critical
          annotations:
            summary: "Pod {{ $labels.pod }} not ready"
            description: "Pod {{ $labels.pod }} in namespace {{ $labels.namespace }} is not ready"
```

---

## 8. 환경 설정

### 로컬 개발 환경 요구사항

| 도구 | 버전 | 용도 |
|------|------|------|
| Docker Desktop | 24.x 이상 | 컨테이너 런타임 |
| KIND | 0.22 이상 | 로컬 K8s 클러스터 |
| kubectl | 1.29 이상 | K8s 클러스터 조작 |
| Helm | 3.14 이상 | 차트 배포 |
| ArgoCD CLI | 2.x | ArgoCD 조작 (선택) |
| Go | 1.22 이상 | frontend-svc 개발 |
| Python | 3.11 이상 | order-svc, inventory-svc 개발 |

### 초기 클러스터 구성 순서

```bash
# 1. KIND 클러스터 생성
kind create cluster --name mini-obs --config kind-config.yaml

# 2. NGINX Ingress Controller 설치
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

# 3. ArgoCD 설치
kubectl create namespace argocd
kubectl apply -n argocd -f infra/argocd/install/argocd-install.yaml

# 4. ArgoCD App of Apps 적용 (이후 전체 스택 자동 배포)
kubectl apply -f infra/argocd/apps/app-of-apps.yaml

# 5. 배포 완료 대기 및 상태 확인
kubectl get applications -n argocd
```

### 포트 매핑 요약

| 서비스 | 호스트 포트 | 접근 URL |
|--------|------------|---------|
| Grafana | 3000 | http://localhost:3000 |
| Jaeger UI | 16686 | http://localhost:16686 |
| ArgoCD UI | 8090 | http://localhost:8090 |
| frontend-svc | 8080 (port-forward) | http://localhost:8080 |
| Prometheus | 9090 (port-forward) | http://localhost:9090 |

---

## 9. 보여줄 수 있는 기술 역량

| 역량 | 구체적 증거 |
|------|------------|
| K8s 인프라 구축 및 운영 | KIND 3-node 클러스터, 5개 네임스페이스 설계, ServiceMonitor/PrometheusRule CRD 관리 |
| Observability 파이프라인 설계 | OTel Collector를 중간 게이트웨이로 traces→Jaeger, metrics→Prometheus 분기 파이프라인 직접 구성 |
| Prometheus 메트릭 수집 | kube-prometheus-stack 배포, 커스텀 exporter 작성(prometheus_client), RED 메트릭 정의 |
| Grafana 대시보드 설계 | 3개 대시보드 JSON 직접 작성, Provisioning 자동화, Loki-Jaeger Derived Fields 설정 |
| 분산 트레이싱 | OTel SDK로 Go/Python 서비스 계측, W3C TraceContext 전파, Jaeger trace 분석 |
| 로그 수집 파이프라인 | Fluent Bit DaemonSet 설정, Kubernetes 메타데이터 주입, Loki LogQL 쿼리 |
| Alertmanager 알림 설계 | PrometheusRule CRD 3개 작성, PromQL 알림 조건 정의 (HighErrorRate, HighP99Latency, PodNotReady) |
| Chaos Engineering | Chaos Mesh NetworkChaos/PodChaos CRD 작성, 장애 주입 → Grafana 이상 감지 → 원인 분석 시나리오 |
| GitOps (ArgoCD) | App of Apps 패턴 구현, 자동 동기화 설정, Helm values Git 관리 |
| CI/CD (IaC) | GitHub Actions로 lint→test→build→push→sync 파이프라인, 이미지 태그 자동 업데이트 |
| Instana vs 오픈소스 비교 | Instana가 자동화하는 계측/트레이싱/알림을 오픈소스로 직접 재현, 각 도구의 역할 설명 가능 |

---

## 10. 제외 범위 (Out of Scope)

MVP에서 명시적으로 제외하는 기능:

- **Tempo 트레이싱 백엔드**: Jaeger를 선택. Tempo는 Grafana 생태계 심화 연동 시 추가 가능
- **Thanos / Cortex**: Prometheus 장기 보존 및 멀티 클러스터 집계. 로컬 MVP 범위 초과
- **Istio / Envoy 서비스 메시**: 사이드카 기반 트레이싱. OTel SDK 계측 방식으로 충분
- **Slack / PagerDuty 알림 연동**: Alertmanager 수신자 설정. 계정 설정 없이 규칙 정의로 증명
- **멀티 클러스터 Federation**: 단일 KIND 클러스터로 모든 기능 시연
- **ELK 스택 (Elasticsearch + Kibana)**: Loki + Grafana 조합으로 충분
- **OpenTelemetry Operator (K8s Operator 방식 계측)**: 직접 SDK 계측 방식 선택 (코드 레벨 이해 증명)
- **서비스 인증/TLS**: 로컬 개발 환경 전제, insecure 통신 허용
- **영구 볼륨 (PersistentVolume)**: MVP는 파드 재시작 시 데이터 초기화 허용 (emptyDir)
- **부하 생성기 (k6, Locust)**: 수동 curl 또는 간단한 bash 루프로 대체
