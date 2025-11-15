import asyncio
from datetime import datetime, timedelta
import json
import traceback
from typing import (
    Any,
    Collection,
    Dict,
    List,
    Optional,
)


from app.core.config import settings
from app.core.helpers.cache_helper import CacheHelper
from app.core.helpers.dict_helper import DictHelper
from app.core.helpers.google_helper import GoogleHelper
from app.core.helpers.lead_helper import LeadHelper
from app.core.helpers.notification_helper import NotificationHelper
from app.database import get_db
from app.domain.enums.ai_prompt import LeadFollowUpMessagePromptEnum, LeadServicePrompts
from app.domain.enums.datasenderservices_enum import DataSenderServicesEnum
from app.domain.enums.date_enum import DateFilterEnum
from app.domain.enums.endpoints_enum import EndpointsEnum
from app.domain.enums.env_enum import EnvEnum
from app.domain.enums.filetype_enum import FileTypeEnum
from app.domain.enums.leadform_enum import LeadFormTypeEnum
from app.domain.enums.microservicestype_enum import MicroServiceTypeEnum
from app.domain.enums.queue_enum import QueueEnum
from app.domain.enums.queue_message_type_enum import (
    AuditLogQueueMessageTypeEnum,
    LeadManagementMessageTypeEnum,
    LeadQueueMessageTypeEnum,
    UserNotificationQueueMessageTypeEnum,
)
from app.domain.requests.lead_requests import GetLeadsByFiltersRequest
from app.domain.responses.lead_response import (
    ImportedConversationalLeadEnrichmentResponse,
)
from app.domain.responses.uri_response import UriResponse
from app.domain.scrapers.lead_scrapers.GoogleLeadDataScraper import (
    GoogleLeadDataScraper,
)
from app.domain.scrapers.lead_scrapers.LeadDataScraper import LeadDataScraper
from app.domain.scrapers.lead_scrapers.TwitterLeadDataScraper import (
    TwitterLeadDataScraper,
)
from app.middlewares.FeatureLimitMiddleware import FeatureLimitExceeded
from app.repository.CacheRepository import CacheRepository
from app.repository.LeadFormRepository import LeadFormRepository
from app.repository.LeadRepository import LeadRepository
from app.services.ApolloService import ApolloService
from app.services.DataSenderService import DataSenderService
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.schemas.lead_schema import Lead, LeadUpdate
from app.services.AIService import AIService
from app.domain.models.chat_model import (
    RegeneratedLeadFollowUpMessage,
)
from app.services.FileExportService import FileExportService
from app.domain.enums.lead_enum import (
    LeadInterestLevelEnum,
    LeadsProcessedStatus,
    LeadSourceEnum,
    LeadStatusEnum,
    LeadOpportunityTypeEnum,
)
from app.domain.schemas.lead_schema import LeadCreate
from app.services.LeadExporterService import LeadExporter
from app.services.NotificationService import NotificationService

from app.services.azure.producers.AuditLogProducer import AuditLogQueueProducerService
from app.services.azure.producers.ExceptionLogProducer import (
    ExceptionLogQueueProducerService,
)
from app.services.uri_microservices.UriTaskManagerService import UriTaskManagerService
from app.services.OpenAIApifyTwitterService import OpenAIApifyTwitterService


from app.services.BrowsercloudService import BrowsercloudService
from app.services.RealtimeLeadProcessor import RealtimeLeadProcessor

class LeadService:
    PLATFORM_SCRAPERS: dict[str, LeadDataScraper] = {
        "google": GoogleLeadDataScraper(),
        "twitter": TwitterLeadDataScraper(),
    }
    
    browsercloud_service = BrowsercloudService()
    realtime_processor = RealtimeLeadProcessor()

    @staticmethod
    async def delete_lead(db: AsyncIOMotorDatabase, lead_id: str):
        deleted_response = await LeadRepository.delete_lead(db, lead_id)

        print("Deleted response: ", deleted_response)

        if not deleted_response.get("status", ""):
            return UriResponse.custom_response("Failed to delete lead", 500)

        deleted_lead = deleted_response.get("responseData", {})

        if deleted_lead:
            await NotificationService.send_lead_management_message(
                deleted_lead, LeadManagementMessageTypeEnum.DELETED_LEAD
            )

        return deleted_response

    @staticmethod
    async def regenerate_lead_follow_up_message(
        lead_id: str, user_prompt: str, db: AsyncIOMotorDatabase
    ):
        existing_lead = (
            await LeadRepository.get_lead_by_id(lead_id=lead_id, db=db)
        ).get("responseData", {})

        if not existing_lead:
            return None

        prompt = f"""
        You are an advanced business opportunity analyst with expertise in lead generation.
        Your task is to analyze the following lead data and regenerate the follow-up message based on the user prompt.
        ### **Lead Data**
        {existing_lead}

        ### **User Prompt**
        {user_prompt}
        """

        model = AIService.build_ai_model(messages=[{"role": "user", "content": prompt}])

        try:
            ai_response = (
                await AIService.structured_chat_completion(
                    model, RegeneratedLeadFollowUpMessage
                )
            ).dict()

            response = ai_response["choices"][0]["message"]["parsed"]

            if not response.get("follow_up_message"):
                raise ValueError("No follow-up message generated")

            updated_lead = await LeadRepository.update_lead(
                lead_id=lead_id,
                updates=LeadUpdate(follow_up_message=response.get("follow_up_message")),
                db=db,
            )

            return updated_lead

        except Exception as e:
            print(f"Error while regenerating lead follow-up message: {e}")
            return None

    @staticmethod
    async def fetch_and_save_conversational_twitter_leads(db: AsyncIOMotorDatabase):
        async for batch in LeadFormRepository.fetch_lead_forms_in_batches(
            db=db, filter={"form_type": LeadFormTypeEnum.CONVERSATIONAL.value}
        ):
            tasks = [
                LeadService._process_conversational_twitter_fetch(db, lead_form)
                for lead_form in batch
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    async def _process_conversational_twitter_fetch(
        db: AsyncIOMotorDatabase, lead_form: dict
    ):
        user_id = lead_form.get("user_id", "")
        keywords = lead_form.get("keywords", [])
        if not user_id or not keywords:
            return

        # Try to get user's subscription plan from Task Manager
        feature_limit_response = await UriTaskManagerService.get_user_feature_limit(
            user_id
        )

        # TODO: TESTING MODE - Allow testing without Task Manager service
        testing_mode = settings.ENV.lower() != "production"

        if not feature_limit_response or not feature_limit_response.get("status"):
            if testing_mode:
                # In testing mode, use mock data if Task Manager is unavailable
                print(f"⚠️  Task Manager unavailable in testing mode - using mock plan")
                # You can override this by setting a test plan in the form's settings
                mock_plan = lead_form.get("settings", {}).get("test_subscription_plan", "STANDARD")
                plan = mock_plan
            else:
                # In production, Task Manager is required
                return
        else:
            fl_data = feature_limit_response.get("responseData", {}).get("data", {})
            plan = (
                fl_data.get("subscriptionPlan")
                or feature_limit_response.get("responseData", {}).get("subscriptionPlan")
                or "STANDARD"
            )
        plan_upper = str(plan).upper()

        # TODO: TESTING MODE - Remove after testing
        # Reduced intervals for testing (minutes instead of hours)
        testing_mode = settings.ENV.lower() != "production"

        if testing_mode:
            # Testing intervals in MINUTES
            if plan_upper == "BUSINESS" or plan_upper == "LEAD_ONLY":
                max_tweets, interval_minutes = 5, 2  # 5 tweets every 2 minutes
            elif plan_upper == "PROFESSIONAL":
                max_tweets, interval_minutes = 4, 4  # 4 tweets every 4 minutes
            else:
                max_tweets, interval_minutes = 3, 6  # 3 tweets every 6 minutes (STANDARD)
            interval_hours = interval_minutes / 60  # Convert to hours for timedelta
        else:
            # Production intervals in HOURS
            if plan_upper == "BUSINESS" or plan_upper == "LEAD_ONLY":
                max_tweets, interval_hours = 40, 1
            elif plan_upper == "PROFESSIONAL":
                max_tweets, interval_hours = 30, 3
            else:
                max_tweets, interval_hours = 20, 7

        settings_obj = lead_form.get("settings", {})
        tw_settings = settings_obj.get("conversational_twitter_fetch", {})
        last_fetched_at = tw_settings.get("last_fetched_at")
        should_fetch = True
        if last_fetched_at:
            try:
                last_dt = datetime.fromisoformat(last_fetched_at)
                should_fetch = datetime.utcnow() - last_dt >= timedelta(
                    hours=interval_hours
                )
            except Exception:
                should_fetch = True

        if not should_fetch:
            return

        service = OpenAIApifyTwitterService()
        keyword = keywords[0]
        result = await service.fetch_tweets_with_analysis(
            keyword=keyword, max_tweets=max_tweets, analyze_sentiment=False
        )
        if not result or not result.get("success"):
            return

        tweets = result.get("tweets", [])
        leads_to_create: List[LeadCreate] = []
        for t in tweets:
            # Parse Twitter date format: 'Sat Nov 15 16:00:13 +0000 2025'
            created_at_str = t.get("created_at")
            if created_at_str:
                try:
                    # Twitter uses this format: '%a %b %d %H:%M:%S %z %Y'
                    created_dt = datetime.strptime(created_at_str, '%a %b %d %H:%M:%S %z %Y')
                    created_iso = created_dt.isoformat()
                except Exception:
                    # Fallback to current time if parsing fails
                    created_iso = datetime.utcnow().isoformat()
            else:
                created_iso = datetime.utcnow().isoformat()

            leads_to_create.append(
                LeadCreate(
                    first_name=t.get("author") or "Twitter User",
                    last_name=None,
                    username=t.get("author") or "",
                    mention=t.get("text") or "",
                    lead_reason=t.get("text") or "",
                    lead_status=LeadStatusEnum.NEW,
                    opportunity_type=LeadOpportunityTypeEnum.OTHER,
                    tags=[],
                    twitter_url=t.get("url") or None,
                    lead_link=t.get("url") or None,
                    social_profile_link=t.get("url") or None,
                    picture_url=None,
                    created_date=created_iso,
                    last_updated=created_iso,
                    lead_type=LeadFormTypeEnum.CONVERSATIONAL,
                    website_url=t.get("url") or None,
                    lead_source=LeadSourceEnum.X,
                    assigned_to=user_id,
                    starred=False,
                )
            )

        if leads_to_create:
            await LeadRepository.multiple_create_leads(db, leads_to_create)

        update_payload = {
            "settings.conversational_twitter_fetch": {
                "last_fetched_at": datetime.utcnow().isoformat(),
                "last_fetch_count": len(tweets),
                "keyword": keyword,
                "interval_hours": interval_hours,
                "max_tweets": max_tweets,
                "plan": plan_upper,
            }
        }
        await db[LeadFormRepository.COLLECTION_NAME].update_one(
            {
                "lead_form_id": lead_form.get("lead_form_id"),
            },
            {"$set": update_payload},
        )

    @staticmethod
    async def generate_leads_background_job(
        db: Collection, batch_size: int = 10
    ) -> None:
        """
        Filter out business info that has already been processed and generate leads.
        """
        async for batch in LeadFormRepository.fetch_lead_forms_in_batches(
            db, batch_size, {"form_type": LeadFormTypeEnum.BUSINESS.value}
        ):
            # Step 1: Filter business info using async concurrency
            filtered = await asyncio.gather(
                *[
                    LeadService.check_cached_leads_settings(business_info)
                    for business_info in batch
                ]
            )

            # Step 2: Remove None (i.e., already processed ones)
            valid_business_infos = [info for info in filtered if info]

            print("Valid business infos: ", valid_business_infos)

            # Step 3: Generate items for each valid business info concurrently
            await asyncio.gather(
                *[
                    LeadService.generate_items_for_lead_generation(info)
                    for info in valid_business_infos
                ]
            )

    @staticmethod
    async def check_cached_leads_settings(business_info: dict):
        business_info_settings = business_info.get("settings", {})
        business_name = business_info.get("business_name", "")
        auto_generate = business_info.get("auto_generate", False)
        leads_processed_status = business_info_settings.get("last_scraped_status")
        last_scraped_date = business_info_settings.get("last_scraped_date")
        now = datetime.utcnow()

        if (
            (
                leads_processed_status != LeadsProcessedStatus.COMPLETED
                or not last_scraped_date
                or now - last_scraped_date > timedelta(hours=12)
            )
            and business_name != "example limited"
            and auto_generate
        ):
            return business_info
        return None

    @staticmethod
    @LeadHelper.enforce_feature_limit(
        lambda lead_form: lead_form.get("user_id", ""), EndpointsEnum.LEAD_GEN.value
    )
    async def generate_items_for_lead_generation(lead_form: dict):
        if not await LeadService.check_cached_leads_settings(lead_form):
            raise Exception("Time to generate leads hasn't been reached.")

        user_id = lead_form.get("user_id", "")

        await AuditLogQueueProducerService.publish_audit_log(
            {"message": f"Lead gen triggered for business form {lead_form}"},
            AuditLogQueueMessageTypeEnum.SYSTEM_EVENT,
        )

        source_platforms = lead_form.get("source_platforms", [])

        if not user_id:
            raise ValueError("No user ID in business info: ", lead_form)

        # Google batches
        google_params_batch_one = (
            GoogleHelper.construct_google_search_params_from_business_info(lead_form)
        )
        google_params_batch_two = (
            GoogleHelper.construct_google_search_params_from_business_info(lead_form, 2)
        )

        # Run scraping for all platforms
        await LeadService.scrape_lead_data_per_platform_and_push_to_redis(
            {
                "user_id": user_id,
                "platform": "google",
                "params": google_params_batch_one,
            },
            lead_form,
        )
        await LeadService.scrape_lead_data_per_platform_and_push_to_redis(
            {
                "user_id": user_id,
                "platform": "google",
                "params": google_params_batch_two,
            },
            lead_form,
        )

        if (
            settings.ENV.lower() == EnvEnum.PRODUCTION
            and source_platforms
            and "twitter" in source_platforms
        ):
            twitter_params = LeadHelper.build_tweet_search_query(lead_form)
            await LeadService.scrape_lead_data_per_platform_and_push_to_redis(
                {
                    "user_id": user_id,
                    "platform": "twitter",
                    "params": twitter_params,
                },
                lead_form,
            )

        print("Data scraping for lead processing completed")

    @staticmethod
    async def scrape_lead_data_per_platform_and_push_to_redis(
        scraping_params: dict,
        business_info: dict,
    ):
        db = get_db()
        platform = scraping_params.get("platform", "")
        params = scraping_params.get("params")

        if not params:
            raise ValueError("No search parameters provided for leads generation")

        handler = LeadService.PLATFORM_SCRAPERS.get(platform)
        if not handler:
            raise ValueError(f"Unsupported platform for lead data scraping: {platform}")

        try:
            result = await handler.scrape(db, params)
        except Exception as e:
            print(f"Error during scraping for platform {platform}: {e}")
            return

        if result:
            del scraping_params["params"]
            scraping_params["result"] = result
            scraping_params["business_info"] = {
                "business_summary": business_info.get("business_summary"),
                "competitors": business_info.get("competitors"),
                "keywords": business_info.get("keywords"),
                "ai_reply_context": business_info.get("ai_response_guide"),
            }
            unprocessed_lead_data = scraping_params
            data_to_send = {"type": "LEAD", "payload": unprocessed_lead_data}

            tasks = [
                DataSenderService.send_data(
                    DataSenderServicesEnum.AZURE_SERVICE_BUS,
                    QueueEnum.LEAD_GENERATION_QUEUE,  # type: ignore[attr-defined]
                    data_to_send,
                    LeadQueueMessageTypeEnum.LEAD,
                ),
                LeadFormRepository.update_user_lead_settings(
                    db, business_info.get("user_id")
                ),
                LeadFormRepository.update_user_next_generation_time(
                    db, business_info.get("user_id")
                ),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    print("Exception in cleaning up lead gen first stage")
                    print(result)  # Immediately raise the first

    @staticmethod
    async def process_lead_from_service_bus(lead):
        lead_dict = json.loads(lead)
        db = get_db()
        user_id = lead_dict.get("assigned_to")
        cache_key = CacheHelper.generate_cache_key(f"should_send_lead_email_{user_id}")
        # Confirm that lead doesn't exist already
        try:
            created_lead = await LeadRepository.create_lead(
                db, lead=LeadCreate(**lead_dict, lead_type=LeadFormTypeEnum.BUSINESS)
            )
            # Send lead email
            await LeadService.send_lead_email(
                db, created_lead.get("responseData"), cache_key
            )
            print("New lead created successfully: ", created_lead)
        except Exception as e:
            print("Exception occurred in creating lead: ", e)

    @staticmethod
    async def process_imported_leads(leads: str, is_pre_stored: bool = False):
        loaded_leads: List[Dict[str, Any]] = json.loads(leads)
        user_id = loaded_leads[0].get("assigned_to")
        db = get_db()

        if not user_id:
            raise Exception("No user ID found in imported leads")

        if is_pre_stored:
            conversational_lead_form = (
                await LeadFormRepository.get_by_filters(
                    db=db,
                    filters={
                        "user_id": user_id,
                        "form_type": LeadFormTypeEnum.CONVERSATIONAL.value,
                    },
                )
            ).get("responseData", [])

            if not conversational_lead_form:
                raise Exception("Lead form not found for conversational leads import.")

            enrichment_tasks = [
                LeadService.perform_ai_enrichment_on_conversational_lead(lead)
                for lead in loaded_leads
            ]

            tasks_results = await asyncio.gather(
                *enrichment_tasks, return_exceptions=True
            )

            lead_objs: List[dict[str, Any]] = [
                lead.model_dump(mode="json")
                for lead in tasks_results
                if not isinstance(lead, BaseException)
            ]

            leads_to_create = await LeadService._attach_follow_ups(
                lead_objs, conversational_lead_form[0]
            )

        else:
            leads_to_create = [LeadCreate(**lead) for lead in loaded_leads]

        await LeadRepository.multiple_create_leads(db, leads_to_create)

    @staticmethod
    async def perform_ai_enrichment_on_conversational_lead(lead: dict) -> LeadCreate:
        prompt = LeadServicePrompts.IMPORTED_CONVERSATIONAL_LEAD_ENRICHMENT_PROMPT.value.format(
            lead=lead
        )
        ai_model = AIService.build_ai_model([AIService.construct_user_prompt(prompt)])

        ai_response = await AIService.structured_chat_completion(
            ai_model, ImportedConversationalLeadEnrichmentResponse
        )

        extracted_response: ImportedConversationalLeadEnrichmentResponse = (
            AIService.extract_ai_result(ai_response)
        )
        return LeadCreate(
            **lead,
            **extracted_response.model_dump(exclude_none=True),
            is_pre_stored=True,
        )

    @staticmethod
    async def send_lead_email(db: AsyncIOMotorDatabase, lead: dict, cache_key: str):
        if lead.get("interest_level") == LeadInterestLevelEnum.HIGH:
            await NotificationService.notify_new_lead(lead, True)
        if not await CacheRepository.get_cache(db, cache_key):
            await NotificationService.notify_new_lead(lead, False)
            await CacheRepository.set_cache(db, cache_key, lead, timedelta(hours=12))

    @staticmethod
    async def export_leads_data(
        file_type: FileTypeEnum,
        db: Collection,
        filters: GetLeadsByFiltersRequest,
        date_filter: Optional[DateFilterEnum] = None,
        skip: int = 0,
        limit: int = 10,
    ):
        """
        Export leads as CSV to the user.
        """
        leads = await LeadExporter._fetch_leads(db, filters, skip, limit, date_filter)

        if not leads:
            raise ValueError("No leads found for export.")

        form_title = await LeadExporter._resolve_form_title(db, filters)

        LeadExporter._format_leads_for_export(leads)

        export_request = LeadExporter._build_export_request(
            user_id=filters.assigned_to,
            file_type=file_type,
            form_title=form_title,
            data=leads,
        )

        await FileExportService.export_file_data(export_request)

    @staticmethod
    async def generate_apollo_person_leads_background_job(
        db: AsyncIOMotorDatabase, batch_size: int = 10
    ) -> None:
        """
        Generate Apollo leads in the background.
        """
        async for batch in LeadFormRepository.fetch_lead_forms_in_batches(
            db, batch_size, {"form_type": LeadFormTypeEnum.PERSON.value}
        ):
            await asyncio.gather(
                *[
                    LeadService.trigger_apollo_leads_generation(lead_form, db)
                    for lead_form in batch
                    if lead_form.get("auto_generate", False)
                ]
            )

    @staticmethod
    async def generate_apollo_organization_leads_background_job(
        db: AsyncIOMotorDatabase, batch_size: int = 10
    ) -> None:
        """
        Generate Apollo organization leads in the background.
        """
        async for batch in LeadFormRepository.fetch_lead_forms_in_batches(
            db, batch_size, {"form_type": LeadFormTypeEnum.ORGANIZATION.value}
        ):
            await asyncio.gather(
                *[
                    LeadService.trigger_apollo_leads_generation(lead_form, db)
                    for lead_form in batch
                    if lead_form.get("auto_generate", False)
                ]
            )

    @staticmethod
    async def trigger_apollo_leads_generation(
        lead_form: dict, db: AsyncIOMotorDatabase
    ):
        """
        Generate individual or organization leads in the background
        """
        if lead_form.get("disabled"):
            print(f"Lead form {lead_form.get('lead_form_id')} is disabled.")
            return UriResponse.custom_response("This lead form has been disabled", 400)
        print("TRIGGER LEADS GEN.")
        await LeadService.generate_apollo_leads(lead_form, db)

        return UriResponse.custom_response(
            "Leads generation triggered successfully", 202, True
        )

    @staticmethod
    @LeadHelper.enforce_feature_limit(
        lambda lead_form: lead_form.get("user_id", ""), EndpointsEnum.LEAD_GEN.value
    )
    async def generate_apollo_leads(lead_form: dict, db: AsyncIOMotorDatabase):
        user_id = lead_form.get("user_id", "")
        if not user_id:
            raise Exception(
                f"No user_id provided for apollo leads gen for lead form {lead_form}"
            )

        limit_available, current_count = (
            await UriTaskManagerService.get_elapsed_leads_limit_and_count(user_id)
        )

        lead_form_type = lead_form.get("form_type")

        leads_to_create: Optional[List[Lead]] = []

        if not lead_form_type:
            raise ValueError("Empty lead form type.")
        elif lead_form_type == LeadFormTypeEnum.PERSON.value:
            leads_to_create = await ApolloService.handle_people_leads_gen(
                lead_form=lead_form, db=db
            )
        elif lead_form_type == LeadFormTypeEnum.ORGANIZATION.value:
            leads_to_create = await ApolloService.handle_organization_leads_gen(
                lead_form=lead_form, db=db
            )
        else:
            raise ValueError(
                f"Invalid lead form type in lead form {lead_form.get('lead_form_id')}."
            )

        if not leads_to_create:
            print("No leads found with your search criteria.")
            return
        print("Creating new leads......")
        response = await LeadRepository.multiple_create_leads(
            db=db,
            leads=(
                leads_to_create[:limit_available]
                if limit_available
                else leads_to_create
            ),
        )
        leads_count = len(response.get("responseData", {}).get("leads", []))
        if not leads_count:
            lead_names = (
                [f"{lead.first_name} {lead.last_name}" for lead in leads_to_create[:5]]
                if lead_form_type == LeadFormTypeEnum.PERSON.value
                else [
                    lead.company_name
                    for lead in leads_to_create[:5]
                    if lead.company_name
                ]
            )
            await LeadService.send_duplicate_apollo_leads_gen_notification(
                lead_form, lead_names
            )
            print("No new leads created, duplicates found.")
            return
        print(f"Leads created: {leads_count}")

        # Update user feature limit
        await UriTaskManagerService.update_user_feature_limit_specific_limit(
            user_id=lead_form.get("user_id", ""),
            url_path=EndpointsEnum.LEAD_GEN.value,
            count=leads_count + current_count,
        )

        # Handle notifications
        await LeadService.send_successful_apollo_leads_gen_notification(
            lead_form, leads_count
        )
        return response

    @staticmethod
    async def send_successful_apollo_leads_gen_notification(
        lead_form: dict, leads_count: int
    ):
        user_id, form_type = DictHelper.extract_multiple_keys(
            lead_form, ["user_id", "form_type"]
        )
        data_to_send = (
            await NotificationHelper.build_extended_lead_notification_payload(
                user_id, form_type, {"leadsCount": leads_count}
            )
        )

        # Send notification
        await NotificationService.send_lead_notification(
            data_to_send,
            UserNotificationQueueMessageTypeEnum.LEADS_GENERATED_SUCCESSFULLY,
        )

    @staticmethod
    async def send_duplicate_apollo_leads_gen_notification(
        lead_form: dict, lead_names: List[str]
    ):
        user_id, form_type = DictHelper.extract_multiple_keys(
            lead_form, ["user_id", "form_type"]
        )
        data_to_send = (
            await NotificationHelper.build_extended_lead_notification_payload(
                user_id, form_type, {"leadNames": lead_names}
            )
        )

        # Send notification
        await NotificationService.send_lead_notification(
            data_to_send, UserNotificationQueueMessageTypeEnum.DUPLICATE_LEADS_FOUND
        )

    @staticmethod
    async def start_realtime_monitoring(db: AsyncIOMotorDatabase, lead_form: dict) -> dict:
        """Start real-time monitoring for a conversational lead form using Browsercloud."""
        try:
            keywords = lead_form.get("keywords", [])
            buying_signals = lead_form.get("buying_signals", [])
            excluded_keywords = lead_form.get("excluded_keywords", [])
            location = lead_form.get("location")

            # Start monitoring tasks for all platforms
            tasks = await LeadService.browsercloud_service.start_platform_monitoring(
                keywords=keywords,
                buying_signals=buying_signals,
                excluded_keywords=excluded_keywords,
                location=location
            )

            return {
                "status": True,
                "message": "Real-time monitoring started successfully",
                "tasks": [task.dict() for task in tasks]
            }
        except Exception as e:
            return {
                "status": False,
                "message": f"Failed to start real-time monitoring: {str(e)}"
            }

    @staticmethod
    async def generate_conversational_leads_background_job(db: AsyncIOMotorDatabase):
        """Now handles both real-time and legacy conversational leads."""
        async for batch in LeadFormRepository.fetch_lead_forms_in_batches(
            db=db, filter={"form_type": LeadFormTypeEnum.CONVERSATIONAL.value}
        ):
            # Start real-time monitoring for each form
            monitoring_tasks = [
                LeadService.start_realtime_monitoring(db, lead_form)
                for lead_form in batch
                if lead_form.get("auto_generate", False)
            ]

            # Process existing pre-stored leads
            legacy_tasks = [
                LeadService.expose_pre_stored_leads(db, lead_form.get("user_id", ""))
                for lead_form in batch
            ]

            results = await asyncio.gather(*(monitoring_tasks + legacy_tasks), return_exceptions=True)

            # Handle errors
            for lead_form, result in zip(batch, results):
                if isinstance(result, Exception):
                    user_id = lead_form.get("user_id", "")
                    log_data = {
                        "userId": user_id,
                        "exceptionDate": datetime.utcnow().isoformat(),
                        "method": "POST",
                        "status": 500,
                        "exception": "".join(
                            traceback.format_exception(
                                type(result), result, result.__traceback__
                            )
                        ),
                        "serviceType": MicroServiceTypeEnum.URI_INSIGHTS.value,
                    }
                    await ExceptionLogQueueProducerService.publish_exception_log(
                        log_data
                    )

    @staticmethod
    async def run_lead_generation_chain(db):
        print("\n\nStart: generate_leads_background_job")
        await LeadService.generate_leads_background_job(db=db)

        print("\n\nNext: generate_conversational_leads")
        await LeadService.generate_conversational_leads_background_job(db=db)

        print("\n\nNext: generate_apollo_person_leads_background_job")
        await LeadService.generate_apollo_person_leads_background_job(db=db)

        print("\n\nNext: generate_apollo_organization_leads_background_job")
        await LeadService.generate_apollo_organization_leads_background_job(db=db)

        print("Completed all lead generation tasks.")

    @staticmethod
    async def update_all_user_feature_limits(db: AsyncIOMotorDatabase):
        """
        Update all user feature limits for lead generation.
        """
        async for batch in LeadFormRepository.fetch_lead_forms_in_batches(
            db=db, filter={"form_type": LeadFormTypeEnum.ORGANIZATION.value}
        ):
            await asyncio.gather(
                *[
                    LeadService.update_user_feature_limit_with_lead_count(db, lead_form)
                    for lead_form in batch
                    if lead_form.get("user_id")
                ]
            )

    @staticmethod
    async def update_user_feature_limit_with_lead_count(
        db: AsyncIOMotorDatabase, lead_form: dict
    ):
        """
        Update all user feature limits for lead generation.
        """
        user_id = lead_form.get("user_id", "")
        if not user_id:
            print("No user ID found in lead form: ", lead_form)
            return

        feature_limit_response = await UriTaskManagerService.get_user_feature_limit(
            user_id
        )

        if not feature_limit_response or not feature_limit_response.get(
            "status", False
        ):
            print("No feature limit found for user: ", user_id)
            return
        feature_limit = feature_limit_response.get("responseData", {})
        if not feature_limit.get("status", False):
            print("No feature limit data found for user: ", user_id)
            return
        start_date = feature_limit.get("data", {}).get("createdAt", "")
        current_count = (
            await LeadRepository.get_leads_count_for_subscription_period(
                db=db, assigned_to=user_id, start_date=start_date
            )
        ).get("responseData", 0)
        await UriTaskManagerService.update_user_feature_limit_specific_limit(
            user_id=user_id,
            url_path=EndpointsEnum.LEAD_GEN.value,
            count=current_count,
        )

    @staticmethod
    async def expose_pre_stored_leads(db: AsyncIOMotorDatabase, user_id: str) -> int:
        print("User_ID: ", user_id)
        limit_available, current_count = (
            await UriTaskManagerService.get_elapsed_leads_limit_and_count(user_id)
        )

        if limit_available == 0:
            raise FeatureLimitExceeded()

        leads = (
            (
                await LeadRepository.get_leads_by_filters(
                    db=db,
                    filters=GetLeadsByFiltersRequest(
                        assigned_to=user_id, is_pre_stored=True
                    ),
                )
            )
            .get("responseData", {})
            .get("data")
        )
        trimmed_leads = leads[:limit_available]
        update_tasks = []
        notification_tasks = []
        cache_key = CacheHelper.generate_cache_key(f"should_send_lead_email_{user_id}")

        for lead in trimmed_leads:
            notification_tasks.append(LeadService.send_lead_email(db, lead, cache_key))
            update_tasks.append(
                LeadRepository.update_lead(
                    db=db,
                    lead_id=lead["lead_id"],
                    updates=LeadUpdate(is_pre_stored=False),
                )
            )

        leads_count = len(trimmed_leads)

        # Concurrently update leads to reveal them to the user
        await asyncio.gather(*update_tasks)

        # Update user feature limit
        await UriTaskManagerService.update_user_feature_limit_specific_limit(
            user_id=user_id,
            url_path=EndpointsEnum.LEAD_GEN.value,
            count=leads_count + current_count,
        )

        # Concurrently handle python asynchronous tasks
        await asyncio.gather(*notification_tasks)

        return leads_count

    @staticmethod
    async def generate_follow_up_message(lead: dict, lead_form: dict) -> str:
        ai_response_guide = lead_form.get("ai_response_guide")

        def safe_dumps(obj):
            try:
                return json.dumps(obj, default=str, ensure_ascii=False)
            except Exception as e:
                print(f"JSON serialization failed: {e}")
                return {}  # fallback to empty object if it really fails

        if ai_response_guide:
            print("AI response guide is present.")
            prompt = ai_response_guide + safe_dumps(lead) + safe_dumps(lead_form)
        else:
            print("AI response guide is not present.")
            prompt = LeadFollowUpMessagePromptEnum.LEAD_CAPTURE.value.format(
                business_info=lead_form, lead_post=lead
            )

        ai_model = AIService.build_ai_model([AIService.construct_user_prompt(prompt)])

        ai_full_response = await AIService.structured_chat_completion(ai_model)

        follow_up_message = AIService.extract_ai_result(ai_full_response)

        return follow_up_message.text

    @staticmethod
    async def _attach_follow_ups(
        leads: list[dict], lead_form: dict
    ) -> list[LeadCreate]:
        """
        Given a list of LeadCreate objects, generate follow-up messages
        concurrently and return only valid leads with follow-ups attached.
        """
        lead_form_copy = lead_form.copy()
        for key, value in lead_form_copy.items():
            if isinstance(value, datetime):
                del lead_form[key]

        print("Lead form: ", lead_form)
        
        follow_up_tasks = [
            LeadService.generate_follow_up_message(lead, lead_form) for lead in leads
        ]
        follow_up_results = await asyncio.gather(
            *follow_up_tasks, return_exceptions=True
        )

        print("Follow up results: ", follow_up_results)

        ready_leads = []
        for lead, follow_up in zip(leads, follow_up_results):
            if not isinstance(follow_up, Exception):
                lead_to_create = LeadCreate(**lead)
                lead_to_create.follow_up_message = follow_up
                ready_leads.append(lead_to_create)

        return ready_leads
