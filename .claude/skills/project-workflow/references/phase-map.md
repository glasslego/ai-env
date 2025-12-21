# Phase Map

## Phase → 스킬 매핑

| Phase | 스킬 | 모드 | Gate Check |
|-------|------|------|------------|
| 0 (Init) | project-workflow | Overview | profile 존재 확인 |
| 1 (Research) | research | Research/Brief | 리서치 파일 1개 이상 |
| 2 (Spec) | spec-manager | Create + Task Decompose | SPEC 파일 500자+ |
| 3 (Implement) | task-implement | Implement (순차) | 전체 테스트 통과 |
| 4 (Review) | code-review | Spec Conformance | Must Fix 0건 |
| 5 (Close) | spec-manager | Close | 모든 AC 충족 |
| D (Domain) | 프로젝트 로컬 스킬 | 해당 스킬의 기본 모드 | 스킬별 |

## Phase 전환 조건

```
intake → research:      리서치 시작 시
research → spec:        리서치 자료 충분 + Brief 생성
spec → implementing:    SPEC + Tasks 완성
implementing → review:  모든 task 완료 (체크박스 전부 [x])
review → done:          Must Fix 0건
```

## 상태 파일 위치

- 프로젝트 루트: `_project-status.yaml`
- 코드 체크포인트: `_code-status.yaml`
- 리뷰 결과: `_project-status.yaml`의 `reviews` 섹션

## project-profile.yaml 스키마

```yaml
project:
  name: string          # 프로젝트 이름 (필수)
  type: enum            # api-server | library | data-pipeline | cli-tool
  description: string   # 프로젝트 설명

architecture:
  pattern: enum         # 3-layer | hexagonal | monolith | microservice
  layers: dict          # 레이어별 디렉토리 매핑

specs:
  directory: string     # 스펙 디렉토리 (기본: specs/)
  format: string        # 스펙 파일 형식 (기본: SPEC-NNN)
  template: string?     # 커스텀 템플릿 경로
  plan_file: string?    # 전체 plan 추적 파일

tests:
  framework: string     # pytest | jest | go-test
  command: string       # 테스트 실행 명령
  lint_command: string? # 린트 명령

status:
  file: string          # 상태 파일 경로 (기본: _project-status.yaml)

domain_ops:             # 프로젝트 고유 ops (선택)
  - skill: string       # 로컬 스킬 이름
    phase: string       # 워크플로우 내 위치
    description: string # 설명

research:               # 리서치 소스 (선택)
  obsidian_base: string?  # Obsidian vault 상대 경로
  sources_dir: string?    # 프로젝트 내 리서치 디렉토리
```
