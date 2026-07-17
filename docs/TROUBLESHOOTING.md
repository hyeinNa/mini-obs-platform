# 트러블슈팅 기록 — mini-obs-platform

**작성일**: 2026-03-30
**환경**: macOS Darwin 24.6.0 / Rancher Desktop + KIND 1.29

---

## 이슈 1: KIND 노드 DNS 해석 실패

**증상**: KIND 노드에서 외부 레지스트리(registry.k8s.io, quay.io, ghcr.io) 이미지 Pull 실패. `ImagePullBackOff` 에러.
**원인**: Rancher Desktop VM의 내부 DNS(192.168.5.2)가 외부 도메인 해석에 불안정. KIND 노드가 이 DNS를 상속받아 이미지 레지스트리 접근 불가.
**해결**:
1. `/etc/resolv.conf`에 `nameserver 8.8.8.8`을 추가 (기존 192.168.5.2 유지)
   - 주의: 기존 DNS를 **대체하면 안 됨** — 대체 시 kubelet-to-API-server 통신이 끊어져 Worker 노드가 NotReady 됨
2. 호스트에서 이미지를 `docker pull`한 뒤 `kind load docker-image`로 노드에 로드
**교훈**: KIND + Rancher Desktop 조합에서는 `/etc/resolv.conf`를 교체가 아닌 **추가(append)** 방식으로 수정해야 함

---

## 이슈 2: ArgoCD imagePullPolicy: Always

**증상**: ArgoCD 매니페스트(install.yaml)로 설치한 파드들이 이미지가 노드에 있는데도 원격 Pull 시도 → DNS 문제와 결합되어 ImagePullBackOff.
**원인**: ArgoCD 공식 매니페스트의 기본 imagePullPolicy가 미지정 (→ :latest가 아닌 태그도 특정 조건에서 Always로 동작). KIND에서 `kind load`로 사전 로드한 이미지를 사용하려면 IfNotPresent 필요.
**해결**: ArgoCD 설치 직후 모든 Deployment/StatefulSet의 imagePullPolicy를 IfNotPresent로 패치:
```bash
for deploy in argocd-applicationset-controller argocd-dex-server argocd-notifications-controller argocd-redis argocd-repo-server argocd-server; do
  kubectl patch deployment $deploy -n argocd --type='json' \
    -p='[{"op":"replace","path":"/spec/template/spec/containers/0/imagePullPolicy","value":"IfNotPresent"}]'
  kubectl patch deployment $deploy -n argocd --type='json' \
    -p='[{"op":"replace","path":"/spec/template/spec/initContainers/0/imagePullPolicy","value":"IfNotPresent"}]'
done
kubectl patch statefulset argocd-application-controller -n argocd --type='json' \
  -p='[{"op":"replace","path":"/spec/template/spec/containers/0/imagePullPolicy","value":"IfNotPresent"}]'
```
**교훈**: KIND 환경에서 외부 매니페스트 설치 시 항상 imagePullPolicy를 확인할 것

---

## 이슈 3: 샘플 앱 imagePullPolicy: Always

**증상**: 3개 샘플 앱(frontend-svc, order-svc, inventory-svc)이 kind load된 이미지를 사용하지 못하고 Pending/ImagePullBackOff
**원인**: `infra/manifests/apps/*.yaml`에 `imagePullPolicy: Always`로 설정됨. ghcr.io 레지스트리에 실제 이미지가 없으므로 Pull 실패.
**해결**: 모든 샘플 앱 매니페스트의 imagePullPolicy를 `IfNotPresent`로 변경
**교훈**: KIND 로컬 개발 환경에서는 imagePullPolicy: IfNotPresent 또는 Never 사용 필수

---

## 이슈 4: Fluent Bit inotify "Too many open files"

**증상**: Fluent Bit DaemonSet 파드가 CrashLoopBackOff. 로그에 `[error] [/src/fluent-bit/plugins/in_tail/tail_fs_inotify.c:360 errno=24] Too many open files`
**원인**: KIND 노드의 inotify watch 제한이 낮아 `/var/log/containers/*.log`의 tail 플러그인이 초기화 실패
**해결**: Fluent Bit values.yaml의 INPUT 설정에 `Inotify_Watcher Off` 추가하여 polling 모드로 전환
**교훈**: KIND/리소스 제한 환경에서는 Fluent Bit의 Inotify를 비활성화하고 polling 사용

---

## 이슈 5: Jaeger Helm Chart image 값 형식 충돌

**증상**: Jaeger 파드가 `InvalidImageName`. 이미지명이 `map[repository:jaegertracing/all-in-one tag:1.55]:1.45.0`으로 잘못 렌더링
**원인**: jaegertracing/jaeger chart v0.71.14에서 `allInOne.image`가 문자열 타입인데, values.yaml에 map(repository/tag)으로 작성하여 병합 충돌
**해결**: values.yaml 수정: `image.repository` + `image.tag` → `image: jaegertracing/all-in-one` + `tag: "1.55"` (차트 스키마에 맞춤)
**교훈**: Helm chart values 작성 시 `helm show values <chart>`로 스키마를 확인할 것

---

## 이슈 6: OTel Collector Helm Chart 스키마 변경

**증상**: `Error: values don't meet the specifications of the schema(s): at '/service': additional properties 'ports' not allowed`
**원인**: opentelemetry-collector chart v0.87.0에서 `service.ports` 대신 최상위 `ports` 키 사용. 또한 `jaeger` exporter가 deprecated됨.
**해결**:
1. `service.ports` → 최상위 `ports` 구조로 변경
2. `jaeger` exporter → `otlp/jaeger` exporter로 변경 (OTLP 프로토콜 사용)
**교훈**: Helm chart 버전 업그레이드 시 breaking changes를 반드시 확인

---

## 이슈 7: Go 1.22 + OTel SDK 의존성 충돌

**증상**: frontend-svc Docker 빌드 시 `go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp@v0.67.0 requires go >= 1.25.0`
**원인**: Dockerfile에서 `golang:1.22-alpine` 사용 중 `go mod tidy`가 otelhttp를 최신 버전(v0.67.0)으로 resolve. go.sum이 placeholder여서 버전 고정 안 됨.
**해결**:
1. Dockerfile의 Go 이미지를 `golang:1.24-alpine`으로 업그레이드
2. placeholder go.sum 파일 삭제
**교훈**: go.sum이 없는 상태에서 go mod tidy는 최신 버전으로 resolve됨. Dockerfile에서 Go 버전과 의존성 호환성 확인 필수

---

## 이슈 8: Rancher Desktop 리소스 부족 (6GB/2CPU)

**증상**: Helm chart 설치 중 API 서버 TLS handshake timeout, kube-scheduler CrashLoopBackOff (leader lease 만료)
**원인**: 3노드 KIND 클러스터 + 전체 Observability 스택(Prometheus, Grafana, Loki, Fluent Bit, Jaeger, OTel Collector, Chaos Mesh, ArgoCD, 3개 샘플 앱)이 6GB RAM / 2 CPU로는 부족
**해결**: Rancher Desktop VM 리소스를 Memory 8GB+, CPU 4+로 증가
**교훈**:
- KIND + 전체 모니터링 스택은 최소 8GB RAM, 4 CPU 필요
- 리소스 제한 환경에서는 워커 노드 수를 줄이거나 컴포넌트를 선택적으로 설치

---

## 배포 전 체크리스트 (KIND + Rancher Desktop)

1. Rancher Desktop VM: Memory >= 8GB, CPU >= 4
2. 클러스터 생성 후 DNS 수정: `echo "nameserver 8.8.8.8" >> /etc/resolv.conf` (교체가 아닌 추가)
3. 필요한 이미지를 호스트에서 `docker pull` → `kind load docker-image`로 사전 로드
4. 외부 매니페스트(ArgoCD 등) 설치 후 imagePullPolicy를 IfNotPresent로 패치
5. 샘플 앱 매니페스트: imagePullPolicy: IfNotPresent 확인

---

## 이슈 9: Jaeger에서 Tempo로 전환이 미완성 상태로 방치 (2026-07-17 발견)

**증상**: 앱 트레이스가 백엔드에 도달하지 않음. OTel Collector 로그에 `otlp/jaeger` exporter가 존재하지 않는 `jaeger-collector.tracing` 서비스로 재시도하다 데이터 드랍.
**원인**: Jaeger를 Tempo로 교체하는 작업이 중간에 중단됨. (1) values 파일은 Tempo로 수정됐지만 클러스터의 Collector 릴리스에는 미적용, (2) `tempo` Helm 릴리스가 `pending-install` 상태로 정지, (3) `deploy-all.sh`는 여전히 Jaeger 설치.
**해결**: tempo 릴리스 uninstall 후 재설치(`grafana/tempo` 1.24.4), Collector를 Tempo exporter values로 upgrade, `deploy-all.sh`를 Tempo 기준으로 갱신.
**교훈**: 스택 교체는 values 수정, 릴리스 적용, 배포 스크립트, 문서까지 한 번에 완료하고 `helm list -A -a`로 릴리스 상태를 검증할 것.

## 이슈 10: Grafana Tempo 데이터소스 포트 오기입

**증상**: Grafana에서 Tempo 데이터소스 연결 실패.
**원인**: values의 Tempo URL이 `http://tempo.tracing:3100`으로 기입됨. 3100은 Loki 포트이고 Tempo HTTP API는 3200.
**해결**: `http://tempo.tracing:3200`으로 수정 후 kube-prometheus-stack upgrade.
**교훈**: 데이터소스 URL 복붙 시 포트 확인 (Loki 3100 / Tempo 3200 / Prometheus 9090).

## 이슈 11: 장기 방치 후 재기동 시 kube-proxy CrashLoop ("too many open files")

**증상**: VM 재시작 후 kube-proxy 3개 전부 CrashLoopBackOff, CoreDNS 0/1, 클러스터 서비스 통신 전면 장애.
**원인**: Rancher Desktop VM의 inotify 한도(fs.inotify.max_user_watches/instances)가 낮아 kube-proxy 초기화 실패. 이슈 4(Fluent Bit inotify)와 같은 뿌리.
**해결**: `rdctl shell sudo sysctl -w fs.inotify.max_user_watches=524288 fs.inotify.max_user_instances=512` 후 kube-proxy 파드 삭제(재생성).
**교훈**: KIND + Rancher Desktop 조합은 VM 커널 파라미터가 재시작 시 초기화될 수 있음. 클러스터 기동 전 sysctl 확인.

## 이슈 12: Fluent Bit imagePullPolicy 미지정으로 ImagePullBackOff

**증상**: 노드에 이미지가 있는데도 Fluent Bit DaemonSet이 ImagePullBackOff.
**원인**: 차트 기본 pullPolicy(Always)가 DNS 불안정과 결합. 이슈 2, 3과 동일 계열인데 Fluent Bit만 수정이 누락됐었음.
**해결**: values에 `image.pullPolicy: IfNotPresent` 명시.
