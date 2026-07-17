# 개발 계획 — mini-obs-platform

**프로젝트**: mini-obs-platform
**버전**: 1.0
**총 태스크**: 22개
**예상 일정**: 4주 (개발 인력 및 테스트 시간 포함)

---

## 개요

mini-obs-platform은 오픈소스 모니터링 스택(Prometheus, Grafana, Jaeger, Loki, OTel)과 Chaos Mesh를 활용한 완전한 관측성 플랫폼입니다. 3개 샘플 마이크로서비스, K8s (KIND) 인프라, GitOps (ArgoCD), CI/CD (GitHub Actions)로 구성됩니다.

### 병렬 실행 가능 구간

프로젝트의 높은 병렬성을 활용:

1. **Phase 1 (기반 설정 — 병렬)**: #1 (Python 백엔드) + #2 (Go 프론트엔드) + #9 (KIND 클러스터)
2. **Phase 2 (앱 개발 — 병렬)**: #3, #4 (Python 엔드포인트) + #5 (Go 엔드포인트)
3. **Phase 3 (계측 및 테스트 — 순차)**: #6 (OTel) → #7 (테스트) → #8 (Docker)
4. **Phase 4 (인프라 구성 — 병렬)**: #10~#17 (Helm, K8s 매니페스트, ArgoCD) — #9와 병렬 가능
5. **Phase 5 (배포 및 QA)**: #18 (CI/CD) → #19 (배포 스크립트) → #20 (문서) → #21 (QA) → #22 (최종 검증)

---

## Phase 1 — 기반 설정 (4 태스크, 병렬 수행 가능)

### 1-1. 백엔드 프로젝트 구조

- **태스크**: #1 백엔드 프로젝트 구조 및 파이썬 기반 설정
- **담당**: db-agent
- **산출물**:
  - `apps/order-svc/` (main.py, otel_setup.py, metrics.py, requirements.txt, Dockerfile, .env.example)
  - `apps/inventory-svc/` (동일 구조)
  - 공통 utilities 패키지 (선택)

### 1-2. 프론트엔드 프로젝트 구조

- **태스크**: #2 프론트엔드 프로젝트 구조 및 Go 기반 설정
- **담당**: frontend-agent
- **산출물**:
  - `apps/frontend-svc/` (main.go, handler.go, otel.go, go.mod, Dockerfile, .env.example)
- **병렬 수행**: #1과 동시 진행 가능

### 1-3. KIND 클러스터 설정

- **태스크**: #9 KIND 클러스터 설정 및 초기화 스크립트
- **담당**: db-agent
- **산출물**:
  - `kind-config.yaml` (K8s 1.29, 3 nodes, port mappings)
  - `scripts/create-cluster.sh`, `scripts/delete-cluster.sh`, `scripts/check-cluster.sh`
- **병렬 수행**: #1, #2와 동시 진행 가능

---

## Phase 2 — 샘플 앱 엔드포인트 개발 (3 태스크)

### 2-1. order-svc 엔드포인트

- **태스크**: #3 order-svc FastAPI 주요 엔드포인트 구현
- **담당**: db-agent
- **의존성**: #1 (백엔드 프로젝트 설정)
- **산출물**:
  - POST /orders (주문 생성, 재고 차감)
  - GET /orders/{order_id} (주문 조회)
  - GET /metrics, GET /health
- **완료 조건**: 모든 엔드포인트 구현, 프로시저 정확성 (api-spec.json 기준)

### 2-2. inventory-svc 엔드포인트

- **태스크**: #4 inventory-svc FastAPI 주요 엔드포인트 구현
- **담당**: db-agent
- **의존성**: #1 (백엔드 프로젝트 설정)
- **산출물**:
  - GET /items (재고 목록)
  - PUT /items/{item_id}/stock (재고 차감)
  - GET /metrics, GET /health
- **완료 조건**: 모든 엔드포인트 구현, 재고 차감 로직 정확성

### 2-3. frontend-svc 엔드포인트

- **태스크**: #5 frontend-svc Go HTTP 게이트웨이 엔드포인트 구현
- **담당**: frontend-agent
- **의존성**: #2 (프론트엔드 프로젝트 설정)
- **산출물**:
  - GET /api/order (order-svc 프록시)
  - GET /api/inventory (inventory-svc 프록시)
  - GET /metrics, GET /health
- **완료 조건**: 모든 엔드포인트 구현, root span 생성, 메트릭 기록

---

## Phase 3 — 계측, 테스트, 컨테이너화 (4 태스크)

### 3-1. OpenTelemetry SDK 계측

- **태스크**: #6 OpenTelemetry SDK 계측 — 3개 서비스
- **담당**: db-agent + frontend-agent
- **의존성**: #3, #4, #5 (모든 엔드포인트 구현)
- **산출물**:
  - OTel TracerProvider, MeterProvider 초기화
  - W3C TraceContext 헤더 전파 (traceparent)
  - Prometheus 메트릭 (http_requests_total, http_request_duration_seconds 등)
  - 구조화 로그 (JSON, trace_id/span_id 포함)
  - OTLP gRPC exporter 설정

### 3-2. 테스트 작성

- **태스크**: #7 3개 샘플 앱 테스트 작성 (unit + integration)
- **담당**: qa-agent
- **의존성**: #6 (OTel 계측 완료)
- **산출물**:
  - `apps/order-svc/tests/` (pytest: 10+ 테스트)
  - `apps/inventory-svc/tests/` (pytest: 10+ 테스트)
  - `apps/frontend-svc/tests/` (Go: 10+ 테스트)
  - 커버리지 >= 80%

### 3-3. Dockerfile 및 Docker 빌드

- **태스크**: #8 Dockerfile 및 Docker 이미지 빌드
- **담당**: db-agent + frontend-agent
- **의존성**: #7 (테스트 통과)
- **산출물**:
  - `apps/*/Dockerfile` (각 서비스)
  - `.dockerignore`
  - 이미지 빌드 검증 (docker build 성공)

---

## Phase 4 — 인프라 구성 (9 태스크, 대부분 병렬)

### 4-1. Helm values 작성 (4 태스크, 병렬)

#### 4-1a. kube-prometheus-stack

- **태스크**: #10 Helm values.yaml — Prometheus, Grafana, Alertmanager
- **담당**: db-agent
- **의존성**: #9 (KIND 클러스터)
- **산출물**: `infra/helm/kube-prometheus-stack/values.yaml`

#### 4-1b. OTel + Jaeger + Loki + Fluent Bit

- **태스크**: #11 Helm values.yaml — OTel Collector, Jaeger, Loki, Fluent Bit
- **담당**: db-agent
- **의존성**: #9 (KIND 클러스터)
- **산출물**:
  - `infra/helm/otel-collector/values.yaml`
  - `infra/helm/jaeger/values.yaml`
  - `infra/helm/loki-stack/values.yaml`
  - `infra/helm/fluent-bit/values.yaml`

#### 4-1c. Chaos Mesh

- **태스크**: #12 Helm values.yaml — Chaos Mesh
- **담당**: qa-agent
- **의존성**: #9 (KIND 클러스터)
- **산출물**: `infra/helm/chaos-mesh/values.yaml`

### 4-2. K8s 매니페스트 (3 태스크)

#### 4-2a. 샘플 앱 리소스

- **태스크**: #13 K8s 매니페스트 — Deployment/Service/ServiceMonitor
- **담당**: db-agent
- **의존성**: #8 (Docker 이미지)
- **산출물**:
  - `infra/manifests/sample-apps/frontend-svc-*.yaml`
  - `infra/manifests/sample-apps/order-svc-*.yaml`
  - `infra/manifests/sample-apps/inventory-svc-*.yaml`

#### 4-2b. Prometheus 규칙

- **태스크**: #14 Prometheus 규칙 — PrometheusRule CRD
- **담당**: qa-agent
- **의존성**: #10 (Prometheus Helm 설정)
- **산출물**: `infra/manifests/prometheus-rules/app-alerts.yaml`
- **규칙**: HighErrorRate, HighP99Latency, PodNotReady (3개)

#### 4-2c. Grafana 대시보드

- **태스크**: #15 Grafana 대시보드 JSON — RED, Service Map, Logs Explorer
- **담당**: qa-agent
- **의존성**: #10, #11 (Prometheus, Loki, Jaeger 연동)
- **산출물**:
  - `infra/grafana/dashboards/red-metrics.json`
  - `infra/grafana/dashboards/service-map.json`
  - `infra/grafana/dashboards/logs-explorer.json`

### 4-3. GitOps 및 Chaos (2 태스크)

#### 4-3a. ArgoCD 구성

- **태스크**: #16 ArgoCD Application 매니페스트 — App of Apps
- **담당**: db-agent
- **의존성**: #10~#15 (모든 Helm/매니페스트 준비)
- **산출물**:
  - `infra/argocd/install/argocd-install.yaml`
  - `infra/argocd/apps/app-of-apps.yaml`
  - `infra/argocd/apps/{kube-prometheus-stack,loki-stack,...}.yaml` (7개 Application)

#### 4-3b. Chaos Experiments

- **태스크**: #17 Chaos Experiment 매니페스트 — NetworkChaos, PodChaos
- **담당**: qa-agent
- **의존성**: #12 (Chaos Mesh Helm)
- **산출물**:
  - `infra/manifests/chaos-experiments/network-delay.yaml`
  - `infra/manifests/chaos-experiments/pod-kill.yaml`

---

## Phase 5 — 배포, 문서, QA (6 태스크)

### 5-1. CI/CD 파이프라인

- **태스크**: #18 GitHub Actions CI/CD 워크플로우
- **담당**: db-agent + frontend-agent
- **의존성**: #7 (테스트), #8 (Docker)
- **산출물**:
  - `.github/workflows/ci.yaml` (PR: lint, test, build)
  - `.github/workflows/cd.yaml` (main: push to ghcr.io, update values.yaml)

### 5-2. 배포 스크립트

- **태스크**: #19 클러스터 배포 및 통합 테스트 스크립트
- **담당**: db-agent
- **의존성**: #9, #16, #17, #18 (모든 인프라 준비)
- **산출물**:
  - `scripts/install-infrastructure.sh` (ArgoCD + 전체 스택 배포)
  - `scripts/port-forward-all.sh` (포트포워드)
  - `tests/e2e-test.sh` (E2E 시나리오)
  - `tests/chaos-test.sh` (Chaos Engineering)

### 5-3. 문서화

- **태스크**: #20 README.md 및 프로젝트 문서
- **담당**: db-agent
- **의존성**: #19 (배포 스크립트 완성)
- **산출물**:
  - `README.md` (빠른 시작)
  - `docs/SETUP.md` (상세 설치)
  - `docs/OPERATIONS.md` (운영 가이드)
  - `docs/CHAOS-TESTING.md` (Chaos 시나리오)
  - `docs/TROUBLESHOOTING.md` (문제 해결)

### 5-4. QA 및 검증

- **태스크**: #21 QA: 코드 리뷰 및 설계 정합성 검증
- **담당**: qa-agent
- **의존성**: 모든 구현 완료
- **검증 항목**:
  - 코드 리뷰 (PEP8, go vet, YAML)
  - 테스트 커버리지 >= 80%
  - 설계 문서 일치성 (api-spec.json, data-model.json)
  - 보안 검증 (시크릿 하드코딩 없음)
  - E2E 시나리오 통과

### 5-5. 최종 배포 검증

- **태스크**: #22 최종 배포 검증 및 프로덕션 준비
- **담당**: db-agent
- **의존성**: #21 (QA 완료)
- **검증 항목**:
  - 모든 Pod Running
  - ArgoCD: 모든 Application Synced
  - Prometheus: Targets 모두 UP
  - Grafana 대시보드: 데이터 표시
  - Jaeger: traces 수신
  - E2E + Chaos 테스트 재검증
  - 문서 최종 검수

---

## 병렬 실행 전략

| 구간 | 병렬 태스크 | 예상 기간 | 설명 |
|------|-----------|----------|------|
| 기반 설정 | #1 (Python) + #2 (Go) + #9 (KIND) | 2시간 | 프로젝트 뼈대 구성 |
| 앱 개발 | #3, #4 (Python) + #5 (Go) | 1.5일 | 3개 마이크로서비스 엔드포인트 |
| 계측 & 테스트 | #6 (OTel) → #7 (테스트) → #8 (Docker) | 1.5일 | 순차 진행 (의존성 높음) |
| 인프라 구성 | #10~#17 (Helm, K8s, ArgoCD, Chaos) | 1.5일 | 대부분 병렬, #10 완료 후 #13 진행 |
| 배포 & QA | #18 (CI/CD) → #19 (배포) → #20 (문서) → #21 (QA) → #22 (최종) | 1.5일 | 순차 진행 |
| **총 예상 기간** | - | **4주** | 개발 인력 1명 기준, 테스트 및 반복 포함 |

---

## 체크포인트 및 검수 기준

### Checkpoint 1: Phase 2 완료 (app 엔드포인트)
- [ ] 3개 서비스 모두 `/health` 응답 가능
- [ ] order-svc POST /orders 정상 작동
- [ ] inventory-svc GET /items 정상 작동
- [ ] frontend-svc GET /api/order 정상 작동

### Checkpoint 2: Phase 3 완료 (계측 & 테스트)
- [ ] OTel span tree 생성 확인 (traceparent 전파)
- [ ] Prometheus /metrics 엔드포인트 데이터 노출
- [ ] 테스트 커버리지 >= 80%
- [ ] Docker 이미지 빌드 성공

### Checkpoint 3: Phase 4 완료 (인프라)
- [ ] KIND 클러스터 생성 완료 (3 nodes)
- [ ] helm lint 모두 통과
- [ ] kubectl apply -f 모든 K8s 리소스 적용 가능
- [ ] ArgoCD UI 접근 가능 (localhost:8090)

### Checkpoint 4: Phase 5 완료 (배포 & QA)
- [ ] CI/CD 파이프라인 작동 (PR lint, main push build)
- [ ] E2E 테스트 100% 통과
- [ ] Grafana 대시보드 데이터 표시
- [ ] Chaos 시나리오 정상 작동 (P99↑, 복구)

---

## 위험 요소 및 완화 방안

| 위험 | 영향도 | 완화 방안 |
|------|--------|---------|
| OTel SDK 호환성 (Python/Go 버전) | 높음 | 설계 단계에서 버전 확정, 초기 PoC |
| K8s 리소스 메모리 부족 (로컬 환경) | 중간 | kind-config.yaml 리소스 조정, Docker 메모리 10GB 확보 |
| Prometheus/Loki 시계열 성능 | 낮음 | 초기 데이터 보관 기간 단축 (24h/7d) |
| ArgoCD 동기화 지연 | 낮음 | webhook 또는 manual sync 옵션 제공 |
| 테스트 환경 간 차이 (로컬 vs CI) | 중간 | Docker-in-Docker 또는 GitHub Actions runner 활용 |

---

## 팀 역할 분담 (병렬 개발 기준)

### db-agent (백엔드 + 인프라)
- Phase 1: #1, #9
- Phase 2: #3, #4
- Phase 3: #6, #8
- Phase 4: #10, #11, #13, #16
- Phase 5: #18, #19, #20

### frontend-agent (프론트엔드)
- Phase 1: #2
- Phase 2: #5
- Phase 3: #6, #8
- Phase 5: #18

### qa-agent (테스트 & 검증)
- Phase 2: 리뷰
- Phase 3: #7
- Phase 4: #12, #14, #15, #17
- Phase 5: #21, #22

---

## 성공 기준

1. **기능 완성도**: 설계 문서(api-spec.json, data-model.json)와 100% 일치
2. **테스트 커버리지**: >= 80%
3. **배포 자동화**: CI/CD 파이프라인 작동, ArgoCD 자동 동기화
4. **관측성**: Prometheus, Grafana, Jaeger, Loki 모두 연동, E2E 시나리오 추적 가능
5. **Chaos Engineering**: 2개 실험 (NetworkChaos, PodChaos) 정상 작동 및 복구 확인
6. **문서**: README, SETUP, OPERATIONS, TROUBLESHOOTING 완성
7. **코드 품질**: PEP8, go vet, YAML 검증 통과, 시크릿 하드코딩 없음

---

## 다음 단계

1. **개발 시작**: 각 에이전트가 할당된 태스크부터 시작
2. **일일 동기화**: 의존성 문제, 블로킹 이슈 공유
3. **주간 리뷰**: Phase 체크포인트 검증
4. **최종 테스트**: Phase 5 QA에서 전체 시스템 검증
5. **문서화 & 릴리스**: README, 스크린샷, 포트폴리오 정리

---

**작성일**: 2026-03-28
**마지막 수정**: 2026-03-28
