from fastapi import APIRouter, Depends
from app.domain.requests.chat_requests import (
    ChatRequest,
    EmbeddingRequest,
    ImageRequest,
    AudioRequest,
)
from app.domain.responses.chat_responses import (
    ChatResponse,
    EmbeddingResponse,
    ImageResponse,
    AudioResponse,
    ChatChoice,
)
from app.domain.models.chat_model import (
    ChatModel,
    EmbeddingModel,
    ImageModel,
    AudioModel,
)
from app.core.mapper_config import (
    map_chat_request_to_chat_model,
    map_embedding_request_to_embedding_model,
    map_image_request_to_image_model,
    map_audio_request_to_audio_model,
)
from app.services.AIService import AIService
from app.core.auth_bearer import JWTBearer
from app.domain.responses.uri_response import UriResponse

router = APIRouter()


@router.post("/chat", dependencies=[Depends(JWTBearer())])
async def chat_completion(request: ChatRequest):
    chat_model = map_chat_request_to_chat_model(request)
    response = await AIService.chat_completion(chat_model)
    return UriResponse.get_status_response(response.dict())


@router.post("/embedding", dependencies=[Depends(JWTBearer())])
async def create_embedding(request: EmbeddingRequest):
    embed_model = map_embedding_request_to_embedding_model(request)
    response = await AIService.create_embedding(embed_model)
    return UriResponse.get_status_response(response.dict())


@router.post("/image", dependencies=[Depends(JWTBearer())])
async def generate_image(request: ImageRequest):
    image_model = map_image_request_to_image_model(request)
    response = await AIService.generate_image(image_model)
    return UriResponse.get_status_response(response.dict())


@router.post("/audio", dependencies=[Depends(JWTBearer())])
async def generate_audio(request: AudioRequest):
    audio_model = map_audio_request_to_audio_model(request)
    response = await AIService.generate_audio(audio_model)
    return UriResponse.get_status_response(response.dict())
