---
id: SPEC-007
title: Doctor Health Check
status: implemented
created: 2026-02-16
updated: 2026-02-16
---

# SPEC-007: Doctor Health Check

## 1. 개요

`ai-env doctor`는 AI 환경의 건강 상태를 검사하는 진단 명령어다. `.env` 환경변수, 동기화 상태, 도구 설치 여부, 쉘 설정 등을 한 번에 점검하여 문제를 조기에 발견한다.

### 핵심 설계 결정

- **비파괴적 검사**: 기본 동작은 읽기 전용이며, 파일을 변경하지 않는다.
- **카테고리별 독립 검사**: 각 검사는 독립적으로 실행되며, 하나가 실패해도 나머지는 계속된다.
- **기존 모듈 재활용**: `MCPConfigGenerator`, `SecretsManager`, `sync.py`의 로직을 재사용하여 "현재 상태 vs 기대 상태"를 비교한다.

## 2. CLI 인터페이스

```bash
ai-env doctor              # 전체 검사
ai-env doctor --json       # JSON 출력 (CI/자동화용)
```

## 3. 검사 카테고리

### 3.1 환경 (Environment)

| 체크 항목 | 검증 방법 | 결과 |
|----------|----------|------|
| `.env` 파일 존재 | `Path.exists()` | pass/fail |
| 필수 환경변수 설정 | `SecretsManager.get()` | provider별 pass/warn |

### 3.2 도구 설치 (Tools)

| 체크 항목 | 검증 방법 | 결과 |
|----------|----------|------|
| claude 설치 | `shutil.which()` | pass/warn |
| codex 설치 | `shutil.which()` | pass/warn |
| gemini 설치 | `shutil.which()` | pass/warn |

### 3.3 동기화 드리프트 (Sync Drift)

"지금 `ai-env sync`를 실행했을 때의 결과"와 "현재 파일 내용"을 비교한다.

| 체크 항목 | 검증 방법 | 결과 |
|----------|----------|------|
| MCP 설정 파일들 | SHA-256 해시 비교 (생성 결과 vs 실제 파일) | pass/drift |
| Claude 글로벌 설정 | CLAUDE.md, settings.json, commands/, skills/ 존재 확인 | pass/warn |
| Codex AGENTS.md | 소스 vs 대상 비교 | pass/drift |
| Gemini GEMINI.md | 소스 vs 대상 비교 | pass/drift |
| shell_exports.sh | 해시 비교 | pass/drift |

### 3.4 쉘 설정 (Shell)

| 체크 항목 | 검증 방법 | 결과 |
|----------|----------|------|
| shell_exports.sh 존재 | `Path.exists()` | pass/fail |

## 4. 데이터 모델

```python
@dataclass
class CheckResult:
    name: str           # 검사 항목 이름
    status: str         # "pass", "warn", "fail"
    message: str        # 상태 설명
    category: str       # "env", "tools", "sync", "shell"

@dataclass
class DoctorReport:
    checks: list[CheckResult]
    passed: int
    warned: int
    failed: int
```

## 5. 파일 구조

| 파일 | 역할 |
|------|------|
| `src/ai_env/core/doctor.py` | 검사 로직 (`run_doctor()` + 개별 체크 함수) |
| `src/ai_env/cli/doctor_cmd.py` | Click 명령어 + Rich 출력 |
| `tests/core/test_doctor.py` | 단위 테스트 |

## 6. 출력 형식

### 기본 (Rich 테이블)

```
🏥 AI Environment Health Check

  Environment
  ✓ .env file exists
  ✓ ANTHROPIC_API_KEY configured
  ⚠ GOOGLE_API_KEY not set

  Tools
  ✓ claude installed
  ✓ codex installed
  ⚠ gemini not found

  Sync Status
  ✓ claude_desktop config up to date
  ✗ codex_global config drifted
  ✓ shell_exports.sh up to date

Summary: 8 passed, 2 warnings, 1 failed
```

### JSON (`--json`)

```json
{
  "checks": [...],
  "summary": {"passed": 8, "warned": 2, "failed": 1}
}
```
