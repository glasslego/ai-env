# Git Worktree Skill
---
name: git-worktree
description: |
  병렬 작업을 위한 Git worktree 활용 가이드.
  Auto-apply when working on multiple branches.
---

# Git Worktree 활용 가이드

## 기본 명령어

### Worktree 생성
```bash
# 기존 브랜치로 생성
git worktree add ../project-feature-a feature/feature-a

# 새 브랜치 생성하며
git worktree add -b feature/new ../project-new
```

### 목록 확인
```bash
git worktree list
```

### 제거
```bash
git worktree remove ../project-feature-a
git worktree prune  # 정리
```

## 병렬 Claude Code 세션

```bash
# 이슈별 worktree 생성
git worktree add -b fix/issue-123 ../proj-123
git worktree add -b fix/issue-456 ../proj-456

# 각 폴더에서 Claude Code 실행
cd ../proj-123 && claude
cd ../proj-456 && claude
```

## 디렉토리 구조
```
~/work/
├── my-project/           # 메인 (main)
├── my-project-issue-123/ # worktree
└── my-project-issue-456/ # worktree
```

## iTerm + tmux 연동
```bash
tmux -CC  # iTerm과 연동된 tmux 세션
```
