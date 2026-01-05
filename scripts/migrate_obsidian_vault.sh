#!/bin/bash
# Obsidian Vault 마이그레이션 스크립트
# Usage: ./migrate_obsidian_vault.sh [--dry-run]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VAULT_PATH="/Users/megan/Documents/Obsidian Vault"

echo "========================================"
echo "Obsidian Vault 마이그레이션"
echo "========================================"
echo "Vault: $VAULT_PATH"
echo "========================================"

# 가상환경 활성화
if [ -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
    echo "✓ Virtual environment activated"
fi

# 인자 전달
python "$SCRIPT_DIR/migrate_obsidian_vault.py" --vault "$VAULT_PATH" "$@"
