#!/usr/bin/env bash
# security_guard.sh — PreToolUse hook
# 위험한 Bash 커맨드를 사전 차단한다.
# Hook type: PreToolUse (Bash tool만 대상)

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')

# Bash tool만 검사
[[ "$TOOL_NAME" != "Bash" ]] && exit 0

COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
[[ -z "$COMMAND" ]] && exit 0

# 위험 패턴 목록
DANGEROUS_PATTERNS=(
  # --- 데이터베이스 ---
  "DROP TABLE"
  "DROP DATABASE"
  "TRUNCATE TABLE"
  "DELETE FROM.*WHERE 1"

  # --- 파일시스템 ---
  "rm -rf /"
  "rm -rf /*"
  "rm -rf ~"
  "rm -rf \$HOME"

  # --- Git 파괴적 명령 ---
  "git push --force main"
  "git push --force master"
  "git push -f main"
  "git push -f master"
  "git push --force-with-lease main"
  "git push --force-with-lease master"

  # --- 레포지토리 삭제 ---
  "gh repo delete"
  "gh api -X DELETE.*/repos/"
  "curl.*-X DELETE.*/repos/"

  # --- Kafka ---
  "kafka-topics.*--delete"

  # --- HDFS 프로덕션 ---
  "hdfs dfs -rm -r /user/prod"
  "hdfs dfs -rm -r /data/prod"
  "hdfs dfs -rmdir /user/prod"

  # --- Kubernetes 프로덕션 ---
  "kubectl delete namespace prod"
  "kubectl delete ns prod"
  "kubectl delete --all"

  # --- Docker 전체 정리 ---
  "docker system prune -a"
  "docker rm -f \$(docker ps"

  # --- 시크릿 노출 ---
  "echo.*TOKEN"
  "echo.*SECRET"
  "echo.*PASSWORD"
  "cat .env$"
  "cat .env "
)

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
  if echo "$COMMAND" | grep -qiE "$pattern"; then
    jq -n --arg reason "🚨 위험 커맨드 차단: $pattern" \
      '{ hookSpecificOutput: {
           hookEventName: "PreToolUse",
           permissionDecision: "deny",
           permissionDecisionReason: $reason
         }}'
    exit 2
  fi
done

exit 0
