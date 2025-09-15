from typing import Optional
from app.repository.AiThreadRepository import AiThreadRepository
from app.domain.requests.aithread_requests import (
    AiThreadCreateRequest,
    AiThreadUpdateRequest,
)
from app.domain.responses.uri_response import UriResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.helpers.assistant_helper import AssistantHelper
from app.domain.models.aithread_model import AiThreadMessage
from app.domain.requests.airun_requests import AiRunCreateRequest
from app.services.AiRunService import AiRunService
from app.domain.requests.aithread_requests import AiThreadUpdateRequest


class AiThreadService:
    @staticmethod
    async def create_thread(
        db: AsyncIOMotorDatabase,
        user_id: str,
        thread_type: str,
        request_data: AiThreadCreateRequest,
    ):
        assistant_id = AssistantHelper.get_assistant_id_for_thread_type(thread_type)

        # Retrieve initial messages (ensuring it's a list)
        initial_messages = await AssistantHelper.get_initial_message_for_thread_type(
            db, thread_type, user_id
        )

        if not initial_messages or not isinstance(initial_messages, list):
            raise ValueError(
                "Invalid response from AssistantHelper.get_initial_message_for_thread_type"
            )

        # Extract the first message’s text properly
        first_message_text = initial_messages[0].get("text", "")

        initial_message = AiThreadMessage(
            role="assistant",
            content=[
                {"type": "text", "text": first_message_text}
            ],  # ✅ Ensure it's a string
            attachments=None,
        )

        if not request_data.messages:
            request_data.messages = []
        request_data.messages.append(initial_message)

        print("Request Data : ", request_data)

        thread_response = await AiThreadRepository.create_thread(
            db, user_id, thread_type, assistant_id, request_data
        )

        print("Response : ", thread_response)
        thread_id = thread_response.get("id")
        if not thread_id:
            return UriResponse.create_response("thread", None)

        # Automatically create a run for the newly created thread
        run_request = AiRunCreateRequest(
            assistant_id=assistant_id,
            model="gpt-4o",
            instructions=None,
            additional_instructions=None,
            additional_messages=None,
            tools=None,
            metadata=None,
            temperature=1.0,
            top_p=1.0,
        )

        response = await AiRunService.create_run(db, thread_id, run_request)
        run_response = response.get("responseData", {})
        run_id = run_response.get("id")

        thread_data = AiThreadUpdateRequest(
            thread_id=thread_id,
            metadata={},
            tool_resources=None,
        )

        print("Thread Data : ", thread_data)
        updated_thread = await AiThreadRepository.update_thread_db(
            db, thread_id, thread_data, run_id
        )
        print("Updated Thread : ", updated_thread)

        return UriResponse.create_response("thread", thread_response)

    @staticmethod
    async def get_thread(db: AsyncIOMotorDatabase, thread_id: str):
        response = await AiThreadRepository.get_thread_db(db, thread_id)
        return UriResponse.get_single_data_response("thread", response)

    @staticmethod
    async def get_threads_by_filter(
        db: AsyncIOMotorDatabase,
        user_id: str,
        thread_type: Optional[str],
        limit: int,
        skip: int,
    ):
        response = await AiThreadRepository.get_all_threads_db(
            db, user_id, thread_type, limit, skip
        )
        return response

    @staticmethod
    async def update_thread(
        db: AsyncIOMotorDatabase, thread_id: str, request_data: AiThreadUpdateRequest
    ):
        response = await AiThreadRepository.update_thread_db(
            db, thread_id, request_data
        )
        return UriResponse.update_response("thread", response)

    @staticmethod
    async def delete_thread(db: AsyncIOMotorDatabase, thread_id: str):
        response = await AiThreadRepository.delete_thread_db(db, thread_id)
        return UriResponse.delete_response("thread", response)
