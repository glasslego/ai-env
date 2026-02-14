---
id: SPEC-005
title: Agent Fallback (claude --fallback)
status: implemented
created: 2025-06-01
updated: 2026-02-14
---

# SPEC-005: Agent Fallback (claude --fallback)

## 개요

`claude --fallback`은 `ai-env sync` 실행 시 자동 생성되는 `claude()` bash 쉘 함수를 통해 제공된다. 원본 `claude` 바이너리를 shadow하며, `--fallback` 플래그 없이 호출하면 원본 바이너리로 passthrough한다. `--fallback` 모드에서는 AI 에이전트를 우선순위 순서대로 시도하고, 앞선 에이전트가 비정상 종료(세션 한도 도달, 에러 등)하면 다음 에이전트로 자동 전환한다.

생성된 함수는 `generated/shell_exports.sh`에 환경변수 export 뒤에 추가되며, 사용자가 `source ./generated/shell_exports.sh`로 활성화한다.

## 핵심 유스케이스

Claude Code는 세션당 사용 한도가 있다. 한도에 도달하면 비정상 종료(exit code != 0)되는데, `claude --fallback`이 이를 감지하여 Codex CLI 등 다음 에이전트로 자동 전환한다. 사용자가 수동으로 도구를 바꿀 필요가 없다.

## 설정

### 설정 소스

`config/settings.yaml`의 `agent_priority` 필드:

```yaml
# === Agent 우선순위 (claude --fallback) ===
# claude --fallback이 이 순서대로 에이전트를 시도
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

## claude() 함수 동작

### 사용법

```bash
claude --fallback              # 1순위 에이전트(claude)부터 시작
claude --fallback "로그인 만들어줘"  # 프롬프트와 함께 시작
claude --fallback -2           # 2순위 에이전트(codex)부터 시작 (1순위 건너뜀)
claude --fallback -3           # 3순위부터 시작
claude --fallback -l           # 에이전트 우선순위 목록 출력
claude --fallback --list       # 에이전트 우선순위 목록 출력 (동일)
claude                         # 일반 claude 실행 (passthrough)
claude --resume session-id     # 일반 claude 실행 (passthrough)
```

### 실행 흐름

```
claude [args...]
  │
  ├─ $1 != "--fallback" → command claude "$@" (passthrough) → return
  │
  └─ $1 == "--fallback" → shift, fallback 모드 진입
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
            ├─ agent == "claude" → command claude "$prompt" 실행
            │  agent != "claude" → $agent "$prompt" 실행
            │
            ├─ exit code 0 → return 0 (성공)
            │
            └─ exit code != 0
                 → rate limit 감지 시 cooldown 설정
                 → "종료 (code: N). 다음 에이전트로 전환..." 출력
                 → 다음 에이전트로 계속

  모든 에이전트 소진 또는 사용 가능한 에이전트 없음:
    → 에러 메시지 출력, return 1
```

### 주요 로직

1. **Passthrough 가드**: `--fallback` 플래그 없으면 `command claude "$@"`로 원본 바이너리에 모든 인자 전달
2. **`command claude`로 재귀 방지**: `claude()` 함수가 원본 바이너리를 shadow하므로, 내부에서 claude 바이너리 호출 시 반드시 `command claude` 사용 (`_run_agent()` 헬퍼 함수로 추상화)
3. **옵션 파싱**: `case` 문으로 `-l`/`--list`(목록 출력)과 `-N`(N순위부터 시작) 처리
4. **Claude Code 중첩 방지**: 이미 Claude Code 세션 내부(`$CLAUDECODE` 환경변수 존재)이면 `claude` 에이전트를 건너뜀
5. **설치 확인**: `command -v`로 에이전트 실행 파일 존재 확인
6. **프롬프트 전달**: 프롬프트가 있으면 에이전트에 첫 번째 인자로 전달
7. **종료 코드 기반 전환**: exit code 0이면 성공 종료, 그 외는 다음 에이전트로 전환
8. **Rate-limit 감지/복귀**: Claude 출력에서 rate limit 키워드 감지 시 cooldown 설정, 해제 후 자동 복귀

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
3. `generate_shell_functions()` -- claude() 함수

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

`tests/mcp/test_vibe.py`의 `TestGenerateShellFunctions` 클래스:

| 테스트 | 검증 내용 |
|--------|-----------|
| `test_default_priority` | 기본 설정(claude, codex)으로 함수 생성 확인 |
| `test_custom_priority` | 커스텀 우선순위(codex, gemini) 반영 확인 |
| `test_single_agent` | 에이전트 1개일 때 정상 생성 |
| `test_empty_priority` | 빈 리스트이면 빈 문자열 반환 |
| `test_contains_claudecode_guard` | CLAUDECODE 중첩 방지 코드 포함 확인 |
| `test_contains_skip_option` | -N 옵션 파싱 코드 포함 확인 |
| `test_contains_claude_rate_limit_recovery_logic` | rate-limit 감지/복귀 로직 포함 확인 |
| `test_contains_passthrough_guard` | `command claude "$@"` passthrough 코드 포함 확인 |
| `test_contains_run_agent_helper` | `_run_agent()` 헬퍼 함수 포함 확인 |
| `test_passthrough_without_fallback_flag` | `--fallback` 없이 호출 시 원본 바이너리 passthrough 통합 테스트 |
| `test_claude_fallback_switches_to_codex_then_returns_to_claude` | rate-limit → codex 전환 → claude 복귀 통합 테스트 |

## 관련 파일

| 파일 | 역할 |
|------|------|
| `config/settings.yaml` | `agent_priority` 설정 소스 |
| `src/ai_env/core/config.py` | `Settings.agent_priority` Pydantic 모델 |
| `src/ai_env/mcp/vibe.py` | `generate_shell_functions()` 구현 |
| `src/ai_env/mcp/generator.py` | vibe 모듈 호출, shell_exports에 통합 |
| `generated/shell_exports.sh` | 생성된 출력 (gitignore) |
| `tests/mcp/test_vibe.py` | `TestGenerateShellFunctions` 테스트 |

## 제약사항

- bash/zsh 호환 (공식 지원 대상은 bash)
- 에이전트 목록은 생성 시점에 하드코딩됨 (런타임 설정 변경 불가, 재동기화 필요)
- 프롬프트는 단일 문자열로만 전달 (`$*`로 합침)
- `-N` 옵션에서 N은 한 자리 숫자만 지원 (`-[0-9]` 패턴)
- `claude()` 함수가 원본 바이너리를 shadow하므로, 함수 내부에서는 반드시 `command claude`로 호출
