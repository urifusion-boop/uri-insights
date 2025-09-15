from app.domain.requests.chat_requests import (
    ChatRequest,
    ChatMessage,
    EmbeddingRequest,
    ImageRequest,
    AudioRequest,
)
from app.domain.models.chat_model import (
    ChatModel,
    ChatMessage as ChatMessageModel,
    EmbeddingModel,
    ImageModel,
    AudioModel,
)


def map_chat_request_to_chat_model(request: ChatRequest) -> ChatModel:
    messages = [
        ChatMessageModel(role=msg.role, content=msg.content) for msg in request.messages
    ]
    return ChatModel(messages=messages)


def map_embedding_request_to_embedding_model(
    request: EmbeddingRequest,
) -> EmbeddingModel:
    return EmbeddingModel(**request.dict())


def map_image_request_to_image_model(request: ImageRequest) -> ImageModel:
    return ImageModel(**request.dict())


def map_audio_request_to_audio_model(request: AudioRequest) -> AudioModel:
    return AudioModel(**request.dict())
