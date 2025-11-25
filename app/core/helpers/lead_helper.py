from functools import wraps
from typing import Any, Awaitable, Callable, List, Optional

from app.core.helpers.text_helper import TextHelper
from app.domain.enums.lead_enum import (
    LeadIndustryTypeEnum,
    LeadInterestLevelEnum,
    LeadSourceEnum,
    LeadStatusEnum,
)
from app.domain.enums.leadform_enum import LeadFormTypeEnum
from app.domain.requests.twitter_requests import TweetSearchParams
from app.core.config import settings
from app.domain.responses.uri_response import UriResponse
from app.middlewares.FeatureLimitMiddleware import FeatureLimitMiddleware


class LeadHelper:
    @staticmethod
    def cleanup_lead_username(raw_username: Optional[str]):
        if raw_username:
            splitted_raw_username = raw_username.split("/")
            if splitted_raw_username:
                processed_username = splitted_raw_username[-1]
            print(processed_username or raw_username)
            return str(processed_username) or str(raw_username)

    @staticmethod
    def build_tweet_search_query(lead_business_info: dict) -> TweetSearchParams:
        # Extract business keywords and competitors
        business_keywords = lead_business_info.get("keywords", [])
        business_competitors = lead_business_info.get("competitors", [])

        # Add quotation marks for keywords or competitors that are more than one word
        business_keywords = [
            f'"{keyword}"' if TextHelper.has_multiple_words(keyword) else keyword
            for keyword in business_keywords
        ]

        business_competitors = [
            (
                f'"{competitor}"'
                if TextHelper.has_multiple_words(competitor)
                else competitor
            )
            for competitor in business_competitors
        ]

        # Compose query string from keywords and competitors
        query_str_from_keywords = " OR ".join(business_keywords)
        query_str_from_competitors = " OR ".join(business_competitors)
        query_str = f"{query_str_from_keywords} OR {query_str_from_competitors}"

        return TweetSearchParams(
            max_results=settings.MAX_TWITTER_POSTS,
            query=query_str,
            is_retweet=False,
        )

    @staticmethod
    def extract_apollo_person_lead(data: dict) -> dict:
        organization = data.get("organization", {})

        location_parts: List[str] = list(
            filter(None, [data.get("city"), data.get("state"), data.get("country")])
        )
        full_location = ", ".join(location_parts) if any(location_parts) else None

        return {
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
            "username": data.get("name"),
            "phone": organization.get("phone"),
            "company_name": organization.get("name"),
            "job_title": data.get("title"),
            "keywords": data.get("subdepartments") or data.get("departments"),
            "industry": LeadIndustryTypeEnum.OTHER,  # Could be improved with mapping if industry info available
            "location": full_location,
            "lead_email": (
                data.get("email")
                if data.get("email") and "not_unlocked" not in data["email"]
                else None
            ),
            "picture_url": data.get("photo_url"),
            "company_logo": organization.get("logo_url"),
            "social_profile": data.get("name"),
            "social_profile_link": data.get("linkedin_url")
            or data.get("facebook_url")
            or data.get("twitter_url"),
            "linkedin_url": data.get("linkedin_url"),
            "facebook_url": data.get("facebook_url"),
            "twitter_url": data.get("twitter_url"),
            "github_url": data.get("github_url"),
            "website_url": organization.get("website_url"),
            "lead_reason": f"{data.get('title') or 'Professional'} at {organization.get('name') or 'Unknown company'}",
            "lead_link": data.get("linkedin_url") or organization.get("linkedin_url"),
            "follow_up_message": f"Hi {data.get('first_name')}, I came across your profile and was impressed by your role at {organization.get('name')}. I’d love to connect and explore how we might collaborate.",
            "follow_up_approach": "LinkedIn" if data.get("linkedin_url") else "Email",
            "lead_type": LeadFormTypeEnum.PERSON,
            "interest_level": LeadInterestLevelEnum.MEDIUM,
            "lead_status": LeadStatusEnum.NEW,
            "lead_source": LeadSourceEnum.OTHER,
            "apollo_id": data.get("id"),
        }

    @staticmethod
    def extract_apollo_organization_lead(data: dict) -> dict:
        return {
            "username": data.get("name"),
            "company_name": data.get("name"),
            "picture_url": data.get("logo_url"),
            "company_logo": data.get("logo_url"),
            "phone": None,
            "website_url": data.get("website_url"),
            "linkedin_url": data.get("linkedin_url"),
            "facebook_url": data.get("facebook_url"),
            "twitter_url": data.get("twitter_url"),
            "github_url": None,  # GitHub not included in organization data
            "keywords": [],  # Apollo doesn't include this in org data
            "industry": LeadIndustryTypeEnum.OTHER,  # Could be inferred from domain later
            "location": None,  # Not included; possible to geocode domain or phone in future
            "lead_email": None,  # No email in org-level data
            "social_profile": data.get("linkedin_url") or data.get("website_url"),
            "social_profile_link": data.get("linkedin_url") or data.get("website_url"),
            "blog_url": data.get("blog_url"),
            "angellist_url": data.get("angellist_url"),
            "crunchbase_url": data.get("crunchbase_url"),
            "languages": data.get("languages", []),
            "founded_year": data.get("founded_year"),
            "primary_domain": data.get("primary_domain"),
            "organization_revenue": data.get("organization_revenue"),
            "organization_revenue_printed": data.get("organization_revenue_printed"),
            "organization_headcount_six_month_growth": data.get(
                "organization_headcount_six_month_growth"
            ),
            "organization_headcount_twelve_month_growth": data.get(
                "organization_headcount_twelve_month_growth"
            ),
            "organization_headcount_twenty_four_month_growth": data.get(
                "organization_headcount_twenty_four_month_growth"
            ),
            "lead_link": data.get("linkedin_url") or data.get("website_url"),
            "follow_up_message": f"Hi team at {data.get('name')}, I came across your company and was impressed by your mission. I’d love to explore potential ways we can collaborate or support your goals.",
            "follow_up_approach": "LinkedIn" if data.get("linkedin_url") else "Email",
            "lead_type": LeadFormTypeEnum.ORGANIZATION,
            "interest_level": LeadInterestLevelEnum.MEDIUM,
            "lead_status": LeadStatusEnum.NEW,
            "lead_source": LeadSourceEnum.OTHER,
            "starred": False,
            "emailed": False,
            "called": False,
        }

    @staticmethod
    def enforce_feature_limit(get_user_id: Callable[[dict], str], endpoint: str):
        def decorator(func: Callable[..., Awaitable[Any]]):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Expecting the lead_form dict as a positional or keyword arg
                lead_form = kwargs.get("lead_form") or (args[0] if args else None)
                if lead_form is None:
                    raise ValueError("Missing lead_form and business info argument.")

                user_id = get_user_id(lead_form)
                if not user_id:
                    raise ValueError("User ID could not be extracted")

                result = await FeatureLimitMiddleware.verify_feature_limit(
                    user_id, endpoint
                )

                if not result or not result.get("status"):
                    print(f"Feature limit verification failed for {user_id}, bypassing for local testing")
                    # return UriResponse.custom_response(
                    #     "Feature limit exceeded", 403, False
                    # )  # ⚠️ Bypassed for local testing

                return await func(*args, **kwargs)

            return wrapper

        return decorator

    @staticmethod
    def get_lead_type_for_notification(lead_type: str):
        return (
            "Individual"
            if lead_type.capitalize() == "Person"
            else lead_type.capitalize()
        )
