# Spec Template

아래 형식을 기반으로 스펙 문서를 작성한다.
프로젝트 profile에 커스텀 템플릿이 지정되어 있으면 이 템플릿 대신 사용.

```markdown
---
spec_id: SPEC-NNN
title: "<제목>"
status: planned
created: YYYY-MM-DD
updated: YYYY-MM-DD
source_evidence: []
owners: []
---

# SPEC-NNN: <제목>

## Goal

이 스펙이 달성하려는 목표를 1-3문장으로 기술.

## Scope

구현 범위를 명확하게 정의.

## Non-Goals

이 스펙에서 다루지 않는 것들.

## Data Model

관련 데이터 모델 변경사항 (있는 경우).

## API

API 엔드포인트/인터페이스 변경 (있는 경우).

## Tasks

- [ ] Task NNN-1: <제목>
  - **AC**: <acceptance criteria>
  - **Test**: <테스트 전략>

- [ ] Task NNN-2: <제목>
  - **AC**: <acceptance criteria>
  - **Test**: <테스트 전략>

## Acceptance Criteria

전체 스펙의 AC를 번호로 나열.

1. AC-1: ...
2. AC-2: ...

## Test Plan

테스트 전략 개요.

## Rollout Notes

배포/마이그레이션 관련 참고사항.
```
