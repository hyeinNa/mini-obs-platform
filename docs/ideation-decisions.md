# 아이데이션 결정 기록

**날짜**: 2026-03-28
**원본 아이디어**: IBM Instana Engineer로 근무 중이며, 인프라/모니터링 직무로 이직 준비 중. Instana가 내부적으로 하는 일을 오픈소스 스택(Prometheus, Grafana, OpenTelemetry, Jaeger, Loki)으로 직접 재현하는 Mini Observability Platform을 구축하고 싶음.

**핵심 컨텍스트**:
- 현재 IBM Instana Engineer, 클라우드/K8s 인프라·모니터링 직무로 이직 준비
- 전통적인 웹앱이 아닌 인프라/DevOps 포트폴리오 프로젝트
- "Instana가 자동화한 것을 직접 오픈소스로 재현"하는 스토리라인이 핵심

---

## 주요 결정 사항

### 결정 1: 트레이싱 백엔드 — Jaeger vs Tempo

- **선택지**: Jaeger (CNCF 졸업 프로젝트) vs Grafana Tempo (LGTM 스택 네이티브)
- **선택**: Jaeger
- **근거**:
  - 사용자가 명시적으로 Jaeger를 기술 스택으로 언급
  - Instana는 내부적으로 OpenTracing/OpenTelemetry 호환 트레이싱 표준을 사용하므로, Jaeger는 직접 비교 포인트가 됨
  - Jaeger는 독립 UI를 제공해 포트폴리오 시연 시 분리된 화면 구성 가능
  - Tempo는 Grafana 내에서만 조회 가능해 시연 시 Jaeger보다 직관성이 떨어짐
- **사용자 확인 필요 여부**: N (명시적 요구사항)

---

### 결정 2: 샘플 앱 서비스 수 — 3개 vs 5개

- **선택지**: 3개 서비스 (frontend + order + inventory) vs 5개 이상 (결제, 배송 등 추가)
- **선택**: 3개
- **근거**:
  - 사용자 아이디어에 "3-4개 서비스"로 명시
  - 분산 트레이싱의 핵심 개념(parent-child span 전파)을 보여주는 최소 단위는 3개
  - 서비스를 더 추가할수록 OTel 계측 코드의 반복이 늘어나고, 차별화된 역량 증명보다 코드 양이 늘어나는 방향
  - MVP 완성도를 높이고 장애 시뮬레이션 시나리오를 충분히 구성하는 것이 더 효과적
- **사용자 확인 필요 여부**: N

---

### 결정 3: 샘플 앱 언어 구성 — Go + Python vs 단일 언어

- **선택지**: A) Go + Python 혼합 | B) Go만 | C) Python만
- **선택**: A) Go(frontend-svc) + Python(order-svc, inventory-svc)
- **근거**:
  - 사용자가 "Python/Go"를 명시
  - 두 언어에서 OTel SDK 계측 방식이 다름 → 폴리글랏 환경의 tracing context 전파 이해를 증명 가능
  - 이직 타겟 JD에서 Go가 K8s/인프라 도구 주요 언어, Python이 자동화 스크립트 언어로 자주 요구됨
  - frontend-svc를 Go로 구현하면 `otelhttp` 미들웨어 패턴, Python 서비스에서는 `opentelemetry-instrumentation-fastapi` 자동 계측 패턴을 각각 보여줄 수 있음
- **사용자 확인 필요 여부**: Y — Go와 Python 모두 익숙한지, 한 언어로 통일할지 확인 권장

---

### 결정 4: 로컬 K8s 환경 — KIND vs minikube vs k3d

- **선택지**: KIND | minikube | k3d
- **선택**: KIND
- **근거**:
  - 사용자가 "kind/minikube" 모두 언급했으나, KIND가 레퍼런스 조사(otel-observability-gitops)에서 사실상 표준
  - KIND는 Docker 컨테이너 기반이라 멀티 노드(control-plane + 2 worker) 구성이 쉬움
  - kube-prometheus-stack + 여러 컴포넌트를 동시에 배포하면 리소스 요구량이 높아, 단일 VM인 minikube보다 KIND 멀티 노드가 유연
  - k3d는 경량이지만 KIND가 CNCF 커뮤니티에서 더 광범위하게 사용됨
- **사용자 확인 필요 여부**: Y — 호스트 머신 사양(RAM 16GB 이상 권장) 확인 필요. 8GB이면 컴포넌트 수를 줄여야 할 수 있음

---

### 결정 5: ArgoCD App of Apps 패턴 적용

- **선택지**: A) App of Apps 패턴 | B) 각 컴포넌트 독립 ArgoCD Application | C) Kustomize 기반
- **선택**: A) App of Apps 패턴
- **근거**:
  - 레퍼런스 조사(otel-observability-gitops)에서 동일 목적 프로젝트가 이 패턴을 사용
  - 전체 observability 스택을 단일 ArgoCD Application 하나로 부트스트랩 가능 → 포트폴리오 시연 시 "ArgoCD App 하나 apply하면 전체 스택 자동 배포" 스토리 구성
  - GitOps 역량 증명에 더 효과적 (단순 ArgoCD 사용보다 패턴 이해 증명)
- **사용자 확인 필요 여부**: N

---

### 결정 6: Alertmanager 수신자 — Slack 연동 포함 여부

- **선택지**: A) Slack webhook 연동 | B) 로그 파일 기록만 | C) 이메일 연동
- **선택**: B) 로그 파일 기록만 (MVP)
- **근거**:
  - 알림 역량 증명은 PrometheusRule CRD 작성과 PromQL 조건 정의에 있음. 실제 Slack 전송 여부는 부차적
  - Slack workspace 설정은 포트폴리오 구축 환경에 따라 다르므로 MVP에서 제외
  - README와 `alertmanager-config.yaml`에 Slack 연동 주석처리 예시를 남겨 "확장 가능성"을 보여주는 것으로 대체
- **사용자 확인 필요 여부**: Y — Slack 연동이 시연 시 필요한지 확인 권장 (면접관에게 직접 보여줄 경우 임팩트 있음)

---

### 결정 7: 장애 시뮬레이션 도구 — Chaos Mesh vs LitmusChaos vs 직접 구현

- **선택지**: Chaos Mesh | LitmusChaos | 직접 Python 스크립트로 에러율 조작
- **선택**: Chaos Mesh
- **근거**:
  - 레퍼런스 조사에서 Chaos Mesh가 K8s 전용으로 설치 간단, CRD 기반 선언적 실험 정의가 GitOps와 자연스럽게 통합
  - LitmusChaos는 K8s 외 환경도 지원하지만 MVP 범위에서 불필요한 복잡도
  - 직접 구현(FastAPI에 에러율 엔드포인트 추가)은 실제 인프라 레벨 장애를 시뮬레이션하지 못해 Instana 역량 증명에 약함
  - Chaos Mesh NetworkChaos는 Instana가 감지하는 네트워크 레이턴시 이상과 동일한 패턴 재현 가능
- **사용자 확인 필요 여부**: N

---

### 결정 8: 메트릭 보존 기간 및 영구 볼륨

- **선택지**: A) emptyDir (파드 재시작 시 데이터 초기화) | B) PersistentVolume | C) 외부 저장소 (Thanos)
- **선택**: A) emptyDir
- **근거**:
  - 로컬 개발 환경에서 PV 프로비저닝은 hostPath를 사용해야 하는데, 프로덕션 패턴과 달라 오히려 혼란을 초래
  - 포트폴리오 목적은 데이터 영구 저장보다 파이프라인 구성과 시각화 능력 증명
  - Prometheus retention을 24시간으로 설정해 시연 세션 내에서 충분한 데이터 유지
  - README에 "프로덕션에서는 PV 또는 Thanos 적용" 명시로 이해도 증명
- **사용자 확인 필요 여부**: N

---

### 결정 9: CI/CD 이미지 레지스트리 — ghcr.io vs Docker Hub

- **선택지**: GitHub Container Registry (ghcr.io) | Docker Hub
- **선택**: ghcr.io
- **근거**:
  - GitHub Actions와 동일 플랫폼 → GITHUB_TOKEN으로 추가 자격증명 없이 push 가능
  - 포트폴리오 리포지토리가 GitHub에 있으므로 ghcr.io 이미지도 함께 공개적으로 조회 가능
  - Docker Hub는 무료 플랜 pull rate limit 이슈 있음
- **사용자 확인 필요 여부**: N

---

### 결정 10: 부하 생성기 포함 여부

- **선택지**: A) k6 또는 Locust 부하 생성기 포함 | B) bash 스크립트 루프 | C) 제외
- **선택**: B) bash 스크립트 루프 (간단한 while-curl 루프)
- **근거**:
  - k6/Locust를 별도 서비스로 배포하면 프로젝트 복잡도 증가
  - Grafana 대시보드 시연에 필요한 최소한의 트래픽 생성은 `while true; do curl ...; sleep 0.5; done` 수준으로 충분
  - 성능 테스트 자체가 이 프로젝트의 목적이 아님 — Observability 파이프라인이 목적
  - `scripts/run-chaos.sh`에 부하 생성 옵션 포함하는 것으로 정리
- **사용자 확인 필요 여부**: N

---

## MVP 포함/제외 결정 요약

| 기능 | MVP 포함 | 결정 근거 |
|------|----------|-----------|
| 샘플 마이크로서비스 3개 (Go + Python) | O | Observability 파이프라인 시연을 위한 기반 |
| OTel SDK 계측 + Collector 파이프라인 | O | 핵심 역량 증명 (Instana 오픈소스 재현) |
| Prometheus + kube-prometheus-stack | O | 메트릭 수집 업계 표준 |
| Grafana RED 메트릭 대시보드 3개 | O | 시각화 역량 증명 |
| Jaeger 분산 트레이싱 | O | 사용자 명시 요구사항 |
| Fluent Bit → Loki 로그 파이프라인 | O | 사용자 명시 요구사항 |
| Alertmanager PrometheusRule 3개 | O | 알림 설계 역량 증명 |
| Chaos Mesh 장애 시뮬레이션 | O | Instana 이상 감지 시나리오 재현 |
| ArgoCD App of Apps GitOps | O | GitOps 역량 증명 |
| GitHub Actions CI/CD | O | CI/CD 파이프라인 역량 증명 |
| Grafana Provisioning 자동화 | O | IaC 원칙 준수 |
| Slack 알림 연동 | X | MVP에서 제외, 확장 예시로 문서화 |
| Grafana Tempo (트레이싱 백엔드) | X | Jaeger 선택 |
| Thanos / Cortex | X | MVP 범위 초과 |
| Istio 서비스 메시 | X | OTel SDK 계측으로 충분 |
| PersistentVolume | X | 로컬 환경 emptyDir로 단순화 |
| k6 / Locust 부하 생성기 | X | bash 루프로 대체 |
| ELK 스택 | X | Loki + Grafana로 충분 |

---

## 사용자에게 확인받을 사항

requirements.md를 리뷰할 때 아래 항목을 특히 확인해주세요:

1. **Go + Python 혼합 구성**: frontend-svc를 Go로 구현하는 것이 적합한지, 모두 Python FastAPI로 통일할지 확인해주세요 (결정 3). Go 익숙도가 낮다면 Python 단일 언어로 진행하는 것도 충분히 효과적입니다.

2. **호스트 머신 메모리**: KIND 3-node 클러스터 + kube-prometheus-stack + Loki + Jaeger + OTel Collector + 샘플 앱을 동시에 띄우면 RAM 12~16GB 이상 필요합니다. 개발 머신 사양이 충분한지 확인 후, 필요시 컴포넌트 수를 줄이거나 minikube 단일 노드로 변경하겠습니다 (결정 4).

3. **Slack 알림 연동**: 면접 시연 시 실제 알림 전송이 필요하다면 Alertmanager Slack webhook 설정을 MVP에 포함하겠습니다 (결정 6). 알림 화면을 직접 보여주는 것이 포트폴리오 임팩트에 도움이 됩니다.

4. **샘플 앱 도메인 선택**: 현재 "주문(order)/재고(inventory)" 도메인으로 설정했습니다. Instana 업무와 더 직접적으로 연결되는 다른 도메인(예: 모니터링 에이전트를 모사한 서비스)이 있다면 변경 가능합니다.

5. **ArgoCD GitHub 리포 연동**: ArgoCD가 실제 GitHub 리포지토리를 바라보도록 설정하려면 리포 URL과 접근 설정이 필요합니다. requirements.md에 구체적인 리포 URL을 반영하려면 알려주세요.
