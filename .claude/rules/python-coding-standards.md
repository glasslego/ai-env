---
paths:
  - "**/*.py"
---

# Python 코딩 표준

프로젝트의 `pyproject.toml`, pre-commit 설정, 프로젝트 전용 지침이 더 구체적인 경우
해당 설정을 우선한다.

## Type Hints

- 모든 함수/메서드 시그니처에 **모든 인자와 반환값의 type hint 필수** (예외 없음)
- 기본 타입: `str`, `int`, `float`, `bool`, `bytes`
- 컬렉션: `list[T]`, `dict[K, V]`, `tuple[T, ...]`, `set[T]` (PEP 585, Python 3.9+)
- nullable: `T | None` (PEP 604, Python 3.10+) — `Optional[T]` 지양
- PySpark: `DataFrame`, `Column`, `SparkSession`, `Row` 등 명시적으로 import 후 사용
- 반환 없을 때 `-> None` 명시 (생략 금지)
- `*args`, `**kwargs`도 `*args: str`, `**kwargs: Any` 형태로 명시
- 복잡한 타입은 `from __future__ import annotations` + 문자열 평가 활용 가능
- `Any` 사용은 지양하되 불가피한 경우 주석으로 이유 명시

예시:

```python
def build_persona_map(
    spark: SparkSession, phase: str, top_n: int = 10
) -> dict[str, list[float]]:
    ...

def write_to_iceberg(df: DataFrame, dt: str | None = None) -> None:
    ...
```

## Docstring

- Google style docstrings 사용
- 모든 public 함수/클래스에 필수
- Args, Returns, Raises 섹션 명시

## PySpark

- `from pyspark.sql import functions as F` (항상 F alias)
- UDF 사용 전 네이티브 함수로 가능한지 반드시 확인
- DataFrame API 우선, SparkSQL은 복잡한 윈도우 함수에서만
- `.cache()` / `.persist()` 사용 시 반드시 `.unpersist()` 쌍으로
- `spark.read` 시 `inferSchema=True` 대신 명시적 `StructType` 정의
- 컬럼 접근은 `F.col("col")` 사용 (`df['col']` 지양)
- 파티션 수는 명시적 지정 — `repartition()`/`coalesce()` 사용 시 근거 주석 필수
- 소규모 테이블(<100MB)은 `F.broadcast()` 명시. 대용량 DataFrame에 `F.broadcast()`를 강제하면 driver OOM 위험(예: 265만건/572MB broadcast → driver OOM). broadcast 전 대상 크기를 실측하고, 애매하면 강제하지 않는다.
- `collect()` / `toPandas()`는 최종 단계에서만, 이유 주석 필수
- 스키마 변경 시 하위 호환성 검토 주석 필수 (nullable 변경 등)
- **SCAPPY/gensim 텍스트 임베딩은 단일 스레드 순차 호출만** — gensim/numpy 네이티브는 thread-unsafe라 멀티스레드 동시 호출 시 SIGSEGV(exit 139)로 죽는다(검증됨, `scappy_embedding_client.py`). 병렬화가 필요하면 스레드가 아니라 Spark executor 분산으로 처리한다.

## Testing (pytest)

- **테스트 디렉토리 구조는 src 패키지 구조와 반드시 1:1 대응**
  - `src/app/feature_store/for_me/user_context/user_action/foo.py` → `tests/app/feature_store/for_me/user_context/user_action/test_foo.py`
  - src에 새 디렉토리/모듈을 추가하면 tests에도 동일 경로로 테스트 파일 생성
  - src에서 모듈 경로가 변경(이동/리네임)되면 tests도 동일하게 반영
- 공통 fixture(SparkSession 등)는 `conftest.py`에 정의
- 함수명 `test_`, 클래스명 `Test` prefix
- `assert a == b` 단순 구문 사용 (pytest가 상세 오류 제공)
- 테스트 파일 하단에 `__main__` 블록 추가하여 단독 실행 지원:

```python
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
```

## Logging (loguru)

- `import logging` 대신 `from loguru import logger` 사용
- 구조화 로그: `logger.bind(key=value).info("message")`
- 예외 자동 기록: `@logger.catch` 데코레이터 활용

## Lint & Format

- black (formatter) + isort (import 정렬) + flake8 (linter)
- pre-commit으로 커밋 전 자동 실행 (`.pre-commit-config.yaml` 참조)

## 네이밍 컨벤션

- 변수/함수: `snake_case`
- 클래스: `PascalCase`
- 상수: `UPPER_SNAKE_CASE`
- private: `_single_underscore` prefix
- PySpark 컬럼명 상수: `COL_USER_ID = "user_id"` (문자열 직접 사용 지양)

## 예외 처리

- 구체적 예외 타입 명시 (bare `except:` 금지)
- `raise ... from e`로 원인 체이닝
- `except: pass`는 이유 주석 필수

## Magic Number 금지

- 의미 있는 상수로 추출: `MIN_SCORE_THRESHOLD = 0.7`
- 임계값, 가중치, 배수 등은 반드시 상수 또는 config로 관리

## 함수/클래스 설계

- 함수 20줄 이하 권장, 복잡하면 분리
- 모듈(파일) 300줄 이하 권장, 초과 시 분리 검토
- `__init__.py`에 구현 코드 금지 (re-export만)
- 빈 `__init__.py` 신규 생성 금지 — implicit namespace packages 사용 (Python 3.3+)
- 데이터 저장 목적 클래스는 `@dataclass` 또는 Pydantic 사용
- 전역 변수 금지, 설정은 Settings 객체 또는 환경 변수로 관리
- 문자열 포매팅은 f-string 사용 (`%` formatting 금지)

## 시크릿 관리

- 코드/설정 파일에 하드코딩 절대 금지
- 환경 변수 또는 Vault 사용
- `.env` 파일은 커밋 금지 (`.gitignore` + `.env.sample` 유지)

## Import 순서

- stdlib → third-party → local (isort 자동 정렬)
