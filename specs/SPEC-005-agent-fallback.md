---
id: SPEC-005
title: Agent Fallback (claude --fallback)
status: implemented
created: 2025-06-01
updated: 2026-03-13
---

# SPEC-005: Agent Fallback (claude --fallback)

## 개요

`claude --fallback`은 `ai-env sync` 실행 시 자동 생성되는 `claude()` bash 쉘 함수를 통해 제공된다. 원본 `claude` 바이너리를 shadow하며, `--fallback` 플래그 없이 호출하면 원본 바이너리로 passthrough한다. `--fallback` 모드에서는 AI 에이전트를 우선순위 순서대로 시도하고, 앞선 에이전트가 비정상 종료(세션 한도 도달, 에러 등)하면 다음 에이전트로 자동 전환한다.

생성된 함수는 `generated/shell_exports.sh`에 환경변수 export 뒤에 추가되며, 사용자가 `source ./generated/shell_exports.sh`로 활성화한다.

## 핵심 유스케이스

Claude Code는 세션당 사용 한도가 있다. 한도에 도달하면 비정상 종료(exit code != 0)되는데, `claude --fallback`이 이를 감지하여 다음 에이전트로 자동 전환한다. 사용자가 수동으로 도구를 바꿀 필요가 없다.

**모델 레벨 fallback**: Opus와 Sonnet은 별도 API quota를 가지므로, Opus가 rate-limit되면 Sonnet을 먼저 시도하고 그것도 소진되면 Codex로 전환한다.

## 설정

### 설정 소스

`config/settings.yaml`의 `agent_priority` 필드:

```yaml
# === Agent 우선순위 (claude --fallback) ===
# claude --fallback이 이 순서대로 에이전트를 시도
# 앞의 에이전트가 세션 한도/에러로 종료되면 다음 에이전트로 자동 전환
# "agent:model" 형식으로 모델 지정 가능 (예: claude:sonnet → claude --model sonnet)
agent_priority:
  - claude           # Opus (default model)
  - claude:sonnet    # Claude with --model sonnet
  - codex
```

### agent:model 문법

`agent:model` 형식으로 동일 에이전트의 다른 모델을 우선순위에 추가할 수 있다:

- `claude` → `claude` 바이너리를 기본 모델(Opus)로 실행
- `claude:sonnet` → `claude --model sonnet`으로 실행
- `claude:haiku` → `claude --model haiku`로 실행

각 엔트리는 독립적인 cooldown을 가진다. Opus가 rate-limit되어도 Sonnet은 별도 quota이므로 계속 사용 가능.

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
            ├─ _parse_agent_entry(agent) → base_agent, model_suffix 추출
            │
            ├─ base_agent == "claude" && entry_cooldown_epochs[i] > now?
            │    → 건너뜀 (이 엔트리의 cooldown 활성)
            │
            ├─ base_agent == "claude" && $CLAUDECODE 설정됨?
            │    → "이미 Claude Code 세션 내부 (건너뜀)" 출력, continue
            │
            ├─ _resolve_bin(base_agent) 실패?
            │    → "설치되지 않음 (건너뜀)" 출력, continue
            │
            ├─ model_suffix 있으면 → --model <suffix> 플래그 주입
            │
            ├─ 에이전트 실행 (script -qF 로 로그 캡처)
            │
            ├─ exit code 0 → return 0 (성공)
            │
            └─ exit code != 0 또는 rate-limit 감지
                 → entry_cooldown_epochs[i] 설정 (per-entry cooldown)
                 → 핸드오프 파일 생성
                 → 다음 에이전트로 계속

  모든 에이전트 소진 또는 사용 가능한 에이전트 없음:
    → 에러 메시지 출력, return 1
```

**모델 fallback 예시** (agent_priority: claude → claude:sonnet → codex):

```
🚀 Starting claude...           # Opus 시작
⚠ claude rate-limit 감지        # Opus rate-limit
🚀 Starting claude (sonnet)...  # Sonnet으로 전환
                                 # Sonnet 성공 → 완료
```

### 주요 로직

1. **Passthrough 가드**: `--fallback` 플래그 없으면 `command claude "$@"`로 원본 바이너리에 모든 인자 전달
2. **`command claude`로 재귀 방지**: `claude()` 함수가 원본 바이너리를 shadow하므로, 내부에서 claude 바이너리 호출 시 반드시 `command claude` 사용
3. **엔트리 파싱**: `_parse_agent_entry()`로 `agent:model` 문법 분석 → `base_agent`와 `model_suffix` 추출
4. **옵션 파싱**: `case` 문으로 `-l`/`--list`(목록 출력)과 `-N`(N순위부터 시작) 처리
5. **Claude Code 중첩 방지**: `base_agent == "claude"` && `$CLAUDECODE` 환경변수 존재이면 건너뜀
6. **설치 확인**: `_resolve_bin(base_agent)`로 에이전트 실행 파일 존재 확인
7. **모델 플래그 주입**: `model_suffix`가 있으면 `--model <suffix>` 플래그를 인자에 선행 추가
8. **종료 코드 기반 전환**: exit code 0이면 성공 종료, 그 외는 다음 에이전트로 전환
9. **Per-entry cooldown**: `entry_cooldown_epochs[]` 배열로 각 엔트리별 독립 cooldown 추적
10. **Rate-limit 감지/복귀**: Claude 출력에서 rate limit 키워드 감지 시 해당 엔트리 cooldown 설정, 해제 후 자동 복귀
11. **3-tier 패턴 계층**: strong(확실한 rate-limit 문구) → strict(exit 0에도 적용) → broad(exit ≠ 0에서만 적용). bare `rate-limit` 등 2-word 패턴은 broad tier에만 포함하여 코드 출력(`rate_limit` 변수명 등) false-positive 방지

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

### `TestGenerateShellFunctions` 클래스 (기존)

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
| `test_passthrough_without_fallback_flag` | `--fallback` 없이 호출 시 원본 바이너리 passthrough 통합 테스트 |
| `test_claude_fallback_switches_to_codex_then_returns_to_claude` | rate-limit → codex 전환 → claude 복귀 통합 테스트 |

### `TestModelLevelFallback` 클래스 (모델 fallback)

| 테스트 | 검증 내용 |
|--------|-----------|
| `test_model_suffix_in_agents_array` | `claude:sonnet`이 agents 배열에 포함 확인 |
| `test_model_suffix_priority_display` | 헤더에 `claude (sonnet)` 형태로 표시 확인 |
| `test_contains_parse_agent_entry_helper` | `_parse_agent_entry` 헬퍼 존재 확인 |
| `test_contains_per_entry_cooldown` | per-entry cooldown 배열 존재 확인 |
| `test_model_flag_injected_for_claude_sonnet` | `--model sonnet` 플래그 주입 통합 테스트 |
| `test_no_model_flag_for_plain_claude` | plain `claude`에는 `--model` 미주입 확인 |
| `test_model_fallback_opus_to_sonnet_to_codex` | Opus rate-limit → Sonnet 성공 전체 경로 테스트 |
| `test_model_fallback_all_claude_rate_limited_then_codex` | Opus + Sonnet 모두 rate-limit → Codex 전환 테스트 |
| `test_model_suffix_auto_mode_injects_skip_permissions` | `claude:sonnet` + `--auto` 플래그 주입 확인 |
| `test_list_display_with_model_suffix` | `-l` 출력에 모델 suffix 표시 확인 |

### `TestCodexTransitionEdgeCases` 클래스 (Codex 전환)

| 테스트 | 검증 내용 |
|--------|-----------|
| `test_claude_crash_no_rate_limit_passes_original_to_codex` | crash(비 rate-limit) 시 원래 프롬프트로 codex 전환 |
| `test_codex_exec_exact_args_structure` | codex exec 인자 구조 정확성 검증 |
| `test_claude_crash_no_prompt_codex_gets_yolo` | 프롬프트 없는 crash → codex --yolo 모드 |
| `test_fallback_with_special_chars_in_prompt` | 특수문자 포함 프롬프트 전달 |
| `test_only_codex_available_claude_not_installed` | Claude 미설치 시 codex만 사용 |
| `test_codex_nonzero_exit_shows_error_and_terminates` | 마지막 에이전트 실패 시 종료 |
| `test_rapid_rate_limit_no_delay_before_codex` | rate-limit 후 즉시 codex 전환 |
| `test_complete_opus_sonnet_codex_flow_with_exec` | Opus → Sonnet → Codex 3단계 degradation |

### `TestRateLimitPatternCoverage` 클래스 (패턴 검증)

| 테스트 | 검증 내용 |
|--------|-----------|
| `test_switch_to_extra_usage` | "switch to extra usage" 메시지 감지 |
| `test_upgrade_your_plan` | "upgrade your plan" 메시지 감지 |
| `test_stop_and_wait_for_limit` | "stop and wait" 메시지 감지 |
| `test_you_have_exhausted` | "you have exhausted" 메시지 감지 |
| `test_too_many_requests` | "too many requests" 메시지 감지 |
| `test_rate_limit_options_with_exit_zero` | exit 0 + `/rate-limit-options` 감지 |
| `test_what_do_you_want_to_do` | "what do you want to do" 메시지 감지 |
| `test_reached_daily_limit` | "reached daily limit" 메시지 감지 |
| `test_exceeded_hourly_limit` | "exceeded hourly limit" 메시지 감지 |
| `test_quota_exceeded` | "quota exceeded" 메시지 감지 |
| `test_no_false_positive_on_normal_output` | 일반 출력 false-positive 방지 |
| `test_no_false_positive_on_limit_in_code` | 코드 출력(`rate_limit`) false-positive 방지 |
| `test_hit_your_limit_resets_with_timezone` | 타임존 포함 limit reset 메시지 감지 |

### `TestHandoffFileIntegrity` 클래스 (핸드오프)

| 테스트 | 검증 내용 |
|--------|-----------|
| `test_handoff_file_contains_required_sections` | 핸드오프 파일 필수 섹션 포함 |
| `test_handoff_original_task_empty_for_interactive` | 대화형 세션 라벨 정확성 |

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
