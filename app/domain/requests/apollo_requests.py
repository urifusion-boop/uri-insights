from pydantic import BaseModel, Field, field_validator, root_validator, validator
from typing import Optional, List

from app.domain.enums.apollo_enum import ContactEmailStatusEnum, PersonSenioritiesEnum


class BaseApolloSearchRequest(BaseModel):
    """
    Base model containing common fields shared between Apollo person and organization search requests.
    Provides standardized validation and configuration for pagination, organizational targeting,
    and location-based filtering.
    """

    organization_locations: Optional[List[str]] = Field(
        None,
        description="Headquarters locations (cities, states, or countries) for organizational targeting",
        max_items=20,
    )

    organization_ids: Optional[List[str]] = Field(
        None,
        description="Apollo-specific organization IDs for targeting known companies",
        max_items=50,
    )

    organization_num_employees_ranges: Optional[List[str]] = Field(
        None,
        description="Employee count ranges formatted as 'min,max' (e.g., '1,10', '250,500')",
        max_items=10,
    )

    page: int = Field(1, ge=1, description="Page number for paginated results")

    per_page: int = Field(10, ge=1, description="Number of results per page")

    @field_validator("organization_num_employees_ranges")
    def validate_employee_ranges(cls, v):
        if not v:
            return v

        valid_ranges = []
        seen = set()

        for range_str in v:
            if isinstance(range_str, str):
                cleaned = range_str.strip()

                # Validate format: "min,max" where both are integers
                if "," in cleaned:
                    try:
                        min_val, max_val = cleaned.split(",", 1)
                        min_employees = int(min_val.strip())
                        max_employees = int(max_val.strip())

                        # Validate logical range
                        if min_employees >= 0 and max_employees > min_employees:
                            formatted_range = f"{min_employees},{max_employees}"
                            if formatted_range not in seen:
                                seen.add(formatted_range)
                                valid_ranges.append(formatted_range)
                    except ValueError:
                        # Skip invalid ranges
                        continue

        return valid_ranges if valid_ranges else None

    class Config:
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"
        json_schema_extra = {
            "example": {
                "organization_locations": ["EMEA", "Abuja", "San Francisco"],
                "organization_ids": ["abc123", "def456"],
                "organization_num_employees_ranges": ["1,50", "100,500"],
                "page": 1,
                "per_page": 25,
            }
        }


class PersonSearchRequest(BaseApolloSearchRequest):
    """
    Represents the full set of query parameters that can be used to filter people
    in Apollo's person search API. This model allows for precise targeting of individuals
    based on a combination of professional attributes, organizational affiliation, and metadata.
    """

    person_titles: Optional[List[str]] = Field(
        None,
        description="Job titles held by the individuals you want to find. Matches include both exact and similar job titles unless 'include_similar_titles' is set to False",
        max_items=25,
    )

    include_similar_titles: bool = Field(
        True,
        description="If True, the search will include job titles similar to those specified in 'person_titles'. If False, only exact matches will be included",
    )

    person_locations: Optional[List[str]] = Field(
        None,
        description="Locations (cities, states, or countries) where individuals reside",
        max_items=20,
    )

    person_seniorities: Optional[List[PersonSenioritiesEnum]] = Field(
        None,
        description="Current job seniority levels of individuals (e.g., VP, Director, Entry). Helps refine results by position level",
        max_items=10,
    )

    q_organization_domains_list: Optional[List[str]] = Field(
        None,
        description="Employer domains (e.g., 'microsoft.com')—can match current or previous organizations",
        max_items=30,
    )

    contact_email_status: Optional[List[ContactEmailStatusEnum]] = Field(
        None,
        description="Email verification statuses such as 'verified', 'unverified', or 'likely to engage'",
        max_items=5,
    )

    q_keywords: Optional[str] = Field(
        None,
        description="Keywords for semantic or contextual filtering within the profile dataset",
        max_length=500,
    )

    # Location Intelligence fields (only used for Organization forms, but included here to prevent validation errors)
    currently_using_any_of_technology_uids: Optional[List[str]] = Field(
        None,
        description="Technology UIDs for filtering organizations",
    )
    enable_location_intelligence: Optional[bool] = Field(
        None,
        description="Enable Location Intelligence feature (Organization forms only)",
    )
    location_zone_center_lat: Optional[float] = Field(
        None,
        description="Latitude of target zone center (Organization forms only)",
    )
    location_zone_center_lng: Optional[float] = Field(
        None,
        description="Longitude of target zone center (Organization forms only)",
    )
    location_zone_radius_km: Optional[float] = Field(
        None,
        description="Radius in kilometers for target zone (Organization forms only)",
    )
    location_zone_name: Optional[str] = Field(
        None,
        description="Name of target zone location (Organization forms only)",
    )
    min_trust_score: Optional[float] = Field(
        None,
        description="Minimum trust score threshold (Organization forms only)",
    )

    class Config:
        use_enum_values = True
        validate_assignment = True
        json_schema_extra = {
            "example": {
                "form_title": "My Personal form",
                "user_id": "user_007",
                "person_titles": [
                    "Software Engineer",
                    "Backend Developer",
                    "Lead Engineer",
                ],
                "auto_generate": False,
                "add_to_history": True,
                "include_similar_titles": True,
                "person_locations": ["Lagos", "Remote"],
                "person_seniorities": ["senior", "manager"],
                "organization_locations": ["Lagos", "San Francisco"],
                "q_organization_domains_list": ["microsoft.com", "google.com"],
                "contact_email_status": ["verified", "likely to engage"],
                "q_keywords": "fintech blockchain",
                "per_page": 10,
            }
        }


class OrganizationSearchRequest(BaseApolloSearchRequest):
    """
    Query model for Apollo's Organization Search API.

    This model captures all query parameters available when searching for companies
    in the Apollo database. It allows you to filter results by company size, location,
    revenue, technology usage, keywords, and more.
    """

    organization_not_locations: Optional[List[str]] = Field(
        None,
        description="Locations to exclude from search results (e.g., 'Ireland', 'Seoul')",
        max_items=20,
    )

    revenue_range_min: Optional[int] = Field(
        None,
        alias="revenue_range[min]",
        description="Lower bound of the company's revenue range. Should be a raw integer (e.g., 300000)",
    )

    revenue_range_max: Optional[int] = Field(
        None,
        alias="revenue_range[max]",
        description="Upper bound of the company's revenue range. Should be a raw integer (e.g., 50000000)",
    )

    currently_using_any_of_technology_uids: Optional[List[str]] = Field(
        None,
        description="Technology identifiers for technologies the organization is currently using. Use underscores instead of spaces or periods (e.g., 'google_analytics', 'salesforce')",
        max_items=50,
    )

    q_organization_keyword_tags: Optional[List[str]] = Field(
        None,
        description="Keywords associated with the company (e.g., 'mining', 'consulting')",
        max_items=20,
    )

    q_organization_name: Optional[str] = Field(
        None,
        description="Partial or full name of the company to filter by",
        max_length=200,
    )

    q_organization_domains_list: Optional[List[str]] = Field(
        None,
        description="Company domains for filtering (e.g., 'microsoft.com', 'google.com')",
        max_items=30,
    )

    # Location Intelligence fields (URI-branded geographic targeting)
    enable_location_intelligence: Optional[bool] = Field(
        None,
        description="Enable Location Intelligence feature for geographic targeting",
    )
    location_zone_center_lat: Optional[float] = Field(
        None,
        description="Latitude of target zone center",
    )
    location_zone_center_lng: Optional[float] = Field(
        None,
        description="Longitude of target zone center",
    )
    location_zone_radius_km: Optional[float] = Field(
        None,
        description="Radius in kilometers for target zone",
    )
    location_zone_name: Optional[str] = Field(
        None,
        description="Name of target zone location",
    )
    min_trust_score: Optional[float] = Field(
        None,
        description="Minimum trust score threshold (20-100 scale)",
    )

    @root_validator(pre=True)
    def validate_revenue_range(cls, values):
        min_val = values.get("revenue_range_min")
        max_val = values.get("revenue_range_max")

        # Both values are explicitly zero -> treat as unset
        if min_val == 0 and max_val == 0:
            values["revenue_range_min"] = None
            values["revenue_range_max"] = None
            return values

        # If one is set and the other isn't -> raise error
        if (min_val is None and max_val is not None) or (
            min_val is not None and max_val is None
        ):
            raise ValueError(
                "Both revenue_range_min and revenue_range_max must be set together."
            )

        # If either is negative -> raise error
        if (min_val is not None and min_val < 0) or (
            max_val is not None and max_val < 0
        ):
            raise ValueError("Revenue values cannot be negative.")

        # If both are set and positive, ensure max > min
        if min_val is not None and max_val is not None:
            if max_val <= min_val:
                raise ValueError(
                    "revenue_range_max must be greater than revenue_range_min."
                )

        return values

    class Config:
        use_enum_values = True
        validate_assignment = True
        populate_by_name = True  # Allows using aliases
        json_schema_extra = {
            "example": {
                "form_title": "My Organizational form",
                "user_id": "user_007",
                "auto_generate": False,
                "add_to_history": True,
                "organization_locations": ["EMEA", "San Francisco"],
                "organization_not_locations": ["Ireland", "Seoul"],
                "revenue_range_min": 1000000,
                "revenue_range_max": 50000000,
                "organization_num_employees_ranges": ["50,200", "500,1000"],
                "technology_uids": [
                    "salesforce",
                    "google_analytics",
                ],
                "q_organization_keyword_tags": ["fintech", "blockchain", "saas"],
                "q_organization_name": "Tech Company",
                "per_page": 10,
            }
        }


class EnrichPersonRequest(BaseModel):
    """
    Parameters for enriching a person profile using Apollo's enrichment endpoint.

    Attributes:
        first_name (str):
            The first name of the person. Optional if 'name' is provided.

        last_name (str):
            The last name of the person. Optional if 'name' is provided.

        name (str):
            The full name of the person (e.g., "Tim Zheng"). If provided, 'first_name' and 'last_name' are not required.

        email (str):
            The person's email address. Can be used for direct lookup.

        hashed_email (str):
            MD5 or SHA-256 hashed email string used for privacy-preserving lookup.

        organization_name (str):
            The name of the person's employer (current or past).

        domain (str):
            The domain name of the person’s current or past employer (e.g., "apollo.io").

        id (str):
            Apollo ID for the individual. Returned from previous people search requests.

        linkedin_url (str):
            LinkedIn profile URL of the individual.

        reveal_personal_emails (bool):
            Whether to reveal personal emails, if available. Defaults to False. May consume credits.

        reveal_phone_number (bool):
            Whether to enrich with phone numbers. Requires 'webhook_url'. Defaults to False.

        webhook_url (str):
            Webhook endpoint to receive phone number data asynchronously if 'reveal_phone_number' is True.
    """

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    hashed_email: Optional[str] = None
    organization_name: Optional[str] = None
    domain: Optional[str] = None
    id: Optional[str] = None
    linkedin_url: Optional[str] = None
    reveal_personal_emails: Optional[bool] = False
    reveal_phone_number: Optional[bool] = False
    webhook_url: Optional[str] = None


class BulkPeopleEnrichment(BaseModel):
    """
    Request body model for Apollo's Bulk People Enrichment endpoint.

    This model allows the enrichment of up to 10 people in a single request by providing
    identifying information for each person as part of a list of detail objects.

    Attributes:
        details (List[EnrichPersonRequest]):
            A list of person identification objects to enrich. Each object can include fields like name,
            email, domain, or LinkedIn URL. Up to 10 people can be enriched per request.

        reveal_personal_emails (bool):
            Set to True to retrieve personal emails where available. Default is False. Consumes credits.

        reveal_phone_number (bool):
            Set to True to retrieve all available phone numbers including mobile. Requires 'webhook_url'.

        webhook_url (str):
            Required if 'reveal_phone_number' is True. This is the endpoint where Apollo will send a
            separate asynchronous response containing verified phone number data.
    """

    details: List[EnrichPersonRequest] = Field(
        ..., description="List of up to 10 person objects to enrich"
    )
    reveal_personal_emails: Optional[bool] = False
    reveal_phone_number: Optional[bool] = False
    webhook_url: Optional[str] = None


class OrgEnrichRequest(BaseModel):
    domain: str


class BulkOrgEnrichRequest(BaseModel):
    emails: List[str]
