#!/bin/bash
# MCP 서버 설정 테스트 스크립트

set -e

echo "🧪 MCP 서버 설정 테스트"
echo "================================"
echo ""

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 테스트 결과 저장
declare -a results

# 1. Claude Code (현재 프로젝트)
echo "1️⃣  Claude Code (로컬 프로젝트 설정)"
echo "   경로: .claude/settings.local.json"
if [ -f ".claude/settings.local.json" ]; then
    echo -e "   ${GREEN}✓${NC} 설정 파일 존재"
    # MCP 서버 개수 확인
    server_count=$(jq '.mcpServers | length' .claude/settings.local.json 2>/dev/null || echo "0")
    echo "   📊 MCP 서버 개수: $server_count"

    # 각 서버 이름 출력
    echo "   서버 목록:"
    jq -r '.mcpServers | keys[]' .claude/settings.local.json 2>/dev/null | while read server; do
        echo "      - $server"
    done
    results+=("claude_local:OK")
else
    echo -e "   ${RED}✗${NC} 설정 파일 없음"
    results+=("claude_local:FAIL")
fi
echo ""

# 2. Claude Code (글로벌)
echo "2️⃣  Claude Code (글로벌 설정)"
echo "   경로: ~/.claude/settings.json"
if [ -f "$HOME/.claude/settings.json" ]; then
    echo -e "   ${GREEN}✓${NC} 설정 파일 존재"
    server_count=$(jq '.mcpServers | length' ~/.claude/settings.json 2>/dev/null || echo "0")
    echo "   📊 MCP 서버 개수: $server_count"
    results+=("claude_global:OK")
else
    echo -e "   ${RED}✗${NC} 설정 파일 없음"
    results+=("claude_global:FAIL")
fi
echo ""

# 3. Claude Desktop
echo "3️⃣  Claude Desktop"
echo "   경로: ~/Library/Application Support/Claude/claude_desktop_config.json"
if [ -f "$HOME/Library/Application Support/Claude/claude_desktop_config.json" ]; then
    echo -e "   ${GREEN}✓${NC} 설정 파일 존재"
    server_count=$(jq '.mcpServers | length' "$HOME/Library/Application Support/Claude/claude_desktop_config.json" 2>/dev/null || echo "0")
    echo "   📊 MCP 서버 개수: $server_count"
    results+=("claude_desktop:OK")
else
    echo -e "   ${RED}✗${NC} 설정 파일 없음"
    results+=("claude_desktop:FAIL")
fi
echo ""

# 4. Codex (글로벌)
echo "4️⃣  Codex (글로벌 설정)"
echo "   경로: ~/.codex/config.toml"
if [ -f "$HOME/.codex/config.toml" ]; then
    echo -e "   ${GREEN}✓${NC} 설정 파일 존재"
    # TOML 파일이므로 [mcp.servers] 섹션 확인
    if grep -q "\[mcp.servers\]" ~/.codex/config.toml; then
        server_count=$(grep -c "^\[mcp.servers\." ~/.codex/config.toml || echo "0")
        echo "   📊 MCP 서버 개수: $server_count"
    else
        echo "   ⚠️  MCP 서버 설정 없음"
    fi
    results+=("codex_global:OK")
else
    echo -e "   ${RED}✗${NC} 설정 파일 없음"
    results+=("codex_global:FAIL")
fi
echo ""

# 5. Codex (로컬)
echo "5️⃣  Codex (로컬 프로젝트 설정)"
echo "   경로: .codex/config.toml"
if [ -f ".codex/config.toml" ]; then
    echo -e "   ${GREEN}✓${NC} 설정 파일 존재"
    if grep -q "\[mcp.servers\]" .codex/config.toml; then
        server_count=$(grep -c "^\[mcp.servers\." .codex/config.toml || echo "0")
        echo "   📊 MCP 서버 개수: $server_count"
    fi
    results+=("codex_local:OK")
else
    echo -e "   ${RED}✗${NC} 설정 파일 없음"
    results+=("codex_local:FAIL")
fi
echo ""

# 6. Gemini (글로벌)
echo "6️⃣  Gemini CLI (글로벌 설정)"
echo "   경로: ~/.gemini/settings.json"
if [ -f "$HOME/.gemini/settings.json" ]; then
    echo -e "   ${GREEN}✓${NC} 설정 파일 존재"
    server_count=$(jq '.mcpServers | length' ~/.gemini/settings.json 2>/dev/null || echo "0")
    echo "   📊 MCP 서버 개수: $server_count"
    results+=("gemini_global:OK")
else
    echo -e "   ${RED}✗${NC} 설정 파일 없음"
    results+=("gemini_global:FAIL")
fi
echo ""

# 7. Gemini (로컬)
echo "7️⃣  Gemini CLI (로컬 프로젝트 설정)"
echo "   경로: .gemini/settings.local.json"
if [ -f ".gemini/settings.local.json" ]; then
    echo -e "   ${GREEN}✓${NC} 설정 파일 존재"
    server_count=$(jq '.mcpServers | length' .gemini/settings.local.json 2>/dev/null || echo "0")
    echo "   📊 MCP 서버 개수: $server_count"

    echo "   서버 목록:"
    jq -r '.mcpServers | keys[]' .gemini/settings.local.json 2>/dev/null | while read server; do
        echo "      - $server"
    done
    results+=("gemini_local:OK")
else
    echo -e "   ${RED}✗${NC} 설정 파일 없음"
    results+=("gemini_local:FAIL")
fi
echo ""

# 8. Antigravity (Gemini MCP)
echo "8️⃣  Antigravity (Gemini MCP 클라이언트)"
echo "   경로: ~/.gemini/antigravity/mcp_config.json"
if [ -f "$HOME/.gemini/antigravity/mcp_config.json" ]; then
    echo -e "   ${GREEN}✓${NC} 설정 파일 존재"
    server_count=$(jq '.mcpServers | length' ~/.gemini/antigravity/mcp_config.json 2>/dev/null || echo "0")
    echo "   📊 MCP 서버 개수: $server_count"
    results+=("antigravity:OK")
else
    echo -e "   ${RED}✗${NC} 설정 파일 없음"
    results+=("antigravity:FAIL")
fi
echo ""

# 9. 환경변수 확인
echo "9️⃣  환경변수 확인"
echo "   경로: .env"
if [ -f ".env" ]; then
    echo -e "   ${GREEN}✓${NC} .env 파일 존재"

    # 주요 환경변수 체크
    check_env_var() {
        if grep -q "^$1=" .env; then
            value=$(grep "^$1=" .env | cut -d'=' -f2)
            if [ -n "$value" ]; then
                echo -e "      ${GREEN}✓${NC} $1 설정됨"
            else
                echo -e "      ${YELLOW}⚠${NC}  $1 값 없음"
            fi
        else
            echo -e "      ${RED}✗${NC} $1 없음"
        fi
    }

    check_env_var "ANTHROPIC_API_KEY"
    check_env_var "OPENAI_API_KEY"
    check_env_var "GOOGLE_API_KEY"
    check_env_var "GITHUB_GLASSLEGO_TOKEN"
    check_env_var "JIRA_PERSONAL_TOKEN"
    check_env_var "CONFLUENCE_PERSONAL_TOKEN"
    check_env_var "NOTION_API_TOKEN"

    results+=("env:OK")
else
    echo -e "   ${RED}✗${NC} .env 파일 없음"
    results+=("env:FAIL")
fi
echo ""

# 결과 요약
echo "================================"
echo "📊 테스트 결과 요약"
echo "================================"

pass_count=0
fail_count=0

for result in "${results[@]}"; do
    IFS=':' read -r name status <<< "$result"
    if [ "$status" = "OK" ]; then
        echo -e "${GREEN}✓${NC} $name"
        ((pass_count++))
    else
        echo -e "${RED}✗${NC} $name"
        ((fail_count++))
    fi
done

echo ""
echo "총계: ${GREEN}$pass_count 성공${NC} / ${RED}$fail_count 실패${NC}"
echo ""

# 다음 단계 안내
if [ $fail_count -gt 0 ]; then
    echo -e "${YELLOW}⚠️  일부 설정이 누락되었습니다.${NC}"
    echo ""
    echo "다음 명령으로 설정을 동기화하세요:"
    echo "  uv run ai-env sync"
    echo ""
    exit 1
else
    echo -e "${GREEN}✅ 모든 설정이 정상입니다!${NC}"
    echo ""
    echo "각 도구에서 MCP 서버를 테스트하려면:"
    echo "  • Claude Code: 현재 세션에서 MCP 도구 사용해보기"
    echo "  • Claude Desktop: 앱 재시작 후 MCP 도구 확인"
    echo "  • Gemini: gemini 명령으로 MCP 서버 확인"
    echo "  • Codex: codex 명령으로 MCP 서버 확인"
    echo ""
fi
