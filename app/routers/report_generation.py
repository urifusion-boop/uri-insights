from fastapi import APIRouter, BackgroundTasks, Depends
from app.dependencies import (
    enforce_feature_limit,
    get_db_dependency,
)
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.enums.reportgeneration_enum import ReportGenerationTypeEnum
from app.domain.requests.reportgeneration_requests import ReportGenerationRequest
from app.domain.responses.uri_response import UriResponse
from app.services.ReportGenerationService import ReportGenerationService

router = APIRouter()


@router.post("/account-tracking/generate")
async def generate_account_tracking_report(
    payload: ReportGenerationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    _: dict = Depends(enforce_feature_limit),
):
    if payload.report_generation_type != ReportGenerationTypeEnum.ACCOUNT_TRACKING:
        response = UriResponse.custom_response("Invalid report type selected.", 400)
    else:
        response = await ReportGenerationService.generate_user_report(
            db=db,
            report_generation_type=ReportGenerationTypeEnum.ACCOUNT_TRACKING,
            report_generation_data=payload,
            background_tasks=background_tasks,
        )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/hashtag-tracking/generate")
async def generate_hashtag_tracking_report(
    payload: ReportGenerationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    _: dict = Depends(enforce_feature_limit),
):
    if payload.report_generation_type != ReportGenerationTypeEnum.HASHTAG_TRACKING:
        response = UriResponse.custom_response("Invalid report type selected.", 400)
    else:
        response = await ReportGenerationService.generate_user_report(
            db=db,
            report_generation_type=ReportGenerationTypeEnum.HASHTAG_TRACKING,
            report_generation_data=payload,
            background_tasks=background_tasks,
        )
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )
