from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import get_db_dependency
from app import schemas
from app.repository.PageRepository import PageRepository
from app.domain.responses.uri_response import UriResponse
from typing import Optional, List
from fastapi.encoders import jsonable_encoder

router = APIRouter()


# Create a new page
@router.post("/create")
async def create_page(
    page: schemas.FacebookUserPagesCreate,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await PageRepository.create_page(db, page)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Get an page by ID
@router.get("/getById")
async def get_page(page_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)):
    data = await PageRepository.get_page_by_id(db, page_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Filter pages by name, email, platform, or location with pagination
@router.get("/getByFilters")
async def filter_pages(
    user_id: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await PageRepository.get_pages_by_filter(db=db, user_id=user_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Update an page's information
@router.post("/update")
async def update_page(
    page: schemas.FacebookUserPagesUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await PageRepository.update_page(db, page.page_id, page.data)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Delete an page by ID
@router.delete("/delete")
async def delete_page(
    page_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await PageRepository.delete_page(db, page_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )
