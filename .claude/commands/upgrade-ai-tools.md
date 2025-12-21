# Upgrade AI Tools: AI CLI 도구 일괄 업그레이드
---
description: Claude Code, Codex CLI, Gemini CLI를 최신 버전으로 업그레이드합니다
---

다음을 순서대로 실행해주세요:

## 1. 현재 버전 확인

```bash
echo "=== 현재 설치 버전 ==="
echo -n "Claude Code: " && (claude --version 2>/dev/null || echo "미설치")
echo -n "Codex CLI:   " && (codex --version 2>/dev/null || echo "미설치")
echo -n "Gemini CLI:  " && (gemini --version 2>/dev/null || echo "미설치")
```

## 2. 업그레이드 실행

각 도구를 순서대로 업그레이드합니다:

**Claude Code** (네이티브 설치):
```bash
claude update
```
만약 `claude update` 가 실패하면 npm 방식으로 폴백:
```bash
npm install -g @anthropic-ai/claude-code@latest
```

**Codex CLI**:
```bash
npm install -g @openai/codex@latest
```

**Gemini CLI**:
```bash
npm install -g @google/gemini-cli@latest
```

## 3. 업그레이드 결과 확인

```bash
echo "=== 업그레이드 후 버전 ==="
echo -n "Claude Code: " && (claude --version 2>/dev/null || echo "미설치")
echo -n "Codex CLI:   " && (codex --version 2>/dev/null || echo "미설치")
echo -n "Gemini CLI:  " && (gemini --version 2>/dev/null || echo "미설치")
```

## 4. 결과 보고

- 각 도구의 이전 버전 → 새 버전 변경사항
- 업그레이드 실패한 도구가 있으면 원인과 해결 방법 안내
