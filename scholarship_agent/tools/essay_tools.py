"""Tools for assembling graduate scholarship essay contexts and saving tailored personal statements."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from .profile_tools import _load_profile_dict
from .search_tools import _CURATED_GRAD_FELLOWSHIPS
from .tracker_tools import _get_data_dir


def _get_essays_dir() -> Path:
    essays_dir = _get_data_dir() / "essays"
    essays_dir.mkdir(parents=True, exist_ok=True)
    return essays_dir


def get_essay_prompt_context(
    scholarship_id: str,
    profile_path: str = "",
) -> dict[str, Any]:
    """Gather the scholarship's essay prompts, mission criteria, and matching student profile stories.

    Args:
        scholarship_id: Unique ID of the target scholarship (e.g. 'nsf-grfp-2027', 'knight-hennessy-2027').
        profile_path: Optional override path to profile.yaml.

    Returns:
        Dictionary containing the scholarship prompts, student research/projects, leadership stories,
        and a tailored outline structure.
    """
    profile = _load_profile_dict(profile_path)
    scholarship = next(
        (s for s in _CURATED_GRAD_FELLOWSHIPS if s["scholarship_id"] == scholarship_id),
        None,
    )
    if not scholarship:
        return {
            "status": "error",
            "error": f"Scholarship '{scholarship_id}' not found.",
        }

    student = profile.get("student", {})
    academics = profile.get("academics", {})
    geographies = profile.get("geographies", {})
    research = profile.get("research_and_career", {})

    outline = [
        f"1. Opening Hook: Connect {student.get('name', 'the applicant')}'s work in {academics.get('field_of_study', 'graduate research')} to the mission of {scholarship['name']}.",
        f"2. Intellectual Merit & Technical Track Record: Highlight projects ({', '.join(p.get('title', '') for p in research.get('publications_or_projects', []))}) and preparation for {academics.get('target_degree', 'graduate study')}.",
        f"3. Research Vision & Graduate Program Fit: Detail proposed work in {', '.join(research.get('research_interests', [])[:3])} at target institutions ({', '.join(academics.get('target_universities', [])[:3])}).",
        f"4. Broader Impacts, Leadership & Regional Connection: Tie in leadership roles ({', '.join(l.get('role', '') for l in research.get('leadership_and_service', []))}) and impact in {geographies.get('current_state_or_province', '')} / {geographies.get('current_region', '')}.",
    ]

    return {
        "status": "success",
        "scholarship_id": scholarship_id,
        "scholarship_name": scholarship["name"],
        "provider": scholarship["provider"],
        "essay_prompts": scholarship.get("essay_prompts", []),
        "student_summary": {
            "name": student.get("name"),
            "target_degree": academics.get("target_degree"),
            "field_of_study": academics.get("field_of_study"),
            "target_universities": academics.get("target_universities"),
            "geography": geographies,
            "research_interests": research.get("research_interests"),
            "career_goals": research.get("career_goals"),
            "projects": research.get("publications_or_projects"),
            "leadership": research.get("leadership_and_service"),
        },
        "recommended_outline": outline,
    }


def save_essay_draft(
    scholarship_id: str,
    essay_title: str,
    draft_markdown: str,
) -> dict[str, Any]:
    """Save a tailored scholarship essay outline or full personal statement draft to data/essays/.

    Args:
        scholarship_id: Unique ID of the scholarship (e.g. 'nsf-grfp-2027').
        essay_title: Title of the essay or prompt.
        draft_markdown: Full Markdown content of the essay outline and draft.

    Returns:
        Dictionary with status and saved file path.
    """
    safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", scholarship_id).strip("-").lower() or "essay"
    file_path = _get_essays_dir() / f"{safe_id}.md"
    content = f"# {essay_title}\n\n**Scholarship ID**: `{scholarship_id}`\n\n{draft_markdown.strip()}\n"
    file_path.write_text(content, encoding="utf-8")
    return {
        "status": "success",
        "scholarship_id": scholarship_id,
        "essay_title": essay_title,
        "file_path": str(file_path),
    }


def list_essay_drafts() -> dict[str, Any]:
    """List all saved scholarship essay drafts in data/essays/.

    Returns:
        Dictionary containing status, count, and list of saved essay files.
    """
    essays_dir = _get_essays_dir()
    files = sorted(essays_dir.glob("*.md"))
    return {
        "status": "success",
        "count": len(files),
        "drafts": [
            {
                "filename": f.name,
                "path": str(f),
                "size_bytes": f.stat().st_size,
            }
            for f in files
        ],
    }
