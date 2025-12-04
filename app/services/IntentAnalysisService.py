"""
IntentAnalysisService - Core LLM-powered intent analysis for CLG upgrade

Analyzes social media posts to detect buying intent using 5 categories:
1. Direct Intent: "Where can I buy sunscreen?"
2. Implied Intent: "Harmattan is making my skin dry"
3. Problem Intent: "My acne won't go away"
4. Comparison Intent: "CeraVe vs La Roche Posay?"
5. Competitor Negative: "The Ordinary ruined my skin"

Returns multi-dimensional scores:
- intent_score (0-1)
- relevance_score (0-1)
- urgency_flag (bool)
- sentiment (positive/negative/neutral)
- intent_category (direct/implied/problem/comparison/competitor_negative)
- final_score (0-1)
- reasoning (string)
"""

from typing import Optional, List, Any
from pydantic import BaseModel, Field
from enum import Enum
import logging

from app.services.AIService import AIService
from app.domain.models.chat_model import ChatModel

logger = logging.getLogger(__name__)


class IntentCategory(str, Enum):
    DIRECT = "direct"
    IMPLIED = "implied"
    PROBLEM = "problem"
    COMPARISON = "comparison"
    COMPETITOR_NEGATIVE = "competitor_negative"
    UNKNOWN = "unknown"


class SentimentType(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"




class IntentAnalysisResult(BaseModel):
    """Structured response model for intent analysis"""
    intent_score: float = Field(ge=0, le=1, description="How strong is the buying intent (0-1)")
    relevance_score: float = Field(ge=0, le=1, description="How relevant to the category/product (0-1)")
    urgency_flag: bool = Field(description="Is there urgency in the post?")
    sentiment: SentimentType = Field(description="Overall sentiment of the post")
    intent_category: IntentCategory = Field(description="Type of intent detected")
    reasoning: str = Field(description="Brief explanation of why this score was given")


class CategoryConfig(BaseModel):
    """Configuration for category-specific intent analysis"""
    category_context: str
    keywords: List[str] = []
    implied_keywords: List[str] = []
    competitors: List[str] = []
    buying_signals: List[str] = []
    excluded_keywords: List[str] = []
    location: List[str] = []  # Geographic targeting (cities, regions, countries)


class IntentAnalysisService:
    """
    Service for analyzing social media posts for buying intent
    Uses LLM to detect direct and implied intent signals with context-aware promotional filtering
    """

    SYSTEM_PROMPT = """You are an expert lead qualification analyst. Your task is to determine if a social media post author matches what the user is looking for.

CRITICAL UNDERSTANDING:
Read the USER'S BUSINESS CONTEXT carefully. They could be looking for ANYONE or ANYTHING:
- Buyers/customers who need their product
- Job seekers who want employment
- Sellers/vendors who offer what they need
- Partners, friends, spouses, prayer partners, study groups
- Literally ANYTHING - always read their context first

YOUR JOB:
1. Understand WHAT the user wants to find (from their business context)
2. Check if this POST AUTHOR is expressing that need/intent
3. Distinguish between GENUINE personal expression vs PROMOTIONAL advertising

UNIVERSAL FILTERING RULE - Detect Promotional Language:

Posts are PROMOTIONAL (score 0.0) if they use:
- **Audience-directed questions**: "Do YOU need?", "Are YOU looking for?", "Want to?", "Need a?"
- **Advertising language**: "We offer", "Contact me", "PM me", "DM for", "Check out my", "Visit our"
- **Sales tactics**: Prices listed, payment plans, "SALE", "PROMO", "Limited time", emojis for promotion (🔥💯✨)
- **Call-to-action**: "Apply now", "Order today", "Book now", "Sign up", "Get yours"
- **Business language**: "Our services", "We provide", "Available for", "Accepting orders"

Posts are GENUINE (score normally) if they express:
- **Personal need/want**: "I need", "I'm looking for", "Can someone help", "Does anyone know"
- **Personal problems**: "My laptop is broken", "I can't find", "I'm struggling with"
- **Personal situations**: "Just moved to", "Starting to", "Planning my"
- **Questions seeking help**: "Where can I find", "Who knows a good", "Recommendations for"
- **Complaints/frustrations**: "This is so expensive", "Why is X so hard", "Fed up with"

Scoring Guidelines:
- intent_score: 0.8-1.0 = Direct explicit match ("I need X", "Looking for Y")
                0.6-0.79 = Strong implied intent (problems, frustrations, questions)
                0.4-0.59 = Moderate implied (situations, lifestyle mentions)
                0.2-0.39 = Weak signals
                0.0 = Promotional/advertising OR excluded keywords OR opposite side

- relevance_score: How well does the post match the user's specific context?

- urgency_flag: True if urgent/emotional language

- sentiment: Consider if negative sentiment indicates readiness for change

Be generous with genuine personal expression, but ruthless with promotional content."""

    @staticmethod
    def _build_analysis_prompt(text: str, config: CategoryConfig) -> str:
        """Build the analysis prompt with category context"""
        location_text = ""
        if config.location:
            location_text = f"""
TARGET LOCATION/GEOGRAPHY (CRITICAL - post must match this location):
{', '.join(config.location)}
⚠️ IMPORTANT: If the post mentions a DIFFERENT location/city/country than the target location above, set intent_score to 0.0 and relevance_score to 0.0 immediately.
"""

        return f"""Analyze this social media post to determine if the author is a qualified lead based on the user's business context.

POST: "{text}"

USER'S BUSINESS CONTEXT (what they do and who they're looking for):
{config.category_context}
{location_text}
DIRECT KEYWORDS (explicit signals to look for):
{', '.join(config.keywords) if config.keywords else 'None specified'}

IMPLIED KEYWORDS (indirect signals - problems, situations, life changes):
{', '.join(config.implied_keywords) if config.implied_keywords else 'None specified'}

COMPETITORS TO MONITOR (mentions of alternatives/competitors):
{', '.join(config.competitors) if config.competitors else 'None specified'}

INTENT SIGNALS (phrases showing readiness/interest):
{', '.join(config.buying_signals) if config.buying_signals else 'None specified'}

EXCLUDED KEYWORDS (filter out these - wrong audience type):
{', '.join(config.excluded_keywords) if config.excluded_keywords else 'None specified'}

Based on the USER'S BUSINESS CONTEXT, determine if this post author is a good match for what they're looking for. Consider both direct and implied signals. If location is specified, posts must match that geographic area."""

    @staticmethod
    async def analyze_post(
        text: str,
        config: CategoryConfig,
        model: str = "gpt-4o-mini"
    ) -> IntentAnalysisResult:
        """
        Analyze a single post for buying intent using universal prompt

        Args:
            text: The social media post text
            config: Category configuration with keywords and context
            model: LLM model to use (default: gpt-4o-mini for cost efficiency)

        Returns:
            IntentAnalysisResult with scores and reasoning
        """
        try:
            # Use universal system prompt
            system_prompt = IntentAnalysisService.SYSTEM_PROMPT

            # Build the user prompt
            user_prompt = IntentAnalysisService._build_analysis_prompt(text, config)

            # Create chat model with universal prompt
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            ai_model = AIService.build_ai_model(messages, model=model, temperature=0.1)

            # Get structured response
            response = await AIService.structured_chat_completion(
                ai_model,
                response_model=IntentAnalysisResult
            )

            result = AIService.extract_ai_result(response)

            return result

        except Exception as e:
            logger.error(f"Intent analysis failed for text: {text[:100]}... Error: {e}")
            # Return low-score result on error
            return IntentAnalysisResult(
                intent_score=0.0,
                relevance_score=0.0,
                urgency_flag=False,
                sentiment=SentimentType.NEUTRAL,
                intent_category=IntentCategory.UNKNOWN,
                reasoning=f"Analysis failed: {str(e)}"
            )

    @staticmethod
    async def analyze_batch(
        posts: List[str],
        config: CategoryConfig,
        model: str = "gpt-4o-mini"
    ) -> List[IntentAnalysisResult]:
        """
        Analyze multiple posts for buying intent

        Args:
            posts: List of social media post texts
            config: Category configuration
            model: LLM model to use

        Returns:
            List of IntentAnalysisResult
        """
        import asyncio

        tasks = [
            IntentAnalysisService.analyze_post(post, config, model)
            for post in posts
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions in results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch analysis failed for post {i}: {result}")
                processed_results.append(IntentAnalysisResult(
                    intent_score=0.0,
                    relevance_score=0.0,
                    urgency_flag=False,
                    sentiment=SentimentType.NEUTRAL,
                    intent_category=IntentCategory.UNKNOWN,
                    reasoning=f"Analysis failed: {str(result)}"
                ))
            else:
                processed_results.append(result)

        return processed_results

    @staticmethod
    def calculate_final_score(
        intent_score: float,
        relevance_score: float,
        urgency_flag: bool
    ) -> float:
        """
        Calculate final qualification score

        Formula: (intent_score * 0.5) + (relevance_score * 0.35) + (urgency_bonus * 0.15)
        """
        urgency_bonus = 1.0 if urgency_flag else 0.5

        final_score = (
            (intent_score * 0.5) +
            (relevance_score * 0.35) +
            (urgency_bonus * 0.15)
        )

        return round(min(final_score, 1.0), 2)

    @staticmethod
    def meets_thresholds(
        result: IntentAnalysisResult,
        intent_min: float = 0.55,
        relevance_min: float = 0.50,
        final_min: float = 0.60
    ) -> bool:
        """
        Check if analysis result meets qualification thresholds

        Default thresholds from requirements:
        - intent_score >= 0.55
        - relevance_score >= 0.50
        - final_score >= 0.60
        """
        final_score = IntentAnalysisService.calculate_final_score(
            result.intent_score,
            result.relevance_score,
            result.urgency_flag
        )

        return (
            result.intent_score >= intent_min and
            result.relevance_score >= relevance_min and
            final_score >= final_min
        )

    @staticmethod
    def filter_qualified_leads(
        results: List[tuple[str, IntentAnalysisResult]],
        intent_min: float = 0.55,
        relevance_min: float = 0.50,
        final_min: float = 0.60
    ) -> List[tuple[str, IntentAnalysisResult, float]]:
        """
        Filter results to only include qualified leads

        Args:
            results: List of (post_text, IntentAnalysisResult) tuples
            intent_min, relevance_min, final_min: Qualification thresholds

        Returns:
            List of (post_text, IntentAnalysisResult, final_score) for qualified leads
        """
        qualified = []

        for post_text, result in results:
            if IntentAnalysisService.meets_thresholds(result, intent_min, relevance_min, final_min):
                final_score = IntentAnalysisService.calculate_final_score(
                    result.intent_score,
                    result.relevance_score,
                    result.urgency_flag
                )
                qualified.append((post_text, result, final_score))

        # Sort by final_score descending
        qualified.sort(key=lambda x: x[2], reverse=True)

        return qualified
