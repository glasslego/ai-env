---
id: SPEC-010
title: AI 코딩 에이전트 효율성 개선 — 코드 중복 제거, 문서 동기화, 패턴 개선
status: implemented
created: 2026-03-12
updated: 2026-03-12
---

# SPEC-010: AI 코딩 에이전트 효율성 개선

## 1. 배경

ai-env는 여러 AI 코딩 에이전트(Claude, Codex, Gemini)의 설정을 통합 관리하는 도구다.
코드가 성장하면서 아래 비효율이 누적됨:

1. **코드 중복**: backup/replace 패턴 3곳, rmtree+copytree 패턴 4곳 반복
2. **문서 불일치**: SPEC 문서가 현재 코드를 반영하지 못함 (SPEC-009 미등록, Codex skills 스펙 부재)
3. **비효율적 패턴**: secrets.py의 O(n*m) 템플릿 치환
4. **모듈 위치 부적절**: codex_skills.py가 스펙 없이 존재, ENV_KEY_MAPPING 위치

## 2. Task 목록

### Task-01: project_sync.py 중복 backup/replace 로직 통합

`_replace_with_symlink`, `_replace_with_copy`, `_sync_codex_skills`에서 반복되는
backup + removal 로직을 공통 함수 `_prepare_target`으로 추출한다.

**AC:**
- [ ] `_prepare_target(target, dry_run) -> Path | None` 헬퍼 추출
- [ ] 3개 함수에서 호출하도록 리팩터
- [ ] 기존 테스트 통과

### Task-02: sync.py 중복 rmtree+copytree 패턴 통합

`_sync_subdirectories`, `_sync_directory`, `_sync_skills_merged`, `codex_skills.copy_skill_tree_for_codex`에서
반복되는 `if exists: rmtree; copytree` 패턴을 `safe_copytree` 유틸로 추출한다.

**AC:**
- [ ] `safe_copytree(src, dst)` 유틸 함수 추출 (core 내)
- [ ] 4곳에서 호출하도록 리팩터
- [ ] 기존 테스트 통과

### Task-03: secrets.py 템플릿 치환 최적화

O(n*m) 루프 방식을 regex 단일 패스로 교체한다.

**AC:**
- [ ] `re.compile(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}')` 사용
- [ ] 기존 substitute 테스트 통과
- [ ] os.environ fallback 유지

### Task-04: 스펙 문서-코드 동기화

- SPEC-001 아키텍처 다이어그램에 Codex Desktop, Codex local 추가
- SPEC-006에 codex_skills.py (Codex YAML frontmatter 정규화) 반영
- SPEC-009를 specs/README.md에 등록
- specs/README.md의 날짜 갱신

**AC:**
- [ ] SPEC-001 아키텍처 다이어그램 업데이트
- [ ] SPEC-006에 Codex skills normalization 섹션 추가
- [ ] SPEC-009 README 등록
- [ ] 날짜 정합성 확인

## 3. Out of Scope

- vibe.py bash 코드 외부 파일 분리 (별도 스펙으로)
- Project sync 양방향 지원 (별도 스펙으로)
- MCP generator codex_global/codex_local 분리 (현재는 의도적으로 동일)

## 4. 구현 순서

Task-01 → Task-02 → Task-03 → Task-04 (순차)
