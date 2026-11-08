"""Tools for searching curated graduate fellowships, live web search, and safe page scraping."""

from __future__ import annotations

import re
import urllib.parse
from typing import Any

from bs4 import BeautifulSoup
import httpx

# Prompt-injection patterns stripped from untrusted external web content
# (Harness Engineering Defense Layer - Section 2C of the DevFest architecture deck)
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"system\s*prompt\s*:", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.IGNORECASE),
    re.compile(r"<\s*/?\s*(script|style|iframe|object|embed)[^>]*>", re.IGNORECASE),
    re.compile(r"\brm\s+-rf\b", re.IGNORECASE),
]

# High-signal curated catalog of real graduate school fellowships & scholarships
# spanning National, State/Regional (WA/PNW/CA), International (UK/Canada), and University awards.
_CURATED_GRAD_FELLOWSHIPS: list[dict[str, Any]] = [
    {
        "scholarship_id": "nsf-grfp-2027",
        "name": "NSF Graduate Research Fellowship Program (GRFP)",
        "provider": "National Science Foundation",
        "award_amount_usd": 159000,
        "award_display": "$37,000/yr stipend + $16,000/yr tuition for 3 years ($159,000 total)",
        "award_type": "Fellowship",
        "deadline": "2027-10-15",
        "degree_levels": ["Master's", "PhD"],
        "fields_of_study": ["STEM", "Computer Science", "Artificial Intelligence", "Engineering", "Mathematics"],
        "allowed_citizenships": ["US Citizen", "Permanent Resident"],
        "geography_scope": "National",
        "study_countries": ["United States"],
        "eligible_states_or_regions": ["Any"],
        "locked_institutions": [],
        "min_gpa": 3.0,
        "requires_service_bond": False,
        "is_repayable_loan": False,
        "has_application_fee": False,
        "recommendation_letters_required": 3,
        "requires_financial_need": False,
        "target_demographics": [],
        "essay_prompts": [
            "Personal, Relevant Background and Future Goals Statement (3 pages): Describe how your experiences prepared you for graduate research and broader societal impacts.",
            "Graduate Research Plan Statement (2 pages): Present an original research topic, methodology, and intellectual merit / broader impacts.",
        ],
        "description": "Five-year fellowship providing three years of financial support for outstanding graduate students in NSF-supported STEM disciplines pursuing research-based Master's and doctoral degrees.",
        "source_url": "https://www.nsfgrfp.org/",
        "verification_status": "verified_catalog",
    },
    {
        "scholarship_id": "gem-fellowship-2027",
        "name": "National GEM Consortium MS & PhD Engineering/Science Fellowship",
        "provider": "The National GEM Consortium",
        "award_amount_usd": 40000,
        "award_display": "Full tuition & fees + $16,000+ stipend + paid industry internship",
        "award_type": "Fellowship",
        "deadline": "2026-11-15",
        "degree_levels": ["Master's", "PhD"],
        "fields_of_study": ["STEM", "Computer Science", "Engineering", "Artificial Intelligence", "Physical Sciences"],
        "allowed_citizenships": ["US Citizen", "Permanent Resident"],
        "geography_scope": "National",
        "study_countries": ["United States"],
        "eligible_states_or_regions": ["Any"],
        "locked_institutions": [],
        "min_gpa": 2.8,
        "requires_service_bond": False,
        "is_repayable_loan": False,
        "has_application_fee": False,
        "recommendation_letters_required": 3,
        "requires_financial_need": False,
        "target_demographics": ["Underrepresented in STEM"],
        "essay_prompts": [
            "Statement of Purpose (500-1000 words): Detail your academic background, research goals in STEM, and career objectives.",
        ],
        "description": "Supports Master's and PhD students in engineering and computer science at GEM Member Universities (including UW, Stanford, UC Berkeley, and CMU) with full tuition, stipend, and summer research internships.",
        "source_url": "https://www.gemfellowship.org/gem-fellowship-program/",
        "verification_status": "verified_catalog",
    },
    {
        "scholarship_id": "knight-hennessy-2027",
        "name": "Knight-Hennessy Scholars at Stanford University",
        "provider": "Stanford University",
        "award_amount_usd": 90000,
        "award_display": "Full funding for up to 3 years (tuition + stipend + academic allowance)",
        "award_type": "Fellowship",
        "deadline": "2027-10-08",
        "degree_levels": ["Master's", "PhD", "MBA", "JD", "MD"],
        "fields_of_study": ["Any", "STEM", "Computer Science", "Artificial Intelligence", "Business", "Policy"],
        "allowed_citizenships": ["US Citizen", "Permanent Resident", "International", "DACA"],
        "geography_scope": "University-Specific",
        "study_countries": ["United States"],
        "eligible_states_or_regions": ["California"],
        "locked_institutions": ["Stanford University"],
        "min_gpa": 3.5,
        "requires_service_bond": False,
        "is_repayable_loan": False,
        "has_application_fee": False,
        "recommendation_letters_required": 2,
        "requires_financial_need": False,
        "target_demographics": [],
        "essay_prompts": [
            "Connect the dots: How have the influences in your life shaped you, and how will Knight-Hennessy help you achieve your vision for purposeful leadership?",
            "Tell us eight improbable facts about yourself.",
        ],
        "description": "Cultivates a multidisciplinary, multicultural community of graduate students across all seven schools at Stanford University with full tuition and living stipend.",
        "source_url": "https://knight-hennessy.stanford.edu/",
        "verification_status": "verified_catalog",
    },
    {
        "scholarship_id": "uw-gsee-fellowship-2027",
        "name": "University of Washington Graduate School Presidential & GSEE Fellowships",
        "provider": "University of Washington Graduate School (Seattle, WA)",
        "award_amount_usd": 36000,
        "award_display": "Full resident/non-resident tuition waiver + $28,000-$36,000 academic year stipend",
        "award_type": "Fellowship",
        "deadline": "2027-01-15",
        "degree_levels": ["Master's", "PhD"],
        "fields_of_study": ["Any", "STEM", "Computer Science", "Artificial Intelligence", "Engineering"],
        "allowed_citizenships": ["US Citizen", "Permanent Resident", "International", "DACA"],
        "geography_scope": "State/Regional",
        "study_countries": ["United States"],
        "eligible_states_or_regions": ["Washington", "Pacific Northwest", "Seattle"],
        "locked_institutions": ["University of Washington"],
        "min_gpa": 3.2,
        "requires_service_bond": False,
        "is_repayable_loan": False,
        "has_application_fee": False,
        "recommendation_letters_required": 3,
        "requires_financial_need": False,
        "target_demographics": [],
        "essay_prompts": [
            "Graduate Statement of Purpose & Personal History Statement: Articulate your research trajectory at UW Seattle and contributions to academic excellence and community leadership.",
        ],
        "description": "University of Washington fellowships supporting incoming Master's and PhD students in Seattle, WA with tuition coverage, GAIP health insurance, and monthly living stipends.",
        "source_url": "https://grad.uw.edu/graduate-student-funding/for-students/fellowships/",
        "verification_status": "verified_catalog",
    },
    {
        "scholarship_id": "arcs-seattle-2027",
        "name": "ARCS Foundation Seattle Chapter Graduate Fellowship (Washington STEM)",
        "provider": "ARCS Foundation Seattle Chapter",
        "award_amount_usd": 22500,
        "award_display": "$7,500/yr for 3 years ($22,500 unrestricted cash award)",
        "award_type": "Fellowship",
        "deadline": "2027-02-01",
        "degree_levels": ["Master's", "PhD"],
        "fields_of_study": ["STEM", "Computer Science", "Engineering", "Life Sciences"],
        "allowed_citizenships": ["US Citizen"],
        "geography_scope": "State/Regional",
        "study_countries": ["United States"],
        "eligible_states_or_regions": ["Washington", "Pacific Northwest", "Seattle"],
        "locked_institutions": ["University of Washington", "Washington State University"],
        "min_gpa": 3.5,
        "requires_service_bond": False,
        "is_repayable_loan": False,
        "has_application_fee": False,
        "recommendation_letters_required": 2,
        "requires_financial_need": False,
        "target_demographics": [],
        "essay_prompts": [
            "Research & Impact Statement: Explain how your STEM graduate research in Washington State advances scientific innovation.",
        ],
        "description": "Provides unrestricted financial awards to outstanding US citizens pursuing graduate degrees in science, engineering, and computer science in Washington State.",
        "source_url": "https://seattle.arcsfoundation.org/",
        "verification_status": "verified_catalog",
    },
    {
        "scholarship_id": "wa-wsos-grts-2027",
        "name": "Washington State Opportunity Scholarship — Graduate Program",
        "provider": "Washington State Opportunity Scholarship (WSOS)",
        "award_amount_usd": 25000,
        "award_display": "Up to $25,000 total graduate tuition & stipend support",
        "award_type": "Scholarship",
        "deadline": "2027-05-01",
        "degree_levels": ["Master's", "PhD"],
        "fields_of_study": ["STEM", "Healthcare", "Computer Science", "Engineering"],
        "allowed_citizenships": ["US Citizen", "Permanent Resident", "DACA"],
        "geography_scope": "State/Regional",
        "study_countries": ["United States"],
        "eligible_states_or_regions": ["Washington", "Pacific Northwest"],
        "locked_institutions": [],
        "min_gpa": 3.0,
        "requires_service_bond": False,
        "is_repayable_loan": False,
        "has_application_fee": False,
        "recommendation_letters_required": 1,
        "requires_financial_need": True,
        "target_demographics": [],
        "essay_prompts": [
            "Washington Community Impact Essay: Describe your connection to Washington State and how your graduate degree will address critical workforce needs in the Pacific Northwest.",
        ],
        "description": "Regional public-private scholarship supporting Washington State residents pursuing high-demand graduate programs in Washington.",
        "source_url": "https://www.waopportunityscholarship.org/",
        "verification_status": "verified_catalog",
    },
    {
        "scholarship_id": "pd-soros-2027",
        "name": "Paul & Daisy Soros Fellowships for New Americans",
        "provider": "The Paul & Daisy Soros Fellowships",
        "award_amount_usd": 90000,
        "award_display": "Up to $90,000 ($25,000/yr stipend + 50% tuition up to $20,000/yr for 2 years)",
        "award_type": "Fellowship",
        "deadline": "2027-10-30",
        "degree_levels": ["Master's", "PhD", "MBA", "JD", "MD"],
        "fields_of_study": ["Any", "STEM", "Computer Science", "Artificial Intelligence", "Business", "Law", "Medicine"],
        "allowed_citizenships": ["US Citizen", "Permanent Resident", "DACA"],
        "geography_scope": "National",
        "study_countries": ["United States"],
        "eligible_states_or_regions": ["Any"],
        "locked_institutions": [],
        "min_gpa": 3.3,
        "requires_service_bond": False,
        "is_repayable_loan": False,
        "has_application_fee": False,
        "recommendation_letters_required": 3,
        "requires_financial_need": False,
        "target_demographics": ["Immigrants & Children of Immigrants"],
        "essay_prompts": [
            "Essay 1 (1,000 words): Tell us about your experiences as a New American (immigrant or child of immigrants) and how they have shaped your intellectual and creative work.",
            "Essay 2 (1,000 words): Describe your career goals and why you selected your graduate program.",
        ],
        "description": "Merit-based two-year graduate fellowship for immigrants and children of immigrants pursuing full-time graduate degrees at accredited US institutions.",
        "source_url": "https://www.pdsoros.org/",
        "verification_status": "verified_catalog",
    },
    {
        "scholarship_id": "dod-smart-2026",
        "name": "DoD SMART Scholarship-for-Service Program (Graduate MS/PhD)",
        "provider": "U.S. Department of Defense",
        "award_amount_usd": 75000,
        "award_display": "Full tuition + $30,000-$46,000/yr stipend + summer internships + guaranteed placement",
        "award_type": "Scholarship",
        "deadline": "2026-12-06",
        "degree_levels": ["Master's", "PhD"],
        "fields_of_study": ["STEM", "Computer Science", "Artificial Intelligence", "Engineering", "Cybersecurity"],
        "allowed_citizenships": ["US Citizen", "United Kingdom", "Canada", "Australia", "New Zealand"],
        "geography_scope": "National",
        "study_countries": ["United States"],
        "eligible_states_or_regions": ["Any"],
        "locked_institutions": [],
        "min_gpa": 3.0,
        "requires_service_bond": True,
        "is_repayable_loan": False,
        "has_application_fee": False,
        "recommendation_letters_required": 2,
        "requires_financial_need": False,
        "target_demographics": [],
        "essay_prompts": [
            "Leadership & Research Statement: Describe your STEM research experience, leadership/mentorship, and how your work aligns with defense science and technology missions.",
        ],
        "description": "Provides full tuition and generous stipends for STEM Master's and PhD students in exchange for 1:1 post-graduation civilian employment at a DoD research laboratory.",
        "source_url": "https://www.smartscholarship.org/",
        "verification_status": "verified_catalog",
    },
    {
        "scholarship_id": "gates-cambridge-2027",
        "name": "Gates Cambridge Scholarship (UK Graduate Study)",
        "provider": "Bill & Melinda Gates Foundation / University of Cambridge",
        "award_amount_usd": 65000,
        "award_display": "Full Cambridge tuition + £21,000/yr maintenance stipend + airfare",
        "award_type": "Scholarship",
        "deadline": "2027-10-15",
        "degree_levels": ["Master's", "PhD"],
        "fields_of_study": ["Any", "STEM", "Computer Science", "Artificial Intelligence", "Humanities"],
        "allowed_citizenships": ["US Citizen", "Permanent Resident", "International"],
        "geography_scope": "International",
        "study_countries": ["United Kingdom"],
        "eligible_states_or_regions": ["International", "United Kingdom"],
        "locked_institutions": [],
        "min_gpa": 3.7,
        "requires_service_bond": False,
        "is_repayable_loan": False,
        "has_application_fee": False,
        "recommendation_letters_required": 3,
        "requires_financial_need": False,
        "target_demographics": [],
        "essay_prompts": [
            "Gates Cambridge Statement (500 words): Explain why you are applying for a Gates Cambridge Scholarship and how you meet the four criteria: intellectual ability, reasons for choice of course, commitment to improving the lives of others, and leadership potential.",
        ],
        "description": "Full-cost international scholarship for outstanding applicants from outside the UK to pursue a full-time postgraduate degree (MPhil or PhD) in any subject at the University of Cambridge.",
        "source_url": "https://www.gatescambridge.org/",
        "verification_status": "verified_catalog",
    },
    {
        "scholarship_id": "fulbright-study-research-2027",
        "name": "Fulbright U.S. Student Program — Graduate Study/Research Grants (Canada, UK & Global)",
        "provider": "U.S. Department of State / IIE",
        "award_amount_usd": 35000,
        "award_display": "Round-trip travel + full living stipend + tuition allowance for 1 academic year",
        "award_type": "Grant",
        "deadline": "2027-10-08",
        "degree_levels": ["Master's", "PhD"],
        "fields_of_study": ["Any", "STEM", "Computer Science", "Artificial Intelligence", "Social Sciences", "Humanities"],
        "allowed_citizenships": ["US Citizen"],
        "geography_scope": "International",
        "study_countries": ["United Kingdom", "Canada", "Germany", "Australia", "Japan"],
        "eligible_states_or_regions": ["International"],
        "locked_institutions": [],
        "min_gpa": 3.2,
        "requires_service_bond": False,
        "is_repayable_loan": False,
        "has_application_fee": False,
        "recommendation_letters_required": 3,
        "requires_financial_need": False,
        "target_demographics": [],
        "essay_prompts": [
            "Statement of Grant Purpose (2 pages): Outline What, How, and Why for your graduate degree or research project in the host country.",
            "Personal Statement (1 page): Provide a narrative of your intellectual trajectory and cross-cultural engagement.",
        ],
        "description": "Funds one year of graduate degree enrollment or independent research in 140+ countries including Canada and the United Kingdom.",
        "source_url": "https://us.fulbrightonline.org/",
        "verification_status": "verified_catalog",
    },
    {
        "scholarship_id": "google-generation-grad-2027",
        "name": "Generation Google Scholarship & Google PhD/MS CS Awards (North America)",
        "provider": "Google Research & Education",
        "award_amount_usd": 10000,
        "award_display": "$10,000 USD (US) or $5,000 CAD (Canada) for Computer Science students",
        "award_type": "Scholarship",
        "deadline": "2027-04-23",
        "degree_levels": ["Master's", "PhD"],
        "fields_of_study": ["STEM", "Computer Science", "Artificial Intelligence", "Machine Learning"],
        "allowed_citizenships": ["US Citizen", "Permanent Resident", "International", "DACA"],
        "geography_scope": "National",
        "study_countries": ["United States", "Canada"],
        "eligible_states_or_regions": ["Any"],
        "locked_institutions": [],
        "min_gpa": 3.5,
        "requires_service_bond": False,
        "is_repayable_loan": False,
        "has_application_fee": False,
        "recommendation_letters_required": 2,
        "requires_financial_need": True,
        "target_demographics": [],
        "essay_prompts": [
            "Technical Challenge Essay (400 words): Describe a complex technical problem in computer science or AI you solved and what you learned.",
            "Community & Leadership Essay (400 words): Give an example of how you have exhibited leadership and mentored others in technology.",
        ],
        "description": "Supports students pursuing computer science, artificial intelligence, or computer engineering degrees at accredited universities in the United States and Canada.",
        "source_url": "https://buildyourfuture.withgoogle.com/scholarships",
        "verification_status": "verified_catalog",
    },
    {
        "scholarship_id": "hertz-fellowship-2027",
        "name": "Fannie and John Hertz Foundation Graduate Fellowship",
        "provider": "The Hertz Foundation",
        "award_amount_usd": 250000,
        "award_display": "Up to $250,000 over 5 years ($38,000/yr stipend + full tuition equivalent)",
        "award_type": "Fellowship",
        "deadline": "2027-10-31",
        "degree_levels": ["PhD"],
        "fields_of_study": ["STEM", "Computer Science", "Artificial Intelligence", "Engineering", "Applied Sciences"],
        "allowed_citizenships": ["US Citizen", "Permanent Resident"],
        "geography_scope": "National",
        "study_countries": ["United States"],
        "eligible_states_or_regions": ["Any"],
        "locked_institutions": [],
        "min_gpa": 3.7,
        "requires_service_bond": False,
        "is_repayable_loan": False,
        "has_application_fee": False,
        "recommendation_letters_required": 4,
        "requires_financial_need": False,
        "target_demographics": [],
        "essay_prompts": [
            "Technical & Research Vision Essay: Explain the most significant technical problem you want to tackle in your graduate career and why independent funding empowers your approach.",
        ],
        "description": "Prestigious fellowship for PhD students (and MS/PhD track students) in applied physical, biological, and engineering sciences including AI and computer science.",
        "source_url": "https://www.hertzfoundation.org/the-fellowship/",
        "verification_status": "verified_catalog",
    },
    {
        "scholarship_id": "tx-good-neighbor-2027",
        "name": "Texas Public Educational Grant (Out-of-Region Demo Filter Test)",
        "provider": "Texas Higher Education Coordinating Board",
        "award_amount_usd": 5000,
        "award_display": "$5,000 Texas state tuition grant",
        "award_type": "Grant",
        "deadline": "2027-03-15",
        "degree_levels": ["Master's", "PhD"],
        "fields_of_study": ["Any"],
        "allowed_citizenships": ["US Citizen", "Permanent Resident"],
        "geography_scope": "State/Regional",
        "study_countries": ["United States"],
        "eligible_states_or_regions": ["Texas"],
        "locked_institutions": ["University of Texas at Austin"],
        "min_gpa": 3.0,
        "requires_service_bond": False,
        "is_repayable_loan": False,
        "has_application_fee": False,
        "recommendation_letters_required": 1,
        "requires_financial_need": True,
        "target_demographics": [],
        "essay_prompts": [
            "Texas Residency & Statement of Financial Need.",
        ],
        "description": "State-restricted grant requiring Texas residency and attendance at a public university in Texas.",
        "source_url": "https://www.highered.texas.gov/",
        "verification_status": "verified_catalog",
    },
]


def _sanitize_untrusted_text(raw_text: str, max_chars: int = 4000) -> dict[str, Any]:
    """Sanitize scraped external web text against prompt injection before returning to the model."""
    text = raw_text or ""
    flagged_patterns: list[str] = []
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            flagged_patterns.append(pattern.pattern)
            text = pattern.sub("[REDACTED_BY_HARNESS_GUARD]", text)

    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars] + "... [truncated]"

    return {
        "clean_text": cleaned,
        "injection_detected": len(flagged_patterns) > 0,
        "flagged_patterns": flagged_patterns,
    }


def search_curated_fellowships(
    query: str = "",
    geography_scope: str = "",
    study_country: str = "",
) -> dict[str, Any]:
    """Search the curated catalog of graduate school fellowships with optional geography and keyword filters.

    Args:
        query: Optional search keyword (e.g. 'AI', 'Washington', 'STEM', 'Stanford', 'UK'). Leave empty to return all.
        geography_scope: Optional scope filter ('National', 'State/Regional', 'International', 'University-Specific').
        study_country: Optional destination country filter (e.g. 'United States', 'United Kingdom', 'Canada').

    Returns:
        Dictionary containing status, count, and matching scholarship records.
    """
    q = (query or "").strip().lower()
    scope_filter = (geography_scope or "").strip().lower()
    country_filter = (study_country or "").strip().lower()

    matches: list[dict[str, Any]] = []
    for item in _CURATED_GRAD_FELLOWSHIPS:
        if scope_filter and item["geography_scope"].lower() != scope_filter:
            continue
        if country_filter:
            countries_lower = [c.lower() for c in item["study_countries"]]
            if country_filter not in countries_lower:
                continue
        if q:
            searchable = " ".join(
                [
                    item["name"],
                    item["provider"],
                    item["description"],
                    " ".join(item["fields_of_study"]),
                    " ".join(item["eligible_states_or_regions"]),
                    " ".join(item["study_countries"]),
                    " ".join(item["locked_institutions"]),
                ]
            ).lower()
            if not any(token in searchable for token in q.split()):
                continue
        matches.append(dict(item))

    return {
        "status": "success",
        "count": len(matches),
        "scholarships": matches,
    }


def search_scholarships_web(query: str, max_results: int = 8) -> dict[str, Any]:
    """Perform a live web search for graduate school scholarships and combine with curated matches.

    Args:
        query: Search query string (e.g. 'computer science graduate fellowship Washington state 2027').
        max_results: Maximum number of web search results to return (default 8).

    Returns:
        Dictionary with status, query, live_web_results (sanitized), and curated_matches.
    """
    curated = search_curated_fellowships(query=query)["scholarships"]
    live_results: list[dict[str, Any]] = []
    web_error: str | None = None

    try:
        encoded = urllib.parse.quote_plus(f"{query} graduate scholarship fellowship")
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            )
        }
        with httpx.Client(timeout=8.0, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for result_node in soup.select(".result")[: max(1, min(max_results, 15))]:
                    title_el = result_node.select_one(".result__a")
                    snippet_el = result_node.select_one(".result__snippet")
                    if not title_el:
                        continue
                    raw_title = title_el.get_text(" ", strip=True)
                    raw_href = str(title_el.get("href", ""))
                    raw_snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""
                    sanitized_title = _sanitize_untrusted_text(raw_title, max_chars=200)
                    sanitized_snippet = _sanitize_untrusted_text(raw_snippet, max_chars=500)
                    live_results.append(
                        {
                            "title": sanitized_title["clean_text"],
                            "url": raw_href,
                            "snippet": sanitized_snippet["clean_text"],
                            "injection_filtered": (
                                sanitized_title["injection_detected"]
                                or sanitized_snippet["injection_detected"]
                            ),
                        }
                    )
    except Exception as exc:
        web_error = str(exc)

    return {
        "status": "success",
        "query": query,
        "live_web_results_count": len(live_results),
        "live_web_results": live_results,
        "curated_matches_count": len(curated),
        "curated_matches": curated[:max_results],
        "web_notice": web_error or "Live search completed and sanitized via harness guard.",
    }


def scrape_scholarship_page(url: str) -> dict[str, Any]:
    """Fetch and extract key scholarship details (deadlines, dollar amounts, text) from a URL safely.

    All fetched HTML content passes through the harness prompt-injection sanitizer before
    returning to the agent.

    Args:
        url: Official http/https URL of the scholarship page.

    Returns:
        Dictionary with extracted title, detected_dollar_amounts, detected_dates, and sanitized_text.
    """
    parsed = urllib.parse.urlparse((url or "").strip())
    if parsed.scheme not in ("http", "https"):
        return {
            "status": "error",
            "error": "Only http:// and https:// URLs are permitted by the harness guard.",
        }

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            )
        }
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            html = resp.text
    except Exception as exc:
        return {
            "status": "error",
            "url": url,
            "error": f"Failed to fetch URL: {exc}",
        }

    return _parse_and_sanitize_html(url, html)


def _parse_and_sanitize_html(url: str, html: str) -> dict[str, Any]:
    """Internal helper to extract scholarship signals from HTML and apply prompt-injection sanitization."""
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
        tag.decompose()

    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    body_text = soup.get_text(" ", strip=True)
    sanitized = _sanitize_untrusted_text(body_text, max_chars=3500)

    dollar_matches = list(
        dict.fromkeys(re.findall(r"\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?", sanitized["clean_text"]))
    )
    date_matches = list(
        dict.fromkeys(
            re.findall(
                r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
                r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
                r"\s+\d{1,2},?\s+202[6-9]\b|\b202[6-9]-\d{2}-\d{2}\b",
                sanitized["clean_text"],
                flags=re.IGNORECASE,
            )
        )
    )

    return {
        "status": "success",
        "url": url,
        "title": _sanitize_untrusted_text(title, max_chars=250)["clean_text"],
        "detected_dollar_amounts": dollar_matches[:10],
        "detected_dates": date_matches[:10],
        "sanitized_text": sanitized["clean_text"],
        "injection_detected": sanitized["injection_detected"],
        "verification_status": "scraped_live",
    }
