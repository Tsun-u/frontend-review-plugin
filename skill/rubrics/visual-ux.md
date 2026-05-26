# Visual UX — Heuristic Evaluation Rubric

Subjective visual and UX assessment. Use screenshots from the server response. Mark each item as **Pass / Issue / N/A** with evidence.

---

## ⚠️ 文字細節佐證原則（重要）

純看截圖**容易漏判文字樣式的細節**——超連結底線、刪除值的刪除線、重點文字字重、斜體等，這些在縮圖 / 抗鋸齒下肉眼難分辨。**不要純憑視覺判斷這類項目**，要用 computed style 佐證。

佐證來源優先序：

1. **server response 的 `text_styling` 欄位**（若有）—— server 端 render 後抽的 computed `text-decoration` / `font-weight` / `font-style` 等，最可靠、直接用
2. **Chrome MCP `getComputedStyle()`**（若 user 裝了 Chrome MCP）—— 對關鍵元素 `evaluate_script` 拿真實 computed 值
3. **都沒有時** —— 明確在報告標註「此項憑視覺截圖判斷、computed style 未驗證、可能不準」，**不要假裝確定**

涉及這條原則的盲點清單見最後一節「Text Styling Details」。

---

## 1. Alt Text Accuracy

Check whether `<img>` alt attributes accurately describe the image content.

**How to check:** Compare visible images in screenshots with the `alt` text from the DOM HTML.

- Decorative images should have `alt=""`
- Informative images should have descriptive alt text
- Alt text should not start with "image of" or "picture of"
- Complex images (charts, infographics) need longer descriptions

**Issue:** Hero image of a mountain sunset has `alt="img1"`.

---

## 2. Visual Hierarchy

Is there a clear reading order? Can the user tell what's most important at a glance?

**How to check:** Look at the desktop screenshot. The primary CTA should be the most visually prominent element above the fold.

- Cross-reference with DeepGaze saliency heatmap: does the top-1 fixation point align with the primary CTA?
- If not, the visual hierarchy may be fighting user attention
- Check that heading sizes decrease from h1 → h2 → h3

**Issue:** Three equally-styled buttons above the fold; saliency heatmap shows attention on the decorative image, not the CTA.

---

## 3. Action Affordance

Can users tell what's clickable and what's not?

**How to check:** Look for:

- Links that look like plain text (no underline, no color difference)
- Non-interactive elements that look clickable (underlined text that isn't a link)
- Buttons without visible boundaries on busy backgrounds
- Hover states that provide feedback (if Chrome MCP available, test hover)

**Issue:** "Learn more" text is a link but styled identically to body text.

---

## 4. Color Usage

Is color used meaningfully and accessibly?

**How to check:** The APCA/WCAG checker handles contrast mathematically. Here, check the semantic use:

- Color is not the ONLY way to convey information (colorblind users)
- Error states use icon + text, not just red color
- Brand colors don't clash with semantic colors (red = danger, green = success)
- Dark mode (if available) maintains the same semantic mapping

**Issue:** Form validation shows errors only by turning the border red; no icon or text.

---

## 5. Responsive Consistency

Do mobile and desktop versions convey the same information and hierarchy?

**How to check:** Compare desktop, tablet, and mobile screenshots from the server response.

- Key content present in all viewports (not hidden on mobile)
- Navigation accessible on mobile (hamburger menu works)
- Images appropriately sized (not overflowing or tiny)
- Touch targets adequate on mobile (the WCAG checker handles the 44px rule; here check visual spacing)

**Issue:** Desktop hero section has 3 feature cards; mobile shows only 1 with no way to see the other 2.

---

## 6. Loading and Empty States

Does the page handle transitional states gracefully?

**How to check:** If Playwright/Chrome MCP available, throttle network and observe. Otherwise, check for:

- Skeleton screens or placeholders during loading
- "No results" state for search/filter
- Offline/error state handling

**Issue:** Product list shows a blank white page while loading, then suddenly renders 50 items.

---

## 7. Text Styling Details（文字樣式細節）

**這節的所有項目都套用開頭的「文字細節佐證原則」——用 computed style 佐證、不要純視覺。**

| 盲點 | computed property | 為何重要 |
|---|---|---|
| 超連結沒底線 | `text-decoration-line` 是否含 `underline` | 連結可發現性（Nielsen #4 一致性 / 行動可見性）；純視覺常看不出細底線 |
| 刪除值刪除線 | `text-decoration-line` 是否含 `line-through` | 折扣價 / 已完成項 / 失效內容的語意；漏判會誤讀 |
| 重點文字字重 | `font-weight`（≥ 600 算粗體）| 視覺層級、強調；截圖縮放後粗細難分 |
| 斜體強調 | `font-style: italic` | 引用 / 術語 / 強調語氣 |
| 全大寫變形 | `text-transform: uppercase` | 影響可讀性（全大寫較難讀）、也影響「原文是否真的大寫」判斷 |
| 字間距異常 | `letter-spacing` | 過大過小影響可讀性 |

**檢查方式**：

- 有 server `text_styling` 欄位 → 直接讀每個文字元素的 computed 值比對
- 有 Chrome MCP → 對可疑元素跑：
  ```js
  getComputedStyle(document.querySelector('SELECTOR')).textDecorationLine
  getComputedStyle(document.querySelector('SELECTOR')).fontWeight
  ```
- 都沒有 → 報告標「文字樣式憑視覺、未經 computed 驗證」

**Issue 範例**：
- 「限時優惠 $1280」原價該有 `line-through` 但 computed 顯示 `none`——使用者看不出哪個是折扣前價
- 導覽列「關於我們」是連結但 `text-decoration-line: none` 且顏色與內文相同——computed 確認後判定行動可見性 Major Issue（不是憑「看起來好像沒底線」猜的）
