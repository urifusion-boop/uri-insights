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
from app.domain.schemas.lead_schema import Lead, LeadUpdate
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
        search_result = await ApolloService.search_organizations(lead_form=lead_form)

        if not search_result:
            raise ValueError("Apollo leads gen failed.")

        await ApolloService.handle_search_result(search_result, lead_form, db)

        return await ApolloService.handle_organization_search_result(
            search_result, lead_form.get("user_id", ""), db
        )

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
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=ApolloService.HEADERS,
            )
            search_result = ApolloService._process_response(response)
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
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=ApolloService.HEADERS,
            )
            search_result = ApolloService._process_response(response)
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
                    # Placeholder for org enrichment logic
                    org_results = await ApolloService.enrich_organization(grouped_leads)
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

        # Normalize payload
        email = email or "UNAVAILABLE"
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
            response = await ApolloService.enrich_person(
                lead, reveal_phone=True, webhook_url=webhook_url
            )
            await LeadRepository.update_lead(
                db, lead_id, LeadUpdate(phone="PROCESSING")
            )

        return await ApolloService._process_person_phone_enrichment_response(
            db, lead_id, phone, response
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
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=ApolloService.HEADERS)
            return ApolloService._process_response(response)

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
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, json=payload, headers=ApolloService.HEADERS
            )
            return ApolloService._process_response(response)

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
        if email:
            updated_lead = (
                await LeadRepository.update_lead(
                    db, lead_id, LeadUpdate(lead_email=email)
                )
            ).get("responseData", {})
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
        phone = response.get("organization", {}).get("phone", "")
        website_url = response.get("organization", {}).get("website_url", "")
        extracted_email = await ApolloService.get_org_email_from_website(website_url)
        update_data = LeadUpdate()
        if reveal_phone and phone:
            update_data.phone = phone
        if reveal_email and extracted_email != "None":
            update_data.lead_email = extracted_email

        if update_data.phone or update_data.lead_email:
            updated_lead = (
                await LeadRepository.update_lead(db, lead_id, update_data)
            ).get("responseData", {})

            if reveal_phone:
                await UriTaskManagerService.update_user_feature_limit_specific_limit(
                    updated_lead.get("assigned_to", ""),
                    EndpointsEnum.LEAD_ENRICHMENT_PHONE.value,
                    0,
                )
            if reveal_email:
                await UriTaskManagerService.update_user_feature_limit_specific_limit(
                    updated_lead.get("assigned_to", ""),
                    EndpointsEnum.LEAD_ENRICHMENT_EMAIL.value,
                    0,
                )
        return response

    @staticmethod
    async def handle_search_result(
        search_result: dict, lead_form: Optional[dict], db: AsyncIOMotorDatabase
    ):
        if not lead_form:
            return
        pagination_data = search_result.get("pagination", {})
        total_entries = pagination_data.get("total_entries", 0)
        total_pages = pagination_data.get("total_pages", 0)
        page = lead_form.get("page", 0)
        lead_form_id = lead_form.get("lead_form_id", "")
        lead_form_type = lead_form.get("form_type", "")
        user_id = lead_form.get("user_id", "")
        if total_entries == 0:
            print("Apollo search turn up empty.")
            await ApolloService.handle_empty_search_result(
                user_id, lead_form_type=lead_form_type
            )
        elif (page + 1) >= total_pages:
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
    ) -> Optional[List[Lead]]:
        people = search_result.get("people", [])

        if not people or not user_id:
            return None

        latest_lead_form_snapshot: LeadFormSnapshot = (
            await ApolloService.get_latest_lead_form_snapshot(
                db, user_id=user_id, form_type=LeadFormTypeEnum.PERSON
            )
        ).get("responseData")

        tasks = []

        for person in people:
            lead_to_create_dict = LeadHelper.extract_apollo_person_lead(person)
            lead_to_create_dict["assigned_to"] = user_id
            lead_to_create_dict["lead_form_snapshot_id"] = (
                latest_lead_form_snapshot.lead_form_snapshot_id
                if latest_lead_form_snapshot
                else None
            )

            del person["employment_history"]
            tasks.append(
                ApolloService.perform_ai_lead_enrichment(lead_to_create_dict, person)
            )

        leads_to_create = await asyncio.gather(*tasks)
        await ApolloRepository.create_multiple(db, people)

        return leads_to_create

    @staticmethod
    async def handle_organization_search_result(
        search_result: dict, user_id: str, db: AsyncIOMotorDatabase
    ) -> Optional[List[Lead]]:
        organizations = search_result.get("organizations", [])
        if not organizations or not user_id:
            return None

        latest_lead_form_snapshot: LeadFormSnapshot = (
            await ApolloService.get_latest_lead_form_snapshot(
                db, user_id=user_id, form_type=LeadFormTypeEnum.PERSON
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
        ai_enriched_lead: Lead = AIService.extract_ai_result(
            await AIService.structured_chat_completion(ai_model, Lead)
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
