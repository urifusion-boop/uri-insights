"""
JobBoardParameterHelper - Helper functions for job board parameter conversion and inference

This module provides utilities to:
1. Convert form location lists to Apify-compatible strings
2. Intelligently infer LinkedIn parameters from job keywords
3. Map post age filters between form and Apify formats
"""
from typing import Dict, List, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


# Post age filter mappings
POST_AGE_TO_LINKEDIN = {
    "24h": "Past 24 hours",
    "7d": "Past Week",
    "30d": "Past Month",
    "3m": "Any Time",  # LinkedIn doesn't have 3 months
    "6m": "Any Time",  # LinkedIn doesn't have 6 months
    "1y": "Any Time",  # LinkedIn doesn't have 1 year
    "all": "Any Time"
}

POST_AGE_TO_JOBBERMAN = {
    "24h": "last_24_hours",
    "7d": "last_7_days",
    "30d": "last_30_days",
    "3m": "anytime",  # Jobberman doesn't have 3 months
    "6m": "anytime",  # Jobberman doesn't have 6 months
    "1y": "anytime",  # Jobberman doesn't have 1 year
    "all": "anytime"
}


def convert_location_for_job_boards(location: Optional[List[str]]) -> Tuple[Optional[str], str]:
    """
    Convert form location list to Apify-compatible format.

    Form location format: ["Lagos", "Nigeria"] or ["New York", "USA"]
    Apify format: "Lagos, Nigeria" or "New York, USA"

    Args:
        location: List of location strings from form (e.g., ["Lagos", "Nigeria"])

    Returns:
        Tuple of:
            - location_string: "City, Country" or "Country" or None
            - location_scope: "city", "country", "worldwide" for logging

    Examples:
        ["Lagos", "Nigeria"] → ("Lagos, Nigeria", "city")
        ["Nigeria"] → ("Nigeria", "country")
        ["New York", "USA"] → ("New York, USA", "city")
        ["USA"] → ("USA", "country")
        [] → (None, "worldwide")
        ["Worldwide"] → (None, "worldwide")
    """
    if not location or len(location) == 0:
        return (None, "worldwide")

    # Check for explicit worldwide keywords
    first_loc = location[0].strip() if location[0] else ""
    if first_loc.lower() in ["worldwide", "global", "remote", "anywhere"]:
        return (None, "worldwide")

    # Single location = country only
    if len(location) == 1:
        return (first_loc, "country")

    # Multiple locations = city, country format
    # Form: ["Lagos", "Nigeria"] → Apify: "Lagos, Nigeria"
    city = location[0].strip()
    country = location[1].strip()

    # Combine as "City, Country"
    location_str = f"{city}, {country}"

    return (location_str, "city")


def map_post_age_filter(post_age_filter: str, platform: str) -> str:
    """
    Map form's post age filter to platform-specific format.

    Args:
        post_age_filter: Form value (e.g., "7d", "30d", "all")
        platform: "linkedin" or "jobberman"

    Returns:
        Platform-specific time filter string

    Examples:
        ("7d", "linkedin") → "Past Week"
        ("7d", "jobberman") → "last_7_days"
        ("all", "linkedin") → "Any Time"
    """
    if platform.lower() == "linkedin":
        return POST_AGE_TO_LINKEDIN.get(post_age_filter, "Past Month")
    elif platform.lower() == "jobberman":
        return POST_AGE_TO_JOBBERMAN.get(post_age_filter, "anytime")
    else:
        return "Any Time"  # Default fallback


def infer_linkedin_parameters(job_keyword: str, solution_context: str = "") -> Dict[str, Any]:
    """
    Intelligently infer LinkedIn job search parameters from job keyword and context.

    LinkedIn uses numeric/letter codes for parameters:
    - experienceLevel: "1"=Internship, "2"=Entry, "3"=Associate, "4"=Mid-Senior, "5"=Director, "6"=Executive
    - workType: "1"=On-site, "2"=Remote, "3"=Hybrid
    - contractType: "F"=Full-time, "P"=Part-time, "C"=Contract, "T"=Temporary, "I"=Internship

    Args:
        job_keyword: The job title to search for (e.g., "Senior Software Engineer")
        solution_context: Optional context about the solution (for additional inference)

    Returns:
        Dict with inferred parameters:
            - experience_level: Experience level code ("1"-"6") or None
            - on_site_remote: Work type code ("1"-"3") or None
            - job_type: Contract type code ("F", "P", "C", "T", "I") or None

    Examples:
        "Senior Software Engineer" → {"experience_level": "4", ...}  # Mid-Senior
        "Remote DevOps Engineer" → {"on_site_remote": "2", ...}  # Remote
        "Junior Marketing Intern" → {"experience_level": "1", "job_type": "I", ...}
        "Contract Project Manager" → {"job_type": "C", ...}  # Contract
    """
    keyword_lower = job_keyword.lower()
    context_lower = solution_context.lower() if solution_context else ""

    params = {
        "experience_level": None,  # "1"-"6" or None
        "on_site_remote": None,    # "1", "2", "3" or None
        "job_type": None           # "F", "P", "C", "T", "I" or None
    }

    # === EXPERIENCE LEVEL INFERENCE ===

    # Internship indicators (LinkedIn code: "1")
    internship_keywords = ["intern", "internship", "co-op"]
    if any(word in keyword_lower for word in internship_keywords):
        params["experience_level"] = "1"  # Internship

    # Entry level indicators (LinkedIn code: "2")
    entry_keywords = ["junior", "entry", "graduate", "trainee"]
    if any(word in keyword_lower for word in entry_keywords):
        params["experience_level"] = "2"  # Entry level

    # Associate indicators (LinkedIn code: "3")
    associate_keywords = ["assistant", "associate", "coordinator"]
    if any(word in keyword_lower for word in associate_keywords):
        params["experience_level"] = "3"  # Associate

    # Senior level indicators (LinkedIn code: "4")
    senior_keywords = ["senior", "lead", "principal", "staff", "architect"]
    if any(word in keyword_lower for word in senior_keywords):
        params["experience_level"] = "4"  # Mid-Senior level

    # Director indicators (LinkedIn code: "5")
    director_keywords = ["director", "vp", "vice president", "head of"]
    if any(word in keyword_lower for word in director_keywords):
        params["experience_level"] = "5"  # Director

    # Executive indicators (LinkedIn code: "6")
    executive_keywords = ["ceo", "cto", "cfo", "coo", "chief", "executive", "president"]
    if any(word in keyword_lower for word in executive_keywords):
        params["experience_level"] = "6"  # Executive

    # If no level detected, don't set (let LinkedIn return all levels)

    # === REMOTE/ONSITE INFERENCE ===

    remote_keywords = ["remote", "work from home", "wfh", "distributed", "anywhere"]
    onsite_keywords = ["onsite", "on-site", "in-office", "office-based"]
    hybrid_keywords = ["hybrid", "flexible"]

    if any(word in keyword_lower for word in remote_keywords):
        params["on_site_remote"] = "2"  # Remote (LinkedIn code: "2")
    elif any(word in keyword_lower for word in onsite_keywords):
        params["on_site_remote"] = "1"  # On-site (LinkedIn code: "1")
    elif any(word in keyword_lower for word in hybrid_keywords):
        params["on_site_remote"] = "3"  # Hybrid (LinkedIn code: "3")
    # else: Leave as None to get all types

    # === CONTRACT TYPE INFERENCE ===

    # Internship (LinkedIn code: "I")
    if any(word in keyword_lower for word in internship_keywords):
        params["job_type"] = "I"  # Internship

    # Contract (LinkedIn code: "C")
    contract_keywords = ["contract", "contractor", "freelance", "consultant"]
    if any(word in keyword_lower for word in contract_keywords):
        params["job_type"] = "C"  # Contract

    # Part-time (LinkedIn code: "P")
    parttime_keywords = ["part-time", "part time", "parttime"]
    if any(word in keyword_lower for word in parttime_keywords):
        params["job_type"] = "P"  # Part-time

    # Temporary (LinkedIn code: "T")
    temporary_keywords = ["temporary", "temp", "seasonal"]
    if any(word in keyword_lower for word in temporary_keywords):
        params["job_type"] = "T"  # Temporary

    # Full-time is default when not specified (LinkedIn code: "F")
    # We don't set it explicitly to allow all types when not specified

    return params
