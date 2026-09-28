---
paths:
  - "src/app/feature_store/**/*.py"
---

# 코드 중복 최소화

## 기존 유틸리티 우선 검색

- 새 함수 작성 전 아래 경로에서 기존 유틸리티 먼저 검색:
  - `common_utils/`, `expoter/`, `conf_load/`, `src/common/utils/`
- 없다고 판단하면 한 번 더 확인

## 핵심 패턴 준수

- SparkClient 필수 — `SparkSession` 직접 생성 금지, Kudu 연동 + 세션 관리 포함
- Import 패턴 — `from src.app.feature_store...` (기본 `--py-files src.zip`; opt-in 레거시 app.zip#app 경로만 `sys.path.append("app")` 선행)
- 설정 로딩 — `get_vault_to_dict(phase)` → dataclass 기반 서비스 설정으로 변환
- Phase 인식 — `self.phase`로 테이블명, job 이름, 동작 분기

## 공유 기반 모듈 변경 주의

- `base_agg`(`features/ranking_v2/common/base_agg_manager.py`)는 다수(14개+) 랭킹 잡의
  공유 입력이라 변경 시 서비스 영향도가 크다.
- 새 기능은 base_agg를 직접 수정하지 말고 **별도 모듈 + 독립 테스트**로 구현한 뒤 붙인다.
- base_agg 직접 변경이 불가피하면 사전 검토/승인을 받고, 회귀 검증(Phase 5)을 반드시 거친다.
