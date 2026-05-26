# Source Scan — 源碼中文文案稽核

靜態掃前端源碼，抽出中文 UI 文字，跑中文可讀性 pipeline，找出「對目標讀者太難的文案」。
**不需 render、不需登入、源碼不離開本機。**

## 適用情境
使用者說「掃這個前端專案的中文文案」「檢查 UI 文字會不會太難」「source scan」「文案稽核」，
且手上有源碼目錄（.jsp/.html/.js/.properties/.xml）。

## 前置
- `REVIEW_API_BASE_URL`、`REVIEW_API_TOKEN` 必須設好（同主 review skill）。
- 確認使用者給的源碼根目錄存在。

## Step 1：本機抽字串（源碼不離本機）
跑抽取腳本（在本機，server 看不到源碼）：
```bash
python skill/scripts/extract_ui_strings.py --root "<源碼根目錄>" --out /tmp/scan_strings.json
```
輸出 `/tmp/scan_strings.json` = `[{"text": "...", "source_file": "...", "line": 12}, ...]`。
跟使用者確認抽出的字串數量合理（過多代表 root 指錯或抽到雜訊）。

## Step 2：問目標讀者程度
問使用者這個專案的目標讀者程度（決定 expected_level）：
- L1：國小（最白話，對外一般大眾）
- L2：國中（對客戶、一般使用者）← 預設
- L3：高中（內部員工、管理後台）
- L4：大學以上（專業人員）

## Step 3：上傳字串、取分析
```bash
curl -s -X POST "$REVIEW_API_BASE_URL/review/source-scan" \
  -H "Authorization: Bearer $REVIEW_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"strings\": $(cat /tmp/scan_strings.json), \"expected_level\": \"L2\"}"
```
回傳 `SourceScanProject`：`expected_level` / `summary` / `files[]`。
> 若字串數 > 5000 會回 413，請縮小 root 或分批。

## Step 4：本機渲染 markdown 稽核報告
讀回傳 JSON，產 markdown 報告（存本機，例如 `<專案>_文案稽核.md`）。報告結構：

1. **稽核摘要** — 目標程度、總檔數、總字串數、超標字串數、超標率、程度分布（L1-L4 各幾筆）
2. **超標文案清單**（重點）— 依 risk_score 由高到低，每筆列：
   - `source_file:line`
   - 原文
   - required_level（pipeline 判定需要的程度） vs expected_level
   - 難詞 / 非中文片段（若有）
   - 一句改寫建議（你依語意給）
3. **各檔彙整** — 每檔的字串數、超標數、最高 required_level
4. **附註** — backend 分布（多數應為 `tbcl_supervised_v2`）；提醒短字串結果僅供參考

報告聚焦「哪些文案要改、怎麼改」，不要只貼數字。
