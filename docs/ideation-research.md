# 레퍼런스 조사 — Mini Observability Platform

## 조사 키워드

- microservices observability platform Prometheus Grafana OpenTelemetry Jaeger Loki open source demo project 2024 2025
- opentelemetry-demo microservices kubernetes helm argocd gitops observability stack implementation
- chaos engineering kubernetes chaos mesh litmus fault injection microservices RED metrics
- Google Hipster Shop Online Boutique microservices demo observability tracing Prometheus Grafana
- Fluent Bit Loki Kubernetes log collection pipeline DaemonSet configuration
- Prometheus custom exporter Python Go RED metrics Alertmanager rules Kubernetes

---

## 유사 서비스/프로젝트 분석

### OpenTelemetry Astronomy Shop (공식 OTel 데모)

- **URL**: https://opentelemetry.io/docs/demo/kubernetes-deployment/
- **GitHub**: https://github.com/open-telemetry/opentelemetry-demo
- **핵심 기능**:
  - 10개 이상의 폴리글랏 마이크로서비스 (Go, Python, Java, Node.js, .NET, Ruby, PHP)
  - OpenTelemetry SDK로 traces, metrics, logs 동시 계측
  - OTel Collector → Jaeger(트레이싱) + Prometheus(메트릭) + Grafana(시각화) 파이프라인
  - Kubernetes Helm chart로 단일 명령 배포 (`helm install`)
  - Grafana에 사전 구성된 RED 메트릭 대시보드 포함
  - Flagd feature flag service로 장애 시뮬레이션 활성화/비활성화
- **참고할 점**:
  - OTel Collector를 중간 게이트웨이로 사용하는 패턴 (앱 → Collector → 백엔드) 채택
  - feature flag 기반 장애 주입은 우리 프로젝트에서 Chaos Mesh로 대체
  - 각 서비스가 `/metrics` 엔드포인트를 노출하고 Prometheus가 scrape하는 패턴
- **기술 스택**: Kubernetes, Helm, OTel SDK, Jaeger, Prometheus, Grafana, Loki

---

### otel-observability-gitops (GitOps 구성 참고)

- **URL**: https://github.com/rushi2828/otel-observability-gitops
- **핵심 기능**:
  - App of Apps 패턴으로 ArgoCD를 통한 전체 observability 스택 GitOps 관리
  - KIND 클러스터에서 로컬 개발 환경 구성
  - NGINX Ingress + TLS 라우팅으로 각 UI(Grafana, Jaeger, ArgoCD) 외부 노출
  - Helm values 파일 환경별 분리 (dev/prod)
  - ArgoCD Application CRD로 각 컴포넌트 독립 배포·동기화
- **참고할 점**:
  - App of Apps 패턴: 최상위 ArgoCD Application이 하위 Application들을 관리
  - KIND + NGINX Ingress 조합이 로컬 K8s 테스트 표준으로 자리잡음
  - `argocd/apps/` 디렉토리에 컴포넌트별 Application manifest 구성
- **기술 스택**: KIND, ArgoCD, Helm, NGINX Ingress Controller

---

### Google Online Boutique (Hipster Shop) + Prometheus/Grafana

- **URL**: https://github.com/GoogleCloudPlatform/microservices-demo
- **참고 프로젝트**: https://github.com/daviddetorres/hipster-metrics-with-prometheus
- **핵심 기능**:
  - 11개 마이크로서비스, 다중 언어 (Go, Python, Java, Node.js, C#)
  - gRPC 기반 서비스 간 통신
  - kube-prometheus-stack Helm chart로 Prometheus Operator + Grafana 배포
  - 서비스별 ServiceMonitor CRD로 메트릭 scrape 대상 선언적 관리
  - 기본 K8s 메트릭(CPU/Memory) + 애플리케이션 커스텀 메트릭 혼합 대시보드
- **참고할 점**:
  - `prometheus.io/scrape: "true"` Pod annotation으로 자동 discovery
  - ServiceMonitor 패턴: Prometheus Operator 환경에서의 표준 scrape 설정 방식
  - 다중 언어 서비스 각각에 맞는 OTel SDK 사용 패턴 (언어별 client library)
- **기술 스택**: Kubernetes, kube-prometheus-stack, Prometheus Operator

---

### Springboot Observability Demo (Grafana + Prometheus + Tempo + Loki)

- **URL**: https://github.com/ashenwgt/springboot-observability-grafana-prometheus-tempo-loki
- **핵심 기능**:
  - Grafana LGTM 스택 (Loki + Grafana + Tempo + Mimir) 통합 구성
  - Tempo를 Jaeger 대체 트레이싱 백엔드로 사용 (OTLP 수신)
  - Loki + Promtail(혹은 Fluent Bit) 로그 수집 파이프라인
  - Grafana Explore로 로그 ↔ 트레이스 ↔ 메트릭 상호 연결 (correlation)
  - 단일 docker-compose로 전체 스택 구동 (로컬 개발)
- **참고할 점**:
  - Trace ID를 로그에 자동 삽입하면 Grafana에서 로그 → 트레이스 점프 가능
  - `traceId` 필드를 Loki 레이블로 인덱싱하는 설정 패턴
  - Grafana 데이터소스 provisioning 파일(`provisioning/datasources/`)로 자동 설정

---

### LitmusChaos + Chaos Mesh (장애 시뮬레이션)

- **URL (Chaos Mesh)**: https://chaos-mesh.org/
- **URL (Litmus)**: https://github.com/litmuschaos/litmus
- **핵심 기능 (Chaos Mesh)**:
  - PodChaos: 파드 강제 종료, 컨테이너 kill
  - NetworkChaos: 네트워크 지연(latency), 패킷 손실(loss), 대역폭 제한
  - StressChaos: CPU/메모리 부하 주입
  - TimeChaos: 시스템 시계 조작
  - 웹 UI Dashboard로 실험 생성·모니터링
  - CRD 기반 선언적 카오스 실험 정의 (`PodChaos`, `NetworkChaos` 등)
- **참고할 점**:
  - Chaos Mesh는 K8s 전용, 설치 간단 (Helm 단일 명령), 포트폴리오 적합
  - NetworkChaos로 서비스 간 지연 주입 → Grafana에서 RED 메트릭 변화 관찰
  - PodChaos로 파드 종료 → Alertmanager 알림 트리거 시나리오 구성 가능

---

### Fluent Bit → Loki 로그 파이프라인

- **URL**: https://fluentbit.net/set-up-fluent-bit-for-grafana-loki-in-kubernetes/
- **공식 문서**: https://docs.fluentbit.io/manual/data-pipeline/outputs/loki
- **핵심 구성**:
  - DaemonSet으로 모든 노드에 배포, `/var/log/containers/*.log` tail 수집
  - Kubernetes Filter 플러그인으로 파드 메타데이터(namespace, pod_name, container_name) 자동 추가
  - Loki output 플러그인: `labels = namespace, pod, container` 설정
  - `auto_kubernetes_labels on` 옵션으로 Pod 레이블 자동 스트림 분류
  - Helm chart: `helm repo add fluent https://fluent.github.io/helm-charts`
- **참고할 점**:
  - Fluent Bit ConfigMap에 `[FILTER] Name kubernetes` 설정이 핵심
  - Loki에서 `{namespace="observability-demo", pod=~"frontend.*"}` 형식으로 조회
  - OTel SDK로 주입한 `trace_id`를 로그 레이블로 추가하면 Grafana correlation 활성화

---

## 공통 패턴 정리

| 패턴 | 설명 | 채택 여부 |
|------|------|-----------|
| OTel Collector 중간 게이트웨이 | 앱 → Collector → Jaeger/Prometheus 파이프라인 | 채택 |
| kube-prometheus-stack Helm | Prometheus + Alertmanager + Grafana 일괄 배포 | 채택 |
| ServiceMonitor CRD | Prometheus Operator 환경 scrape 대상 선언 | 채택 |
| Pod annotation auto-discovery | `prometheus.io/scrape: "true"` | 채택 (보조) |
| App of Apps (ArgoCD) | 최상위 Application이 하위 Application 관리 | 채택 |
| Fluent Bit DaemonSet | 노드별 로그 수집, Kubernetes 메타데이터 주입 | 채택 |
| RED 메트릭 대시보드 | Rate / Errors / Duration 3개 핵심 지표 | 채택 |
| Trace ID 로그 주입 | OTel SDK가 trace_id를 구조화 로그에 자동 삽입 | 채택 |
| Chaos Mesh NetworkChaos | K8s CRD로 선언적 장애 주입 | 채택 |
| Grafana provisioning | datasource/dashboard JSON 자동 프로비저닝 | 채택 |
| feature flag 장애 토글 | Flagd 기반 소프트웨어 장애 주입 | 미채택 (Chaos Mesh로 대체) |
| Tempo (트레이싱 백엔드) | Jaeger 대신 Tempo | 미채택 (Jaeger 선택: Instana 친숙도) |
| 멀티 클러스터 Thanos | Prometheus 장기 저장 + 멀티 클러스터 | 미채택 (MVP 범위 초과) |

---

## MVP 포함 기능 확정 목록

조사 결과 기반 MVP 핵심 기능:

1. **샘플 마이크로서비스 앱** — 3개 서비스 (frontend/Go, order-service/Python, inventory-service/Python), gRPC + REST 혼합, OTel SDK 계측
2. **메트릭 수집** — Prometheus + kube-prometheus-stack, 커스텀 exporter (Python prometheus_client), ServiceMonitor CRD
3. **분산 트레이싱** — OTel SDK → OTel Collector → Jaeger, trace_id 로그 연동
4. **로그 수집** — Fluent Bit DaemonSet → Loki, Kubernetes 메타데이터 주입
5. **대시보드** — Grafana RED 메트릭 대시보드, 서비스 맵, 로그 탐색, Provisioning 자동화
6. **알림** — Alertmanager PrometheusRule CRD, HighErrorRate / HighLatency / PodDown 규칙 3개
7. **장애 시뮬레이션** — Chaos Mesh NetworkChaos(지연 주입) + PodChaos(파드 종료) CRD
8. **GitOps** — ArgoCD App of Apps 패턴, Helm values 환경 분리
9. **CI/CD** — GitHub Actions: lint → test → docker build → image push → ArgoCD sync 트리거

---

## Sources

- [OpenTelemetry Demo Kubernetes Deployment](https://opentelemetry.io/docs/demo/kubernetes-deployment/)
- [otel-observability-gitops (GitHub)](https://github.com/rushi2828/otel-observability-gitops)
- [GoogleCloudPlatform/microservices-demo](https://github.com/GoogleCloudPlatform/microservices-demo)
- [Hipster Shop Metrics with Prometheus](https://github.com/daviddetorres/hipster-metrics-with-prometheus)
- [Springboot Observability Demo (GitHub)](https://github.com/ashenwgt/springboot-observability-grafana-prometheus-tempo-loki)
- [Chaos Mesh Official Site](https://chaos-mesh.org/)
- [LitmusChaos GitHub](https://github.com/litmuschaos/litmus)
- [Fluent Bit + Loki Kubernetes Setup](https://fluentbit.net/set-up-fluent-bit-for-grafana-loki-in-kubernetes/)
- [Fluent Bit Loki Output Plugin (Official Docs)](https://docs.fluentbit.io/manual/data-pipeline/outputs/loki)
- [Prometheus Custom Exporter in Go](https://www.civo.com/learn/build-your-own-prometheus-exporter-in-go)
- [Developing Custom Exporter for Prometheus Using Python](https://www.gspann.com/resources/blogs/developing-custom-exporter-for-prometheus-using-python/)
- [Kubernetes Observability with OpenTelemetry — SigNoz](https://signoz.io/blog/kubernetes-observability-with-opentelemetry/)
- [Practical Guide to Chaos Engineering — youngju.dev](https://www.youngju.dev/blog/devops/2026-03-09-devops-chaos-engineering-litmus-chaos-mesh.en)
- [Mastering Observability: Deploying OTel Demo on Kubernetes — DEV Community](https://dev.to/barda/mastering-observability-deploying-the-opentelemetry-demo-on-kubernetes-fbg)
- [Kubernetes Alerting with Prometheus & Alertmanager — Medium](https://medium.com/@bavicnative/alerting-incident-management-in-kubernetes-configuring-alerts-with-alertmanager-f744500c4b9b)
