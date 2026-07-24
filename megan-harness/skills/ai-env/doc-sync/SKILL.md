---
name: doc-sync
description: |
  프로젝트 문서와 코드의 정합성을 검증하고 동기화하는 스킬.
  "문서 동기화", "doc sync", "docs 업데이트", "문서 정합성" 등의 요청에 반응.
  CLAUDE.md, AGENTS.md, README.md, SERVICES.md, SETUP.md, specs/ 등
  프로젝트 문서가 실제 코드/구조와 일치하는지 검증하고 수정한다.
---

# doc-sync

프로젝트 문서 ↔ 코드 정합성 검증 및 동기화 스킬.

## 트리거

"문서 동기화", "doc sync", "docs update", "문서 정합성 검증" 등.

## 검증 대상

| 문서 | 검증 항목 |
|------|----------|
| `CLAUDE.md` | 프로젝트 구조, 모듈 목록, 아키텍처 다이어그램 |
| `AGENTS.md` | 저장소 구조, 코드 작성 규칙 |
| `README.md` | CLI 명령어, 동기화 대상, 빠른 시작 |
| `SERVICES.md` | MCP 서버 목록, 환경변수명 |
| `SETUP.md` | 환경변수명, 생성 파일 경로 |
| `specs/` | Spec 문서 내 경로 참조, 구현 위치 |
| `.claude/README.md` | 디렉토리 구조, 스킬/커맨드 목록 |

## Workflow

### Step 1: 현재 상태 수집 (Truth Source)

코드에서 실제 정보를 추출한다:

1. **프로젝트 구조**: `ls` + `find`로 실제 디렉토리 트리
2. **모듈 목록**: `src/ai_env/` 하위 `.py` 파일 스캔
3. **CLI 명령어**: `uv run ai-env --help` 출력 파싱
4. **MCP 서버**: `config/mcp_servers.yaml` 파싱
5. **환경변수**: `.env.example` 또는 `config/mcp_servers.yaml`의 `env_keys` 수집
6. **스킬 목록**: `.claude/skills/*/SKILL.md` frontmatter 스캔
7. **커맨드 목록**: `.claude/commands/*.md` 스캔
8. **Spec 목록**: `specs/SPEC-*.md` frontmatter 스캔

### Step 2: 문서별 Diff 생성

각 문서를 읽고, Step 1의 truth source와 비교하여 불일치 항목을 목록화한다.

출력 형식:
```
## Doc Sync Report

### CLAUDE.md
- [MISMATCH] 프로젝트 구조: .claude/hooks/ 누락
- [OUTDATED] 모듈 목록: core/workflow.py 미기재
- [OK] 환경변수 치환 설명

### SERVICES.md
- [MISMATCH] 환경변수: JIRA_PERSONAL_TOKEN → JIRA_TOKEN
- [OK] MCP 서버 목록
```

### Step 3: 수정 적용

사용자에게 diff 보고서를 보여준 뒤, 확인을 받고 수정을 적용한다.

수정 원칙:
- **코드가 Truth**: 문서를 코드에 맞춘다 (코드를 문서에 맞추지 않음)
- **최소 변경**: 불일치 부분만 수정, 스타일/구조 리팩터링 금지
- **SSOT 존중**: `.claude/global/CLAUDE.md`가 에이전트 가이드라인의 원본. 프로젝트 `CLAUDE.md`는 프로젝트 고유 정보만

## 자주 발생하는 불일치 패턴

1. **경로 변경**: 디렉토리 이동/삭제 후 문서에 옛 경로 잔존
2. **환경변수명 변경**: MCP 서버 env_keys 변경 후 SETUP.md/SERVICES.md 미갱신
3. **모듈 추가/삭제**: 새 모듈 추가 후 CLAUDE.md 모듈 테이블 미갱신
4. **스킬/커맨드 추가**: 새 스킬 추가 후 .claude/README.md 미갱신
5. **CLI 명령어 변경**: 새 서브커맨드 추가 후 README.md 미갱신

## pre-push 자동 검증

`scripts/doc_sync_check.py`가 pre-push hook으로 등록되어 있다.
push 전에 아래 항목을 자동 검증하고, 불일치 시 push를 차단한다:

| 검증 | 대상 |
|------|------|
| MCP 서버 목록 | SERVICES.md ↔ mcp_servers.yaml |
| 핵심 모듈 테이블 | CLAUDE.md ↔ src/ai_env/ 실제 모듈 |
| 환경변수 목록 | SETUP.md ↔ mcp_servers.yaml env_keys |
| 프로젝트 구조 | CLAUDE.md ↔ 실제 디렉토리 |
| 스킬 무결성 | .claude/skills/*/SKILL.md 존재 여부 |

차단 시 `/doc-sync`를 실행하여 문서를 업데이트한 뒤 다시 push한다.
긴급 시 `git push --no-verify`로 우회 가능 (비권장).

## 절대 금지

- SSOT인 `.claude/global/CLAUDE.md`를 프로젝트 `CLAUDE.md` 기준으로 수정하지 마라
- 코드를 문서에 맞추지 마라 (문서를 코드에 맞춰라)
- 문서 전체를 재작성하지 마라 (불일치 부분만 수정)
