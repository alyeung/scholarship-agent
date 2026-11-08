# Scholarship Agent — Harness Engineering & Repository Rules

This repository implements a **Graduate School Scholarship Finder** multi-agent application built with **Google Agent Development Kit (`google-adk`)** and augmented with **Antigravity Harness Engineering** (`AGENTS.md`, `.agents/skills/`, and `.agents/hooks.json`).

## 1. Repository Architecture

```text
scholarship agent/
├── AGENTS.md                        # Always-on repository rules & architectural boundaries
├── profile.yaml                     # User-configurable graduate student profile
├── cli.py                           # CLI & autonomous batch runner (discovery, matching, dashboard, ADK chat)
├── scholarship_agent/               # Google ADK Python package (`adk web` / `adk run` compatible)
│   ├── __init__.py                  # Exports `root_agent` with lazy-import fast startup
│   ├── agent.py                     # Multi-agent orchestration (Coordinator + 4 specialist subagents)
│   ├── models.py                    # Pydantic schemas for profiles, scholarships, fit scores, and essays
│   └── tools/                       # Deterministic ADK FunctionTools
│       ├── profile_tools.py         # Profile loader & updater (`profile.yaml`)
│       ├── search_tools.py          # Curated catalog + live web search & HTML page scraper with sanitization
│       ├── eligibility_tools.py     # Deterministic 0-100 Fit Score & eligibility evaluator
│       ├── tracker_tools.py         # SQLite (`scholarships.db`), CSV & Markdown Dashboard exporter
│       └── essay_tools.py           # Personal statement & fellowship essay workspace manager
├── .agents/                         # Antigravity Harness Engineering customizations
│   ├── hooks.json                   # PreToolUse safety gate hook config
│   ├── scripts/pre_tool_guard.py    # Deterministic & untrusted-input guard script
│   └── skills/                      # Progressive-disclosure modular skills
│       ├── adk-architecture/        # ADK conventions, lazy imports, visibility rules
│       ├── scholarship-discovery/   # Runbook for live web scholarship discovery & verification
│       └── essay-tailoring/         # Runbook for drafting grad fellowship essays
├── data/                            # Local persistence (SQLite DB, CSV export, Markdown dashboard, essays)
└── tests/                           # Full pytest suite verifying tools, schemas, and ADK agents
```

## 2. Core Guardrails (From the ADK Gemini 4 Argon Case Study)

1. **Public Tool Schema Stability**:
   - Never alter the function signature or parameter names of public ADK tool functions in `scholarship_agent/tools/` without updating all agent instructions and unit tests.
   - Internal helper functions in any module MUST be prefixed with a single underscore (`_helper_name`) so they are not accidentally exposed as public ADK tools.
2. **Fast Cold Imports**:
   - Keep `scholarship_agent/__init__.py` lightweight and avoid executing network requests or database migrations at module import time.
3. **Zero Hallucinated Scholarship Data**:
   - Never fabricate scholarship URLs, award amounts, or deadlines.
   - When scraping live web pages, always record `source_url` and `verification_status` (`verified_catalog`, `scraped_live`, or `needs_manual_check`).
4. **Prompt Injection Defense on External Web Content**:
   - All scraped HTML/text from external scholarship websites MUST pass through `_sanitize_untrusted_text()` in `scholarship_agent/tools/search_tools.py` before returning to the model.
5. **Verification Before Completion**:
   - Always run `.venv/bin/pytest` after modifying any file under `scholarship_agent/` or `cli.py` and verify 100% test pass rate.
