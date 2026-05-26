# Server API Quick Reference

Base URL: `$REVIEW_API_BASE_URL` (set as environment variable)
Auth: `Authorization: Bearer $REVIEW_API_TOKEN`

---

## POST /review/objective

Run a full objective review on a URL.

**Request:**
```json
{
  "url": "https://example.com",
  "viewports": ["desktop", "tablet", "mobile"],
  "options": {
    "skip_deepgaze": false,
    "skip_wcag_extended": false,
    "use_psi_api": true
  }
}
```

**Response (200):** Full review result including lighthouse, axe_violations, wcag_extended, screenshots, deepgaze, readability, and worker_warnings.

**Errors:** 400 (bad URL), 401 (auth), 422 (validation), 504 (timeout)

**Typical time:** 60–90 seconds.

---

## POST /review/source-scan

對 client 本機抽出的中文 UI 字串跑可讀性稽核。**Stateless**：server 只收字串、不讀檔、不寫 DB、不存報告（源碼不離開本機）。

抽取在本機跑（`skill/scripts/extract_ui_strings.py`），只上傳字串。

**Request:**
```json
{
  "strings": [
    {"text": "請輸入查詢號碼", "source_file": "client/order.jsp", "line": 42}
  ],
  "expected_level": "L2",
  "jargon_whitelist": ["API", "URL"]
}
```
- `expected_level`：目標讀者程度 `L1`（國小）/ `L2`（國中，預設）/ `L3`（高中）/ `L4`（大學以上）
- `jargon_whitelist`（選填）：視為熟詞、不計入難度的英文片段
- 上限 `MAX_SCAN_STRINGS = 5000`，超過回 413

**Response (200):** `SourceScanProject` —
```
{ expected_level, summary{total_files, total_strings, flagged_strings, flag_rate,
  level_distribution, backend_distribution}, files[{source_file, string_count,
  flagged_count, max_required_level, strings[StringAnalysis]}] }
```
每筆 `StringAnalysis` 含 `required_level` / `risk_score` / `flag`（= required > expected）/ `backend` / `hard_words` / `jargon_detected` / `warnings`。`files` 按 flagged 數由高到低排序。

**Errors:** 400（strings 空）、401（auth）、413（超過 5000 筆）、422（validation）、500（內部）

---

## GET /asset/{review_id}/{filename}

Retrieve a stored asset (screenshot, heatmap, DOM HTML). Returns a 302 redirect to a time-limited signed URL.

**Common filenames:**
- `desktop.png`, `tablet.png`, `mobile.png` — viewport screenshots
- `dom.html` — captured DOM
- `deepgaze_desktop_heatmap.png` — raw saliency map
- `deepgaze_desktop_overlay.png` — saliency overlaid on screenshot

---

## GET /report/{review_id}

View the review as an HTML page in a browser. Useful for sharing with non-technical stakeholders.

---

## GET /health

No auth required. Returns `{"status": "ok"}` if the server is running.

Full API schema: `docs/specs/api-schema.json`
