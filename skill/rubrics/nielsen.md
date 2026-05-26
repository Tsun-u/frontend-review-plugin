# Nielsen 10 Heuristics — Evaluation Rubric

For each heuristic, assign a verdict: **Pass** / **Minor Issue** / **Major Issue** / **Critical Issue**. Always cite specific evidence from the screenshots, DOM, or computed styles.

> ⚠️ 涉及文字樣式的判斷（連結底線、刪除線、字重、斜體等）不要純憑視覺——截圖肉眼易漏判。用 computed style 佐證，原則見 `rubrics/visual-ux.md` 的「文字細節佐證原則」。特別是 #4 一致性、#8 美學與視覺層級這兩條常踩到。

---

## 1. Visibility of System Status

The system should keep users informed about what is going on through appropriate feedback within reasonable time.

**Check:**
- Loading indicators present during async operations
- Form submission feedback (success/error states)
- Progress indicators for multi-step flows
- Current location visible in navigation

**Good:** Spinner appears during search; toast confirms save.
**Bad:** Button clicked, nothing happens for 3 seconds, no loading state.

---

## 2. Match Between System and Real World

The system should speak the users' language, with words, phrases, and concepts familiar to the user.

**Check:**
- Jargon-free labels (or jargon appropriate to audience)
- Icons match conventional meaning
- Information flows in natural, logical order
- Date/time/currency formats match locale

**Good:** "Shopping Cart" with cart icon; dates in user's locale format.
**Bad:** "Enqueue item to procurement pipeline" on a consumer e-commerce site.

---

## 3. User Control and Freedom

Users often perform actions by mistake and need a clearly marked "emergency exit."

**Check:**
- Undo/cancel available for destructive actions
- Back button works as expected (no broken history)
- Modal dialogs have close button
- Forms have cancel/reset option

**Good:** "Undo" toast after deleting an email.
**Bad:** Delete confirmation has only "OK" button, no cancel.

---

## 4. Consistency and Standards

Users should not have to wonder whether different words, situations, or actions mean the same thing.

**Check:**
- Same action uses same label across pages
- Button styles consistent (primary/secondary/danger)
- Navigation structure consistent across sections
- Terminology consistent (don't mix "log in" / "sign in")

**Good:** Primary CTA is always blue, destructive actions always red.
**Bad:** "Submit" on one form, "Send" on another, "Go" on a third.

---

## 5. Error Prevention

Even better than good error messages is a design that prevents problems in the first place.

**Check:**
- Input validation before submission (inline, real-time)
- Confirmation dialogs for irreversible actions
- Sensible defaults that reduce input errors
- Disabled states for invalid combinations

**Good:** Password field shows strength meter and requirements in real-time.
**Bad:** Free-text date field with no format hint or date picker.

---

## 6. Recognition Rather Than Recall

Minimize the user's memory load by making objects, actions, and options visible.

**Check:**
- Recently viewed / search history available
- Form fields have labels (not just placeholders)
- Breadcrumbs or clear navigation path
- Help text visible where needed (not hidden in tooltips)

**Good:** Breadcrumb trail: Home > Category > Product.
**Bad:** 12-step wizard with no way to see previous answers.

---

## 7. Flexibility and Efficiency of Use

Accelerators — unseen by the novice user — may speed up the interaction for the expert user.

**Check:**
- Keyboard shortcuts available for power users
- Search/filter available in lists
- Responsive to different input methods (touch, keyboard, mouse)
- Bulk actions available where appropriate

**Good:** Cmd+K command palette for power users; search bar for everyone.
**Bad:** 500-item dropdown with no search/filter.

---

## 8. Aesthetic and Minimalist Design

Dialogues should not contain information that is irrelevant or rarely needed.

**Check:**
- Visual hierarchy clear (primary CTA stands out)
- No competing CTAs of equal visual weight
- Whitespace used effectively
- Content density appropriate for the context

**Good:** Landing page with one hero CTA and clean layout.
**Bad:** Homepage with 15 equally-styled buttons above the fold.

---

## 9. Help Users Recognize, Diagnose, and Recover from Errors

Error messages should be expressed in plain language, precisely indicate the problem, and constructively suggest a solution.

**Check:**
- Error messages in plain language (not error codes)
- Error messages indicate what went wrong AND how to fix it
- Form validation errors appear near the problematic field
- 404/500 pages have helpful navigation back

**Good:** "Email address is invalid. Example: name@example.com"
**Bad:** "Error 422: Unprocessable Entity"

---

## 10. Help and Documentation

Even though it is better if the system can be used without documentation, it may be necessary to provide help.

**Check:**
- Help/FAQ accessible from every page
- Contextual help (info icons, tooltips) for complex features
- Onboarding flow for first-time users
- Search within help content

**Good:** "?" icon next to "APR" field links to explanation.
**Bad:** No help section; user must email support for any question.
