# config/topics — 리서치 토픽 가이드

토픽(Topic)은 6-Phase 워크플로우의 시작점이다.
`topic.yaml` 하나로 리서치 쿼리·심층리서치 프롬프트·Spec 생성·코드 생성까지 전체를 정의한다.

---

## 디렉토리 구조

```
config/topics/
└── {topic-id}/               ← 토픽 ID (kebab-case)
    ├── topic.yaml            ← 필수: 토픽 정의
    ├── {name}.md             ← 선택: Gemini 심층리서치 프롬프트 (frontmatter 방식)
    └── {name}.md             ← 선택: GPT 심층리서치 프롬프트 (frontmatter 방식)
```

> **레거시 포맷**: `config/topics/{topic-id}.yaml`도 지원하나, 신규 토픽은 디렉토리 방식을 사용한다.

---

## topic.yaml 스키마

```yaml
# ── 토픽 기본 정보 (필수) ──────────────────────────────────────
topic:
  id: my-topic                          # 필수: kebab-case, CLI에서 사용
  name: "내 토픽 이름"                   # 필수: 한글 표시명
  obsidian_base: "폴더/하위폴더"          # 필수: Obsidian vault 기준 상대경로
  project_repo: ~/work/path/to/repo     # 선택: 코드 생성 대상 리포지토리

# ── 3-Track 리서치 (선택, 기본값: 빈 목록) ──────────────────────
research:
  # Track A: Claude Code 자동 실행 (brave-search + web_fetch)
  auto:
    - query: "검색 쿼리 (영어 권장)"
      output: "07_참고/auto-파일명.md"  # obsidian_base 기준 상대경로

  # Track B: Gemini 심층리서치 (API 자동 또는 웹 수동)
  # ※ 프롬프트는 topic 폴더의 .md 파일로 분리하는 것을 권장 (아래 참조)
  gemini_deep:
    - prompt: "리서치 프롬프트 (멀티라인 가능)"
      output: "07_참고/gemini-파일명.md"
      focus: "조사 초점 태그 (선택)"    # 상태 파일에 표시됨

  # Track C: GPT 심층리서치 (API 자동 또는 웹 수동)
  gpt_deep:
    - prompt: "리서치 프롬프트"
      output: "07_참고/gpt-파일명.md"
      focus: "조사 초점 태그 (선택)"

# ── Plan/Spec 생성 (선택, /wf-spec 실행에 필요) ─────────────────
plan:
  synthesis_prompt: |                   # 필수: 리서치 → Spec 변환 지침
    리서치 자료를 읽고 다음을 작성해줘.
    1. 시스템 아키텍처
    2. 기술 스택
    ...
  output: "01_폴더/plan-spec.md"        # 필수: Spec 저장 경로 (obsidian_base 기준)

# ── 코드 생성 (선택, /wf-code 실행에 필요) ──────────────────────
code:
  style: tdd                            # 선택: "tdd" (기본값)
  target_repo: ~/work/path/to/repo      # 선택: 기본값은 topic.project_repo
  test_framework: pytest                # 선택: "pytest" (기본값)
  modules:                              # 필수 (code 섹션 있을 때): 구현할 모듈 목록
    - name: "module_name"               # Python 모듈명 (snake_case)
      desc: "모듈 설명 (한 줄)"

# ── 워크플로우 확장 (선택) ────────────────────────────────────────
workflow:
  obsidian_structure: standard          # 선택: "standard" (기본값) | "flat" | "custom"
  enable_adr: true                      # 선택: ADR 자동 생성 여부 (기본값: true)
  enable_review: true                   # 선택: Review Phase 활성화 (기본값: true)
  review_prompts: []                    # 선택: 커스텀 리뷰 프롬프트 목록
```

---

## 필드 상세

### `topic` (필수)

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `id` | string | ✅ | 토픽 고유 ID. kebab-case. CLI 커맨드에서 사용 (`/wf-init my-topic`) |
| `name` | string | ✅ | 사람이 읽는 표시명. 상태 파일·문서 제목에 사용 |
| `obsidian_base` | string | ✅ | Obsidian vault 루트 기준 상대경로. 모든 output 경로의 기준점 |
| `project_repo` | string | - | 코드를 생성할 로컬 리포지토리 경로. `~` 확장 지원 |

### `research` (선택)

#### `research.auto` — Track A

자동 웹검색. `/wf-research` 실행 시 Claude Code가 `brave-search` + `web_fetch`로 직접 수행한다.

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `query` | string | ✅ | 검색 쿼리. 영어 쿼리가 결과 품질이 좋음 |
| `output` | string | ✅ | 저장 경로 (`obsidian_base` 기준). `auto-` 접두사 권장 |

> **파일명 규칙**: `auto-`로 시작해야 Track A로 자동 분류된다.

#### `research.gemini_deep` / `research.gpt_deep` — Track B/C

심층리서치. API 키 있으면 자동 실행, 없으면 프롬프트 파일 생성 후 수동 실행 안내.

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `prompt` | string | ✅ | 리서치 프롬프트 전문 |
| `output` | string | ✅ | 저장 경로. `gemini-` 또는 `gpt-` 접두사 권장 |
| `focus` | string | - | 조사 초점 설명. 상태 파일에 태그로 표시됨 |

> **권장**: 프롬프트가 길면 `topic.yaml`에 인라인하지 말고 `.md` 파일로 분리한다 (아래 참조).

### `plan` (선택, `/wf-spec` 필요)

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `synthesis_prompt` | string | ✅ | 리서치 자료 → Spec 변환 지침. 멀티라인 `|` 블록 권장 |
| `output` | string | ✅ | Spec 파일 저장 경로 (`obsidian_base` 기준) |

### `code` (선택, `/wf-code` 필요)

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `style` | string | `"tdd"` | 코딩 스타일. 현재 `"tdd"` 지원 |
| `target_repo` | string | `topic.project_repo` | 코드 생성 대상 경로 |
| `test_framework` | string | `"pytest"` | 테스트 프레임워크 |
| `modules` | list | `[]` | 구현 모듈 목록. 순서대로 순차 생성됨 |
| `modules[].name` | string | — | Python 모듈명 (snake_case) |
| `modules[].desc` | string | — | 모듈 역할 설명 |

### `workflow` (선택)

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `obsidian_structure` | string | `"standard"` | 폴더 구조 유형 |
| `enable_adr` | bool | `true` | `/wf-spec` 시 ADR 자동 생성 여부 |
| `enable_review` | bool | `true` | `/wf-review` Phase 활성화 여부 |
| `review_prompts` | list[string] | `[]` | 커스텀 리뷰 체크리스트 항목 |

---

## 심층리서치 프롬프트 파일 (권장 방식)

프롬프트가 길거나 여러 개인 경우, `topic.yaml` 인라인 대신 `.md` 파일로 분리한다.
`topic.yaml`의 `gemini_deep`/`gpt_deep`을 비워두고, 아래 형식의 `.md` 파일을 토픽 폴더에 넣으면 자동으로 로드된다.

### 파일 형식

```markdown
---
track: gemini          # 필수: "gemini" 또는 "gpt"
output: "07_참고/gemini-파일명.md"   # 필수: Obsidian 저장 경로
focus: "조사 초점 설명"              # 선택: 상태 파일에 표시
---

여기에 리서치 프롬프트를 자유롭게 작성한다.
마크다운 사용 가능.
```

### 파일명 규칙

- 자유롭게 작성 가능 (`gemini-trend-analysis.md`, `gpt-quant-strategy.md` 등)
- `README.md`는 로드에서 제외됨

### topic.yaml vs .md 파일 우선순위

| 상황 | 동작 |
|------|------|
| `topic.yaml`에 `gemini_deep` 항목이 있음 | YAML 항목 사용 |
| `topic.yaml`은 비어있고 `.md` 파일이 있음 | `.md` 파일 로드 |
| 둘 다 있음 | YAML 항목 우선 (`.md` 파일 무시) |

---

## 파일명 접두사 규칙

Obsidian의 리서치 파일은 접두사로 Track을 자동 분류한다.

| 접두사 | Track | 예시 |
|--------|-------|------|
| `auto-` | Track A (Claude 자동검색) | `auto-ccxt-best-practices.md` |
| `gemini` | Track B (Gemini 심층리서치) | `gemini-trend-analysis.md` |
| `gpt` | Track C (GPT 심층리서치) | `gpt-quant-strategy.md` |
| 기타 | Manual (수동 리서치) | `reference-paper.md` |
| `_` 시작 | 시스템 파일 (제외) | `_research-status.md` |

---

## Phase별 필요 섹션

| Phase | 커맨드 | 필요한 섹션 |
|-------|--------|------------|
| 0: Intake | `/wf-init` | `topic` |
| 1: Research | `/wf-research` | `topic` + `research` (auto/gemini_deep/gpt_deep 중 하나 이상) |
| 2: Spec Freeze | `/wf-spec` | `topic` + `plan` + 리서치 결과 파일 |
| 3: Implement | `/wf-code` | `topic` + `plan` + `code` (modules 필수) |
| 4: Review | `/wf-review` | `topic` + `plan` (Spec 파일 존재) |

---

## 예시: 최소 구성 (리서치만)

```yaml
topic:
  id: my-research
  name: "내 리서치 주제"
  obsidian_base: "10_연구/내주제"

research:
  auto:
    - query: "my topic best practices 2025"
      output: "07_참고/auto-best-practices.md"
```

## 예시: 전체 구성

`config/topics/bitcoin-automation/topic.yaml` 참고.

---

## 새 토픽 추가 방법

```bash
# 1. 토픽 디렉토리 생성
mkdir config/topics/my-topic

# 2. topic.yaml 작성
# (이 README 스키마 참고)

# 3. (선택) 심층리서치 프롬프트 .md 파일 추가

# 4. 등록 확인
uv run ai-env pipeline list
uv run ai-env pipeline info my-topic

# 5. 워크플로우 시작
uv run ai-env pipeline scaffold my-topic
# 또는
claude "/wf-init my-topic"
```
