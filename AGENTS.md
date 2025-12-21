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
- README.md, CLAUDE.md, GEMINI.md 업데이트
- 사용법 및 예제 추가

---

## 📌 3. 저장소 구조

### **src/ai_env/**
- `cli.py`: Click 기반 CLI 엔트리포인트
- `core/config.py`: 설정 로더
- `core/secrets.py`: 시크릿 관리
- `mcp/generator.py`: MCP config 생성기

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
- 명령어 그룹화 (secrets, config, generate, sync)

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

## 📌 6. AI가 해야 하는 것

* 코드 품질 유지 (type hints, docstrings)
* 설정 변경 시 영향 범위 설명
* 보안 관련 주의사항 안내
* 테스트 코드 함께 작성

## 📌 7. AI가 하면 안 되는 것

* .env 파일의 실제 토큰값을 출력하거나 로깅
* 시크릿을 git에 커밋하도록 유도
* 보안 설정을 약화시키는 변경

---

## 📌 8. 주요 명령어

```bash
# 개발 환경 설정
uv sync

# CLI 실행
uv run ai-env --help
uv run ai-env status
uv run ai-env secrets list
uv run ai-env sync

# 테스트
uv run pytest

# 린트
uv run ruff check .
uv run mypy src/
```
