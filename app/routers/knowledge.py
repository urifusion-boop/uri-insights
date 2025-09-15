from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from app.domain.requests.chat_requests import ChatRequest
from app.domain.responses.chat_responses import ChatResponse, ChatChoice, ChatUsage
from app.domain.models.chat_model import ChatModel, ChatMessage
from app.core.mapper_config import map_chat_request_to_chat_model
from app.services.AIService import AIService
from app.core.auth_bearer import JWTBearer
from app.domain.responses.uri_response import UriResponse
from app.dependencies import get_db_dependency
from motor.motor_asyncio import AsyncIOMotorDatabase


import json
import fitz  # PyMuPDF

router = APIRouter()


@router.post("/upload-knowledge", dependencies=[Depends(JWTBearer())])
async def upload_knowledge(
    file: UploadFile = File(...), db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    if file.content_type == "application/pdf":
        content = await file.read()
        text = extract_text_from_pdf(content)
        data = {"text": text}
    else:
        content = await file.read()
        data = json.loads(content)
    await AIService.update_knowledge_base(data, db)
    return {"message": "Knowledge base updated successfully"}


def extract_text_from_pdf(content: bytes) -> str:
    pdf_document = fitz.open(stream=content, filetype="pdf")
    text = ""
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        text += page.get_text()
    return text


@router.post(
    "/query-knowledge", response_model=ChatResponse, dependencies=[Depends(JWTBearer())]
)
async def query_knowledge(
    request: ChatRequest, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    query = request.messages[0].content
    kb_results = await AIService.query_knowledge_base(query, db)
    if kb_results:
        tailored_response = await AIService.generate_response_from_knowledge(
            query, kb_results
        )
        print("Tailored Response : ", tailored_response)
        response_message = ChatMessage(
            role="assistant", content=tailored_response
        ).dict()
        response = {
            "id": "knowledge-base-response",
            "object": "chat.completion",
            "model": "knowledge-base",
            "usage": {
                "completion_tokens": 0,  # These values can be adjusted as necessary
                "prompt_tokens": 0,
                "total_tokens": 0,
            },
            "choices": [
                {
                    "message": response_message,
                    "finish_reason": "stop",
                    "index": 0,
                    "logprobs": None,
                }
            ],
        }
        return UriResponse.get_status_response(response)
    else:
        chat_model = map_chat_request_to_chat_model(request)
        chat_response = await AIService.chat_completion(chat_model)
        return UriResponse.get_status_response(chat_response)
