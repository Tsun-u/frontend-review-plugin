# Changelog

## [0.3.x] - 2026-05-23

### Added
- **source-scan**：`POST /review/source-scan` 對源碼抽出的中文 UI 文字跑可讀性稽核。隱私優先——源碼不離開本機（client `skill/scripts/extract_ui_strings.py` 本機抽字串、只上傳字串），endpoint stateless（不讀檔 / 不寫 DB / 不存報告）。三層 schema（StringAnalysis / SourceFileResult / SourceScanProject）+ `MAX_SCAN_STRINGS` 防 DoS
- Chinese readability target_level 可由 request 設定（L1-L4）
- report.html 中文 v2 schema 區塊 + Text Styling 區塊
- Lighthouse 支援帶 auth（`--extra-headers`，secrets 不落地）
- `scripts/deploy.ps1`（備份/排除 .env、staging 置換、health check retry）

### Changed
- text_styling 改 leaf-only 計數，避免巢狀重複計算
- dev scripts 移入 `_dev/` + `.dockerignore` 排除（含 `server/_dev/`）

## [0.2.x] - 2026-05

### Added
- 中文可讀性 hybrid pipeline（短文字 `tbcl_supervised_v2` RF + 長文字 `svm_sung2014_v1`），取代 v0.1 LLM stop-gap
- auth 注入（cookies / extra_headers）
- 文字樣式佐證（text_styling）+ 多 viewport 校準

### Fixed
- 公司實測 4-bug fix

## [0.1.0] - 2026-05-19

### Added
- Client-side `frontend-review` skill (SKILL.md + 3 rubrics + 2 examples + 2 reference docs)
- Server FastAPI orchestrator with Bearer auth
- Playwright worker (screenshots + DOM capture + text extraction + APCA-WCAG injection + axe-core + lighthouse CLI)
- DeepGaze worker (PyTorch CPU saliency prediction + heatmap overlay + CTA-in-attention ranking)
- Readability worker (English textstat + Chinese deferred stub for v0.2 SVM swap)
- APCA + WCAG 2 extended a11y checker (standalone JS module, 6 rules, MIT)
- MinIO asset storage with signed URL redirect
- HTML report view (Jinja2 template with color-coded scores and violation tables)
- Worker warnings mechanism (lighthouse/axe/deepgaze failures surface as warnings, not silent zero-scores)
- Docker Compose development environment (PostgreSQL + MinIO + API + fixture-server)
- Integration tests for 6 URLs (4 public + 2 self-hosted fixtures)
- API JSON schema (docs/specs/api-schema.json)

### Known limitations
- Chinese readability is client-side LLM stop-gap (SVM coming in v0.2)
- No async job queue (sync only, 120s hard cap)
- Single-tenant Bearer auth
- Lighthouse scores may show as 0 if the deployment Chromium is not a full Chrome
  installation. Check `worker_warnings` for "lighthouse: timed out" — if present,
  lighthouse did not run and the score is a placeholder, not a real measurement.
  Production deploy should verify Chrome compatibility.
- DeepGaze CTA detection requires Playwright worker to pass CTA layout data;
  pages without detectable CTA elements will show empty CTA ranking
