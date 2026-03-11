# Logging Guidelines

> How logging is done in this project.

---

## Overview

This project uses Python's standard `logging` module. Logging is configured once in `start.py`:

- level: `INFO`
- format: `%(asctime)s [%(name)s] %(levelname)s: %(message)s`

Each module creates `logger = logging.getLogger(__name__)`. Logs are plain text and mostly Chinese. There is no structured JSON logging layer today.

The practical rule is: log route decisions, upstream failures, and save/auth events, but keep noisy payload dumps behind debug gating.

---

## Log Levels

- `INFO`
  - normal request summaries
  - route/backend/model selection
  - save/update/delete success messages
  - usage/token summaries
- `WARNING`
  - auth rejection
  - empty or suspicious input
  - upstream non-200 responses
- `ERROR`
  - network failures
  - settings persistence failures
  - unexpected transport exceptions

There is no separate `DEBUG` logger configuration, but route modules use local helpers such as `_dbg(...)` in `routes/chat.py` and `routes/responses.py` that only emit when `Config.DEBUG` is true.

---

## Structured Logging

Logs are not formally structured JSON, but there are a few conventions worth preserving:

- Include the route name in square brackets for route-level logs, for example via `routes.common.log_route_context(...)`.
- Include the key request dimensions that explain behavior:
  - client model
  - upstream model
  - backend
  - whether the request is streaming
- Use centralized helpers when possible so log phrasing does not drift between routes.

Existing reusable helpers:

- `routes.common.log_route_context(...)`
- `routes.common.log_usage(...)`
- local `_dbg(...)` helpers in `routes/chat.py` and `routes/responses.py`

If you need detailed payload logs, truncate them. Existing code usually limits debug dumps to the first few chunks/events and slices JSON strings to a few hundred or thousand characters.

---

## What to Log

Log these events:

- request routing decisions at route entry
- model mapping/backend selection
- token usage after non-stream completions
- settings changes in admin endpoints
- upstream non-200 responses
- request exceptions to the upstream service
- compatibility or recovery behavior that materially changes the request, such as auto-converting Responses payloads inside `routes/chat.py`

Good examples in the repo:

- `routes/common.py` for route context and usage logs
- `app.py` for auth rejection logs
- `utils/http.py` for upstream HTTP failures
- `routes/admin.py` for persistence success/failure

---

## What NOT to Log

Do not log:

- API keys from env, settings, headers, or admin forms
- full request bodies unless gated behind `Config.DEBUG` and truncated
- full streaming payloads for long sessions
- entire upstream error bodies without truncation
- raw settings snapshots that include secrets

Be especially careful in `routes/admin.py` and `static/admin.js` related flows, where users can submit proxy credentials and per-model API keys.
