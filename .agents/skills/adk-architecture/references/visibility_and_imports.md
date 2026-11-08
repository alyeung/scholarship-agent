# Visibility & Import Conventions (ADK Best Practices)

Derived from the `google/adk-python` optimization case study:

1. **Private Helpers (`_` prefix)**:
   - Any helper function not meant to be invoked directly as an ADK `FunctionTool` must start with `_`.
   - Never attach ad-hoc attributes to Pydantic models or ADK `Agent` instances without declaring them cleanly or keeping them in private module helpers.
2. **Deferred / Lazy Heavy Imports**:
   - Defer heavy network/scraping or SQLite initialization until the tool function is actually called, keeping cold import time fast.
3. **Session State Discipline**:
   - Avoid caching mutable objects across sessions by raw `id()` reference, which can leak stale state after garbage collection. Use explicit keys in SQLite (`data/scholarships.db`) or deterministic keys.
