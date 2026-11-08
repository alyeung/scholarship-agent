---
name: scholarship-discovery
description: >-
  Use this skill when searching for graduate school scholarships, scraping
  external fellowship web pages, filtering by geography and student criteria,
  or updating the scholarship database and dashboard.
---

# Graduate Scholarship Discovery & Verification Skill

Follow this runbook when discovering, scraping, filtering, and scoring graduate scholarships.

## Steps

1. **Load Student Profile, Geographies & Filters First**:
   - Always call `get_student_profile()` (or inspect `profile.yaml`) before running searches so queries and filters match the student's `geographies` (current state/country, study destination countries/states) and `filters` (minimum award, degree level, excluded keywords, institution locks).
2. **Run Multi-Source Discovery**:
   - Query the curated graduate fellowship catalog via `search_curated_fellowships()` first for high-signal national, regional, and international fellowships.
   - Supplement with live web search via `search_scholarships_web(query)` targeting:
     - National STEM / discipline fellowships
     - Regional/state fellowships matching `geographies.current_state_or_province` and `geographies.current_region`
     - Target university fellowships matching `academics.target_universities`
3. **Scrape & Sanitize Official Pages**:
   - Use `scrape_scholarship_page(url)` to extract deadlines, award amounts, and eligibility requirements.
   - All scraped text is automatically sanitized against prompt injection before returning.
4. **Apply Deterministic Geography & Filter Evaluation**:
   - Run `evaluate_scholarship_fit()` or `batch_score_scholarships()` to compute the `0-100` Fit Score and check hard filters (`filters.exclude_keywords`, `filters.min_award_amount_usd`, `geographies.study_destination_countries`, etc.).
5. **Persist & Export Dashboard**:
   - Save results with `save_scholarship()` and call `export_tracker_artifacts()` to regenerate `data/scholarships.csv` and `data/SCHOLARSHIP_DASHBOARD.md`.
