# Fix GitHub Issue
---
description: GitHub 이슈를 분석하고 해결한 후 PR을 생성합니다
---

## 입력
- $ISSUE_NUMBER: GitHub 이슈 번호

## 수행 단계

1. **이슈 분석**
   - GitHub MCP로 이슈 내용 조회
   - 관련 코드 파일 파악
   - 재현 단계 확인

2. **브랜치 생성**
   ```bash
   git checkout -b fix/issue-$ISSUE_NUMBER
   ```

3. **코드 수정**
   - 문제 원인 파악
   - 최소한의 변경으로 해결
   - 테스트 코드 추가/수정

4. **검증**
   ```bash
   pytest tests/ -v
   pre-commit run --all-files
   ```

5. **커밋 & PR**
   ```bash
   git add .
   git commit -m "fix: resolve issue #$ISSUE_NUMBER"
   git push origin fix/issue-$ISSUE_NUMBER
   ```
   - PR 생성 (이슈 링크 포함)

6. **결과 보고**
   - 변경된 파일 목록
   - 해결 방법 설명
   - PR 링크
