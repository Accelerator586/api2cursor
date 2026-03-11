# State Management

> How state is managed in this project.

---

## Overview

State management in this project is intentionally simple and imperative. The admin UI uses:

- file-level mutable variables in `static/admin.js`
- the DOM as the primary source of truth for form fields
- `sessionStorage` for the auth key across page reloads
- explicit reloads after mutations instead of a client-side cache/store

There is no Redux, Zustand, MobX, or framework state system.

---

## State Categories

Current state falls into four buckets:

- UI session state
  - `authKey`
  - `editingName`
- form state
  - values read directly from inputs like `#targetUrl`, `#proxyKey`, `#mName`, `#mUpstream`
- server state
  - settings payload from `/api/admin/settings`
  - mapping list from `/api/admin/mappings`
- persisted browser state
  - `_ak` in `sessionStorage`

Derived state is kept lightweight and computed inline, for example:

- backend tag class/label derived from `m.backend`
- `hasOverride` derived from `target_url || api_key`

---

## When to Use Global State

In the current architecture, only keep a value in file-global state when it is needed across multiple handlers and is not already owned by the DOM:

- current auth token
- the name being edited in the modal

Do not promote ordinary form field values into extra globals; the current convention is to read them directly from the inputs when needed.

If more than a few globals become necessary, that is a sign the frontend architecture may need to evolve, not a reason to keep adding ad hoc globals forever.

---

## Server State

Server state is fetched on demand and refreshed explicitly:

- `loadDashboard()` fetches settings, then mappings, then health
- `saveSettings()` writes, then shows a toast
- `saveMapping()` and `deleteMapping()` mutate the server, then call `loadMappings()`

There is no cache invalidation layer or optimistic update system. Prefer consistency and simplicity:

- fetch through `api()`
- after mutation, reload the affected data
- render the latest server response

For this small admin panel, full-list rerendering is the normal pattern.

---

## Common Mistakes

- Duplicating DOM state into many JavaScript globals.
- Introducing a second fetch/error path instead of reusing `api()`.
- Forgetting to refresh UI state after a successful mutation.
- Treating `innerHTML` rendering as safe for all contexts; visible text is escaped with `esc()`, but inline handler interpolation is still fragile.
- Encoding persistent application data in the browser when the source of truth already lives on the server in `settings.py`.
