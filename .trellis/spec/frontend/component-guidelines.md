# Component Guidelines

> How components are built in this project.

---

## Overview

This frontend is not componentized with React/Vue. "Components" here means reusable UI sections built from plain HTML, CSS classes, and JavaScript helpers.

Current composition style:

- one page shell in `static/admin.html`
- repeated visual patterns expressed through shared CSS classes such as `.card`, `.field`, `.btn`, `.tag`, `.modal`
- behavior attached through global JavaScript functions in `static/admin.js`

Favor extending these existing page sections and class patterns rather than introducing a framework-like abstraction style into one file.

---

## Component Structure

The current page is organized into a few reusable UI sections:

- login screen
- dashboard header
- global settings card
- model mappings card
- reusable modal overlay
- toast notification area

When adding a new UI section:

1. add semantic markup to `admin.html`
2. reuse existing wrapper patterns like `.card`, `.field`, `.input-wrap`, `.btn`
3. hook behavior up in `admin.js`
4. keep business data loading in the shared `api()` helper flow

This repo currently prefers one reusable modal for create/edit flows instead of separate pages or many bespoke dialogs.

---

## Props Conventions

There are no props in the framework sense.

Equivalent conventions in this project are:

- pass data into rendering through function arguments in `admin.js`
- read form state directly from DOM elements by ID
- keep small global UI state in file-level variables such as `authKey` and `editingName`
- use `data` returned from the admin API directly rather than wrapping it in client-side model classes

If you add helper functions, keep signatures explicit and small. Avoid hidden dependencies on many globals when a value can be passed in directly.

---

## Styling Patterns

Styles are global CSS in `static/admin.css`.

Use the existing styling approach:

- theme tokens in `:root`
- reusable component classes for cards, buttons, tags, fields, modal, toast
- modifier classes for variants such as `.btn-primary`, `.btn-green`, `.btn-red`, `.btn-sm`
- flexbox-based layout
- class toggles for state such as `.modal-overlay.active`

Prefer class-based styling over new inline styles. The current codebase still has a few inline style attributes and JS style mutations, but those should be treated as existing debt, not the default pattern to copy.

---

## Accessibility

Accessibility is basic today but still worth preserving:

- inputs are paired with visible labels
- password fields can be toggled visible
- the modal can be dismissed by clicking the backdrop or pressing `Escape`
- the login input supports pressing `Enter`

When extending the page:

- keep labels and button text explicit
- preserve keyboard-triggered actions where there is already a pattern
- do not replace text buttons with icon-only controls unless the label remains clear

There are no ARIA-heavy patterns in the current page, so additions should stay simple and understandable.

---

## Common Mistakes

- Mixing too much presentation into inline `style=""` attributes instead of shared CSS classes.
- Adding more inline `onclick` handlers without considering whether a centralized event listener would be clearer.
- Rendering unescaped server data into HTML. Use `esc()` for visible text.
- Treating string escaping for HTML as sufficient for inline event-handler attributes; it is not robust for quote-heavy values.
- Creating highly custom one-off section markup when existing `.card`, `.field`, and `.btn` patterns already fit.
