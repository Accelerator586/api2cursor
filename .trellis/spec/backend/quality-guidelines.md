# Quality Guidelines

> Code quality standards for backend development.

---

## Overview

The backend is a protocol proxy, so quality here means preserving compatibility across multiple API shapes while keeping route logic understandable. The current codebase favors:

- thin Flask route handlers
- reusable translation helpers in `adapters/`
- shared HTTP/SSE helpers in `utils/http.py`
- tolerant normalization over strict schema frameworks
- explicit comments/docstrings when conversion logic is non-obvious

There is no formal lint/test setup in the repo yet, so reviewers must rely more heavily on architectural consistency and manual verification.

---

## Forbidden Patterns

- Putting large protocol-conversion blocks directly inside route handlers when they belong in `adapters/`.
- Duplicating outbound request code instead of using `utils/http.forward_request(...)` without a clear reason.
- Returning HTML errors from API routes.
- Logging secrets or full credential-bearing settings payloads.
- Introducing a second source of truth for model resolution outside `settings.py`.
- Adding a new response/error shape for one code path when an existing shape already exists.
- Coupling adapter code to Flask request/response objects.

Existing exception to be aware of: `routes/messages.py` has its own streaming transport path. Treat that as legacy/special-case behavior, not the default pattern for new work.

---

## Required Patterns

- Keep orchestration in `routes/`, conversion in `adapters/`, and shared transport/parsing in `utils/`.
- Resolve target model/backend through `settings.resolve_model(...)` or `routes.common.build_route_context(...)`.
- Use `jsonify(...)` for non-stream JSON responses and `sse_response(...)` for SSE responses.
- Preserve the client-facing model name on outbound responses when the route currently does so.
- Gate verbose payload/event logs behind `Config.DEBUG`.
- Reuse existing helpers such as:
  - `normalize_request(...)`
  - `fix_response(...)`
  - `fix_stream_chunk(...)`
  - `chat_error_chunk(...)`
  - `responses_error_event(...)`
  - `log_route_context(...)`
  - `log_usage(...)`

When adding a new protocol path, prefer adding one focused adapter/helper rather than branching the same special-case logic in multiple routes.

---

## Testing Requirements

There are currently no automated tests checked into the repo. Minimum expectation for backend changes is manual verification:

- exercise the affected endpoint locally
- verify both stream and non-stream behavior when relevant
- verify model name rewriting still works
- verify the right upstream path is chosen for `openai`, `responses`, and `anthropic` backends when your change touches routing logic
- verify admin changes persist correctly to `data/settings.json`

If a change affects protocol conversion, test representative payloads rather than only the happy path.

---

## Code Review Checklist

- Is the code in the correct layer (`routes/`, `adapters/`, `utils/`, `settings.py`)?
- Does it preserve existing protocol behavior for both stream and non-stream modes?
- Does it reuse existing helpers before adding new ones?
- Are client-visible response shapes still compatible?
- Are errors returned as JSON/SSE instead of HTML/plain text where applicable?
- Are logs informative but secret-safe?
- If persistence changed, is it backward-compatible with existing `data/settings.json` files?
- If a constant or field name changed, were all protocol boundaries checked (`chat`, `responses`, `messages`, admin UI, settings)?
