import asyncio
import functools
import hashlib
from typing import Union, Callable, Optional
from app.core.helpers.dict_helper import DictHelper
from app.database import get_db
from app.domain.enums.leadform_enum import LeadFormTypeEnum
from app.domain.requests.apollo_requests import (
    EnrichPersonRequest,
    OrganizationSearchRequest,
    PersonSearchRequest,
)
import functools
import json
from datetime import timedelta
from app.domain.responses.uri_response import UriResponse
from app.repository.CacheRepository import CacheRepository
from urllib.parse import quote, urlparse


class ApolloHelper:
    BASE_URL = "https://api.apollo.io/api/v1"

    @staticmethod
    def get_search_params(
        lead_form: dict,
    ) -> Union[PersonSearchRequest, OrganizationSearchRequest]:
        form_type = lead_form.get("form_type")

        if form_type == LeadFormTypeEnum.PERSON.value:
            return ApolloHelper.get_person_search_params(lead_form)
        return ApolloHelper.get_organization_search_params(lead_form)

    @staticmethod
    def get_person_search_params(lead_form: dict):
        unwanted_keys = [
            "lead_form_id",
            "form_type",
            "form_title",
            "user_id",
            "id",
            "created_date",
            "last_updated",
            "organization_not_locations",
            "revenue_range_min",
            "revenue_range_max",
            "technology_uids",
            "q_organization_keyword_tags",
            "q_organization_name",
            "disabled",
            "disabled_reason",
            "ai_response_guide",
            "next_generation_date",
            "settings",
            "business_name",
            "business_summary",
            "business_website",
            "keywords",
            "q_keywords",
            "competitors",
            "source_platforms",
            "auto_generate",
            "add_to_history",
            "apollo_id",
            "organization_num_employees_ranges",
            "buying_signals",
            "excluded_keywords",
            "location",
            "post_age_filter",
            "intent_type",
            "category_context",
            "implied_keywords",
            "scoring_thresholds",
            "enable_realtime",
            "monitoring_platforms",
            "platform_configs",
        ]

        lead_form.copy()
        person_search_request_dict = DictHelper.remove_keys(
            lead_form.copy(), unwanted_keys
        )
        return PersonSearchRequest(**person_search_request_dict)

    @staticmethod
    def get_organization_search_params(lead_form: dict):
        lead_form["currently_using_any_of_technology_uids"] = lead_form[
            "technology_uids"
        ]
        unwanted_keys = [
            "lead_form_id",
            "form_type",
            "form_title",
            "user_id",
            "include_similar_titles",
            "id",
            "created_date",
            "last_updated",
            "person_titles",
            "person_locations",
            "person_seniorities",
            "q_organization_domains_list",
            "contact_email_status",
            "q_keywords",
            "technology_uids",
            "disabled",
            "disabled_reason",
            "ai_response_guide",
            "next_generation_date",
            "settings",
            "business_name",
            "business_summary",
            "business_website",
            "keywords",
            "competitors",
            "source_platforms",
            "auto_generate",
            "add_to_history",
            "apollo_id",
            "buying_signals",
            "excluded_keywords",
            "location",
            "intent_type",
            "category_context",
            "implied_keywords",
            "scoring_thresholds",
            "enable_realtime",
            "monitoring_platforms",
            "platform_configs",
            "post_age_filter",
        ]
        organization_search_request_dict = DictHelper.remove_keys(
            lead_form.copy(), unwanted_keys
        )
        return OrganizationSearchRequest(**organization_search_request_dict)

    @staticmethod
    def format_url(base_url: str, params: dict) -> str:
        query_parts = []

        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, list):
                for v in value:
                    if v is not None:
                        query_parts.append(f"{quote(str(key))}[]={quote(str(v))}")
            elif isinstance(value, bool):
                query_parts.append(f"{quote(str(key))}={quote(str(value).lower())}")
            else:
                query_parts.append(f"{quote(str(key))}={quote(str(value))}")

        query_string = "&".join(query_parts)
        return f"{base_url}?{query_string}" if query_string else base_url

    @staticmethod
    def get_url_for_search_request(lead_form: dict):
        form_type = lead_form.get("form_type")
        if form_type == LeadFormTypeEnum.PERSON.value:
            base_url = f"{ApolloHelper.BASE_URL}/mixed_people/search"
        elif form_type == LeadFormTypeEnum.ORGANIZATION.value:
            base_url = f"{ApolloHelper.BASE_URL}/mixed_companies/search"
        else:
            raise ValueError(f"Unsupported form type: {form_type}")
        params = ApolloHelper.get_search_params(lead_form)
        return ApolloHelper.format_url(base_url, params.dict(exclude_none=True))

    @staticmethod
    def get_enrich_person_params_from_lead(lead: dict):
        # Extract domain from website_url
        website_url = lead.get("website_url") or ""
        parsed_domain = (
            urlparse(website_url).netloc.replace("www.", "") if website_url else ""
        )

        return {
            "name": f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
            "organization_name": lead.get("company_name", ""),
            "domain": parsed_domain,
            "linkedin_url": lead.get("linkedin_url", ""),
        }

    @staticmethod
    def get_url_for_enrich_person_request(
        lead: dict,
        reveal_email: bool = False,
        reveal_phone: bool = False,
        webhook_url: Optional[str] = None,
    ) -> str:
        url = f"https://api.apollo.io/api/v1/people/match"

        if not lead:
            return UriResponse.custom_response("Lead not found for enrichment", 404)
        if reveal_phone and not webhook_url:
            return UriResponse.custom_response(
                "A webhook url must be provided if reveal_phone is set to true.", 400
            )

        # Helper function to extract Enrich Person params from lead.
        params_dict = ApolloHelper.get_enrich_person_params_from_lead(lead)

        params = EnrichPersonRequest(
            **params_dict,
            reveal_personal_emails=reveal_email,
            reveal_phone_number=reveal_phone,
            webhook_url=webhook_url,
        )
        url = ApolloHelper.format_url(url, params.dict(exclude_none=True))
        return url

    @classmethod
    def cache_result(
        cls,
        ttl_seconds: Optional[int] = None,
        custom_key_func: Optional[Callable[..., str]] = None,
    ):
        """
        Decorator to cache the result of a class/static method that makes a third-party call.

        Args:
            ttl_seconds (Optional[int]): TTL in seconds. If None, cache result indefinitely.
            custom_key_func (Optional[Callable]): Optional function to customize cache key based on args/kwargs.
        """

        def decorator(fn):
            @functools.wraps(fn)
            async def wrapper(*args, **kwargs):
                if kwargs.get("reveal_phone", False):
                    return await fn(*args, **kwargs)
                key_base = {
                    "func": fn.__name__,
                    "args": args,
                    "kwargs": kwargs,
                }

                custom_key = ""
                if custom_key_func:
                    result = custom_key_func(*args, **kwargs)
                    custom_key = await result if asyncio.iscoroutine(result) else result
                    if isinstance(custom_key, dict):
                        custom_key = json.dumps(custom_key, sort_keys=True)

                raw_key = custom_key or json.dumps(str(key_base), sort_keys=True)
                cache_key = hashlib.sha256(raw_key.encode()).hexdigest()
                db = get_db()
                if db is None:
                    raise ValueError("Database instance not found.")

                cached = await CacheRepository.get_cache(db, cache_key)
                if cached is not None:
                    print("Returning cached result.")
                    return cached

                result = await fn(*args, **kwargs)

                # Only add TTL if provided
                if ttl_seconds is not None:
                    ttl = timedelta(seconds=ttl_seconds)
                else:
                    ttl = None
                await CacheRepository.set_cache(db, cache_key, result, ttl)
                return result

            return wrapper

        return decorator

    @staticmethod
    async def cache_lead_email_and_phone(lead: dict):
        email = lead.get("email", "")
        phone = lead.get("phone", "")
        print("Email for caching: ", email)
        print("Phone for caching: ", phone)
        cache_key: str = ""
        if email:
            cache_key = f"email-{ApolloHelper.generate_apollo_lead_cache_key(lead)}"
            await CacheRepository.set_cache(
                get_db(), cache_key, email, timedelta(seconds=2419200)
            )

        if phone:
            cache_key = f"phone-{ApolloHelper.generate_apollo_lead_cache_key(lead)}"
            await CacheRepository.set_cache(
                get_db(), cache_key, phone, timedelta(seconds=2419200)
            )

    @staticmethod
    def generate_apollo_lead_cache_key(lead: dict):
        lead_id = lead.get("lead_id")
        user_id = lead.get("assigned_to")
        lead_type = lead.get("lead_type")

        raw_key: str = f"{lead_id}-{user_id}-{lead_type}"
        return hashlib.sha256(raw_key.encode()).hexdigest()
