# Backend Agent Lessons — mini-obs-platform

---

### 2026-03-28 | mini-obs-platform — sample app implementation

**에이전트**: db-agent

**문제 1: OTel SDK와 pytest 환경 충돌**
`setup_otel()`이 앱 모듈 임포트 시점에 실행되므로 pytest가 라이브 OTLP 엔드포인트 없이 실행되면 `grpc` 연결 오류가 발생한다.

**해결**: `conftest.py`에서 `sys.modules`에 no-op `otel_setup` 스텁을 주입하여 앱 모듈 임포트 전에 OTel 초기화를 차단. `setdefault`를 사용해 이미 임포트된 경우에는 덮어쓰지 않음.

**교훈**: FastAPI + OTel 조합은 모듈 임포트 시점에 SDK를 초기화하므로, 테스트 픽스처가 아닌 `conftest.py` 최상단에서 스텁을 주입해야 한다. 개별 테스트 파일마다 중복 스텁을 넣으면 임포트 순서 문제가 발생할 수 있다.

---

**문제 2: prometheus_client 전역 레지스트리와 테스트 격리**
`metrics.py`에서 `Counter`, `Histogram`, `Gauge`를 모듈 레벨에서 생성하면 동일 pytest 세션에서 앱을 여러 번 임포트 시 "Duplicated timeseries" 오류가 발생할 수 있다.

**해결**: 현재 구현에서는 `metrics.py`가 단순히 전역 인스턴스를 한 번만 생성하므로 단일 pytest 프로세스에서는 문제없음. 만약 테스트 간 레지스트리 초기화가 필요하면 `prometheus_client.REGISTRY.unregister()` 또는 `CollectorRegistry(auto_describe=False)` 격리 레지스트리를 사용할 것.

**교훈**: Prometheus 메트릭 객체는 모듈 수준 싱글턴으로 구현하되, 테스트에서 `generate_latest()` 텍스트 검증만 하면 레지스트리 충돌 없이 안전하게 테스트 가능.

---

**문제 3: Go `semconv` 패키지 버전 참조**
`go.opentelemetry.io/otel/semconv/v1.26.0`은 `go.opentelemetry.io/otel` 모듈의 서브패키지로, `go.mod`에 별도 `require` 항목이 필요 없다. 잘못된 버전 지정 시 `go mod tidy`가 오류를 냄.

**해결**: `semconv/v1.24.0` 경로로 수정하여 otel v1.27.0에 포함된 버전 사용. `go.mod`에서 별도 require 없이 상위 모듈 버전에 포함됨.

**교훈**: Go의 OTel semconv 패키지는 상위 `go.opentelemetry.io/otel` 모듈에 포함된 서브디렉토리다. 버전 번호는 임포트 경로에 포함되지만(`semconv/v1.24.0`) `go.mod`에 별도로 선언하지 않는다.

---

**문제 4: Go 환경 없이 go.sum 생성 불가**
로컬 환경에 Go가 설치되지 않아 `go mod tidy`를 실행할 수 없어 `go.sum`을 자동 생성할 수 없었다.

**해결**: Dockerfile의 builder 스테이지에서 `go mod tidy`를 실행하도록 구성. `go.sum`에 플레이스홀더 파일을 커밋하고 Docker 빌드 시 실제 해시값이 채워지는 구조.

**교훈**: Go 프로젝트의 `go.sum`은 `go mod tidy` 실행 환경(로컬 또는 CI Docker 빌드)이 보장되어야 한다. 로컬 Go 설치가 없는 에이전트 환경에서는 Dockerfile 빌드가 소스 of truth가 된다. `go.sum` 플레이스홀더 파일과 Dockerfile의 `go mod tidy` 조합으로 해결.

---

**문제 5: Observability 프로젝트에서 인메모리 저장소 테스트 격리**
`_orders`(order-svc), `_inventory`(inventory-svc) 딕셔너리가 모듈 전역 변수여서 테스트 간에 상태가 공유된다.

**해결**: `autouse=True` pytest fixture에서 각 테스트 전/후에 저장소를 `clear()`하고 초기 시드값을 복원.

**교훈**: 인메모리 저장소는 MVP의 단순성을 위해 적합하지만, 테스트 격리를 위해 `autouse=True` fixture에서 반드시 초기화해야 한다. DB 기반 프로젝트의 트랜잭션 롤백과 같은 역할.

---

**문제 6: httpx.AsyncClient 컨텍스트 매니저 모킹**
`async with httpx.AsyncClient() as client:` 패턴을 `unittest.mock.patch`로 모킹할 때 `__aenter__`와 `__aexit__`를 명시적으로 `AsyncMock`으로 설정해야 한다.

**해결**:
```python
mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
mock_instance.__aexit__ = AsyncMock(return_value=None)
mock_instance.put = AsyncMock(return_value=httpx.Response(200, json={...}))
```

**교훈**: `AsyncMock`으로 클래스를 패치할 때 `__aenter__`/`__aexit__` 설정이 필수. `AsyncMock()` 자체는 비동기 컨텍스트 매니저 프로토콜을 자동으로 지원하지 않는다. `httpx.Response` 생성자는 `status_code`와 `json=` 키워드를 받는다.
