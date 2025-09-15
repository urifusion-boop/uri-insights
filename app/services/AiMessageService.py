import os
import tempfile
from typing import Optional
import aiofiles
from fastapi import UploadFile
import openai
from app.repository.AiMessageRepository import AiMessageRepository
from app.domain.requests.aimessage_requests import (
    AiMessageCreateRequest,
    AiMessageUpdateRequest,
)
from app.domain.responses.uri_response import UriResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.AiRunService import AiRunService
from app.repository.AiThreadRepository import AiThreadRepository
from app.services.AiFunctionService import AiFunctionService


class AiMessageService:
    @staticmethod
    async def create_message(
        db: AsyncIOMotorDatabase, thread_id: str, request_data: AiMessageCreateRequest
    ):
        """
        Creates a new AI message and processes the AI response if the message is from a user.
        """
        response = await AiMessageRepository.create_message(db, thread_id, request_data)

        if request_data.role == "user":
            await AiMessageService._handle_user_message(
                db, thread_id, request_data.content[0].get("text", "")
            )

        return UriResponse.create_response("message", response)

    @staticmethod
    async def _handle_user_message(
        db: AsyncIOMotorDatabase,
        thread_id: str,
        user_message: Optional[str] = None,
    ):
        """
        Handles additional processing for messages sent by users.
        """
        thread = await AiThreadRepository.get_thread_db(db, thread_id)
        assistant_id = await AiFunctionService._get_assistant_id(thread)

        if not assistant_id:
            return UriResponse.get_single_data_response("assistant id", None)

        run_response = await AiFunctionService._trigger_ai_run(
            db, thread_id, assistant_id
        )
        run_id = run_response.get("id", "")

        ai_response = await AiRunService.wait_for_run_completion(thread_id, run_id)
        print("AI Operation Response:", ai_response)

        if ai_response.get("status") == "requires_action":
            await AiFunctionService._handle_function_calls(
                db, thread_id, run_id, ai_response, user_message
            )

    @staticmethod
    async def get_message(thread_id: str, message_id: str):
        response = await AiMessageRepository.get_message(thread_id, message_id)
        return UriResponse.get_single_data_response("message", response)

    @staticmethod
    async def get_all_messages(thread_id: str, limit: int, order: str):
        response = await AiMessageRepository.get_all_messages(thread_id, limit, order)
        return response

    @staticmethod
    async def update_message(
        thread_id: str, message_id: str, request_data: AiMessageUpdateRequest
    ):
        response = await AiMessageRepository.update_message(
            thread_id, message_id, request_data
        )
        return UriResponse.update_response("message", response)

    @staticmethod
    async def delete_message(thread_id: str, message_id: str):
        response = await AiMessageRepository.delete_message(thread_id, message_id)
        return UriResponse.delete_response("message", response)

    @staticmethod
    async def delete_all_messages(db: AsyncIOMotorDatabase, thread_id: str):
        response = await AiMessageRepository.delete_all_messages_db(db, thread_id)
        return UriResponse.delete_response("messages", response)

    @staticmethod
    async def handle_voice_message(
        thread_id: str, file: UploadFile, db: AsyncIOMotorDatabase
    ):
        # Save uploaded audio to a temp file
        suffix = os.path.splitext(file.filename)[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_filename = tmp.name
            async with aiofiles.open(temp_filename, "wb") as out_file:
                content = await file.read()
                await out_file.write(content)

        # Transcribe audio using OpenAI Whisper
        with open(temp_filename, "rb") as audio_file:
            transcription_response = openai.audio.transcriptions.create(
                model="whisper-1", file=audio_file
            )

        os.remove(temp_filename)

        transcribed_text = transcription_response.text

        print("Transcribed text: ", transcribed_text)

        # Inject into your existing flow
        request_data = AiMessageCreateRequest(
            role="user", content=[{"type": "text", "text": transcribed_text}]
        )

        result = await AiMessageService.create_message(db, thread_id, request_data)

        return result
