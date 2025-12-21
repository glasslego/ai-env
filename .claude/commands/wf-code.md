# Plan/Spec 기반 TDD 코드 생성

토픽 ID: $ARGUMENTS

> `claude --fallback`과 함께 사용하면 토큰 한도 도달 시 Codex로 자동 전환됩니다.
> 모듈은 **순차 실행**한다 (모듈 간 의존성 가능하므로 병렬화하지 않는다).

**절대 금지**: 테스트를 통과시키기 위해 테스트 코드 자체를 삭제/수정하지 마라.

## Step 1: 토픽 YAML 로드

- `~/work/glasslego/ai-env/config/topics/$ARGUMENTS.yaml` 파일을 Read로 읽는다
- `code` 섹션이 없으면 "이 토픽은 코드 생성 대상이 아닙니다" 안내 후 종료
- Obsidian 경로:
  - vault_root = `/Users/megan/Documents/Obsidian Vault`
  - base_path = `{vault_root}/{topic.obsidian_base}`

## Step 2: Plan/Spec 읽기

- `{base_path}/{plan.output}` 파일을 Read로 읽는다
- spec이 없으면 `claude "/wf-spec $ARGUMENTS"` 실행을 안내하고 종료
- spec의 구현 우선순위(MVP 로드맵)를 확인하여 모듈 순서를 결정
- spec의 기술 스택 결정사항을 파악 (의존성 패키지 목록)

## Step 2.5: 체크포인트 로드

`{base_path}/01_시스템구성/_code-status.yaml` 파일이 존재하면 Read로 읽는다.

```yaml
# _code-status.yaml 형식
last_updated: "2026-02-23"
modules:
  core:
    status: done      # done | failed | pending
    tests_passed: 12
    tests_failed: 0
  api:
    status: failed
    error: "3회 시도 후 test_auth_flow 실패"
  scheduler:
    status: pending
```

- **done** 모듈: Step 4에서 건너뛴다 (사용자에게 "core: 이전 완료, 건너뜀" 표시)
- **failed** 모듈: 해당 모듈부터 재개한다
- **pending** 모듈: 순서대로 실행한다
- 파일이 없으면 모든 모듈을 pending으로 간주한다

각 모듈의 Step 4-5 완료 시 이 파일을 Write로 갱신한다.

## Step 3: 프로젝트 초기화 (최초 실행 시)

`code.target_repo` 경로에 프로젝트가 없으면 초기화한다.

Python 프로젝트 (test_framework == pytest):
```bash
mkdir -p {target_repo}
cd {target_repo}
git init
uv init --name {프로젝트명}
```

디렉토리 구조:
```
{target_repo}/
├── pyproject.toml
├── src/{프로젝트명}/
│   ├── __init__.py
│   └── {module.name}.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_{module.name}.py
├── .gitignore
└── README.md
```

- pyproject.toml에 spec에서 결정된 의존성 포함
- `uv add`로 패키지 설치
- 프로젝트가 이미 존재하면 이 단계를 건너뛴다

## Step 4: TDD 방식 모듈별 코드 생성

`code.modules`를 **순서대로** 처리한다. 각 모듈마다:

### 4-1. 테스트 먼저 작성 (Red)

- spec에서 해당 모듈의 요구사항 분석
- `tests/test_{module.name}.py` 작성
- 핵심 유스케이스별 테스트 함수
- 경계 조건, 에러 케이스 포함
- 외부 API는 mock 처리

### 4-2. 구현 코드 작성 (Green)

- `src/{프로젝트명}/{module.name}.py` 작성
- 테스트를 통과하는 **최소 구현**
- type hints 필수, Google style docstring
- 기존 모듈의 함수를 재활용 (중복 금지)

### 4-3. 테스트 실행 및 수정

```bash
cd {target_repo} && uv run pytest tests/test_{module.name}.py -v
```

- 실패 시 **구현 코드만** 수정 (테스트는 수정하지 않음!)
- 최대 3회 반복 후에도 실패하면 사용자에게 알림
- 사용자 확인 없이 테스트 코드를 변경하지 않는다

### 4-4. 리팩토링 (Refactor)

- 테스트 통과 확인 후 코드 정리
- 중복 제거, 네이밍 개선
- 리팩토링 후 테스트 재실행으로 기능 보존 확인

### 4-5. 모듈 완료 + 체크포인트 저장

- 해당 모듈 전체 테스트 통과 확인
- `_code-status.yaml`에 해당 모듈 상태 기록:
  - 성공 시: `status: done`, `tests_passed: N`
  - 실패 시 (3회 반복 후): `status: failed`, `error: "실패 사유"`
- 다음 모듈로 이동

## Step 5: 통합 테스트

모든 모듈 완료 후:

```bash
cd {target_repo}
uv run pytest -v --tb=short
uv run ruff check .
uv run ruff format .
```

- 전체 테스트 통과 + lint 클린 확인
- 실패 항목이 있으면 수정

## Step 6: Obsidian에 코드 현황 업데이트

`{base_path}/01_시스템구성/code-status.md` 생성/업데이트:

```markdown
# 코드 구현 현황

마지막 업데이트: {날짜}
레포: {target_repo}

| 모듈 | 설명 | 테스트 | 구현 | 상태 |
|------|------|:------:|:----:|:----:|
| {name} | {desc} | ✅/❌ | ✅/❌ | 통과/실패 |

## 전체 테스트 결과
- pytest: {n} passed, {n} failed
- ruff: clean / {n} issues
```

## Step 7: 워크플로우 상태 갱신

```bash
uv run ai-env pipeline workflow $ARGUMENTS
```

Phase가 "implementing"으로 업데이트되었는지 확인한다.

## Step 8: 완료 보고

사용자에게 보고:
- **생성된 모듈** 목록 + 각 모듈 테스트 결과
- **전체 pytest 결과** 요약
- **코드 현황 파일** 경로
- **다음 단계** 권장 (통합테스트, 배포, 추가 모듈 등)
