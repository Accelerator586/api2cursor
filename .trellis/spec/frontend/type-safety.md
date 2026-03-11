# Type Safety

> Type safety patterns in this project.

---

## Overview

The frontend does not use TypeScript or another static type system today.

Current admin UI stack:

- plain HTML
- plain CSS
- plain browser JavaScript

Because of that, "type safety" in this project is mostly about keeping request/response shapes simple and validating critical assumptions at runtime through defensive UI logic.

---

## Type Organization

Not applicable in the TypeScript sense.

There are no shared type definition files, interfaces, or generated API types for the frontend. Data contracts are implied by:

- `routes/admin.py` response payloads
- DOM element IDs used in `static/admin.js`
- the shape of mapping objects returned from `/api/admin/mappings`

If the project later adopts TypeScript, revisit this file rather than treating today's JavaScript as if it were typed.

---

## Validation

There is no frontend schema validation library.

Current runtime validation is lightweight:

- required-field checks with `.trim()`
- content-type checks inside `api()`
- normalization of server-side error payloads into a user-visible message

Critical validation still lives mainly on the server side. Frontend changes should keep client assumptions minimal and fail with readable messages when the API shape is unexpected.

---

## Common Patterns

Given the lack of static typing, favor these practical patterns:

- keep API payloads flat and explicit
- use clear variable names for server data
- check for missing objects before reading nested fields
- centralize response parsing in `api()`
- keep rendering logic small enough that the expected object shape is obvious

If a new UI feature needs more complex data handling, consider extracting focused helpers before the file becomes hard to reason about.

---

## Forbidden Patterns

- Writing guidance that assumes TypeScript exists when it does not.
- Creating pseudo-type conventions in comments that are not enforced anywhere.
- Scattering response-shape assumptions across many functions instead of normalizing them centrally.
- Adding a client-side validation dependency for a tiny form flow without a strong need.
