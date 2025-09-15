from fastapi import APIRouter, Body, Depends, Query
from fastapi.encoders import jsonable_encoder
from typing import List, Optional

from app.dependencies import get_db_dependency
from app.domain.requests.apollo_requests import (
    OrgEnrichRequest,
)
from app.domain.responses.uri_response import UriResponse
from app.services.ApolloService import ApolloService
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter()


@router.get("/people/enrich")
async def enrich_person(
    lead_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    reveal_email: bool = False,
    reveal_phone: bool = False,
    webhook_url: Optional[str] = None,
):
    result = await ApolloService.enrich_person(
        lead_id=lead_id,
        db=db,
        reveal_email=reveal_email,
        reveal_phone=reveal_phone,
        webhook_url=webhook_url,
    )
    return UriResponse.get_status_response(response=jsonable_encoder(result))


@router.post("/people/enrich/bulk")
async def enrich_people_bulk(
    details: List[dict] = Body(...),
    reveal_personal_emails: bool = Query(False),
    reveal_phone_number: bool = Query(False),
    webhook_url: Optional[str] = Query(None),
):
    result = await ApolloService.enrich_people_bulk(
        details=details,
        reveal_personal_emails=reveal_personal_emails,
        reveal_phone_number=reveal_phone_number,
        webhook_url=webhook_url,
    )
    return UriResponse.get_status_response(response=jsonable_encoder(result))


@router.get("/organization/enrich")
async def enrich_organization(domain: str = Query(...)):
    result = await ApolloService.enrich_organization(OrgEnrichRequest(domain=domain))
    return UriResponse.get_status_response(response=jsonable_encoder(result))


@router.post("/organizations/enrich/bulk")
async def enrich_organizations_bulk(domains: List[str] = Body(...)):
    result = await ApolloService.enrich_organizations_bulk(domains)
    return UriResponse.get_status_response(response=jsonable_encoder(result))


@router.get("/usage-stats")
async def get_api_usage_stats():
    result = await ApolloService.get_api_usage_stats()
    return UriResponse.get_status_response(response=jsonable_encoder(result))
