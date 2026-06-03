# megan-skills 진짜 차별화 + glasslego 통합 — 방향성 검토

> 작성: 2026-05-13
> 상태: 계획·방향성 결정 (구현 X)
> 컨텍스트: 사용자가 "megan-skills 를 cde-skills / cde-ranking-skills 처럼 만들면서,
> glasslego 개인 프로젝트에도 접근하려면 어떻게 가야 할까?" 라고 물어봄.
> 본 문서는 의사결정용 — 결론을 내리지 않고 옵션 + 추천을 제시한다.

---

## 0. 한 줄 요약

megan-skills 는 지금 **cde-\* 위임 wrapper 70% + jackie 이식 30%** 라서
"진짜 megan 만의 것" 이 약하다. 차별화 여지는 두 군데에 있다:

1. **카카오 ↔ glasslego cross-context** — 둘 다 다루는 사람만 필요한 작업
2. **glasslego 사이드 프로젝트 공통 패턴** — 6개 프로젝트가 같은 스택을 반복

별도 repo 분리는 아직 ROI 가 안 나오고, **ai-env 내부 유지 + lib 보강**이 합리적.

---

## 1. 조사 결과 요약

### 1-1. 비교 — 4개 skill 묶음의 정체성

| 묶음 | 위치 | 정체성 | 자체 구현 비율 | Plugin marketplace |
|---|---|---|---|---|
| **cde-skills** | 별도 repo | 카카오 팀 공용 플랫폼 wrapper (Trino/K8s/Airflow ...) | 100% 자체 | ✅ `.claude-plugin/` |
| **cde-ranking-skills** | 별도 repo | 도메인 풀 패키지 (랭킹 운영 + `lib/`) | ~95% 자체 + lib 중앙집중 | ❌ |
| **jackie-skills** | 별도 repo | 개인 PKM + 코딩 보조 (Obsidian + cross-LLM 검증) | ~90% 자체 | ✅ marketplace.json |
| **megan-skills 현재** | ai-env 내부 | jackie 이식 + cde-\* 위임 + Obsidian 통합 | **~30% 자체 + 70% 위임/이식** | ❌ |

→ megan-skills 는 **bridge 묶음** — 세 묶음의 중간 지점에 있고, 그래서
"무엇이 진짜 megan 의 가치인가?" 가 흐릿하다.

### 1-2. glasslego 프로젝트별 현황

| 프로젝트 | 도메인 | 자체 `.claude/skills/` | 공통 스택 |
|---|---|---|---|
| auto-bitcoin | Upbit 자동매매 + APScheduler + Telegram | `aws-deploy`, `bitcoin-strategy`, `review` | Python 3.11 / uv / Streamlit / SQLite |
| auto-stock | 64 전략 백테스팅 + KIS 매매 + Optuna | `review` (+ agents/commands/handoff 풀스택) | Python / FastAPI / Redis / PostgreSQL |
| bbang-map | OSM 빵집 검색 (SQLite RTree) | 없음 (handoff 만) | Python / FastAPI / SQLite |
| drama-fashion | 셀럽 패션 CLIP 검색 + Meilisearch | `collect-fashion`, `drama-workflow`, `process-pipeline` | Python / FastAPI / PyTorch / Redis |
| tech-stock-news | RSS → Gemini 요약 → Telegram | 없음 (CLAUDE.md 만) | Python / FastAPI / Streamlit / PostgreSQL |
| claude-code-harness | (별도) | (조사 미수행 — 메타성격) | - |

**반복되는 공통 패턴 (★ = 강도):**
- ★★★ 데이터 수집 (외부 API) → 검증 → DB 적재 → 분석 → 알림 (Telegram)
- ★★★ pydantic-settings + `.env` 패턴 — 6/6 프로젝트가 동일
- ★★ Streamlit 또는 FastAPI 대시보드
- ★★ ruff + mypy + pytest + uv (같은 lint 규칙)
- ★ Alembic + SQLAlchemy
- ★ LLM 호출 (Gemini / OpenAI / Claude) — 일부

### 1-3. ai-env sync 가 megan-skills 를 보는 방식

`core/sync.py:285-331` 에서 스킬 출처는 4종으로 분리:

```
personal  : .claude/skills/*           (ai-env 자체 + ~/.claude/skills 로 항상 sync)
own       : megan-skills/skills/<cat>/<name>/   ← megan-skills 가 여기
always    : ALWAYS_TEAM_SKILLS = ("cde-ranking-skills",)  (옵션 없이 항상)
team      : --skills-include 지정 시만 (cde-skills 같은)
```

핵심:
- megan-skills 는 **이미 `own` 카테고리로 자동 인식**됨 (Phase 6 완료). 추가 옵션 필요 없음.
- 외부 repo 로 분리하면 `sync.py:293` 의 `project_root / "megan-skills"` 가
  `symlink → resolve()` 로 바뀌어야 하고, `_resolve_team_skill_root()` 호출 추가 필요.
  → **변경 3줄 정도** 면 분리 가능하지만, 분리 자체의 ROI 가 별도 문제.
- 동일 이름 충돌 시 `personal > own > always > team` 순서.
  예: `.claude/skills/spark-debug`(없음) vs `cde-ranking-skills/spark-debug` → 후자 적용.

---

## 2. "진짜 megan 만의 것" 은 어디에 있나

cde-\* 와 jackie 가 이미 잘 다루는 영역을 빼고 남는 것:

### 2-1. 다른 묶음이 못 다루는 영역 (megan 만 가능)

| 영역 | 왜 megan 만 | 후보 스킬 |
|---|---|---|
| **카카오 ↔ glasslego bridge** | 양쪽 다 쓰는 사람만 필요 | `cross-context-snapshot` (회사 작업 중 개인 프로젝트 빠른 점검), `secret-scope-check` (.env 가 카카오 vs 개인 어느 쪽인지 검증) |
| **glasslego 사이드 프로젝트 공통 패턴** | jackie/cde 는 카카오 도메인만 다룸 | `glasslego-collector` (yfinance/feedparser 래퍼), `glasslego-telegram-notify`, `glasslego-strategy-eval` |
| **개인 트레이딩 도메인** | 카카오 도메인 아님 | `backtest-runner`, `optuna-tune`, `risk-report` |
| **다중 vault 환경** | jackie 도 vault 통합하지만 megan 은 카카오 vault(`1X_업무카카오/`) + 개인 vault(`90_journal/`) 동시 운영 | 이미 일부 `obsidian/` 에 반영, 더 강화 가능 |

### 2-2. 위임 wrapper 를 줄여도 되는 부분

현재 megan-skills 가 위임만 하는 스킬 (`trino-query`, `es-query`, `kafka-browse`,
`hadoop-yarn`, `kdp-browse`, `query-manager`, `airflow-ops`, `flink-ops`,
`grafana-board`, `k8s-ops`, `oncall-respond`) — 11개.

이들은 **cde-skills 가 이미 동일 트리거로 동작**하므로,
megan-skills wrapper 는 **megan 만의 부가가치가 있을 때만 유지**해야 한다:
- ✅ 한글 트리거 매핑 — megan 만의 가치 (cde-skills 는 영문 위주)
- ✅ Obsidian 노트로 결과 저장 옵션 — megan 만
- ❌ 단순 passthrough — 제거 가능

→ **action 후보**: wrapper 스킬을 정리해서 자체 구현 비율을 50%+ 로 끌어올림.

---

## 3. glasslego 통합 — 4가지 전략 비교

### 전략 A: 모두 megan-skills 로 흡수 (DRY)

각 glasslego 프로젝트의 자체 `.claude/skills/` 를 점진 제거하고,
공통 패턴을 `megan-skills/glasslego/` 로 중앙화.

```
megan-skills/skills/glasslego/
  data-collector/      # yfinance + feedparser + Upbit wrapper
  telegram-notify/     # 모든 프로젝트 공용 알림
  backtest-runner/     # Optuna + 성과 리포트
  streamlit-template/  # 대시보드 스캐폴딩
```

- 👍 DRY, 한 곳에서 유지보수
- 👎 도메인 특화 (예: `bitcoin-strategy`) 가 megan-skills 에 들어가면 결합도↑
- 👎 megan-skills 가 비대해짐 (현재 40+ → 60+)
- 👎 각 프로젝트가 megan-skills 의존 — `~/.claude/skills/` 없으면 동작 X

### 전략 B: 각 프로젝트 자체 스킬 유지 + megan-skills 는 cross-project meta

각 glasslego 프로젝트는 자체 `.claude/skills/` 로 도메인 스킬 보유.
megan-skills 는 **여러 프로젝트를 가로지르는 작업**만 담당.

```
megan-skills/skills/glasslego/
  cross-context-snapshot/  # "지금 카카오 / glasslego 어디 상태야?"
  multi-repo-sync/         # ai-env 변경을 glasslego/* 에 propagate
  side-project-status/     # 6개 사이드 프로젝트 한눈에 (PR/배포/오류)
```

- 👍 도메인 결합 X, megan-skills 는 진짜로 cross-cutting 만
- 👍 각 프로젝트 독립성 유지
- 👎 공통 코드(data-collector 같은) 가 6번 복제됨

### 전략 C: 하이브리드 — `lib/` 중앙집중, 도메인 스킬은 분산

cde-ranking-skills 패턴을 모방. 공통 **라이브러리 코드**는 megan-skills 의
`lib/` 에 두고, 각 glasslego 프로젝트가 import. 도메인 스킬(`bitcoin-strategy`,
`drama-workflow`)은 각 프로젝트가 보유.

```
megan-skills/
  lib/
    obsidian.py           # 이미 계획됨
    trino_proxy.py        # cde-ranking 래핑
    glasslego_collectors.py   # yfinance + feedparser + Upbit
    glasslego_telegram.py     # AlertThrottle + DigestBuilder
    glasslego_settings.py     # pydantic-settings 베이스
  skills/
    glasslego/
      side-project-status/    # cross-cutting 만
      cross-context-snapshot/
```

각 glasslego 프로젝트의 `pyproject.toml` 또는 `sys.path` 에서
`megan-skills/lib/` 를 참조. 또는 **megan-skills 를 별도 패키지로 build** 해서
`uv add` 가능하게 만들 수도 있음 (장기).

- 👍 DRY (lib) + 도메인 결합 없음 (skills 분산) — 양쪽의 장점
- 👍 cde-ranking-skills 와 동일한 패턴 → 이미 megan 이 익숙
- 👎 lib 패키지화에 약간의 초기 비용 (sys.path 정리 or pyproject 추가)
- 👎 `.claude/skills/` vs `lib/` 의 라우팅이 약간 복잡 — 한 줄 ADR 필요

### 전략 D: megan-skills 를 별도 repo 로 분리 (Phase 7)

DESIGN.md 가 이미 옵션으로 언급. cde-skills / jackie-skills 처럼 독립.

- 👍 marketplace 공개 가능, 카카오 도메인 자산과 강하게 분리
- 👍 ai-env 와 megan-skills 의 라이프사이클 분리
- 👎 ai-env sync 코드 변경 (3줄, 작긴 함)
- 👎 cde-ranking lib import 가 sys.path 의존 → 분리 시 더 복잡
- 👎 현재 변경 빈도가 높아 모노레포 ROI 가 더 큼
- 👎 megan 만 쓰는데 marketplace 공개의 실익이 낮음

---

## 4. 추천 방향 (toolchain 입장에서의 의견)

### 4-1. 단기 (이번 분기 안에 가능)

> **전략 C (하이브리드, lib 중앙집중) + 위임 wrapper 정리.**
> 별도 repo 분리는 **하지 않는다**.

이유:
- 별도 repo 의 비용 > 이득. ai-env sync 가 이미 `own` 으로 자동 인식.
- lib 중앙집중은 cde-ranking 에서 검증된 패턴 + megan 이 익숙.
- 각 glasslego 프로젝트의 도메인 스킬 (`bitcoin-strategy`, `drama-workflow`)
  은 그 프로젝트의 컨텍스트가 가장 풍부한 곳에 두는 게 맞다.

구체 작업 (≈ 5개 Phase, 각 1~3시간):

| Phase | 작업 | 산출물 |
|---|---|---|
| 7-A | `lib/` 디렉토리 보강 — `obsidian.py`, `trino_proxy.py` 우선 구현 | DESIGN.md 의 미구현 lib 완성 |
| 7-B | 위임 wrapper 11개 audit — 단순 passthrough 는 제거, 부가가치 있는 것만 유지 | SKILLS.md 갱신 |
| 7-C | `glasslego/` 카테고리 신설 — cross-project meta 스킬만 (`side-project-status`, `cross-context-snapshot`) | skills/glasslego/ 2~3개 |
| 7-D | glasslego 공통 lib (`lib/glasslego_collectors.py`, `glasslego_telegram.py`) — 각 프로젝트가 import 할 수 있게 | lib/ 확장 |
| 7-E | 각 glasslego 프로젝트의 `pyproject.toml` 또는 `.claude/project-profile.yaml` 에 megan-skills lib 경로 명시 | 6개 프로젝트 작은 변경 |

### 4-2. 중기 (반년 단위)

> **glasslego 프로젝트별 .claude/skills/ 컨벤션 통일**

각 프로젝트가 자체 스킬을 가지되, 다음을 강제:
- SKILL.md frontmatter 컨벤션을 megan-skills 와 동일하게 (skill-creator 사용)
- 카테고리 = `domain/` (도메인 특화) + `ops/` (배포·운영) 두 개로 통일
- 트리거에 프로젝트명 prefix 권장 (예: `/bitcoin-strategy`, `/drama-collect`)
- megan-skills 에서 `multi-repo-skill-audit` 스킬로 6개 프로젝트 일관성 점검

### 4-3. 장기 (연 단위)

> **분리 여부 재평가**

다음 조건이 만족되면 그때 별도 repo 분리 검토:
- megan-skills 가 marketplace 공개 가치를 가질 정도로 성숙 (현재는 너무 카카오 vault 특화)
- 변경 빈도가 분기에 1-2회 수준으로 안정화 (현재는 주 단위)
- 다른 사람도 쓸 일이 생김

지금은 분리 X.

---

## 5. SKILL.md 컨벤션 강화 (Phase 7 외 즉시 가능)

조사에서 발견된 약점: megan-skills 의 description 이 너무 짧아
**다른 cwd 에서 트리거 적중률이 낮다**.

```yaml
# 현재 megan-skills 평균
description: "trino 쿼리"  # 너무 짧음

# cde-ranking 수준 (권장)
description: |
  Trino SQL 실행 + 결과를 markdown table 로 변환해 옵시디언 노트에 임베드 가능한
  형태로 출력. 사용자가 "/trino", "trino 쿼리", "트리노로 조회", "Trino SQL" 을
  말하면 트리거. 실제 Trino 호출은 cde-skills `data/trino` 서브스킬에 위임.
```

조치: `skill-creator` 또는 `doc-sync` 스킬을 megan-skills 자신에게 한 번 돌려서
description 을 일괄 보강. 별도 Phase 가 아니라 7-A 와 함께 진행 가능.

---

## 6. 결정 필요한 질문 (megan 에게)

다음 5개에 답하면 Phase 7 착수 가능:

1. **glasslego 통합 전략** — A / B / **C (추천)** / D 중 어느 것?
2. **위임 wrapper 정리** — 한글 트리거 + 부가가치 없는 wrapper 11개를 다 제거할지,
   아니면 유지할지? (제거 시 토큰 절약, 유지 시 megan 의 한국어 워크플로우 보존)
3. **각 glasslego 프로젝트 자체 스킬** — 그대로 둘지, megan-skills 컨벤션으로 통일할지?
   (auto-bitcoin / auto-stock / drama-fashion 은 이미 스킬 있음)
4. **lib 패키지화 수준** — `sys.path` 만 정리할지, 아예 `pyproject.toml` 의 dev
   dependency 로 megan-skills 를 등록할지?
5. **별도 repo 분리** — 지금 안 하는 것에 동의하는가? 동의하면 DESIGN.md Phase 7 을
   "분리 X / 본 문서로 대체" 로 갱신.

---

## 7. 부록: 즉시 가능한 작은 작업들 (Phase 7 이전)

본 문서가 거대해 보이지만, 다음 작업들은 **각 30분 이내**로 가능하고
즉시 가치가 있음:

- [ ] `megan-skills/lib/` 디렉토리 만들고 `__init__.py` + `obsidian.py` 빈 stub 작성
- [ ] DESIGN.md §7 (Phase 7 별도 repo) 를 "당분간 분리 X, 본 문서 참조" 로 갱신
- [ ] SKILLS.md 의 "위임 wrapper" 11개에 ★ (제거 후보) 마킹
- [ ] glasslego 6개 프로젝트의 `.claude/skills/` 목록을 한 곳에 모은 매핑 표 추가 (본 문서 §1-2 확장)
- [ ] `auto-stock`, `auto-bitcoin`, `drama-fashion` 의 `review` 스킬이 megan-skills `code-review` 와 중복인지 점검
