#!/usr/bin/env bash
# Frontend Review Skill 安裝腳本 (Mac / Linux)
# 用法：cd 到 skill 目錄後跑 bash install.sh

set -euo pipefail

API_BASE_URL="https://your-server.example.com"
API_TOKEN="YOUR_REVIEW_API_TOKEN"

SKILL_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DST="$HOME/.claude/skills/frontend-review"

echo "=== Frontend Review Skill 安裝 ==="

# Step 1: 複製 skill 檔（排除 installer 自己）
echo ""
echo "[1/3] 複製 skill 檔到 $SKILL_DST"
mkdir -p "$SKILL_DST"
cp "$SKILL_SRC/SKILL.md" "$SKILL_DST/"
for dir in rubrics examples reference; do
    if [ -d "$SKILL_SRC/$dir" ]; then
        cp -R "$SKILL_SRC/$dir" "$SKILL_DST/"
    fi
done
echo "      完成。"

# Step 2: 設環境變數（append 到 shell rc）
echo ""
echo "[2/3] 設環境變數"

# 偵測 shell rc
if [ -n "${ZSH_VERSION:-}" ] || [ "$(basename "${SHELL:-}")" = "zsh" ]; then
    RC_FILE="$HOME/.zshrc"
else
    RC_FILE="$HOME/.bashrc"
fi

# 避免重複 append
if grep -q "REVIEW_API_BASE_URL" "$RC_FILE" 2>/dev/null; then
    echo "      $RC_FILE 已有 REVIEW_API_* 設定，跳過（如需更新請手動改）。"
else
    {
        echo ""
        echo "# Frontend Review Skill"
        echo "export REVIEW_API_BASE_URL=\"$API_BASE_URL\""
        echo "export REVIEW_API_TOKEN=\"$API_TOKEN\""
    } >> "$RC_FILE"
    echo "      已寫入 $RC_FILE"
fi

# Step 3: 提示
echo ""
echo "[3/3] 安裝完成"
echo ""
echo "接下來請："
echo "  1. 重新載入 shell：source $RC_FILE（或開新 terminal）"
echo "  2. 重啟 Claude Code（讓 skill 被偵測到）"
echo ""
echo "驗證：在 Claude Code 裡跑 /review-frontend https://example.com"
