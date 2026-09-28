---
paths:
  - "**/*.{py,sql}"
---

# SQL 코딩 표준

dialect: SparkSQL, linter: sqlfluff (`.sqlfluff` 참조)

## 대소문자 (CP01~CP04)

- 키워드 대문자: `SELECT`, `FROM`, `WHERE`, `JOIN`, `ON`, `GROUP BY`, `ORDER BY`
- 함수명 대문자: `COUNT()`, `SUM()`, `COALESCE()`, `DATE_FORMAT()`
- 리터럴 대문자: `TRUE`, `FALSE`, `NULL`
- 타입 대문자: `STRING`, `INT`, `BIGINT`, `TIMESTAMP`
- 식별자(컬럼/테이블/별칭)는 소문자 snake_case

## 레이아웃

- 들여쓰기: 4칸 스페이스
- 최대 줄 길이: 120자
- 쉼표(`,`)는 줄 끝(trailing)에 배치
- `WHERE` 절은 줄 앞(leading)에 배치
- 논리 연산자(`AND`, `OR`)는 줄 앞(leading)에 배치
- 비교/산술/대입 연산자(`=`, `+`, `-` 등)는 inline 유지
- `SELECT *`는 단독 줄일 때만 허용
- trailing comma 금지

## PySpark SQL

- `spark.sql()` 내 SQL 문자열에도 동일한 대소문자·레이아웃 규칙 적용
- 여러 줄 SQL은 triple-quote (`"""`) 사용
