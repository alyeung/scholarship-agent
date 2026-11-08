"""Pydantic data models for student profiles, geography/filter rules, scholarships, and essays."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class GeographiesConfig(BaseModel):
    current_country: str = "United States"
    current_state_or_province: str = "Washington"
    current_city_or_metro: str = "Seattle"
    current_region: str = "Pacific Northwest"
    study_destination_countries: list[str] = Field(
        default_factory=lambda: ["United States"]
    )
    study_destination_states_or_regions: list[str] = Field(
        default_factory=lambda: ["Any US State"]
    )
    include_national_scholarships: bool = True
    include_state_and_regional_scholarships: bool = True
    include_international_fellowships: bool = True
    excluded_countries: list[str] = Field(default_factory=list)


class FiltersConfig(BaseModel):
    min_award_amount_usd: int = 2500
    allowed_degree_levels: list[str] = Field(
        default_factory=lambda: ["Master's", "PhD", "Graduate"]
    )
    allowed_award_types: list[str] = Field(
        default_factory=lambda: [
            "Fellowship",
            "Scholarship",
            "Grant",
            "Tuition Waiver",
            "Stipend",
        ]
    )
    exclude_repayable_loans: bool = True
    exclude_service_or_employment_bonds: bool = False
    exclude_institution_locked_unless_target: bool = True
    require_no_application_fee: bool = True
    only_show_eligible_or_likely: bool = False
    min_fit_score_threshold: int = 40
    deadline_after: str = "2026-11-01"
    deadline_before: str = "2027-12-31"
    max_recommendation_letters: int = 4
    must_match_any_keywords: list[str] = Field(default_factory=list)
    boost_keywords: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)


class ScholarshipRecord(BaseModel):
    scholarship_id: str
    name: str
    provider: str
    award_amount_usd: int = 0
    award_display: str = ""
    award_type: str = "Fellowship"
    deadline: str = "Rolling"
    degree_levels: list[str] = Field(default_factory=lambda: ["Master's", "PhD"])
    fields_of_study: list[str] = Field(default_factory=lambda: ["Any"])
    allowed_citizenships: list[str] = Field(
        default_factory=lambda: ["US Citizen", "Permanent Resident", "International"]
    )
    geography_scope: str = "National"  # "National", "State/Regional", "International", "University-Specific"
    study_countries: list[str] = Field(default_factory=lambda: ["United States"])
    eligible_states_or_regions: list[str] = Field(default_factory=lambda: ["Any"])
    locked_institutions: list[str] = Field(default_factory=list)
    min_gpa: float = 0.0
    requires_service_bond: bool = False
    is_repayable_loan: bool = False
    has_application_fee: bool = False
    recommendation_letters_required: int = 2
    requires_financial_need: bool = False
    target_demographics: list[str] = Field(default_factory=list)
    essay_prompts: list[str] = Field(default_factory=list)
    description: str = ""
    source_url: str = ""
    verification_status: str = "verified_catalog"
    # Computed fields populated by the eligibility matcher
    fit_score: int = 0
    eligibility_status: str = "Unscored"
    filter_passed: bool = True
    filter_rejection_reasons: list[str] = Field(default_factory=list)
    match_reasons: list[str] = Field(default_factory=list)
    application_status: str = "discovered"


class EligibilityEvaluation(BaseModel):
    scholarship_id: str
    scholarship_name: str
    fit_score: int
    eligibility_status: str  # "Eligible", "Likely Eligible", "Filtered Out", "Ineligible"
    filter_passed: bool
    filter_rejection_reasons: list[str] = Field(default_factory=list)
    score_breakdown: dict[str, int] = Field(default_factory=dict)
    match_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
