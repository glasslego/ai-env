# Spec Frontmatter Schema

## 필수 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `spec_id` | string | `SPEC-NNN` 형식 (프로젝트 내 유일) |
| `title` | string | 스펙 제목 |
| `status` | enum | `planned`, `in_progress`, `review_required`, `done`, `blocked` |
| `created` | date | 생성일 (YYYY-MM-DD) |
| `updated` | date | 최종 수정일 (YYYY-MM-DD) |

## 선택 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `source_evidence` | list[string] | 리서치 근거 파일 목록 |
| `owners` | list[string] | 담당자 |
| `priority` | enum | `P0`, `P1`, `P2` |
| `depends_on` | list[string] | 선행 스펙 ID 목록 |

## 상태 전환

```
planned ──→ in_progress ──→ review_required ──→ done
                 ↑                  |
                 └── blocked ←──────┘
```

- `planned → in_progress`: task 구현 시작 시
- `in_progress → review_required`: 모든 task 구현 완료 시
- `review_required → done`: 리뷰 통과 (Must Fix 0건) 시
- `* → blocked`: 외부 의존성/이슈 발생 시
- `blocked → in_progress`: 블로커 해결 시
