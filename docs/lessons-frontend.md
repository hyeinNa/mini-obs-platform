# Lessons — Infrastructure / DevOps Tasks

## 2026-03-28 | mini-obs-platform

**에이전트**: frontend-agent (infra role)
**문제**: ArgoCD App of Apps에서 Helm chart values를 참조할 때 `valueFiles` 경로로 raw GitHub URL을 사용하는 패턴이 필요한데, 로컬 상대 경로만으로는 remote chart source와 로컬 values 파일을 동시에 지정할 수 없다.
**해결**: ArgoCD Application의 `source.helm.valueFiles`에 `https://raw.githubusercontent.com/...` raw URL 형태로 values 파일 경로를 지정. 또는 Helm chart와 values를 같은 Git 레포에 두고 multi-source Application 패턴 사용을 검토할 것.
**교훈**: ArgoCD에서 외부 Helm 레포 chart + 자체 Git values를 동시에 사용하려면 ArgoCD 2.6+의 multiple sources 기능(`spec.sources` 배열) 또는 raw GitHub URL valueFiles 중 하나를 선택해야 한다. 프로젝트 초기에 이 결정을 내려야 ArgoCD Application 파일 구조가 일관성 있게 유지된다.

**에이전트**: frontend-agent (infra role)
**문제**: Jaeger Helm chart의 all-in-one 모드에서 기본 서비스 타입이 ClusterIP이므로, KIND 클러스터의 NodePort 30001 포트 매핑을 활용하려면 별도 NodePort 서비스 또는 values.yaml에서 서비스 타입 오버라이드가 필요하다. Helm chart values 구조가 버전마다 다르기 때문에 `service.type: NodePort` 설정이 어느 서비스에 적용되는지 주의해야 한다.
**해결**: Jaeger values.yaml에 NodePort 설정 주석으로 명시하고, 실제 NodePort 서비스는 manifests/apps 또는 Jaeger chart의 query.service.type으로 설정. `jaegertracing/jaeger` chart에서 all-in-one 모드 시 `allInOne.service.type: NodePort`로 지정하는 것이 올바른 키 경로.
**교훈**: 인프라 Helm chart의 서비스 노출 설정은 chart 버전과 모드(all-in-one vs. distributed)에 따라 values 키 경로가 다르다. 배포 전 `helm show values <chart>` 로 실제 values 구조를 반드시 확인할 것.

**에이전트**: frontend-agent (infra role)
**문제**: `kube-prometheus-stack`의 PrometheusRule 자동 로드를 위해 `ruleSelector`와 `ruleSelectorNilUsesHelmValues: false` 설정이 모두 필요한데, values.yaml에서 `ruleSelector: {}` (빈 셀렉터, 모두 허용)와 `ruleSelectorNilUsesHelmValues: false`를 함께 써야 외부 네임스페이스의 PrometheusRule도 수집된다.
**해결**: values.yaml에 `prometheus.prometheusSpec.ruleSelectorNilUsesHelmValues: false`와 `prometheus.prometheusSpec.ruleSelector: {}`를 명시적으로 설정. ServiceMonitor도 동일하게 `serviceMonitorSelectorNilUsesHelmValues: false`와 `serviceMonitorSelector: {}` 필요.
**교훈**: kube-prometheus-stack 배포 시 다른 네임스페이스의 ServiceMonitor/PrometheusRule을 수집하려면 Nil Uses Helm Values 플래그를 반드시 false로 설정해야 한다. 기본값(true)은 Helm chart 자신의 레이블이 있는 리소스만 수집한다.

**에이전트**: frontend-agent (infra role)
**문제**: Fluent Bit의 Loki output 플러그인이 기본 Helm chart에 포함되지 않는 경우가 있다. `fluent/fluent-bit` chart의 일부 버전은 Loki output을 built-in으로 지원하지만, 버전에 따라 별도 플러그인 설치가 필요하다.
**해결**: `fluent/fluent-bit` 공식 chart 0.43.x 이상에서는 Loki output이 기본 포함된 `fluent-bit:2.x` 이미지를 사용. values.yaml에서 image tag를 `2.2.2`로 고정. `[OUTPUT] Name loki` 설정에서 Host/Port 방식 사용(HTTP endpoint).
**교훈**: Fluent Bit Loki output 플러그인 사용 시 반드시 이미지 버전과 chart 버전이 built-in Loki plugin을 포함하는지 확인. Loki output HTTP endpoint 형식: `Host loki.monitoring.svc.cluster.local`, `Port 3100`.

**에이전트**: frontend-agent (infra role)
**문제**: KIND 클러스터의 extraPortMappings는 control-plane 노드에만 설정된다. NodePort 서비스(Grafana 30000, Jaeger 30001, ArgoCD 30002)가 worker 노드에 스케줄되면 포트 매핑이 작동하지 않는다.
**해결**: 각 NodePort 서비스를 control-plane 노드에 강제 스케줄하거나 (nodeSelector 사용), 또는 KIND에서 모든 노드에 extraPortMappings를 동일하게 설정. 가장 단순한 해결책은 port-forward를 병행 제공하는 것 (scripts/port-forward.sh).
**교훈**: KIND extraPortMappings는 control-plane 노드에만 유효하다. NodePort 서비스가 worker 노드에 스케줄될 경우 포트 매핑이 실패한다. 로컬 KIND 환경에서는 NodePort보다 `kubectl port-forward`가 더 안정적인 접근 방법이다. 두 방법을 모두 제공하는 스크립트 구성이 권장된다.
