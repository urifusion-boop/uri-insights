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
    AINextStepsResponse,
    NextStepAction,
)
from motor.motor_asyncio import AsyncIOMotorDatabase

from app import schemas
from typing import Any, List, Dict, Optional
import asyncio
from datetime import datetime
import uuid

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
                    max_tokens=2000,  # Reduced from 11000 - structured responses should be small
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

    @staticmethod
    async def analyze_with_structured_output(
        prompt: str,
        response_model: Any,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7
    ) -> Any:
        """
        Analyze text with structured output using OpenAI's structured output feature.

        Args:
            prompt: The analysis prompt
            response_model: Pydantic model for structured response
            model: OpenAI model to use
            temperature: Temperature for generation

        Returns:
            Parsed response matching the response_model schema
        """
        messages = [
            {"role": "system", "content": "You are an expert analyst. Provide accurate, structured analysis."},
            {"role": "user", "content": prompt}
        ]

        chat_request = ChatModel(
            model=model,
            messages=messages,
            temperature=temperature
        )

        try:
            response = await AIService.structured_chat_completion(
                request=chat_request,
                response_model=response_model
            )

            # Extract the parsed result
            result = AIService.extract_ai_result(response)
            return result

        except Exception as e:
            print(f"Error in analyze_with_structured_output: {e}")
            raise

    @staticmethod
    async def generate_lead_next_steps(
        lead_data: Dict[str, Any],
        user_goal: Optional[str] = None,
        lead_type: str = "PERSON"
    ) -> Dict[str, Any]:
        """
        Generate actionable next steps for a lead based on user's business goal.

        Args:
            lead_data (Dict): Lead information including context, post content, job listing, etc.
            user_goal (str): User's business goal/reason for generating leads
            lead_type (str): Type of lead (PERSON, ORGANIZATION, CONVERSATIONAL, etc.)

        Returns:
            Dict: Structured next steps with actions, reasoning, and priority
        """
        # Extract relevant lead context
        lead_name = lead_data.get("first_name", "") or lead_data.get("company_name", "this lead")
        lead_source = lead_data.get("lead_source", "unknown")
        post_content = lead_data.get("mention", "") or lead_data.get("summary_of_mention", "")
        job_description = lead_data.get("lead_reason", "")
        lead_link = lead_data.get("lead_link", "")
        keywords_matched = lead_data.get("keywords", [])

        # Fallback goal if not provided
        if not user_goal:
            user_goal = "Convert this lead into a customer"

        # Build context based on lead type
        if lead_type == "CONVERSATIONAL" or post_content:
            context_section = f"""
Lead Context:
- Name/Company: {lead_name}
- Source: Social media post ({lead_source})
- Post Content: "{post_content}"
- Keywords Matched: {', '.join(keywords_matched) if keywords_matched else 'N/A'}
- Link: {lead_link}
"""
        elif "job" in lead_source.lower() or job_description:
            context_section = f"""
Lead Context:
- Company: {lead_name}
- Source: Job listing ({lead_source})
- Job Description/Problem: {job_description}
- Keywords Matched: {', '.join(keywords_matched) if keywords_matched else 'N/A'}
- Link: {lead_link}
"""
        else:
            context_section = f"""
Lead Context:
- Name/Company: {lead_name}
- Source: {lead_source}
- Description: {job_description or post_content or 'No additional context'}
- Keywords Matched: {', '.join(keywords_matched) if keywords_matched else 'N/A'}
"""

        system_prompt = {
            "role": "system",
            "content": """You are a sales strategy expert. Generate 2-4 specific, actionable next steps for converting a lead.
Each step should be:
- Concrete and specific (not generic advice)
- Prioritized (high/medium/low)
- Platform-specific where applicable
- Include reasoning based on the lead's context
- Assigned a confidence score (0.0-1.0)

Consider: timing, relevance to the user's goal, and the lead's specific situation."""
        }

        user_prompt = {
            "role": "user",
            "content": f"""User's Business Goal: {user_goal}

{context_section}

Generate specific next steps this user should take to convert this lead. Each step should include:
1. The specific action to take
2. Why this action makes sense given the context
3. Priority level (high/medium/low)
4. Confidence score
5. Platform to use (if applicable: linkedin, twitter, email, phone, etc.)

Focus on practical, immediate actions."""
        }

        chat_request = AIService.build_ai_model(
            messages=[system_prompt, user_prompt],
            model="gpt-4o",  # Use better model for strategic advice
            temperature=0.7
        )

        try:
            response = await AIService.structured_chat_completion(
                request=chat_request,
                response_model=AINextStepsResponse,
            )

            result: Dict = response.dict() if hasattr(response, 'dict') else response
            parsed_steps: Dict = result["choices"][0]["message"]["parsed"]

            # Add step_id and timestamp to each step
            for step in parsed_steps.get("steps", []):
                if "step_id" not in step or not step["step_id"]:
                    step["step_id"] = str(uuid.uuid4())
                step["completed"] = False
                step["completed_at"] = None

            # Build final response
            return {
                "steps": parsed_steps.get("steps", []),
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "based_on_goal": user_goal,
                "summary": parsed_steps.get("summary", f"{len(parsed_steps.get('steps', []))} actions recommended")
            }
        except Exception as e:
            print(f"Error generating next steps: {e}")
            # Return fallback generic steps
            return {
                "steps": [
                    {
                        "step_id": str(uuid.uuid4()),
                        "action": "Review the lead details and prepare personalized outreach",
                        "reasoning": "Understanding the lead's context is crucial for effective communication",
                        "priority": "high",
                        "confidence": 0.85,
                        "platform": None,
                        "completed": False,
                        "completed_at": None
                    }
                ],
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "based_on_goal": user_goal,
                "summary": "1 action recommended (fallback due to AI error)"
            }
