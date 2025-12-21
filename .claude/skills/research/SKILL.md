---
name: research
description: |
  멀티소스 리서치 통합 및 교차 분석 스킬.
  사용자가 리서치, research, 조사, brief, 교차 분석을 요청할 때 트리거.
  "리서치해줘", "research", "자료 조사", "brief 생성", "교차 분석" 등에 반응.
  Obsidian vault, 프로젝트 내 문서, 웹 검색 등 다양한 소스를 지원한다.
  프로젝트의 .claude/project-profile.yaml에서 리서치 소스 경로를 자동 로드한다.
---

# Research

멀티소스 리서치 수행 및 교차 분석 스킬.

## 프로젝트 컨텍스트 로드

`.claude/project-profile.yaml`의 `research.obsidian_base`(vault) / `research.sources_dir`(프로젝트 내) 로드. 둘 다 없으면 사용자에게 질문.

## 모드 판별

- **"리서치" / "research"** → Research 모드
- **"brief" / "brief 생성"** → Brief 모드
- **"교차 분석"** → Cross-Analysis 모드

---

## Research 모드

### Step 1: 리서치 소스 수집

리서치 파일 탐색 순서:
1. `research.sources_dir` (프로젝트 내)
2. Obsidian vault `{obsidian_base}/10_Research/Clippings/`
3. Obsidian vault `{obsidian_base}/07_참고/` (레거시)

파일 패턴으로 Track 분류:
- `auto-*.md` → Track A (자동 검색)
- `gemini-*.md` → Track B (Gemini Deep Research)
- `gpt-*.md` → Track C (GPT Deep Research)
- 기타 `.md` → Manual Track

### Step 2: 현황 보고

Track별 파일 수와 상태를 테이블로 출력 (Track A/B/C/Manual).

### Step 3: 추가 리서치 (선택)

사용자 요청 시 웹 검색/API로 추가 리서치 수행.
ai-env pipeline dispatch가 설정되어 있으면 Gemini/GPT Deep Research API 호출 가능:

```bash
uv run ai-env pipeline dispatch {topic_id} --track gemini
```

---

## Brief 모드

리서치 결과를 30% 이하로 압축한 Brief를 생성한다.

### Step 1: 기존 Brief 확인

Brief 파일 존재 여부 확인. 있으면 재사용할지 사용자에게 질문.

### Step 2: Brief 작성

`references/cross-analysis.md`의 교차 분석 가이드를 참조하여:

1. **합의 사항 (Consensus)**: 2개 이상 소스가 동의
2. **이견 사항 (Divergence)**: 소스 간 의견 다름 → 테이블 비교
3. **고유 인사이트 (Unique)**: 단일 소스의 유의미한 정보
4. 각 항목에 `[출처: 파일명]` 태그 부착
5. Brief 길이: 원본의 **30% 이하**

### Step 3: 저장

- Obsidian vault가 있으면: `{base_path}/10_Research/Briefs/BRIEF-{id}.md`
- 프로젝트 내: `docs/briefs/` 또는 사용자 지정 경로

---

## Cross-Analysis 모드

`references/cross-analysis.md`의 4-Way 교차 분석 프레임워크를 적용한다.

상세 절차는 `references/cross-analysis.md` 참조.

---

## ai-env pipeline 연동

ai-env 프로젝트 내에서 실행 중이고 topics YAML이 있는 경우:
- `ai-env pipeline status {topic_id}` 로 리서치 현황 확인
- `ai-env pipeline dispatch` 로 Deep Research 자동 실행

ai-env 외부 프로젝트에서는 이 기능을 사용하지 않는다.
