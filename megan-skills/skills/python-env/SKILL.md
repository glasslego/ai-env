---
name: python-env
description: |
  uv를 사용한 Python 프로젝트 환경 구축 가이드.
  Use when users want to: (1) 새 Python 프로젝트 초기화, (2) pyproject.toml 구성,
  (3) 가상환경 생성 및 의존성 관리, (4) 개발 도구(ruff, mypy, pytest, pre-commit) 설정,
  (5) 기존 프로젝트에 uv 도입, (6) pip → uv 마이그레이션.
---

# Python Environment Setup with uv

uv를 사용하여 Python 프로젝트 환경을 구축하는 스킬.

## 프로젝트 초기화 워크플로우

### 1. 새 프로젝트 생성

```bash
# 프로젝트 디렉토리 생성 및 초기화
uv init <project-name>
cd <project-name>

# Python 버전 지정 (3.11+ 권장)
uv python pin 3.11

# 가상환경 생성 및 의존성 설치
uv sync
```

### 2. 기존 프로젝트에 uv 도입

```bash
cd <existing-project>

# requirements.txt가 있는 경우
uv init
uv add $(cat requirements.txt | grep -v '^#' | grep -v '^$' | tr '\n' ' ')

# setup.py/setup.cfg만 있는 경우
uv init
# pyproject.toml에 의존성 수동 이전 후
uv sync
```

### 3. pyproject.toml 기본 구성

`uv init`으로 생성된 `pyproject.toml`을 아래를 참고하여 보강:

```toml
[project]
name = "project-name"
version = "0.1.0"
description = "프로젝트 설명"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=6.0",
    "ruff>=0.9",
    "mypy>=1.14",
    "pre-commit>=4.0",
]

[project.scripts]
# CLI 진입점 (필요시)
# my-cli = "project_name.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.backends"

[tool.ruff]
target-version = "py311"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.ruff.lint.isort]
known-first-party = ["project_name"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
```

### 4. 의존성 관리

```bash
# 의존성 추가
uv add <package>

# 개발 의존성 추가 (--group dev 또는 --optional dev)
uv add --group dev <package>

# 의존성 제거
uv remove <package>

# 모든 의존성 설치 (개발 의존성 포함)
uv sync --all-extras

# 특정 그룹만 설치
uv sync --group dev

# lock 파일 업데이트
uv lock
```

### 5. 개발 도구 설정

#### pre-commit

```bash
uv add --group dev pre-commit
uv run pre-commit install
```

`.pre-commit-config.yaml` 생성:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.14.1
    hooks:
      - id: mypy
        additional_dependencies: []
```

#### 프로젝트 디렉토리 구조

```
project-name/
├── pyproject.toml
├── uv.lock
├── .python-version
├── .pre-commit-config.yaml
├── .gitignore
├── src/
│   └── project_name/
│       ├── __init__.py
│       └── main.py
└── tests/
    ├── __init__.py
    └── test_main.py
```

### 6. 실행 및 테스트

```bash
# 스크립트 실행
uv run python src/project_name/main.py

# pytest 실행
uv run pytest

# 커버리지 포함
uv run pytest --cov

# ruff 검사
uv run ruff check .
uv run ruff format .

# mypy 타입 체크
uv run mypy src/
```

## 판단 기준

### src 레이아웃 vs flat 레이아웃

- **src 레이아웃** (권장): 패키지 배포 예정이거나 import 충돌 방지 필요시
- **flat 레이아웃**: 간단한 스크립트성 프로젝트

사용자가 명시하지 않으면 **src 레이아웃** 사용.

### 의존성 그룹 전략

- `dependencies`: 런타임 필수 의존성
- `[project.optional-dependencies].dev`: 개발 도구 (pytest, ruff, mypy, pre-commit)
- `[dependency-groups].dev`: uv 전용 개발 그룹 (`uv add --group dev`)

사용자가 명시하지 않으면 `[dependency-groups]` 방식 사용 (uv 네이티브).

### 권장 라이브러리

글로벌 CLAUDE.md의 "자주 쓰는 라이브러리" 섹션 참조.

## 참고

- uv 고급 사용법은 `references/uv-advanced.md` 참조
- 항상 `source .venv/bin/activate` 없이 `uv run`으로 실행 가능
- `pip install` 대신 `uv add` 사용 (글로벌 규칙)
