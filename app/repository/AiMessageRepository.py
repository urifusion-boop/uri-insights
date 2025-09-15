from datetime import datetime
from typing import Any, Optional, Dict
import httpx
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.models.aimessage_model import AiMessageModel
from app.domain.requests.aimessage_requests import (
    AiMessageCreateRequest,
    AiMessageUpdateRequest,
)
from app.core.config import settings
from app.domain.responses.uri_response import UriResponse
from app.repository.AiThreadRepository import AiThreadRepository

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
    "OpenAI-Beta": "assistants=v2",
}

BASE_URL = "https://api.openai.com/v1/threads"


class AiMessageRepository:
    @staticmethod
    async def create_message(
        db: AsyncIOMotorDatabase, thread_id: str, request_data: AiMessageCreateRequest
    ) -> Dict[str, Any]:
        """
        Create a message via OpenAI API and store it in the database.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/{thread_id}/messages",
                headers=HEADERS,
                json=request_data.dict(),
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )

        api_response = response.json()
        message_id = api_response["id"]

        message_data = {
            "message_id": message_id,
            "thread_id": thread_id,
            "role": request_data.role,
            "content": request_data.content,
            "attachments": request_data.attachments,
            "metadata": request_data.metadata,
        }

        await db["messages"].insert_one(message_data)
        return api_response

    @staticmethod
    async def get_message(thread_id: str, message_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/{thread_id}/messages/{message_id}",
                headers=HEADERS,
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )

        return response.json()

    @staticmethod
    async def get_all_messages(
        thread_id: str, limit: int = 20, order: str = "desc"
    ) -> Dict[str, Any]:
        params = {"limit": limit, "order": order}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/{thread_id}/messages",
                headers=HEADERS,
                params=params,
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )

        return response.json()

    @staticmethod
    async def update_message(
        thread_id: str, message_id: str, request_data: AiMessageUpdateRequest
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/{thread_id}/messages/{message_id}",
                headers=HEADERS,
                json=request_data.dict(),
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )

        return response.json()

    @staticmethod
    async def delete_message(thread_id: str, message_id: str) -> bool:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{BASE_URL}/{thread_id}/messages/{message_id}",
                headers=HEADERS,
            )
        return response.status_code == 200

    @staticmethod
    async def delete_all_messages_db(db: AsyncIOMotorDatabase, thread_id: str) -> bool:
        response = await AiThreadRepository.delete_thread(thread_id)
        if response:
            await db["messages"].delete_many({"thread_id": thread_id})
        return response
