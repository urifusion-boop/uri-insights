import asyncio
import httpx
from typing import Any, Dict, List, Optional, Union
from app.core.config import settings
from app.core.helpers.apollo_helper import ApolloHelper
from app.core.helpers.lead_helper import LeadHelper
from app.core.helpers.notification_helper import NotificationHelper
from app.database import get_db
from app.domain.enums.endpoints_enum import EndpointsEnum
from app.domain.enums.leadform_enum import LeadFormDisabledReasonEnum, LeadFormTypeEnum
from app.domain.enums.queue_message_type_enum import (
    UserNotificationQueueMessageTypeEnum,
)
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.models.chat_model import PlainText
from app.domain.requests.lead_requests import GetLeadsByFiltersRequest
from app.domain.responses.uri_response import UriResponse
from app.domain.schemas.lead_schema import Lead, LeadCreate, LeadUpdate
from app.domain.schemas.leadform_schema import (
    LeadFormUpdateBase,
    PersonLeadFormUpdate,
)
from app.domain.schemas.leadformsnapshot_schema import LeadFormSnapshot
from app.repository.ApolloRepository import ApolloRepository
from app.repository.CacheRepository import CacheRepository
from app.repository.LeadFormRepository import LeadFormRepository
from app.repository.LeadFormSnapshotRepository import LeadFormSnapshotRepository
from app.repository.LeadRepository import LeadRepository
from app.services.AIService import AIService
from app.services.NotificationService import NotificationService
from app.services.uri_microservices.UriTaskManagerService import UriTaskManagerService


class ApolloService:
    BASE_URL = "https://api.apollo.io/api/v1"
    HEADERS = headers = {
        "accept": "application/json",
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "x-api-key": settings.APOLLO_API_KEY,
    }

    @staticmethod
    async def handle_people_leads_gen(lead_form: dict, db: AsyncIOMotorDatabase):
        search_result = await ApolloService.search_people(lead_form=lead_form)
        if not search_result:
            raise ValueError("Apollo leads gen failed.")

        await ApolloService.handle_search_result(search_result, lead_form, db)

        return await ApolloService.handle_people_search_result(
            search_result, lead_form.get("user_id", ""), db
        )

    @staticmethod
    async def handle_organization_leads_gen(lead_form: dict, db: AsyncIOMotorDatabase):
        print(f"[ORG LEADS] Starting organization leads generation for form: {lead_form.get('lead_form_id')}")
        search_result = await ApolloService.search_organizations(lead_form=lead_form)

        print(f"[ORG LEADS] Search result received: {len(search_result.get('organizations', []))} organizations found")

        if not search_result:
            print("[ORG LEADS] ERROR: Apollo search returned empty result")
            raise ValueError("Apollo leads gen failed.")

        await ApolloService.handle_search_result(search_result, lead_form, db)

        result = await ApolloService.handle_organization_search_result(
            search_result, lead_form.get("user_id", ""), db
        )
        print(f"[ORG LEADS] Completed. Leads to create: {len(result) if result else 0}")
        return result

    @staticmethod
    @ApolloHelper.cache_result(
        custom_key_func=ApolloHelper.get_url_for_search_request, ttl_seconds=2419200
    )
    async def search_people(lead_form: dict) -> Dict[str, Any]:
        lead_form_type = lead_form.get("form_type")
        if lead_form_type != LeadFormTypeEnum.PERSON.value:
            raise ValueError(
                "Invalid lead form type for people search request: ", lead_form_type
            )
        search_result = {}
        url = ApolloHelper.get_url_for_search_request(lead_form)
        print(f"[PEOPLE SEARCH] Calling Apollo API: {url[:150]}...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=ApolloService.HEADERS,
            )
            print(f"[PEOPLE SEARCH] Apollo API response status: {response.status_code}")
            if response.status_code != 200:
                print(f"[PEOPLE SEARCH] Error response: {response.text}")
            search_result = ApolloService._process_response(response)
        print(f"[PEOPLE SEARCH] People in response: {len(search_result.get('people', []))}")
        return search_result

    @staticmethod
    @ApolloHelper.cache_result(
        custom_key_func=ApolloHelper.get_url_for_search_request, ttl_seconds=2419200
    )
    async def search_organizations(lead_form: dict) -> Dict[str, Any]:
        lead_form_type = lead_form.get("form_type")
        if lead_form_type != LeadFormTypeEnum.ORGANIZATION.value:
            raise ValueError(
                "Invalid lead form type for organization search request: ",
                lead_form_type,
            )
        search_result = {}
        url = ApolloHelper.get_url_for_search_request(lead_form)
        print(f"[ORG SEARCH] Calling Apollo API: {url[:100]}...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=ApolloService.HEADERS,
            )
            print(f"[ORG SEARCH] Apollo API response status: {response.status_code}")
            search_result = ApolloService._process_response(response)
        print(f"[ORG SEARCH] Organizations in response: {len(search_result.get('organizations', []))}")
        return search_result

    @staticmethod
    async def handle_enrichment_request(
        lead_ids: List[str],
        db: AsyncIOMotorDatabase,
        reveal_email: bool = False,
        reveal_phone: bool = False,
        webhook_url: Optional[str] = None,
    ):
        # Fetch leads concurrently
        get_leads_tasks = [LeadRepository.get_lead_by_id(db, lid) for lid in lead_ids]
        tasks_results = await asyncio.gather(*get_leads_tasks, return_exceptions=True)

        # Extract valid results
        leads = [
            result.get("responseData", {})
            for result in tasks_results
            if not isinstance(result, Exception) and result
        ]

        if not leads:
            return UriResponse.custom_response("Lead(s) not found for enrichment.", 404)

        # Group leads by type (so you can bulk-enrich per type)
        leads_by_type: dict[LeadFormTypeEnum, list] = {}
        for lead in leads:
            lead_type = lead.get("lead_type")
            if not lead_type:
                continue
            leads_by_type.setdefault(lead_type, []).append(lead)

        results = []

        for lead_type, grouped_leads in leads_by_type.items():
            match lead_type:
                case LeadFormTypeEnum.PERSON:
                    if len(grouped_leads) == 1:
                        grouped_leads = grouped_leads[0]
                    person_results = (
                        await ApolloService.handle_person_enrichment_request(
                            grouped_leads, db, reveal_email, reveal_phone, webhook_url
                        )
                    )
                    results.extend(
                        person_results
                        if isinstance(person_results, list)
                        else [person_results]
                    )

                case LeadFormTypeEnum.ORGANIZATION:
                    # Handle organization enrichment (email/phone reveal)
                    if len(grouped_leads) == 1:
                        grouped_leads = grouped_leads[0]
                    org_results = (
                        await ApolloService.handle_organization_enrichment_request(
                            grouped_leads, db, reveal_email, reveal_phone, webhook_url
                        )
                    )
                    results.extend(
                        org_results if isinstance(org_results, list) else [org_results]
                    )

                case _:
                    continue

        if not results:
            return UriResponse.custom_response(
                "Unsupported lead(s) provided for enrichment.", 400
            )

        # Return a single result if one lead was requested, otherwise return the list
        return results[0] if len(lead_ids) == 1 else results

    @staticmethod
    async def handle_person_enrichment_request(
        leads: Union[List[dict], dict],
        db: AsyncIOMotorDatabase,
        reveal_email: bool = False,
        reveal_phone: bool = False,
        webhook_url: Optional[str] = None,
    ):
        if not leads:
            return UriResponse.custom_response("Lead(s) not found for enrichment.", 404)

        if isinstance(leads, list):
            return await ApolloService.handle_multiple_person_leads_enrichment(
                leads,
                db,
                reveal_email,
                reveal_phone,
                webhook_url,
            )
        else:
            if reveal_email:
                return await ApolloService.handle_person_email_enrichment_request(
                    db=db, lead=leads
                )
            elif reveal_phone:
                return await ApolloService.handle_person_phone_enrichment_request(
                    db=db, lead=leads, webhook_url=webhook_url
                )

    @staticmethod
    async def handle_multiple_person_leads_enrichment(
        leads: Union[List[dict], dict],
        db: AsyncIOMotorDatabase,
        reveal_email: bool = False,
        reveal_phone: bool = False,
        webhook_url: Optional[str] = None,
    ):
        if reveal_email:
            email_enrichement_tasks = [
                ApolloService.handle_person_email_enrichment_request(lead=lead, db=db)
                for lead in leads
            ]
            task_responses = await asyncio.gather(*email_enrichement_tasks)
            results = [
                task for task in task_responses if not isinstance(task, Exception)
            ]
            return results
        elif reveal_phone:
            phone_enrichment_tasks = [
                ApolloService.handle_person_phone_enrichment_request(
                    db=db, lead=lead, webhook_url=webhook_url
                )
                for lead in leads
            ]
            task_responses = await asyncio.gather(*phone_enrichment_tasks)
            results = [
                task for task in task_responses if not isinstance(task, Exception)
            ]
            return results

    @staticmethod
    async def handle_person_email_enrichment_request(
        lead: dict,
        db: AsyncIOMotorDatabase,
    ):
        if not lead:
            return UriResponse.custom_response("Lead not found for enrichment.", 404)

        lead_id = lead.get("lead_id", "")
        cache_key = f"email-{ApolloHelper.generate_apollo_lead_cache_key(lead)}"

        # Try to get email from cache
        email = await CacheRepository.get_cache(db, cache_key=cache_key)

        # Try to enrich if not cached
        if not email:
            response = await ApolloService.enrich_person(lead, reveal_email=True)
            email = response.get("person", {}).get("email", "")
            email_status = response.get("person", {}).get("email_status", "")
            revealed = response.get("person", {}).get("revealed_for_current_team", False)

            print(f"[EMAIL ENRICHMENT] Lead: {lead.get('username', 'Unknown')}")
            print(f"[EMAIL ENRICHMENT] Apollo Response: {response}")
            print(f"[EMAIL ENRICHMENT] Extracted Email: {email}")
            print(f"[EMAIL ENRICHMENT] Email Status: {email_status}")
            print(f"[EMAIL ENRICHMENT] Revealed for team: {revealed}")

            # If no email but revealed, Apollo doesn't have it in database
            if not email and revealed:
                print(f"[EMAIL ENRICHMENT] ⚠️  Apollo has no email for this contact in their database")
                email = "UNAVAILABLE"

        # Normalize payload
        email = email or "UNAVAILABLE"
        print(f"[EMAIL ENRICHMENT] Final Email Value: {email}")
        payload = {"person": {"email": email}} if isinstance(email, str) else email

        # Process and persist
        return await ApolloService._process_person_email_enrichment_response(
            db, lead_id, payload
        )

    @staticmethod
    async def handle_person_phone_enrichment_request(
        lead: dict, db: AsyncIOMotorDatabase, webhook_url: Optional[str]
    ):
        lead_id = lead.get("lead_id", "")

        # Handle leads that don't have their corresponding apollo_ids
        if not (lead.get("apollo_id")):
            phone = None
            response = await ApolloService.enrich_person(lead)
            person = response.get("person", {})
            if person:
                await LeadRepository.update_lead(
                    db, lead_id, LeadUpdate(apollo_id=person.get("id"))
                )
                await ApolloRepository.create(db, person)
        else:  # Handle leads that already have an apollo id attached to them
            apollo_id = lead.get("apollo_id", "")
            phone = await ApolloRepository.get_phone_number_by_id(db, apollo_id)

            response = (await ApolloRepository.get_by_id(db, apollo_id)).get(
                "responseData", {}
            )
        # Trigger apollo webhook process if phone number isn't already in DB
        if not phone:
            print(f"[PHONE ENRICHMENT] Lead: {lead.get('username', 'Unknown')} - No phone in DB, calling Apollo API...")
            response = await ApolloService.enrich_person(
                lead, reveal_phone=True, webhook_url=webhook_url
            )
            print(f"[PHONE ENRICHMENT] Apollo Response: {response}")
            await LeadRepository.update_lead(
                db, lead_id, LeadUpdate(phone="PROCESSING")
            )
            print(f"[PHONE ENRICHMENT] Phone set to PROCESSING (awaiting webhook)")
        else:
            print(f"[PHONE ENRICHMENT] Lead: {lead.get('username', 'Unknown')} - Phone found in DB: {phone}")

        return await ApolloService._process_person_phone_enrichment_response(
            db, lead_id, phone, response
        )

    @staticmethod
    async def handle_organization_enrichment_request(
        leads: Union[List[dict], dict],
        db: AsyncIOMotorDatabase,
        reveal_email: bool = False,
        reveal_phone: bool = False,
        webhook_url: Optional[str] = None,
    ):
        """
        Handle organization enrichment similar to person enrichment.
        Calls Apollo API and saves the enriched data back to the database.
        """
        if not leads:
            return UriResponse.custom_response("Lead(s) not found for enrichment.", 404)

        if isinstance(leads, list):
            return await ApolloService.handle_multiple_organization_leads_enrichment(
                leads,
                db,
                reveal_email,
                reveal_phone,
                webhook_url,
            )
        else:
            # Single organization lead
            return await ApolloService.handle_single_organization_lead_enrichment(
                leads, db, reveal_email, reveal_phone, webhook_url
            )

    @staticmethod
    async def handle_multiple_organization_leads_enrichment(
        leads: List[dict],
        db: AsyncIOMotorDatabase,
        reveal_email: bool = False,
        reveal_phone: bool = False,
        webhook_url: Optional[str] = None,
    ):
        """Handle multiple organization leads enrichment concurrently"""
        enrichment_tasks = [
            ApolloService.handle_single_organization_lead_enrichment(
                lead=lead,
                db=db,
                reveal_email=reveal_email,
                reveal_phone=reveal_phone,
                webhook_url=webhook_url
            )
            for lead in leads
        ]
        task_responses = await asyncio.gather(*enrichment_tasks, return_exceptions=True)
        results = [
            task for task in task_responses if not isinstance(task, Exception)
        ]
        return results

    @staticmethod
    async def handle_single_organization_lead_enrichment(
        lead: dict,
        db: AsyncIOMotorDatabase,
        reveal_email: bool = False,
        reveal_phone: bool = False,
        webhook_url: Optional[str] = None,
    ):
        """
        Enrich a single organization lead.
        Similar to person enrichment but for organizations.
        """
        if not lead:
            return UriResponse.custom_response("Lead not found for enrichment.", 404)

        lead_id = lead.get("lead_id", "")
        website_url = lead.get("website_url", "")

        print(f"[ORG ENRICHMENT] Lead: {lead.get('company_name', 'Unknown')}")
        print(f"[ORG ENRICHMENT] Website: {website_url}")
        print(f"[ORG ENRICHMENT] reveal_email={reveal_email}, reveal_phone={reveal_phone}")

        if not website_url:
            print(f"[ORG ENRICHMENT] ⚠️ No website URL found for organization")
            return UriResponse.custom_response("No domain found for this lead.", 404)

        # Call Apollo API to enrich organization
        response = await ApolloService.handle_single_org_enrichement(lead)

        print(f"[ORG ENRICHMENT] Apollo Response: {response}")

        # Process and persist the enriched data
        return await ApolloService._process_organization_enrichment_response(
            db=db,
            lead_id=lead_id,
            response=response,
            reveal_phone=reveal_phone,
            reveal_email=reveal_email,
        )

    @staticmethod
    @ApolloHelper.cache_result(
        custom_key_func=ApolloHelper.get_url_for_enrich_person_request
    )
    async def enrich_person(
        lead: dict,
        reveal_email: bool = False,
        reveal_phone: bool = False,
        webhook_url: Optional[str] = None,
    ) -> dict:
        if reveal_phone and not webhook_url:
            webhook_url = f"{settings.URI_GATEWAY_BASE_API_URL}/uri-insights/webhooks/apollo-webhook"

        url = ApolloHelper.get_url_for_enrich_person_request(
            lead, reveal_email, reveal_phone, webhook_url
        )
        print(f"[APOLLO ENRICH] URL: {url}")
        print(f"[APOLLO ENRICH] Lead: {lead.get('username', 'Unknown')}, Apollo ID: {lead.get('apollo_id', 'None')}")
        print(f"[APOLLO ENRICH] reveal_email={reveal_email}, reveal_phone={reveal_phone}")
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=ApolloService.HEADERS)
            result = ApolloService._process_response(response)
            print(f"[APOLLO ENRICH] Response status: {response.status_code}")
            print(f"[APOLLO ENRICH] Response data: {result}")
            return result

    @staticmethod
    async def auto_enrich_people_after_search(people: List[dict]) -> List[dict]:
        """
        Auto-enrich people after search to get full profile data (photo, linkedin_url, name)
        WITHOUT revealing email/phone (those cost credits and are only revealed when user clicks).

        Args:
            people (List[dict]): List of people from Apollo search (with apollo_id).

        Returns:
            List[dict]: List of enriched people with full profile data.
        """
        if not people:
            return []

        print(f"[AUTO ENRICH] Starting auto-enrichment for {len(people)} people")

        # Build enrichment details from search results
        # We use apollo_id for fastest/most reliable matching
        details = []
        for person in people:
            apollo_id = person.get("id")
            if apollo_id:
                details.append({"id": apollo_id})
            else:
                # Fallback: use name and organization if no apollo_id
                first_name = person.get("first_name", "")
                organization = person.get("organization", {})
                org_name = organization.get("name", "")
                if first_name and org_name:
                    details.append({
                        "first_name": first_name,
                        "organization_name": org_name
                    })

        if not details:
            print("[AUTO ENRICH] No valid details for enrichment, returning original data")
            return people

        # Enrich in batches of 10 (Apollo bulk API limit)
        enriched_people = []
        batch_size = 10

        for i in range(0, len(details), batch_size):
            batch = details[i:i + batch_size]
            print(f"[AUTO ENRICH] Enriching batch {i//batch_size + 1} ({len(batch)} people)")

            try:
                result = await ApolloService.enrich_people_bulk(
                    details=batch,
                    reveal_personal_emails=False,  # Don't reveal email (costs credits)
                    reveal_phone_number=False,     # Don't reveal phone (costs credits)
                )

                # Extract enriched people from response
                matches = result.get("matches", [])
                print(f"[AUTO ENRICH] Response structure - matches count: {len(matches)}")
                if matches and len(matches) > 0:
                    print(f"[AUTO ENRICH] First match keys: {list(matches[0].keys())}")

                for idx, match in enumerate(matches):
                    print(f"[AUTO ENRICH] Match {idx} keys: {list(match.keys())}")
                    enriched_person = match.get("person", {})
                    if not enriched_person:
                        # Try alternative response structure
                        enriched_person = match

                    if enriched_person:
                        enriched_people.append(enriched_person)
                        print(f"[AUTO ENRICH] ✓ Enriched: {enriched_person.get('name', 'Unknown')} (has {len(enriched_person)} fields)")
                    else:
                        print(f"[AUTO ENRICH] ✗ Match {idx} has no person data")
            except Exception as e:
                print(f"[AUTO ENRICH] ✗ Batch enrichment failed: {str(e)}")
                # Fallback: use original data for this batch
                enriched_people.extend(people[i:i + batch_size])

        print(f"[AUTO ENRICH] Complete. Enriched {len(enriched_people)} people")
        return enriched_people if enriched_people else people

    @staticmethod
    async def enrich_people_bulk(
        details: List[dict],
        reveal_personal_emails: bool = False,
        reveal_phone_number: bool = False,
        webhook_url: Optional[str] = None,
    ) -> dict:
        """
        Enrich a list of up to 10 people using Apollo's bulk match API.

        Args:
            details (List[dict]): List of person info dictionaries (e.g., name, email).
            reveal_personal_emails (bool): Whether to request personal emails. Defaults to False.
            reveal_phone_number (bool): Whether to request phone numbers. Defaults to False.
            webhook_url (str): Required if reveal_phone_number is True.

        Returns:
            dict: API response from Apollo.
        """
        url = f"{ApolloService.BASE_URL}/people/bulk_match"
        params = {
            "reveal_personal_emails": str(reveal_personal_emails).lower(),
            "reveal_phone_number": str(reveal_phone_number).lower(),
        }
        if reveal_phone_number and webhook_url:
            params["webhook_url"] = webhook_url

        payload = {"details": details}
        url = ApolloHelper.format_url(url, params)
        print(f"[ENRICH BULK] URL: {url}")
        print(f"[ENRICH BULK] Payload: {len(details)} people")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, json=payload, headers=ApolloService.HEADERS
            )
            result = ApolloService._process_response(response)
            print(f"[ENRICH BULK] Response: {response.status_code}, Matches: {len(result.get('matches', []))}")
            return result

    @staticmethod
    @ApolloHelper.cache_result()
    async def enrich_organization(
        lead_data: Union[List[dict], dict]
    ) -> Union[List[dict], dict]:
        if isinstance(lead_data, dict):
            return await ApolloService.handle_single_org_enrichement(lead_data)
        else:
            return await ApolloService.handle_multiple_org_enrichment(lead_data)

    @staticmethod
    async def handle_single_org_enrichement(lead: dict) -> dict:
        url = f"{ApolloService.BASE_URL}/organizations/enrich"
        domain = lead.get("website_url", "")
        if not domain:
            return UriResponse.custom_response("No domain found for this lead.", 404)

        params = {"domain": domain}

        url = ApolloHelper.format_url(url, params)

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=ApolloService.HEADERS)
            return ApolloService._process_response(response)

    @staticmethod
    async def handle_multiple_org_enrichment(leads: List[dict]) -> List[dict]:
        org_enrichment_tasks = [
            ApolloService.handle_single_org_enrichement(lead) for lead in leads
        ]
        tasks_results = await asyncio.gather(*org_enrichment_tasks)
        results = [
            result for result in tasks_results if not isinstance(result, Exception)
        ]
        return results

    @staticmethod
    async def find_decision_makers(
        company_name: str,
        job_titles: List[str],
        max_results: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find decision-makers at a company for job signal opportunities
        PRD Section 8: Decision-Maker Connection Feature

        Args:
            company_name: Company name from job posting
            job_titles: List of decision-maker titles to search for (e.g., ["CTO", "VP Engineering"])
            max_results: Maximum number of contacts to return (default: 3)

        Returns:
            List of decision-makers with contact details
        """
        url = f"{ApolloService.BASE_URL}/mixed_people/search"

        # Build Apollo search payload
        # Search for people at this company with these job titles
        payload = {
            "q_organization_name": company_name,
            "person_titles": job_titles,
            "page": 1,
            "per_page": max_results,
            "organization_num_employees_ranges": ["1,10", "11,50", "51,200", "201,500", "501,1000", "1001,5000", "5001,10000", "10001+"],
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=ApolloService.HEADERS
                )

                if response.status_code != 200:
                    error_message = f"Apollo API error: {response.status_code}"
                    print(f"❌ {error_message} - {response.text}")

                    # Raise exception for API errors so endpoint can handle gracefully
                    if response.status_code == 403:
                        raise Exception("Apollo API service temporarily unavailable")
                    elif response.status_code == 429:
                        raise Exception("Rate limit exceeded, please try again later")
                    else:
                        raise Exception("Decision-maker lookup service unavailable")

                result = response.json()
                people = result.get("people", [])

                # Format results to match PRD Section 8.4 requirements
                decision_makers = []
                for person in people[:max_results]:
                    # Extract contact details
                    name = person.get("name") or f"{person.get('first_name', '')} {person.get('last_name', '')}".strip()
                    title = person.get("title") or person.get("headline", "")
                    email = person.get("email")
                    phone = person.get("phone_numbers", [{}])[0].get("raw_number") if person.get("phone_numbers") else None
                    linkedin_url = person.get("linkedin_url")
                    organization_name = person.get("organization", {}).get("name") or company_name

                    # Only include if we have at least name and email
                    if name and email:
                        decision_makers.append({
                            "name": name,
                            "title": title,
                            "email": email,
                            "phone": phone,
                            "linkedin_url": linkedin_url,
                            "organization_name": organization_name,
                            "id": person.get("id")
                        })

                print(f"✅ Found {len(decision_makers)} decision-makers at {company_name}")
                return decision_makers

        except Exception as e:
            print(f"❌ Error finding decision-makers: {str(e)}")
            import traceback
            traceback.print_exc()
            # Re-raise the exception so endpoint can handle it properly
            raise

    @staticmethod
    async def enrich_organizations_bulk(domains: List[str]) -> dict:
        """
        Enrich a list of up to 10 organizations using Apollo's bulk enrich API.

        Args:
            domains (List[str]): A list of organization domains (e.g., ["microsoft.com", "apollo.io"]).

        Returns:
            dict: The response from Apollo's API.
        """
        url = f"{ApolloService.BASE_URL}/organizations/bulk_enrich"
        payload = {"domains": domains}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, json=payload, headers=ApolloService.HEADERS
            )
            return ApolloService._process_response(response)

    @staticmethod
    async def get_api_usage_stats() -> dict:
        """
        Retrieve usage statistics for the Apollo API, including information about
        credit consumption and request limits.

        Returns:
            dict: A dictionary containing the API usage stats.
        """
        url = f"{ApolloService.BASE_URL}/usage_stats/api_usage_stats"

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=ApolloService.HEADERS)
            return ApolloService._process_response(response)

    @staticmethod
    def _process_response(response: httpx.Response) -> dict:
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(
                {"status_code": response.status_code, "error": response.text}
            )

    @staticmethod
    async def _process_person_email_enrichment_response(
        db: AsyncIOMotorDatabase, lead_id: str, response: dict
    ):
        email = response.get("person", {}).get("email", "")
        print(f"[EMAIL SAVE] Lead ID: {lead_id}, Email being saved: {email}")
        if email:
            updated_lead = (
                await LeadRepository.update_lead(
                    db, lead_id, LeadUpdate(lead_email=email)
                )
            ).get("responseData", {})
            print(f"[EMAIL SAVE] Updated lead with email: {email}")
            if email != "UNAVAILABLE":
                await UriTaskManagerService.update_user_feature_limit_specific_limit(
                    updated_lead.get("assigned_to", ""),
                    EndpointsEnum.LEAD_ENRICHMENT_EMAIL.value,
                    0,
                )
        return response

    @staticmethod
    async def _process_person_phone_enrichment_response(
        db: AsyncIOMotorDatabase, lead_id: str, phone: Optional[str], response: dict
    ):
        if phone:
            updated_lead = (
                await LeadRepository.update_lead(db, lead_id, LeadUpdate(phone=phone))
            ).get("responseData", {})
            await UriTaskManagerService.update_user_feature_limit_specific_limit(
                updated_lead.get("assigned_to", ""),
                EndpointsEnum.LEAD_ENRICHMENT_PHONE.value,
                0,
            )
        return response

    @staticmethod
    async def _process_organization_enrichment_response(
        db: AsyncIOMotorDatabase,
        lead_id: str,
        response: dict,
        reveal_phone: bool = False,
        reveal_email: bool = False,
    ):
        """
        Process Apollo organization enrichment response and save to database.
        Similar to _process_person_email_enrichment_response but for organizations.
        """
        organization = response.get("organization", {})
        phone = organization.get("phone", "")

        # Apollo organization API returns contact info differently than person API
        # Organizations may have: primary_phone, phone, or sanitized_phone
        if not phone:
            phone = organization.get("primary_phone", "")
        if not phone:
            phone = organization.get("sanitized_phone", "")

        # For organizations, email is typically in the format info@domain.com, contact@domain.com
        # Apollo may provide this in the organization object or we construct it from domain
        email = organization.get("email", "")
        if not email:
            # Try to get from organization contact fields
            email = organization.get("organization_email", "")

        # If still no email, try to extract from primary domain
        if not email and reveal_email:
            primary_domain = organization.get("primary_domain", "")
            website_url = organization.get("website_url", "")

            print(f"[ORG EMAIL] No direct email from Apollo. Domain: {primary_domain}, Website: {website_url}")

            if primary_domain:
                # Common organizational email patterns
                email = f"info@{primary_domain}"
                print(f"[ORG EMAIL] Generated generic email: {email}")
            elif website_url:
                # Extract domain from website URL as fallback
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(website_url)
                    domain = parsed.netloc.replace('www.', '')
                    if domain:
                        email = f"info@{domain}"
                        print(f"[ORG EMAIL] Generated email from URL: {email}")
                except:
                    pass

        print(f"[ORG ENRICHMENT] Processing response for lead_id: {lead_id}")
        print(f"[ORG ENRICHMENT] Phone: {phone or 'None'}")
        print(f"[ORG ENRICHMENT] Email: {email or 'None'}")
        print(f"[ORG ENRICHMENT] reveal_phone={reveal_phone}, reveal_email={reveal_email}")

        # Build update data
        update_data = LeadUpdate()

        if reveal_phone:
            if phone:
                update_data.phone = phone
                print(f"[ORG ENRICHMENT] Will update phone: {phone}")
            else:
                update_data.phone = "UNAVAILABLE"
                print(f"[ORG ENRICHMENT] No phone found, setting to UNAVAILABLE")

        if reveal_email:
            if email:
                update_data.lead_email = email
                print(f"[ORG ENRICHMENT] Will update email: {email}")
            else:
                update_data.lead_email = "UNAVAILABLE"
                print(f"[ORG ENRICHMENT] No email found, setting to UNAVAILABLE")

        # Save to database if we have any data to update
        if update_data.phone or update_data.lead_email:
            updated_lead = (
                await LeadRepository.update_lead(db, lead_id, update_data)
            ).get("responseData", {})

            print(f"[ORG ENRICHMENT] ✅ Updated lead in database")

            # Update feature limits
            if reveal_phone and phone and phone != "UNAVAILABLE":
                await UriTaskManagerService.update_user_feature_limit_specific_limit(
                    updated_lead.get("assigned_to", ""),
                    EndpointsEnum.LEAD_ENRICHMENT_PHONE.value,
                    0,
                )
                print(f"[ORG ENRICHMENT] ✅ Updated phone feature limit")

            if reveal_email and email and email != "UNAVAILABLE":
                await UriTaskManagerService.update_user_feature_limit_specific_limit(
                    updated_lead.get("assigned_to", ""),
                    EndpointsEnum.LEAD_ENRICHMENT_EMAIL.value,
                    0,
                )
                print(f"[ORG ENRICHMENT] ✅ Updated email feature limit")
        else:
            print(f"[ORG ENRICHMENT] ⚠️ No data to update")

        return response

    @staticmethod
    async def handle_search_result(
        search_result: dict, lead_form: Optional[dict], db: AsyncIOMotorDatabase
    ):
        if not lead_form:
            return

        lead_form_type = lead_form.get("form_type", "")
        user_id = lead_form.get("user_id", "")
        lead_form_id = lead_form.get("lead_form_id", "")
        page = lead_form.get("page", 0)

        # Check ACTUAL data array, not just pagination metadata
        # Pagination metadata can be stale/cached/incorrect, but the actual data is the source of truth
        actual_data = search_result.get("people", []) if lead_form_type == "PERSON" else search_result.get("organizations", [])

        print(f"[SEARCH RESULT] Form type: {lead_form_type}, Actual data count: {len(actual_data)}")

        if len(actual_data) == 0:
            print("Apollo search returned no results (actual data array is empty).")
            await ApolloService.handle_empty_search_result(user_id, lead_form_type=lead_form_type)
            return

        # Handle pagination advancement
        pagination_data = search_result.get("pagination", {})
        total_pages = pagination_data.get("total_pages", 0)

        print(f"[SEARCH RESULT] Page {page + 1}/{total_pages}, Data count: {len(actual_data)}")

        if (page + 1) >= total_pages:
            print("Pagination limit reached for Apollo search")
            await ApolloService.handle_pagination_end_result(db, lead_form=lead_form)
        else:
            await LeadFormRepository.update(
                db,
                PersonLeadFormUpdate(page=page + 1),
                lead_form_id,
            )

    @staticmethod
    async def handle_empty_search_result(user_id: str, lead_form_type: str):
        data_to_send = await NotificationHelper.build_base_lead_notification_payload(
            user_id, lead_form_type
        )
        await NotificationService.send_lead_notification(
            data_to_send,
            UserNotificationQueueMessageTypeEnum.EMPTY_APOLLO_SEARCH_RESULT,
        )

    @staticmethod
    async def handle_pagination_end_result(db: AsyncIOMotorDatabase, lead_form: dict):
        lead_form_id = lead_form.get("lead_form_id", "")
        user_id = lead_form.get("user_id", "")
        lead_form_type = lead_form.get("form_type", "")
        form_title = lead_form.get("form_title", "")
        data_to_send = (
            await NotificationHelper.build_extended_lead_notification_payload(
                user_id, lead_form_type, {"searchTerm": form_title}
            )
        )

        # Disable lead form
        await LeadFormRepository.update(
            db=db,
            lead_form_id=lead_form_id,
            data=LeadFormUpdateBase(
                disabled=True,
                disabled_reason=LeadFormDisabledReasonEnum.MAX_PAGE_REACHED,
                page=1,
            ),
        )

        await NotificationService.send_lead_notification(
            data_to_send, UserNotificationQueueMessageTypeEnum.APOLLO_PAGINATION_END
        )

    @staticmethod
    async def handle_people_search_result(
        search_result: dict, user_id: str, db: AsyncIOMotorDatabase
    ) -> Optional[List[LeadCreate]]:
        people = search_result.get("people", [])

        print(f"[PEOPLE RESULT] Processing {len(people)} people from search result")
        if people:
            # Log first person's keys to understand response structure
            print(f"[PEOPLE RESULT] First person keys: {list(people[0].keys())[:10]}")

        if not people or not user_id:
            return None

        # Auto-enrich people to get full profile data (photo, linkedin_url, name)
        # WITHOUT revealing email/phone (those are only revealed when user clicks)
        print(f"[PEOPLE RESULT] Auto-enriching {len(people)} people to get full profile data...")
        enriched_people = await ApolloService.auto_enrich_people_after_search(people)
        print(f"[PEOPLE RESULT] Enrichment complete. Using enriched data for lead creation.")

        latest_lead_form_snapshot: LeadFormSnapshot = (
            await ApolloService.get_latest_lead_form_snapshot(
                db, user_id=user_id, form_type=LeadFormTypeEnum.PERSON
            )
        ).get("responseData")

        tasks = []

        for enriched_person in enriched_people:
            lead_to_create_dict = LeadHelper.extract_apollo_person_lead(enriched_person)
            lead_to_create_dict["assigned_to"] = user_id
            lead_to_create_dict["lead_form_snapshot_id"] = (
                latest_lead_form_snapshot.lead_form_snapshot_id
                if latest_lead_form_snapshot
                else None
            )
            lead_to_create_dict["form_title"] = (
                latest_lead_form_snapshot.form_title
                if latest_lead_form_snapshot
                else None
            )

            # Safely remove employment_history if it exists (may not be present in new API)
            enriched_person.pop("employment_history", None)
            tasks.append(
                ApolloService.perform_ai_lead_enrichment(lead_to_create_dict, enriched_person)
            )

        leads_to_create = await asyncio.gather(*tasks)
        await ApolloRepository.create_multiple(db, enriched_people)

        return leads_to_create

    @staticmethod
    async def handle_organization_search_result(
        search_result: dict, user_id: str, db: AsyncIOMotorDatabase
    ) -> Optional[List[LeadCreate]]:
        organizations = search_result.get("organizations", [])
        if not organizations or not user_id:
            return None

        latest_lead_form_snapshot: LeadFormSnapshot = (
            await ApolloService.get_latest_lead_form_snapshot(
                db, user_id=user_id, form_type=LeadFormTypeEnum.ORGANIZATION
            )
        ).get("responseData")

        tasks = []

        for organization in organizations:
            lead_to_create_dict = LeadHelper.extract_apollo_organization_lead(
                organization
            )
            lead_to_create_dict["assigned_to"] = user_id
            lead_to_create_dict["lead_form_snapshot_id"] = (
                latest_lead_form_snapshot.lead_form_snapshot_id
                if latest_lead_form_snapshot
                else None
            )
            lead_to_create_dict["form_title"] = (
                latest_lead_form_snapshot.form_title
                if latest_lead_form_snapshot
                else None
            )

            tasks.append(
                ApolloService.perform_ai_lead_enrichment(
                    lead_to_create_dict, organization
                )
            )

        leads_to_create = await asyncio.gather(*tasks)
        await ApolloRepository.create_multiple(db, organizations)

        return leads_to_create

    @staticmethod
    async def get_latest_lead_form_snapshot(
        db: AsyncIOMotorDatabase, user_id: str, form_type: LeadFormTypeEnum
    ):
        filters = {
            "user_id": user_id,
            "form_type": form_type.value,
        }

        return await LeadFormSnapshotRepository.get_latest_snapshot(db, filters)

    @staticmethod
    async def perform_ai_lead_enrichment(lead_dict: dict, person_or_org: dict):
        prompt = f"""
            You are provided with partially completed lead data that needs contextual enrichment.

            Please focus on filling in the following specific fields, using insight from the lead's background. Here's what each field represents:

            1. **follow_up_message** – A personalized, friendly, and professional message that the user can send to the lead to initiate contact or express interest in collaboration.
            2. **interest_level** – An assessment of how relevant or promising this lead appears for the business, using levels such as LOW, MEDIUM, or HIGH.
            3. **industry** – The primary industry the lead is associated with, inferred from the company or individual profile.
            4. **lead_reason** - A description of what makes the lead relevant to the client.
            5. **tags** - Identifiable keywords that communicate the qualifications or industry of the lead.

            Below is the current lead data:

            {lead_dict}

            And here is the original data used to identify this lead (could be a person or organization profile):

            {person_or_org}

            Using all this information, please return the filled values for the four target fields with contextual understanding.
        """

        ai_model = AIService.build_ai_model([AIService.construct_user_prompt(prompt)])
        ai_enriched_lead: LeadCreate = AIService.extract_ai_result(
            await AIService.structured_chat_completion(ai_model, LeadCreate)
        )
        await ApolloHelper.cache_lead_email_and_phone(
            ai_enriched_lead.model_dump(exclude_none=True)
        )
        ai_enriched_lead.lead_email = None
        ai_enriched_lead.phone = None
        return ai_enriched_lead

    @staticmethod
    async def get_org_email_from_website(website_url: str):
        prompt = f"""
                You are a smart extraction AI. Your task is to visit the official website of a given company and extract the company's official contact email address.

                Instructions:

                1. Start from the company’s homepage URL {website_url}.
                2. Search through relevant pages (e.g., Contact Us, About, Footer, or Privacy Policy) for any valid email address belonging to the company.
                3. Ignore personal, third-party, or suspicious-looking emails (like Gmail, Yahoo, or unrelated domains).
                4. Return only the official email address as a string.
                5. If no valid email address is found, return None.
            """

        ai_model = AIService.build_ai_model([AIService.construct_user_prompt(prompt)])
        company_email: PlainText = AIService.extract_ai_result(
            await AIService.structured_chat_completion(ai_model)
        )
        return company_email.text

    @staticmethod
    async def process_webhook_event(db: AsyncIOMotorDatabase, data: dict):
        apollo_id = data.get("id", "")
        if not apollo_id:
            raise ValueError("Apollo ID is required")

        leads = await ApolloService._get_processing_leads(db, apollo_id)
        if not leads:
            raise ValueError("Leads not found for phone number enrichment")

        phone = await ApolloService._extract_phone_number(data)

        if phone:
            print(
                "Phone number found, updating leads, apollo records and feature limits."
            )
            await ApolloService._update_apollo_record(db, apollo_id, phone)
            await ApolloService._update_leads_with_phone(db, leads, phone)
        else:
            print("Phone number not found, updating leads with 'UNAVAILABLE'.")
            await ApolloService._mark_leads_unavailable(db, leads)
            await ApolloService._update_apollo_record(db, apollo_id, "UNAVAILABLE")

    @staticmethod
    async def _get_processing_leads(db: AsyncIOMotorDatabase, apollo_id: str) -> list:
        response = await LeadRepository.get_leads_by_filters(
            db,
            filters=GetLeadsByFiltersRequest(apollo_id=apollo_id, phone="PROCESSING"),
        )
        return response.get("responseData", {}).get("data", [])

    @staticmethod
    async def _extract_phone_number(data: dict) -> Optional[str]:
        status = data.get("status")

        if status != "success":
            return None
        phone_data = data.get("phone_numbers", [])
        return phone_data[0].get("raw_number", "") if phone_data else ""

    @staticmethod
    async def _update_apollo_record(
        db: AsyncIOMotorDatabase, apollo_id: str, phone: str
    ):
        apollo_data = await ApolloRepository.get_by_id(db, apollo_id)
        if not apollo_data.get("status", False):
            print("Apollo data not found for phone number enrichment.")
            return

        update_data = apollo_data.get("responseData", {})
        update_data["phone"] = phone
        await ApolloRepository.update(db, apollo_id, update_data)

    @staticmethod
    async def _update_leads_with_phone(
        db: AsyncIOMotorDatabase, leads: list, phone: str
    ):
        if len(leads) == 1:
            lead = leads[0]
            lead_id = lead.get("lead_id")
            assigned_to = lead.get("assigned_to", "")

            await LeadRepository.update_lead(
                db, lead_id, updates=LeadUpdate(phone=phone)
            )

            await UriTaskManagerService.update_user_feature_limit_specific_limit(
                assigned_to,
                EndpointsEnum.LEAD_ENRICHMENT_PHONE.value,
                0,
            )
        else:
            # Update all leads concurrently
            update_tasks = [
                LeadRepository.update_lead(
                    db, lead.get("lead_id"), updates=LeadUpdate(phone=phone)
                )
                for lead in leads
            ]

            # Update all user limits concurrently
            feature_tasks = [
                UriTaskManagerService.update_user_feature_limit_specific_limit(
                    lead.get("assigned_to"),
                    EndpointsEnum.LEAD_ENRICHMENT_PHONE.value,
                    0,
                )
                for lead in leads
            ]

            await asyncio.gather(*update_tasks)
            await asyncio.gather(*feature_tasks)

    @staticmethod
    async def _mark_leads_unavailable(db: AsyncIOMotorDatabase, leads: list):
        if len(leads) == 1:
            await LeadRepository.update_lead(
                db, leads[0].get("lead_id"), updates=LeadUpdate(phone="UNAVAILABLE")
            )
        else:
            update_tasks = [
                LeadRepository.update_lead(
                    db, lead.get("lead_id"), updates=LeadUpdate(phone="UNAVAILABLE")
                )
                for lead in leads
            ]
            await asyncio.gather(*update_tasks)
