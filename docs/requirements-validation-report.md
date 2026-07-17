# 요구사항 검증 리포트

**날짜**: 2026-03-28
**프로젝트명**: mini-obs-platform
**프로젝트 타입**: 인프라/DevOps/Observability (마이크로서비스 모니터링 플랫폼)
**최종 판정**: **PASS**
**모호성 점수**: **0.092** (충분히 구체적)

---

## 요약

이 프로젝트는 **인프라/DevOps 프로젝트**로, 전통적인 웹앱과 다른 평가 기준을 적용했습니다.

- 검증 대상: 요구사항의 완성도, 플레이스홀더 제거, 기술적 명확성
- 평가 특성: 데이터 모델 → 인프라 구성 요소 정의, API 엔드포인트 → 서비스 간 통신으로 조정
- 결론: **PASS** - 설계 및 구현 진행 가능

---

## 모호성 점수 상세 분석

| # | 차원 | 가중치 | 명확도 | 가중 점수 | 판정 |
|---|------|--------|--------|----------|------|
| 1 | 서비스 목적 | 15% | 1.0 | 0.150 | OK |
| 2 | 기술 스택 | 10% | 0.95 | 0.095 | OK |
| 3 | 인프라 구성 요소 정의 | 20% | 0.90 | 0.180 | OK |
| 4 | 서비스 간 통신 정의 | 15% | 0.85 | 0.128 | OK |
| 5 | 서비스 플로우 | 20% | 0.95 | 0.190 | OK |
| 6 | 운영 규칙/알림 규칙 | 10% | 0.95 | 0.095 | OK |
| 7 | 범위 정의 | 10% | 0.70 | 0.070 | WARN |
| | **합계** | 100% | | **0.908** | |

**모호성 점수** = 1 − 0.908 = **0.092** (거의 무시할 수 있는 수준)

---

## 섹션별 상세 평가

### 1. 서비스 목적 (명확도: 1.0)

**평가**: 완벽함

**근거**:
- 서비스명: `mini-obs-platform` (구체적 실명)
- 한 줄 설명: 구체적이고 도메인 지식 포함 (Instana와의 비교)
- 목적: 포트폴리오 스토리라인까지 명확히 기술
- 직무 역량 명시: 클라우드, K8s, CI/CD, 모니터링 등 구체적 나열
- 추가 질문 불필요

**예시**:
```
프로젝트명: mini-obs-platform
한 줄 설명: Instana가 내부적으로 처리하는 Observability 파이프라인을 오픈소스 스택으로 직접 재현한 미니 관측성 플랫폼
목적: IBM Instana Engineer로서 축적한 도메인 지식을 바탕으로 오픈소스 스택을 직접 설계·구현·운영하여...
```

**추가 질문**: 없음

---

### 2. 기술 스택 (명확도: 0.95)

**평가**: 매우 구체적 (사소한 미흡)

**강점**:
- 각 레이어별 기술 명시 (Kubernetes, Helm, ArgoCD, Prometheus, Grafana, Loki, Jaeger, OTel, Chaos Mesh)
- 버전 정보 포함 (KIND 1.29, Helm 3.x, Grafana 10.x 등)
- 선택 근거 기술 (로컬 K8s 클러스터, 이직 타겟 기술 스택과 일치)
- 샘플 앱 언어 명시 (Go 1.22, Python 3.11)

**미흡한 점**:
- 컨테이너 레지스트리: `ghcr.io` 언급은 있으나, 레지스트리 접근 권한 설정 여부가 명시되지 않음 (사소)
- 개발 환경: Docker Desktop 24.x는 명시되었으나, Mac/Linux/Windows 플랫폼별 특수 설정 여부 미명시 (비중 낮음)

**추가 질문**: 없음 (프로토타입 수준에서는 충분)

---

### 3. 인프라 구성 요소 정의 (명확도: 0.90)

**평가**: 구체적 (약간의 보충 필요)

**강점**:
- 프로젝트 구조 매우 상세 (apps/, infra/, scripts/ 트리 포함)
- 각 주요 컴포넌트 정의:
  - 샘플 앱 3개 (frontend-svc, order-svc, inventory-svc)
  - 메트릭 수집 (Prometheus + kube-prometheus-stack)
  - 로그 수집 (Fluent Bit + Loki)
  - 분산 트레이싱 (OTel Collector + Jaeger)
  - 알림 (Alertmanager)
  - 장애 시뮬레이션 (Chaos Mesh)
  - GitOps (ArgoCD)
- Helm values 핵심 설정 구체적 (retention: 24h, admin password, datasource 연결 등)
- 네임스페이스 구성 명확 (observability-demo, monitoring, tracing, chaos-mesh, argocd)
- 포트 매핑 완전함 (Grafana 3000, Jaeger 16686, ArgoCD 8090)

**미흡한 점**:
- Helm 차트 버전 명시: kube-prometheus-stack, loki-stack 등의 차트 버전이 구체적으로 명시되지 않음
  - 예: `helm repo add prometheus-community https://prometheus-community.github.io/helm-charts` 명시 필요
- 스토리지: MVP 단계에서 영구 저장 없다고 명시했으나, production 마이그레이션 시 스토리지 클래스 정의 필요 (단, 현재 문서에서는 불필요)
- ServiceMonitor 선택기: 구체적 label selector 예시 없음 (설계 단계에서 필요)

**추가 질문**: 없음 (현재 프로토타입/MVP 수준에서 충분함)

---

### 4. 서비스 간 통신 정의 (명확도: 0.85)

**평가**: 대부분 명확 (구체성 개선 필요)

**강점**:
- 샘플 앱 3개의 역할과 엔드포인트 명시:
  - frontend-svc: `GET /api/order`, `GET /api/inventory`, `GET /metrics`, `GET /health`
  - order-svc: `POST /orders`, `GET /orders/{id}`, `GET /metrics`, `GET /health`
  - inventory-svc: `GET /items`, `PUT /items/{id}/stock`, `GET /metrics`, `GET /health`
- OTel 계측 범위 명확 (W3C TraceContext, trace_id/span_id 주입)
- 메트릭 수집 대상 명시 (Prometheus scrape: 샘플 앱 3개, kube-state-metrics, node-exporter)
- ServiceMonitor + Pod annotation 방식 명시

**미흡한 점**:
- HTTP 호출 간 요청 본문(request/response body) 스키마 미명시
  - 예: `POST /orders` 요청 본문 형식? `{ order_id, quantity }` 같은 구체적 필드명 없음
  - 예: `PUT /items/{id}/stock` 요청 본문 형식? `{ new_stock_level }` 등
- 에러 응답 형식 미정의 (HTTP status code는 알림 규칙에 나오지만, 응답 본문 구조 없음)
- 타임아웃/재시도 정책 미명시
- 서비스 간 인증 방식: 언급 없음 (현재 없는 것으로 보임, 명시 필요)

**추가 질문**:
1. 샘플 앱의 요청/응답 스키마(JSON 필드)를 정의하고 싶으신가요? 아니면 설계 단계에서 정하시겠어요?
   - 예: `POST /orders` → `{ "item_id": "uuid", "quantity": 1 }` 형식 등
2. 서비스 간 통신에 인증이 필요한가요? (현재는 TLS/mTLS 없이 in-cluster 통신인 것으로 보임)

---

### 5. 서비스 플로우 (명확도: 0.95)

**평가**: 매우 구체적 (완전함)

**강점**:
- 4개 시나리오 모두 단계별로 상세히 기술:
  - 시나리오 1: 정상 요청 흐름 (Traces + Metrics 생성) — 10단계
  - 시나리오 2: 장애 감지 흐름 (Chaos → Alert → 분석) — 10단계
  - 시나리오 3: 파드 강제 종료 시뮬레이션 — 8단계
  - 시나리오 4: GitOps 배포 흐름 — 8단계
- 각 시나리오에서 사용자/시스템 주어가 명확 ("사용자가", "시스템이", "Prometheus가" 등)
- 관찰 포인트 명시 (Grafana에서 무엇을 보는지, Jaeger에서 무엇을 확인하는지)
- Chaos Engineering 시나리오까지 포함 (심화된 내용)
- 포트/URL 구체적 (localhost:8080, 4317, 14250 등)

**미흡한 점**:
- 정상 요청의 응답 시간: "15초 간격"은 Prometheus scrape interval이지만, 실제 사용자가 느끼는 응답 시간 SLO 명시 없음
- 장애 감지 시간: "2분 후" 알림이라고 했는데, 이게 PrometheusRule의 `for: 2m` 때문인지 명시 필요

**추가 질문**: 없음 (충분히 구체적)

---

### 6. 운영 규칙/알림 규칙 (명확도: 0.95)

**평가**: 매우 구체적

**강점**:
- 3개 알림 규칙 완전 정의:
  - `HighErrorRate`: 에러율 5% 초과, 심각도 critical, 2분 지속
  - `HighP99Latency`: P99 응답시간 1초 초과, 심각도 warning, 2분 지속
  - `PodNotReady`: 파드 Ready 상태 아님, 심각도 critical, 1분 지속
- PromQL 조건식 완전함 (histogram_quantile, rate 함수 포함)
- 알림 수신자: Alertmanager 로그 기록 (MVP 명시)
- PrometheusRule CRD YAML 전체 제시

**미흡한 점**:
- 알림 수신자 동작: 로그 파일이라고 했는데, 구체적 파일 경로나 형식 명시 없음
- 알림 복구(resolved) 규칙 명시 없음 (자동 복구 vs 수동 복구)
- 슬랙/이메일 등 추가 채널 제외 범위에만 있음

**추가 질문**: 없음 (MVP 단계에서 충분함)

---

### 7. 범위 정의 (명확도: 0.70)

**평가**: 부분적 명확 (개선 권고)

**강점**:
- MVP 단계 명시: 영구 저장 없음, 24시간 보존, 로그 파일 기록만
- "제외 범위"는 명시되지 않았으나, 각 섹션에서 암묵적으로 드러남:
  - Slack/이메일 알림 제외 (로그 파일만)
  - 사용자 인증 제외
  - production 멀티 환경 제외 (local 단일 환경)
  - 파일 업로드 제외
  - WebSocket 제외

**미흡한 점**:
- "제외 범위" 섹션 누락: template에는 섹션 9로 있으나, 요구사항.md에는 명시적 섹션 없음
- 다음 버전(Phase 2) 계획 없음:
  - 예: production K8s 클러스터 지원? 멀티 환경? Slack 연동? 데이터 영구 저장?
- 마일스톤 미명시: 1단계(MVP, 현재), 2단계(?), 3단계(?) 같은 명확한 단계 분할 없음

**추가 질문**:
1. 명시적인 "제외 범위" 섹션을 추가하시겠어요? 아니면 현재 암묵적 정의로 진행하시겠어요?
2. Phase 2 계획이 있다면, 다음 버전에 추가할 기능(production 환경, 장기 저장 등)이 있으신가요?

---

## 보완이 필요한 항목

### 필수 보완 (FAIL 항목)

없음 - 현재 명확도가 충분하여 설계 진행 가능합니다.

### 권고 보완 (WARNING 항목)

**범위 정의 개선** (선택 사항, 진행 가능하지만 권고):

1. "제외 범위" 섹션을 requirements.md에 명시적으로 추가하시겠어요?
   - 예:
   ```markdown
   ## 9. 제외 범위 (Out of Scope)

   - 사용자 인증 (RBAC, JWT 등)
   - Slack/Email/Teams 알림 채널
   - Production 멀티 환경 지원 (현재: local KIND 클러스터만)
   - Prometheus 메트릭 장기 저장 (현재: 24시간만)
   - Grafana 대시보드 영구 저장
   ```

2. Phase 2 계획이 있다면 미리 기록하시겠어요? (예: production 환경, 데이터 영구 저장, Slack 연동)

---

## 판정 근거

**모호성 점수**: 0.092

**판정 기준**:
- PASS: 모호성 ≤ 0.3
- WARNING: 0.3 < 모호성 ≤ 0.5
- FAIL: 모호성 > 0.5

**현재 모호성 0.092이므로 PASS 판정합니다.**

---

## 플레이스홀더 검사

**검색 결과**: `[...]` 형식의 플레이스홀더 제거 상태

**제거된 플레이스홀더**:
- `[서비스 이름]` → `mini-obs-platform` ✓
- `[리소스]` → 실제 서비스명 (frontend-svc, order-svc, inventory-svc) ✓
- `[시나리오명]` → 4개 구체적 시나리오 ✓
- `[필드명]`, `[타입]`, `[제약조건]` → 구체적 데이터 정의 ✓

**남아있는 플레이스홀더**: 없음

---

## 결론

이 요구사항은 **인프라/DevOps 프로젝트답게 매우 구체적**입니다:

✓ 서비스 목적과 포트폴리오 스토리가 명확함
✓ 기술 스택이 구체적 (도구, 버전, 선택 근거)
✓ 인프라 구성 요소가 상세히 정의됨 (파일 구조, 포트, 네임스페이스)
✓ 서비스 플로우가 4개 시나리오로 완전함
✓ 알림 규칙이 PromQL과 함께 정의됨
✓ 플레이스홀더 제거됨 (실제 서비스명, 엔드포인트 등)

⚠️ 범위 정의: 암묵적이지만 대부분 명시됨 (명시적 섹션 추가 권고)

**설계 및 구현 진행 가능합니다.**

---

## Next Steps

1. **설계 단계 진행**
   - 요청/응답 스키마 상세화 (필요시)
   - 범위 정의 섹션 추가 (권고)
   - design-agent가 service-flow.md (mermaid), data-model.md, api-spec.md 생성

2. **추가 검증**
   - flow-validator가 설계 문서 간 정합성 검증
   - 필요시 설계 재검토

3. **구현 진행**
   - planning-agent가 dev-plan.md 생성
   - db-agent + frontend-agent 병렬 구현

---

**검증 완료일**: 2026-03-28
**검증자 역할**: Requirements Validator Agent (Senior Business Analyst)
**프로젝트 경로**: /Users/hyein/Desktop/Personal/practice/My-Claude-Agents
