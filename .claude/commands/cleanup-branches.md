# Cleanup Branches
---
description: 병합된 Git 브랜치를 정리합니다
---

## 수행 단계

1. **로컬 브랜치 조회**
   ```bash
   git branch --merged main | grep -v "main\|master\|develop"
   ```

2. **삭제 대상 확인**
   - 병합 완료된 브랜치 목록 표시
   - 사용자 확인 요청

3. **로컬 브랜치 삭제**
   ```bash
   git branch -d <branch_name>
   ```

4. **원격 브랜치 정리**
   ```bash
   git remote prune origin
   ```

5. **결과 보고**
   - 삭제된 브랜치 수
   - 남아있는 브랜치 목록
