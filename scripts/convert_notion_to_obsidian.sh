#!/bin/bash
# Notion to Obsidian 변환 스크립트
# Usage: ./convert_notion_to_obsidian.sh [source_dir] [target_dir]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 기본 경로 설정
DEFAULT_SOURCE="/Users/megan/google_download/Export-ab820445-7b11-476a-872f-1506c6b717c6"
DEFAULT_TARGET="/Users/megan/Documents/Obsidian Vault/Notion Import"

SOURCE_DIR="${1:-$DEFAULT_SOURCE}"
TARGET_DIR="${2:-$DEFAULT_TARGET}"

echo "========================================"
echo "Notion to Obsidian Converter"
echo "========================================"
echo "Source: $SOURCE_DIR"
echo "Target: $TARGET_DIR"
echo "========================================"

# 가상환경 활성화
if [ -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
    echo "✓ Virtual environment activated"
else
    echo "⚠ Virtual environment not found, using system Python"
fi

# 변환 실행
cd "$PROJECT_ROOT"
python -m ai_assistant.notion_to_obsidian.cli "$SOURCE_DIR" "$TARGET_DIR" -v

echo ""
echo "========================================"
echo "변환 완료!"
echo "Obsidian에서 '$TARGET_DIR' 폴더를 vault로 열어보세요."
echo "========================================"
