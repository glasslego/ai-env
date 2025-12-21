---
name: wiki-manager
description: |
  카카오 온프레미스 Confluence 위키 관리 스킬.
  페이지 읽기/쓰기/수정, 검색, 하위 페이지 탐색 지원.

  주요 기능:
  - 페이지 CRUD (읽기/생성/수정/삭제)
  - CQL 검색 및 하위/상위 페이지 탐색
  - Markdown ↔ Storage 형식 변환
  - Dry-run 모드로 안전한 미리보기
  - 라벨, 댓글, 첨부파일 관리
  - 버전 히스토리 조회
  - 페이지 복사/이동
  - 공간 정보 조회

  대표 공간:
  - KCAI: 우리팀. 커머스 추천팀
  - developerguide: Kakao DevGuide. 카카오 전사 개발 가이드 및 API 연동 문서
---

# wiki-manager

카카오 온프레미스 Confluence 위키(https://wiki.daumkakao.com) 관리 스킬.

## 환경 설정

`.env` 파일에 다음 환경변수 필요:
```
WIKI_BASE_URL=https://wiki.daumkakao.com
WIKI_TOKEN=your_personal_access_token
```

Personal Access Token: 위키 사용자 설정 > 개인 액세스 토큰에서 발급.

## CLI 공통

```bash
CLI=".claude/skills/wiki-manager/scripts/wiki_client.py"
uv run python $CLI <command> [options]
```

모든 쓰기 명령에 `--dry-run` 옵션으로 미리보기 가능.

## 대표 공간

| 공간 키 | 설명 |
|---------|------|
| `KCAI` | 커머스추천팀 (홈: 815966617) |
| `developerguide` | Kakao DevGuide |
| `CommerceDataEngineeringTeam` | CDE 팀 |

---

## 워크플로우

### 1. 페이지 읽기

```bash
# Markdown 형식
uv run python $CLI read --page-id {ID} --format markdown

# URL로 직접 조회
uv run python $CLI read --url "{URL}" --format markdown

# URL에서 페이지 ID 추출
uv run python $CLI parse-url "{URL}"
```

### 2. 페이지 검색

```bash
# CQL 검색 (특정 공간)
uv run python $CLI cql 'space = KCAI and title ~ "검색어"'

# 본문 검색
uv run python $CLI cql 'text ~ "검색어"'

# 하위 페이지 목록
uv run python $CLI children --page-id {PARENT_ID}

# 상위 페이지 경로 (breadcrumb)
uv run python $CLI ancestors --page-id {PAGE_ID}
```

> `space = KCAI` 조건은 사용자가 우리팀을 명시할 때만 추가.

### 3. 페이지 생성

> 공간 미지정 시 **KCAI**. **반드시 parent-id 지정** (미지정 시 루트에 생성되어 찾기 어려움).

```bash
# Dry-run 미리보기
uv run python $CLI --dry-run create --space KCAI --title "제목" --parent-id {ID}

# 실제 생성
uv run python $CLI create --space KCAI --title "제목" --parent-id {ID} --body-file content.md
```

### 4. 페이지 수정

```bash
# 현재 내용 조회 → 수정 → dry-run → 실제 수정
uv run python $CLI read --page-id {ID} --format markdown
uv run python $CLI --dry-run update --page-id {ID} --body-file updated.md
uv run python $CLI update --page-id {ID} --body-file updated.md
```

### 5. 페이지 삭제

삭제 전 반드시 사용자에게 확인 (제목, 버전, 하위 페이지 존재 여부).

```bash
uv run python $CLI --dry-run delete --page-id {ID}
uv run python $CLI delete --page-id {ID}
```

---

## CLI 명령어 전체 목록

| 명령 | 설명 |
|------|------|
| `read --page-id ID [--format markdown\|json]` | 페이지 읽기 |
| `read --url URL` | URL로 페이지 읽기 |
| `cql 'QUERY'` | CQL 검색 |
| `search --space KEY --title TITLE` | 제목 검색 |
| `children --page-id ID` | 하위 페이지 |
| `ancestors --page-id ID` | 상위 페이지 경로 |
| `create --space KEY --title TITLE --parent-id ID` | 생성 |
| `update --page-id ID --body-file FILE` | 수정 |
| `delete --page-id ID` | 삭제 |
| `parse-url URL` | URL → 페이지 ID |
| `labels --page-id ID` | 라벨 조회 |
| `add-label --page-id ID --label NAME` | 라벨 추가 |
| `remove-label --page-id ID --label NAME` | 라벨 삭제 |
| `history --page-id ID [--limit N]` | 버전 히스토리 |
| `version --page-id ID --version N` | 특정 버전 조회 |
| `attachments --page-id ID` | 첨부파일 목록 |
| `upload --page-id ID --file PATH` | 파일 업로드 |
| `download --page-id ID --attachment-id AID --output PATH` | 파일 다운로드 |
| `comments --page-id ID` | 댓글 목록 |
| `add-comment --page-id ID --body TEXT` | 댓글 추가 |
| `copy --page-id ID --dest-page-id DEST_ID [--title T]` | 복사 |
| `move --page-id ID --target-page-id TARGET_ID` | 이동 |
| `space SPACE_KEY` | 공간 정보 |
| `watchers --page-id ID` | 워처 목록 |

---

## PlantUML 다이어그램

Markdown에서 ` ```plantuml ` 코드 블록 사용 시 자동으로 Confluence PlantUML 매크로로 변환.
역변환도 지원 (read --format markdown 시 자동 복원).

지원 유형: 시퀀스, 클래스, 컴포넌트, 액티비티, 마인드맵, JSON/YAML 시각화.

## 참고 자료

- `references/api-notes.md` - API 특이사항
- `references/space-structure.md` - 위키 구조
