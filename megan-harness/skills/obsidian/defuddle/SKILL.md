---
name: defuddle
description: 웹 페이지 또는 임의 HTML 을 토큰 효율적인 마크다운으로 정제 (광고/사이드바/푸터 제거). 사용자가 "/defuddle <URL>", "이 URL 정제", "기사 마크다운 으로", "웹페이지 노트로" 를 말하면 트리거. 결과는 옵시디언 노트로 저장 가능.
---

# Defuddle

> Origin: kepano/obsidian-skills 의 defuddle 컨셉. megan 환경에서는 ① readability 알고리즘
> 로컬 구현 (Python `readability-lxml` 또는 `trafilatura`), ② 결과를 vault 의 inbox 또는
> session 노트로 저장.

## When to invoke

- "/defuddle https://...", "이 URL 정리해서 노트로"
- 큰 웹 페이지 인용 전 토큰 절감
- autoresearch 등 후속 스킬의 전처리

## 동작

```
URL → fetch (curl) → readability/trafilatura 추출 → markdown 변환 → 출력 / vault 저장
```

## 의존성

다음 중 하나가 설치되어 있어야 함 (사용자 책임):

| Tool | 설치 |
|---|---|
| `trafilatura` (권장) | `uv tool install trafilatura` 또는 `pipx install trafilatura` |
| `readability-lxml` | `uv tool install readability-lxml` |
| `pandoc` (fallback) | brew/apt |

스크립트는 위 순서로 자동 폴백.

## 실행

```bash
~/.claude/skills/defuddle/scripts/defuddle.sh https://example.com/article
# 옵션
--save SLUG          # 결과를 vault 00_inbox/{date}-{slug}.md 로 저장
--save-to PATH       # 저장 경로 직접 지정
--no-images          # 이미지 wikilink 제거
--max-bytes N        # 출력 본문 컷오프 (기본 30KB)
```

## 출력

```markdown
---
date: 2026-05-06
type: web
source: https://example.com/article
tags: [defuddle, web]
---

# {추출된 제목}

> 출처: [link](url)
> 추출: trafilatura | 2026-05-06 KST

{정제된 본문}
```
