from app.domain.enums.ai_prompt import AIChiefAnalystPrompt
from app.repository.KnowledgeRepository import KnowledgeRepository
from app.repository.BotConversationRepository import BotConversationRepository
from openai import OpenAI
from app.core.config import settings
from app.domain.models.chat_model import (
    ChatModel,
    EmbeddingModel,
    ImageModel,
    AudioModel,
    PlainText,
    SentimentResponse,
)
from motor.motor_asyncio import AsyncIOMotorDatabase

from app import schemas
from typing import Any, List
import asyncio

client = OpenAI(api_key=settings.OPENAI_API_KEY)


class AIService:
    @staticmethod
    def construct_user_prompt(prompt: str):
        return {"role": "user", "content": prompt}

    @staticmethod
    def extract_ai_result(ai_response):
        if isinstance(ai_response, dict):
            return ai_response["choices"][0]["message"]["parsed"]
        return ai_response.choices[0].message.parsed

    @staticmethod
    def build_ai_model(
        messages: List[dict], model: str = "gpt-4o-mini", temperature: float = 0.7
    ):
        return ChatModel(model=model, messages=messages, temperature=temperature)

    @staticmethod
    async def chat_completion(request: ChatModel):
        completion = client.chat.completions.create(
            model=request.model,
            messages=[message.dict() for message in request.messages],
            temperature=request.temperature,
        )
        print("Chat Completion Response: ", completion)
        return completion

    @staticmethod
    async def structured_chat_completion(
        request: ChatModel, response_model: Any = PlainText
    ):
        try:
            loop = asyncio.get_running_loop()

            # Offload sync parse call to thread pool
            completion = await loop.run_in_executor(
                None,
                lambda: client.beta.chat.completions.parse(
                    model=request.model,
                    messages=[message.dict() for message in request.messages],
                    response_format=response_model,
                    temperature=request.temperature,
                    max_tokens=11000,
                ),
            )

        except Exception as e:
            if "LengthFinishReasonError" in str(e):
                return {"error": "Response was truncated due to length limit."}
            raise e

        return completion

    @staticmethod
    async def format_structured_chat_completion(
        request: ChatModel, response_model: Any = None
    ) -> Any:
        """
        Generates a structured chat completion using OpenAI's API.

        Args:
            request (ChatModel): The chat model request containing prompts and configurations.
            response_model (Any): Optional. A class to structure the response for consistency.

        Returns:
            Any: Parsed and structured response based on the response_model class.
        """
        # Call OpenAI's API with the provided request
        completion = client.beta.chat.completions.parse(
            model=request.model,
            messages=[message.dict() for message in request.messages],
            temperature=request.temperature,
            response_format=response_model,
        )

        if response_model:
            try:
                # Parse the response into the desired class
                return response_model(**completion["choices"][0]["message"]["parsed"])
            except Exception as e:
                print(f"Error structuring response: {e}")
                raise ValueError("Failed to adapt response to the provided model.")
        else:
            # Return raw response if no response_model is provided
            return completion

    @staticmethod
    async def create_embedding(request: EmbeddingModel):
        response = client.embeddings.create(
            model="text-embedding-ada-002", input=request.input
        )
        print("Embedding Response: ", response)
        return response

    @staticmethod
    async def generate_image(request: ImageModel):
        response = client.images.create(
            prompt=request.prompt, n=request.n, size=request.size
        )
        print("Image Response: ", response)
        return response

    @staticmethod
    async def generate_audio(request: AudioModel):
        response = client.audio.create(
            model="gpt-4o-mini", voice=request.voice, input=request.input
        )
        print("Audio Response: ", response)
        return response

    @staticmethod
    async def update_knowledge_base(data: dict, db: AsyncIOMotorDatabase):
        if "text" in data:
            title = "Knowledge Base Entry"  # You can update this to something more meaningful
            content = data["text"]
        else:
            title = data.get("title", "No Title")
            content = data.get("content", "")

        knowledge = schemas.KnowledgeCreate(title=title, content=content)
        db_knowledge = await KnowledgeRepository.create_knowledge(
            db=db, knowledge=knowledge
        )
        print("Knowledge base updated with: ", data)
        return schemas.Knowledge(**db_knowledge)

    @staticmethod
    async def query_knowledge_base(query: str, db: AsyncIOMotorDatabase):
        results = await KnowledgeRepository.query_knowledge(query, db)
        return list(results)

    @staticmethod
    async def generate_response_from_knowledge(query: str, kb_results: list) -> Any:
        context = "\n".join([result["content"] for result in kb_results])
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": query},
            {"role": "assistant", "content": context},
        ]
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
        )
        chat_response = response.dict()
        return chat_response["choices"][0]["message"]["content"]

    @staticmethod
    async def save_conversation_history(
        user_id: str, new_messages: list, db: AsyncIOMotorDatabase
    ):
        await BotConversationRepository.create_conversation(user_id, new_messages, db)

    @staticmethod
    async def get_conversation_history(user_id: str, db: AsyncIOMotorDatabase) -> Any:
        conversations = await BotConversationRepository.get_conversations(user_id, db)
        return conversations

    @staticmethod
    async def clear_conversation_history(user_id: str, db: AsyncIOMotorDatabase):
        await BotConversationRepository.delete_conversations(user_id, db)

    @staticmethod
    async def analyze_sentiment(text: str) -> dict:
        """
        Perform sentiment analysis on a given text using OpenAI structured chat completion.

        Args:
            text (str): Text to analyze for sentiment.

        Returns:
            dict: Contains the sentiment score, magnitude, and sentiment type.
        """
        system_prompt = {
            "role": "system",
            "content": AIChiefAnalystPrompt.SENTIMENT_ANALYSIS_SYSTEM_PROMPT.value,
        }

        user_prompt = {
            "role": "user",
            "content": AIChiefAnalystPrompt.SENTIMENT_ANALYSIS_USER_PROMPT.value.format(
                text=text
            ),
        }

        chat_request = AIService.build_ai_model(messages=[system_prompt, user_prompt])

        try:
            response = (
                await AIService.structured_chat_completion(
                    request=chat_request,
                    response_model=SentimentResponse,
                )
            ).dict()
            result: SentimentResponse = response["choices"][0]["message"]["parsed"]
            return {
                "text": text,
                "score": result.get("score", 0.0),
                "magnitude": result.get("magnitude", 0.0),
                "sentiment": result.get("sentiment", 0.0),
            }
        except Exception as e:
            return {"error": str(e)}
