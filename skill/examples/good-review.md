# Good Review Example

> This shows the expected format and depth of a frontend review report.

---

**User:** `/review-frontend https://staging.acme.com/landing`

**Claude:**

Starting review. Checking capabilities...
- Server API: connected (`$REVIEW_API_BASE_URL` set)
- Playwright MCP: not available
- Chrome MCP: not available
- DeepGaze + APCA: via server

Calling server `/review/objective`...

---

## Review Report — staging.acme.com/landing

**Overall:** ⚠️ Needs Improvement (Critical: 2, Major: 3, Minor: 5)

### Worker Warnings

None — all workers completed successfully.

### Lighthouse Scores

| Performance | Accessibility | Best Practices | SEO |
|---|---|---|---|
| 78 | 85 | 95 | 100 |

### Critical Issues

**1. Hero CTA contrast fails both APCA and WCAG 2 AA** (WCAG 1.4.3)
- Element: `.hero-cta` — text `#999` on background `#eee`
- APCA Lc: 28 (need ≥ 60 for body text)
- WCAG 2 ratio: 2.15 (need ≥ 4.5 for AA normal)
- **Fix:** Change text color to `#333` (ratio → 7.2, APCA Lc → 81)
- Viewport: desktop

**2. Mobile nav links too small** (WCAG 2.5.8)
- Element: `nav a` — 28×28px (need ≥ 44×44px)
- **Fix:** Increase padding to achieve 44px minimum tap target
- Viewport: mobile

### Major Issues

**3. No form cancel button** (Nielsen #3: User Control)
- The contact form has "Submit" but no "Cancel" or "Clear" option
- **Fix:** Add secondary "Cancel" button that resets the form

**4. CTA not in top attention zone** (DeepGaze)
- DeepGaze heatmap shows top-3 fixation on the hero image, not the CTA button
- CTA rank: #5 out of 7 detected CTAs
- **Fix:** Increase CTA size, add contrasting background, move above the hero image fold

**5. Error messages show codes, not guidance** (Nielsen #9)
- Form validation error: "Error 422" instead of explaining what's wrong
- **Fix:** "Please enter a valid email address (e.g. name@example.com)"

### Minor Issues

6. Line-height 1.2× on body text (need ≥ 1.5×) — `main p`
7. Footer links missing focus indicator — `footer a { outline: none }`
8. English readability: Flesch-Kincaid grade 11.2 (target ≤ 8 for landing page)
9. Breadcrumb not present on landing page (Nielsen #6)
10. No loading state on form submission (Nielsen #1)

### Nielsen Heuristic Summary

| # | Heuristic | Verdict |
|---|---|---|
| 1 | Visibility of System Status | ⚠️ Minor — no form submit loading |
| 2 | Match Real World | ✅ Pass |
| 3 | User Control | ⚠️ Major — no form cancel |
| 4 | Consistency | ✅ Pass |
| 5 | Error Prevention | ✅ Pass |
| 6 | Recognition > Recall | ⚠️ Minor — no breadcrumb |
| 7 | Flexibility & Efficiency | ✅ Pass |
| 8 | Aesthetic & Minimalist | ✅ Pass |
| 9 | Error Recovery | ⚠️ Major — error codes |
| 10 | Help & Documentation | ✅ Pass |

### Chinese Readability (LLM estimate)

Estimated grade: **8** (國二)
- Hard sentence: "在進行最佳化的同時兼顧使用者體驗的核心價值" (35字, 4層套疊)
- Suggestion: "優化時也照顧使用者體驗" (12字)
- Target for landing page: grade 5–7

### Links

- Full HTML report: `$REVIEW_API_BASE_URL/report/abc12345-...`
- DeepGaze heatmap: `$REVIEW_API_BASE_URL/asset/abc12345-.../deepgaze_desktop_overlay.png`
