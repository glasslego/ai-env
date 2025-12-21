# Agent Team Examples

## 예시 1: SF 소설 집필 팀

### 에이전트 구성
| 에이전트 | 역할 | 스킬 |
|---------|------|------|
| worldbuilder | 세계관 구축 | world-setting |
| character-designer | 캐릭터 설계 | character-profile |
| plot-architect | 플롯 구조 | outline |
| prose-stylist | 문체 편집 | write-scene, review-chapter |
| science-consultant | 과학 검증 | science-check |
| continuity-manager | 일관성 검증 | consistency-check |

### 통합 스킬
- `sf-novel-writer`: 팀을 조율하는 오케스트레이터 스킬

### 팀 아키텍처
```
Phase 1 (병렬): worldbuilder + character-designer + plot-architect
Phase 2 (순차): prose-stylist (집필)
Phase 3 (병렬): prose-stylist + science-consultant + continuity-manager (리뷰)
```

## 예시 2: 웹툰 제작 팀

### 에이전트 구성
| 에이전트 | 역할 | 스킬 |
|---------|------|------|
| webtoon-artist | 패널 이미지 생성 | generate-webtoon |
| webtoon-reviewer | 품질 검수 | review-webtoon, fix-webtoon-panel |

### 통합 스킬
- `webtoon-creator`: 팀을 조율하는 오케스트레이터 스킬

### 팀 아키텍처
```
Phase 1: webtoon-artist (패널 생성)
Phase 2: webtoon-reviewer (검수)
Phase 3: webtoon-artist (문제 패널 재생성)
```

## 예시 3: 리서치 팀

### 에이전트 구성
| 에이전트 | 역할 | 스킬 |
|---------|------|------|
| web-researcher | 웹 검색/수집 | (내장 도구 사용) |
| analyst | 데이터 분석/종합 | (내장 도구 사용) |
| report-writer | 보고서 작성 | (내장 도구 사용) |

### 통합 스킬
- `agent-research`: 팀을 조율하는 오케스트레이터 스킬

## 산출물 패턴

### 에이전트 정의 파일
위치: `프로젝트/.claude/agents/{agent-name}.md`

### 스킬 파일 구조
위치: `프로젝트/.claude/skills/{skill-name}/skill.md` (프로젝트 레벨)
또는: `~/.claude/skills/{skill-name}/SKILL.md` (글로벌 레벨)

### 통합 스킬 (오케스트레이터)
팀 전체를 조율하는 상위 스킬. 시나리오별 에이전트 구성과 워크플로우를 정의.
