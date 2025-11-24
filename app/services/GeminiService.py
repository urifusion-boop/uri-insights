"""
GeminiService - Google Gemini API integration for LLM fallback

Used as a fallback when OpenAI is unavailable.
Supports:
- Gemini 2.0 Flash (fast, cost-effective)
- Gemini 1.5 Pro (complex analysis)
- Gemini 3.0 (latest - when available)

Cost: ~50% cheaper than OpenAI for fallback scenarios
"""

from typing import Any, List, Optional
from pydantic import BaseModel
import logging
import json
import asyncio

from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiService:
    """
    Google Gemini API integration for fallback LLM calls
    """

    # Available models
    FLASH_MODEL = "gemini-2.0-flash"  # Fast, cost-effective
    PRO_MODEL = "gemini-1.5-pro"       # Higher quality
    LATEST_MODEL = "gemini-2.0-flash"  # Default to flash until 3.0 is available

    _client = None

    @classmethod
    def _get_client(cls):
        """Lazy initialization of Gemini client"""
        if cls._client is None:
            try:
                import google.generativeai as genai

                api_key = getattr(settings, 'GEMINI_API_KEY', None)
                if not api_key:
                    raise ValueError("GEMINI_API_KEY not configured in settings")

                genai.configure(api_key=api_key)
                cls._client = genai

            except ImportError:
                raise ImportError(
                    "google-generativeai package not installed. "
                    "Install with: pip install google-generativeai"
                )

        return cls._client

    @staticmethod
    async def structured_completion(
        messages: List[dict],
        model: str = "gemini-2.0-flash",
        response_model: Any = None,
        temperature: float = 0.1
    ) -> Any:
        """
        Call Gemini with structured output

        Args:
            messages: Chat messages (will be converted to Gemini format)
            model: Gemini model name
            response_model: Pydantic model for response structure
            temperature: Generation temperature

        Returns:
            Parsed response matching response_model
        """
        try:
            genai = GeminiService._get_client()

            # Convert messages to Gemini format
            prompt = GeminiService._convert_messages_to_prompt(messages)

            # Add JSON schema instruction if response_model provided
            if response_model:
                schema_instruction = GeminiService._get_schema_instruction(response_model)
                prompt = f"{prompt}\n\n{schema_instruction}"

            # Create model and generate
            gemini_model = genai.GenerativeModel(
                model_name=model,
                generation_config={
                    "temperature": temperature,
                    "response_mime_type": "application/json" if response_model else "text/plain"
                }
            )

            # Run in executor to not block event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: gemini_model.generate_content(prompt)
            )

            # Parse response
            if response_model:
                result = GeminiService._parse_response(response.text, response_model)
                return result
            else:
                return response.text

        except Exception as e:
            logger.error(f"Gemini completion failed: {e}")
            raise

    @staticmethod
    def _convert_messages_to_prompt(messages: List[dict]) -> str:
        """Convert OpenAI-style messages to single prompt for Gemini"""
        parts = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                parts.append(f"SYSTEM INSTRUCTIONS:\n{content}\n")
            elif role == "user":
                parts.append(f"USER:\n{content}\n")
            elif role == "assistant":
                parts.append(f"ASSISTANT:\n{content}\n")

        return "\n".join(parts)

    @staticmethod
    def _get_schema_instruction(response_model: Any) -> str:
        """Generate JSON schema instruction from Pydantic model"""
        try:
            schema = response_model.model_json_schema()
            schema_str = json.dumps(schema, indent=2)

            return f"""
IMPORTANT: You must respond with valid JSON that matches this exact schema:

{schema_str}

Return ONLY the JSON object, no additional text or explanation.
"""
        except Exception:
            # Fallback for non-Pydantic models
            return "Respond with a valid JSON object."

    @staticmethod
    def _parse_response(response_text: str, response_model: Any) -> Any:
        """Parse Gemini response into Pydantic model"""
        try:
            # Clean up response text (remove markdown code blocks if present)
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            # Parse JSON
            data = json.loads(cleaned)

            # Validate with Pydantic model
            if hasattr(response_model, "model_validate"):
                return response_model.model_validate(data)
            elif hasattr(response_model, "parse_obj"):
                return response_model.parse_obj(data)
            else:
                return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            raise ValueError(f"Invalid JSON response from Gemini: {e}")

    @staticmethod
    async def simple_completion(
        prompt: str,
        model: str = "gemini-2.0-flash",
        temperature: float = 0.7
    ) -> str:
        """
        Simple text completion without structured output

        Args:
            prompt: The prompt text
            model: Gemini model name
            temperature: Generation temperature

        Returns:
            Generated text
        """
        try:
            genai = GeminiService._get_client()

            gemini_model = genai.GenerativeModel(
                model_name=model,
                generation_config={"temperature": temperature}
            )

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: gemini_model.generate_content(prompt)
            )

            return response.text

        except Exception as e:
            logger.error(f"Gemini simple completion failed: {e}")
            raise

    @staticmethod
    def is_available() -> bool:
        """Check if Gemini service is properly configured"""
        try:
            api_key = getattr(settings, 'GEMINI_API_KEY', None)
            if not api_key:
                return False

            # Try to import the library
            import google.generativeai
            return True

        except ImportError:
            return False
