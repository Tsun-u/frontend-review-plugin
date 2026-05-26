# Bad Review — Common Mistakes

> These patterns reduce the review's usefulness. Avoid them.

---

## Mistake 1: Skipping Capability Detection

**Wrong:**
```
Here's my review of your page:
The colors look fine...
```

**Why it's wrong:** Did not check for server API, Playwright MCP, or Chrome MCP. The user doesn't know what was actually tested vs. eyeballed.

**Fix:** Always run Step 0 and report which capabilities are available.

---

## Mistake 2: Ignoring worker_warnings

**Wrong:**
```
Lighthouse scores:
- Performance: 0
- Accessibility: 0
This page has severe performance and accessibility problems.
```

**Why it's wrong:** Scores are 0 because lighthouse timed out, not because the page is bad. The `worker_warnings` field contained `"lighthouse: timed out after 60s"` but was never checked.

**Fix:** Always check `worker_warnings` first. If a worker failed, say:
> "Lighthouse did not complete (timed out). Scores shown as 0 are placeholders. Retry or use Google PageSpeed Insights for manual check."

---

## Mistake 3: Using LLM Vision Instead of Algorithms for Measurable Properties

**Wrong:**
```
Looking at the screenshot, the text color appears to have sufficient
contrast against the background.
```

**Why it's wrong:** Contrast is mathematically measurable. The server's APCA+WCAG checker gives exact ratios. LLM visual estimation of contrast has known systematic errors (documented in the design doc).

**Fix:** Quote the server's numbers:
> "APCA Lc: 52 (fail, need ≥ 60). WCAG 2 ratio: 3.94 (fail AA normal, pass AA large)."

---

## Mistake 4: Report Too Long / Unfocused

**Wrong:**
```
## Detailed Analysis of Every Single Element

### The Header
The header uses a sans-serif font. The navigation has 5 items.
The logo is in the top-left corner...
[continues for 2000 words of description without findings]
```

**Why it's wrong:** Describes what's there instead of what's wrong. No findings, no severity, no actionable fixes.

**Fix:** Only report findings. Each finding = problem + standard + evidence + fix. Skip elements that pass all checks.

---

## Mistake 5: Treating DeepGaze Failure as Page Failure

**Wrong:**
```
DeepGaze could not analyze the page, suggesting the visual design
is too chaotic for users to focus on.
```

**Why it's wrong:** DeepGaze failure (timeout, model error) means the worker couldn't run. It says nothing about the page's visual quality.

**Fix:** Report the failure as a worker warning and move on:
> "DeepGaze worker timed out. Saliency analysis unavailable for this review."

---

## Mistake 6: Missing Actionable Fixes

**Wrong:**
```
The tap targets are too small on mobile.
```

**Why it's wrong:** No selector, no current size, no expected size, no fix.

**Fix:**
> "Mobile tap target too small: `nav a:nth-child(2)` is 28×28px (need ≥ 44×44px). Fix: add `padding: 8px 12px` to achieve minimum 44px height."
