#!/bin/bash
# Notion to Obsidian converter script
# Usage: ./notion_to_obsidian.sh [source_dir] [target_dir] [options]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHON_SCRIPT="$PROJECT_ROOT/src/ai_assistant/notion_to_obsidian/cli.py"

# Default paths
DEFAULT_NOTION_EXPORT="$HOME/google_download/Export-ab820445-7b11-476a-872f-1506c6b717c6"
DEFAULT_OBSIDIAN_VAULT="$HOME/Documents/Obsidian Vault/NotionImport"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Notion to Obsidian Converter ===${NC}"

# Parse arguments
SOURCE="${1:-$DEFAULT_NOTION_EXPORT}"
TARGET="${2:-$DEFAULT_OBSIDIAN_VAULT}"
shift 2 2>/dev/null || true  # Remove first two args, ignore if not present

echo "Source: $SOURCE"
echo "Target: $TARGET"
echo ""

# Check if source exists
if [ ! -d "$SOURCE" ]; then
    echo -e "${YELLOW}Error: Source directory not found: $SOURCE${NC}"
    exit 1
fi

# Activate virtual environment if exists
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
    echo "Using venv: $PROJECT_ROOT/.venv"
fi

# Run converter
python "$PYTHON_SCRIPT" "$SOURCE" "$TARGET" "$@"
