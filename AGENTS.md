# Repository Guidelines

AI 에이전트(Claude, Gemini, Codex 등)가 이 저장소에서 수행해야 할 역할과 규칙을 정의합니다.

---

## 📌 1. 프로젝트 목적

이 저장소는 **AI 개발 환경 통합 관리 도구**입니다.

* 대상: Claude Code, Gemini CLI, Codex, Antigravity
* 핵심: MCP 서버 토큰 중앙 관리 및 config 자동 생성

---

## 📌 1-1. 공용 에이전트 가이드라인 운영 (Spec-Task-Test-Commit)

전체 에이전트 공용 기준의 단일 원본(SSOT)은 아래 파일이다.

- `ai-env/.claude/global/CLAUDE.md`

이 파일은 `ai-env sync`로 각 에이전트 글로벌 설정으로 배포된다.

- Claude Code: `~/.claude/CLAUDE.md`
- Codex CLI: `~/.codex/AGENTS.md`
- Gemini CLI: `~/.gemini/GEMINI.md`

공용 필수 규칙:
- Spec 기준으로 Task를 먼저 확정한다.
- Task 단위로만 구현한다.
- 테스트 통과 후에만 커밋한다.
- 커밋 단위는 Spec의 Task 완료 단위로 유지한다.
- 커밋 메시지에 `spec/task` 식별자를 포함한다.

운영 명령:
```bash
uv run ai-env sync --claude-only
```

---

## 📌 2. 에이전트의 핵심 임무

### ① 환경설정 관리 지원
- .env 파일의 시크릿 관리
- config/*.yaml 설정 파일 수정
- MCP 서버 추가/수정/삭제

### ② CLI 개발 지원
- src/ai_env/ 하위 Python 코드 개발
- Click CLI 명령어 추가
- 테스트 코드 작성

### ③ 문서화
- README.md, CLAUDE.md, AGENTS.md 업데이트
- 사용법 및 예제 추가

---

## 📌 3. 저장소 구조

### **src/ai_env/**
- `cli/`: Click 기반 CLI 패키지 (doctor, generate, pipeline, status, sync 명령어)
- `core/config.py`: Pydantic 모델, YAML 설정 로드
- `core/secrets.py`: `.env` 환경변수 관리, `${VAR}` 치환
- `core/sync.py`: 글로벌 설정 동기화 (Claude, Codex, Gemini)
- `core/doctor.py`: 환경 건강 검사
- `core/pipeline.py`: 토픽 YAML 모델, 리서치 파이프라인 유틸
- `core/research.py`: Deep Research API 디스패치 (Gemini/OpenAI)
- `core/workflow.py`: 6-Phase 워크플로우 스캐폴딩
- `mcp/generator.py`: 타겟별 MCP 설정 생성 (stdio/SSE)
- `mcp/vibe.py`: Agent Fallback 셸 함수 생성

### **config/**
- `settings.yaml`: 메인 설정
- `mcp_servers.yaml`: MCP 서버 정의

### **.env**
- 🔐 마스터 시크릿 파일 (gitignore)

### **generated/**
- 자동 생성된 config 파일들 (gitignore)

---

## 📌 4. 코드 작성 규칙

### **1) Python 스타일**
- Python 3.11+ 문법 사용
- Type hints 필수
- Google style docstrings
- Pydantic 모델로 설정/스키마 정의 (orjson/msgspec은 성능 우선 직렬화용)
- loguru 로깅 (backtrace + rotation 기본 설정)

### **2) CLI 규칙**
- Click 프레임워크 사용
- Rich로 출력 포맷팅 (`console.print()` 사용, `print()` 금지)
- 명령어 그룹화 (config, doctor, generate, pipeline, secrets, setup, status, sync)

### **3) pre-commit + ruff**
- 프로젝트 루트에 `.pre-commit-config.yaml` 필수
- ruff 자동 수정 hook: `ruff check --fix` + `ruff format`
- gitleaks hook 권장 (시크릿 유출 방지)
- 새 프로젝트 시작 시 `pre-commit install` 반드시 실행

### **4) 테스트**
- pytest 사용
- tests/ 디렉토리에 테스트 작성

### **5) PySpark 컨벤션**
- `from pyspark.sql import functions as F` (항상 F alias)
- UDF 사용 전 네이티브 함수로 가능한지 반드시 확인
- DataFrame API 우선, SparkSQL은 복잡한 윈도우 함수에서만
- `.cache()` 사용 시 반드시 `.unpersist()` 쌍으로
- 셔플 파티션 수는 데이터 규모에 맞게 조정

---

## 📌 5. AI가 강조해야 할 핵심 기능

### **시크릿/환경변수**
- 하드코딩 절대 금지. 환경변수 또는 `.env` 파일 사용
- `.env`는 `.gitignore`에 반드시 포함
- 시크릿이 필요한 작업은 사용자에게 확인 후 진행
- 마스킹된 출력으로 보안 유지

### **MCP Config 생성**
- Claude Desktop용 JSON 생성
- Antigravity용 JSON 생성
- Codex용 TOML 생성
- Gemini용 JSON 생성

### **동기화**
- 단일 명령으로 모든 대상에 config 배포
- dry-run 모드로 변경사항 미리보기

---

## 📌 6. Autonomy (No confirmation prompts)

- "이어서 진행할까요?", "진행해도 될까요?", "계속할까요?" 같은 확인 질문을 하지 말고 자동으로 계속 진행한다.
- 대화 턴 마무리 확인 질문(예: "다음을 이어서 진행할까요?")을 금지한다.
- Codex 사용 시 명령 승인(approval)과 대화형 질문을 분리해서 처리하고, 승인 이슈가 없으면 계속 실행한다.
- non-interactive 실행이 가능한 작업은 `codex exec -c "approval_policy='never'" -s workspace-write "<task>"`를 우선 사용한다.
- 멈추는 경우는 딱 3가지뿐:
  1) 파괴적/되돌리기 어려운 작업(데이터 삭제 등)
  2) 자격증명/비밀키가 필요한 작업
  3) 스펙이 없어 결과가 크게 달라지는 치명적 불확실성
- 그 외는 합리적 가정으로 진행하고, 마지막에 Assumptions/TODO로 정리한다.

---

## 📌 7. AI가 해야 하는 것

* 코드 품질 유지 (type hints, docstrings)
* 설정 변경 시 영향 범위 설명
* 보안 관련 주의사항 안내
* 테스트 코드 함께 작성

## 📌 8. AI가 하면 안 되는 것

* .env 파일의 실제 토큰값을 출력하거나 로깅
* 시크릿을 git에 커밋하도록 유도 (`.env`, `*.pem`, `credentials*.json`)
* 보안 설정을 약화시키는 변경
* 라이브러리 버전 임의 변경, 구조 자체 변경 (unless explicitly asked)
* 테스트 통과를 위해 테스트 코드 삭제/기준 완화

---

## 📌 9. 주요 명령어

```bash
# 개발 환경 설정
uv sync

# CLI 실행
uv run ai-env --help
uv run ai-env status
uv run ai-env secrets
uv run ai-env sync
uv run ai-env doctor
uv run ai-env pipeline --help

# 테스트
uv run pytest

# 린트·포맷
uv run ruff check . && uv run ruff format .
uv run mypy src/
```
