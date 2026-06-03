---
name: session-save
description: |
  스킬/대화 도중 현재 세션 컨텍스트를 Obsidian vault에 마크다운 노트로 저장.
  사용자가 "세션 저장", "옵시디언에 저장", "session save", "obsidian 저장",
  "지금까지 정리해줘", "결정사항 노트로 남겨" 등을 요청하면 트리거.
  `ai-env session save` CLI를 호출하므로 Claude Code와 Codex 양쪽에서 동작한다.
---

# Session Save

현재 세션의 핵심 컨텍스트(사용자 결정·진행 메모·git 상태)를 Obsidian vault에
영구 저장하는 스킬. 다음 세션 인계용인 `/handoff`와 달리, 외부 노트로 내보내
검색·연결 가능한 형태로 보존한다.

## 트리거 키워드

- "세션 저장", "session save", "옵시디언 저장", "obsidian 저장"
- "지금까지 정리해줘", "결정사항 노트로 남겨"
- "/session-save"

## 사용 시점

- 긴 대화 도중 의미 있는 결정/구현이 정리되어, 다른 곳에서 참조할 가능성이 있을 때
- 다른 작업으로 컨텍스트 전환하기 전 체크포인트
- /handoff 보다 풍부한 본문(아키텍처 결정, 리뷰 결과 등)을 외부 vault에 보관할 때

## 동작 단계

### Step 1: 메모 후보 작성

다음 정보를 머릿속에 정리하고, 한 단락(최대 8~12줄)의 메모로 압축한다:

1. 이번 세션에서 수행한 작업 (구현/리뷰/리서치/디버깅 등)
2. 핵심 결정과 그 근거
3. 남은 TODO와 후속 액션
4. 사용자가 강조한 제약/선호

### Step 2: 사용자 확인

압축한 메모를 사용자에게 제시하고 "이 내용으로 저장할까요?"로 짧게 확인.
사용자가 다른 제목·디렉토리를 원하면 옵션을 받는다.

### Step 3: CLI 호출

`ai-env session save`로 노트를 저장한다. 메모는 반드시 `--note`로 전달:

```bash
uv run ai-env session save \
    --note "이번 세션 메모 내용 (한 단락)" \
    --title "이번 세션 제목 (옵션)" \
    --subdir 00_session
```

옵션:

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--note` / `-n` | (없음) | 본문에 들어가는 사용자 메모. 권장. |
| `--title` / `-t` | `{HHMM} {branch}` | 노트 제목 |
| `--vault` | `settings.yaml`의 `obsidian_base` | Obsidian vault 루트 |
| `--subdir` | `00_session` | vault 내부 디렉토리 |
| `--dry-run` | false | 본문만 미리보기 |

### Step 4: 결과 보고

저장된 파일 경로를 사용자에게 보고하고, vault에서 확인 가능함을 알린다.

## 절대 금지

- 사용자에게 확인 없이 자동으로 저장하지 않는다 (메모 내용 검증 후 진행).
- vault 경로를 추측하지 않는다 — `settings.yaml` 또는 `--vault` 인자만 사용.
- `--note`를 비워둔 채 저장하지 않는다 (의미 없는 노트 양산 방지).

## Codex에서의 사용

이 스킬은 CLI에 의존하므로 Codex CLI에서도 동일하게 동작한다.
Codex는 `~/.codex/skills/session-save/SKILL.md`를 자동으로 읽고, 동일한
`uv run ai-env session save` 명령을 실행한다.
