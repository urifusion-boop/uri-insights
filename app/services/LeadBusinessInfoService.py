import json
from typing import Collection, List, Optional

from fastapi import BackgroundTasks

from app.database import get_db
from app.domain.enums.ai_prompt import AIChiefAnalystPrompt
from app.domain.models.chat_model import (
    LeadBusinessSummary,
    LeadBusinessSummaryWithKeywords,
)
from app.domain.responses.uri_response import UriResponse
from app.domain.schemas.leadbusinessinfo_schema import (
    LeadBusinessInfoCreate,
    LeadBusinessInfoUpdate,
)
from app.repository.LeadBusinessInfoRepository import LeadBusinessInfoRepository
from app.services.AIService import AIService
from app.services.LeadService import LeadService
from motor.motor_asyncio import AsyncIOMotorDatabase


class LeadBusinessInfoService:
    @staticmethod
    async def create_lead_business_info(
        db: AsyncIOMotorDatabase,
        background_tasks: BackgroundTasks,
        lead_business_info: LeadBusinessInfoCreate,
    ):
        lead_business_info_data = lead_business_info.dict()
        user_id = lead_business_info_data.get("user_id")
        print("User ID: ", user_id)
        if not user_id:
            print("Invalid data in lead business info (NO USER ID)")
            return None
        existing_lead_business_info = (
            (
                await LeadBusinessInfoRepository.get_lead_business_info_by_filters(
                    db=db, user_id=user_id
                )
            )
            .get("responseData", {})
            .get("data", [])
        )
        print("Existing lead business info: ", existing_lead_business_info)
        if existing_lead_business_info:
            return UriResponse.conflict_response("Lead business info")

        initial_business_summary = lead_business_info_data["business_summary"]
        business_website = lead_business_info_data.get("business_website", None)

        if business_website or initial_business_summary:
            generated_business_summary = (
                await LeadBusinessInfoService.generate_business_summary(
                    business_website,
                    initial_business_summary,
                    (lead_business_info.keywords == None),
                )
            )
            if not generated_business_summary:
                raise ValueError("Failed to generate business summary")
            lead_business_info_data["business_summary"] = (
                generated_business_summary.get("summary")
            )
            generated_keywords = generated_business_summary.get("keywords")
            if generated_keywords:
                lead_business_info_data["keywords"] = generated_keywords

        # Create Lead Business Info
        response = await LeadBusinessInfoRepository.create(
            db=db,
            lead_business_info=LeadBusinessInfoCreate(**lead_business_info_data),
        )

        print("\nResponse: ", response)

        if response.get("status") == True:
            # Generate business leads
            background_tasks.add_task(
                LeadBusinessInfoService.__generate_business_leads,
                lead_business_info_data,
            )

        return response

    @staticmethod
    async def update_leads_business_info(
        db: Collection,
        lead_business_info_id: str,
        updates: LeadBusinessInfoUpdate,
        background_tasks: BackgroundTasks,
    ):
        lead_update_data = updates.dict(exclude_none=True)

        # Generate updated business summary
        business_summary = lead_update_data.get("business_summary")
        business_website = lead_update_data.get("business_website")
        keywords = lead_update_data.get("keywords")

        if business_summary or business_website:
            generated_business_summary = (
                await LeadBusinessInfoService.generate_business_summary(
                    business_summary=business_summary,
                    business_website=business_website,
                    with_keywords=(keywords == None),
                )
            )

            if not generated_business_summary:
                print("\nNew business summary not generated")
            else:
                lead_update_data["business_summary"] = generated_business_summary.get(
                    "summary"
                )
                generated_keywords = generated_business_summary.get("keywords")
                if generated_keywords:
                    lead_update_data["keywords"] = generated_keywords
        # Update lead business info
        response = await LeadBusinessInfoRepository.update(
            db,
            lead_business_info_id=lead_business_info_id,
            updates=LeadBusinessInfoUpdate(**lead_update_data),
        )

        if response.get("status"):
            business_info = response.get("responseData")
            background_tasks.add_task(
                (LeadBusinessInfoService.__generate_business_leads),
                business_info,
            )

            await LeadBusinessInfoRepository.update_user_lead_settings(
                db, business_info.get("user_id")
            )
            await LeadBusinessInfoRepository.update_user_next_generation_time(
                db, business_info.get("user_id")
            )

        return response

    @staticmethod
    async def generate_business_summary(
        business_website: str,
        business_summary: str,
        with_keywords: bool,
    ) -> Optional[LeadBusinessSummary]:
        """
        Create a business summary by performing a lookup of the business website

        Args:
            website (str): The business website..

        Returns:
            str: An AI generated business summary
        """
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

        model = AIService.build_ai_model(
            messages=[{"role": "user", "content": f"{prompt}"}]
        )

        try:
            # Parse AI response
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

            response = ai_response["choices"][0]["message"]["parsed"]

            # Return the parsed summary directly
            return response
        except Exception as e:
            # Log issues for debugging
            print(f"Error while generating business summary: {e}")
            return None

    @staticmethod
    async def __generate_business_leads(business_info: dict):
        keywords = business_info.get("keywords")

        if not keywords:
            raise ValueError("Business keywords missing")

        await LeadService.generate_items_for_lead_generation(business_info)

    # ----------- Methods for business info creation on user subscribe -------------
    @staticmethod
    async def process_business_info_creation_from_service_bus(data: str):
        db = get_db()

        data_dict = json.loads(data)
        user_id = data_dict.get("userId")
        platforms = data_dict.get("platforms")
        result = await LeadBusinessInfoService.create_or_update_on_user_subscribe(
            db, user_id, platforms
        )

        return result

    @staticmethod
    async def create_or_update_on_user_subscribe(
        db: AsyncIOMotorDatabase, user_id: str, platforms: List[str]
    ):
        existing_user_business_info_response = (
            await LeadBusinessInfoRepository.get_lead_business_info_by_filters(
                db, user_id
            )
        )

        if (
            existing_user_business_info_response
            and existing_user_business_info_response.get("status")
        ):
            user_business_info = existing_user_business_info_response.get(
                "responseData", {}
            ).get("data", [])

            if len(user_business_info) > 0:
                return await LeadBusinessInfoService.update_user_business_info_on_subscribe(
                    db, user_business_info[0], platforms
                )
        return await LeadBusinessInfoService.create_user_business_info_on_subscribe(
            db, user_id, platforms
        )

    @staticmethod
    async def update_user_business_info_on_subscribe(
        db: AsyncIOMotorDatabase, user_business_info: dict, platforms: List[str]
    ):
        lead_business_info_id = user_business_info.get("lead_business_info_id", "")
        business_info_data = user_business_info  # Already a single dict, not a list
        existing_platforms = business_info_data.get("source_platforms", [])

        if existing_platforms and existing_platforms != platforms:
            business_info_data["source_platforms"] = list(
                set(existing_platforms + platforms)
            )
        else:
            business_info_data["source_platforms"] = platforms
        updated_user_business_info = await LeadBusinessInfoRepository.update(
            db, lead_business_info_id, LeadBusinessInfoUpdate(**business_info_data)
        )

        if not updated_user_business_info.get("status"):
            return None
        return updated_user_business_info

    @staticmethod
    async def create_user_business_info_on_subscribe(
        db: AsyncIOMotorDatabase, user_id: str, platforms: List[str]
    ):
        lead_business_info_data = LeadBusinessInfoCreate(
            user_id=user_id,
            business_name="example limited",
            business_summary="A business",
            source_platforms=platforms,
        )

        created_user_business_info = await LeadBusinessInfoRepository.create(
            db, lead_business_info_data
        )

        if not created_user_business_info.get("status"):
            return None
        return created_user_business_info
