import json
from typing import Any, List, Optional, Union
from fastapi import BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.helpers.leadform_helper import LeadFormHelper
from app.core.helpers.user_helper import UserHelper
from app.database import get_db
from app.domain.enums.ai_prompt import AIChiefAnalystPrompt, LeadFormServicePrompts
from app.domain.enums.lead_enum import LeadStatusEnum
from app.domain.enums.leadform_enum import (
    AiLeadResponseGuidePlaybookEnum,
    LeadFormTypeEnum,
)
from app.domain.enums.queue_message_type_enum import LeadFormNotificationMessageTypeEnum
from app.domain.models.chat_model import (
    LeadBusinessSummary,
    LeadBusinessSummaryWithKeywords,
)
from app.domain.requests.lead_requests import GetLeadsByFiltersRequest
from app.domain.responses.uri_response import UriResponse
from app.domain.schemas.leadform_schema import (
    BusinessLeadFormUpdate,
    ConversationalLeadFormUpdate,
    LeadFormCreate,
    OrganizationLeadFormUpdate,
    PersonLeadFormUpdate,
)
from app.repository.LeadFormRepository import LeadFormRepository
from app.repository.LeadRepository import LeadRepository
from app.services.AIService import AIService
from app.services.LeadService import LeadService
from app.services.NotificationService import NotificationService


class LeadFormService:
    @staticmethod
    async def create(
        db: AsyncIOMotorDatabase,
        lead_form: LeadFormCreate,
        background_tasks: Optional[BackgroundTasks] = None,
    ):
        non_apollo_form_types = [
            LeadFormTypeEnum.CONVERSATIONAL,
            LeadFormTypeEnum.BUSINESS,
        ]

        if lead_form.form_type == LeadFormTypeEnum.BUSINESS and background_tasks:
            create_response = await LeadFormService.create_business_lead_form(
                db=db, background_tasks=background_tasks, lead_form=lead_form
            )
        elif lead_form.form_type == LeadFormTypeEnum.CONVERSATIONAL:
            return await LeadFormService.create_conversational_lead_form(db, lead_form, background_tasks)
        else:
            if lead_form.per_page and lead_form.per_page == 0:
                return UriResponse.custom_response(
                    "You cannot generate 0 leads per page.", 400
                )
            if lead_form.per_page and lead_form.per_page > 100:
                return UriResponse.custom_response(
                    "You cannot generate more than 100 leads at once.", 400
                )
            create_response = await LeadFormRepository.create(db, lead_form)

        if not create_response.get("status"):
            return create_response

        if lead_form.form_type in non_apollo_form_types:
            return create_response

        lead_form = create_response.get("responseData", {})

        if background_tasks:
            background_tasks.add_task(
                LeadService.trigger_apollo_leads_generation, lead_form, db
            )

        return create_response

    @staticmethod
    async def create_conversational_lead_form(
        db: AsyncIOMotorDatabase,
        lead_form: LeadFormCreate,
        background_tasks: Optional[BackgroundTasks] = None
    ):
        create_response = await LeadFormRepository.create(db, lead_form)

        if create_response.get("status"):
            await LeadFormService.send_lead_request_notification(
                db, create_response.get("responseData", {}), lead_form.user_id
            )

            # Trigger immediate background job to fetch leads
            if background_tasks:
                from app.services.ConversationalLeadJobService import ConversationalLeadJobService
                lead_form_data = create_response.get("responseData", {})
                print(f"✅ Adding background task for conversational lead form {lead_form_data.get('lead_form_id')}")
                background_tasks.add_task(
                    ConversationalLeadJobService.fetch_leads_from_platforms,
                    db,
                    lead_form_data,
                    lead_form.user_id
                )
            else:
                print("⚠️ No background_tasks provided - skipping lead fetching")

        return create_response

    @staticmethod
    async def create_business_lead_form(
        db: AsyncIOMotorDatabase,
        background_tasks: BackgroundTasks,
        lead_form: LeadFormCreate,
    ):
        lead_form_data = lead_form.dict()
        user_id = lead_form_data.get("user_id")

        if not user_id:
            return UriResponse.custom_response(
                "Invalid data: user_id is required.", 400
            )

        existing_forms = (
            await LeadFormRepository.get_by_filters(
                db,
                {
                    "user_id": user_id,
                    "form_type": LeadFormTypeEnum.BUSINESS.value,
                },
            )
        ).get("responseData", [])

        if existing_forms:
            return UriResponse.conflict_response("Business lead form")

        # Enrich with AI if needed
        summary = lead_form_data.get("business_summary")
        website = lead_form_data.get("business_website")
        needs_keywords = lead_form_data.get("keywords") is None

        if summary or website:
            generated = await LeadFormService.__generate_business_summary(
                website, summary, needs_keywords
            )
            if not generated:
                raise ValueError("Failed to generate business summary")

            lead_form_data["business_summary"] = generated.get("summary")
            if generated.get("keywords"):
                lead_form_data["keywords"] = generated["keywords"]

        # Create lead form
        response = await LeadFormRepository.create(
            db=db,
            lead_form=LeadFormCreate(**lead_form_data),
        )

        if response.get("status"):
            background_tasks.add_task(
                LeadFormService.__generate_business_leads, lead_form_data
            )

        return response

    @staticmethod
    async def update_apollo_lead_forms(
        db: AsyncIOMotorDatabase,
        update_data: Union[
            PersonLeadFormUpdate,
            OrganizationLeadFormUpdate,
        ],
        lead_form_id: str,
        background_tasks: BackgroundTasks,
    ):
        if update_data.per_page and update_data.per_page == 0:
            return UriResponse.custom_response(
                "You cannot generate 0 leads per page.", 400
            )
        if update_data.per_page and update_data.per_page > 100:
            return UriResponse.custom_response(
                "You cannot generate more than 100 leads at once.", 400
            )
        update_data.disabled = False
        update_data.disabled_reason = None
        update_response = await LeadFormRepository.update(db, update_data, lead_form_id)

        if update_response.get("status"):
            lead_form = update_response.get("responseData", {})
            background_tasks.add_task(
                LeadService.trigger_apollo_leads_generation, lead_form, db
            )
        return update_response

    @staticmethod
    async def update_conversational_lead_form(
        db: AsyncIOMotorDatabase,
        lead_form_id: str,
        updates: ConversationalLeadFormUpdate,
        background_tasks: Optional[BackgroundTasks] = None
    ):
        update_response = await LeadFormRepository.update(db, updates, lead_form_id)

        if update_response.get("status"):
            lead_form = update_response.get("responseData", {})
            user_id = lead_form.get("user_id", "")
            await LeadFormService.send_lead_request_notification(db, lead_form, user_id)

            # Trigger immediate background job to fetch leads
            if background_tasks:
                from app.services.ConversationalLeadJobService import ConversationalLeadJobService
                print(f"✅ Adding background task for conversational lead form update {lead_form.get('lead_form_id')}")
                background_tasks.add_task(
                    ConversationalLeadJobService.fetch_leads_from_platforms,
                    db,
                    lead_form,
                    user_id
                )
            else:
                print("⚠️ No background_tasks provided - skipping lead fetching")

        return update_response

    @staticmethod
    async def update_business_lead_form(
        db: AsyncIOMotorDatabase,
        lead_form_id: str,
        updates: BusinessLeadFormUpdate,
        background_tasks: BackgroundTasks,
    ):
        update_data = updates.dict(exclude_none=True)
        summary = update_data.get("business_summary")
        website = update_data.get("business_website")
        needs_keywords = update_data.get("keywords") is None

        if summary or website:
            generated = await LeadFormService.__generate_business_summary(
                website, summary, needs_keywords
            )
            if generated:
                update_data["business_summary"] = generated.get("summary")
                if generated.get("keywords"):
                    update_data["keywords"] = generated["keywords"]

        await db[LeadFormRepository.COLLECTION_NAME].update_one(
            {"lead_form_id": lead_form_id}, {"$set": update_data}
        )

        updated_form = await LeadFormRepository.get_by_id(db, lead_form_id)

        if updated_form.get("status"):
            form_data = updated_form.get("responseData")
            background_tasks.add_task(
                LeadFormService.__generate_business_leads,
                form_data,
            )

        return updated_form

    @staticmethod
    async def get_by_filters(filters: dict, db: AsyncIOMotorDatabase):
        user_lead_forms = (await LeadFormRepository.get_by_filters(db, filters)).get(
            "responseData", []
        )
        results = []
        if not user_lead_forms:
            return UriResponse.custom_response("Lead forms not found.", 404)

        for lead_form in user_lead_forms:
            lead_form["total_leads"] = await LeadFormService.get_metadata_for_lead_form(
                db, lead_form
            )
            lead_form["total_new_leads"] = (
                await LeadFormService.get_metadata_for_lead_form(db, lead_form, True)
            )
            results.append(lead_form)

        return UriResponse.get_list_data_response("Lead form", results)

    @staticmethod
    async def get_metadata_for_lead_form(
        db: AsyncIOMotorDatabase, lead_form: dict, get_new: bool = False
    ):
        user_id = lead_form.get("user_id", "")
        lead_form_type = lead_form.get("form_type", "")

        lead_filters = {"assigned_to": user_id, "lead_type": lead_form_type}

        if get_new:
            lead_filters["lead_status"] = LeadStatusEnum.NEW

        leads_response = await LeadRepository.get_leads_by_filters(
            db=db, filters=GetLeadsByFiltersRequest(**lead_filters)
        )

        return leads_response.get("responseData", {}).get("total", 0)

    @staticmethod
    async def auto_populate_lead_form(
        lead_form_type: LeadFormTypeEnum,
        data: Any,
    ):
        prompt = LeadFormHelper.get_prompt_for_auto_population(lead_form_type).format(
            data=data
        )
        result_model = LeadFormHelper.get_result_model_for_auto_population(
            lead_form_type
        )

        ai_model = AIService.build_ai_model([AIService.construct_user_prompt(prompt)])

        ai_response = await AIService.structured_chat_completion(ai_model, result_model)

        extracted_response = LeadFormHelper.process_auto_generated_inputs(
            AIService.extract_ai_result(ai_response)
        )

        return UriResponse.get_single_data_response(
            "Suggested form", extracted_response.model_dump()
        )

    @staticmethod
    async def __generate_business_summary(
        business_website: str,
        business_summary: str,
        with_keywords: bool,
    ):
        if with_keywords:
            prompt = (
                AIChiefAnalystPrompt.LEADS_BUSINESS_SUMMARY_WITH_KEYWORDS.value.format(
                    business_website=business_website,
                    business_summary=business_summary,
                )
            )
        else:
            prompt = AIChiefAnalystPrompt.LEADS_BUSINESS_SUMMARY.value.format(
                business_website=business_website,
                business_summary=business_summary,
            )

        model = AIService.build_ai_model(messages=[{"role": "user", "content": prompt}])

        try:
            if with_keywords:
                ai_response = (
                    await AIService.structured_chat_completion(
                        model, LeadBusinessSummaryWithKeywords
                    )
                ).dict()
            else:
                ai_response = (
                    await AIService.structured_chat_completion(
                        model, LeadBusinessSummary
                    )
                ).dict()

            return ai_response["choices"][0]["message"]["parsed"]
        except Exception as e:
            print(f"Error generating business summary: {e}")
            return None

    @staticmethod
    async def __generate_business_leads(lead_form: dict):
        keywords = lead_form.get("keywords")
        if not keywords:
            raise ValueError("Keywords missing")
        await LeadService.generate_items_for_lead_generation(lead_form)

    # ----------- Methods for business info creation on user subscribe -------------
    @staticmethod
    async def process_business_info_creation_from_service_bus(data: str):
        db = get_db()

        data_dict = json.loads(data)
        user_id = data_dict.get("userId")
        platforms = data_dict.get("platforms")
        result = await LeadFormService.create_or_update_on_user_subscribe(
            db, user_id, platforms
        )

        return result

    @staticmethod
    async def create_or_update_on_user_subscribe(
        db: AsyncIOMotorDatabase, user_id: str, platforms: List[str]
    ):
        existing_forms = (
            await LeadFormRepository.get_by_filters(
                db,
                {
                    "user_id": user_id,
                    "form_type": LeadFormTypeEnum.BUSINESS.value,
                },
            )
        ).get("responseData", [])

        if existing_forms:
            return await LeadFormService.update_business_platforms(
                db, existing_forms[0], platforms
            )
        return await LeadFormService.create_on_user_subscribe(db, user_id, platforms)

    @staticmethod
    async def update_business_platforms(
        db: AsyncIOMotorDatabase, lead_form: dict, platforms: List[str]
    ):
        lead_form_id = lead_form.get("lead_form_id", "")
        existing_platforms = lead_form.get("source_platforms", [])

        if existing_platforms and existing_platforms != platforms:
            combined = list(set(existing_platforms + platforms))
        else:
            combined = platforms

        update = BusinessLeadFormUpdate(source_platforms=combined)

        return await LeadFormService.update_business_lead_form(
            db, lead_form_id, update, BackgroundTasks()
        )

    @staticmethod
    async def create_on_user_subscribe(
        db: AsyncIOMotorDatabase, user_id: str, platforms: List[str]
    ):
        business_lead_form_data = LeadFormCreate(
            user_id=user_id,
            business_name="exmaple limited",
            business_summary="A business",
            source_platforms=platforms,
        )

        created_lead_form = await LeadFormRepository.create(db, business_lead_form_data)
        return created_lead_form

    @staticmethod
    async def summarize_lead_form(db: AsyncIOMotorDatabase, lead_form: dict):
        ai_model = AIService.build_ai_model(
            [
                AIService.construct_user_prompt(
                    LeadFormServicePrompts.SUMMARY_PROMPT.value.format(data=lead_form)
                )
            ]
        )

        ai_full_response = await AIService.structured_chat_completion(ai_model)

        summarized_lead_form = AIService.extract_ai_result(ai_full_response)

        return UriResponse.get_single_data_response(
            "Lead form summary", summarized_lead_form.text
        )

    @staticmethod
    async def send_lead_request_notification(
        db: AsyncIOMotorDatabase, lead_form: dict, user_id: str
    ):
        lead_form_summary_response = await LeadFormService.summarize_lead_form(
            db, lead_form
        )
        print("Lead form summary: ", lead_form_summary_response)
        notification_data = {
            "userEmail": await UserHelper.get_user_email(user_id),
            "leadsFormSummary": lead_form_summary_response.get("responseData"),
        }

        await NotificationService.send_lead_form_notification(
            data=notification_data,
            message_type=LeadFormNotificationMessageTypeEnum.LEAD_REQUEST,
        )
