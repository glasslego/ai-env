---
name: second-opinion
description: 현재 git diff (브랜치 vs base) 에 대해 Codex CLI 로 두 번째 의견을 받음. 사용자가 "/2nd", "second opinion", "교차 검증", "코덱스로 봐줘" 를 말하면 트리거. Gemini 는 의도적으로 제외 (megan 정책 — Gemini 는 웹만 사용).
---

# Code Second Opinion

> Origin: jackie-skills/code-second-opinion. **Codex CLI 한정** 으로 단순화.
>
> 전제: `codex` CLI 가 사용자 머신에 이미 설치/인증됨. 이 스킬은 자격증명 관리 X.

## When to invoke

- 사용자가 "/2nd", "second opinion", "교차 검증", "코덱스로 리뷰"
- 큰 PR push / merge 직전 자기 검증

## 동작

```
git merge-base HEAD <base>
        ↓
git diff $(merge-base)..HEAD
        ↓
codex exec -c "approval_policy='never'" -s read-only "리뷰 프롬프트 + diff"
        ↓
응답을 콘솔 + (옵션) ~/Documents/Obsidian Vault/90_journal/04_sessions/{date}-2nd.md
```

## 실행

```bash
~/.claude/skills/second-opinion/scripts/review.sh
# 옵션
--base BRANCH        # 기본 main (또는 master 자동 탐지)
--save               # 결과를 vault session 노트로 저장
--max-bytes N        # diff 가 너무 크면 자르기 (기본 80KB)
```

## 리뷰 프롬프트 (고정 템플릿)

```
당신은 시니어 코드 리뷰어. 다음 git diff 에서 다음을 식별:
1. 명백한 버그 / 회귀 위험
2. 보안 위협 (입력 검증, 인증, secret 노출)
3. 테스트 누락
4. 명명/구조 개선 제안 (낮은 우선순위)

severity 별로 묶어 출력 (HIGH / MEDIUM / LOW).
```

## 토큰 예산

diff 가 80KB 초과 시 자르기. 큰 PR 은 파일별 분할 리뷰 권장 (`--by-file` 추후 P4.5).
