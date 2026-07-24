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

`uv init`으로 생성된 `pyproject.toml`을 보강. 상세 템플릿은 `references/pyproject-template.toml` 참조.

필수 섹션: `[project]` (name, version, requires-python>=3.11, dependencies), `[project.optional-dependencies].dev` (pytest, ruff, mypy, pre-commit), `[build-system]` (hatchling), `[tool.ruff]` (py311, line-length=120, select=E,F,I,N,W,UP), `[tool.mypy]` (strict), `[tool.pytest.ini_options]` (testpaths=tests).

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

`uv add --group dev pre-commit && uv run pre-commit install`

`.pre-commit-config.yaml` 생성: ruff (check --fix + format) + mypy hooks. 상세 예시는 `references/pre-commit-template.yaml` 참조.

#### 프로젝트 디렉토리 구조

src 레이아웃: `src/project_name/` + `tests/` + `pyproject.toml` + `.pre-commit-config.yaml`

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
