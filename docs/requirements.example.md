# 프로젝트 요구사항

> 이 파일을 복사해서 `docs/requirements.md`로 저장한 뒤 내용을 채우세요.
> 에이전트들이 이 파일을 읽고 설계 → 구현 → QA를 자동으로 진행합니다.

---

## 1. 서비스 개요

**서비스명**: [서비스 이름]
**한 줄 설명**: [이 서비스가 무엇인지 한 문장으로]
**목적**: [왜 이 서비스를 만드는지]

---

## 2. 기술 스택

| 레이어 | 기술 | 비고 |
|--------|------|------|
| Frontend | Next.js 15 (App Router) + TailwindCSS + TypeScript | 또는 다른 프레임워크로 변경 가능 |
| Backend | Python 3.11+ + Django 5.2 + Django REST Framework | 또는 FastAPI, Express 등 |
| Database | PostgreSQL 15+ | 또는 MySQL, SQLite |
| 패키지 관리 | uv (backend), npm (frontend) | CLAUDE.md PY-2 규칙 참조 |

---

## 3. 환경 설정

```
Backend:  http://localhost:8000
Frontend: http://localhost:3000
DB:       [DB명] (localhost:5432)
```

---

## 4. 데이터 모델

### [모델명 예: User, Product, Post ...]

| 필드명 | 타입 | 제약 | 설명 |
|--------|------|------|------|
| id | UUID | PK, auto | 고유 식별자 |
| [필드명] | [타입] | [제약조건] | [설명] |
| created_at | DateTime | auto | 생성일시 |
| updated_at | DateTime | auto | 수정일시 |

또는 JSON 형식으로 정의할 수 있습니다:

```json
{
  "entities": [
    {
      "name": "모델명",
      "fields": [
        { "name": "id", "type": "uuid", "primary_key": true },
        { "name": "title", "type": "string", "max_length": 200, "required": true },
        { "name": "created_at", "type": "datetime", "auto": true }
      ]
    }
  ],
  "relations": [
    { "from": "Post", "to": "User", "type": "many_to_one", "field": "author" }
  ]
}
```

---

## 5. API 엔드포인트

```
GET    /api/[리소스]/           # 목록 조회
POST   /api/[리소스]/           # 생성
GET    /api/[리소스]/{id}/      # 단일 조회
PUT    /api/[리소스]/{id}/      # 전체 수정
PATCH  /api/[리소스]/{id}/      # 부분 수정
DELETE /api/[리소스]/{id}/      # 삭제
```

---

## 6. 서비스 플로우

> 사용자의 핵심 시나리오를 순서대로 기술하세요.
> design-agent가 이 내용을 기반으로 mermaid 다이어그램을 자동 생성합니다.

### 주요 시나리오

**시나리오 1: [시나리오명 예: 상품 주문]**
1. 사용자가 [행동 1]
2. 시스템이 [처리 1]
3. 사용자가 [행동 2]
4. 시스템이 [처리 2]
5. 결과: [최종 상태]

**시나리오 2: [시나리오명]**
1. ...

### 비즈니스 규칙 (있을 경우)

- [규칙 1 - 예: 재고가 0이면 주문 불가]
- [규칙 2 - 예: 하루 최대 5건까지 생성 가능]

---

## 7. 프론트엔드 기능

- [ ] [기능 1 - 예: 목록 조회 페이지]
- [ ] [기능 2 - 예: 생성 폼]
- [ ] [기능 3 - 예: 수정/삭제]
- [ ] [기능 4 - 예: 필터/검색]

---

## 8. 비기능 요구사항

- [ ] CORS 설정 (백엔드 ↔ 프론트엔드)
- [ ] 환경변수 분리 (.env 파일)
- [ ] 입력값 유효성 검사 (백엔드 + 프론트엔드)
- [ ] 에러 처리 및 사용자 피드백

---

## 9. 제외 범위 (Out of Scope)

> 이번 버전에서는 구현하지 않는 기능을 명시합니다.

- [ ] 사용자 인증/권한 (JWT, OAuth)
- [ ] 파일 업로드
- [ ] 실시간 기능 (WebSocket)
- [ ] [기타 제외 항목]
