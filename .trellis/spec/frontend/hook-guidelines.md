# Hook Guidelines

> How hooks are used in this project.

---

## Overview

Hooks are not part of the current frontend architecture.

The admin UI is plain HTML/CSS/JavaScript served from `static/`:

- no React
- no Vue composition API
- no custom hooks
- no client-side module system

Do not invent hook-style abstractions for small admin UI changes unless the frontend stack is intentionally upgraded first.

---

## Custom Hook Patterns

Not applicable in the current codebase.

Shared stateful logic is currently handled with:

- small file-level variables in `static/admin.js`
- helper functions such as `api()`, `toast()`, `loadDashboard()`, and `loadMappings()`
- direct DOM reads/writes by element ID

If the project later adopts a framework, this file should be rewritten to reflect that new stack instead of backfilling fake hook conventions now.

---

## Data Fetching

There is no hook-based data fetching library.

Current data fetching pattern:

- use the shared `api(path, opts)` helper in `static/admin.js`
- inject the bearer token from `authKey`
- parse JSON centrally
- normalize error messages once
- trigger UI refreshes explicitly after mutations

Keep using the shared `api()` helper for admin API calls instead of open-coding many `fetch(...)` variants.

---

## Naming Conventions

There are no `use*` naming conventions because there are no hooks.

For shared client logic, use descriptive function names such as:

- `loadDashboard`
- `checkHealth`
- `saveSettings`
- `openEditModal`

---

## Common Mistakes

- Writing guidance as if the project used React hooks when it does not.
- Adding a second data-fetching pattern instead of extending `api()`.
- Hiding important page state inside many closures when the existing file uses a small amount of explicit global state.
