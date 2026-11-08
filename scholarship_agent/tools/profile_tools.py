"""Tools for loading, inspecting, and updating the student profile and filter configuration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PROFILE_PATH = _REPO_ROOT / "profile.yaml"
_EXAMPLE_PROFILE_PATH = _REPO_ROOT / "profile.example.yaml"


def _resolve_profile_path(custom_path: str = "") -> Path:
    if custom_path and custom_path.strip():
        return Path(custom_path).expanduser().resolve()
    env_path = os.environ.get("SCHOLARSHIP_PROFILE_PATH", "").strip()
    if env_path:
        return Path(env_path).expanduser().resolve()
    if _DEFAULT_PROFILE_PATH.exists():
        return _DEFAULT_PROFILE_PATH
    if _EXAMPLE_PROFILE_PATH.exists():
        return _EXAMPLE_PROFILE_PATH
    return _DEFAULT_PROFILE_PATH


def _load_profile_dict(custom_path: str = "") -> dict[str, Any]:
    path = _resolve_profile_path(custom_path)
    if not path.exists():
        raise FileNotFoundError(f"Profile configuration file not found at {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def get_student_profile(profile_path: str = "") -> dict[str, Any]:
    """Load the student's graduate school profile, geographies, and filter settings from profile.yaml.

    Args:
        profile_path: Optional override path to a custom profile.yaml file. Leave empty for default.

    Returns:
        Dictionary containing status, profile_path, and the parsed student, geographies,
        academics, filters, research_and_career, and financial_and_preferences sections.
    """
    try:
        resolved = _resolve_profile_path(profile_path)
        data = _load_profile_dict(profile_path)
        return {
            "status": "success",
            "profile_path": str(resolved),
            "profile": data,
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
        }


def update_profile_setting(
    section: str,
    key: str,
    value_yaml: str,
    profile_path: str = "",
) -> dict[str, Any]:
    """Update a specific field inside profile.yaml (e.g. geographies, filters, academics, student).

    Args:
        section: Top-level section in profile.yaml ('student', 'geographies', 'academics', 'filters', 'research_and_career', 'financial_and_preferences').
        key: Field name within that section (e.g. 'min_award_amount_usd', 'current_state_or_province', 'boost_keywords').
        value_yaml: YAML-formatted value string (e.g. '5000', 'true', '["United States", "Canada"]').
        profile_path: Optional override path to a custom profile.yaml file.

    Returns:
        Dictionary confirming the updated setting.
    """
    try:
        resolved = _resolve_profile_path(profile_path)
        data = _load_profile_dict(profile_path)
        if section not in data or not isinstance(data.get(section), dict):
            data[section] = {}
        parsed_value = yaml.safe_load(value_yaml)
        data[section][key] = parsed_value
        with resolved.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
        return {
            "status": "success",
            "section": section,
            "key": key,
            "new_value": parsed_value,
            "profile_path": str(resolved),
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
        }
