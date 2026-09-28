---
paths:
  - "src/app/feature_store/**/*.sh"
---

# Spark Job 실행 규칙

## 리소스 할당 — static allocation 고정

- 랭킹 배치 spark-submit은 **static allocation**을 쓴다. 모든 랭킹 잡 스크립트가
  `--conf spark.dynamicAllocation.enabled="false"`를 명시한다
  (base_agg·score·feature_short·relation_price·brand_trend 등).
- 새 잡에도 dynamicAllocation을 켜지 않는다. `spark.dynamicAllocation.*` /
  `spark.shuffle.service.*` 옵션을 임의로 추가하지 않는다.
- 예외: `anti_abusing/scripts/run_abuse_user_snapshot.sh` 는 워크로드 특성상
  dynamicAllocation을 쓴다. 이 예외를 랭킹 잡에 확대 적용하지 않는다.
- executor/driver 리소스는 `--executor-cores`/`--executor-memory`/`--num-executors`로
  명시 지정한다.

## 메모리·overhead 조정

- driver/executor 메모리·overhead는 근거 주석과 함께 조정한다. shuffle read나
  parquet 저장 구간에서 off-heap이 커지면 heap이 아니라 `memoryOverhead`를 올린다.
- 선례: `script/ranking_v2/run_gift_ranking_base_agg.sh` — driver 12G +
  `spark.driver.memoryOverhead=4g` (parquet 저장 구간 PythonRunner 여유 확보).
- 증상만 보고 메모리를 무작정 올리지 말고 원인(구간·off-heap)을 주석으로 남긴다.

## 패키징·제출 패턴

- `bin/pack_app.bash`로 `src.zip`(소스)+`deps.zip`(의존성)+`vault.zip`(시크릿)을 만들고
  `spark3-submit --py-files "src.zip,deps.zip" --archives "vault.zip#tmp/vault"`로 제출한다
  → `from src.app.feature_store...` import 직접 가능.
- 레거시(opt-in `BUILD_APP_ZIP=true`): `app.zip` + `--archives "app.zip#app"` + entrypoint `sys.path.append("app")` fallback.
- 인증: `get_vault_to_dict(phase)`로 시크릿 로드, Hadoop은 Kerberos(keytab) 인증.
