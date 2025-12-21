---
id: SPEC-011
title: AI 코딩 에이전트 인프라 강화 — 프로젝트 프로파일, 커버리지, CI, 보안
status: implemented
created: 2026-03-13
updated: 2026-03-13
---

# SPEC-011: AI 코딩 에이전트 인프라 강화

## 1. 배경

ai-env 레포를 AI 코딩 에이전트 효율성 관점에서 평가한 결과 **74/100**점.
주요 갭: project-profile.yaml 부재(스킬 컨텍스트 누락), 커버리지 미측정,
gitleaks 미적용(CLAUDE.md 권장 vs 미구현), CI/CD 완전 부재.

claude-plugin 레포 참조 결과 도입할 패턴:
- project-profile.yaml (스킬/커맨드 자동 컨텍스트)
- GitHub Actions CI (테스트+린트 자동화)

## 2. Task 목록

### Task-01: .claude/project-profile.yaml 생성

스킬들이 `project-profile.yaml`을 참조해 프로젝트 컨텍스트를 자동 로드하지만,
현재 파일이 존재하지 않아 모든 스킬이 fallback 동작.

**AC:**
- [ ] `.claude/project-profile.yaml` 생성 (프로젝트 메타, 스펙 경로, 테스트/린트 명령, 아키텍처)
- [ ] git 추적 대상 (gitignore에 없어야 함)

### Task-02: pytest-cov 커버리지 설정

`pytest-cov`가 dev 의존성에 있지만 설정이 없어 커버리지를 측정하지 않음.

**AC:**
- [ ] pyproject.toml에 `[tool.coverage.run]`/`[tool.coverage.report]` 설정
- [ ] 최소 커버리지 임계값 설정 (75%)
- [ ] `uv run pytest --cov` 동작 확인

### Task-03: gitleaks pre-commit hook 추가

CLAUDE.md에서 gitleaks 권장하지만 `.pre-commit-config.yaml`에 미등록.

**AC:**
- [ ] `.pre-commit-config.yaml`에 gitleaks hook 추가
- [ ] `pre-commit install` 후 동작 확인

### Task-04: GitHub Actions CI workflow

원격 품질 게이트가 전무함. 로컬 pre-commit만으로는 팀 수준 품질 보장 불가.

**AC:**
- [ ] `.github/workflows/ci.yml` 생성 (test + lint + type-check)
- [ ] push/PR 트리거

### Task-05: .gitignore 보강 및 stale worktree 정리

`.claude/worktrees/`가 gitignore에 없어 stale worktree가 untracked로 노출.

**AC:**
- [ ] `.gitignore`에 `.claude/worktrees/` 추가
- [ ] stale worktree 정리

## 3. Out of Scope

- Convention reference files (python-conventions.md 등) — 별도 스펙
- Plugin marketplace 배포 — 별도 스펙
- Security audit (glocal.json 토큰) — 별도 작업

## 4. 구현 순서

Task-01 → Task-02 → Task-03 → Task-04 → Task-05 (순차)
