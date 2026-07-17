# QA 교훈 기록

---

### 2026-03-28 | mini-obs-platform

**에이전트**: qa-agent

---

#### 교훈 1: Helm all-in-one 차트의 서비스명은 서브컴포넌트 이름과 다르다

**문제**: Jaeger Helm 차트에서 `allInOne.enabled=true`, `collector.enabled=false`로 설정했을 때, OTel Collector가 참조한 `jaeger-collector.tracing.svc.cluster.local`와 Grafana datasource가 참조한 `jaeger-query.tracing.svc.cluster.local` 서비스가 실제로 생성되지 않음.

**해결**: Helm 차트 all-in-one 모드에서 생성되는 실제 서비스명인 `jaeger-all-in-one.tracing.svc.cluster.local`으로 모든 참조를 변경.

**교훈**: all-in-one 방식 Helm 차트(Jaeger, Elasticsearch 등)를 사용할 때는 반드시 `helm template` 으로 실제 생성되는 Service 리소스 이름을 먼저 확인하고 다운스트림 참조를 설정해야 한다. 컴포넌트별 서비스명(`jaeger-collector`, `jaeger-query`)은 각 컴포넌트가 `enabled=true`일 때만 존재한다.

---

#### 교훈 2: KIND extraPortMappings는 NodePort 서비스가 별도로 필요하다

**문제**: `kind-config.yaml`에 containerPort 30001 → hostPort 16686 매핑이 정의되어 있었으나, nodePort 30001을 사용하는 K8s NodePort Service 매니페스트가 없어서 실제로 localhost:16686에서 Jaeger UI에 접근 불가.

**해결**: `infra/manifests/monitoring/jaeger-nodeport.yaml` 생성 및 `deploy-all.sh`에 ArgoCD NodePort 패치 추가.

**교훈**: KIND 포트 매핑은 "클러스터 노드의 특정 포트를 로컬호스트로 노출"하는 것이므로, 해당 nodePort를 listen하는 K8s Service가 반드시 존재해야 한다. 설계 시 KIND config와 NodePort Service 매니페스트를 항상 쌍으로 작성하고 체크리스트로 관리할 것.

---

#### 교훈 3: CD 워크플로우의 sed 패턴은 idempotent하게 작성해야 한다

**문제**: CD 워크플로우가 이미지 태그 업데이트 시 `s|ghcr.io/owner/...|...|` 패턴을 사용. 최초 실행 후 `owner` 플레이스홀더가 실제 소유자명으로 교체되면 이후 실행에서 패턴이 매칭되지 않아 이미지 태그가 갱신되지 않음.

**해결**: 소유자명 부분을 와일드카드로 변경 (`s|ghcr.io/.*/mini-obs-<svc>:.*|...|`).

**교훈**: GitOps 이미지 태그 업데이트 스크립트의 sed/awk 패턴은 반드시 idempotent해야 한다. 특히 플레이스홀더(`owner`, `latest`)가 포함된 초기 상태에서만 동작하는 패턴은 프로덕션 환경에서 자동화가 조용히 실패한다. 패턴에는 특정 소유자나 초기 태그를 하드코딩하지 말고 와일드카드를 사용할 것.

---

#### 교훈 4: Python 타입 힌트 문법은 최소 지원 버전을 기준으로 작성해야 한다

**문제**: `inventory-svc/tests/test_unit.py`에서 `int | None` 유니온 타입 힌트 문법 사용. Python 3.10 이상에서만 지원되는 문법이나 시스템 Python 3.9에서 `TypeError` 발생.

**해결**: 파일 첫 줄에 `from __future__ import annotations` 추가.

**교훈**: Python 서비스의 최소 지원 버전(pyproject.toml의 `requires-python`)에 맞는 문법을 사용해야 한다. Python 3.9 호환이 필요하면 `Optional[int]` 또는 `from __future__ import annotations`를 사용. CI에서 테스트 환경의 Python 버전과 프로덕션 Docker 이미지 버전이 일치하는지 확인할 것.

---

#### 교훈 5: Grafana 대시보드 JSON 파일은 ConfigMap으로 래핑되어야 한다

**문제**: `infra/manifests/monitoring/dashboards/` 에 3개의 Grafana 대시보드 JSON 파일이 존재하지만, kube-prometheus-stack의 Grafana sidecar가 자동으로 로드하는 ConfigMap 형식으로 래핑되지 않음. Grafana 시작 시 대시보드가 자동 임포트되지 않는다.

**해결**: 미수정 (권고사항으로 기록).

**교훈**: kube-prometheus-stack의 Grafana sidecar는 `grafana_dashboard: "1"` 레이블을 가진 ConfigMap에서 JSON을 자동 로드한다. 대시보드 파일을 단독 JSON으로 보관하는 것만으로는 부족하며, 반드시 ConfigMap 래핑이 필요하다. 설계 시 대시보드 프로비저닝 방식(sidecar ConfigMap vs Helm values grafana.dashboards)을 명시적으로 정의하고 해당 매니페스트를 함께 작성할 것.

---

#### 교훈 6: 미사용 임포트는 CI에서 자동으로 잡힌다 (ruff 활용)

**문제**: `order-svc/metrics.py`에서 `REGISTRY`가 임포트되었으나 사용되지 않음.

**해결**: 임포트 제거.

**교훈**: ruff의 `F401` 규칙은 미사용 임포트를 자동으로 감지한다. CI에서 `ruff check` 단계가 있으면 이런 문제가 조기에 차단된다. 이미 ci.yaml에 ruff 단계가 포함되어 있으므로 향후에는 CI에서 차단됨.

---

#### 교훈 7: service-flow.md flowchart는 실제 API 호출과 일치해야 한다

**문제**: `service-flow.md` flowchart 2번에서 `ORD → GET http://inventory-svc:8082/items`로 표기되었으나 실제 코드는 `PUT /items/{item_id}/stock`을 호출.

**해결**: 문서 수정 권고 (미수정).

**교훈**: 서비스 플로우 다이어그램의 화살표 레이블에 실제 API 메서드와 경로를 명시할 때 api-spec.json과 교차 검증해야 한다. 특히 flowchart와 sequence diagram이 동일한 흐름을 다른 방식으로 표현할 때, 두 다이어그램의 일관성을 점검해야 한다. 설계 단계 flow-validator가 이를 체크하도록 검증 항목에 추가할 것.
