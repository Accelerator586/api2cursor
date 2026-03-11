# Database Guidelines

> Database patterns and conventions for this project.

---

## Overview

This project does not use a database, ORM, or migration system.

Persistent state is stored in a single JSON file managed by `settings.py`:

- storage path: `data/settings.json`
- persisted keys:
  - `proxy_target_url`
  - `proxy_api_key`
  - `model_mappings`

If you are changing runtime configuration behavior, treat `settings.py` as the source of truth rather than introducing a new persistence layer ad hoc.

---

## Query Patterns

There are no queries in the database sense. Current persistence patterns are:

- read settings through `settings.get()` or `settings.resolve_model(...)`
- write settings only through `settings.save(...)`
- prefer working on a copied/updated settings dict and then saving once
- keep file I/O behind the lock inside `settings.py`

If future work needs richer persistence, document and review that architecture explicitly instead of quietly expanding this JSON-file approach.

---

## Migrations

There are no migrations today.

Schema evolution for `data/settings.json` is handled informally by:

- merging loaded data with `_DEFAULTS`
- tolerating missing keys
- falling back to defaults when the file is absent or malformed

If a new persisted field is added:

1. add it to `_DEFAULTS`
2. make reads tolerant of older files
3. avoid breaking existing deployed `settings.json` files

---

## Naming Conventions

For persisted settings keys:

- use `snake_case`
- keep names aligned with existing keys in `settings.py`
- prefer explicit names over nested or abbreviated structures

For model mappings:

- key: Cursor-facing model name
- value: object with `upstream_model`, `backend`, `target_url`, `api_key`

Do not create multiple files or hidden sidecar state for config unless there is a deliberate design change.

---

## Common Mistakes

- Assuming a database exists and designing features around transactions or migrations.
- Writing directly to `data/settings.json` outside `settings.py`.
- Adding required persisted fields without default values or backward-compatible reads.
- Treating secrets in the settings file as safe to log or echo back to clients.
- Introducing a second persistence mechanism for closely related config data.
