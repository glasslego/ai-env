---
name: distill
description: 길어진 세션 트랜스크립트(jsonl) 또는 임의 텍스트를 vault 의 정돈된 마크다운 노트로 압축. 사용자가 "이 세션 정리해줘", "/distill", "distill", "transcript 정리" 를 말하면 트리거. 외부 LLM 호출 없이 결정적 필터로 본문을 줄이고, 압축은 in-conversation Claude/Codex 가 직접 수행.
---

# Distill

> Origin: jackie-skills/distill. 외부 `claude -p` headless 호출은 선택지로 두되, 기본은
> in-conversation 압축으로 토큰을 더 효율적으로 사용한다.

## When to invoke

- 사용자가 "/distill <prefix>" 또는 "이 archive 정리해줘"
- auto-session-archive 가 raw jsonl 을 큐에 넣고 distill 요청
- 긴 텍스트(웹 페이지·로그)를 세션 노트로 정리 요청

## 동작 (2단계)

### 1) 결정적 전처리 (filter_transcript.py)

```bash
~/.claude/skills/distill/scripts/filter_transcript.py <jsonl-path-or-prefix>
```

- `~/Documents/Obsidian Vault/99_archive/sessions/*.jsonl` 또는 prefix 매칭
- user/assistant 텍스트만 추출 (tool_use, tool_result, system 제외)
- turn 당 2KB 제한, 100 turn 초과 시 마지막 100 만
- stdout 으로 정제된 plain text (마크다운 ready)

### 2) 압축 (in-conversation)

전처리 결과를 Claude/Codex 가 직접 읽고 다음 형식으로 vault 에 저장:

```
~/Documents/Obsidian Vault/90_journal/04_sessions/{YYYY-MM}/{YYYY-MM-DD-HHMM}-{slug}.md
```

frontmatter:
```yaml
---
date: 2026-05-06
type: session
source: distill
tags: [session]
---
```

본문 섹션:
- `## TL;DR` — 한 줄
- `## 결정사항` — bullet
- `## 작업 / 결과` — bullet
- `## 미완 / TODO` — bullet
- `## 참고` — wikilink/외부 링크

## 옵션 (filter_transcript.py)

```
--turn-limit 100      # 최대 turn 수 (기본 100)
--turn-bytes 2048     # turn 당 최대 바이트 (기본 2KB)
--latest              # _archive/sessions/ 에서 최신 jsonl 자동 선택
--utc-to-kst          # jsonl 첫 timestamp(UTC) 를 KST 로 출력 (헤더용)
```

## 외부 headless 모드 (선택)

토큰을 절약하지 않고 별도 quota 로 처리하고 싶을 때:

```bash
claude -p "다음 트랜스크립트를 megan vault (90_journal/04_sessions) 컨벤션으로 정리하고 경로 출력." < $FILTERED
```

기본 권장은 in-conversation. headless 는 cron / 백그라운드 distill 에만.
