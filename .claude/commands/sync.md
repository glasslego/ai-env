# Sync: MCP 설정 동기화
---
description: ai-env의 MCP 설정을 글로벌 환경에 동기화합니다
---

다음을 수행해주세요:

1. **현재 토큰 상태 확인**
   ```bash
   cd /Users/megan/work/ai-env && uv run ai-env secrets list
   ```

2. **설정 파일 동기화**
   ```bash
   cd /Users/megan/work/ai-env && uv run ai-env sync
   ```

3. **동기화 결과 확인**
   - Claude Desktop: ~/Library/Application Support/Claude/claude_desktop_config.json
   - Antigravity: ~/.gemini/antigravity/mcp_config.json
   - Shell exports: ./generated/shell_exports.sh

4. **변경사항 보고**
   - 업데이트된 MCP 서버 목록
   - 새로 추가된 환경변수
