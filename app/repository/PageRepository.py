from typing import Dict, Any, Optional, List
from pymongo.collection import Collection
from bson import ObjectId
from datetime import datetime
from app import schemas
from app.domain.responses.uri_response import UriResponse


class PageRepository:
    @staticmethod
    async def create_page(
        db: Collection, page: schemas.FacebookUserPagesCreate
    ) -> Dict[str, Any]:
        # Prepare page data for MongoDB insertion
        db_page = page.dict()
        db_page["page_id"] = str(ObjectId())

        # Insert into the database
        await db["facebook_user_pages"].insert_one(db_page)

        # Return the response using the UriResponse pattern
        return UriResponse.create_response(
            "page", schemas.FacebookUserPages(**db_page).dict()
        )

    @staticmethod
    async def create_pages(
        db: Collection, pages: List[schemas.FacebookUserPagesCreate]
    ) -> Dict[str, Any]:
        # Prepare a list of page data for MongoDB insertion
        db_pages = []

        for page in pages:
            db_page = page.dict()
            db_page["page_id"] = str(ObjectId())
            db_pages.append(db_page)

        # Insert multiple pages into the database
        _ = await db["facebook_user_pages"].insert_many(db_pages)

        # Fetch the inserted pages with the ObjectIds
        inserted_pages = []
        for db_page in db_pages:
            inserted_pages.append(schemas.FacebookUserPages(**db_page).dict())

        # Return the response using the UriResponse pattern
        return UriResponse.create_response("pages", inserted_pages)

    @staticmethod
    async def get_page_by_id(db: Collection, page_id: str) -> Any:
        # Retrieve the page by ID
        db_page = await db["facebook_user_pages"].find_one({"page_id": page_id})

        # If not found, return None
        if not db_page:
            return UriResponse.get_single_data_response("page", None)

        # Return the page data in the response
        return UriResponse.get_single_data_response(
            "page", schemas.FacebookUserPages(**db_page).dict()
        )

    @staticmethod
    async def get_pages_by_filter(
        db: Collection,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
    ) -> Any:
        # Prepare the query for filtering
        query: Dict[str, Any] = {}

        if user_id is not None:
            query["user_id"] = user_id

        # Get the total count of matching pages
        total_pages = db["facebook_user_pages"].count_documents(query)

        # Execute the query with pagination
        db_pages = list(db["facebook_user_pages"].find(query).skip(skip).limit(limit))

        # Map the results to the Page schema
        pages = [
            schemas.FacebookUserPages(**page).model_dump(exclude_unset=True)
            for page in db_pages
        ]

        meta_data = {"totalPages": total_pages}
        # Return the list of pages in the response
        return UriResponse.get_paged_data_response(
            "pages", pages, total_pages, skip + 1, limit, meta_data
        )

    @staticmethod
    async def update_page(db: Collection, page_id: str, data: dict) -> Any:
        # Update the page data in the database
        result = await db["facebook_user_pages"].update_one(
            {"page_id": page_id}, {"$set": {"data": data}}
        )

        # If no records were updated, return None
        if result.matched_count == 0:
            return None

        # Return the updated page
        return PageRepository.get_page_by_id(db, page_id)

    @staticmethod
    async def delete_page(db: Collection, page_id: str) -> Any:
        # Delete the page from the database
        result = await db["facebook_user_pages"].delete_one({"page_id": page_id})

        # Return the deletion result in the response
        return UriResponse.delete_response("page", result.deleted_count > 0)
