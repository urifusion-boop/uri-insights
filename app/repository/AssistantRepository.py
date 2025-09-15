import httpx
from fastapi import HTTPException
from app.domain.requests.assistant_requests import AssistantCreateRequest
from app.core.config import settings

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
    "OpenAI-Beta": "assistants=v2",
}

BASE_URL = "https://api.openai.com/v1/assistants"


class AssistantRepository:
    @staticmethod
    async def create_assistant(request_data: AssistantCreateRequest) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                BASE_URL, headers=HEADERS, json=request_data.dict()
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code, detail=response.json()
                )
            return response.json()

    @staticmethod
    async def list_assistants(limit: int = 20, order: str = "desc") -> list:
        params = {"limit": limit, "order": order}
        async with httpx.AsyncClient() as client:
            response = await client.get(BASE_URL, headers=HEADERS, params=params)
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code, detail=response.json()
                )
            return response.json()

    @staticmethod
    async def get_assistant(assistant_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/{assistant_id}", headers=HEADERS)
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code, detail=response.json()
                )
            return response.json()

    @staticmethod
    async def update_assistant(
        assistant_id: str, request_data: AssistantCreateRequest
    ) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/{assistant_id}", headers=HEADERS, json=request_data.dict()
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code, detail=response.json()
                )
            return response.json()

    @staticmethod
    async def delete_assistant(assistant_id: str) -> bool:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{BASE_URL}/{assistant_id}", headers=HEADERS
            )
            return response.status_code == 200
