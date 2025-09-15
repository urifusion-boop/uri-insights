from typing import Callable, Coroutine, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.factories.AdapterFactory import AdapterFactory
from app.domain.requests.reportgeneration_requests import ReportGenerationRequest
from app.services.FacebookService import FacebookService
from app.services.InstagramService import InstagramService
from app.services.LinkedInService import LinkedInService


async def facebook_metadata(
    db: AsyncIOMotorDatabase,
    report_generation_data: ReportGenerationRequest,
):
    metadata = await FacebookService.generate_raw_metadata_for_report_gen(
        db, report_generation_data
    )
    result = AdapterFactory.get_adapter("facebook", metadata).to_report_gen_metadata()
    return result


async def instagram_metadata(
    db: AsyncIOMotorDatabase,
    report_generation_data: ReportGenerationRequest,
):
    try:
        metadata = await InstagramService.generate_raw_metadata_for_report_gen(
            db, report_generation_data
        )
        result = AdapterFactory.get_adapter(
            "instagram", metadata
        ).to_report_gen_metadata()
        return result
    except:
        raise


async def linkedin_metadata(
    db: AsyncIOMotorDatabase,
    report_generation_data: ReportGenerationRequest,
):
    try:
        metadata = await LinkedInService.generate_raw_metadata_for_report_gen(
            db, report_generation_data
        )
        result = AdapterFactory.get_adapter(
            "linkedin", metadata
        ).to_report_gen_metadata()
        return result
    except:
        raise


PLATFORM_METADATA_FETCHERS: Dict[
    str, Callable[[AsyncIOMotorDatabase, ReportGenerationRequest], Coroutine]
] = {
    "FACEBOOK": facebook_metadata,
    "INSTAGRAM": instagram_metadata,
    "LINKEDIN": linkedin_metadata,
}
