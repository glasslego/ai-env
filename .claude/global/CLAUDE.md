# System-wide Claude Code Configuration
# ai-env/.claude/global/CLAUDE.md
# 이 파일을 ~/.claude/CLAUDE.md로 동기화하여 모든 프로젝트에 적용

## The Golden Rule
When unsure about implementation details, ALWAYS ask the developer.
불확실한 구현 세부사항이 있으면 반드시 사용자에게 확인하라.

---

## 🚫 절대 금지 사항 (Never Do)

### 패키지/버전 관리
- 문제 해결을 위해 라이브러리 버전을 임의로 변경하지 마라
- pip 대신 **uv**를 사용하라 (pip install → uv add)
- 작업 전 항상 가상환경 활성화: `source .venv/bin/activate`

### 테스트 코드 관련
- 테스트를 통과시키기 위해 테스트 코드 자체를 삭제/수정하지 마라
- 점수/기준점을 낮추어 테스트를 통과시키지 마라
- 테스트 코드와 구현 코드는 분리하여 접근하라

### 데이터/API 관련
- API 이름과 파라미터를 자의적으로 바꾸지 마라
- 자의적으로 데이터를 마이그레이션하지 마라
- LLM 모델 버전을 임의로 변경하지 마라

### 코드 변경 범위
- 시킨 것만 고쳐라 (Only fix what I asked)
- 지금 내가 지시한 것과 상관 없는 것은 바꾸지 마라
- 구조 자체를 바꾸지 마라 (unless explicitly asked)
- 가능한 간단한 솔루션을 따르라 (KISS principle)

---

## ✅ 항상 해야 할 것 (Always Do)

### 코드 작성 전
- 중복된 함수가 있는지 철저히 확인하라
- 기존 유틸리티 함수를 먼저 찾아보라
- 없다고 판단하면 정말 없는지 다시 확인하라

### Python 개발
- uv 패키지 매니저 사용
- pytest로 테스트 작성
- Type hints 필수
- Google style docstrings
- pre-commit 검증

### 파일/네이밍
- 파일 이름은 설명적으로 길게 (예: user_identity_check.py)
- 주석과 docstring을 풍부하게 (AI RAG 검색에 도움)

### 환경 구분
- dev, staging, prod 환경을 명확히 구분하라
- 환경별 설정을 혼동하지 마라

---

## 🔧 기술 스택 기본 설정

### Python
```
- Version: 3.11+
- Package manager: uv (NOT pip)
- Test framework: pytest
- Linting: ruff, black, isort
- Type checking: mypy
```

### 자주 쓰는 라이브러리 (권장)
```python
# JSON: orjson 또는 msgspec (기본 json 대신)
import orjson  # indent 없이 사용

# Logging: loguru
from loguru import logger

# 캐싱: diskcache
from diskcache import Cache

# SQL ORM: SQLAlchemy 2.0
from sqlalchemy import select

# DataFrame 출력: tabulate + CJK wide char
pd.set_option('display.unicode.east_asian_width', True)
```

### Spark
```python
from pyspark.sql import functions as F  # 항상 F로 alias
```

---

## 📁 프로젝트별 CLAUDE.md

각 프로젝트 루트에 CLAUDE.md를 생성하여 프로젝트별 규칙 추가.
`/init` 명령으로 기본 생성 후 커스터마이즈.

---

## 🔄 Commit과 CLAUDE.md 연동

`/commit` 시 자동으로:
1. git commit 메시지 생성
2. 변경사항에 맞춰 CLAUDE.md 업데이트 (필요시)

---

## 🌐 MCP 서버 사용

### 사용 가능한 MCP
- **jira-wiki-mcp**: Jira 이슈/Confluence 페이지 조회
- **github**: GitHub Enterprise 연동
- **playwright**: 브라우저 자동화/프론트엔드 테스트
- **kkoto-mcp**: Kakao 내부 서비스
- **cdp-mcp-server**: CDP 데이터 접근

### MCP 승인 팁
특정 MCP의 모든 기능을 영구 승인하려면 settings.json에서 이름만 추가:
```json
"permissions": {
  "allow": ["mcp__jira-wiki-mcp"]
}
```

---

## 🛠️ 문제 해결 패턴

### 증상만 해결하려 하지 마라
❌ 메모리 부족 → 메모리 할당 늘림
❌ 에러 발생 → 재시도 횟수 늘림
❌ 경고 발생 → 경고 삭제

✅ 근본 원인을 찾아 해결하라
✅ 우회책은 사용자 확인 후에만

---

## 🇰🇷 언어

- 사용자와의 대화: 한국어
- 코드 주석: 한국어 또는 영어 (프로젝트 관례 따름)
- Commit 메시지: 한국어 또는 영어 (프로젝트 관례 따름)

---

## 🤖 Codex 자동 실행 (Full Auto)

- 기본 실행은 Codex 기준으로 한다.
- 대화 턴 마무리 시 "다음을 이어서 진행할까요?" 같은 확인 질문을 하지 않는다.
- 사용자 요청 범위의 작업은 중간 확인 없이 끝까지 진행한다.
- 명령 승인(approval)과 대화형 확인 질문은 구분하고, 승인 이슈가 없으면 계속 진행한다.
- non-interactive 실행이 가능한 작업은 `codex exec -c "approval_policy='never'" -s workspace-write "<task>"`를 우선 사용한다.
- 아래 3가지에서만 멈춘다:
  1) 파괴적/되돌리기 어려운 작업
  2) 자격증명/비밀키가 필요한 작업
  3) 스펙 부재로 결과가 크게 달라지는 치명적 불확실성
- 그 외는 합리적 가정으로 진행하고, 마지막에 `Assumptions/TODO`로만 정리한다.
