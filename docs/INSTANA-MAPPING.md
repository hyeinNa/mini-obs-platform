# IBM Instana ↔ 오픈소스 스택 매핑

## 목적

이 프로젝트는 IBM Instana가 내부적으로 수행하는 Observability 파이프라인을 오픈소스 스택으로 재현하여, Instana의 아키텍처와 동작 원리를 깊이 이해하기 위한 것이다.

---

## 기능 매핑 테이블

| Instana 기능 | 이 프로젝트에서 사용한 오픈소스 | 대응 방식 | 차이점 |
|-------------|---------------------------|----------|--------|
| **Agent (호스트 에이전트)** | OpenTelemetry SDK (Go/Python) + Fluent Bit DaemonSet | Instana Agent는 호스트에 설치되어 자동 계측. 이 프로젝트는 OTel SDK를 코드에 직접 삽입하고 Fluent Bit으로 로그를 수집 | Instana: 자동 계측 (코드 수정 없음) / OTel: 수동 SDK 삽입 |
| **센서 (Sensor)** | OTel Instrumentation 라이브러리 | Instana 센서는 JVM/Python/Go 런타임을 자동 감지. OTel은 `otelhttp`, `opentelemetry-instrumentation-fastapi` 등 수동 연결 | Instana: zero-config 자동 감지 / OTel: 명시적 import 필요 |
| **트레이스 수집** | OTel Collector (OTLP gRPC) → Jaeger | Instana Backend이 직접 트레이스를 수집하지만, 이 프로젝트는 OTel Collector를 게이트웨이로 사용하고 Jaeger에 저장 | Instana: 단일 백엔드 / 이 프로젝트: Collector + Jaeger 2단계 |
| **컨텍스트 전파** | W3C TraceContext (traceparent 헤더) | Instana는 자체 X-Instana-T/S/L 헤더 사용. 이 프로젝트는 W3C 표준 사용 | 헤더 형식은 다르지만 전파 원리는 동일 |
| **메트릭 수집** | Prometheus (scrape 모델) + ServiceMonitor CRD | Instana는 push 모델로 Agent가 메트릭을 전송. Prometheus는 pull 모델로 15초 간격 스크랩 | Push vs Pull 모델, 수집 간격 차이 |
| **RED 메트릭** | `http_requests_total`, `http_request_duration_seconds` (Histogram) | Instana는 자동으로 Rate/Error/Duration 계산. 이 프로젝트는 앱에서 Prometheus Counter/Histogram을 직접 등록 | 동일한 골든 시그널, 구현 방식만 다름 |
| **서비스 맵 (Application Perspectives)** | Jaeger Service Dependencies + Grafana nodeGraph | Instana는 실시간 서비스 토폴로지를 자동 생성. 이 프로젝트는 Jaeger의 의존성 분석으로 서비스 맵 구성 | Instana: 실시간 자동 / Jaeger: 트레이스 기반 사후 분석 |
| **트레이스 뷰 (Analyze Calls)** | Jaeger UI (trace waterfall) + 포털 워터폴 | Instana의 Unbounded Analytics와 유사하게 span 워터폴 표시. Jaeger UI에서 각 span의 태그/로그 확인 가능 | Instana: 상관 분석 통합 / Jaeger: 독립 UI |
| **로그 수집 및 연계** | Fluent Bit → Loki + Grafana Derived Fields | Instana는 로그를 트레이스에 자동 연결. 이 프로젝트는 로그에 trace_id를 포함하고 Grafana Derived Fields로 Jaeger 링크 생성 | 동일한 원리 (trace_id 기반 상관), 구현 깊이 차이 |
| **알림 (Smart Alerts)** | PrometheusRule + Alertmanager | Instana는 동적 베이스라인 기반 이상 감지. 이 프로젝트는 정적 임계값 기반 PromQL 규칙 사용 | Instana: AI 기반 이상 감지 / Prometheus: 정적 규칙 |
| **대시보드** | Grafana (RED Metrics, Logs Explorer) + 통합 포털 | Instana는 빌트인 대시보드. Grafana에서 커스텀 대시보드 구성 | UI/UX 차이, 기능적으로 동등 |
| **인프라 모니터링** | kube-state-metrics + node-exporter + Prometheus | Instana Agent가 호스트/컨테이너/K8s 메트릭을 자동 수집. 이 프로젝트는 kube-prometheus-stack으로 동일한 메트릭 수집 | 동일한 데이터, 수집 방식 차이 |
| **GitOps 배포** | ArgoCD (App of Apps) + GitHub Actions | Instana 자체 기능은 아니지만, 실제 운영 환경의 CI/CD를 시뮬레이션 | 배포 자동화 + Observability 통합 시연 |
| **장애 주입 (Chaos Engineering)** | Chaos Mesh (NetworkChaos, PodChaos) | Instana에서 관찰할 장애 시나리오를 Chaos Mesh로 재현. RED 메트릭 변화와 알림 트리거를 관찰 | Instana는 관찰 도구, Chaos Mesh는 주입 도구 |

---

## Observability 3대 축 (Three Pillars) 매핑

```
         ┌─────────────────────────────────────────────┐
         │              IBM Instana                     │
         │  Agent → Backend → UI (통합 단일 플랫폼)      │
         └─────────────────────────────────────────────┘
                          ↕ 대응
         ┌─────────────────────────────────────────────┐
         │         이 프로젝트 (오픈소스 스택)             │
         │                                              │
  Metrics│  App (Prometheus client) ──scrape──▸ Prometheus ──▸ Grafana  │
         │                                                              │
  Traces │  App (OTel SDK) ──OTLP──▸ OTel Collector ──▸ Jaeger         │
         │                                                              │
  Logs   │  App (stdout JSON) ──tail──▸ Fluent Bit ──▸ Loki ──▸ Grafana│
         │                                                              │
         │  ────── trace_id로 세 축 연결 ──────                         │
         └─────────────────────────────────────────────┘
```

---

## 이 프로젝트에서 배울 수 있는 것

### 1. Observability 파이프라인의 전체 구조
- 계측(Instrumentation) → 수집(Collection) → 저장(Storage) → 시각화(Visualization) → 알림(Alerting)
- Instana가 이 5단계를 단일 제품으로 제공하지만, 내부적으로는 동일한 아키텍처

### 2. 분산 트레이싱의 원리
- W3C TraceContext 표준 (traceparent 헤더)
- trace_id(32자 hex) + span_id(16자 hex)로 요청 추적
- 서비스 간 컨텍스트 전파 (propagation)
- Instana의 X-Instana-T/S/L 헤더와 동일한 원리

### 3. 메트릭 수집과 알림
- RED 메트릭 (Rate, Errors, Duration) — Instana의 핵심 지표와 동일
- PromQL로 알림 규칙 작성 → Alertmanager 라우팅
- Instana Smart Alerts의 정적 규칙 버전

### 4. 로그-트레이스 상관 (Correlation)
- 구조화 로그에 trace_id 삽입 → Loki에서 검색 → Jaeger 링크
- Instana가 자동으로 하는 것을 수동으로 구현하여 원리 이해

### 5. Kubernetes Observability
- ServiceMonitor CRD로 메트릭 타겟 자동 등록
- DaemonSet(Fluent Bit)으로 노드별 로그 수집
- kube-state-metrics로 K8s 리소스 상태 모니터링

### 6. Chaos Engineering과 Observability
- 장애 주입(NetworkChaos, PodChaos) → RED 메트릭 변화 관찰
- 알림 트리거 확인 → MTTR(Mean Time To Recovery) 측정
- Instana에서 장애 상황을 분석하는 것과 동일한 워크플로우

---

## Instana 면접 대비 — 이 프로젝트로 답변할 수 있는 질문

1. **"분산 트레이싱이 어떻게 동작하나요?"**
   → trace_id/span_id 전파, OTel SDK 계측, Collector→Jaeger 파이프라인을 직접 구현하며 이해

2. **"Instana Agent는 어떻게 데이터를 수집하나요?"**
   → OTel SDK(코드 계측) + Prometheus(메트릭 scrape) + Fluent Bit(로그 수집)으로 Agent의 3가지 역할을 분리 구현

3. **"서비스 맵은 어떻게 생성되나요?"**
   → 트레이스의 parent-child span 관계에서 서비스 의존성 추출. Jaeger Dependencies 탭에서 확인

4. **"메트릭-트레이스-로그를 어떻게 연결하나요?"**
   → trace_id가 핵심 링크. 로그에 trace_id 삽입 → Grafana Derived Fields → Jaeger 링크

5. **"알림은 어떻게 동작하나요?"**
   → PromQL 조건(에러율 5%, P99 > 1초) → PrometheusRule → Alertmanager 라우팅

6. **"Kubernetes 환경에서 Observability를 어떻게 구성하나요?"**
   → ServiceMonitor, DaemonSet, Helm chart, namespace 분리 전략을 직접 설계/구현
