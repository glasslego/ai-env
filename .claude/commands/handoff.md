# Handoff
---
description: 현재 세션의 작업 컨텍스트를 .claude/handoff/latest.md에 저장합니다. 다음 세션에서 자동 로드됩니다.
---

## 수행 단계

1. `.claude/handoff/` 디렉토리가 없으면 생성 (archive/ 포함)
2. 기존 `latest.md`가 있으면 `archive/` 디렉토리로 이동 (파일명: `{date}_{session_id_8자}.md`)
3. 현재 세션의 작업 내용을 분석하여 아래 형식으로 `.claude/handoff/latest.md` 작성:

```markdown
# Handoff: {project_name}
- Date: {YYYY-MM-DD HH:MM}
- Branch: {current_branch}

## 진행 중이던 작업
- (이번 세션에서 수행한 주요 작업 2-5줄 요약)

## 다음 해야 할 것
- (미완료 작업, 다음 단계, 남은 TODO)

## 주요 결정/변경사항
- (아키텍처 결정, 중요 파일 변경, 사용자 확인 사항 등)

## 변경된 파일
- (git diff --stat 결과 요약)
```

4. 작성 완료 후 "Handoff 저장 완료: .claude/handoff/latest.md" 메시지 출력

## 주의사항
- handoff 파일은 다음 세션 시작 시 session_start hook이 자동으로 Claude에게 전달한다
- archive/에는 최근 10개만 유지 (오래된 것부터 삭제)
- `.claude/handoff/`는 `.gitignore`에 포함되어 커밋되지 않는다
