# 개발자 가이드

mini-obs-platform 프로젝트의 코드 구조, 개발 환경 설정, 빌드/테스트 방법을 설명합니다.

---

## 프로젝트 아키텍처

### 서비스 호출 체인

```
Client → frontend-svc (Go :8080)
              ├── GET /api/order  → order-svc (Python :8081) POST /orders
              │                         └── inventory-svc (Python :8082) PUT /items/{id}/stock
              └── GET /api/inventory → inventory-svc (Python :8082) GET /items
```

### OTel 계측 파이프라인

```
앱 (OTel SDK)
  → OTLP gRPC (:4317)
  → OTel Collector
      ├── → Jaeger (:14250)    — 트레이스 저장
      └── → Prometheus (:8889) — 메트릭 내보내기

앱 stdout (JSON 구조화 로그, trace_id 포함)
  → Fluent Bit (DaemonSet, /var/log/containers/*.log)
  → Loki (:3100)
  → Grafana (Derived Fields: trace_id → Jaeger 링크)
```

### 네임스페이스 구조

| 네임스페이스 | 컴포넌트 |
|-------------|----------|
| `observability-demo` | frontend-svc, order-svc, inventory-svc |
| `monitoring` | Prometheus, Grafana, Alertmanager |
| `tracing` | OTel Collector, Jaeger |
| `logging` | Loki, Fluent Bit |
| `chaos-mesh` | Chaos Mesh |

---

## 로컬 개발 환경 설정

### Python 서비스 (order-svc, inventory-svc)

```bash
cd apps/order-svc

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정 (OTel 없이 로컬 실행)
export OTEL_EXPORTER_OTLP_ENDPOINT=""
export OTEL_SERVICE_NAME=order-svc
export INVENTORY_SVC_URL=http://localhost:8082

# 서버 실행
uvicorn main:app --host 0.0.0.0 --port 8081 --reload
```

```bash
cd apps/inventory-svc

pip install -r requirements.txt
export OTEL_EXPORTER_OTLP_ENDPOINT=""
export OTEL_SERVICE_NAME=inventory-svc

uvicorn main:app --host 0.0.0.0 --port 8082 --reload
```

### Go 서비스 (frontend-svc)

```bash
cd apps/frontend-svc

# 의존성 정리
go mod tidy

# 환경변수 설정
export ORDER_SVC_URL=http://localhost:8081
export INVENTORY_SVC_URL=http://localhost:8082
export OTEL_EXPORTER_OTLP_ENDPOINT=""
export OTEL_SERVICE_NAME=frontend-svc

# 서버 실행
go run .
```

---

## 테스트

### Python 테스트

```bash
# order-svc
cd apps/order-svc
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx
pytest -v

# inventory-svc
cd apps/inventory-svc
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx
pytest -v
```

테스트는 `conftest.py`에서 OTel SDK를 no-op 스텁으로 대체하므로, 라이브 OTLP 엔드포인트 없이 실행됩니다.

**테스트 구조:**
- `tests/test_unit.py` — 순수 로직 단위 테스트 (HTTP/OTel 의존성 없음)
- `tests/test_integration.py` — FastAPI TestClient 통합 테스트
- `tests/conftest.py` — OTel 스텁 주입 + 인메모리 저장소 초기화 fixture

### Go 테스트

```bash
cd apps/frontend-svc
go vet ./...
go test -v ./...
```

### 린트

```bash
# Python
pip install ruff
ruff check apps/order-svc/ apps/inventory-svc/

# Go
cd apps/frontend-svc && go vet ./...

# Bash 스크립트
for f in scripts/*.sh; do bash -n "$f" && echo "OK: $f"; done
```

---

## Docker 빌드

모든 서비스는 멀티스테이지 빌드를 사용합니다.

```bash
# Python 서비스
docker build -t order-svc:latest apps/order-svc/
docker build -t inventory-svc:latest apps/inventory-svc/

# Go 서비스 (scratch 기반 최소 이미지)
docker build -t frontend-svc:latest apps/frontend-svc/
```

### 이미지 태그 전략

- 로컬: `latest`
- CI/CD: `ghcr.io/<owner>/mini-obs-<svc>:<commit-sha>`
- ArgoCD가 `infra/manifests/apps/` 매니페스트의 이미지 태그 변경을 감지하여 자동 배포

---

## 인프라 코드 구조

### Helm Values

```
infra/helm/
├── kube-prometheus-stack/values.yaml   # Prometheus + Grafana + Alertmanager
├── otel-collector/values.yaml          # OTel Collector 파이프라인
├── jaeger/values.yaml                  # Jaeger All-in-one
├── loki/values.yaml                    # Loki 3.x
├── fluent-bit/values.yaml              # Fluent Bit DaemonSet
└── chaos-mesh/values.yaml              # Chaos Mesh 2.x
```

각 values.yaml은 공식 Helm chart의 기본값을 오버라이드합니다. 주요 커스텀 설정:

- **kube-prometheus-stack**: `serviceMonitorSelectorNilUsesHelmValues: false` (외부 네임스페이스 ServiceMonitor 수집)
- **OTel Collector**: OTLP gRPC 수신 → Jaeger + Prometheus 내보내기 파이프라인
- **Jaeger**: all-in-one 모드, 메모리 저장 (max 10000 traces)
- **Fluent Bit**: tail → kubernetes filter → Loki output (JSON 파싱)

### K8s 매니페스트

```
infra/manifests/
├── namespace.yaml                     # 5개 네임스페이스
├── apps/                              # 샘플 앱 Deployment + Service + ServiceMonitor
│   ├── frontend-svc.yaml
│   ├── order-svc.yaml
│   └── inventory-svc.yaml
├── monitoring/
│   ├── prometheus-rules.yaml          # PrometheusRule CRD (3개 알림 규칙)
│   ├── jaeger-nodeport.yaml           # Jaeger NodePort 서비스
│   └── dashboards/                    # Grafana 대시보드 JSON
│       ├── red-metrics.json
│       ├── service-map.json
│       └── logs-explorer.json
└── chaos/                             # Chaos Mesh 실험
    ├── network-delay.yaml             # order-svc 500ms 지연
    └── pod-kill.yaml                  # inventory-svc 파드 종료
```

### ArgoCD App of Apps

```
infra/argocd/
├── app-of-apps.yaml                   # 최상위 Application
└── apps/                              # 하위 7개 Application
    ├── kube-prometheus-stack.yaml
    ├── otel-collector.yaml
    ├── jaeger.yaml
    ├── loki.yaml
    ├── fluent-bit.yaml
    ├── chaos-mesh.yaml
    └── sample-apps.yaml
```

모든 Application에 `automated sync (prune + selfHeal)` 설정이 적용되어 있어, Git에 push하면 ArgoCD가 자동으로 클러스터 상태를 동기화합니다.

---

## CI/CD 파이프라인

### CI (`.github/workflows/ci.yaml`)

PR 트리거. 병렬 실행:

```
├── Python lint (ruff check)
├── Python test (pytest)
├── Go lint (go vet)
├── Go test (go test)
├── Helm lint
└── Docker build (push 없음, 빌드 검증만)
```

### CD (`.github/workflows/cd.yaml`)

main push 트리거:

```
1. Docker build + push (ghcr.io, commit SHA 태그)
2. sed로 K8s 매니페스트 이미지 태그 업데이트
3. git commit + push (매니페스트 변경)
4. ArgoCD 자동 감지 → 클러스터 sync
```

---

## 주요 설계 결정

| 결정 | 선택 | 이유 |
|------|------|------|
| 트레이싱 백엔드 | Jaeger (vs Tempo) | 독립 UI 제공, Instana 비교 포인트 |
| 로컬 K8s | KIND (vs minikube) | 멀티 노드, Docker 기반, CNCF 표준 |
| GitOps 패턴 | App of Apps | 단일 Application으로 전체 스택 부트스트랩 |
| 저장소 | emptyDir (vs PV) | MVP 단순화, 24h retention |
| 이미지 레지스트리 | ghcr.io (vs Docker Hub) | GitHub Actions 네이티브 연동, rate limit 없음 |
| 장애 시뮬레이션 | Chaos Mesh (vs Litmus) | K8s CRD 네이티브, GitOps 통합 용이 |

---

## 알려진 제한사항

1. **Grafana 대시보드 자동 로드**: JSON 파일이 ConfigMap으로 래핑되지 않아 수동 임포트 필요. `grafana_dashboard: "1"` 레이블이 있는 ConfigMap으로 래핑하면 sidecar가 자동 로드.
2. **Go go.sum**: 플레이스홀더 상태. `go mod tidy` 또는 Docker 빌드 시 자동 생성.
3. **KIND NodePort 제한**: extraPortMappings는 control-plane 노드에만 유효. `port-forward.sh`를 병행 사용 권장.
4. **인메모리 저장소**: 파드 재시작 시 데이터 초기화. MVP 허용 범위.
