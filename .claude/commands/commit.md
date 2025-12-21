# Commit with CLAUDE.md Update
---
description: 변경사항을 커밋하고 필요시 CLAUDE.md도 업데이트합니다
---

## 수행 단계

1. **변경사항 확인**
   ```bash
   git status
   git diff --cached
   ```

2. **커밋 메시지 생성**
   - 변경 내용 분석
   - Conventional Commits 형식으로 메시지 작성
   - feat/fix/refactor/docs/chore 등 적절한 타입 선택

3. **CLAUDE.md 업데이트 필요성 검토**
   다음 경우 CLAUDE.md 업데이트:
   - 새로운 디렉토리 구조 추가
   - 새로운 라이브러리/도구 도입
   - 새로운 패턴/규칙 발견
   - 중요한 아키텍처 변경

4. **커밋 실행**
   ```bash
   git add .
   git commit -m "<type>: <description>"
   ```

5. **결과 보고**
   - 커밋 해시
   - 변경된 파일 수
   - CLAUDE.md 업데이트 여부
