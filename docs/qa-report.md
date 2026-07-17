# QA 리포트 — mini-obs-platform

**날짜**: 2026-03-28
**검증자**: qa-agent
**최종 판정**: CONDITIONAL PASS (인프라 버그 수정 후 통과)

---

## 1. 테스트 결과 요약

| 항목 | 결과 | 상세 |
|------|------|------|
| order-svc 단위/통합 테스트 | PASS | 17/17 통과 |
| inventory-svc 단위/통합 테스트 | PASS | 20/20 통과 (1개 버그 수정 후) |
| Go handler 테스트 | SKIP | Go 런타임 미설치 (코드 리뷰로 대체) |
| Python ruff 린트 (order-svc) | PASS | 1개 수정 후 clean |
| Python ruff 린트 (inventory-svc) | PASS | clean |
| bash 문법 검사 (6개 스크립트) | PASS | 모두 통과 |
| YAML 문법 검사 (24개 파일) | PASS | 모두 통과 |
| Grafana 대시보드 JSON | PASS | 3개 파일 모두 유효 |

---

## 2. 코드 리뷰 결과

### 2-1. order-svc (Python FastAPI)

**평가: PASS with minor fix**

- PEP8 / type hints: 전체 함수에 type annotation 적용, 구조 준수
- OTel 계측: `tracer.start_as_current_span` + `extract(dict(request.headers))` 로 W3C TraceContext propagation 정상
- 구조화 로그: `StructuredFormatter`가 `trace_id`, `span_id`를 JSON으로 출력 (Fluent Bit 파싱 가능)
- 인메모리 저장소: `_orders` dict 사용, 동시성 보호 없음 (MVP 허용 범위)
- 발견된 결함:
  - `metrics.py`: `REGISTRY`가 임포트되었으나 사용되지 않음 (ruff F401) → **수정 완료**

### 2-2. inventory-svc (Python FastAPI)

**평가: PASS**

- delta=0 거부 로직, stock < 0 거부 로직 모두 정상
- Gauge 초기화 (`inventory_stock_level.labels(item_id).set(stock)`) 시작 시 seed 값으로 설정
- PUT `/items/{item_id}/stock` 응답에 `previous_stock`, `current_stock`, `delta` 포함 — api-spec 일치

### 2-3. frontend-svc (Go)

**평가: PASS (코드 리뷰 기반)**

- `otelhttp.NewHandler` 로 자동 span 생성, `injectHeaders` 로 W3C TraceContext 하위 전파
- Prometheus 메트릭: `http_requests_total`, `http_request_duration_seconds` 정상 등록
- 에러 처리: upstream 5xx 또는 connection failure 시 502 반환, 409 pass-through
- `handleAPIOrder`: 고정 페이로드 `{"item_id":"item-001","quantity":1}` 사용 — order-svc에 항상 동일한 주문 전송 (MVP 허용)

---

## 3. 설계 정합성 검증 (api-spec.json 기준)

### 3-1. 엔드포인트 구현 여부

| 서비스 | 엔드포인트 | 스펙 | 구현 | 판정 |
|--------|----------|------|------|------|
| frontend-svc | GET /api/order | O | O | PASS |
| frontend-svc | GET /api/inventory | O | O | PASS |
| frontend-svc | GET /metrics | O | O | PASS |
| frontend-svc | GET /health | O | O | PASS |
| order-svc | POST /orders | O | O | PASS |
| order-svc | GET /orders/{order_id} | O | O | PASS |
| order-svc | GET /metrics | O | O | PASS |
| order-svc | GET /health | O | O | PASS |
| inventory-svc | GET /items | O | O | PASS |
| inventory-svc | PUT /items/{item_id}/stock | O | O | PASS |
| inventory-svc | GET /metrics | O | O | PASS |
| inventory-svc | GET /health | O | O | PASS |

### 3-2. 응답 필드 검증

| 엔드포인트 | 스펙 필드 | 실제 구현 | 판정 |
|-----------|----------|----------|------|
| POST /orders (201) | order_id, item_id, quantity, status, created_at, trace_id | 모두 포함 | PASS |
| GET /orders/{id} (200) | order_id, item_id, quantity, status, created_at | 모두 포함 | PASS |
| PUT /items/{id}/stock (200) | item_id, previous_stock, current_stock, delta | 모두 포함 | PASS |
| GET /items (200) | items[] 배열 | 포함 | PASS |
| GET /health | status, service | 모두 포함 | PASS |

### 3-3. service-flow.md vs 코드 불일치

| 항목 | service-flow.md | 실제 코드 | 판정 |
|------|----------------|----------|------|
| order-svc→inventory 호출 | `GET /items` (flowchart 2번) | `PUT /items/{item_id}/stock` | WARN |

**설명**: `service-flow.md`의 flowchart 2번에서 `ORD → GET http://inventory-svc:8082/items`로 표기되어 있으나, 실제 order-svc는 `PUT /items/{item_id}/stock`을 호출합니다. api-spec.json과 시퀀스 다이어그램(3-1절)은 올바르게 기술되어 있습니다. flowchart의 표기 오류입니다.

### 3-4. data-model.json K8s 리소스 커버리지

| 리소스 | data-model.json | infra/manifests/ | 판정 |
|--------|----------------|-----------------|------|
| Deployment (3개) | O | O | PASS |
| Service — 앱 3개 | O | O | PASS |
| ServiceMonitor (3개) | O | O (앱 yaml에 포함) | PASS |
| Namespace | O | O | PASS |
| PrometheusRule | O | O | PASS |
| Jaeger NodePort Service | O (data-model) | 수정 전 MISSING → **생성 완료** | FIXED |
| Grafana 대시보드 ConfigMap | 없음 | 없음 | WARN |

---

## 4. 인프라 설정 검증

### 4-1. YAML 문법

24개 YAML 파일 모두 문법 이상 없음.

### 4-2. ArgoCD Application 정합성

| ArgoCD App | repoURL | path | 판정 |
|-----------|---------|------|------|
| app-of-apps | github.com/owner/mini-obs-platform.git | infra/argocd/apps | WARN: owner 플레이스홀더 |
| sample-apps | github.com/owner/mini-obs-platform.git | infra/manifests/apps | WARN: owner 플레이스홀더 |
| 나머지 6개 | Helm 차트 repo | 각 차트명 | OK |

**비고**: `owner` 플레이스홀더는 실제 배포 전 팀의 GitHub 사용자명으로 교체 필요. Helm valueFiles도 동일하게 수정 필요.

### 4-3. Jaeger 서비스명 불일치 (Critical — 수정 완료)

- **문제**: `jaeger/values.yaml`에서 `allInOne.enabled=true`, `collector.enabled=false`, `query.enabled=false` 설정. 이 모드에서 Helm 차트가 생성하는 서비스명은 `jaeger-all-in-one`이며, `jaeger-collector`와 `jaeger-query` 서비스는 생성되지 않음.
- **영향**:
  - OTel Collector가 `jaeger-collector.tracing...:14250`을 참조 → 트레이스 전송 실패
  - Grafana Jaeger datasource가 `jaeger-query.tracing...:16686`을 참조 → Jaeger UI 연결 실패
- **수정**: 두 참조 모두 `jaeger-all-in-one.tracing.svc.cluster.local`로 변경

### 4-4. Jaeger/ArgoCD NodePort 서비스 누락 (High — 수정 완료)

- KIND `kind-config.yaml`은 containerPort 30001 → hostPort 16686 (Jaeger), 30002 → hostPort 8090 (ArgoCD) 매핑 정의
- 하지만 NodePort 30001을 사용하는 Jaeger 서비스 매니페스트가 없었음
- `infra/manifests/monitoring/jaeger-nodeport.yaml` 생성 및 `deploy-all.sh`에 ArgoCD NodePort 패치 추가

### 4-5. Prometheus PromQL 검증

3개 알림 규칙 모두 문법 이상 없음:
- `HighErrorRate`: rate 나눗셈 패턴 정상
- `HighP99Latency`: histogram_quantile + _bucket suffix 정상
- `PodNotReady`: kube_pod_status_ready 쿼리 정상

### 4-6. CD 워크플로우 sed 패턴 버그 (High — 수정 완료)

- **문제**: `sed -i "s|ghcr.io/owner/...:.*|...|"` 패턴이 초기 플레이스홀더(`owner`)만 매칭
- **영향**: 첫 번째 CD 실행 후 실제 소유자명으로 이미지 URL이 업데이트되면, 그 이후 CD 실행에서 `owner` 패턴이 매칭되지 않아 이미지 태그 업데이트 실패
- **수정**: `s|ghcr.io/.*/mini-obs-<svc>:.*|...|` 패턴으로 변경 (소유자명에 무관하게 매칭)

### 4-7. Grafana 대시보드 ConfigMap 누락 (Medium — 미수정, 권고)

- `infra/manifests/monitoring/dashboards/` 에 JSON 파일 3개 존재
- kube-prometheus-stack Grafana sidecar는 `grafana_dashboard: "1"` 레이블을 가진 ConfigMap에서 자동 로드
- 현재 이 ConfigMap이 정의되어 있지 않음 → Grafana 시작 시 대시보드가 자동 임포트되지 않음
- 권고: `kubectl create configmap grafana-dashboards ... --from-file=...` 또는 Helm values에서 `grafana.dashboards` 섹션 추가

### 4-8. namespace.yaml의 미사용 'logging' 네임스페이스 (Low)

- `namespace.yaml`에 `logging` 네임스페이스가 정의되어 있으나 어떤 컴포넌트에서도 사용되지 않음
- Fluent Bit은 `monitoring` 네임스페이스에 배포됨
- 정리 권고

---

## 5. 스크립트 검증

| 스크립트 | bash 문법 | set -euo pipefail | 실행 권한 | 판정 |
|---------|----------|-------------------|----------|------|
| setup-cluster.sh | PASS | O | rwxr-xr-x | PASS |
| deploy-all.sh | PASS | O | rwxr-xr-x | PASS |
| e2e-test.sh | PASS | O | rwxr-xr-x | PASS |
| port-forward.sh | PASS | O | rwxr-xr-x | PASS |
| run-chaos.sh | PASS | O | rwxr-xr-x | PASS |
| teardown-cluster.sh | PASS | O | rwxr-xr-x | PASS |

---

## 6. CI/CD 워크플로우 검증

### ci.yaml

- Python lint (ruff) → pytest → Go vet → Go test → Helm lint → Docker build 순서 구조 정상
- `needs:` 의존성 체인 올바름 (`test-python needs lint-python`, `docker-build needs [test-python, test-go]`)
- Helm lint에서 `|| true` 사용 — 경고 발생해도 CI 실패하지 않음 (의도적)

### cd.yaml

- main push + apps|infra 경로 필터 → build-and-push → update-image-tags 체인 정상
- `contents: write`, `packages: write` 권한 필요 (올바르게 설정됨)
- sed 패턴 버그 **수정 완료**
- CD 커밋이 다시 CD를 트리거하나 두 번째 실행에서 `No changes to commit` 으로 자연 종료

---

## 7. 발견된 이슈 요약

| # | 심각도 | 카테고리 | 파일 | 설명 | 상태 |
|---|--------|---------|------|------|------|
| 1 | High | 인프라 버그 | infra/helm/otel-collector/values.yaml | Jaeger endpoint 서비스명 불일치 (jaeger-collector → jaeger-all-in-one) | **수정 완료** |
| 2 | High | 인프라 버그 | infra/helm/kube-prometheus-stack/values.yaml | Grafana Jaeger datasource URL 불일치 | **수정 완료** |
| 3 | High | 인프라 누락 | infra/manifests/monitoring/ | Jaeger NodePort 서비스 매니페스트 없음 → localhost:16686 접근 불가 | **생성 완료** |
| 4 | High | CI/CD 버그 | .github/workflows/cd.yaml | sed 패턴 하드코딩 'owner' → 2번째 CD 이후 이미지 태그 업데이트 실패 | **수정 완료** |
| 5 | Medium | 코드 결함 | apps/order-svc/metrics.py | REGISTRY 미사용 임포트 (ruff F401) | **수정 완료** |
| 6 | Medium | 테스트 버그 | apps/inventory-svc/tests/test_unit.py | Python 3.9에서 `int \| None` 타입 힌트 구문 오류 | **수정 완료** |
| 7 | Medium | 인프라 누락 | infra/manifests/monitoring/ | Grafana 대시보드 ConfigMap 없음 → 대시보드 자동 로드 불가 | 미수정 (권고) |
| 8 | Low | 설계 불일치 | docs/service-flow.md | flowchart에서 order-svc→inventory 호출이 GET /items로 잘못 표기 (실제: PUT /items/{id}/stock) | 미수정 (문서 오류) |
| 9 | Low | 인프라 잉여 | infra/manifests/namespace.yaml | 'logging' 네임스페이스 정의되었으나 어디서도 사용되지 않음 | 미수정 (정리 권고) |

---

## 8. 개선 권고사항

1. **Grafana 대시보드 ConfigMap 추가**: `infra/manifests/monitoring/dashboards/` JSON 파일을 ConfigMap으로 래핑하여 Grafana sidecar가 자동 로드하도록 구성
2. **ArgoCD repoURL 플레이스홀더 문서화**: README에 "배포 전 `owner` 플레이스홀더를 실제 GitHub 사용자명으로 교체하라"는 지침 추가
3. **service-flow.md flowchart 수정**: `ORD → GET /items` → `ORD → PUT /items/{item_id}/stock`으로 정정
4. **namespace.yaml 정리**: 미사용 `logging` 네임스페이스 제거
5. **Go 테스트 커버리지**: CI에서 `-coverprofile` 추가 권장 (`go test -v -race -coverprofile=coverage.out ./...`)
