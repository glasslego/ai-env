# Commit by Spec Task
---
description: Spec Task 단위로 테스트 통과 후 커밋합니다
---

## 수행 단계

1. **Spec/Task 식별**
- 이번 커밋이 어떤 Spec의 어떤 Task인지 먼저 확정한다.
- 식별자가 없으면 커밋하지 않고 먼저 정리한다.

2. **변경사항 확인**
   ```bash
   git status
   git diff --cached
   ```

3. **테스트 실행 (필수)**
- Task와 연관된 테스트를 실행하고 통과를 확인한다.
- 실패 상태에서는 커밋하지 않는다.

4. **커밋 메시지 생성**
   - 변경 내용 분석
   - Conventional Commits + spec/task 식별자 포함
   - feat/fix/refactor/docs/chore 등 적절한 타입 선택
   - 권장 형식:
     - `<type>(spec-<id>/task-<id>): <summary>`
     - 예: `feat(spec-003/task-02): add team skills include filter`

5. **CLAUDE.md 업데이트 필요성 검토**
   다음 경우 CLAUDE.md 업데이트:
   - 새로운 디렉토리 구조 추가
   - 새로운 라이브러리/도구 도입
   - 새로운 패턴/규칙 발견
   - 중요한 아키텍처 변경

6. **커밋 실행**
   ```bash
   git add .
   git commit -m "<type>(spec-<id>/task-<id>): <description>"
   ```

7. **결과 보고**
   - 커밋 해시
   - Spec/Task 식별자
   - 실행한 테스트와 결과
   - 변경된 파일 수
   - CLAUDE.md 업데이트 여부
