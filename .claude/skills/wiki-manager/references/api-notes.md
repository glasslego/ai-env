# Confluence API 특이사항

카카오 온프레미스 Confluence (https://wiki.daumkakao.com) 사용 시 발견된 특이사항들을 기록합니다.

## 버전 정보
- Confluence Data Center 9.2.3

## 인증
- **방식**: Personal Access Token (Bearer)
- **헤더**: `Authorization: Bearer {token}`
- 토큰 발급: 사용자 설정 > 개인 액세스 토큰

## URL 접근 패턴

### 페이지 ID만으로 접근
- `viewpage.action?pageId={id}` 형식은 **정상 동작**
  - 예: `https://wiki.daumkakao.com/pages/viewpage.action?pageId=815966617`
- REST API는 페이지 ID만으로 조회 가능
  - `GET /rest/api/content/{pageId}`

### 전체 경로 URL
- 전체 경로 형식: `/spaces/{SPACE}/pages/{pageId}/{title}`
  - 예: `https://wiki.daumkakao.com/spaces/KCAI/pages/815966617/카카오+커머스추천팀+Home`

## 검색 API

### title 파라미터 (정확 일치)
- `GET /rest/api/content?spaceKey=KCAI&title=정확한+제목`
- 정확히 일치하는 제목만 검색됨
- 부분 매칭 불가

### CQL 검색 (유연한 검색)
- `GET /rest/api/content/search?cql={query}`
- 부분 매칭 가능: `title ~ "검색어"`
- 예시:
  ```
  space = KCAI and title ~ "Products"
  space = KCAI and text ~ "추천"
  parent = 815966617
  ```

## 페이지 수정 시 주의사항

### 버전 번호 필수
- `PUT /rest/api/content/{id}` 호출 시 버전 번호 필수
- 현재 버전 + 1 로 설정해야 함
- 버전 충돌 시 409 Conflict 에러

### Storage Format
- 페이지 본문은 XHTML 기반 storage format 사용
- Markdown을 직접 저장할 수 없음
- 변환 필요: Markdown → HTML → Storage

## 페이지네이션

### scan 엔드포인트 (Confluence 7.18+)
- `GET /rest/api/content/scan?spaceKey={key}&limit={n}`
- cursor 기반 페이지네이션
- 대량 페이지 스캔에 최적화

### 일반 목록
- start/limit 파라미터 사용
- `_links.next` 로 다음 페이지 확인

## 알려진 제한사항

1. **첨부파일 크기 제한**: 서버 설정에 따름
2. **Rate Limiting**: 사내 정책에 따름 (명시적 제한 미확인)
3. **대용량 페이지**: storage format 변환 시 시간 소요 가능

## 테스트 완료 기능

### 기본 기능

| 기능 | 상태 | 비고 |
|------|------|------|
| 페이지 읽기 | ✅ | ID, URL 모두 지원 |
| 페이지 생성 | ✅ | dry-run 및 실제 생성 테스트 완료 |
| 페이지 수정 | ✅ | dry-run 및 실제 수정 테스트 완료 |
| 페이지 삭제 | ✅ | dry-run 및 실제 삭제 테스트 완료 |
| 하위 페이지 조회 | ✅ | 정상 동작 |
| 상위 페이지 조회 | ✅ | ancestors breadcrumb |
| CQL 검색 | ✅ | 정상 동작 |
| Markdown 변환 | ✅ | html2text, mistune 사용 |

### 확장 기능 (2차)

| 기능 | 상태 | 비고 |
|------|------|------|
| 라벨 조회 | ✅ | 빈 라벨 시 "No labels" 출력 |
| 라벨 추가/삭제 | ✅ | dry-run 지원 |
| 버전 히스토리 | ✅ | 생성일, 수정자, 버전 목록 |
| 특정 버전 조회 | ✅ | Markdown 변환 지원 |
| 첨부파일 목록 | ✅ | 파일명, 크기, 타입 표시 |
| 첨부파일 업로드 | ✅ | dry-run 지원 |
| 첨부파일 다운로드 | ✅ | 바이너리 저장 |
| 댓글 조회 | ✅ | 작성자, 날짜, 내용 |
| 댓글 추가 | ✅ | dry-run 지원 |
| 페이지 복사 | ✅ | dry-run 지원, 첨부파일 포함 옵션 |
| 페이지 이동 | ✅ | dry-run 지원 |
| 공간 정보 | ✅ | 홈페이지 ID 포함 |
| 워처 목록 | ✅ | 사용자명 표시 |

## 추가 API 엔드포인트

| 기능 | 엔드포인트 |
|------|------------|
| 라벨 조회 | `GET /rest/api/content/{id}/label` |
| 라벨 추가 | `POST /rest/api/content/{id}/label` |
| 라벨 삭제 | `DELETE /rest/api/content/{id}/label/{label}` |
| 버전 히스토리 | `GET /rest/api/content/{id}/history` |
| 특정 버전 | `GET /rest/api/content/{id}?status=historical&version={n}` |
| 첨부파일 목록 | `GET /rest/api/content/{id}/child/attachment` |
| 첨부파일 업로드 | `POST /rest/api/content/{id}/child/attachment` (multipart) |
| 첨부파일 다운로드 | `GET /rest/api/content/{id}/child/attachment/{aid}/download` |
| 댓글 조회 | `GET /rest/api/content/{id}/child/comment?expand=body.storage` |
| 댓글 추가 | `POST /rest/api/content` (type=comment, container=page) |
| 페이지 복사 | `POST /rest/api/content/{id}/copy` |
| 페이지 이동 | `PUT /rest/api/content/{id}/move/{position}/{targetId}` |
| 공간 정보 | `GET /rest/api/space/{key}?expand=homepage` |
| 워처 목록 | `GET /rest/api/user/watch/content/{id}` |
