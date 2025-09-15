from datetime import datetime
from typing import Any, Optional, Dict
import httpx
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.models.airun_model import AiRunModel
from app.domain.requests.airun_requests import AiRunCreateRequest, AiRunUpdateRequest
from app.core.config import settings
from app.domain.responses.uri_response import UriResponse

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
    "OpenAI-Beta": "assistants=v2",
}
BASE_URL = "https://api.openai.com/v1/threads"


class AiRunRepository:
    @staticmethod
    async def create_run(
        db: AsyncIOMotorDatabase, thread_id: str, request_data: AiRunCreateRequest
    ) -> Dict[str, Any]:
        run_payload = request_data.dict()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/{thread_id}/runs", headers=HEADERS, json=run_payload
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )

        api_response = response.json()
        run_id = api_response["id"]

        run_data = {
            "run_id": run_id,
            "thread_id": thread_id,
            "assistant_id": request_data.assistant_id,
            "status": api_response.get("status", "queued"),
            "created_at": datetime.utcnow(),
            "model": request_data.model,
            "instructions": request_data.instructions,
            "tools": request_data.tools,
            "metadata": request_data.metadata,
            "temperature": request_data.temperature,
            "top_p": request_data.top_p,
        }

        await db["runs"].insert_one(run_data)
        return api_response

    @staticmethod
    async def get_run(thread_id: str, run_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/{thread_id}/runs/{run_id}", headers=HEADERS
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )

        return response.json()

    @staticmethod
    async def get_all_runs(
        thread_id: str, limit: int = 20, order: str = "desc"
    ) -> Dict[str, Any]:
        params = {"limit": limit, "order": order}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/{thread_id}/runs", headers=HEADERS, params=params
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )

        return response.json()

    @staticmethod
    async def update_run(
        thread_id: str, run_id: str, request_data: AiRunUpdateRequest
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/{thread_id}/runs/{run_id}",
                headers=HEADERS,
                json=request_data.dict(),
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )

        return response.json()

    @staticmethod
    async def update_function_run(
        thread_id: str, run_id: str, tool_outputs: dict
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/{thread_id}/runs/{run_id}/submit_tool_outputs",
                headers=HEADERS,
                json=tool_outputs,
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )

        return response.json()

    @staticmethod
    async def cancel_run(thread_id: str, run_id: str) -> bool:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/{thread_id}/runs/{run_id}/cancel", headers=HEADERS
            )
        return response.status_code == 200

    @staticmethod
    async def delete_run_db(db: AsyncIOMotorDatabase, run_id: str) -> bool:
        await db["runs"].delete_one({"run_id": run_id})
        return True

    @staticmethod
    async def get_run_status(thread_id: str, run_id: str) -> Optional[str]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/{thread_id}/runs/{run_id}", headers=HEADERS
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )

        run_data = response.json()
        print("🟡 AI Run Status Response: ", run_data)
        return run_data.get("status")

    @staticmethod
    async def get_run_response(thread_id: str, run_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/{thread_id}/runs/{run_id}", headers=HEADERS
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )

        run_data = response.json()
        print("🟡 AI Run Full Response: ", run_data)
        return run_data
