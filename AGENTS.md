# Repository Guidelines

AI 에이전트(Claude, Gemini, Codex 등)가 이 저장소에서 수행해야 할 역할과 규칙을 정의합니다.

---

## 📌 1. 프로젝트 목적

이 저장소는 **AI 개발 환경 통합 관리 도구**입니다.

* 대상: Claude Code, Gemini CLI, Codex, Antigravity
* 핵심: MCP 서버 토큰 중앙 관리 및 config 자동 생성

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
- Pydantic 모델로 설정 정의

### **2) CLI 규칙**
- Click 프레임워크 사용
- Rich로 출력 포맷팅
- 명령어 그룹화 (config, doctor, generate, pipeline, secrets, setup, status, sync)

### **3) 테스트**
- pytest 사용
- tests/ 디렉토리에 테스트 작성

---

## 📌 5. AI가 강조해야 할 핵심 기능

### **시크릿 관리**
- .env 파일 기반 환경변수 관리
- 마스킹된 출력으로 보안 유지
- keyring 연동 (선택)

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
* 시크릿을 git에 커밋하도록 유도
* 보안 설정을 약화시키는 변경

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
