#!/usr/bin/env bash
# Defuddle: URL → readable markdown.

set -euo pipefail

VAULT="${OBSIDIAN_BASE:-${HOME}/Documents/Obsidian Vault}"
SAVE_SLUG=""
SAVE_TO=""
MAX_BYTES=30720
URL=""
NO_IMAGES=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --save) SAVE_SLUG="$2"; shift 2;;
        --save-to) SAVE_TO="$2"; shift 2;;
        --no-images) NO_IMAGES=1; shift;;
        --max-bytes) MAX_BYTES="$2"; shift 2;;
        -h|--help) sed -n '2,15p' "$0"; exit 0;;
        http*|*) URL="$1"; shift;;
    esac
done

[[ -z "$URL" ]] && { echo "URL 필요" >&2; exit 2; }

extract_with_trafilatura() {
    python3 -c "
import sys, trafilatura
url = sys.argv[1]
downloaded = trafilatura.fetch_url(url)
if not downloaded:
    sys.exit(2)
md = trafilatura.extract(downloaded, output_format='markdown', include_links=True, include_images=True)
if not md:
    sys.exit(3)
print(md)
" "$URL"
}

extract_with_readability() {
    python3 -c "
import sys, urllib.request
from readability import Document
import html2text
req = urllib.request.Request(sys.argv[1], headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', errors='replace')
doc = Document(html)
title = doc.title()
content_html = doc.summary()
h = html2text.HTML2Text(); h.ignore_links = False
print(f'# {title}\n')
print(h.handle(content_html))
" "$URL"
}

extract_with_pandoc() {
    local html
    html=$(curl -fsSL --max-time 20 -A "Mozilla/5.0" "$URL")
    echo "$html" | pandoc -f html -t markdown_strict
}

OUT="$(mktemp)"
trap 'rm -f "$OUT"' EXIT

if python3 -c "import trafilatura" 2>/dev/null; then
    extract_with_trafilatura > "$OUT" 2>/dev/null && TOOL=trafilatura
elif python3 -c "import readability, html2text" 2>/dev/null; then
    extract_with_readability > "$OUT" 2>/dev/null && TOOL=readability
elif command -v pandoc >/dev/null 2>&1; then
    extract_with_pandoc > "$OUT" 2>/dev/null && TOOL=pandoc
else
    echo "추출 도구 없음 — trafilatura/readability-lxml/pandoc 중 하나 설치 필요." >&2
    echo "권장: uv tool install trafilatura" >&2
    exit 2
fi

if [[ ! -s "$OUT" ]]; then
    echo "추출 실패 (빈 결과). URL 또는 페이지 형식 점검." >&2
    exit 1
fi

if [[ "$NO_IMAGES" == 1 ]]; then
    sed -i '' -E 's/!\[[^]]*\]\([^)]+\)//g' "$OUT" 2>/dev/null || \
        sed -i -E 's/!\[[^]]*\]\([^)]+\)//g' "$OUT"
fi

# 토큰 컷오프
SIZE=$(wc -c < "$OUT")
if (( SIZE > MAX_BYTES )); then
    head -c "$MAX_BYTES" "$OUT" > "${OUT}.cut"
    echo "" >> "${OUT}.cut"
    echo "_(... ${SIZE} bytes 중 ${MAX_BYTES} 까지만 — --max-bytes 로 조정)_" >> "${OUT}.cut"
    mv "${OUT}.cut" "$OUT"
fi

DATE_KST="$(TZ='Asia/Seoul' date +%Y-%m-%d)"
HEADER=$(cat <<EOF
---
date: ${DATE_KST}
type: web
source: ${URL}
tags: [defuddle, web]
---

> 출처: [link](${URL})
> 추출: ${TOOL} | ${DATE_KST} KST

EOF
)

if [[ -n "$SAVE_SLUG" || -n "$SAVE_TO" ]]; then
    if [[ -n "$SAVE_TO" ]]; then
        DEST="$SAVE_TO"
    else
        mkdir -p "${VAULT}/00_inbox"
        DEST="${VAULT}/00_inbox/${DATE_KST}-${SAVE_SLUG}.md"
    fi
    { echo "$HEADER"; cat "$OUT"; } > "$DEST"
    echo "saved: $DEST" >&2
    cat "$DEST"
else
    echo "$HEADER"
    cat "$OUT"
fi
