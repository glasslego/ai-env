# 스킬 토큰 효율화 분석 — cde-skills / cde-ranking-skills / jackie-skills / megan-skills

> 작성일: 2026-05-31 · 작성자: megan (개인 분석용) · 상태: **분석/계획 only — 코드·sync 변경 없음**
> 목적: 4개 스킬 소스를 어떻게 나눠 쓰면 토큰을 아끼는지, 특히 중복 스킬을 어떻게 관리할지 정리.

---

## 0. TL;DR (결론 먼저)

1. **jackie-skills 는 현재 설치돼 있지 않다.** `~/.claude/plugins` 에 흔적 없음. → megan-skills 가 jackie 패턴에서 **파생된 fork** 이고, 둘이 동시에 컨텍스트에 올라오는 게 아니다. "megan ↔ jackie 중복"은 *런타임 토큰 비용*이 아니라 *유지보수 중복*의 문제다.
2. **진짜 런타임 낭비는 "이중 등록"이다.** `~/.claude/skills/`(personal)와 프로젝트 `.claude/skills/`(project)에 **같은 스킬 12개가 중복 배포**돼 매 세션 description 이 2번씩 로드된다 (세션 시작 system-reminder 에서 `code-review`, `doc-sync`, `harness`, `research`, `session-save`, `spec-manager`, `task-implement` 등이 2번씩 보이는 이유).
3. **ES 접근이 3계층 중첩** (`es-query` / `es-gift-ranking` · `forme-es-lookup` / 백엔드 `cde-skills/elasticsearch`). 진입점이 너무 많다.
4. 상시 로드되는 description 총량은 약 **3,371 토큰**(57스킬). 본문(호출 시 로드)은 약 **44,448 토큰**. → description 다이어트 + 이중 등록 제거가 가장 효과 크다.

---

## 1. 4개 소스의 정체 (계층이 다르다)

| 소스 | 위치 | 계층 | SKILL.md | 설치 상태 |
|------|------|------|:---:|------|
| **cde-skills** | `~/work/cde/cde-skills/skills/` | **백엔드** API 클라이언트 (github/jira/agit/trino/ES/kafka/flink/kdp/qm/k8s/airflow/grafana/vault) | ❌ 없음 (scripts/ 만) | 스킬 아님 — 래퍼가 `python skills/<n>/scripts/...` 로 호출 |
| **cde-ranking-skills** | `~/work/cde/cde-ranking-skills/.claude/skills/` | **도메인** (gift/forme/talkstore 랭킹, score-drilldown, service-onboard) | ✅ 12개 | ✅ 팀 스킬로 동기화됨 |
| **jackie-skills** | `~/work/cde/jackie-skills/plugins/.../skills/` | **개인 하네스 플러그인** (Jackie 의 원본) | ✅ 21개 | ❌ **미설치** (upstream 참고용) |
| **megan-skills** | `~/work/glasslego/ai-env/megan-skills/skills/` | **내 개인 스킬** (jackie 파생 + cde 래퍼) | ✅ 24개 | ✅ personal 로 동기화됨 |

**핵심 통찰**: 이건 "4개의 같은 레이어가 겹친 것"이 아니라 **백엔드(cde) → 래퍼(megan) → 도메인(ranking)** 의 수직 스택 + **상류 fork(jackie)** 구조다. 따라서 처방도 계층마다 다르다.

---

## 2. 토큰 측정 (실측)

세션 시작 시 **상시 로드되는 것은 frontmatter 의 `description` 뿐**이다. 본문은 스킬을 실제 호출할 때만 로드된다.

| 소스 | 스킬 수 | description 합 (상시 로드) | 본문 합 (호출 시) |
|------|:---:|---:|---:|
| megan-skills | 24 | 4,608B (**~1,152 tok**) | 37,125B (~9,281 tok) |
| cde-ranking-skills | 12 | 2,614B (**~653 tok**) | 64,382B (~16,095 tok) |
| jackie-skills (미설치) | 21 | 6,263B (~1,565 tok) | 76,285B (~19,071 tok) |
| **현재 로드 합 (megan+ranking)** | **36** | **~1,805 tok** | ~25,376 tok |

여기에 프로젝트 `.claude/skills/` 12개가 **이중 등록**으로 추가 로드된다 (아래 3-A 참고). 즉 실제 세션 비용은 위 + 중복분.

> 측정 근거: `description` 은 frontmatter 의 `description:` ~ 다음 키 직전까지. 1토큰 ≈ 4바이트 근사.

---

## 3. 중복 매트릭스 (3개 축)

### 축 A — 이중 등록 (★ 가장 시급, 순수 낭비)

`~/.claude/skills/`(personal sync)와 프로젝트 `.claude/skills/`(project) **양쪽에 똑같이** 존재해 description 이 2번 로드되는 스킬:

| 스킬 | personal(`~/.claude/skills`) | project(`.claude/skills`) | 비고 |
|------|:---:|:---:|------|
| code-review | ✅ | ✅ | 동일 |
| doc-sync | ✅ | ✅ | 동일 |
| es-gift-ranking | ✅ | ✅ | ranking 과도 겹침 |
| handoff-resume | ✅ | ✅ | 동일 |
| harness | ✅ | ✅ | 동일 |
| python-env | ✅ | ✅ | 동일 |
| research | ✅ | ✅ | 동일 |
| session-save | ✅ | ✅ | 동일 |
| skill-creator | ✅ | ✅ | 동일 |
| spark-debug | ✅ | ✅ | 동일 |
| spec-manager | ✅ | ✅ | 동일 |
| task-implement | ✅ | ✅ | 동일 |

→ **12개 × ~50 tok = ~600 tok 이 매 세션 그냥 낭비.** 효과 대비 가장 고치기 쉬움.

### 축 B — megan ↔ jackie (유지보수 중복, 런타임 X)

jackie 가 미설치이므로 토큰엔 영향 없지만, **두 레포에 같은 기능이 따로 진화**한다 (드리프트 위험):

| 기능 | megan-skills | jackie-skills | 권장 SoT |
|------|------|------|------|
| wrap-up | `work/wrap-up` (2,348B) | `wrap-up` (3,767B) | megan(개인 vault 경로 반영) |
| distill | `obsidian/distill` (2,402B) | `distill` (3,765B) | megan |
| branch-guard | `code/branch-guard` (1,601B) | `branch-guard` (4,410B) | jackie 가 hook 강제까지 — 아이디어만 흡수 |
| pr-evaluator | `code/pr-evaluator` (2,087B) | `pr-evaluator` (3,112B) | megan |
| vault-lint | `obsidian/vault-lint` (1,701B) | `vault-lint` (3,573B) | megan |
| memory-hygiene | `meta/memory-hygiene` | `memory-hygiene` (3,065B) | megan |
| second-opinion | `code/second-opinion` (1,717B) | `code-second-opinion` (9,523B) | megan(가볍게) |
| jira | `work/jira-task` (2,918B) | `jira-create`+`jira-update`+`cde-jira-to-vault` (12.8KB) | 용도 분리 — 통합 검토 |
| session-save | `session-save` (CLI 위임) | `session-saver`(15KB)+`auto-session-archive`(11KB) | megan(CLI 기반이 가벼움) |
| hot-context | `obsidian/hot-context` (2,492B) | `daily-hot-builder`+`daily` (4.8KB) | megan |
| harness | `harness` (1개) | `harness-engineering/apply/improve/observe` (4개) | jackie 가 더 정교 — 아이디어 참고 |

→ **처방: jackie 를 "참고용 upstream"으로 명시**하고, 좋은 패턴은 megan 으로 흡수하되 둘을 동시에 설치하지 않는다 (설치하면 description 거의 2배).

### 축 C — megan 래퍼 ↔ cde-skills 백엔드 (의도된 위임, 비용 존재)

megan 래퍼는 cde-skills 백엔드를 한국어 트리거 + 옵시디언 저장으로 감싼 것. **의도된 설계**지만 description 비용이 있다:

| megan 래퍼 | 위임 대상 (cde-skills) | 부가가치 |
|------|------|------|
| airflow-ops | `airflow` | 한국어, --env shortcut, 노트 저장 |
| es-query | `elasticsearch` | 한국어, 노트 저장 |
| trino-query | `data/trino` | markdown table → 옵시디언 임베드 |
| kafka-browse / flink-ops | `kafka` / `flink` | read-only 가드 |
| k8s-ops / grafana-board / kdp-browse | `platform` / `grafana` / `kdp` | mutating 차단 |
| query-manager / hadoop-yarn | `data/query-manager` / `data` | upload/kill 차단 |
| oncall-respond | `operations/watchtower`+ 다수 | 진단 흐름 통합 |

→ **유지 권장** (래퍼는 안전 가드 + UX 가치). 단 description 을 한 줄로 압축 가능.

### 축 D — cde-ranking 내부 + ES 3계층

- `es-query`(범용) / `es-gift-ranking` / `forme-es-lookup` / 백엔드 `cde-skills/elasticsearch` → **ES 진입점 4개**. 도메인(forme/gift)은 남기되 범용 `es-query` 와의 경계를 description 에 명시.
- ranking 의 `forme-es/trino/redis-lookup`, `gift-*`, `ranking-*` 는 도메인 특화라 유지. 단 `service-onboard`(19KB), `feature-crud`(10KB) 등 큰 본문은 호출 시만 로드되므로 description 만 슬림하면 됨.

---

## 4. 토큰 효율화 권고 (우선순위)

| 우선순위 | 조치 | 예상 절감 | 리스크 |
|:---:|------|---:|:---:|
| **P1** | **이중 등록 제거** — 축 A 12개를 personal 또는 project 한쪽만 sync (`ai-env sync` 가 둘 다 밀지 않게) | ~600 tok/세션 | 낮음 |
| **P2** | **description 슬림화** — 래퍼(축 C) description 을 "트리거 키워드 1줄 + 위임 1줄"로 압축 | ~300–500 tok | 낮음 |
| **P3** | **jackie = 미설치 명문화** — fork 관계 문서화, 동시 설치 금지 규칙 | (설치 시) ~1,565 tok 회피 | 낮음 |
| **P4** | **ES 진입점 경계 정리** — `es-query`(범용) vs forme/gift(도메인) 를 description 에 명시해 오발동 방지 | 간접 (오호출 토큰) | 중 |
| **P5** | **sync 프로파일 도입** — 작업 맥락별(`--skills-include`)로 필요한 스킬만 배포 (랭킹 작업 / 일반 개발 분리) | 맥락당 수백 tok | 중 |

### 권장 운영 규칙 (중복 관리 정책)

1. **계층 = 단일 책임**: 백엔드는 cde-skills, 안전 래퍼/한국어 UX 는 megan, 도메인은 cde-ranking. 같은 일을 두 계층에서 새로 구현하지 않는다.
2. **SoT 우선**: 기능이 jackie 와 겹치면 megan 을 SoT 로, jackie 는 아이디어 소스. 동시 설치 금지.
3. **이중 등록 금지**: personal 과 project `.claude/skills` 에 같은 스킬을 두지 않는다. sync 시 같은 `name` 충돌을 경고하는 가드 추가 검토.
4. **description 예산**: 스킬당 description ≤ ~60 토큰(트리거 키워드 + 한 줄 설명). 상세는 본문으로.

---

## 4.5 배포 방식 비교 — `ai-env sync` vs plugin 설치

> 질문: "skill 을 plugin 으로 설치하면 뭐가 더 유리한가?" — 결론부터: **토큰 효율 관점에선 이득 없음.**

### 핵심: plugin 으로 깔아도 토큰은 안 줄어든다

plugin 으로 설치하든 `ai-env sync` 로 파일 복사하든, **세션 시작 시 로드되는 description 양은 동일**하다. plugin skill 도 frontmatter description 이 그대로 컨텍스트에 올라온다. → 이 문서가 다루는 *이중 등록 · description 다이어트* 문제는 plugin 전환으로 해결되지 않는다.

### plugin 이 실제로 유리한 지점 (토큰과 무관)

| plugin 이 주는 것 | 내용 | 개인(megan) 사용 시 의미 |
|------|------|------|
| 버전 관리/업데이트 | `plugin.json` version → `claude plugin update`, install-count 캐시 | 작음 — `ai-env sync` 재실행으로 대체 |
| **hook 등록을 manifest 로** | `hooks/claude-hooks.json` 으로 등록 → `~/.claude/settings.json` 직접 수정 회피 (jackie 의 CDE-2374 인시던트 회피책) | **유의미** — 설정 충돌 방지, uninstall 시 깨끗이 제거 |
| **namespacing** (`plugin:skill`) | 스킬 이름이 plugin 으로 격리됨 | **유의미** — 축 A 의 이중 등록 이름 충돌을 구조적으로 차단 |
| enable/disable 단위 | plugin 통째로 on/off | 중간 — sync 는 파일 수동 삭제 필요 |
| marketplace 배포 | 남이 한 줄로 설치 | **무의미** — 개인 사용 |
| 멀티 호스트 parity | 한 레포 → Claude/Codex/Cursor/Antigravity 동시 설치 | 낮음 — `ai-env sync` 가 이미 Claude+Codex parity 처리 |

### plugin 으로 가면 오히려 잃는 것 (★ 결정적)

지금 `ai-env sync` 는 단순 복사가 아니라 **변환 파이프라인**을 돈다. plugin 은 파일을 "있는 그대로" 배포하므로 이걸 우회하게 된다:

- **`${VAR}` 시크릿 치환 + `ENV_KEY_MAPPING`** (예: `GITHUB_GLASSLEGO_TOKEN` → `GITHUB_PERSONAL_ACCESS_TOKEN`)
- **Codex 용 SKILL.md frontmatter strict-YAML 정규화** (`~/.codex/skills/`)
- **타겟별 MCP 설정 생성** (stdio/SSE 분기)

### 결론 (개인 사용 기준)

- **토큰 효율이 목적 → plugin 전환은 답이 아니다.** P1(이중 등록 제거) + P2(description 슬림화)가 직접 해법.
- **plugin 이 가치 있는 경우는 단 둘:** (1) hook 을 settings.json 직접 수정 없이 깔끔히 등록/제거할 때, (2) 이름 충돌을 namespacing 으로 막을 때 — 단 (2)는 "한쪽만 sync" 로도 동일 해결.
- **권고**: megan-skills 본체는 변환이 필요하므로 **`ai-env sync` 유지**. plugin 구조는 jackie 처럼 *팀 배포 또는 hook 다수 운용* 시에만 채택.

---

## 5. 다음 단계 (이 문서 이후, 별도 승인 필요)

- [ ] `ai-env sync` 가 축 A 12개를 이중 배포하지 않도록 옵션/로직 점검 (코드 변경 — **미실행**)
- [ ] 래퍼 description 압축안 초안 (스킬 본문 변경 — **미실행**)
- [ ] sync 프로파일(`--skills-include` 프리셋) 설계
- [ ] jackie fork 관계를 CLAUDE.md/README 에 1줄 명시

> 본 문서는 분석·계획만 담는다. 스킬 파일·sync·코드는 **변경하지 않았다.**
