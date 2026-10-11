# 팀 스킬·환경변수 점검 (2026-10-12)

작업: `spec-skills-current/task-sync-and-env-audit`.

cde-skills와 cde-ranking-skills의 develop은 origin/develop과 동일하다. 활성 팀 스킬은 원본 링크로 동기화하고, 랭킹 helper는 정본 .venv/bin/python으로 실행한다.

템플릿과 실행 코드의 정적 변수 이름 232개를 수집했다. ai-env .env의 활성 값 39개, 활성 빈 값 7개, 주석 자리 186개다. 초기 누락은 187개였다.

전체 변수 이름은 .env와 .env.example에 기록했다. 모든 변수가 필수는 아니며, 주석은 미설정 상태를 나타낸다. 값이 있어도 유효성·만료·서비스 접속은 확인하지 않았다. 동적으로 조합하는 환경별 변수 이름은 각 스킬의 설정을 따른다.

Jira/Wiki URL은 Cloud 주소로 갱신했다. JIRA_EMAIL은 ai-env .env에 없으며 Cloud 인증에 필요하다. WIKI_EMAIL은 JIRA_EMAIL로 fallback할 수 있다. 기존 토큰은 변경하지 않았고 Cloud API token 여부는 미검증이다. cde-skills 저장소 .env에는 JIRA_EMAIL과 Cloud URL이 있지만 그 자격증명을 자동 복사하지 않았다.

템플릿에 포함된 예시 비밀번호·토큰은 복사하지 않는다. 선택 변수의 빈 활성 값은 기본값을 덮을 수 있어 주석으로만 추가한다.

## 검증

- 관련 pytest: 69 passed (coverage 옵션 제외).
- pre-commit: ruff, format, mypy, secret 검사, doc-sync 통과.
- Claude·Codex·Agents에 각각 67개 스킬 반영, 그중 33개 팀 정본 링크 검증.
- 실제 .env는 gitignore 대상이며 값은 보고서에 포함하지 않음.

## 변수 이름별 상태

| 이름 | ai-env .env 상태 | 출처 |
|---|---|---|
| `AGIT_API_BASE_URL` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `AGIT_ID` | 주석 자리 (미설정) | cde-skills:code |
| `AGIT_KSP_SEARCH_URL` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `AGIT_TOKEN` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `AGIT_USER_AGIT_ID` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `AGIT_WEBHOOK_URL` | 주석 자리 (미설정) | cde-skills:template |
| `AIRFLOW_CDE_RANKING_STAGE_URL` | 주석 자리 (미설정) | cde-skills:template |
| `AIRFLOW_CDE_RANKING_URL` | 주석 자리 (미설정) | cde-skills:template |
| `AIRFLOW_CDE_STAGE_URL` | 주석 자리 (미설정) | cde-skills:template |
| `AIRFLOW_CDE_URL` | 주석 자리 (미설정) | cde-skills:template |
| `AIRFLOW_DAGS_REPO_URL` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:template |
| `AIRFLOW_KCAI_FEATURE_URL` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `AIRFLOW_KCAI_STAGE_URL` | 주석 자리 (미설정) | cde-skills:template |
| `AIRFLOW_KCAI_URL` | 주석 자리 (미설정) | cde-skills:template |
| `AIRFLOW_PASSWORD` | 값 있음 (유효성 미검증) | cde-ranking-skills:code, cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `AIRFLOW_PROD_URL` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `AIRFLOW_STAGE_URL` | 주석 자리 (미설정) | cde-skills:template |
| `AIRFLOW_USERNAME` | 값 있음 (유효성 미검증) | cde-ranking-skills:code, cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `AIRFLOW_V3_PROD_URL` | 주석 자리 (미설정) | cde-skills:template |
| `AIRFLOW_V3_RANKING_STAGE_URL` | 주석 자리 (미설정) | cde-skills:template |
| `AIRFLOW_V3_RANKING_URL` | 주석 자리 (미설정) | cde-skills:template |
| `AIRFLOW_V3_STAGE_URL` | 주석 자리 (미설정) | cde-skills:template |
| `AIR_SCRIBE_TOKEN` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `AIR_SCRIBE_TOKEN_FILE` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `AIR_SCRIBE_URL` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `ALERTMANAGER_CDP_FLINK_PROD_URL` | 주석 자리 (미설정) | cde-skills:template |
| `ALERTMANAGER_CDP_FLINK_STAGE_URL` | 주석 자리 (미설정) | cde-skills:template |
| `ALERTMANAGER_CDP_PLATFORM_PROD_URL` | 주석 자리 (미설정) | cde-skills:template |
| `ALERTMANAGER_CDP_PLATFORM_STAGE_URL` | 주석 자리 (미설정) | cde-skills:template |
| `ALERTMANAGER_USER` | 주석 자리 (미설정) | cde-skills:template |
| `ANTHROPIC_API_KEY` | 활성 빈 값 | cde-skills:code |
| `ARGOCD_DEV_URL` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `ARGOCD_PASSWORD` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `ARGOCD_PROD_URL` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `ARGOCD_SERVER_URL` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `ARGOCD_TOKEN` | 활성 빈 값 | cde-skills:code, cde-skills:template |
| `ARGOCD_USERNAME` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `BDP_TOKEN` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `CDE_DOCS_MANIFEST` | 주석 자리 (미설정) | cde-skills:code |
| `CDE_ONTOLOGY_URL` | 주석 자리 (미설정) | cde-skills:code |
| `CDE_SKILLS` | 주석 자리 (미설정) | cde-skills:code |
| `CDE_SKILLS_ENV` | 주석 자리 (미설정) | cde-skills:code |
| `CDE_SKILLS_REPO_ROOT` | 주석 자리 (미설정) | cde-skills:runtime |
| `CDE_SKILLS_ROOT` | 주석 자리 (미설정) | cde-ranking-skills:code |
| `CDE_SKILLS_SOURCE_ROOT` | 값 있음 (유효성 미검증) | cde-skills:runtime |
| `CDP_AIR_ADMIN_CLIENT_ID` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `CDP_AIR_ADMIN_CLIENT_SECRET` | 주석 자리 (미설정) | cde-skills:template |
| `CDP_AIR_ADMIN_DEV_CLIENT_SECRET` | 주석 자리 (미설정) | cde-skills:template |
| `CDP_AIR_ADMIN_ENABLE_TEST_PHASE` | 주석 자리 (미설정) | cde-skills:template |
| `CDP_AIR_ADMIN_ON_BEHALF_OF` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `CDP_AIR_API_KEY` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `CDP_AIR_PASSWORD` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `CDP_AIR_PROD_URL` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `CDP_AIR_STAGE_URL` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `CDP_AIR_TOKEN` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `CDP_AIR_USERNAME` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `CDP_EXPORTER_PATH` | 주석 자리 (미설정) | cde-skills:template |
| `CICD_BASE_URL` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `CICD_ID` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `CICD_PW` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `CLAUDE_BIN` | 주석 자리 (미설정) | cde-skills:code |
| `CODEX_BIN` | 주석 자리 (미설정) | cde-ranking-skills:code |
| `CODEX_MODEL` | 주석 자리 (미설정) | cde-ranking-skills:code |
| `CONTAINER_ID` | 주석 자리 (미설정) | cde-skills:code |
| `COSMOS_LINEAGE_API_URL` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `COSMOS_LINEAGE_TOKEN` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `DEBOT_BASE_URL` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `DEBOT_REPO` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `DEMO_DIR` | 주석 자리 (미설정) | cde-skills:code |
| `DEMO_MODE` | 주석 자리 (미설정) | cde-skills:code |
| `DRUID_DATASOURCE` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `DRUID_PASSWORD` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `DRUID_SQL_ENDPOINT` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `DRUID_USER` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `EPIC_LINK_CACHE` | 주석 자리 (미설정) | cde-skills:code |
| `ES_API_KEY` | 활성 빈 값 | cde-skills:code |
| `ES_CLUSTER_DEV_URL` | 주석 자리 (미설정) | cde-skills:template |
| `ES_CLUSTER_STAGE_URL` | 주석 자리 (미설정) | cde-skills:template |
| `ES_HOST` | 주석 자리 (미설정) | cde-ranking-skills:code |
| `ES_PASSWORD` | 주석 자리 (미설정) | cde-skills:code |
| `ES_URL` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `ES_USER` | 주석 자리 (미설정) | cde-skills:code |
| `FLINK_DEV_URL` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:template |
| `FLINK_PROD_URL` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:template |
| `FLINK_STAGE_URL` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:template |
| `GH_HOST` | 주석 자리 (미설정) | cde-ranking-skills:code |
| `GITHUB_BASE_REF` | 주석 자리 (미설정) | cde-ranking-skills:code |
| `GITHUB_ENTERPRISE_URL` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `GITHUB_HEAD_REF` | 주석 자리 (미설정) | cde-ranking-skills:code |
| `GITHUB_TOKEN` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `GOOGLE_CLIENT_ID` | 활성 빈 값 | cde-skills:code, cde-skills:template |
| `GOOGLE_CLIENT_SECRET` | 활성 빈 값 | cde-skills:code, cde-skills:template |
| `GOOGLE_TOKEN_PATH` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `GRAFANA_CDP_ML_PROD_URL` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `GRAFANA_CDP_ML_STAGE_URL` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `GRAFANA_PASSWORD` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `GRAFANA_PROD_PASSWORD` | 주석 자리 (미설정) | cde-skills:code |
| `GRAFANA_PROD_URL` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `GRAFANA_PROD_USERNAME` | 주석 자리 (미설정) | cde-skills:code |
| `GRAFANA_STAGE_PASSWORD` | 주석 자리 (미설정) | cde-skills:code |
| `GRAFANA_STAGE_URL` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `GRAFANA_STAGE_USERNAME` | 주석 자리 (미설정) | cde-skills:code |
| `GRAFANA_URL` | 주석 자리 (미설정) | cde-skills:code |
| `GRAFANA_USERNAME` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `G_CDPDEV_KEYTAB` | 주석 자리 (미설정) | cde-skills:template |
| `HADOOP_CDP_ENV_PATH` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `HADOOP_CDP_ENV_SCRIPT` | 주석 자리 (미설정) | cde-skills:template |
| `HADOOP_CLIENT_ENV_BIN` | 주석 자리 (미설정) | cde-ranking-skills:code |
| `HADOOP_ENV_FILE` | 주석 자리 (미설정) | cde-ranking-skills:code |
| `HADOOP_ENV_FUNC` | 주석 자리 (미설정) | cde-ranking-skills:code |
| `HADOOP_KEYTAB` | 주석 자리 (미설정) | cde-ranking-skills:code |
| `HADOOP_KRB_KEYTAB` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `HADOOP_KRB_PASSWORD` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `HADOOP_KRB_PRINCIPAL` | 값 있음 (유효성 미검증) | cde-skills:code, cde-skills:template |
| `HADOOP_PRINCIPAL` | 주석 자리 (미설정) | cde-ranking-skills:code |
| `HELLOMIS_AUTHKEY` | 주석 자리 (미설정) | cde-skills:code |
| `HIVE_CONF_DIR` | 주석 자리 (미설정) | cde-skills:code |
| `ICW_ALERT` | 주석 자리 (미설정) | cde-skills:code |
| `ICW_ALERT_ROOM` | 주석 자리 (미설정) | cde-skills:code |
| `ICW_ALERT_TO` | 주석 자리 (미설정) | cde-skills:code |
| `ICW_AVG_MB_BAD` | 주석 자리 (미설정) | cde-skills:code |
| `ICW_CATALOG` | 주석 자리 (미설정) | cde-skills:code |
| `ICW_EXCLUDE` | 주석 자리 (미설정) | cde-skills:code |
| `ICW_FILE_COUNT_BAD` | 주석 자리 (미설정) | cde-skills:code |
| `ICW_PART_TIMEOUT` | 주석 자리 (미설정) | cde-skills:code |
| `ICW_REPLACE_STALE_H` | 주석 자리 (미설정) | cde-skills:code |
| `ICW_SCAN` | 주석 자리 (미설정) | cde-skills:code |
| `ICW_SCHEMA` | 주석 자리 (미설정) | cde-skills:code |
| `ICW_SETTLE_H` | 주석 자리 (미설정) | cde-skills:code |
| `ICW_STATE` | 주석 자리 (미설정) | cde-skills:code |
| `ICW_TARGETS` | 주석 자리 (미설정) | cde-skills:code |
| `ICW_TARGET_MB` | 주석 자리 (미설정) | cde-skills:code |
| `JIRA_AXIS_HUB_CAP` | 주석 자리 (미설정) | cde-skills:code |
| `JIRA_AXIS_LIST_DUMP_CAP` | 주석 자리 (미설정) | cde-skills:code |
| `JIRA_AXIS_MAX_URL_BYTES` | 주석 자리 (미설정) | cde-skills:code |
| `JIRA_DEFAULT_PROJECT` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `JIRA_EMAIL` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `JIRA_TOKEN` | 값 있음 (유효성 미검증) | cde-ranking-skills:code, cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `JIRA_URL` | 값 있음 (유효성 미검증) | cde-ranking-skills:code, cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `KAFKA_CACHE_CLEAR` | 주석 자리 (미설정) | cde-skills:code |
| `KAFKA_CACHE_TTL` | 주석 자리 (미설정) | cde-skills:code |
| `KAFKA_CLUSTERS` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `KAKAOWORK_CMD_FRAGMENT` | 주석 자리 (미설정) | cde-skills:code |
| `KAKAOWORK_INSPECTOR_URL` | 주석 자리 (미설정) | cde-skills:code |
| `KAKAOWORK_SESSION_GAP` | 주석 자리 (미설정) | cde-skills:code |
| `KAKAOWORK_SPACE_ID` | 주석 자리 (미설정) | cde-skills:code |
| `KAMEK_BATCH_PATH` | 주석 자리 (미설정) | cde-ranking-skills:code, cde-skills:code, cde-skills:template |
| `KAMEK_BATCH_ROOT` | 주석 자리 (미설정) | cde-ranking-skills:code |
| `KARGO_API_URL` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `KARGO_ID` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `KARGO_PASSWORD` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `KARGO_PIPELINE_API_URL` | 주석 자리 (미설정) | cde-skills:code |
| `KCP_IAM_API_URL` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `KCP_PROMETHEUS_API_URL` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `KDP_TOKEN` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `KW_MCP_BIN` | 주석 자리 (미설정) | cde-skills:code |
| `MATRIX_API_BASE_URL` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `MATRIX_API_KEY` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `METRIC_BASE_URL` | 주석 자리 (미설정) | cde-skills:code |
| `MONGO_CDC_DEV_URI` | 주석 자리 (미설정) | cde-skills:template |
| `MONGO_CDC_HIVE_METASTORE_URIS` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `MONGO_CDC_ICEBERG_JAR` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `MONGO_CDC_MONGO_JARS_DIR` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `MONGO_CDC_PROD_URI` | 주석 자리 (미설정) | cde-skills:template |
| `MONGO_CDC_RESULT_URI` | 주석 자리 (미설정) | cde-skills:code |
| `MONGO_CDC_SHUFFLE_PARTITIONS` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `MONGO_CDC_SPARK_MASTER` | 주석 자리 (미설정) | cde-skills:code |
| `MONGO_CDC_SPARK_PYTHON` | 주석 자리 (미설정) | cde-skills:template |
| `MONGO_CDC_SPARK_QUEUE` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `MONGO_CDC_STAGE_URI` | 주석 자리 (미설정) | cde-skills:template |
| `N8N_API_KEY` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `N8N_BASE_URL` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `N8N_CBT_API_KEY` | 주석 자리 (미설정) | cde-skills:template |
| `N8N_CBT_BASE_URL` | 주석 자리 (미설정) | cde-skills:template |
| `N8N_EMAIL` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `N8N_PASSWORD` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `NEXUS_PASSWORD` | 활성 빈 값 | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `NEXUS_REGISTRY` | 주석 자리 (미설정) | cde-skills:template |
| `NEXUS_REPO_NAME` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:template |
| `NEXUS_USERNAME` | 활성 빈 값 | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `OBSIDIAN_VAULT` | 주석 자리 (미설정) | cde-skills:code |
| `ONCALL_API_TOKEN` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `ONCALL_BOT_WORKFLOW` | 주석 자리 (미설정) | cde-skills:code |
| `ONCALL_REDIS_READ_PATH` | 주석 자리 (미설정) | cde-skills:code |
| `OPENAI_API_KEY` | 값 있음 (유효성 미검증) | cde-skills:code, cde-skills:template |
| `ORG_GRAPH_HTTP_URL` | 주석 자리 (미설정) | cde-skills:code |
| `ORG_GRAPH_PASS` | 주석 자리 (미설정) | cde-skills:code |
| `ORG_GRAPH_URL` | 주석 자리 (미설정) | cde-skills:code |
| `ORG_GRAPH_USER` | 주석 자리 (미설정) | cde-skills:code |
| `PLANS_BASE_URL` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `PLANS_JIRA_PAT` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `PROMETHEUS_CDP_AIR_PROD_URL` | 주석 자리 (미설정) | cde-skills:template |
| `PROMETHEUS_CDP_AIR_STAGE_URL` | 주석 자리 (미설정) | cde-skills:template |
| `PROMETHEUS_CDP_FLINK_PROD_URL` | 주석 자리 (미설정) | cde-skills:template |
| `PROMETHEUS_CDP_FLINK_STAGE_URL` | 주석 자리 (미설정) | cde-skills:template |
| `PR_DOCS_BASE_REF` | 주석 자리 (미설정) | cde-ranking-skills:code |
| `PR_DOCS_HEAD_REF` | 주석 자리 (미설정) | cde-ranking-skills:code |
| `QUERY_MANAGER_BASE_URL` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `QUERY_MANAGER_PRODUCTION` | 주석 자리 (미설정) | cde-skills:code |
| `QUERY_MANAGER_PRODUCTIONS_URL` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `RABBIT_TRINO_HOST` | 주석 자리 (미설정) | cde-skills:template |
| `RABBIT_TRINO_PASSWORD` | 주석 자리 (미설정) | cde-skills:template |
| `RABBIT_TRINO_PORT` | 주석 자리 (미설정) | cde-skills:template |
| `RABBIT_TRINO_USER` | 주석 자리 (미설정) | cde-skills:template |
| `REDASH_API_KEY` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `REDASH_URL` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `REDIS_CLUSTER_MODE` | 주석 자리 (미설정) | cde-skills:code |
| `REDIS_HOST` | 주석 자리 (미설정) | cde-skills:code |
| `REDIS_PASSWORD` | 주석 자리 (미설정) | cde-skills:code |
| `REDIS_PORT` | 주석 자리 (미설정) | cde-skills:code |
| `SEARCH_LEGACY_API_BASE_URLS` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:template |
| `SPARK_RUN_CLUSTER_ENV` | 주석 자리 (미설정) | cde-ranking-skills:code |
| `SPARK_RUN_PRINCIPAL` | 주석 자리 (미설정) | cde-ranking-skills:code |
| `STATIC_TEST_ACCOUNT_ID` | 주석 자리 (미설정) | cde-skills:template |
| `STOVE_HOST` | 주석 자리 (미설정) | cde-skills:code |
| `STOVE_PASSWORD` | 주석 자리 (미설정) | cde-skills:code |
| `STOVE_TOKEN_PATH` | 주석 자리 (미설정) | cde-skills:code |
| `TRINO_HOST` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `TRINO_PASSWORD` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `TRINO_PORT` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `TRINO_TLS_VERIFY` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `TRINO_USER` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `VAULT_ADDR` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `VAULT_KAFKA_PATH` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `VAULT_TOKEN` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `WATCHTOWER_BASE_URL` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `WIKI_BASE_URL` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `WIKI_EMAIL` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `WIKI_TOKEN` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `YARN_RM_DEV_URL` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
| `YARN_RM_URL` | 값 있음 (유효성 미검증) | cde-ranking-skills:template, cde-skills:code, cde-skills:template |
| `YOSHI_ISLAND_REPO` | 주석 자리 (미설정) | cde-skills:code, cde-skills:template |
