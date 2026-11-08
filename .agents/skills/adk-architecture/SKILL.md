---
name: adk-architecture
description: >-
  Use this skill when modifying or extending the Google ADK agent hierarchy,
  adding new FunctionTools, or optimizing runtime/import performance in
  scholarship_agent/.
---

# Google ADK Architecture & Optimization Skill

Follow these procedures when building, modifying, or optimizing agents and tools in `scholarship_agent/`.

## Steps

1. **Read Visibility & Import Guidelines**:
   Review [visibility_and_imports.md](./references/visibility_and_imports.md) before adding new modules or modifying `scholarship_agent/agent.py`.
2. **Tool Contract Rules**:
   - ADK `LlmAgent` inspects Python type annotations and docstrings to generate JSON schemas for the model.
   - Every public tool function in `scholarship_agent/tools/` must use simple, JSON-serializable parameter types (`str`, `int`, `float`, `bool`, `list[str]`) and return a `dict[str, Any]` with a `"status"` key (`"success"` or `"error"`).
   - Prefix all internal helpers with `_` (e.g., `_sanitize_untrusted_text`, `_connect_db`).
3. **Verify with Full Test Suite**:
   Run `.venv/bin/pytest -v` to validate tool schemas, agent initialization, and end-to-end workflows.
