# mini-obs-platform

Instana가 내부적으로 처리하는 Observability 파이프라인을 오픈소스 스택으로 직접 재현한 미니 관측성 플랫폼.

3개 샘플 마이크로서비스에 OpenTelemetry SDK를 계측하고, Prometheus/Grafana/Tempo/Loki로 메트릭/트레이스/로그를 수집하여 통합 대시보드에서 관찰합니다. Chaos Mesh로 장애를 주입해 RED 메트릭 변화를 실시간으로 관찰하고, Alertmanager 알림이 트리거되는 전체 Observability 루프를 구현합니다.

> 파이프라인 아키텍처 설계, 기술 스택 선정, 장애 주입 시나리오와 알림 검증은 직접 수행했으며, 개별 서비스와 매니페스트 코드 구현에는 AI 코딩 도구를 활용했습니다 (AI-assisted implementation).

---

## 아키텍처 개요

```
                        ┌─────────────────────────────────────────────┐
                        │              KIND K8s Cluster                │
  사용자 요청            │                                             │
  ───────────►  ┌───────┴───────┐                                     │
                │ frontend-svc  │──── GET /api/order ────►┌──────────┐│
                │   (Go 1.24)   │                         │ order-svc││
                │   :8080       │◄────── 응답 ────────────│ (FastAPI)││
                └───────┬───────┘                         │  :8081   ││
                        │                                 └────┬─────┘│
                        │ GET /api/inventory                   │      │
                        ▼                                      │      │
                ┌───────────────┐    PUT /items/{id}/stock     │      │
                │ inventory-svc │◄─────────────────────────────┘      │
                │  (FastAPI)    │                                      │
                │   :8082       │                                      │
                └───────────────┘                                      │
                        │                                              │
          ┌─────────────┼─────────────────────────────────────┐       │
          │   OTel SDK (traces, metrics, structured logs)     │       │
          └─────────────┼─────────────────────────────────────┘       │
                        ▼                                              │
                ┌───────────────┐     ┌────────────┐  ┌────────────┐  │
                │ OTel Collector│────►│  Tempo     │  │ Prometheus │  │
                │  :4317 gRPC   │     │  :4317     │  │  :9090     │  │
                └───────────────┘     └────────────┘  └─────┬──────┘  │
                                                            │         │
                ┌───────────────┐     ┌────────────┐  ┌─────▼──────┐  │
                │  Fluent Bit   │────►│   Loki     │  │  Grafana   │  │
                │  (DaemonSet)  │     │   :3100    │  │  :3000     │  │
                └───────────────┘     └────────────┘  └────────────┘  │
                                                                       │
                ┌───────────────┐     ┌────────────┐                  │
                │  Chaos Mesh   │     │  ArgoCD    │                  │
                │  (실험 주입)   │     │  :8090     │                  │
                └───────────────┘     └────────────┘                  │
                        └─────────────────────────────────────────────┘
```

---

## 기술 스택

| 카테고리 | 기술 |
|----------|------|
| 오케스트레이션 | Kubernetes (KIND) — 1 control-plane + 2 worker |
| 패키지 배포 | Helm 3.x |
| GitOps | ArgoCD 2.x (App of Apps 패턴) |
| CI/CD | GitHub Actions + ghcr.io |
| 메트릭 | Prometheus + Alertmanager (kube-prometheus-stack) |
| 시각화 | Grafana 10.x |
| 트레이싱 | OpenTelemetry SDK + OTel Collector + Grafana Tempo 2.x |
| 로그 | Fluent Bit DaemonSet + Loki 2.9 |
| 장애 시뮬레이션 | Chaos Mesh 2.x |
| 앱 언어 | Go 1.24, Python 3.11 (FastAPI) |

---

## 사전 요구사항

- Docker Desktop (4.x 이상)
- kubectl (1.28+)
- Helm (3.x)
- KIND (0.20+)
- Go 1.24+ (frontend-svc 로컬 빌드 시)
- Python 3.11+ (order-svc, inventory-svc 로컬 빌드 시)
- 최소 RAM: 12GB (16GB 권장)

---

## 빠른 시작

### 1. 클러스터 생성

```bash
./scripts/setup-cluster.sh
```

KIND 클러스터(1 control-plane + 2 worker)를 생성하고 포트 매핑을 설정합니다.

### 2. 전체 스택 배포

```bash
./scripts/deploy-all.sh
```

6단계로 전체 스택을 순차 배포합니다:
1. 네임스페이스 생성 (observability-demo, monitoring, tracing, logging, chaos-mesh)
2. ArgoCD 설치
3. Helm 레포지토리 추가
4. 모니터링 스택 설치 (Prometheus, Grafana, Alertmanager)
5. 트레이싱/로그 스택 설치 (OTel Collector, Tempo, Loki, Fluent Bit)
6. 샘플 앱 + Chaos Mesh + ArgoCD App of Apps 배포

### 3. 포트 포워딩

```bash
./scripts/port-forward.sh
```

| 서비스 | 로컬 주소 |
|--------|-----------|
| Grafana | http://localhost:3000 (admin/admin, 트레이스는 Explore의 Tempo 데이터소스) |
| ArgoCD UI | http://localhost:8090 |
| frontend-svc | http://localhost:8080 |

### 4. 트래픽 생성 및 관찰

```bash
# 주문 요청 (frontend → order → inventory 호출 체인)
curl http://localhost:8080/api/order

# 재고 조회
curl http://localhost:8080/api/inventory

# 연속 트래픽 생성 (Grafana 대시보드 관찰용)
while true; do curl -s http://localhost:8080/api/order > /dev/null; sleep 0.5; done
```

### 5. 장애 시뮬레이션

```bash
# 네트워크 지연 주입 (order-svc에 500ms 지연)
./scripts/run-chaos.sh apply network-delay

# 파드 종료 실험 (inventory-svc 파드 kill)
./scripts/run-chaos.sh apply pod-kill

# 패킷 드랍 실험 (inventory-svc 향 패킷 100% 손실, readiness 실패 유발)
./scripts/run-chaos.sh apply network-loss

# 실험 상태 확인
./scripts/run-chaos.sh status

# 실험 제거
./scripts/run-chaos.sh delete network-delay
```

### 6. E2E 테스트

```bash
./scripts/e2e-test.sh
```

### 7. 클러스터 삭제

```bash
./scripts/teardown-cluster.sh
```

---

## Grafana 대시보드

| 대시보드 | 설명 |
|----------|------|
| RED Metrics | Request Rate, Error Rate, Duration(P99) 서비스별 시각화 |
| Service Map | Tempo nodeGraph 기반 서비스 호출 토폴로지 |
| Logs Explorer | Loki 로그 스트림 + trace_id Derived Fields → Tempo 트레이스 드릴다운 |

---

## Alertmanager 알림 규칙

| 규칙 | 조건 | 심각도 |
|------|------|--------|
| HighErrorRate | 5xx 비율 > 5% (2분간) | critical |
| HighP99Latency | P99 응답시간 > 1초 (2분간) | warning |
| PodNotReady | Running이 아닌 파드 존재 (1분간) | critical |

---

## 프로젝트 구조

```
mini-obs-platform/
├── apps/                          # 샘플 마이크로서비스
│   ├── frontend-svc/              # Go HTTP 게이트웨이
│   ├── order-svc/                 # Python FastAPI 주문 서비스
│   └── inventory-svc/             # Python FastAPI 재고 서비스
├── infra/                         # 인프라 선언 (GitOps 소스)
│   ├── argocd/                    # ArgoCD App of Apps
│   ├── helm/                      # Helm values 오버라이드
│   └── manifests/                 # K8s 매니페스트, PrometheusRule, Chaos 실험
├── scripts/                       # 클러스터 셋업, 배포, E2E 테스트
├── .github/workflows/             # CI/CD (ci.yaml, cd.yaml)
└── docs/                          # 설계 문서, 개발자 가이드, 면접 가이드
```

---

## 문서

- [README.md](README.md) — 사용자 가이드 (이 문서)
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — 개발자 가이드 (코드 구조, 빌드, 테스트)
- [docs/INTERVIEW.md](docs/INTERVIEW.md) — 면접 대비 가이드 (시연 시나리오, 예상 질문)

---

## 확장 가능성 (프로덕션 환경)

- **영구 저장소**: Prometheus/Loki/Tempo에 PersistentVolume 적용
- **장기 메트릭 저장**: Thanos 또는 Cortex 도입
- **알림 수신**: Alertmanager에 Slack/PagerDuty webhook 연동
- **부하 테스트**: k6 또는 Locust로 체계적 부하 생성
- **서비스 메시**: Istio 도입으로 mTLS, traffic management 추가
- **멀티 클러스터**: Federation 또는 Thanos Sidecar로 멀티 클러스터 메트릭 통합
