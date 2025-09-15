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


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(JWTBearer())])
async def botchat(
    request: ChatRequest,
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    try:
        # Retrieve conversation history
        history = await AIService.get_conversation_history(user_id, db)

        # Add current query to the conversation history
        current_message = {"role": "user", "content": request.messages[0].content}
        history.append(current_message)

        # Query the knowledge base
        kb_results = await AIService.query_knowledge_base(
            request.messages[0].content, db
        )

        if kb_results:
            tailored_response = await AIService.generate_response_from_knowledge(
                request.messages[0].content, kb_results
            )
            response_message = ChatMessage(
                role="assistant", content=tailored_response
            ).dict()
        else:
            chat_model = ChatModel(model="gpt-4o-mini", messages=history)
            res = await AIService.chat_completion(chat_model)
            chat_response = res.dict()
            response_message = chat_response["choices"][0]["message"]

        # Add the response to the conversation history
        new_messages = [
            current_message,
            {"role": "assistant", "content": response_message["content"]},
        ]

        # Save the updated conversation history
        await AIService.save_conversation_history(user_id, new_messages, db)

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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear-chat", dependencies=[Depends(JWTBearer())])
async def clear_conversation(
    user_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    await AIService.clear_conversation_history(user_id, db)
    return {"message": "Conversation history cleared successfully"}
