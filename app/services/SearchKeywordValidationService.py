"""
SearchKeywordValidationService.py
AI-powered validation to detect mismatch between what user sells vs what they're searching for.
Prevents irrelevant lead generation by warning users when category_context doesn't match solution_context.
"""

from typing import Dict, Any, Optional
import json
from app.services.AIService import AIService


class SearchKeywordValidationService:
    """
    Validates if user's search keywords/context align with their business solution.

    Example scenarios:
    - Sells laptops, searches for "skin care" → MISMATCH
    - Sells laptops, searches for "IT equipment complaints" → MATCH
    - Sells laptops, job boards search for "DevOps Engineer" → MATCH (hiring signal)
    """

    @staticmethod
    async def validate_search_context(
        solution_context: str,
        category_context: Optional[str] = None,
        social_keywords: Optional[list] = None,
        job_keywords: Optional[list] = None,
        has_social_platforms: bool = False,
        has_job_boards: bool = False
    ) -> Dict[str, Any]:
        """
        Validates if search context matches business solution.

        Args:
            solution_context: What the user sells/offers (from Job Boards field)
            category_context: What people are complaining about (from Social Platforms field)
            social_keywords: Keywords for social platform search
            job_keywords: Keywords for job board search
            has_social_platforms: Whether user selected social platforms
            has_job_boards: Whether user selected job boards

        Returns:
            {
                "is_valid": bool,  # Overall validation result
                "match_score": float,  # 0.0-1.0 confidence in match
                "social_platform_match": float,  # How well social search matches business
                "job_board_match": float,  # How well job search matches business
                "recommendation": str,  # "proceed" | "use_only_social" | "use_only_job_boards" | "update_search"
                "reasoning": str,  # Human-readable explanation
                "suggested_social_keywords": list,  # AI-suggested keywords that would match better
            }
        """

        # If only one source selected, no validation needed
        if not has_social_platforms or not has_job_boards:
            return {
                "is_valid": True,
                "match_score": 1.0,
                "social_platform_match": 1.0 if has_social_platforms else 0.0,
                "job_board_match": 1.0 if has_job_boards else 0.0,
                "recommendation": "proceed",
                "reasoning": "Only one signal source selected, no mismatch possible",
                "suggested_social_keywords": []
            }

        # If no context provided, skip validation
        if not solution_context or not category_context:
            return {
                "is_valid": True,
                "match_score": 0.8,
                "social_platform_match": 0.8,
                "job_board_match": 0.8,
                "recommendation": "proceed",
                "reasoning": "Insufficient context for validation",
                "suggested_social_keywords": []
            }

        # Build AI prompt
        prompt = f"""You are a business-context validator. Analyze if the user's search makes sense for their business.

USER'S BUSINESS (what they sell):
{solution_context}

SOCIAL PLATFORM SEARCH (what people are complaining about):
Category Context: {category_context or 'Not specified'}
Keywords: {', '.join(social_keywords) if social_keywords else 'Not specified'}

JOB BOARD SEARCH (hiring signals):
Job Keywords: {', '.join(job_keywords) if job_keywords else 'Auto-generated from solution context'}

TASK:
1. Determine if the social platform search aligns with the business solution
2. Score the match from 0.0 (completely unrelated) to 1.0 (perfect match)
3. Provide a recommendation

EXAMPLES:
- Business: "Enterprise laptops and IT equipment"
  Social Search: "skin care issues"
  → social_platform_match: 0.05, recommendation: "use_only_job_boards"

- Business: "Enterprise laptops and IT equipment"
  Social Search: "slow computers, IT equipment complaints"
  → social_platform_match: 0.95, recommendation: "proceed"

- Business: "Marketing automation software"
  Social Search: "struggling with manual marketing tasks"
  → social_platform_match: 0.90, recommendation: "proceed"

OUTPUT FORMAT (JSON only, no markdown):
{{
    "social_platform_match": 0.0-1.0,
    "job_board_match": 0.0-1.0,
    "recommendation": "proceed" | "use_only_social" | "use_only_job_boards" | "update_search",
    "reasoning": "Brief explanation of the match/mismatch",
    "suggested_social_keywords": ["keyword1", "keyword2", "keyword3"]
}}

Note: Job boards almost always match because they're hiring signals (any business can target hiring companies).
Focus primarily on validating if social platform search makes sense."""

        try:
            # Call OpenAI using same approach as AIService
            from openai import OpenAI
            from app.core.config import settings

            client = OpenAI(api_key=settings.OPENAI_API_KEY)

            messages = [
                {"role": "system", "content": "You are a business context validator. Always respond with valid JSON only, no markdown."},
                {"role": "user", "content": prompt}
            ]

            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Same model as auto-populate uses
                messages=messages,
                temperature=0.3,
                max_tokens=500
            )

            response_text = response.choices[0].message.content.strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()

            # Parse JSON response
            result = json.loads(response_text)

            # Calculate overall match score (weighted toward social since job boards always match)
            overall_match = (
                0.7 * result.get("social_platform_match", 0.5) +
                0.3 * result.get("job_board_match", 0.8)
            )

            # Determine if valid (threshold: 0.4)
            is_valid = overall_match >= 0.4

            return {
                "is_valid": is_valid,
                "match_score": overall_match,
                "social_platform_match": result.get("social_platform_match", 0.5),
                "job_board_match": result.get("job_board_match", 0.8),
                "recommendation": result.get("recommendation", "proceed"),
                "reasoning": result.get("reasoning", "Unable to determine match quality"),
                "suggested_social_keywords": result.get("suggested_social_keywords", [])
            }

        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse AI validation response: {e}")
            print(f"Raw response: {response}")
            # Fail open - allow search to proceed
            return {
                "is_valid": True,
                "match_score": 0.5,
                "social_platform_match": 0.5,
                "job_board_match": 0.8,
                "recommendation": "proceed",
                "reasoning": "Validation error - proceeding with caution",
                "suggested_social_keywords": []
            }

        except Exception as e:
            print(f"❌ Search validation error: {e}")
            # Fail open - allow search to proceed
            return {
                "is_valid": True,
                "match_score": 0.5,
                "social_platform_match": 0.5,
                "job_board_match": 0.8,
                "recommendation": "proceed",
                "reasoning": "Validation unavailable - proceeding with search",
                "suggested_social_keywords": []
            }
