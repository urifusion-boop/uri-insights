from fastapi import APIRouter, Depends, File, Form, UploadFile
from app.services.AiMessageService import AiMessageService
from app.domain.requests.aimessage_requests import (
    AiMessageCreateRequest,
    AiMessageUpdateRequest,
)
from app.domain.responses.uri_response import UriResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import get_db_dependency

router = APIRouter()


@router.post("/create/{thread_id}", summary="Create a message in a thread")
async def create_message(
    thread_id: str,
    request_data: AiMessageCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await AiMessageService.create_message(db, thread_id, request_data)
    return UriResponse.get_status_response(response=response)


@router.get("/getById/{thread_id}/{message_id}", summary="Retrieve a message by ID")
async def get_message(thread_id: str, message_id: str):
    response = await AiMessageService.get_message(thread_id, message_id)
    return UriResponse.get_status_response(response=response)


@router.get("/getByThread/{thread_id}", summary="List all messages in a thread")
async def get_all_messages(thread_id: str, limit: int = 20, order: str = "desc"):
    response = await AiMessageService.get_all_messages(thread_id, limit, order)
    return UriResponse.get_status_response(response=response)


@router.post("/update/{thread_id}/{message_id}", summary="Update an existing message")
async def update_message(
    thread_id: str,
    message_id: str,
    request_data: AiMessageUpdateRequest,
):
    response = await AiMessageService.update_message(
        thread_id, message_id, request_data
    )
    return UriResponse.get_status_response(response=response)


@router.delete("/delete/{thread_id}/{message_id}", summary="Delete a message")
async def delete_message(thread_id: str, message_id: str):
    response = await AiMessageService.delete_message(thread_id, message_id)
    return UriResponse.get_status_response(response=response)


@router.delete("/deleteAll/{thread_id}", summary="Delete a message")
async def delete_all_messages(
    thread_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    response = await AiMessageService.delete_all_messages(db, thread_id)
    return UriResponse.get_status_response(response=response)


@router.post(
    "/voice/message/{thread_id}", summary="Accept audio message to AI assistant"
)
async def handle_voice_message(
    thread_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    file: UploadFile = File(...),
):
    response = await AiMessageService.handle_voice_message(
        thread_id=thread_id, file=file, db=db
    )
    return UriResponse.get_status_response(response=response)
