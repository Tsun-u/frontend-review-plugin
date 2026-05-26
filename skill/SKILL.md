---
name: review-frontend
description: Frontend UI/UX review combining objective metrics (Lighthouse, WCAG, DeepGaze saliency) with subjective evaluation (Nielsen heuristics, Chinese readability). One command to get a full report.
triggers:
  - /review-frontend
  - review this URL
  - check this frontend
  - frontend sanity check
---

# Frontend Review Skill

Run a comprehensive frontend UI/UX review on any URL. Combines server-side objective metrics with your own subjective evaluation.

## Prerequisites

Two environment variables must be set:

- `REVIEW_API_BASE_URL` — server endpoint (e.g. `https://review.example.com`)
- `REVIEW_API_TOKEN` — Bearer token for server auth

If either is missing, **stop and tell the user** to configure them. Do not attempt a partial review without the server.

## Step 0: Capability Detection

Check what tools you have available:

| Capability | How to detect | What it enables |
|---|---|---|
| Playwright MCP | `mcp__playwright__*` tools in system reminder | Local lighthouse, screenshots, DOM (faster than server) |
| Chrome MCP | `mcp__chrome-devtools__*` tools | Focus order simulation, console errors, interactive checks |
| Server API | `REVIEW_API_BASE_URL` env var set | APCA-WCAG checker, DeepGaze saliency, readability |

Report your detected capabilities to the user before proceeding.

## Step 1: Collect Objective Metrics

Call the server API:

```bash
curl -s -X POST "$REVIEW_API_BASE_URL/review/objective" \
  -H "Authorization: Bearer $REVIEW_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "<TARGET_URL>", "viewports": ["desktop", "tablet", "mobile"]}'
```

This returns: lighthouse scores, axe-core violations, APCA+WCAG extended checker results, multi-viewport screenshots, DeepGaze saliency heatmap, English readability metrics, and worker_warnings.

**Check `worker_warnings` immediately.** If any worker failed (lighthouse timeout, axe injection error, deepgaze failure), note which metrics are missing and flag that conclusions based on those metrics should be treated as incomplete.

If you have Playwright MCP, you can also run lighthouse locally for comparison.

**⚠️ 自包含快照的 performance 分數不可信**：如果 review 對象是「自包含快照」/ 單檔 inline 所有資源的 HTML（CSS + 字型 base64 inline、單檔可能數 MB），lighthouse `performance` 會嚴重失真（inline 資源撐大單檔、不反映真實頁面載入）。這種情況**略過 performance 分數、或在報告標註「快照假象、非真實效能」**。a11y / 對比 / DeepGaze / 文字可讀性才是快照適用的項目（這些看 render 後的 DOM/畫面、不受 inline 影響）。

## Step 2: Subjective Evaluation

With the screenshots and data from Step 1, evaluate using these rubrics:

1. **Nielsen 10 Heuristics** — read `rubrics/nielsen.md`, evaluate each heuristic against the screenshots
2. **Chinese Readability** (if page is zh-TW/zh-CN) — read `rubrics/chinese-readability-stopgap.md`, estimate grade level and identify hard sentences
3. **Visual UX** — read `rubrics/visual-ux.md`, check alt text accuracy, visual hierarchy, action affordance

**⚠️ 文字樣式細節不要純憑視覺**：超連結底線、刪除線、字重、斜體等細節，截圖肉眼容易漏判。佐證優先序：(1) server response 的 `text_styling` 欄位 → (2) Chrome MCP `getComputedStyle()` → (3) 都沒有就在報告明確標「憑視覺、未經 computed 驗證」。詳見 `rubrics/visual-ux.md` 的「文字細節佐證原則」。

**Optional** (if Chrome MCP available):
- Tab through the page with `press_key('Tab')` to check focus order
- Check console for JS errors
- Verify hover/click affordances match visual design
- 對可疑文字元素跑 `getComputedStyle()` 佐證 text-decoration / font-weight

## Step 3: Compile Report

Read `examples/good-review.md` for format reference.

### Report Structure

Sort all findings by severity: **Critical → Major → Minor → Suggestion**

For each finding, include:
- Problem description (one sentence)
- Which standard it violates (WCAG SC number / Nielsen heuristic number)
- Element selector + screenshot viewport
- Suggested fix

### Sections

1. **Summary** — overall verdict (Pass / Needs Improvement / Critical Issues), counts by severity
2. **Worker Warnings** — if any worker failed, list what's missing and how it affects conclusions
3. **Lighthouse Scores** — performance / accessibility / best-practices / SEO
4. **WCAG + APCA Violations** — from server's extended checker, grouped by rule
5. **axe-core Violations** — from server's axe scan
6. **DeepGaze Analysis** — is the primary CTA in the top attention zone? Include heatmap link.
7. **Nielsen Heuristic Evaluation** — your subjective assessment per heuristic
8. **Readability** — English Flesch-Kincaid or Chinese estimated grade + hard sentences
9. **Visual UX Notes** — alt text, hierarchy, affordance

### Footer

- Link to full HTML report: `$REVIEW_API_BASE_URL/report/<review_id>`
- Link to DeepGaze heatmap: `$REVIEW_API_BASE_URL/asset/<review_id>/deepgaze_desktop_overlay.png`

## Authenticated Pages

If the user says "this site requires login" or the review returns a login page / 401:

1. **Ask the user for their session cookie.** Guide them:
   - Easiest: install a browser extension like Cookie-Editor, navigate to the logged-in page, export cookies as JSON
   - Alternative: DevTools → Application → Cookies → copy the session cookie (e.g. `JSESSIONID`)
2. **Add cookies to the API request:**
   ```json
   "auth": {
     "cookies": [{"name": "JSESSIONID", "value": "abc123", "domain": "internal.company.com", "path": "/"}]
   }
   ```
   For Bearer/Basic auth, use `extra_headers` instead:
   ```json
   "auth": { "extra_headers": {"Authorization": "Bearer ..."} }
   ```
3. **Warn the user:** cookies contain login credentials — they are only used for this review and discarded immediately. Never paste them in public channels.
4. **After receiving cookies:** put them ONLY in the API request `auth` field. **Never write cookie values to conversation history, files, logs, or memory.** They are secrets.
5. **Lighthouse with auth:** lighthouse now supports auth via `--extra-headers`. Cookies are converted to a `Cookie` header and passed securely via a temp file (deleted after use). If lighthouse still fails with auth, check worker_warnings for details.

## Error Handling

- **Server unreachable**: tell user to check `REVIEW_API_BASE_URL` and network
- **401 Unauthorized**: tell user to check `REVIEW_API_TOKEN`
- **504 Timeout**: the target page may be too slow or complex; suggest retrying with `skip_deepgaze: true`
- **worker_warnings present**: do NOT skip the affected section silently — state "Lighthouse did not run; scores shown as 0 are placeholders, not real scores"

## Source Scan 模式（源碼中文文案稽核）

當使用者要的不是「review 一個 URL」，而是「掃一個前端專案的中文文案會不會太難」
（手上有源碼目錄、不需 render、不需登入），改走 source-scan 流程，
詳見 `reference/source-scan.md`。

核心差異：源碼**不離開本機**——本機抽字串、只上傳字串到 `POST /review/source-scan`，
server 不讀檔、不存任何東西，報告在本機渲染。

## Related Files

- `rubrics/nielsen.md` — Nielsen 10 heuristics evaluation rubric
- `rubrics/chinese-readability-stopgap.md` — Chinese readability LLM stop-gap rubric
- `rubrics/visual-ux.md` — Visual layer UX heuristic
- `examples/good-review.md` — Good review report example
- `examples/bad-review.md` — Common mistakes to avoid
- `reference/api-endpoints.md` — Server API quick reference
- `reference/capability-detection.md` — Capability detection logic
- `reference/source-scan.md` — 源碼中文文案稽核 workflow
