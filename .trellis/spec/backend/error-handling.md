# Error Handling

> How errors are handled in this project.

---

## Overview

This project mostly uses inline error handling rather than custom exception classes. The current style is:

- use Flask app-level JSON error handlers for generic `404`, `405`, and `500` responses in `app.py`
- catch transport and persistence failures close to where they happen
- return structured JSON for non-stream endpoints
- emit SSE error payloads/events for stream endpoints

Prefer handling errors near the boundary that understands the protocol shape. Do not let Flask fall back to HTML error pages.

---

## Error Types

There are no custom Python exception classes today. Error categories are expressed through JSON payloads instead:

- `authentication_error` for invalid API key checks in `app.py`
- `proxy_error` for local request failures in `utils/http.py`
- `upstream_error` for non-200 upstream failures in streaming paths
- `save_error` for settings persistence failures in `routes/admin.py`
- `not_found`, `method_not_allowed`, `server_error` for app-level HTTP errors in `app.py`

Use these existing string `type` values when adding related behavior instead of inventing new shapes per route.

---

## Error Handling Patterns

Follow the current boundary-based pattern:

1. Parse request JSON in the route.
2. Delegate conversion and transport.
3. If transport returns an error, return it immediately.
4. For stream endpoints, convert failures to SSE output instead of normal JSON responses.

Concrete patterns in the codebase:

- `utils/http.py` centralizes outbound request failure handling in `forward_request(...)`.
- `routes/chat.py` and `routes/responses.py` do early `if err: return err` checks in non-stream paths.
- Stream handlers wrap `forward_request(..., stream=True)` and `yield` a protocol-specific error chunk/event before returning.
- `routes/admin.py` catches `OSError` in `_save_and_respond(...)` and translates it into a JSON `500`.
- `routes/messages.py` is an exception: its streaming branch uses direct `requests.post(...)` plus local `try/except`.

For new code:

- Reuse `utils.http.error_json(...)`, `routes.common.chat_error_chunk(...)`, and `routes.common.responses_error_event(...)` where they fit.
- Log the failure once near the boundary. Avoid logging the same exception in multiple layers.
- Return early after an error rather than continuing partial conversion.

---

## API Error Responses

Preferred non-stream response shape for data-plane APIs:

```json
{
  "error": {
    "message": "human-readable message",
    "type": "proxy_error"
  }
}
```

Where this is used:

- `app.py` for `404`, `405`, `500`
- `utils/http.py` via `error_json(...)`
- streaming chat errors via `chat_error_chunk(...)`

Current repo reality is slightly inconsistent:

- data-plane APIs usually use nested `error.message` and `error.type`
- some admin endpoints return flat strings like `{"error": "未授权"}` or `{"ok": false, "message": "..."}`
- Responses streaming uses `event: error` with `{"error": "..."}` rather than the nested object form

When touching existing admin endpoints, prefer preserving backward compatibility unless you are intentionally standardizing the whole surface.

---

## Common Mistakes

- Returning bare Flask/HTML errors instead of JSON. `app.py` exists specifically to avoid that.
- Handling protocol-specific stream errors inline instead of reusing shared helpers from `routes/common.py`.
- Logging secrets, request bodies, or full upstream error bodies without truncation.
- Introducing a new one-off error shape for a single endpoint.
- Catching broad exceptions too far away from the real failure source, which loses protocol context.
- Adding heavy validation/exceptions inside adapters when the existing codebase favors tolerant normalization plus minimal required-field fixes.
