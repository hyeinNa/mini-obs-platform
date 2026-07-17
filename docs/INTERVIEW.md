# 면접 대비 가이드

이 문서는 mini-obs-platform 프로젝트를 활용한 면접 준비 자료입니다.

---

## 1. 프로젝트 한 줄 소개 (엘리베이터 피치)

> "Instana에서 APM 엔지니어로 일하며 배운 Observability 파이프라인의 내부 동작을 오픈소스 스택으로 직접 재현한 프로젝트입니다. Prometheus, Grafana, OpenTelemetry, Jaeger, Loki를 K8s 위에 직접 설계하고 배포해서, 장애 주입부터 알림 트리거까지 전체 관측 루프를 구현했습니다."

---

## 2. 왜 이 프로젝트를 만들었나?

**준비된 답변:**

"Instana는 에이전트 하나 설치하면 메트릭, 트레이스, 로그를 자동으로 수집하고 상관분석까지 해주는 강력한 제품입니다. 하지만 그 편리함 뒤에는 Prometheus가 하는 메트릭 스크래핑, Jaeger가 하는 span 수집, Fluent Bit가 하는 로그 라우팅 같은 개별 컴포넌트들이 있습니다.

저는 이 컴포넌트들을 직접 조립해서 '내가 Instana의 내부 동작을 이해하고 있다'는 걸 코드로 증명하고 싶었습니다. 그래서 OpenTelemetry SDK로 계측하고, OTel Collector로 라우팅하고, Grafana에서 trace_id로 로그와 트레이스를 연결하는 전체 파이프라인을 직접 구축했습니다."

---

## 3. 직무상세별 매핑 (면접관이 확인하고 싶은 것)

### 3-1. 클라우드/K8s 기반 인프라 구축 및 운영

**질문 예상:**
- "K8s 클러스터를 어떻게 구성했나요?"
- "네임스페이스 전략은?"

**답변 포인트:**
- KIND로 1 control-plane + 2 worker 멀티 노드 클러스터 구성
- 5개 네임스페이스로 관심사 분리: `observability-demo`(앱), `monitoring`(Prometheus/Grafana), `tracing`(OTel/Jaeger), `logging`(Loki/Fluent Bit), `chaos-mesh`
- Helm 3.x로 kube-prometheus-stack, Jaeger, Loki, Fluent Bit, Chaos Mesh 등 6개 차트 관리
- **시연**: `scripts/setup-cluster.sh` → `scripts/deploy-all.sh`로 전체 스택 원클릭 배포

**코드 레퍼런스:**
- `scripts/kind-config.yaml` — 클러스터 설정
- `infra/manifests/namespace.yaml` — 네임스페이스 정의
- `infra/helm/*/values.yaml` — Helm 오버라이드

---

### 3-2. CI/CD 파이프라인 구축 (IaC, GitOps)

**질문 예상:**
- "GitOps 경험이 있으신가요?"
- "CI/CD 파이프라인을 어떻게 설계했나요?"

**답변 포인트:**
- **CI**: GitHub Actions — ruff lint → pytest → go vet → go test → helm lint → docker build (PR마다 자동 실행)
- **CD**: main push → docker build+push(ghcr.io, commit SHA 태그) → K8s 매니페스트 이미지 태그 자동 업데이트 → ArgoCD 자동 sync
- **GitOps**: ArgoCD **App of Apps 패턴** — 하나의 Application으로 7개 하위 Application을 관리. Git이 single source of truth
- **IaC**: 모든 인프라가 Helm values.yaml + K8s 매니페스트로 선언적 관리. 클릭으로 설정하는 것 없음

**핵심 어필 포인트:**
> "App of Apps 패턴을 적용해서, `app-of-apps.yaml` 하나만 apply하면 Prometheus부터 Chaos Mesh까지 전체 스택이 자동으로 배포됩니다. 새 컴포넌트를 추가할 때도 `infra/argocd/apps/`에 Application YAML만 추가하면 됩니다."

**코드 레퍼런스:**
- `.github/workflows/ci.yaml`, `cd.yaml`
- `infra/argocd/app-of-apps.yaml`
- `infra/argocd/apps/*.yaml`

---

### 3-3. 모니터링 및 로그 기반 장애 원인 분석

**질문 예상:**
- "장애가 발생하면 어떻게 원인을 분석하나요?"
- "모니터링 도구를 실제로 운영해본 경험이 있나요?"

**답변 포인트 (시연 시나리오):**

**시나리오: order-svc에 네트워크 지연 500ms 주입 후 원인 분석**

```
1. Chaos Mesh로 장애 주입
   $ ./scripts/run-chaos.sh apply network-delay

2. Grafana RED 대시보드에서 이상 감지
   - Request Duration P99 그래프가 급등 (< 100ms → > 600ms)
   - Error Rate 상승

3. Alertmanager에서 HighP99Latency 알림 트리거
   - PromQL: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) > 1.0

4. Jaeger에서 느린 트레이스 조회
   - 검색: service=frontend-svc, minDuration=500ms
   - Span waterfall에서 order-svc → inventory-svc 구간에 500ms 지연 확인

5. Loki 로그에서 trace_id로 필터링
   - {namespace="observability-demo"} |= "트레이스ID"
   - Derived Fields 클릭 → Jaeger 트레이스로 직접 이동

6. 근본 원인 특정: order-svc의 네트워크 지연
```

> "이 프로세스가 바로 Instana가 자동으로 해주는 것입니다. 저는 이걸 수동으로 재현해서 각 단계가 어떻게 동작하는지 보여드리는 겁니다."

**코드 레퍼런스:**
- `infra/manifests/chaos/network-delay.yaml`
- `infra/manifests/monitoring/prometheus-rules.yaml`
- `infra/manifests/monitoring/dashboards/red-metrics.json`

---

### 3-4. Prometheus, Grafana 등 모니터링 도구 운영

**질문 예상:**
- "Prometheus ServiceMonitor가 뭔가요?"
- "Grafana 대시보드를 직접 만들어보셨나요?"
- "PromQL을 쓸 줄 아시나요?"

**답변 포인트:**

| 역량 | 이 프로젝트에서의 증거 |
|------|----------------------|
| Prometheus 운영 | kube-prometheus-stack Helm values 커스텀, ServiceMonitor CRD 3개 작성, 외부 네임스페이스 수집을 위한 `ruleSelectorNilUsesHelmValues: false` 설정 |
| PromQL | 3개 PrometheusRule 작성: `rate(http_requests_total{status=~"5.."}[5m])`, `histogram_quantile(0.99, ...)` |
| Grafana 대시보드 | RED Metrics, Service Map, Logs Explorer 3개 직접 설계. Loki Derived Fields로 trace_id → Jaeger 연결 |
| Alertmanager | HighErrorRate, HighP99Latency, PodNotReady 3개 알림 규칙 (severity 라벨 + for duration 설정) |
| OTel Collector | OTLP gRPC 수신 → batch/memory_limiter 프로세서 → Jaeger + Prometheus 이중 내보내기 파이프라인 |

**핵심 PromQL 예시 (암기):**

```promql
# 에러율 (5xx)
rate(http_requests_total{status_code=~"5.."}[5m])
  / rate(http_requests_total[5m]) * 100

# P99 레이턴시
histogram_quantile(0.99,
  rate(http_request_duration_seconds_bucket[5m])
)

# 서비스별 요청 처리량
sum(rate(http_requests_total[5m])) by (service)
```

---

### 3-5. 인프라 성능 지표 모니터링 및 최적화

**질문 예상:**
- "성능 최적화 경험이 있나요?"
- "어떤 메트릭을 보나요?"

**답변 포인트:**
- **RED Method** (Rate, Errors, Duration) 적용 — Google SRE에서 제안한 마이크로서비스 모니터링 골든 시그널
- Prometheus에서 `http_requests_total`(Rate), `http_requests_total{status=~"5.."}`(Errors), `http_request_duration_seconds`(Duration)을 수집
- Chaos Mesh로 장애 주입 전후 메트릭 비교로 성능 영향도 분석
- 커스텀 비즈니스 메트릭: `inventory_stock_level` Gauge로 재고 수준 모니터링

---

## 4. Instana 경험을 녹여낸 기술적 깊이

### "Instana와 비교하면 이 프로젝트에서 뭘 배웠나요?"

| Instana (상용) | 이 프로젝트 (직접 구현) | 배운 점 |
|----------------|----------------------|---------|
| 에이전트 하나로 자동 계측 | OTel SDK로 수동 계측 (Python: `opentelemetry-instrumentation-fastapi`, Go: `otelhttp`) | 자동 계측 뒤에는 바이트코드 조작/미들웨어 주입이 있음을 체감 |
| 자동 서비스 맵 | Jaeger nodeGraph + Prometheus 메트릭으로 수동 구성 | 서비스 맵은 trace span의 parent-child 관계에서 추출됨 |
| Smart Alert | PrometheusRule PromQL로 수동 정의 | Instana의 "이상 감지"는 내부적으로 비슷한 통계적 쿼리를 자동 생성하는 것 |
| 로그 ↔ 트레이스 자동 연결 | Loki Derived Fields + Grafana로 수동 연결 | `trace_id`가 로그와 트레이스를 연결하는 핵심 링크. 구조화 로그에서 `trace_id` 필드를 정규식으로 추출해 Jaeger URL로 링크 |
| 1초 메트릭 수집 | Prometheus 15초 scrape interval | 수집 간격과 저장 비용의 트레이드오프 |

### "trace_id가 어떻게 전파되나요?"

```
1. frontend-svc (Go)가 요청 수신
   → otelhttp 미들웨어가 root span 생성
   → traceparent 헤더 생성: 00-<32자 trace_id>-<16자 span_id>-01

2. frontend-svc → order-svc HTTP 호출 시
   → propagation.Inject()로 traceparent 헤더를 하위 요청에 주입

3. order-svc (Python)가 요청 수신
   → FastAPI 미들웨어가 traceparent 추출
   → extract(dict(request.headers))로 context 복원
   → 동일 trace_id의 child span 생성

4. 구조화 로그에 trace_id 자동 포함
   → Fluent Bit → Loki로 수집
   → Grafana Derived Fields: regex로 trace_id 추출 → Jaeger URL 링크
```

---

## 5. 예상 질문 & 답변

### Q: "이 프로젝트에서 가장 어려웠던 부분은?"

**A:** "OTel Collector를 통해 trace가 Jaeger로, metric이 Prometheus로 분기되는 파이프라인 설정이요. 특히 Jaeger all-in-one 모드에서 실제 생성되는 서비스 이름이 `jaeger-collector`가 아니라 `jaeger-all-in-one`이라서, OTel Collector와 Grafana datasource가 잘못된 서비스를 참조하는 문제가 있었습니다. Helm chart의 all-in-one 모드는 각 컴포넌트 서비스를 생성하지 않는다는 걸 배웠고, `helm template`으로 실제 생성되는 리소스를 미리 확인하는 습관이 생겼습니다."

### Q: "프로덕션 환경에서는 어떻게 달라져야 하나요?"

**A:**
- "Prometheus에 Thanos sidecar를 붙여 장기 저장소를 분리합니다"
- "Jaeger는 all-in-one 대신 collector/query/ingester 분리 배포하고 Elasticsearch나 Cassandra를 백엔드로 사용합니다"
- "Loki도 분산 모드로 전환하고 S3를 chunk 저장소로 사용합니다"
- "Alertmanager에 Slack/PagerDuty를 연결하고 라우팅 트리를 팀별로 구성합니다"
- "KIND 대신 EKS/GKE 같은 관리형 K8s를 사용하고, Terraform으로 클러스터 자체를 IaC로 관리합니다"

### Q: "왜 Datadog 대신 Prometheus/Grafana를 선택했나요?"

**A:** "이직 타겟 직무에서 Prometheus와 Grafana를 명시적으로 요구했기 때문입니다. 또한 Instana에서 일하면서 상용 도구가 내부적으로 하는 일을 오픈소스로 직접 구성하는 것이 기술적 깊이를 더 잘 보여준다고 판단했습니다. Datadog도 비슷한 파이프라인이지만, Prometheus/Grafana는 각 컴포넌트를 직접 설정해야 하므로 내부 동작 이해를 증명하기에 더 적합합니다."

### Q: "OpenTelemetry를 선택한 이유는?"

**A:** "Instana도 내부적으로 OpenTelemetry 호환을 지원하고, 실제로 OTel Collector를 통해 데이터를 수집하는 아키텍처를 제공합니다. 벤더 중립 표준이라 Jaeger, Prometheus, Loki 등 어떤 백엔드와도 연결할 수 있고, 이 프로젝트에서 Go와 Python 두 언어의 OTel SDK 계측 방식의 차이를 직접 보여줄 수 있습니다."

### Q: "Chaos Engineering을 왜 포함했나요?"

**A:** "직무상세에 '장애 분석 및 해결'이 있어서요. 장애를 분석하려면 먼저 장애를 만들 수 있어야 합니다. Chaos Mesh로 네트워크 지연을 주입하면 Prometheus에서 P99 레이턴시가 올라가는 걸 Grafana 대시보드에서 실시간으로 보여드릴 수 있고, 그 과정에서 Jaeger 트레이스와 Loki 로그로 근본 원인을 특정하는 전체 워크플로우를 시연할 수 있습니다."

---

## 6. 시연 시나리오 (면접 당일 순서)

### 5분 시연 버전

```
1. [30초] 아키텍처 다이어그램으로 전체 구조 설명
2. [30초] ArgoCD UI에서 App of Apps 상태 보여주기
3. [1분]  Grafana RED 대시보드에서 정상 상태 메트릭 확인
4. [1분]  curl로 요청 보내고 Jaeger에서 분산 트레이스 확인
5. [1분]  Chaos Mesh로 장애 주입 → Grafana에서 메트릭 변화 관찰
6. [1분]  Loki 로그에서 trace_id 클릭 → Jaeger 드릴다운 시연
```

### 준비 체크리스트 (면접 전날)

```bash
# 1. 클러스터 실행 확인
kubectl get nodes  # 3개 노드 Ready 확인

# 2. 모든 파드 Running 확인
kubectl get pods -A | grep -v Running  # 없어야 함

# 3. 포트 포워딩 실행
./scripts/port-forward.sh &

# 4. 트래픽 생성 (최소 5분간 — Grafana 그래프에 데이터 쌓이도록)
while true; do curl -s http://localhost:8080/api/order > /dev/null; sleep 0.5; done &

# 5. 각 UI 접근 확인
open http://localhost:3000    # Grafana (admin/admin)
open http://localhost:16686   # Jaeger
open http://localhost:8090    # ArgoCD

# 6. 장애 시뮬레이션 한 번 리허설
./scripts/run-chaos.sh apply network-delay
# Grafana에서 P99 상승 확인
./scripts/run-chaos.sh delete network-delay
```

---

## 7. 이 프로젝트로 증명하는 역량 요약

| 직무 요구사항 | 증명 방법 | 핵심 파일 |
|--------------|----------|-----------|
| K8s 인프라 구축/운영 | KIND 멀티 노드 + 5개 네임스페이스 + Helm 6개 차트 | `scripts/`, `infra/helm/` |
| CI/CD (IaC, GitOps) | GitHub Actions + ArgoCD App of Apps | `.github/workflows/`, `infra/argocd/` |
| 모니터링/로그 기반 장애 분석 | Chaos Mesh 장애 주입 → Grafana/Jaeger/Loki로 근본 원인 특정 | `infra/manifests/chaos/`, `infra/manifests/monitoring/` |
| Prometheus/Grafana 운영 | ServiceMonitor, PrometheusRule, PromQL, 커스텀 대시보드 | `infra/manifests/monitoring/` |
| 성능 지표 모니터링/최적화 | RED Method 적용, P99 레이턴시 모니터링, 커스텀 비즈니스 메트릭 | `apps/*/metrics.py` |
| 분산 시스템 이해 | W3C TraceContext 전파, 폴리글랏(Go+Python) OTel 계측 | `apps/*/otel*.py`, `apps/frontend-svc/otel.go` |
