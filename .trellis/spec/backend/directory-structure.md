# Directory Structure

> How backend code is organized in this project.

---

## Overview

This project is a small Flask proxy application. Backend code is organized by responsibility rather than by vertical feature slices:

- `routes/` owns HTTP entrypoints, request parsing, response shaping, and backend dispatch.
- `adapters/` owns protocol conversion between Chat Completions, Responses, and Anthropic Messages.
- `utils/` owns transport and low-level helpers such as HTTP forwarding, SSE parsing, `<think>` extraction, and tool-call repair.
- `settings.py` owns persisted runtime configuration in `data/settings.json`.
- `app.py` and `start.py` own process/bootstrap concerns.

Keep route handlers thin. If logic is about protocol translation, put it in `adapters/`. If it is reusable transport or parsing logic, put it in `utils/`.

---

## Directory Layout

```text
api2cursor/
├── app.py
├── start.py
├── config.py
├── settings.py
├── routes/
│   ├── __init__.py
│   ├── admin.py
│   ├── chat.py
│   ├── common.py
│   ├── messages.py
│   └── responses.py
├── adapters/
│   ├── cc_anthropic_adapter.py
│   ├── openai_compat_fixer.py
│   └── responses_cc_adapter.py
├── utils/
│   ├── http.py
│   ├── think_tag.py
│   └── tool_fixer.py
└── static/
    ├── admin.css
    ├── admin.html
    └── admin.js
```

---

## Module Organization

When adding backend code, place it by layer:

- Add new HTTP endpoints under `routes/`.
- Add shared request-context helpers or SSE message helpers to `routes/common.py` when multiple routes need the same behavior.
- Add protocol translators under `adapters/`. These modules should stay Flask-free and mostly operate on plain dicts/events.
- Add reusable transport, parsing, or repair helpers under `utils/`.
- Add persisted runtime settings only through `settings.py`; do not introduce ad-hoc file writes in route modules.

Typical flow:

1. Route reads JSON with `request.get_json(force=True)`.
2. Route resolves model/backend context via `settings.resolve_model()` or `routes.common.build_route_context()`.
3. Route chooses the upstream protocol path.
4. Adapter converts request/response shapes if needed.
5. `utils.http.forward_request()` performs I/O.
6. Route returns `jsonify(...)` for non-stream or `sse_response(...)` for stream.

---

## Naming Conventions

- Use `snake_case` for files, functions, and module-level helpers.
- Name route files after the public protocol or surface they serve: `chat.py`, `responses.py`, `messages.py`, `admin.py`.
- Name adapter files after the translation boundary they own: `responses_cc_adapter.py`, `cc_anthropic_adapter.py`.
- Prefer explicit directional function names such as `cc_to_messages_request()`, `responses_to_cc()`, `messages_to_cc_response()`.
- Stream converters are named as stateful classes, for example `ResponsesStreamConverter` and `AnthropicStreamConverter`.

Avoid vague names like `helpers.py` or `misc.py`; put code in the existing layer-specific module or create a narrowly named module.

---

## Examples

Good examples to follow in this codebase:

- `routes/chat.py`: route orchestration with backend dispatch and minimal transport details.
- `routes/common.py`: shared route-layer context building and logging/SSE helpers.
- `adapters/responses_cc_adapter.py`: protocol translation isolated away from Flask.
- `utils/http.py`: centralized outbound HTTP behavior and SSE parsing.
- `settings.py`: the single place for persisted configuration and model mapping resolution.
