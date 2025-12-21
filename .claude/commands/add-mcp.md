# Add MCP: 새 MCP 서버 추가
---
description: 새로운 MCP 서버를 ai-env에 등록합니다
---

## 입력 필요
- $SERVER_NAME: MCP 서버 이름
- $SERVER_TYPE: stdio 또는 sse
- $COMMAND 또는 $URL: 실행 명령 또는 SSE URL

## 수행 단계

1. **기존 MCP 서버 목록 확인**
   ```bash
   cat /Users/megan/work/ai-env/config/mcp_servers.yaml
   ```

2. **config/mcp_servers.yaml에 새 서버 추가**
   - enabled: true
   - type: $SERVER_TYPE
   - command/url 설정
   - targets 설정 (claude_desktop, antigravity, claude_local 등)
   - 필요한 env_keys 추가

3. **필요한 환경변수가 있다면 .env에 추가**
   ```bash
   cd /Users/megan/work/ai-env && uv run ai-env secrets set NEW_KEY "value"
   ```

4. **설정 동기화**
   ```bash
   cd /Users/megan/work/ai-env && uv run ai-env sync
   ```

5. **결과 확인**
   - 생성된 config에 새 서버가 포함되었는지 확인
   - MCP 서버 연결 테스트
