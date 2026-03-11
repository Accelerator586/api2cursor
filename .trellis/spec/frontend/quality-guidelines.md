# Quality Guidelines

> Code quality standards for frontend development.

---

## Overview

Frontend quality in this project means keeping the admin UI small, clear, and dependency-free while staying safe around credentials and mapping data. The current standard is pragmatic:

- one static HTML page
- one global CSS file
- one plain JavaScript file
- centralized API/error handling through `api()`
- fast manual verification over elaborate frontend tooling

Because the UI is simple, unnecessary abstraction is usually a quality regression rather than an improvement.

---

## Forbidden Patterns

- Adding a framework-style architecture on top of one small static page without a broader project decision.
- Duplicating `fetch(...)` and error parsing logic instead of using `api()`.
- Rendering unescaped server-controlled text directly into HTML.
- Logging, echoing, or exposing API keys unnecessarily in the UI.
- Spreading more inline styles and inline event handlers when existing shared classes or listeners would work.
- Creating many one-off DOM manipulation styles instead of reusing the page's card/field/button/modal patterns.

Be aware that the current code already has some inline handlers and `innerHTML` rendering. That is existing behavior, not a best practice to expand casually.

---

## Required Patterns

- Use the shared `api()` helper in `static/admin.js` for admin API calls.
- Escape visible dynamic text with `esc()` before inserting it into HTML.
- Reuse existing CSS tokens and component classes from `static/admin.css`.
- Keep mutations followed by an explicit UI refresh such as `loadMappings()`.
- Keep credential-related UI flows simple and readable.
- Preserve the two-screen layout:
  - login screen
  - dashboard screen

For new UI work, prefer extending the existing flat structure over introducing complex client-side abstractions.

---

## Testing Requirements

There is no automated frontend test setup in the repo. Minimum manual checks for frontend changes:

- login still works with `ACCESS_API_KEY`
- saved auth state survives refresh through `sessionStorage`
- settings load and save correctly
- add, edit, and delete mapping flows still work
- health badge still reflects `/health`
- modal open/close still works by button, backdrop click, and `Escape`
- dynamic text still renders safely and legibly

If you touch rendering or escaping, test names containing quotes or unusual characters.

---

## Code Review Checklist

- Does the change fit the existing static admin architecture?
- Is `api()` reused instead of duplicated request logic?
- Are dynamic strings escaped before HTML insertion?
- Are secrets handled carefully in both UI and logs?
- Are shared CSS classes reused instead of new ad hoc styling?
- Does the change preserve current flows for login, settings, mappings, and modal behavior?
- If inline event-handler strings are involved, could special characters break them?
