---
id: SPEC-005
title: Agent Fallback (vibe Function)
status: implemented
created: 2025-06-01
updated: 2026-02-13
---

# SPEC-005: Agent Fallback (vibe Function)

## 개요

`vibe`는 `ai-env sync` 실행 시 자동 생성되는 bash 쉘 함수다. AI 에이전트를 우선순위 순서대로 시도하고, 앞선 에이전트가 비정상 종료(세션 한도 도달, 에러 등)하면 다음 에이전트로 자동 전환한다.

생성된 함수는 `generated/shell_exports.sh`에 환경변수 export 뒤에 추가되며, 사용자가 `source ./generated/shell_exports.sh`로 활성화한다.

## 핵심 유스케이스

Claude Code는 세션당 사용 한도가 있다. 한도에 도달하면 비정상 종료(exit code != 0)되는데, `vibe`가 이를 감지하여 Codex CLI 등 다음 에이전트로 자동 전환한다. 사용자가 수동으로 도구를 바꿀 필요가 없다.

## 설정

### 설정 소스

`config/settings.yaml`의 `agent_priority` 필드:

```yaml
# === Agent 우선순위 (바이브코딩 fallback) ===
# vibe 함수가 이 순서대로 에이전트를 시도
# 앞의 에이전트가 세션 한도/에러로 종료되면 다음 에이전트로 자동 전환
agent_priority:
  - claude
  - codex
```

### Pydantic 모델

`src/ai_env/core/config.py`의 `Settings` 클래스:

```python
class Settings(BaseModel):
    agent_priority: list[str] = Field(default_factory=lambda: ["claude", "codex"])
```

기본값은 `["claude", "codex"]`이다.

### 출력 경로

```yaml
outputs:
  shell_exports: ./generated/shell_exports.sh
```

## vibe() 함수 동작

### 사용법

```bash
vibe                # 1순위 에이전트(claude)부터 시작
vibe "로그인 만들어줘"  # 프롬프트와 함께 시작
vibe -2             # 2순위 에이전트(codex)부터 시작 (1순위 건너뜀)
vibe -3             # 3순위부터 시작
vibe -l             # 에이전트 우선순위 목록 출력
vibe --list         # 에이전트 우선순위 목록 출력 (동일)
```

### 실행 흐름

```
vibe [옵션] [프롬프트]
  │
  ├─ -l / --list → 우선순위 목록 출력 후 종료
  ├─ -N → start_idx를 N-1로 설정 (N순위부터 시작)
  │
  └─ for agent in agents[start_idx:]:
       │
       ├─ agent == "claude" && $CLAUDECODE 설정됨?
       │    → "이미 Claude Code 세션 내부 (건너뜀)" 출력, continue
       │
       ├─ command -v $agent 실패?
       │    → "설치되지 않음 (건너뜀)" 출력, continue
       │
       ├─ 프롬프트 있음 → $agent "$prompt" 실행
       │  프롬프트 없음 → $agent 실행
       │
       ├─ exit code 0 → return 0 (성공)
       │
       └─ exit code != 0
            → "종료 (code: N). 다음 에이전트로 전환..." 출력
            → 다음 에이전트로 계속

  모든 에이전트 소진 또는 사용 가능한 에이전트 없음:
    → 에러 메시지 출력, return 1
```

### 주요 로직

1. **옵션 파싱**: `case` 문으로 `-l`/`--list`(목록 출력)과 `-N`(N순위부터 시작) 처리
2. **Claude Code 중첩 방지**: 이미 Claude Code 세션 내부(`$CLAUDECODE` 환경변수 존재)이면 `claude` 에이전트를 건너뜀
3. **설치 확인**: `command -v`로 에이전트 실행 파일 존재 확인
4. **프롬프트 전달**: 프롬프트가 있으면 에이전트에 첫 번째 인자로 전달
5. **종료 코드 기반 전환**: exit code 0이면 성공 종료, 그 외는 다음 에이전트로 전환
6. **소진 처리**: 시도한 에이전트가 0개면 "사용 가능한 에이전트 없음", 1개 이상이면 "모든 에이전트 소진" 메시지 출력

## 생성 로직

### MCPConfigGenerator.generate_shell_functions()

`src/ai_env/mcp/generator.py`에 구현:

```python
def generate_shell_functions(self) -> str:
    agents = self.settings.agent_priority
    if not agents:
        return ""
    # f-string으로 bash 함수 생성
```

- `self.settings.agent_priority` 리스트를 읽음
- 비어있으면 빈 문자열 반환 (함수 미생성)
- agents 배열과 priority 표시 주석을 포함한 완전한 bash 함수를 f-string으로 생성

### save_all()에서의 통합

```python
def save_all(self, dry_run: bool = False) -> dict[str, Path]:
    configs = [
        # ... 다른 설정들 ...
        (
            "shell_exports",
            self.settings.outputs.shell_exports,
            self.secrets.export_to_shell() + "\n\n" + self.generate_shell_functions(),
        ),
    ]
```

`shell_exports.sh` 파일 구성:
1. `secrets.export_to_shell()` -- 환경변수 export 문
2. `"\n\n"` -- 구분자
3. `generate_shell_functions()` -- vibe 함수

## 생성되는 코드 예시

`agent_priority: [claude, codex]` 설정 시 `generated/shell_exports.sh`에 추가되는 내용:

```bash
# === AI Agent Fallback (vibe coding) ===
# Priority: claude → codex
# Usage: vibe [prompt]  - 우선순위대로 에이전트 시도, 실패 시 자동 전환
#        vibe -2        - 2순위 에이전트부터 시작 (예: codex)
#        vibe -l        - 에이전트 우선순위 목록 출력
vibe() {
    local agents=("claude" "codex")
    local start_idx=0
    local prompt=""

    case "$1" in
        -l|--list)
            printf '\033[36mAgent priority:\033[0m\n'
            for i in "${!agents[@]}"; do
                printf '  %d. %s\n' "$((i+1))" "${agents[$i]}"
            done
            return 0
            ;;
        -[0-9])
            start_idx=$((${1#-} - 1))
            shift
            ;;
    esac
    prompt="$*"

    local tried=0
    for ((i=start_idx; i<${#agents[@]}; i++)); do
        local agent="${agents[$i]}"

        if [[ "$agent" == "claude" && -n "${CLAUDECODE:-}" ]]; then
            printf '\033[33m⏭ %s: 이미 Claude Code 세션 내부 (건너뜀)\033[0m\n' "$agent"
            continue
        fi

        if ! command -v "$agent" &>/dev/null; then
            printf '\033[33m⏭ %s: 설치되지 않음 (건너뜀)\033[0m\n' "$agent"
            continue
        fi

        tried=$((tried + 1))
        printf '\033[36m🚀 Starting %s...\033[0m\n' "$agent"

        if [[ -n "$prompt" ]]; then
            "$agent" "$prompt"
        else
            "$agent"
        fi
        local exit_code=$?

        if [[ $exit_code -eq 0 ]]; then
            return 0
        fi

        printf '\n\033[33m⚠ %s 종료 (code: %d). 다음 에이전트로 전환...\033[0m\n\n' "$agent" "$exit_code"
    done

    if [[ $tried -eq 0 ]]; then
        printf '\033[31m❌ 사용 가능한 AI 에이전트가 없습니다\033[0m\n'
    else
        printf '\033[31m❌ 모든 AI 에이전트 소진\033[0m\n'
    fi
    return 1
}
```

## 활성화 방법

`ai-env sync` 실행 후:

```bash
source ./generated/shell_exports.sh
```

또는 `.bashrc`/`.zshrc`에 추가:

```bash
source /path/to/ai-env/generated/shell_exports.sh
```

## 우선순위 변경

`config/settings.yaml`의 `agent_priority` 수정 후 재동기화:

```bash
# 예: Codex를 1순위로 변경
# agent_priority:
#   - codex
#   - claude

uv run ai-env sync
source ./generated/shell_exports.sh
```

## 테스트 커버리지

`tests/test_ai_env.py`의 `TestGenerateShellFunctions` 클래스:

| 테스트 | 검증 내용 |
|--------|-----------|
| `test_default_priority` | 기본 설정(claude, codex)으로 함수 생성 확인 |
| `test_custom_priority` | 커스텀 우선순위(codex, gemini) 반영 확인 |
| `test_single_agent` | 에이전트 1개일 때 정상 생성 |
| `test_empty_priority` | 빈 리스트이면 빈 문자열 반환 |
| `test_contains_claudecode_guard` | CLAUDECODE 중첩 방지 코드 포함 확인 |
| `test_contains_skip_option` | -N 옵션 파싱 코드 포함 확인 |

## 관련 파일

| 파일 | 역할 |
|------|------|
| `config/settings.yaml` | `agent_priority` 설정 소스 |
| `src/ai_env/core/config.py` | `Settings.agent_priority` Pydantic 모델 |
| `src/ai_env/mcp/generator.py` | `generate_shell_functions()` 구현 |
| `generated/shell_exports.sh` | 생성된 출력 (gitignore) |
| `tests/test_ai_env.py` | `TestGenerateShellFunctions` 테스트 |

## 제약사항

- bash 전용 (zsh 호환이지만 공식 지원 대상은 bash)
- 에이전트 목록은 생성 시점에 하드코딩됨 (런타임 설정 변경 불가, 재동기화 필요)
- 프롬프트는 단일 문자열로만 전달 (`$*`로 합침)
- `-N` 옵션에서 N은 한 자리 숫자만 지원 (`-[0-9]` 패턴)
