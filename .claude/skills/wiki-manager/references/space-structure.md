# KCAI 공간 위키 구조

커머스추천팀(KCAI) 위키 공간의 페이지 구조를 정리합니다.

> 이 문서는 위키 구조 정비 후 업데이트 예정입니다.

## 최상위 구조

```
카카오 커머스추천팀 Home (815966617)
├── 커머스추천팀 (1704669054)
├── [Products] 추천 (1892187086)
├── [Projects] 공통 (826598409)
├── [Projects] 추천 (1461686477)
├── [Projects] 타겟팅 (1482193990)
├── [Guide] 문서 (1912380187)
├── [Guide] 개발 (1467074659)
├── [Guide] 업무 (1461700967)
├── [Domain] 유저/아이템 모델링 (1612487992)
├── [Comm] 외부 비공개 공유 (1590379995)
└── Archived (1467074592)
```

## 주요 페이지 설명

### [Products] 추천
프로덕트별 문서 모음

### [Projects] 공통
팀 공통 프로젝트 문서

### [Guide] 개발
개발 가이드, 온보딩 문서

### [Guide] 업무
업무 프로세스, 정책 문서

---

## 구조 업데이트 방법

하위 페이지 목록 갱신:
```bash
uv run python tmp/wiki-manager/scripts/wiki_client.py children --page-id 815966617
```

특정 섹션 검색:
```bash
uv run python tmp/wiki-manager/scripts/wiki_client.py cql 'space = KCAI and title ~ "[Products]"'
```
