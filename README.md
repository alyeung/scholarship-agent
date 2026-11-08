# Graduate School Scholarship Finder

An autonomous multi-agent system that finds, filters, scores, and tracks graduate school scholarships. Built with the Google Agent Development Kit (`google-adk`) and Antigravity Harness Engineering.

## Executive Summary

Graduate students leave millions of dollars in fellowship funding unclaimed each year. Searching fragmented university pages, verifying eligibility rules, and tracking deadlines takes dozens of hours.

This product automates the entire scholarship funnel:

- **Targeted Discovery**: Searches curated national, regional, and international fellowships alongside live web results.
- **Precision Filtering**: Applies strict geography, degree, GPA, and award-size filters from a local configuration file.
- **Deterministic Fit Scoring**: Ranks every scholarship on a `0-100` scale with clear pass or fail reasons.
- **Application Readiness**: Exports a prioritized dashboard and generates tailored essay outlines for top matches.

---

## Product Architecture

The system combines an application harness (`google-adk`) with a repository safety harness (`.agents/`).

| Component | Role | Output |
| :--- | :--- | :--- |
| **Coordinator Agent** | Routes user goals across four specialist subagents | Unified workflow execution |
| **Discovery Agent** | Searches fellowship catalogs and scrapes official web pages | Verified deadlines, award amounts, and links |
| **Eligibility Matcher** | Evaluates geography, citizenship, GPA, and keyword filters | `0-100` Fit Score and rejection audit log |
| **Tracker Agent** | Saves results and exports portfolio views | SQLite DB, CSV, and Markdown dashboard |
| **Essay Assistant** | Aligns student project history with fellowship prompts | Structured outlines and first drafts |

---

## Governance, Security, and Privacy

This repository is engineered for safe, unattended execution. Personal data never leaves the local machine.

- **Zero Personal Data in Git**: Personal profiles (`profile.yaml`), generated dashboards (`data/`), and essay drafts are strictly git-ignored. Only anonymized templates (`profile.example.yaml`) are committed.
- **Prompt Injection Defense**: External web pages pass through a sanitizer before reaching the model. Malicious instructions and scripts are stripped automatically.
- **Pre-Execution Safety Gate**: A deterministic hook (`.agents/scripts/pre_tool_guard.py`) blocks destructive shell commands and prevents network exfiltration of local files.
- **Automated Security Tests**: The test suite scans tracked files on every run to ensure zero leaked credentials, tokens, or local file paths.

---

## Personalization and Filtering

Any applicant can customize the agent via `profile.yaml` or CLI flags.

1. **Geographies**: Current state, metro area, regional residency, and target study countries (such as the United States, United Kingdom, or Canada).
2. **Hard Filters**: Minimum award amount, degree level, maximum recommendation letters, institution locks, and service-bond exclusions.
3. **Priority Keywords**: Research areas and domain keywords that boost relevant fellowships to the top of the rankings.

---

## Quick Start

### 1. Initialize and Customize Your Profile

```bash
.venv/bin/python cli.py init \
  --name "Your Name" \
  --degree "Master's" \
  --field "Computer Science" \
  --state "California" \
  --gpa 3.85 \
  --min-award 5000
```

You can also edit `profile.yaml` directly to customize target universities, research interests, and filter rules.

### 2. Run the Matching Engine

```bash
.venv/bin/python cli.py match
```

This command scores all fellowships and generates three local files:
- `data/SCHOLARSHIP_DASHBOARD.md`
- `data/scholarships.csv`
- `data/scholarships.db`

### 3. Draft an Application Essay

```bash
.venv/bin/python cli.py essay nsf-grfp-2027
```

### 4. Launch the Interactive Web UI

```bash
cp .env.example .env
.venv/bin/adk web
```

### 5. Run Verification Tests

```bash
.venv/bin/pytest -v
```
