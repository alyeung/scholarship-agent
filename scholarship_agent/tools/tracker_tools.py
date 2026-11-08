"""SQLite, CSV, and Markdown Dashboard Tracker tools for managing graduate scholarships."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from .eligibility_tools import batch_score_scholarships
from .profile_tools import _load_profile_dict

_DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _get_data_dir() -> Path:
    env_dir = os.environ.get("SCHOLARSHIP_DATA_DIR", "").strip()
    path = Path(env_dir).expanduser().resolve() if env_dir else _DEFAULT_DATA_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def _connect_db() -> sqlite3.Connection:
    db_path = _get_data_dir() / "scholarships.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scholarships (
            scholarship_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            provider TEXT,
            award_amount_usd INTEGER DEFAULT 0,
            award_display TEXT,
            award_type TEXT,
            deadline TEXT,
            geography_scope TEXT,
            study_countries TEXT,
            eligible_states_or_regions TEXT,
            fit_score INTEGER DEFAULT 0,
            eligibility_status TEXT,
            filter_passed INTEGER DEFAULT 1,
            filter_rejection_reasons TEXT,
            match_reasons TEXT,
            application_status TEXT DEFAULT 'discovered',
            source_url TEXT,
            raw_json TEXT
        )
        """
    )
    conn.commit()
    return conn


def sync_and_export_tracker(profile_path: str = "") -> dict[str, Any]:
    """Run batch eligibility scoring using profile.yaml, persist to SQLite, and export CSV & Markdown Dashboard.

    Args:
        profile_path: Optional override path to profile.yaml.

    Returns:
        Dictionary with paths to scholarships.db, scholarships.csv, SCHOLARSHIP_DASHBOARD.md, and summary metrics.
    """
    scored = batch_score_scholarships(include_filtered_out=True, profile_path=profile_path)
    profile = _load_profile_dict(profile_path)
    data_dir = _get_data_dir()

    conn = _connect_db()
    try:
        for rec in scored["scholarships"]:
            existing = conn.execute(
                "SELECT application_status FROM scholarships WHERE scholarship_id = ?",
                (rec["scholarship_id"],),
            ).fetchone()
            app_status = existing["application_status"] if existing else rec.get("application_status", "discovered")
            rec["application_status"] = app_status

            conn.execute(
                """
                INSERT OR REPLACE INTO scholarships (
                    scholarship_id, name, provider, award_amount_usd, award_display,
                    award_type, deadline, geography_scope, study_countries,
                    eligible_states_or_regions, fit_score, eligibility_status,
                    filter_passed, filter_rejection_reasons, match_reasons,
                    application_status, source_url, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rec["scholarship_id"],
                    rec["name"],
                    rec.get("provider", ""),
                    int(rec.get("award_amount_usd", 0)),
                    rec.get("award_display", ""),
                    rec.get("award_type", "Fellowship"),
                    rec.get("deadline", "Rolling"),
                    rec.get("geography_scope", "National"),
                    ", ".join(rec.get("study_countries", [])),
                    ", ".join(rec.get("eligible_states_or_regions", [])),
                    int(rec.get("fit_score", 0)),
                    rec.get("eligibility_status", "Unscored"),
                    1 if rec.get("filter_passed", True) else 0,
                    "; ".join(rec.get("filter_rejection_reasons", [])),
                    "; ".join(rec.get("match_reasons", [])),
                    app_status,
                    rec.get("source_url", ""),
                    json.dumps(rec),
                ),
            )
        conn.commit()
    finally:
        conn.close()

    csv_path = data_dir / "scholarships.csv"
    md_path = data_dir / "SCHOLARSHIP_DASHBOARD.md"
    db_path = data_dir / "scholarships.db"

    _write_csv_export(csv_path, scored["scholarships"])
    _write_markdown_dashboard(md_path, scored, profile)

    matched_list = [r for r in scored["scholarships"] if r.get("filter_passed")]
    total_potential_usd = sum(int(r.get("award_amount_usd", 0)) for r in matched_list)

    return {
        "status": "success",
        "matched_count": scored["matched_count"],
        "filtered_out_count": scored["filtered_out_count"],
        "total_potential_award_usd": total_potential_usd,
        "sqlite_db_path": str(db_path),
        "csv_path": str(csv_path),
        "dashboard_markdown_path": str(md_path),
        "top_matches": [
            {
                "scholarship_id": r["scholarship_id"],
                "name": r["name"],
                "fit_score": r["fit_score"],
                "eligibility_status": r["eligibility_status"],
                "award_display": r["award_display"],
                "deadline": r["deadline"],
                "geography_scope": r["geography_scope"],
            }
            for r in matched_list[:5]
        ],
    }


def _write_csv_export(csv_path: Path, records: list[dict[str, Any]]) -> None:
    fieldnames = [
        "fit_score",
        "eligibility_status",
        "filter_passed",
        "scholarship_id",
        "name",
        "provider",
        "award_amount_usd",
        "award_display",
        "deadline",
        "geography_scope",
        "study_countries",
        "eligible_states_or_regions",
        "application_status",
        "match_reasons",
        "filter_rejection_reasons",
        "source_url",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow(
                {
                    "fit_score": r.get("fit_score", 0),
                    "eligibility_status": r.get("eligibility_status", ""),
                    "filter_passed": r.get("filter_passed", True),
                    "scholarship_id": r.get("scholarship_id", ""),
                    "name": r.get("name", ""),
                    "provider": r.get("provider", ""),
                    "award_amount_usd": r.get("award_amount_usd", 0),
                    "award_display": r.get("award_display", ""),
                    "deadline": r.get("deadline", ""),
                    "geography_scope": r.get("geography_scope", ""),
                    "study_countries": ", ".join(r.get("study_countries", [])),
                    "eligible_states_or_regions": ", ".join(r.get("eligible_states_or_regions", [])),
                    "application_status": r.get("application_status", "discovered"),
                    "match_reasons": " | ".join(r.get("match_reasons", [])),
                    "filter_rejection_reasons": " | ".join(r.get("filter_rejection_reasons", [])),
                    "source_url": r.get("source_url", ""),
                }
            )


def _write_markdown_dashboard(
    md_path: Path,
    scored: dict[str, Any],
    profile: dict[str, Any],
) -> None:
    student = profile.get("student", {})
    geo = profile.get("geographies", {})
    acad = profile.get("academics", {})
    flt = profile.get("filters", {})

    matched = [r for r in scored["scholarships"] if r.get("filter_passed")]
    rejected = [r for r in scored["scholarships"] if not r.get("filter_passed")]
    total_usd = sum(int(r.get("award_amount_usd", 0)) for r in matched)

    lines: list[str] = [
        "# Graduate School Scholarship Finder — Personalized Dashboard",
        "",
        f"- **Student**: {student.get('name', 'Grad Applicant')} ({student.get('citizenship_status', 'US Citizen')})",
        f"- **Target Program**: {acad.get('target_degree', 'Graduate')} in {acad.get('field_of_study', 'STEM')} (GPA: {acad.get('gpa', 'N/A')})",
        f"- **Current Location**: {geo.get('current_city_or_metro', '')}, {geo.get('current_state_or_province', '')} ({geo.get('current_region', '')})",
        f"- **Study Destinations**: {', '.join(geo.get('study_destination_countries', []))} | States: {', '.join(geo.get('study_destination_states_or_regions', []))}",
        f"- **Active Filters**: Min Award `${flt.get('min_award_amount_usd', 0):,}` | Min Fit Score `{flt.get('min_fit_score_threshold', 0)}` | Deadlines `{flt.get('deadline_after', '')}` to `{flt.get('deadline_before', '')}`",
        f"- **Matched Opportunities**: **{len(matched)}** scholarships (`${total_usd:,}` cumulative value) | **{len(rejected)}** filtered out",
        "",
        "## Recommended Scholarships (Passed Geography & Profile Filters)",
        "",
        "| Fit Score | Status | Scholarship | Award | Deadline | Geography / Scope | App Status | Official Link |",
        "| :---: | :--- | :--- | :--- | :---: | :--- | :---: | :--- |",
    ]

    for r in matched:
        scope_str = f"{r.get('geography_scope')} ({', '.join(r.get('eligible_states_or_regions', [])[:2])})"
        lines.append(
            f"| **{r['fit_score']}/100** | {r['eligibility_status']} | **{r['name']}** (`{r['scholarship_id']}`) | {r['award_display']} | `{r['deadline']}` | {scope_str} | `{r.get('application_status', 'discovered')}` | [Link]({r['source_url']}) |"
        )

    lines.extend(["", "## Detailed Fit Breakdown", ""])
    for r in matched:
        lines.append(f"### {r['name']} — Fit Score: {r['fit_score']}/100 ({r['eligibility_status']})")
        lines.append(f"- **Provider**: {r['provider']} | **Award**: {r['award_display']} | **Deadline**: `{r['deadline']}`")
        lines.append(f"- **Why It Matches Your Profile & Geography**: {'; '.join(r.get('match_reasons', []))}")
        if r.get("warnings"):
            lines.append(f"- **Notes / Check Requirements**: {'; '.join(r['warnings'])}")
        if r.get("essay_prompts"):
            lines.append(f"- **Key Essay Prompt**: *{r['essay_prompts'][0]}*")
        lines.append("")

    if rejected:
        lines.extend(
            [
                "## Filtered-Out Scholarships (Blocked by Geography or Filter Rules)",
                "",
                "| Scholarship | Geography | Rejection Reason(s) |",
                "| :--- | :--- | :--- |",
            ]
        )
        for r in rejected:
            lines.append(
                f"| {r['name']} (`{r['scholarship_id']}`) | {', '.join(r.get('eligible_states_or_regions', []))} | {'; '.join(r.get('filter_rejection_reasons', []))} |"
            )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def list_tracked_scholarships(only_passed_filters: bool = True) -> dict[str, Any]:
    """Query the local SQLite database for tracked scholarships ordered by fit score.

    Args:
        only_passed_filters: If True, only return scholarships that passed geography and profile filters.

    Returns:
        Dictionary containing status, count, and tracked scholarship rows.
    """
    conn = _connect_db()
    try:
        query = "SELECT * FROM scholarships"
        if only_passed_filters:
            query += " WHERE filter_passed = 1"
        query += " ORDER BY fit_score DESC, award_amount_usd DESC"
        rows = [dict(row) for row in conn.execute(query).fetchall()]
        for row in rows:
            row.pop("raw_json", None)
        return {
            "status": "success",
            "count": len(rows),
            "scholarships": rows,
        }
    finally:
        conn.close()


def update_scholarship_status(
    scholarship_id: str,
    application_status: str,
) -> dict[str, Any]:
    """Update the application workflow status for a scholarship in SQLite.

    Args:
        scholarship_id: Unique ID of the scholarship (e.g. 'nsf-grfp-2027').
        application_status: New status ('discovered', 'researching', 'drafting_essay', 'submitted', 'won', 'archived').

    Returns:
        Confirmation dictionary.
    """
    conn = _connect_db()
    try:
        cur = conn.execute(
            "UPDATE scholarships SET application_status = ? WHERE scholarship_id = ?",
            (application_status, scholarship_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            return {
                "status": "error",
                "error": f"Scholarship '{scholarship_id}' not found in SQLite tracker. Run sync_and_export_tracker first.",
            }
        return {
            "status": "success",
            "scholarship_id": scholarship_id,
            "application_status": application_status,
        }
    finally:
        conn.close()
