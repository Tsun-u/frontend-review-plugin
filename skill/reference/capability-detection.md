# Capability Detection Logic

At the start of every review, detect what tools are available and route work accordingly.

## Detection Table

| Check | How | Result |
|---|---|---|
| Server API | `REVIEW_API_BASE_URL` env var exists and non-empty | Required. Abort if missing. |
| Server auth | `REVIEW_API_TOKEN` env var exists and non-empty | Required. Abort if missing. |
| Playwright MCP | System reminder lists `mcp__playwright__*` tools | Optional. Enables local lighthouse for comparison. |
| Chrome MCP | System reminder lists `mcp__chrome-devtools__*` tools | Optional. Enables focus order test, console check, interactive verification. |

## Routing Matrix

| Metric | Server API | Playwright MCP | Chrome MCP |
|---|---|---|---|
| APCA + WCAG contrast | Always server | — | — |
| DeepGaze saliency | Always server | — | — |
| Lighthouse scores | Server (primary) | Local (optional comparison) | — |
| axe-core a11y | Server (primary) | — | — |
| Multi-viewport screenshots | Server | Can also capture locally | — |
| DOM / text extraction | Server | Can also extract locally | — |
| English readability | Server | — | — |
| Chinese readability (v0.1) | — | — | — |
| Chinese readability (LLM stop-gap) | **You do this** | — | — |
| Nielsen heuristic evaluation | **You do this** | — | — |
| Visual UX evaluation | **You do this** | — | — |
| Focus order simulation | — | — | `press_key('Tab')` loop |
| Console errors | — | — | `list_console_messages` |
| Interactive affordance | — | — | `hover`, `click` |

## Without Optional MCPs

If neither Playwright MCP nor Chrome MCP is available, the review still covers all server-based objective metrics plus your subjective evaluation. The only gaps are:
- No focus order simulation (mention in report as "not tested")
- No console error check (mention in report)
- No interactive affordance verification (rely on visual inspection of screenshots)
