# uv 고급 사용법

## Python 버전 관리

```bash
# 사용 가능한 Python 버전 목록
uv python list

# 특정 버전 설치
uv python install 3.11 3.12

# 프로젝트에 Python 버전 고정
uv python pin 3.11
# → .python-version 파일 생성
```

## Workspace (모노레포)

여러 패키지를 하나의 저장소에서 관리:

```toml
# 루트 pyproject.toml
[tool.uv.workspace]
members = ["packages/*"]
```

```
monorepo/
├── pyproject.toml          # workspace 루트
├── uv.lock                 # 공유 lock 파일
├── packages/
│   ├── core/
│   │   ├── pyproject.toml
│   │   └── src/core/
│   ├── api/
│   │   ├── pyproject.toml
│   │   └── src/api/
│   └── cli/
│       ├── pyproject.toml
│       └── src/cli/
```

```bash
# 특정 패키지의 의존성 추가
uv add --package api flask

# 워크스페이스 내부 의존성
uv add --package api core --editable
```

## Tool 관리 (글로벌 CLI 도구)

```bash
# 글로벌 도구 설치
uv tool install ruff
uv tool install httpie

# 일회성 실행 (설치 없이)
uvx ruff check .
uvx black --check .

# 설치된 도구 목록
uv tool list
```

## Lock 파일 활용

```bash
# lock 파일 생성/업데이트
uv lock

# 특정 플랫폼용 lock
uv lock --python-platform linux

# lock 파일 기반 설치 (CI용)
uv sync --frozen

# lock 파일 검증
uv lock --check
```

## Docker 통합

```dockerfile
FROM python:3.11-slim

# uv 설치
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 의존성 캐시 활용
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 소스 코드 복사 후 프로젝트 설치
COPY . .
RUN uv sync --frozen --no-dev

CMD ["uv", "run", "python", "-m", "project_name"]
```

캐시 마운트를 활용한 빌드 최적화:

```dockerfile
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev
```

## CI/CD 통합

### GitHub Actions

```yaml
- uses: astral-sh/setup-uv@v5
  with:
    version: "latest"

- run: uv sync --all-extras
- run: uv run pytest
- run: uv run ruff check .
- run: uv run mypy src/
```

### 캐시 설정

```yaml
- uses: astral-sh/setup-uv@v5
  with:
    enable-cache: true
    cache-dependency-glob: "uv.lock"
```

## 환경변수 및 설정

```bash
# uv 캐시 디렉토리 변경
export UV_CACHE_DIR=/path/to/cache

# 기본 Python 버전
export UV_PYTHON=3.11

# 오프라인 모드 (lock 기반)
export UV_FROZEN=1

# 인덱스 URL 설정 (사내 PyPI 미러)
export UV_INDEX_URL=https://pypi.company.com/simple/
export UV_EXTRA_INDEX_URL=https://pypi.org/simple/
```

`pyproject.toml`에서도 설정 가능:

```toml
[tool.uv]
index-url = "https://pypi.company.com/simple/"
extra-index-url = ["https://pypi.org/simple/"]
```

## pip 마이그레이션 체크리스트

| pip 명령어 | uv 명령어 |
|-----------|----------|
| `pip install pkg` | `uv add pkg` |
| `pip install -r requirements.txt` | `uv add $(cat requirements.txt)` |
| `pip install -e .` | `uv sync` (자동 editable) |
| `pip install --upgrade pkg` | `uv add pkg` (자동 최신) |
| `pip uninstall pkg` | `uv remove pkg` |
| `pip freeze` | `uv pip freeze` 또는 `uv lock` |
| `pip list` | `uv pip list` |
| `python -m venv .venv` | `uv venv` (자동 생성) |
| `source .venv/bin/activate` | `uv run ...` (활성화 불필요) |
