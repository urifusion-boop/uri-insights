from datetime import datetime
from typing import Any, Optional, Dict
import httpx
from fastapi import HTTPException
from app.domain.models.aithread_model import AiThreadModel
from app.domain.requests.aithread_requests import (
    AiThreadCreateRequest,
    AiThreadUpdateRequest,
)
from app.core.config import settings
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.domain.responses.uri_response import UriResponse

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
    "OpenAI-Beta": "assistants=v2",
}
BASE_URL = "https://api.openai.com/v1/threads"


class AiThreadRepository:
    @staticmethod
    async def create_thread(
        db: AsyncIOMotorDatabase,
        user_id: str,
        thread_type: str,
        assistant_id: str,
        request_data: AiThreadCreateRequest,
    ) -> Dict[str, Any]:
        payload = request_data.dict()
        payload["messages"] = [msg.dict() for msg in request_data.messages or []]

        async with httpx.AsyncClient() as client:
            response = await client.post(BASE_URL, headers=HEADERS, json=payload)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )

        api_response = response.json()
        thread_id = api_response["id"]

        existing_thread = await db["threads"].find_one({"thread_id": thread_id})
        if existing_thread:
            return UriResponse.get_single_data_response("thread", existing_thread)

        thread_data = {
            "user_id": user_id,
            "thread_type": thread_type,
            "thread_id": thread_id,
            "assistant_id": assistant_id,
            "messages": payload["messages"],
            "metadata": payload.get("metadata"),
            "tool_resources": payload.get("tool_resources"),
            "created_at": datetime.utcnow().isoformat(),
        }

        await db["threads"].insert_one(thread_data)
        return api_response

    @staticmethod
    async def get_thread(thread_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/{thread_id}", headers=HEADERS)
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )
        return response.json()

    @staticmethod
    async def get_thread_db(db: AsyncIOMotorDatabase, thread_id: str) -> Dict[str, Any]:
        thread = await db["threads"].find_one({"thread_id": thread_id})
        return thread or await AiThreadRepository.get_thread(thread_id)

    @staticmethod
    async def get_all_threads(
        limit: int = 20,
        order: str = "desc",
        previous: Optional[str] = None,
        next: Optional[str] = None,
    ) -> dict:
        params = {"limit": limit, "order": order}
        if previous:
            params["before"] = previous
        if next:
            params["after"] = next

        async with httpx.AsyncClient() as client:
            response = await client.get(BASE_URL, headers=HEADERS, params=params)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )
        return response.json()

    @staticmethod
    async def get_all_threads_db(
        db: AsyncIOMotorDatabase,
        user_id: str,
        thread_type: Optional[str] = None,
        limit: int = 20,
        skip: int = 0,
    ) -> Dict[str, Any]:
        query = {"user_id": user_id}
        if thread_type:
            query["thread_type"] = thread_type

        total_threads = await db["threads"].count_documents(query)
        cursor = (
            db["threads"].find(query).sort("created_at", -1).skip(skip).limit(limit)
        )
        threads = await cursor.to_list(length=limit)
        threads_list = [AiThreadModel(**thread).model_dump() for thread in threads]

        return UriResponse.get_paged_data_response(
            "threads", threads_list, total_threads, skip + 1, limit
        )

    @staticmethod
    async def update_thread(
        thread_id: str, request_data: AiThreadUpdateRequest
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/{thread_id}", headers=HEADERS, json=request_data.dict()
            )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )
        return response.json()

    @staticmethod
    async def update_thread_db(
        db: AsyncIOMotorDatabase,
        thread_id: str,
        request_data: AiThreadUpdateRequest,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        response = await AiThreadRepository.update_thread(thread_id, request_data)

        updates = request_data.dict(exclude_none=True)
        updates["run_id"] = run_id
        updates["updated_at"] = datetime.utcnow().isoformat()

        result = await db["threads"].update_one(
            {"thread_id": thread_id}, {"$set": updates}
        )

        if result.matched_count == 0:
            return UriResponse.get_single_data_response(
                "thread", None, "Thread not found."
            )

        return response

    @staticmethod
    async def delete_thread(thread_id: str) -> bool:
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{BASE_URL}/{thread_id}", headers=HEADERS)
        return response.status_code == 200

    @staticmethod
    async def delete_thread_db(db: AsyncIOMotorDatabase, thread_id: str) -> bool:
        deleted_from_openai = await AiThreadRepository.delete_thread(thread_id)
        if deleted_from_openai:
            await db["threads"].delete_one({"thread_id": thread_id})
        return deleted_from_openai
