# Directory Structure

> How frontend code is organized in this project.

---

## Overview

This project does not have a separate frontend app or build pipeline. The frontend is a small admin panel served directly from Flask as static assets.

- `static/admin.html` contains the full page structure.
- `static/admin.css` contains all styles.
- `static/admin.js` contains all client-side behavior.
- `routes/admin.py` serves the page and the corresponding admin API endpoints.

The frontend is intentionally flat and dependency-free. Organize code around this simple static page model unless the project explicitly adopts a frontend framework later.

---

## Directory Layout

```text
api2cursor/
├── static/
│   ├── admin.html
│   ├── admin.css
│   └── admin.js
└── routes/
    └── admin.py
```

---

## Module Organization

Current organization is by asset type, not by component/feature folder:

- HTML document structure and screen layout live in `static/admin.html`
- reusable visual classes and theme tokens live in `static/admin.css`
- all interactive behavior, API calls, rendering, and modal logic live in `static/admin.js`
- server-side page delivery and admin APIs live in `routes/admin.py`

When extending the admin UI:

- add markup in `admin.html`
- add shared styles in `admin.css`
- add behavior in `admin.js`
- add or update server endpoints in `routes/admin.py`

Avoid creating a pseudo-`src/` structure unless the frontend architecture actually changes.

---

## Naming Conventions

- Keep asset names explicit and surface-based: `admin.html`, `admin.css`, `admin.js`.
- Use lowercase kebab-like CSS class names such as `mapping-list`, `modal-overlay`, `btn-primary`.
- Use camelCase for JavaScript function and variable names such as `loadDashboard`, `editingName`, `saveMapping`.
- Use semantic element IDs for DOM lookups such as `targetUrl`, `mappingList`, `statusBadge`.

If the UI grows, prefer adding clearly named helpers inside `admin.js` before splitting files arbitrarily.

---

## Examples

Good references in the current frontend:

- `static/admin.html`: complete page layout with login screen, dashboard, modal, and toast container
- `static/admin.css`: token-based styling with reusable classes
- `static/admin.js`: centralized API helper plus imperative UI state management
- `routes/admin.py`: the backend/frontend boundary for page serving and admin CRUD APIs
