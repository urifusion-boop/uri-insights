from fastapi import APIRouter, Depends, Query, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, List
from fastapi.encoders import jsonable_encoder
import logging
import uuid

from app.dependencies import get_db_dependency
from app.domain.responses.uri_response import UriResponse
from app.services.LazarusService import LazarusService
from app.services.LazarusMonitoringService import LazarusMonitoringService
from app.repository.LazarusRepository import LazarusRepository
from app.domain.schemas.lazarus_schema import (
    FocusContactCreate,
    CompanyMonitorCreate,
    LazarusMonitoringStatusEnum,
    LazarusAlertStatusEnum,
    LazarusMonitorTypeEnum,
    CSVUploadRow,
    DetectionRulesUpdate,
    KeywordExtractionRequest,
    KeywordExtractionResult,
)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

router = APIRouter()

# Log all registered routes when router is loaded
@router.on_event("startup")
async def log_routes():
    logger.info("=" * 80)
    logger.info("LAZARUS ROUTER LOADED - Registered Routes:")
    for route in router.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            methods = ','.join(route.methods) if route.methods else 'ANY'
            logger.info(f"  {methods:10} {route.path}")
    logger.info("=" * 80)


# ============ FOCUS CONTACTS ============
@router.post("/focus-contacts/add")
async def add_focus_contact(
    contact: FocusContactCreate,
    user_id: str = Query(...),
    source_lead_id: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Add a new focus contact to monitor
    PRD Section 4.1: Focus Contact Monitoring
    """
    result = await LazarusService.add_focus_contact(
        db, user_id, contact, source_lead_id
    )

    if not result["success"]:
        return UriResponse.custom_response(result["message"], 400)

    return UriResponse.custom_response(
        result["message"],
        200,
        {
            "focus_id": result.get("focus_id"),
            "slots_used": result.get("slots_used"),
            "slots_available": result.get("slots_available"),
            "contact": jsonable_encoder(result.get("contact")) if result.get("contact") else None,
        },
    )


@router.get("/focus-contacts")
async def get_focus_contacts(
    user_id: str = Query(...),
    status: Optional[LazarusMonitoringStatusEnum] = Query(None),
    skip: int = Query(0),
    limit: int = Query(50),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Get all focus contacts for a user"""
    from app.repository.LazarusRepository import LazarusRepository

    contacts = await LazarusRepository.get_focus_contacts_by_user(
        db, user_id, status, skip, limit
    )

    # Debug: Check if twitter_data is present
    for c in contacts:
        if c.twitter_handle:
            logger.info(f"[GET CONTACTS] {c.name} - twitter_handle: {c.twitter_handle}, twitter_data present: {c.twitter_data is not None}")
            if c.twitter_data:
                logger.info(f"[GET CONTACTS] twitter_data keys: {list(c.twitter_data.keys())}")
                logger.info(f"[GET CONTACTS] followers: {c.twitter_data.get('followers')}")

    return UriResponse.custom_response(
        message="Focus contacts retrieved successfully",
        error_code=200,
        success=True,
        data=[jsonable_encoder(c) for c in contacts],
    )


@router.put("/focus-contacts/{focus_id}")
async def update_focus_contact(
    focus_id: str,
    update_data: FocusContactCreate,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Update focus contact details (name, social_handle, keywords, etc.)"""
    try:
        # Convert Pydantic model to dict and filter out None values
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}

        # Don't allow changing user_id
        if "user_id" in update_dict:
            del update_dict["user_id"]

        updated_contact = await LazarusRepository.update_focus_contact(
            db, focus_id, user_id, update_dict
        )

        if not updated_contact:
            return UriResponse.custom_response(
                message="Focus contact not found or you don't have permission to update it",
                error_code=404,
                success=False
            )

        return UriResponse.custom_response(
            message="Focus contact updated successfully",
            error_code=200,
            success=True,
            data=jsonable_encoder(updated_contact)
        )
    except Exception as e:
        logger.error(f"Error updating focus contact: {str(e)}")
        return UriResponse.custom_response(
            message=f"Failed to update focus contact: {str(e)}",
            error_code=500,
            success=False
        )


@router.delete("/focus-contacts/{focus_id}")
async def remove_focus_contact(
    focus_id: str,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Remove a focus contact"""
    result = await LazarusService.remove_focus_contact(db, user_id, focus_id)

    if not result["success"]:
        return UriResponse.custom_response(result["message"], 404)

    return UriResponse.custom_response(result["message"], 200)


@router.put("/focus-contacts/{focus_id}/pause")
async def pause_focus_contact(
    focus_id: str,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Pause monitoring for a focus contact"""
    result = await LazarusService.pause_focus_contact(db, user_id, focus_id)

    if not result["success"]:
        return UriResponse.custom_response(result["message"], 404)

    return UriResponse.custom_response(result["message"], 200)


@router.put("/focus-contacts/{focus_id}/resume")
async def resume_focus_contact(
    focus_id: str,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Resume monitoring for a paused focus contact"""
    result = await LazarusService.resume_focus_contact(db, user_id, focus_id)

    if not result["success"]:
        return UriResponse.custom_response(result["message"], 404)

    return UriResponse.custom_response(result["message"], 200)


@router.post("/focus-contacts/{focus_id}/enrich")
async def enrich_focus_contact(
    focus_id: str,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Manually trigger LinkedIn profile enrichment for a focus contact
    Phase 1: Contact Enrichment - Extracts email, phone, and profile data
    """
    from app.repository.LazarusRepository import LazarusRepository
    from app.services.LinkedInProfileScraperService import LinkedInProfileScraperService
    from datetime import datetime

    # Get contact
    contact = await LazarusRepository.get_focus_contact_by_id(db, focus_id, user_id)
    if not contact:
        return UriResponse.custom_response("Focus contact not found", 404)

    # Check if LinkedIn URL exists
    if not contact.linkedin_url:
        return UriResponse.custom_response(
            message="No LinkedIn URL found for this contact",
            error_code=400,
            success=False
        )

    logger.info(f"🔍 Enriching contact: {contact.name} ({focus_id})")

    # Update status to pending
    await LazarusRepository.update_focus_contact(
        db, focus_id, user_id, {"enrichment_status": "pending"}
    )

    # Call LinkedIn Profile Scraper
    scraper_service = LinkedInProfileScraperService()
    enrichment_result = await scraper_service.enrich_profile(
        linkedin_url=contact.linkedin_url,
        timeout_seconds=90
    )

    if not enrichment_result.get("success"):
        # Mark as failed
        await LazarusRepository.update_focus_contact(
            db, focus_id, user_id, {
                "enrichment_status": "failed",
                "enriched_at": datetime.utcnow()
            }
        )
        return UriResponse.custom_response(
            message=f"Enrichment failed: {enrichment_result.get('error_message', 'Unknown error')}",
            error_code=500,
            success=False
        )

    # Extract enriched data
    profile_data = enrichment_result.get("profile_data", {})

    # Transform skills, languages, etc. from [{"title": "X"}] to ["X"] format
    skills = profile_data.get("skills", [])
    if skills and isinstance(skills, list) and len(skills) > 0 and isinstance(skills[0], dict):
        skills = [skill.get("title", skill) for skill in skills if skill]

    languages = profile_data.get("languages", [])
    if languages and isinstance(languages, list) and len(languages) > 0 and isinstance(languages[0], dict):
        languages = [lang.get("title", lang) for lang in languages if lang]

    # Update contact with enriched data
    enrichment_update = {
        "email": enrichment_result.get("email"),
        "phone": enrichment_result.get("phone"),
        "linkedin_url": contact.linkedin_url,  # Preserve the LinkedIn URL we used to scrape
        "profile_photo": profile_data.get("profile_photo"),
        "headline": profile_data.get("headline"),
        "location": profile_data.get("location"),
        "connections_count": profile_data.get("connections_count"),
        "about": profile_data.get("about"),
        "work_experience": profile_data.get("work_experience"),
        "education": profile_data.get("education"),
        "skills": skills if skills else None,
        "languages": languages if languages else None,
        "certifications": profile_data.get("certifications"),
        "enriched_at": datetime.utcnow(),
        "enrichment_status": "completed"
    }

    # Update current_company if we got it from enrichment
    if profile_data.get("current_company"):
        enrichment_update["current_company"] = profile_data.get("current_company")

    # Remove None values (like auto-enrichment does)
    enrichment_update = {k: v for k, v in enrichment_update.items() if v is not None}

    updated = await LazarusRepository.update_focus_contact(
        db, focus_id, user_id, enrichment_update
    )

    if not updated:
        return UriResponse.custom_response("Failed to save enrichment data", 500)

    logger.info(f"✅ Successfully enriched contact: {contact.name}")
    if enrichment_result.get("email"):
        logger.info(f"   📧 Email: {enrichment_result.get('email')}")
    if enrichment_result.get("phone"):
        logger.info(f"   📱 Phone: {enrichment_result.get('phone')}")

    return UriResponse.custom_response(
        message="Contact enriched successfully",
        error_code=200,
        success=True,
        data={
            "email": enrichment_result.get("email"),
            "phone": enrichment_result.get("phone"),
            "profile_data": profile_data
        }
    )


@router.post("/focus-contacts/{focus_id}/enrich-twitter")
async def enrich_twitter_profile(
    focus_id: str,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Manually trigger Twitter profile enrichment for a focus contact
    Gets profile data + 5 recent posts for enrichment snapshot
    """
    from app.services.TwitterEnrichmentService import TwitterEnrichmentService
    from datetime import datetime

    # Get focus contact
    contact = await LazarusRepository.get_focus_contact_by_id(db, focus_id, user_id)
    if not contact:
        return UriResponse.custom_response("Focus contact not found", 404)

    # Check if Twitter URL or handle exists
    twitter_identifier = contact.twitter_url or contact.twitter_handle
    if not twitter_identifier:
        return UriResponse.custom_response(
            message="No Twitter URL or handle found for this contact",
            error_code=400,
            success=False
        )

    logger.info(f"🐦 Enriching Twitter profile: {contact.name} ({twitter_identifier})")

    # Update status to pending
    await LazarusRepository.update_focus_contact(
        db, focus_id, user_id, {"enrichment_status": "pending"}
    )

    # Call Twitter Enrichment Service
    twitter_service = TwitterEnrichmentService()
    profile_data = await twitter_service.enrich_profile(
        twitter_url_or_handle=twitter_identifier,
        max_posts=5  # Just 5 posts for enrichment
    )

    if not profile_data:
        # Mark as failed
        await LazarusRepository.update_focus_contact(
            db, focus_id, user_id, {
                "enrichment_status": "failed",
                "enriched_at": datetime.utcnow()
            }
        )
        return UriResponse.custom_response(
            message="Twitter enrichment failed. Please check the Twitter handle/URL.",
            error_code=500,
            success=False
        )

    # Transform to FocusContact format
    enrichment_data = twitter_service.transform_to_focus_contact_data(profile_data)

    # Update contact with enriched data
    updated = await LazarusRepository.update_focus_contact(
        db, focus_id, user_id, enrichment_data
    )

    if not updated:
        return UriResponse.custom_response("Failed to save Twitter enrichment data", 500)

    logger.info(f"✅ Successfully enriched Twitter profile: {contact.name}")
    logger.info(f"   👤 Handle: @{enrichment_data.get('twitter_handle')}")
    logger.info(f"   👥 Followers: {enrichment_data.get('twitter_data', {}).get('followers', 0):,}")

    return UriResponse.custom_response(
        message="Twitter profile enriched successfully",
        error_code=200,
        success=True,
        data={
            "twitter_handle": enrichment_data.get("twitter_handle"),
            "twitter_data": enrichment_data.get("twitter_data")
        }
    )


@router.post("/company-monitors/{monitor_id}/enrich")
async def enrich_company_monitor(
    monitor_id: str,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Manually trigger LinkedIn company enrichment for a company monitor
    Extracts company details, employees, followers, funding, etc.
    """
    from app.repository.LazarusRepository import LazarusRepository
    from app.services.BrightDataCompanyEnrichmentService import BrightDataCompanyEnrichmentService
    from datetime import datetime

    # Get company monitor
    monitor = await LazarusRepository.get_company_monitor_by_id(db, monitor_id, user_id)
    if not monitor:
        return UriResponse.custom_response("Company monitor not found", 404)

    # Check if LinkedIn URL exists
    if not monitor.linkedin_url:
        return UriResponse.custom_response(
            "No LinkedIn URL found for this company. Please add a LinkedIn company URL first.",
            error_code=400,
            success=False
        )

    logger.info(f"🔧 Enriching company monitor: {monitor.company_name} (LinkedIn: {monitor.linkedin_url})")

    # Update status to pending
    await LazarusRepository.update_company_monitor(
        db, monitor_id, user_id, {"enrichment_status": "pending"}
    )

    # Call Bright Data Company Enrichment Service
    enrichment_service = BrightDataCompanyEnrichmentService()
    enrichment_result = await enrichment_service.enrich_company(
        linkedin_url=monitor.linkedin_url,
        timeout_seconds=90
    )

    if not enrichment_result.get("success"):
        # Mark as failed
        await LazarusRepository.update_company_monitor(
            db, monitor_id, user_id, {
                "enrichment_status": "failed",
                "enriched_at": datetime.utcnow()
            }
        )
        return UriResponse.custom_response(
            message=f"Enrichment failed: {enrichment_result.get('error_message', 'Unknown error')}",
            error_code=500,
            success=False
        )

    # Update company monitor with enriched data
    enrichment_update = {
        "about": enrichment_result.get("about"),
        "slogan": enrichment_result.get("slogan"),
        "description": enrichment_result.get("description"),
        "specialties": enrichment_result.get("specialties", []),
        "organization_type": enrichment_result.get("organization_type"),
        "company_size": enrichment_result.get("company_size"),
        "industries": enrichment_result.get("industries", []),
        "founded": enrichment_result.get("founded"),
        "country_code": enrichment_result.get("country_code"),
        "headquarters": enrichment_result.get("headquarters"),
        "followers": enrichment_result.get("followers"),
        "employees": enrichment_result.get("employees"),
        "logo": enrichment_result.get("logo"),
        "company_image": enrichment_result.get("company_image"),
        "enriched_at": datetime.utcnow(),
        "enrichment_status": "completed"
    }

    updated = await LazarusRepository.update_company_monitor(
        db, monitor_id, user_id, enrichment_update
    )

    if not updated:
        return UriResponse.custom_response("Failed to save enrichment data", 500)

    logger.info(f"✅ Successfully enriched company: {monitor.company_name}")

    return UriResponse.custom_response(
        message="Company enriched successfully",
        error_code=200,
        success=True,
        data={
            "company_name": enrichment_result.get("name"),
            "about": enrichment_result.get("about"),
            "employees": enrichment_result.get("employees"),
            "followers": enrichment_result.get("followers"),
            "headquarters": enrichment_result.get("headquarters")
        }
    )


@router.post("/focus-contacts/{focus_id}/reveal-email")
async def reveal_focus_contact_email(
    focus_id: str,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Reveal email for focus contact using Apollo (charges 1 credit)
    Similar to individual leads reveal functionality
    """
    from app.repository.LazarusRepository import LazarusRepository
    from app.services.ApolloService import ApolloService
    from app.services.uri_microservices.UriTaskManagerService import UriTaskManagerService
    from datetime import datetime

    # Get contact
    contact = await LazarusRepository.get_focus_contact_by_id(db, focus_id, user_id)
    if not contact:
        return UriResponse.custom_response("Contact not found", 404)

    # Check if email already revealed
    if contact.email and contact.email != "PROCESSING" and contact.email != "UNAVAILABLE":
        return UriResponse.custom_response(
            message="Email already revealed",
            error_code=200,
            success=True,
            data={"email": contact.email}
        )

    # Check if LinkedIn URL exists
    if not contact.linkedin_url:
        return UriResponse.custom_response(
            "No LinkedIn URL found for this contact",
            error_code=400,
            success=False
        )

    # Check credits (1 credit for email)
    try:
        credit_check = await UriTaskManagerService.check_payment_balance(
            user_id=user_id,
            action_type="ENRICHMENT_EMAIL",
            payment_mode="CREDITS",
            quantity=1
        )
        if not credit_check.get("responseData", {}).get("hasSufficientBalance"):
            return UriResponse.custom_response(
                "Insufficient credits for email reveal",
                error_code=402,
                success=False
            )
    except Exception as e:
        logger.error(f"Credit check failed: {str(e)}")
        return UriResponse.custom_response(f"Credit check failed: {str(e)}", 500, success=False)

    # Call Apollo to reveal email
    try:
        temp_lead = {"linkedin_url": contact.linkedin_url, "username": contact.name}
        apollo_result = await ApolloService.enrich_person(temp_lead, reveal_email=True)

        person_data = apollo_result.get("person", {})
        email = person_data.get("email")

        if not email:
            email = "UNAVAILABLE"

        # Update contact with email
        await LazarusRepository.update_focus_contact(
            db, focus_id, user_id, {"email": email}
        )

        # Deduct credits
        await UriTaskManagerService.deduct_payment(
            user_id=user_id,
            action_type="ENRICHMENT_EMAIL",
            payment_mode="CREDITS",
            quantity=1,
            reference=f"lazarus_email_reveal_{focus_id}"
        )

        logger.info(f"✅ Email revealed for {contact.name}: {email}")

        return UriResponse.custom_response(
            message="Email revealed successfully",
            error_code=200,
            success=True,
            data={"email": email}
        )

    except Exception as e:
        logger.error(f"Apollo email reveal failed: {str(e)}")
        return UriResponse.custom_response(
            f"Failed to reveal email: {str(e)}",
            error_code=500,
            success=False
        )


@router.post("/focus-contacts/{focus_id}/reveal-phone")
async def reveal_focus_contact_phone(
    focus_id: str,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Reveal phone for focus contact using Apollo (charges 7 credits)
    Similar to individual leads reveal functionality
    """
    from app.repository.LazarusRepository import LazarusRepository
    from app.services.ApolloService import ApolloService
    from app.services.uri_microservices.UriTaskManagerService import UriTaskManagerService
    from app.core.config import settings
    from datetime import datetime

    # Get contact
    contact = await LazarusRepository.get_focus_contact_by_id(db, focus_id, user_id)
    if not contact:
        return UriResponse.custom_response("Contact not found", 404)

    # Check if phone already revealed
    if contact.phone and contact.phone != "PROCESSING" and contact.phone != "UNAVAILABLE":
        return UriResponse.custom_response(
            message="Phone already revealed",
            error_code=200,
            success=True,
            data={"phone": contact.phone}
        )

    # Check if LinkedIn URL exists
    if not contact.linkedin_url:
        return UriResponse.custom_response(
            "No LinkedIn URL found for this contact",
            error_code=400,
            success=False
        )

    # Check credits (7 credits for phone)
    try:
        credit_check = await UriTaskManagerService.check_payment_balance(
            user_id=user_id,
            action_type="ENRICHMENT_PHONE",
            payment_mode="CREDITS",
            quantity=1
        )
        if not credit_check.get("responseData", {}).get("hasSufficientBalance"):
            return UriResponse.custom_response(
                "Insufficient credits for phone reveal (7 credits required)",
                error_code=402,
                success=False
            )
    except Exception as e:
        logger.error(f"Credit check failed: {str(e)}")
        return UriResponse.custom_response(f"Credit check failed: {str(e)}", 500, success=False)

    # Set phone to PROCESSING
    await LazarusRepository.update_focus_contact(
        db, focus_id, user_id, {"phone": "PROCESSING"}
    )

    # Call Apollo to reveal phone (async via webhook)
    try:
        webhook_url = f"{settings.URI_GATEWAY_BASE_API_URL}/uri-insights/webhooks/apollo-webhook"
        temp_lead = {"linkedin_url": contact.linkedin_url, "username": contact.name, "focus_id": focus_id}
        apollo_result = await ApolloService.enrich_person(temp_lead, reveal_phone=True, webhook_url=webhook_url)

        # Extract apollo_id from result and save it to focus contact for webhook lookup
        apollo_id = apollo_result.get("person", {}).get("id")
        if apollo_id:
            await LazarusRepository.update_focus_contact(
                db, focus_id, user_id, {"apollo_id": apollo_id}
            )
            logger.info(f"✅ Saved apollo_id {apollo_id} to focus contact for webhook")

        # Deduct credits
        await UriTaskManagerService.deduct_payment(
            user_id=user_id,
            action_type="ENRICHMENT_PHONE",
            payment_mode="CREDITS",
            quantity=1,
            reference=f"lazarus_phone_reveal_{focus_id}"
        )

        logger.info(f"✅ Phone reveal request sent for {contact.name} (awaiting webhook)")

        return UriResponse.custom_response(
            message="Phone reveal in progress (will be available shortly)",
            error_code=200,
            success=True,
            data={"phone": "PROCESSING"}
        )

    except Exception as e:
        logger.error(f"Apollo phone reveal failed: {str(e)}")
        await LazarusRepository.update_focus_contact(
            db, focus_id, user_id, {"phone": None}
        )
        return UriResponse.custom_response(
            f"Failed to reveal phone: {str(e)}",
            error_code=500,
            success=False
        )


@router.get("/focus-contacts/{focus_id}/detail")
async def get_focus_contact_detail(
    focus_id: str,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Get full contact details including enrichment data
    Phase 1: Contact Detail Page
    """
    from app.repository.LazarusRepository import LazarusRepository

    logger.info(f"🔍 Looking for focus contact: focus_id={focus_id}, user_id={user_id}")
    contact = await LazarusRepository.get_focus_contact_by_id(db, focus_id, user_id)

    if not contact:
        logger.warning(f"❌ Focus contact not found: focus_id={focus_id}, user_id={user_id}")
        # Check if it exists for any user (debugging)
        any_contact = await db["focus_contacts"].find_one({"focus_id": focus_id})
        if any_contact:
            logger.warning(f"⚠️ Contact exists but for different user: {any_contact.get('user_id')}")
        else:
            logger.warning(f"⚠️ Contact does not exist in database at all")
        return UriResponse.custom_response("Focus contact not found", 404)

    logger.info(f"✅ Contact found: {contact.name}")
    return UriResponse.custom_response(
        message="Contact details retrieved successfully",
        error_code=200,
        success=True,
        data=jsonable_encoder(contact)
    )


# ============ DIAGNOSTIC TEST ENDPOINTS ============
@router.get("/diagnostic/ping")
async def diagnostic_ping():
    """Ultra-simple test endpoint - no dependencies, just returns success"""
    logger.info("🏓 DIAGNOSTIC PING endpoint hit!")
    return {
        "success": True,
        "message": "Lazarus router is alive!",
        "endpoint": "/diagnostic/ping"
    }


@router.patch("/diagnostic/test-patch/{item_id}")
async def diagnostic_test_patch(item_id: str, value: int = Query(default=1)):
    """Test PATCH method with path param and query param"""
    logger.info(f"🧪 DIAGNOSTIC TEST-PATCH hit! item_id={item_id}, value={value}")
    return {
        "success": True,
        "message": "PATCH method works!",
        "item_id": item_id,
        "value": value
    }


@router.put("/focus-contacts/{focus_id}/scanfrequency")
async def update_focus_contact_scan_frequency(
    focus_id: str,
    scan_frequency_days: int = Query(..., ge=1, le=30),
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Update scan frequency for a focus contact (1-30 days)"""
    logger.info("=" * 80)
    logger.info(f"🔥 SCANFREQUENCY ENDPOINT HIT!")
    logger.info(f"  focus_id: {focus_id}")
    logger.info(f"  user_id: {user_id}")
    logger.info(f"  scan_frequency_days: {scan_frequency_days}")
    logger.info("=" * 80)
    print(f"🔍 [BACKEND] scan-frequency endpoint HIT! focus_id={focus_id}, user_id={user_id}, days={scan_frequency_days}")
    from app.repository.LazarusRepository import LazarusRepository
    from datetime import datetime, timedelta

    # Get contact to calculate new next_scan_date
    contact = await LazarusRepository.get_focus_contact_by_id(db, focus_id, user_id)
    if not contact:
        return UriResponse.custom_response("Focus contact not found", 404)

    # Update scan frequency and recalculate next scan
    updated = await LazarusRepository.update_focus_contact(
        db,
        focus_id,
        user_id,
        {
            "scan_frequency_days": scan_frequency_days,
            "next_scan_date": datetime.utcnow() + timedelta(days=scan_frequency_days),
        },
    )

    if not updated:
        return UriResponse.custom_response("Failed to update scan frequency", 500)

    return UriResponse.custom_response(
        message=f"Scan frequency updated to every {scan_frequency_days} days",
        error_code=200,
        success=True,
        data={"scan_frequency_days": scan_frequency_days}
    )


# ============ COMPANY MONITORS ============
@router.post("/company-monitors/add")
async def add_company_monitor(
    monitor: CompanyMonitorCreate,
    user_id: str = Query(...),
    source_lead_id: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Add a new company monitor
    PRD Section 3 Track A: Company Monitoring
    """
    result = await LazarusService.add_company_monitor(
        db, user_id, monitor, source_lead_id
    )

    if not result["success"]:
        return UriResponse.custom_response(result["message"], 400)

    return UriResponse.custom_response(
        result["message"],
        200,
        {
            "monitor_id": result.get("monitor_id"),
            "slots_used": result.get("slots_used"),
            "slots_available": result.get("slots_available"),
        },
    )


@router.get("/company-monitors")
async def get_company_monitors(
    user_id: str = Query(...),
    status: Optional[LazarusMonitoringStatusEnum] = Query(None),
    skip: int = Query(0),
    limit: int = Query(50),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Get all company monitors for a user"""
    from app.repository.LazarusRepository import LazarusRepository

    monitors = await LazarusRepository.get_company_monitors_by_user(
        db, user_id, status, skip, limit
    )

    return UriResponse.custom_response(
        message="Company monitors retrieved successfully",
        error_code=200,
        success=True,
        data=[jsonable_encoder(m) for m in monitors],
    )


@router.delete("/company-monitors/{monitor_id}")
async def remove_company_monitor(
    monitor_id: str,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Remove a company monitor"""
    result = await LazarusService.remove_company_monitor(db, user_id, monitor_id)

    if not result["success"]:
        return UriResponse.custom_response(result["message"], 404)

    return UriResponse.custom_response(result["message"], 200)


@router.put("/company-monitors/{monitor_id}/scanfrequency")
async def update_company_monitor_scan_frequency(
    monitor_id: str,
    scan_frequency_days: int = Query(..., ge=1, le=30),
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Update scan frequency for a company monitor (1-30 days)"""
    from app.repository.LazarusRepository import LazarusRepository
    from datetime import datetime, timedelta

    # Get monitor to calculate new next_scan_date
    monitor = await LazarusRepository.get_company_monitor_by_id(db, monitor_id, user_id)
    if not monitor:
        return UriResponse.custom_response("Company monitor not found", 404)

    # Update scan frequency and recalculate next scan
    updated = await LazarusRepository.update_company_monitor(
        db,
        monitor_id,
        user_id,
        {
            "scan_frequency_days": scan_frequency_days,
            "next_scan_date": datetime.utcnow() + timedelta(days=scan_frequency_days),
        },
    )

    if not updated:
        return UriResponse.custom_response("Failed to update scan frequency", 500)

    return UriResponse.custom_response(
        message=f"Scan frequency updated to every {scan_frequency_days} days",
        error_code=200,
        success=True,
        data={"scan_frequency_days": scan_frequency_days}
    )


# ============ BULK CSV UPLOAD ============
@router.post("/bulk-upload")
async def bulk_upload_csv(
    csv_rows: List[CSVUploadRow],
    user_id: str = Query(...),
    auto_enrich: bool = Query(False, description="Auto-trigger LinkedIn enrichment for all contacts with LinkedIn URLs"),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Bulk upload focus contacts/companies from CSV
    PRD Section 4.2: Bulk Upload via CSV

    Features:
    - Accepts full URLs or handles for social_handle (auto-parsed)
    - Supports LinkedIn, Twitter/X, Facebook, Instagram
    - Optional auto-enrichment for LinkedIn profiles (email, phone, profile data)
    - Duplicate detection based on social URLs
    - Returns detailed feedback on URL parsing and normalization
    """
    result = await LazarusService.bulk_upload_from_csv(db, user_id, csv_rows, auto_enrich)

    return UriResponse.custom_response(
        message=result["message"],
        error_code=200,
        success=True,
        data={
            "added_count": result.get("added_count"),
            "failed_count": result.get("failed_count"),
            "enrichment_queued_count": result.get("enrichment_queued_count", 0),
            "duplicate_count": result.get("duplicate_count", 0),
            "errors": result.get("errors", []),
            "uploaded_contacts": result.get("uploaded_contacts", []),
        },
    )


# ============ ALERTS ============
@router.get("/alerts")
async def get_alerts(
    user_id: str = Query(...),
    status: Optional[LazarusAlertStatusEnum] = Query(None),
    skip: int = Query(0),
    limit: int = Query(50),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Get Lazarus alerts for a user"""
    alerts = await LazarusService.get_alerts(db, user_id, status, skip, limit)

    return UriResponse.custom_response(
        message="Alerts retrieved successfully",
        error_code=200,
        success=True,
        data=[jsonable_encoder(a) for a in alerts],
    )


@router.put("/alerts/{alert_id}/contacted")
async def mark_alert_contacted(
    alert_id: str,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Mark an alert as contacted"""
    result = await LazarusService.mark_alert_contacted(db, user_id, alert_id)

    if not result["success"]:
        return UriResponse.custom_response(result["message"], 404)

    return UriResponse.custom_response(result["message"], 200)


@router.put("/alerts/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: str,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Dismiss an alert"""
    result = await LazarusService.dismiss_alert(db, user_id, alert_id)

    if not result["success"]:
        return UriResponse.custom_response(result["message"], 404)

    return UriResponse.custom_response(result["message"], 200)


@router.put("/alerts/{alert_id}/viewed")
async def mark_alert_viewed(
    alert_id: str,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Mark an alert as viewed"""
    from app.repository.LazarusRepository import LazarusRepository
    from datetime import datetime

    updated = await LazarusRepository.update_alert_status(
        db, alert_id, user_id, LazarusAlertStatusEnum.VIEWED
    )

    if not updated:
        return UriResponse.custom_response("Alert not found", 404)

    return UriResponse.custom_response(
        message="Alert marked as viewed",
        error_code=200,
        success=True
    )


@router.put("/alerts/{alert_id}/resurrected")
async def mark_alert_resurrected(
    alert_id: str,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Mark an alert as resurrected (deal won!)
    Phase 1: Alert Workflow System
    """
    from app.repository.LazarusRepository import LazarusRepository
    from datetime import datetime

    # Get the alert
    alert = await LazarusRepository.get_alert_by_id(db, alert_id, user_id)
    if not alert:
        return UriResponse.custom_response("Alert not found", 404)

    # Update alert status - using ACTED as "resurrected" since schema doesn't have RESURRECTED enum
    # In future, we can add RESURRECTED to the enum
    updated = await LazarusRepository.update_alert_status(
        db, alert_id, user_id, LazarusAlertStatusEnum.ACTED
    )

    # Also mark the contact/monitor as resurrected (update metrics)
    if alert.source_type == LazarusMonitorTypeEnum.FOCUS_CONTACT:
        await LazarusRepository.update_focus_contact(
            db, alert.source_id, user_id, {
                "marked_dead_date": None,  # No longer dead!
                "monitoring_status": LazarusMonitoringStatusEnum.ACTIVE
            }
        )

    return UriResponse.custom_response(
        message="🎉 Alert marked as resurrected! Deal won!",
        error_code=200,
        success=True
    )


@router.post("/alerts/{alert_id}/outreach")
async def log_outreach(
    alert_id: str,
    user_id: str = Query(...),
    outreach_type: str = Query(...),  # "email", "phone", "whatsapp", "other"
    notes: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Log an outreach attempt for an alert
    Phase 1: Alert Workflow System
    """
    from app.repository.LazarusRepository import LazarusRepository
    from datetime import datetime

    # Get the alert
    alert = await LazarusRepository.get_alert_by_id(db, alert_id, user_id)
    if not alert:
        return UriResponse.custom_response("Alert not found", 404)

    # Create outreach log entry
    outreach_log = {
        "outreach_id": str(uuid.uuid4()),
        "alert_id": alert_id,
        "user_id": user_id,
        "source_type": alert.source_type,
        "source_id": alert.source_id,
        "outreach_type": outreach_type,
        "notes": notes,
        "timestamp": datetime.utcnow()
    }

    # Store in new collection: lazarus_outreach_log
    await db["lazarus_outreach_log"].insert_one(outreach_log)

    # Auto-mark alert as contacted if this is first outreach
    if alert.status == LazarusAlertStatusEnum.NEW or alert.status == LazarusAlertStatusEnum.VIEWED:
        await LazarusRepository.update_alert_status(
            db, alert_id, user_id, LazarusAlertStatusEnum.ACTED
        )

    logger.info(f"📞 Outreach logged: {outreach_type} for alert {alert_id}")

    return UriResponse.custom_response(
        message=f"Outreach logged successfully ({outreach_type})",
        error_code=200,
        success=True,
        data={"outreach_id": outreach_log["outreach_id"]}
    )


@router.put("/alerts/{alert_id}/assign")
async def assign_alert(
    alert_id: str,
    user_id: str = Query(...),
    assigned_to_user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Assign an alert to a team member
    Phase 2: Team Collaboration
    """
    from app.repository.LazarusRepository import LazarusRepository
    from datetime import datetime

    # Get the alert
    alert = await LazarusRepository.get_alert_by_id(db, alert_id, user_id)
    if not alert:
        return UriResponse.custom_response("Alert not found", 404)

    # Update assignment
    update_data = {
        "assigned_to": assigned_to_user_id,
        "assigned_at": datetime.utcnow(),
        "assigned_by": user_id
    }

    await db["lazarus_alerts"].update_one(
        {"alert_id": alert_id, "user_id": user_id},
        {"$set": update_data}
    )

    logger.info(f"👥 Alert {alert_id} assigned to {assigned_to_user_id} by {user_id}")

    return UriResponse.custom_response(
        message="Alert assigned successfully",
        error_code=200,
        success=True,
        data=update_data
    )


# ============ SLOTS & METRICS ============
@router.get("/slots")
async def get_user_slots(
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Get user's slot information"""
    slots = await LazarusService.get_user_slots(db, user_id)

    return UriResponse.custom_response(
        "Slots retrieved successfully", 200, jsonable_encoder(slots)
    )


@router.get("/notification-preferences")
async def get_notification_preferences(
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Get user's email notification preferences for Lazarus alerts
    Phase 2: Notification System
    """
    from app.repository.LazarusRepository import LazarusRepository

    slots = await LazarusRepository.get_or_create_slots(db, user_id)

    return UriResponse.custom_response(
        message="Notification preferences retrieved successfully",
        error_code=200,
        success=True,
        data={
            "email_notifications_enabled": slots.email_notifications_enabled,
            "notification_email": slots.notification_email
        }
    )


@router.put("/notification-preferences")
async def update_notification_preferences(
    user_id: str = Query(...),
    email_notifications_enabled: bool = Query(...),
    notification_email: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Update user's email notification preferences for Lazarus alerts
    Phase 2: Notification System
    """
    from app.repository.LazarusRepository import LazarusRepository

    # Update slots with new preferences
    update_data = {"email_notifications_enabled": email_notifications_enabled}
    if notification_email is not None:
        update_data["notification_email"] = notification_email

    await db["lazarus_slots"].update_one(
        {"user_id": user_id},
        {"$set": update_data},
        upsert=True
    )

    logger.info(f"📧 Notification preferences updated for user {user_id}: enabled={email_notifications_enabled}, email={notification_email}")

    return UriResponse.custom_response(
        message="Notification preferences updated successfully",
        error_code=200,
        success=True,
        data={
            "email_notifications_enabled": email_notifications_enabled,
            "notification_email": notification_email
        }
    )


@router.get("/metrics")
async def get_user_metrics(
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Get comprehensive Lazarus metrics for a user
    PRD Section 7: Success Metrics
    """
    try:
        metrics = await LazarusService.get_user_metrics(db, user_id)
        return UriResponse.custom_response(
            message="Metrics retrieved successfully",
            error_code=200,
            success=True,
            data=jsonable_encoder(metrics)
        )
    except Exception as e:
        print(f"❌ Error in get_user_metrics: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


@router.post("/upgrade-to-pro")
async def upgrade_to_pro(
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Upgrade user from BASIC (50 slots) to PRO (500 slots)"""
    result = await LazarusService.upgrade_to_pro(db, user_id)

    if not result["success"]:
        return UriResponse.custom_response(result["message"], 400)

    return UriResponse.custom_response(
        result["message"],
        200,
        {
            "max_slots": result.get("max_slots"),
            "plan_type": result.get("plan_type"),
        },
    )


# ============ LEAD INTEGRATION ============
@router.put("/leads/{lead_id}/mark-dead")
async def mark_lead_as_dead(
    lead_id: str,
    user_id: str = Query(...),
    reason: str = Query(...),
    auto_monitor: bool = Query(False),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Mark a lead as DEAD
    Optionally auto-add to Lazarus monitoring
    """
    result = await LazarusService.mark_lead_as_dead(
        db, user_id, lead_id, reason, auto_monitor
    )

    if not result["success"]:
        return UriResponse.custom_response(result["message"], 404)

    return UriResponse.custom_response(result["message"], 200, result)


@router.put("/leads/{lead_id}/resurrect")
async def resurrect_lead(
    lead_id: str,
    user_id: str = Query(...),
    alert_type: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Resurrect a DEAD lead
    PRD Section 5.2: Resurrection
    """
    result = await LazarusService.resurrect_lead(db, user_id, lead_id, alert_type)

    if not result["success"]:
        return UriResponse.custom_response(result["message"], 404)

    return UriResponse.custom_response(result["message"], 200, result)


# ============ BACKGROUND SCANNING ============
@router.post("/scan/run-weekly")
async def run_weekly_scan(
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Trigger weekly background scan manually
    PRD Section 6: Origami Method
    NOTE: This should normally be triggered by APScheduler cron job
    """
    result = await LazarusMonitoringService.run_weekly_scan(db)

    return UriResponse.custom_response(
        "Weekly scan completed",
        200,
        result,
    )


@router.post("/scan/focus-contacts")
async def scan_focus_contacts(
    batch_size: int = Query(100),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Manually trigger focus contact scan"""
    result = await LazarusMonitoringService.scan_focus_contacts(db, batch_size)

    return UriResponse.custom_response(
        "Focus contact scan completed",
        200,
        result,
    )


@router.post("/scan/focus-contact/{focus_id}")
async def scan_single_focus_contact(
    focus_id: str,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Scan a single specific focus contact immediately"""
    # Check credits for Lazarus scan (10 credits per scan)
    from app.services.uri_microservices.UriTaskManagerService import UriTaskManagerService

    try:
        credit_check = await UriTaskManagerService.check_payment_balance(
            user_id=user_id,
            action_type="LAZARUS_SCAN",
            payment_mode="CREDITS",
            quantity=1
        )

        if credit_check.get("status") and credit_check.get("responseData"):
            balance_data = credit_check["responseData"]
            if not balance_data.get("hasSufficientBalance"):
                return UriResponse.custom_response(
                    message="Insufficient credits for Lazarus scan. Requires 10 credits.",
                    error_code=403,
                    success=False,
                    data={
                        "required_credits": balance_data.get("requiredAmount", 10),
                        "available_credits": balance_data.get("availableBalance", 0),
                        "limit_exceeded": True
                    }
                )
    except Exception as e:
        print(f"⚠️ Credit check failed: {str(e)}")
        # Continue anyway if credit check fails

    result = await LazarusMonitoringService.scan_single_focus_contact(db, user_id, focus_id)

    if not result.get("success"):
        return UriResponse.custom_response(
            message=result.get("message", "Scan failed"),
            error_code=400,
            success=False,
            data=result,
        )

    # Deduct credits after successful scan (10 credits)
    try:
        await UriTaskManagerService.deduct_payment(
            user_id=user_id,
            action_type="LAZARUS_SCAN",
            payment_mode="CREDITS",
            quantity=1,
            reference=f"lazarus_focus_scan_{focus_id}"
        )
        print(f"💳 Deducted 10 credits for Lazarus scan (user: {user_id}, focus: {focus_id})")
    except Exception as credit_error:
        print(f"⚠️ Failed to deduct credits: {str(credit_error)}")

    return UriResponse.custom_response(
        message="Focus contact scanned successfully",
        error_code=200,
        success=True,
        data=result,
    )


@router.post("/scan/twitter-activity")
async def scan_twitter_activity(
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Scan all Twitter focus contacts for new activity
    Detects new posts since last scan and triggers resurrection alerts
    """
    from app.services.TwitterEnrichmentService import TwitterEnrichmentService
    from datetime import datetime

    # Get all focus contacts with Twitter data
    contacts = await db["focus_contacts"].find({
        "user_id": user_id,
        "twitter_id": {"$exists": True, "$ne": None},
        "monitoring_status": "ACTIVE"
    }).to_list(length=None)

    if not contacts:
        return UriResponse.custom_response(
            message="No Twitter contacts found to scan",
            error_code=200,
            success=True,
            data={"scanned": 0, "active": 0}
        )

    logger.info(f"🔍 Scanning {len(contacts)} Twitter contacts for activity...")

    # Build batch request for all contacts
    twitter_urls = [contact.get("twitter_url") or f"https://x.com/{contact.get('twitter_handle')}" for contact in contacts]

    # Call Twitter Enrichment Service (batch)
    twitter_service = TwitterEnrichmentService()
    profiles = await twitter_service.enrich_multiple_profiles(
        twitter_urls=twitter_urls,
        max_posts=20  # More posts for activity detection
    )

    # Process each profile and detect new activity
    active_contacts = []

    for profile, contact in zip(profiles, contacts):
        if not profile:
            continue

        # Get last known post ID from enrichment snapshot
        last_known_post_id = (
            contact.get("twitter_data", {})
            .get("enrichment_snapshot", {})
            .get("last_post_id")
        )

        # Detect new activity
        activity = twitter_service.detect_new_activity(profile, last_known_post_id)

        if activity["has_new_activity"]:
            # CONTACT IS ACTIVE! New posts detected
            active_contacts.append({
                "contact_id": contact["focus_id"],
                "contact_name": contact["name"],
                "twitter_handle": contact.get("twitter_handle"),
                "new_posts_count": activity["new_posts_count"],
                "latest_post": activity["latest_post"],
                "activity_detected_at": datetime.utcnow()
            })

            # Update contact with new activity
            posts = profile.get("posts", [])
            await db["focus_contacts"].update_one(
                {"focus_id": contact["focus_id"]},
                {
                    "$set": {
                        "twitter_data.enrichment_snapshot.last_post_id": posts[0]["post_id"] if posts else None,
                        "twitter_data.enrichment_snapshot.posts": posts[:5],
                        "twitter_data.last_scanned": datetime.utcnow(),
                        "twitter_data.last_activity_detected": datetime.utcnow(),
                        "twitter_data.new_posts_since_last_scan": activity["new_posts_count"],
                        "last_scan_date": datetime.utcnow()
                    }
                }
            )

            logger.info(f"🔥 ACTIVITY DETECTED: {contact['name']} (@{contact.get('twitter_handle')}) - {activity['new_posts_count']} new posts")

    logger.info(f"✅ Twitter scan completed: {len(contacts)} scanned, {len(active_contacts)} active")

    return UriResponse.custom_response(
        message=f"Twitter activity scan completed",
        error_code=200,
        success=True,
        data={
            "scanned": len(contacts),
            "active": len(active_contacts),
            "active_contacts": active_contacts
        }
    )


@router.post("/scan/company-monitors")
async def scan_company_monitors(
    batch_size: int = Query(100),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Manually trigger company monitor scan"""
    result = await LazarusMonitoringService.scan_company_monitors(db, batch_size)

    return UriResponse.custom_response(
        "Company monitor scan completed",
        200,
        result,
    )


# ============ AUTO-DETECTION RULES ============
@router.get("/auto-detection/rules")
async def get_auto_detection_rules(
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Get user's auto-detection rules for dead leads
    Returns default rules if none configured
    """
    from app.services.AutoDeadLeadDetectionService import AutoDeadLeadDetectionService

    rules = await AutoDeadLeadDetectionService.get_user_detection_rules(db, user_id)

    return UriResponse.custom_response(
        "Auto-detection rules retrieved successfully",
        200,
        jsonable_encoder(rules)
    )


@router.put("/auto-detection/rules")
async def update_auto_detection_rules(
    rules_update: DetectionRulesUpdate,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Update user's auto-detection rules"""
    from app.services.AutoDeadLeadDetectionService import AutoDeadLeadDetectionService

    result = await AutoDeadLeadDetectionService.update_user_detection_rules(
        db, user_id, rules_update.dict(exclude_unset=True)
    )

    # Remove MongoDB _id before encoding
    if result and "_id" in result:
        result.pop("_id")

    return UriResponse.custom_response(
        "Auto-detection rules updated successfully",
        200,
        jsonable_encoder(result)
    )


@router.post("/auto-detection/scan")
async def trigger_auto_detection_scan(
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Manually trigger auto-detection scan for dead leads
    Scans user's leads based on their configured rules
    """
    # Check credits for Lazarus auto-detection scan (10 credits per scan)
    from app.services.uri_microservices.UriTaskManagerService import UriTaskManagerService

    try:
        credit_check = await UriTaskManagerService.check_payment_balance(
            user_id=user_id,
            action_type="LAZARUS_SCAN",
            payment_mode="CREDITS",
            quantity=1
        )

        if credit_check.get("status") and credit_check.get("responseData"):
            balance_data = credit_check["responseData"]
            if not balance_data.get("hasSufficientBalance"):
                return UriResponse.custom_response(
                    message="Insufficient credits for Lazarus auto-detection scan. Requires 10 credits.",
                    error_code=403,
                    success=False,
                    data={
                        "required_credits": balance_data.get("requiredAmount", 10),
                        "available_credits": balance_data.get("availableBalance", 0),
                        "limit_exceeded": True
                    }
                )
    except Exception as e:
        print(f"⚠️ Credit check failed: {str(e)}")
        # Continue anyway if credit check fails

    from app.services.AutoDeadLeadDetectionService import AutoDeadLeadDetectionService

    # Get user's detection rules
    rules_doc = await AutoDeadLeadDetectionService.get_user_detection_rules(db, user_id)

    if not rules_doc.get("enabled"):
        return UriResponse.custom_response(
            "Auto-detection is disabled. Enable it in settings first.",
            400
        )

    # Run scan
    scan_result = await AutoDeadLeadDetectionService.scan_for_dead_leads(
        db, user_id, rules_doc["detection_rules"]
    )

    # Save to history
    await AutoDeadLeadDetectionService.save_scan_result(db, user_id, scan_result)

    # Deduct credits after successful scan (10 credits)
    try:
        await UriTaskManagerService.deduct_payment(
            user_id=user_id,
            action_type="LAZARUS_SCAN",
            payment_mode="CREDITS",
            quantity=1,
            reference=f"lazarus_auto_scan_{user_id}"
        )
        print(f"💳 Deducted 10 credits for Lazarus auto-detection scan (user: {user_id})")
    except Exception as credit_error:
        print(f"⚠️ Failed to deduct credits: {str(credit_error)}")

    return UriResponse.custom_response(
        "Auto-detection scan completed successfully",
        200,
        jsonable_encoder(scan_result)
    )


@router.get("/auto-detection/history")
async def get_auto_detection_history(
    user_id: str = Query(...),
    skip: int = Query(0),
    limit: int = Query(20),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Get history of auto-detection scans"""
    from app.services.AutoDeadLeadDetectionService import AutoDeadLeadDetectionService

    history = await AutoDeadLeadDetectionService.get_scan_history(
        db, user_id, skip, limit
    )

    return UriResponse.custom_response(
        "Scan history retrieved successfully",
        200,
        [jsonable_encoder(record) for record in history]
    )


# ============ AI KEYWORD EXTRACTION ============
@router.post("/extract-keywords")
async def extract_keywords(
    request: KeywordExtractionRequest,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Extract industry keywords from profile/post data using AI
    This endpoint helps auto-generate keywords for Paste & Go and CSV uploads
    """
    from app.services.AIService import AIService
    from app.domain.enums.ai_prompt import LazarusPrompt

    try:
        # Build context from provided data
        context_parts = []
        if request.name:
            context_parts.append(f"Name: {request.name}")
        if request.title:
            context_parts.append(f"Title: {request.title}")
        if request.company:
            context_parts.append(f"Company: {request.company}")
        if request.bio:
            context_parts.append(f"Bio: {request.bio}")
        if request.recent_post:
            context_parts.append(f"Recent Post: {request.recent_post}")

        context = "\n".join(context_parts)

        if not context:
            return UriResponse.custom_response(
                "No data provided for keyword extraction",
                400,
            )

        # Build AI prompt
        prompt = LazarusPrompt.EXTRACT_KEYWORDS_FROM_POST.value.format(
            context=context,
            signal_types=", ".join(request.signal_types)
        )

        # Get AI analysis
        ai_model = AIService.build_ai_model([
            AIService.construct_user_prompt(prompt)
        ])

        ai_response = await AIService.structured_chat_completion(
            ai_model, KeywordExtractionResult
        )

        result = AIService.extract_ai_result(ai_response)

        return UriResponse.custom_response(
            "Keywords extracted successfully",
            200,
            {
                "keywords": result.keywords,
                "confidence": result.confidence,
                "reasoning": result.reasoning
            }
        )

    except Exception as e:
        logger.error(f"Keyword extraction failed: {e}")
        return UriResponse.custom_response(
            f"Keyword extraction failed: {str(e)}",
            500
        )


# ============ ANALYTICS ============
@router.get("/analytics")
async def get_analytics_data(
    user_id: str = Query(...),
    days: int = Query(30, description="Number of days to analyze (default: 30)"),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Get detailed analytics data for Lazarus dashboard
    PRD Section 7 - Success Metrics

    Returns:
    - Resurrection rate (% of alerts acted upon) - Target >15%
    - Quota utilization (% of slots used)
    - Alert performance by type
    - Weekly trend data (last 4 weeks)
    - False positive rate (dismissals)
    - Accuracy rate
    """
    analytics = await LazarusService.get_analytics_data(db, user_id, days)
    return UriResponse.custom_response(
        "Analytics data retrieved successfully", 200, analytics
    )


@router.post("/alerts/recalculate-priority")
async def recalculate_alert_priorities(
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Recalculate priority scores for all NEW alerts
    Useful for existing alerts that don't have priority scores yet
    """
    from app.services.LazarusMonitoringService import LazarusMonitoringService

    # Get all NEW alerts for user
    alerts = await db["lazarus_alerts"].find({
        "user_id": user_id,
        "status": "NEW"
    }).to_list(None)

    updated_count = 0
    for alert in alerts:
        # Calculate priority score
        priority_score, priority_level = LazarusMonitoringService.calculate_priority_score(alert)

        # Update alert
        await db["lazarus_alerts"].update_one(
            {"alert_id": alert["alert_id"]},
            {"$set": {
                "priority_score": priority_score,
                "priority_level": priority_level
            }}
        )
        updated_count += 1

    logger.info(f"🔥 Recalculated priority for {updated_count} alerts for user {user_id}")

    return UriResponse.custom_response(
        f"Recalculated priority for {updated_count} alerts",
        200,
        {"updated_count": updated_count}
    )


# ============ SCANNED CONTENT ============
@router.get("/scanned-content")
async def get_scanned_content(
    user_id: str = Query(...),
    skip: int = Query(0),
    limit: int = Query(50),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Get all scanned content for Phase 2: Scanned Content Tab

    NEW: Retrieves from scan_history collection which saves ALL scanned posts
    Groups by contact and time period for organized display

    Returns:
    - All scan history records with posts (grouped by contact and date)
    - Signal detection status for each scan
    """
    from app.repository.LazarusRepository import LazarusRepository
    from datetime import datetime
    from collections import defaultdict

    try:
        # Get all scan history for this user, sorted by most recent first
        scan_history_records = await db["scan_history"].find({
            "user_id": user_id
        }).sort("scan_date", -1).to_list(None)

        # Build grouped scan history data from new scan_history collection
        scan_groups = []

        for scan in scan_history_records:
            # Build scanned posts for this scan
            scanned_posts = []
            triggering_index = scan.get("triggering_post_index")

            for post in scan.get("scanned_posts", []):
                is_triggering = (post.get("post_index") == triggering_index)

                scanned_posts.append({
                    "post_id": f"{scan.get('_id')}_{post.get('post_index')}",
                    "post_url": post.get("post_url"),
                    "post_text": post.get("post_text"),
                    "post_platform": post.get("post_platform"),
                    "post_author": post.get("post_author"),
                    "post_created_at": post.get("post_created_at"),
                    "post_likes": post.get("post_likes", 0),
                    "post_comments": post.get("post_comments", 0),
                    "post_index": post.get("post_index"),
                    "is_triggering_post": is_triggering,
                })

            # Build scan group
            scan_group = {
                "scan_id": str(scan.get("_id")),
                "source_type": scan.get("source_type"),
                "source_id": scan.get("source_id"),
                "source_name": scan.get("source_name"),
                "scan_date": scan.get("scan_date"),
                "platform": scan.get("platform"),
                "posts_scanned_count": scan.get("posts_scanned_count", 0),
                "scanned_posts": scanned_posts,
                "signal_detected": scan.get("signal_detected", False),
                "alert_id": scan.get("alert_id"),
                "signal_type": scan.get("signal_type"),
                "confidence": scan.get("confidence"),
                "triggering_post_index": triggering_index,
            }

            scan_groups.append(scan_group)

        # BACKWARD COMPATIBILITY: Convert old alerts with scanned_posts to scan_groups format
        # This shows historical scanned content that was saved in alerts before scan_history existed
        old_alerts = await db["lazarus_alerts"].find({
            "user_id": user_id,
            "evidence.scanned_posts": {"$exists": True, "$ne": []}
        }).sort("created_at", -1).to_list(None)

        for alert in old_alerts:
            evidence = alert.get("evidence", {})
            alert_scanned_posts = evidence.get("scanned_posts", [])

            if not alert_scanned_posts:
                continue

            # Build scanned posts for legacy alert
            scanned_posts = []
            triggering_index = evidence.get("triggering_post_index")

            for post in alert_scanned_posts:
                is_triggering = (post.get("post_index") == triggering_index)

                scanned_posts.append({
                    "post_id": f"{alert.get('alert_id')}_{post.get('post_index')}",
                    "post_url": post.get("post_url"),
                    "post_text": post.get("post_text"),
                    "post_platform": post.get("post_platform"),
                    "post_author": post.get("post_author"),
                    "post_created_at": post.get("post_created_at"),
                    "post_likes": post.get("post_likes", 0),
                    "post_comments": post.get("post_comments", 0),
                    "post_index": post.get("post_index"),
                    "is_triggering_post": is_triggering,
                })

            # Build scan group from legacy alert
            scan_group = {
                "scan_id": alert.get("alert_id"),
                "source_type": alert.get("source_type"),
                "source_id": alert.get("source_id"),
                "source_name": alert.get("source_name"),
                "scan_date": alert.get("created_at"),
                "platform": evidence.get("post_platform", "Unknown"),
                "posts_scanned_count": len(scanned_posts),
                "scanned_posts": scanned_posts,
                "signal_detected": True,  # Old alerts always had signals
                "alert_id": alert.get("alert_id"),
                "signal_type": evidence.get("signal_type"),
                "confidence": evidence.get("confidence"),
                "triggering_post_index": triggering_index,
            }

            scan_groups.append(scan_group)

        # Sort all scan groups by scan_date (most recent first)
        scan_groups.sort(key=lambda x: x.get("scan_date") or datetime.min, reverse=True)

        # Apply pagination
        paginated_scan_groups = scan_groups[skip:skip + limit]

        return UriResponse.custom_response(
            message="Scanned content retrieved successfully",
            error_code=200,
            success=True,
            data={
                "scan_groups": paginated_scan_groups,
                "total_scans": len(scan_groups),
                "total_posts": sum(sg.get("posts_scanned_count", 0) for sg in paginated_scan_groups),
            }
        )

    except Exception as e:
        logger.error(f"❌ Error fetching scanned content: {str(e)}")
        import traceback
        traceback.print_exc()
        return UriResponse.custom_response(
            message=f"Failed to fetch scanned content: {str(e)}",
            error_code=500,
            success=False
        )


@router.get("/rejected-posts")
async def get_rejected_posts(
    user_id: str = Query(...),
    skip: int = Query(0),
    limit: int = Query(50),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Get posts that were scanned but didn't meet alert criteria

    Returns scan history where signal_detected=False with AI rejection reasons
    Shows users why certain posts didn't trigger alerts (e.g., promotional content,
    no pain points, doesn't match keywords, confidence too low)

    Returns:
    - Rejected scans with human-friendly reasons from AI
    - Grouped by contact for easy review
    """
    from datetime import datetime

    try:
        # Debug: Check what's in scan_history
        all_scans = await db["scan_history"].find({
            "user_id": user_id
        }).sort("scan_date", -1).limit(5).to_list(5)

        print(f"🔍 DEBUG: Total scans for user: {len(all_scans)}")
        for scan in all_scans:
            print(f"🔍 DEBUG:   Scan {scan.get('_id')}: signal_detected={scan.get('signal_detected')}, has_rejection_reason={bool(scan.get('rejection_reason'))}, rejection_reason={scan.get('rejection_reason')[:50] if scan.get('rejection_reason') else 'None'}...")

        # Get scan history where NO signal was detected
        rejected_scans = await db["scan_history"].find({
            "user_id": user_id,
            "signal_detected": False,
            "rejection_reason": {"$exists": True, "$ne": None}
        }).sort("scan_date", -1).to_list(None)

        print(f"🔍 DEBUG Rejected Posts: Found {len(rejected_scans)} rejected scans for user {user_id}")

        # Build rejected posts data
        rejected_groups = []

        for scan in rejected_scans:
            # Build scanned posts for this scan
            scanned_posts = []

            for post in scan.get("scanned_posts", []):
                scanned_posts.append({
                    "post_id": f"{scan.get('_id')}_{post.get('post_index')}",
                    "post_url": post.get("post_url"),
                    "post_text": post.get("post_text"),
                    "post_platform": post.get("post_platform"),
                    "post_author": post.get("post_author"),
                    "post_created_at": post.get("post_created_at"),
                    "post_likes": post.get("post_likes", 0),
                    "post_comments": post.get("post_comments", 0),
                    "post_index": post.get("post_index"),
                })

            # Build rejected scan group
            rejected_group = {
                "scan_id": str(scan.get("_id")),
                "source_type": scan.get("source_type"),
                "source_id": scan.get("source_id"),
                "source_name": scan.get("source_name"),
                "scan_date": scan.get("scan_date"),
                "platform": scan.get("platform"),
                "posts_scanned_count": scan.get("posts_scanned_count", 0),
                "scanned_posts": scanned_posts,
                "rejection_reason": scan.get("rejection_reason"),
                "confidence": scan.get("confidence", 0.0),
            }

            rejected_groups.append(rejected_group)

        # Pagination
        total_count = len(rejected_groups)
        paginated_rejected_groups = rejected_groups[skip : skip + limit]

        return UriResponse.custom_response(
            message="Rejected posts retrieved successfully",
            error_code=200,
            success=True,
            data={
                "rejected_scans": paginated_rejected_groups,
                "total_count": total_count,
                "skip": skip,
                "limit": limit,
                "total_posts": sum(sg.get("posts_scanned_count", 0) for sg in paginated_rejected_groups),
            }
        )

    except Exception as e:
        logger.error(f"❌ Error fetching rejected posts: {str(e)}")
        import traceback
        traceback.print_exc()
        return UriResponse.custom_response(
            message=f"Failed to fetch rejected posts: {str(e)}",
            error_code=500,
            success=False
        )
