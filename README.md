# Frontend Review Plugin

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

一句 `/review-frontend <url>` 就能對任意網頁跑完客觀指標（Lighthouse / WCAG / DeepGaze）加主觀評估（Nielsen heuristic / 中文可讀性），產出整合報告。

## Quick Start

### 1. Server 啟動

```bash
cd server
cp .env.example .env
# 編輯 .env 填入正式的 REVIEW_API_MASTER_KEY
docker compose up -d --build
```

驗證：`curl http://localhost:5566/health` → `{"status":"ok"}`

### 2. Skill 安裝

設定環境變數：

```bash
export REVIEW_API_BASE_URL=https://your-server.example.com
export REVIEW_API_TOKEN=your-bearer-token
```

將 `skill/` 目錄安裝為 Claude Code skill。

### 3. 使用

```
/review-frontend https://staging.your-app.com
```

Claude 會自動：
1. 偵測可用工具（Server API / Playwright MCP / Chrome MCP）
2. 呼叫 server 跑客觀指標（APCA + WCAG 對比度、tap target、DeepGaze 視線預測、Lighthouse、axe-core）
3. 用截圖做 Nielsen 10 heuristics 主觀評估
4. 產出依嚴重度排序的整合報告

### API 範例

```bash
curl -s -X POST "$REVIEW_API_BASE_URL/review/objective" \
  -H "Authorization: Bearer $REVIEW_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "viewports": ["desktop", "tablet", "mobile"]}'
```

## 源碼中文文案稽核（source-scan）

除了 review 線上 URL，還能靜態掃前端專案源碼、找出「對目標讀者太難的中文文案」。**不需 render、不需登入、源碼不離開本機**——本機抽字串、只上傳字串，server 不讀檔也不存任何東西。

```bash
# 1. 本機抽中文 UI 字串（源碼留在本機）
python skill/scripts/extract_ui_strings.py <源碼根目錄> --out strings.json

# 2. 上傳字串跑稽核（expected_level: L1 國小 / L2 國中 / L3 高中 / L4 大學以上）
curl -s -X POST "$REVIEW_API_BASE_URL/review/source-scan" \
  -H "Authorization: Bearer $REVIEW_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"strings\": $(cat strings.json), \"expected_level\": \"L2\"}"
```

回傳分層稽核結果（哪些檔、哪些文案超出目標程度）。skill 流程見 `skill/reference/source-scan.md`。

## 架構

```
Client (Claude Code)          Server (FastAPI + Docker)
┌─────────────────────┐       ┌──────────────────────────┐
│ frontend-review     │       │ Playwright worker        │
│ skill (markdown)    │──────▶│ DeepGaze worker (PyTorch)│
│ + Nielsen rubrics   │ HTTPS │ Readability worker       │
│ + Chinese readability│      │ APCA-WCAG checker (JS)   │
└─────────────────────┘       │ PostgreSQL + MinIO       │
                              └──────────────────────────┘
```

- **Client 端**：pure markdown skill，教 Claude 流程編排，progressive enhancement 利用 Playwright MCP / Chrome MCP
- **Server 端**：Python FastAPI orchestrator + 4 個 worker，Docker Compose 部署

## 中文可讀性資料

中文可讀性功能依賴 NAER/TBCL 詞庫與訓練模型，因著作權考量**不隨 repo 散布**。取得與重建方式見 [`data/DATA.md`](server/app/chinese_readability/data/DATA.md)。缺少時其餘功能（Lighthouse / WCAG / DeepGaze / Nielsen）不受影響。

## 開發環境

```bash
cd server
cp .env.example .env
docker compose up -d --build

# 跑測試
docker compose exec api pytest tests/ -v

# 跑整合測試（需要 fixture-server）
docker compose exec api pytest tests/test_integration.py -v -m integration
```

## 文件

- [API Schema](docs/specs/api-schema.json)
- [中文可讀性資料取得說明](server/app/chinese_readability/data/DATA.md)

## Changelog

見 [CHANGELOG.md](CHANGELOG.md)

## License

[MIT](LICENSE)
