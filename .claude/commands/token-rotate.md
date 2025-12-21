# Token Rotate: 토큰 갱신
---
description: 만료된 토큰을 갱신하고 모든 설정에 반영합니다
---

## 입력 필요
- $TOKEN_NAME: 갱신할 토큰 이름 (예: GITHUB_GLASSLEGO_TOKEN)
- $NEW_VALUE: 새 토큰 값

## 수행 단계

1. **기존 토큰 백업** (마스킹된 값 기록)
   ```bash
   cd /Users/megan/work/ai-env && uv run ai-env secrets get $TOKEN_NAME
   ```

2. **새 토큰 설정**
   ```bash
   cd /Users/megan/work/ai-env && uv run ai-env secrets set $TOKEN_NAME "$NEW_VALUE"
   ```

3. **모든 config 재생성**
   ```bash
   cd /Users/megan/work/ai-env && uv run ai-env sync
   ```

4. **연결 테스트** (해당되는 경우)
   - GitHub: `gh auth status`
   - Jira: MCP 서버 연결 테스트

5. **완료 보고**
   - 갱신된 토큰
   - 업데이트된 설정 파일 목록
