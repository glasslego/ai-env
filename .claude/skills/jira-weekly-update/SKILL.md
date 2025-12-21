---
name: jira-weekly-update
description: |
  JIRA 이슈 기반 주간 업무 보고서 자동 생성.
  사용 시점: 사용자가 "주간 보고서 생성", "weekly report", "이번 주 업무 정리" 등을 요청할 때.
  기능: JIRA에서 진행중/완료 Task를 조회하여 Component > Service > Epic > Task 구조로 Markdown 요약 생성.
---

# JIRA Weekly Update

JIRA 이슈를 조회하여 주간 업무 보고서를 생성한다.

## Workflow

1. **Draft 데이터 생성**: 스크립트를 실행하여 Component별 YAML 파일 생성
2. **YAML 파일 읽기**: `_index.yaml`로 Component 목록 확인 후 각 파일 순차 읽기
3. **Markdown 요약 생성**: 아래 형식 규칙에 따라 요약 작성
4. **파일 저장**: `reports/weekly/weekly_YYYYMMDD.md`로 저장
5. **HTML 변환**: Markdown을 HTML로 변환하여 `reports/weekly/weekly_YYYYMMDD.html` 생성

## Step 1: Draft 생성

다음 스크립트를 실행하여 JIRA 데이터를 YAML로 추출:

```bash
uv run python .claude/skills/jira-weekly-update/scripts/generate_draft.py
```

결과:
```
reports/draft/draft_weekly_YYYYMMDD/
├── _index.yaml           # Component 목록
├── 추천.yaml
├── 타겟팅.yaml
├── 유저_아이템_프로파일링.yaml
├── 운영.yaml
└── 기타.yaml
```

## Step 2: YAML 파일 읽기

### 읽기 순서
1. `_index.yaml`을 먼저 읽어 Component 목록 확인
2. 각 Component 파일을 순차적으로 읽기

### YAML 구조
- `_index.yaml`: Component 목록 (`components: [추천, 타겟팅, ...]`)
- Component YAML: `component` > `services` > Epic (`key`, `summary`, `url`) > `tasks` (`summary`, `status`, `key`, `url`, `assignee`, `description`, `comments`)
- 서비스 순서: **선물하기 → 톡딜 → 쇼핑탭 → 라이브 → 기타**

## Step 3: Markdown 요약 규칙

다음 규칙을 **엄격히** 따른다:

### 언어
- 항상 **한국어**로 작성

### 헤딩 구조
- 최상위: `## 업무 상세`
- Component별: `### [ Component Name ]`
- Component 사이와 마지막에 `---` 구분선 추가

### Epic 표기
- 굵게 + 링크: `**[Epic Summary](epic_url)**`
- Epic summary에 `[]` 기호가 있으면 백슬래시로 이스케이프: `\[선물하기\]`
- 예: `**\[선물하기\] 상품상세 전체 개편** [jira](https://...)`

### Task 표기
- 상태 + 요약 + 링크: `- [상태] Task Summary [jira](task_url)`
- 상태 매핑:
  - `Closed`, `Resolved` → `[완료]`
  - `In Progress` → `[진행중]`

### 활동 요약 (핵심)
- 각 Task 아래 들여쓰기(2칸)로 핵심 활동 요약 (1-3줄)
- `description.text`, `comments[].body`, `crawled_content` 활용
- 핵심 업데이트, 결정사항, 결과물 위주로 추출
- 중요 링크가 있으면 도메인별 레이블 사용:

| 도메인 | 레이블 |
|--------|--------|
| `github.daumkakao.com` | `[github](url)` |
| `wiki.daumkakao.com` | `[wiki](url)` |
| `kakao-product.slack.com` | `[slack](url)` |
| `pivot.tiara.kakaocorp.com` | `[pivot](url)` |
| `cdp-redash.is.kakaocorp.com` | `[redash](url)` |
| `docs.google.com` | `[docs]](url)` |
| `grafana-*` | `[grafana](url)` |

### 출력 예시

`## 업무 상세` > `### [ Component ]` > `**\[서비스\] Epic제목** [jira](url)` > `- [완료/진행중] Task명 [jira](url)` > `  - 활동 요약 1-3줄`

Component 사이와 마지막에 `---` 구분선. Epic의 `[]`는 백슬래시 이스케이프.

## Step 4: 파일 저장

생성된 Markdown을 다음 경로에 저장:

```
reports/weekly/weekly_YYYYMMDD.md
```

(YYYYMMDD는 오늘 날짜, 예: 20251213)

## Step 5: HTML 변환

Markdown 보고서를 HTML로 변환:

```bash
uv run python .claude/skills/jira-weekly-update/scripts/md_to_html.py
```

또는 특정 파일 지정:

```bash
uv run python .claude/skills/jira-weekly-update/scripts/md_to_html.py reports/weekly/weekly_20251213.md
```

결과:
```
reports/weekly/weekly_YYYYMMDD.html
```

### Bullet 변환 규칙
HTML에서 bullet 계층이 텍스트 기반으로 변환됩니다:
- 1단계: `-`
- 2단계: `  ㄴ`
- 3단계: `    ㄴ`

### 스타일링
- 상태 배지 색상: [완료] 초록색, [진행중] 주황색
- 링크는 클릭 가능한 하이퍼링크로 유지
