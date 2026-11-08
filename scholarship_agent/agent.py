"""Google ADK Multi-Agent Hierarchy for the Graduate School Scholarship Finder.

Compatible with:
  - `adk web` (Interactive Web UI)
  - `adk run scholarship_agent` (Interactive CLI)
  - `python cli.py ...` (Direct CLI & autonomous workflow runner)
"""

from __future__ import annotations

import os
from google.adk.agents import LlmAgent

from .tools.eligibility_tools import (
    batch_score_scholarships,
    evaluate_scholarship_fit,
)
from .tools.essay_tools import (
    get_essay_prompt_context,
    list_essay_drafts,
    save_essay_draft,
)
from .tools.profile_tools import (
    get_student_profile,
    update_profile_setting,
)
from .tools.search_tools import (
    scrape_scholarship_page,
    search_curated_fellowships,
    search_scholarships_web,
)
from .tools.tracker_tools import (
    list_tracked_scholarships,
    sync_and_export_tracker,
    update_scholarship_status,
)

DEFAULT_MODEL = os.environ.get("SCHOLARSHIP_AGENT_MODEL", "gemini-2.5-flash")

# -----------------------------------------------------------------------------
# 1. Discovery & Web Scraping Subagent
# -----------------------------------------------------------------------------
discovery_agent = LlmAgent(
    name="discovery_agent",
    model=DEFAULT_MODEL,
    description=(
        "Searches curated graduate fellowships, executes live web searches for grad school "
        "scholarships, and scrapes official scholarship web pages with prompt-injection sanitization."
    ),
    instruction=(
        "You are the Graduate Scholarship Discovery Specialist.\n"
        "1. Always inspect the student's profile (`get_student_profile`) first so your searches "
        "reflect their `geographies` (state/region, study destination countries) and `academics`.\n"
        "2. Use `search_curated_fellowships` for verified national, regional, and international fellowships.\n"
        "3. Use `search_scholarships_web` and `scrape_scholarship_page` to find live awards and extract "
        "deadlines, dollar amounts, and eligibility criteria.\n"
        "4. Never fabricate URLs or deadlines. Report verification status clearly."
    ),
    tools=[
        get_student_profile,
        search_curated_fellowships,
        search_scholarships_web,
        scrape_scholarship_page,
    ],
)

# -----------------------------------------------------------------------------
# 2. Eligibility, Geography & Filter Matching Subagent
# -----------------------------------------------------------------------------
eligibility_matcher_agent = LlmAgent(
    name="eligibility_matcher_agent",
    model=DEFAULT_MODEL,
    description=(
        "Evaluates scholarships against profile.yaml geographies, hard filters, GPA, "
        "citizenship, and research keywords to compute a 0-100 Fit Score."
    ),
    instruction=(
        "You are the Eligibility & Fit Scoring Analyst.\n"
        "1. Load or update `profile.yaml` via `get_student_profile` and `update_profile_setting`.\n"
        "2. Use `batch_score_scholarships` or `evaluate_scholarship_fit` to run the deterministic "
        "0-100 scoring engine across geographies (state/region residency, study destination countries) "
        "and hard filters (min award amount, institution locks, degree level, excluded keywords).\n"
        "3. Explain clearly why each scholarship passed or failed filters and highlight its score breakdown."
    ),
    tools=[
        get_student_profile,
        update_profile_setting,
        evaluate_scholarship_fit,
        batch_score_scholarships,
    ],
)

# -----------------------------------------------------------------------------
# 3. Tracker & Dashboard Exporter Subagent
# -----------------------------------------------------------------------------
tracker_agent = LlmAgent(
    name="tracker_agent",
    model=DEFAULT_MODEL,
    description=(
        "Manages the SQLite scholarship database (data/scholarships.db), exports CSV files, "
        "and generates the prioritized Markdown dashboard (data/SCHOLARSHIP_DASHBOARD.md)."
    ),
    instruction=(
        "You are the Scholarship Portfolio & Deadline Tracker.\n"
        "1. Call `sync_and_export_tracker` to score all scholarships against `profile.yaml`, save them "
        "to SQLite (`data/scholarships.db`), and export `data/scholarships.csv` and `data/SCHOLARSHIP_DASHBOARD.md`.\n"
        "2. Use `list_tracked_scholarships` to inspect current tracked items and `update_scholarship_status` "
        "to update workflow status ('discovered', 'researching', 'drafting_essay', 'submitted', 'won')."
    ),
    tools=[
        sync_and_export_tracker,
        list_tracked_scholarships,
        update_scholarship_status,
    ],
)

# -----------------------------------------------------------------------------
# 4. Essay & Personal Statement Assistant Subagent
# -----------------------------------------------------------------------------
essay_assistant_agent = LlmAgent(
    name="essay_assistant_agent",
    model=DEFAULT_MODEL,
    description=(
        "Drafts tailored graduate fellowship personal statements, research proposals, "
        "and essay outlines aligned with the student's profile.yaml and saves them to data/essays/."
    ),
    instruction=(
        "You are the Graduate Fellowship Essay Coach.\n"
        "1. Call `get_essay_prompt_context(scholarship_id)` to retrieve the target scholarship's "
        "prompts and the student's projects, leadership, and career goals from `profile.yaml`.\n"
        "2. Draft a compelling, specific outline and full personal statement that weaves together "
        "their technical projects, leadership, and regional/broader impacts.\n"
        "3. Save the draft to `data/essays/` using `save_essay_draft`."
    ),
    tools=[
        get_essay_prompt_context,
        save_essay_draft,
        list_essay_drafts,
    ],
)

# -----------------------------------------------------------------------------
# Root Coordinator Agent (`root_agent` required by ADK CLI / Web)
# -----------------------------------------------------------------------------
root_agent = LlmAgent(
    name="scholarship_coordinator",
    model=DEFAULT_MODEL,
    description=(
        "Root coordinator agent for discovering, filtering by geography/criteria, scoring, "
        "tracking, and drafting essays for graduate school scholarships."
    ),
    instruction=(
        "You are the Graduate School Scholarship Finder Coordinator built with Google ADK.\n"
        "You help the user discover graduate fellowships, filter them using `profile.yaml` "
        "(including `geographies` and `filters`), maintain a prioritized tracker in `data/`, "
        "and draft tailored personal statements.\n\n"
        "You have direct access to fast tools as well as four specialist subagents:\n"
        "- `discovery_agent`: Web search, curated catalog lookup, and safe HTML scraping.\n"
        "- `eligibility_matcher_agent`: Geography + filter enforcement and 0-100 Fit Scoring.\n"
        "- `tracker_agent`: SQLite persistence, CSV export, and Markdown dashboard generation.\n"
        "- `essay_assistant_agent`: Fellowship personal statement outlining and drafting.\n\n"
        "Always ground your answers in the student's `profile.yaml` settings and never invent URLs."
    ),
    tools=[
        get_student_profile,
        update_profile_setting,
        search_curated_fellowships,
        search_scholarships_web,
        scrape_scholarship_page,
        evaluate_scholarship_fit,
        batch_score_scholarships,
        sync_and_export_tracker,
        list_tracked_scholarships,
        update_scholarship_status,
        get_essay_prompt_context,
        save_essay_draft,
        list_essay_drafts,
    ],
    sub_agents=[
        discovery_agent,
        eligibility_matcher_agent,
        tracker_agent,
        essay_assistant_agent,
    ],
)
