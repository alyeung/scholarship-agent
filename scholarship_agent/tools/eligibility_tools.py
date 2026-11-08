"""Deterministic Geography, Filter & Eligibility Fit Scoring Engine for Graduate Scholarships."""

from __future__ import annotations

from typing import Any

from .profile_tools import _load_profile_dict
from .search_tools import _CURATED_GRAD_FELLOWSHIPS


def _normalize_list(items: Any) -> list[str]:
    if not items:
        return []
    if isinstance(items, str):
        return [items.strip()]
    return [str(x).strip() for x in items if str(x).strip()]


def _evaluate_single_scholarship(
    scholarship: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate a single scholarship record against student profile, geographies, and filters."""
    student = profile.get("student", {}) or {}
    geographies = profile.get("geographies", {}) or {}
    academics = profile.get("academics", {}) or {}
    filters = profile.get("filters", {}) or {}
    research = profile.get("research_and_career", {}) or {}
    financial = profile.get("financial_and_preferences", {}) or {}

    rejection_reasons: list[str] = []
    match_reasons: list[str] = []
    warnings: list[str] = []

    # -------------------------------------------------------------------------
    # 1. Geography & Citizenship Rules
    # -------------------------------------------------------------------------
    citizenship_status = str(student.get("citizenship_status") or student.get("citizenship") or "US Citizen")
    citizenship_countries = _normalize_list(student.get("citizenship_countries"))
    allowed_citizenships = _normalize_list(scholarship.get("allowed_citizenships"))

    citizenship_ok = True
    if allowed_citizenships and "Any" not in allowed_citizenships:
        lower_allowed = [c.lower() for c in allowed_citizenships]
        user_tokens = [citizenship_status.lower()] + [c.lower() for c in citizenship_countries]
        if not any(tok in lower_allowed for tok in user_tokens):
            citizenship_ok = False
            rejection_reasons.append(
                f"Citizenship mismatch: requires {allowed_citizenships}, profile has '{citizenship_status}'"
            )
        else:
            match_reasons.append(f"Citizenship eligible ({citizenship_status})")

    scope = str(scholarship.get("geography_scope", "National"))
    if scope == "National" and not geographies.get("include_national_scholarships", True):
        rejection_reasons.append("Excluded by geographies.include_national_scholarships=false")
    elif scope == "State/Regional" and not geographies.get("include_state_and_regional_scholarships", True):
        rejection_reasons.append("Excluded by geographies.include_state_and_regional_scholarships=false")
    elif scope == "International" and not geographies.get("include_international_fellowships", True):
        rejection_reasons.append("Excluded by geographies.include_international_fellowships=false")

    # Study destination country check
    study_dest_countries = [c.lower() for c in _normalize_list(geographies.get("study_destination_countries"))]
    excluded_countries = [c.lower() for c in _normalize_list(geographies.get("excluded_countries"))]
    sch_countries = _normalize_list(scholarship.get("study_countries"))
    sch_countries_lower = [c.lower() for c in sch_countries]

    if excluded_countries and any(c in excluded_countries for c in sch_countries_lower):
        rejection_reasons.append(f"Study country in excluded_countries: {sch_countries}")

    country_matched = True
    if study_dest_countries and sch_countries_lower and "any" not in sch_countries_lower:
        if not any(c in study_dest_countries for c in sch_countries_lower):
            country_matched = False
            rejection_reasons.append(
                f"Study destination country mismatch: award is for {sch_countries}, profile targets {geographies.get('study_destination_countries')}"
            )
        else:
            matched_c = [c for c in sch_countries if c.lower() in study_dest_countries]
            match_reasons.append(f"Study destination country match: {', '.join(matched_c)}")

    # State / regional eligibility check
    eligible_regions = _normalize_list(scholarship.get("eligible_states_or_regions"))
    eligible_regions_lower = [r.lower() for r in eligible_regions]
    user_geo_tokens = [
        str(geographies.get("current_state_or_province", "")).lower(),
        str(geographies.get("current_city_or_metro", "")).lower(),
        str(geographies.get("current_region", "")).lower(),
    ] + [s.lower() for s in _normalize_list(geographies.get("study_destination_states_or_regions"))]
    user_geo_tokens = [t for t in user_geo_tokens if t]

    regional_bonus = 0
    if eligible_regions_lower and "any" not in eligible_regions_lower and "international" not in eligible_regions_lower:
        if any(r in user_geo_tokens for r in eligible_regions_lower):
            regional_bonus = 12
            match_reasons.append(f"Regional/State geography match ({', '.join(eligible_regions)})")
        else:
            rejection_reasons.append(
                f"State/Regional restriction mismatch: requires {eligible_regions}, profile has {geographies.get('current_state_or_province')} / {geographies.get('study_destination_states_or_regions')}"
            )

    # -------------------------------------------------------------------------
    # 2. Hard Filter Rules from `filters` section in profile.yaml
    # -------------------------------------------------------------------------
    award_usd = int(scholarship.get("award_amount_usd", 0) or 0)
    min_award = int(filters.get("min_award_amount_usd", 0) or 0)
    if award_usd > 0 and award_usd < min_award:
        rejection_reasons.append(f"Award amount (${award_usd:,}) below min_award_amount_usd (${min_award:,})")

    if filters.get("exclude_repayable_loans", True) and scholarship.get("is_repayable_loan", False):
        rejection_reasons.append("Excluded: repayable loan program")

    if filters.get("exclude_service_or_employment_bonds", False) and scholarship.get("requires_service_bond", False):
        rejection_reasons.append("Excluded by filters.exclude_service_or_employment_bonds=true")
    elif scholarship.get("requires_service_bond", False):
        warnings.append("Requires post-graduation service/employment commitment")

    if filters.get("require_no_application_fee", True) and scholarship.get("has_application_fee", False):
        rejection_reasons.append("Excluded: scholarship charges an application fee")

    max_rec_letters = int(filters.get("max_recommendation_letters", 10) or 10)
    rec_letters = int(scholarship.get("recommendation_letters_required", 0) or 0)
    if rec_letters > max_rec_letters:
        rejection_reasons.append(
            f"Requires {rec_letters} recommendation letters (max allowed: {max_rec_letters})"
        )

    # Institution lock check
    locked_insts = _normalize_list(scholarship.get("locked_institutions"))
    target_unis = _normalize_list(academics.get("target_universities"))
    target_unis_lower = [u.lower() for u in target_unis]
    institution_bonus = 0
    if locked_insts:
        matched_unis = [u for u in locked_insts if u.lower() in target_unis_lower]
        if matched_unis:
            institution_bonus = 10
            match_reasons.append(f"Target university fellowship match: {', '.join(matched_unis)}")
        elif filters.get("exclude_institution_locked_unless_target", True):
            rejection_reasons.append(
                f"Locked to non-target institution(s): {locked_insts}"
            )

    # Deadline window check
    deadline = str(scholarship.get("deadline", "Rolling"))
    deadline_after = str(filters.get("deadline_after", "")).strip()
    deadline_before = str(filters.get("deadline_before", "")).strip()
    if deadline and deadline != "Rolling" and len(deadline) == 10:
        if deadline_after and deadline < deadline_after:
            rejection_reasons.append(f"Deadline ({deadline}) is earlier than deadline_after ({deadline_after})")
        if deadline_before and deadline > deadline_before:
            rejection_reasons.append(f"Deadline ({deadline}) is later than deadline_before ({deadline_before})")

    # Degree level check
    target_degree = str(academics.get("target_degree", "Master's"))
    allowed_degrees = _normalize_list(filters.get("allowed_degree_levels")) or [target_degree]
    sch_degrees = _normalize_list(scholarship.get("degree_levels"))
    sch_degrees_lower = [d.lower() for d in sch_degrees]
    degree_matched = any(d.lower() in sch_degrees_lower for d in allowed_degrees) or "any" in sch_degrees_lower
    if not degree_matched:
        rejection_reasons.append(
            f"Degree level mismatch: award supports {sch_degrees}, profile targets {allowed_degrees}"
        )
    elif target_degree.lower() in sch_degrees_lower:
        match_reasons.append(f"Supports target degree ({target_degree})")

    # GPA check
    student_gpa = float(academics.get("gpa", 0.0) or 0.0)
    min_gpa = float(scholarship.get("min_gpa", 0.0) or 0.0)
    if min_gpa > 0 and student_gpa > 0 and student_gpa < min_gpa:
        rejection_reasons.append(f"GPA ({student_gpa}) is below minimum required GPA ({min_gpa})")

    # Keyword filters
    full_text = " ".join(
        [
            str(scholarship.get("name", "")),
            str(scholarship.get("provider", "")),
            str(scholarship.get("description", "")),
            " ".join(_normalize_list(scholarship.get("fields_of_study"))),
            " ".join(_normalize_list(scholarship.get("eligible_states_or_regions"))),
        ]
    ).lower()

    exclude_keywords = _normalize_list(filters.get("exclude_keywords"))
    for bad_kw in exclude_keywords:
        if bad_kw.lower() in full_text:
            rejection_reasons.append(f"Matched excluded keyword: '{bad_kw}'")

    must_keywords = _normalize_list(filters.get("must_match_any_keywords"))
    if must_keywords:
        if not any(kw.lower() in full_text for kw in must_keywords):
            rejection_reasons.append(f"Did not match any required keyword in {must_keywords}")

    # -------------------------------------------------------------------------
    # 3. Compute 0-100 Weighted Fit Score
    # -------------------------------------------------------------------------
    # A. Academic & Degree Fit (0-25)
    academic_score = 0
    if target_degree.lower() in sch_degrees_lower:
        academic_score += 18
    elif degree_matched:
        academic_score += 12

    discipline = str(academics.get("discipline_category", "STEM")).lower()
    field = str(academics.get("field_of_study", "")).lower()
    sch_fields_lower = [f.lower() for f in _normalize_list(scholarship.get("fields_of_study"))]
    if any(tok in " ".join(sch_fields_lower) for tok in [discipline] + field.split()):
        academic_score += 7
        match_reasons.append(f"Field of study aligns with {scholarship.get('fields_of_study')}")
    elif "any" in sch_fields_lower:
        academic_score += 4
    academic_score = min(25, academic_score)

    # B. Research Interests & Boost Keywords (0-25)
    boost_keywords = _normalize_list(filters.get("boost_keywords"))
    research_interests = _normalize_list(research.get("research_interests"))
    matched_boosts: list[str] = []
    for kw in boost_keywords + research_interests:
        if kw.lower() in full_text and kw not in matched_boosts:
            matched_boosts.append(kw)
    keyword_score = min(25, 8 + len(matched_boosts) * 5) if matched_boosts else 6
    if matched_boosts:
        match_reasons.append(f"Matched priority keywords: {', '.join(matched_boosts[:4])}")

    # C. Geography & Target University Alignment (0-20)
    geo_score = 8 if (citizenship_ok and country_matched) else 0
    geo_score = min(20, geo_score + regional_bonus + institution_bonus)

    # D. GPA & Demographic / Need Alignment (0-15)
    gpa_score = 10 if student_gpa >= max(min_gpa, 3.5) else (7 if student_gpa >= min_gpa else 0)
    demographics = _normalize_list(scholarship.get("target_demographics"))
    user_demos = [d.lower() for d in _normalize_list(student.get("underrepresented_backgrounds"))]
    if demographics:
        if any(d.lower() in " ".join(user_demos) for d in demographics):
            gpa_score += 5
            match_reasons.append(f"Demographic match: {', '.join(demographics)}")
        else:
            warnings.append(
                f"Verify demographic/background requirement: {', '.join(demographics)}"
            )
            gpa_score = max(0, gpa_score - 3)
    else:
        gpa_score += 3

    if scholarship.get("requires_financial_need", False):
        if financial.get("demonstrated_financial_need", False):
            gpa_score += 2
            match_reasons.append("Demonstrated financial need criteria met")
        else:
            warnings.append("Requires demonstrated financial need")
            gpa_score = max(0, gpa_score - 4)
    gpa_score = min(15, gpa_score)

    # E. Award Value & Low Application Friction (0-15)
    value_score = 5
    if award_usd >= 50000:
        value_score = 13
    elif award_usd >= 20000:
        value_score = 10
    elif award_usd >= 10000:
        value_score = 8
    if not scholarship.get("requires_service_bond", False):
        value_score += 2
    value_score = min(15, value_score)

    raw_total = academic_score + keyword_score + geo_score + gpa_score + value_score
    filter_passed = len(rejection_reasons) == 0

    if not filter_passed:
        # Cap score if hard filters or geography failed
        fit_score = min(35, max(5, raw_total // 3))
        eligibility_status = "Filtered Out"
    elif warnings:
        fit_score = min(92, raw_total)
        eligibility_status = "Likely Eligible"
    else:
        fit_score = min(100, raw_total)
        eligibility_status = "Eligible"

    min_threshold = int(filters.get("min_fit_score_threshold", 0) or 0)
    if filter_passed and fit_score < min_threshold:
        filter_passed = False
        rejection_reasons.append(
            f"Fit score ({fit_score}) below min_fit_score_threshold ({min_threshold})"
        )
        eligibility_status = "Filtered Out"

    return {
        "scholarship_id": scholarship.get("scholarship_id", ""),
        "scholarship_name": scholarship.get("name", ""),
        "fit_score": fit_score,
        "eligibility_status": eligibility_status,
        "filter_passed": filter_passed,
        "filter_rejection_reasons": rejection_reasons,
        "score_breakdown": {
            "academic_and_degree": academic_score,
            "keywords_and_research": keyword_score,
            "geography_and_institution": geo_score,
            "gpa_and_background": gpa_score,
            "award_value": value_score,
        },
        "match_reasons": match_reasons,
        "warnings": warnings,
    }


def evaluate_scholarship_fit(
    scholarship_id: str,
    profile_path: str = "",
) -> dict[str, Any]:
    """Evaluate a specific scholarship's fit score (0-100), geography match, and filter compliance.

    Args:
        scholarship_id: Unique ID of the scholarship (e.g. 'nsf-grfp-2027', 'uw-gsee-fellowship-2027').
        profile_path: Optional override path to profile.yaml.

    Returns:
        Detailed eligibility evaluation with fit_score, score_breakdown, match_reasons, and filter status.
    """
    profile = _load_profile_dict(profile_path)
    target = next(
        (s for s in _CURATED_GRAD_FELLOWSHIPS if s["scholarship_id"] == scholarship_id),
        None,
    )
    if not target:
        return {
            "status": "error",
            "error": f"Scholarship '{scholarship_id}' not found in catalog.",
        }

    evaluation = _evaluate_single_scholarship(target, profile)
    return {
        "status": "success",
        "evaluation": evaluation,
    }


def batch_score_scholarships(
    include_filtered_out: bool = False,
    profile_path: str = "",
) -> dict[str, Any]:
    """Score and filter all cataloged scholarships against profile.yaml geographies and filters.

    Args:
        include_filtered_out: Whether to also return scholarships rejected by geography/filter rules.
        profile_path: Optional override path to profile.yaml.

    Returns:
        Dictionary with ranked scholarships, summary counts, and active geography/filter summary.
    """
    profile = _load_profile_dict(profile_path)
    only_eligible = bool(profile.get("filters", {}).get("only_show_eligible_or_likely", False))

    scored_records: list[dict[str, Any]] = []
    filtered_out_records: list[dict[str, Any]] = []

    for item in _CURATED_GRAD_FELLOWSHIPS:
        eval_res = _evaluate_single_scholarship(item, profile)
        merged = dict(item)
        merged["fit_score"] = eval_res["fit_score"]
        merged["eligibility_status"] = eval_res["eligibility_status"]
        merged["filter_passed"] = eval_res["filter_passed"]
        merged["filter_rejection_reasons"] = eval_res["filter_rejection_reasons"]
        merged["match_reasons"] = eval_res["match_reasons"]
        merged["warnings"] = eval_res["warnings"]
        merged["score_breakdown"] = eval_res["score_breakdown"]

        if eval_res["filter_passed"]:
            scored_records.append(merged)
        else:
            filtered_out_records.append(merged)

    scored_records.sort(key=lambda r: (-r["fit_score"], -r["award_amount_usd"], r["deadline"]))
    filtered_out_records.sort(key=lambda r: (-r["fit_score"], r["name"]))

    results = scored_records
    if include_filtered_out and not only_eligible:
        results = scored_records + filtered_out_records

    return {
        "status": "success",
        "matched_count": len(scored_records),
        "filtered_out_count": len(filtered_out_records),
        "active_geographies": profile.get("geographies", {}),
        "active_filters": profile.get("filters", {}),
        "scholarships": results,
        "filtered_out_summary": [
            {
                "scholarship_id": r["scholarship_id"],
                "name": r["name"],
                "reasons": r["filter_rejection_reasons"],
            }
            for r in filtered_out_records
        ],
    }
