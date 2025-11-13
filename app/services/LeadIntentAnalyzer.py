"""
AI-powered Lead Intent Analyzer Service
Analyzes leads against business context to determine relevance and intent.
"""

import asyncio
import json
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from openai import AsyncOpenAI

from app.core.config import settings
from app.services.AIService import AIService
from app.domain.enums.ai_prompt import AIChiefAnalystPrompt


class LeadIntentAnalyzer:
    """
    Service for analyzing lead relevance and intent using AI and semantic matching.
    Automatically filters leads to match user's business purpose.
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.embedding_cache: Dict[str, List[float]] = {}
        self.relevance_threshold = 0.65  # Minimum score to consider a lead relevant

    async def analyze_lead_batch(
        self,
        leads: List[Dict[str, Any]],
        business_context: Dict[str, Any],
        threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Analyze a batch of leads and filter by relevance.
        
        Args:
            leads: List of lead dictionaries
            business_context: Business info containing keywords, summary, intent_type
            threshold: Optional custom relevance threshold (default: 0.65)
            
        Returns:
            List of filtered and scored leads
        """
        threshold = threshold or self.relevance_threshold
        
        # Process leads concurrently
        analysis_tasks = [
            self.analyze_single_lead(lead, business_context)
            for lead in leads
        ]
        
        results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
        
        # Filter and enrich leads
        filtered_leads = []
        for lead, result in zip(leads, results):
            if isinstance(result, Exception):
                print(f"Error analyzing lead: {result}")
                continue
            
            relevance_score, intent_type, reasoning = result
            
            # Only include leads above threshold
            if relevance_score >= threshold:
                lead["ai_relevance_score"] = round(relevance_score, 3)
                lead["intent_type"] = intent_type
                lead["match_reasoning"] = reasoning
                filtered_leads.append(lead)
        
        # Sort by relevance score (highest first)
        filtered_leads.sort(key=lambda x: x.get("ai_relevance_score", 0), reverse=True)
        
        return filtered_leads

    async def analyze_single_lead(
        self,
        lead: Dict[str, Any],
        business_context: Dict[str, Any],
    ) -> Tuple[float, str, str]:
        """
        Analyze a single lead for relevance and intent.
        
        Returns:
            Tuple of (relevance_score, intent_type, reasoning)
        """
        # Extract lead content
        lead_content = self._extract_lead_content(lead)
        
        # Get business details
        business_summary = business_context.get("business_summary", "")
        keywords = business_context.get("keywords", [])
        buying_signals = business_context.get("buying_signals", [])
        intent_type = business_context.get("intent_type", "sales")
        
        # Step 1: Quick semantic similarity check
        semantic_score = await self._calculate_semantic_similarity(
            lead_content, keywords
        )
        
        # If semantic score is too low, skip expensive GPT analysis
        if semantic_score < 0.4:
            return (semantic_score * 0.5, "none", "Low semantic match with keywords")
        
        # Step 2: Deep intent analysis with GPT-4
        intent_analysis = await self._analyze_intent_with_gpt(
            lead_content=lead_content,
            business_summary=business_summary,
            keywords=keywords,
            buying_signals=buying_signals,
            intent_type=intent_type,
        )
        
        # Combine semantic and intent scores
        final_score = (semantic_score * 0.3) + (intent_analysis["score"] * 0.7)
        
        return (
            final_score,
            intent_analysis["intent_type"],
            intent_analysis["reasoning"],
        )

    async def _calculate_semantic_similarity(
        self, lead_content: str, keywords: List[str]
    ) -> float:
        """Calculate cosine similarity between lead content and keywords."""
        if not lead_content or not keywords:
            return 0.0
        
        try:
            # Get embeddings
            lead_embedding = await self._get_embedding(lead_content)
            keywords_text = " ".join(keywords)
            keywords_embedding = await self._get_embedding(keywords_text)
            
            # Calculate cosine similarity
            similarity = np.dot(lead_embedding, keywords_embedding) / (
                np.linalg.norm(lead_embedding) * np.linalg.norm(keywords_embedding)
            )
            
            return float(max(0.0, min(1.0, similarity)))
        except Exception as e:
            print(f"Error calculating semantic similarity: {e}")
            return 0.0

    async def _get_embedding(self, text: str) -> List[float]:
        """Get text embedding using OpenAI with caching."""
        # Simple cache key
        cache_key = text[:100]  # Use first 100 chars as key
        
        if cache_key in self.embedding_cache:
            return self.embedding_cache[cache_key]
        
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text[:8000]  # Limit input length
            )
            embedding = response.data[0].embedding
            
            # Cache the result
            self.embedding_cache[cache_key] = embedding
            
            return embedding
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return [0.0] * 1536  # Return zero vector on error

    async def _analyze_intent_with_gpt(
        self,
        lead_content: str,
        business_summary: str,
        keywords: List[str],
        buying_signals: List[str],
        intent_type: str,
    ) -> Dict[str, Any]:
        """Use GPT-4 to deeply analyze lead intent."""
        prompt = f"""
You are an expert lead qualification analyst. Analyze this social media post/content to determine if it represents a genuine lead opportunity.

BUSINESS CONTEXT:
{business_summary}

TARGET KEYWORDS: {', '.join(keywords)}
BUYING SIGNALS: {', '.join(buying_signals) if buying_signals else 'Not specified'}
INTENT TYPE: {intent_type} (e.g., sales, hiring, partnership)

LEAD CONTENT:
{lead_content[:2000]}

ANALYSIS REQUIREMENTS:
1. Determine if this person/post shows DIRECT or IMPLIED intent related to the business
   - DIRECT: Explicitly seeking product/service, asking for recommendations, expressing immediate need
   - IMPLIED: Discussing pain points, problems, or context that suggests future need
   - NONE: Just mentioning keywords but no actual intent

2. Score relevance from 0.0 to 1.0:
   - 0.9-1.0: Perfect match, clear buying intent
   - 0.7-0.89: Strong match, probable interest
   - 0.5-0.69: Moderate match, possible interest
   - 0.3-0.49: Weak match, tangential mention
   - 0.0-0.29: Poor match, irrelevant

3. Consider:
   - Is this a real person expressing a genuine need?
   - Does their context align with the business offering?
   - Are they in a decision-making position or pain point?
   - Is this spam, bot, or irrelevant chatter?

Respond ONLY with valid JSON:
{{
    "score": 0.85,
    "intent_type": "direct|implied|none",
    "reasoning": "Brief explanation of why this lead is or isn't relevant",
    "buying_stage": "awareness|consideration|decision|none"
}}
"""
        
        try:
            messages = [
                {"role": "system", "content": "You are a lead qualification expert. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ]
            
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",  # Fast and cost-effective
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.3,
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return {
                "score": float(result.get("score", 0.5)),
                "intent_type": result.get("intent_type", "none"),
                "reasoning": result.get("reasoning", ""),
                "buying_stage": result.get("buying_stage", "none"),
            }
        except Exception as e:
            print(f"Error in GPT intent analysis: {e}")
            return {
                "score": 0.5,
                "intent_type": "unknown",
                "reasoning": f"Analysis error: {str(e)}",
                "buying_stage": "none",
            }

    def _extract_lead_content(self, lead: Dict[str, Any]) -> str:
        """Extract relevant text content from a lead for analysis."""
        content_parts = []
        
        # Common lead content fields
        for field in ["mention", "content", "notes", "description", "post_content"]:
            if value := lead.get(field):
                content_parts.append(str(value))
        
        # Add context from other fields
        if username := lead.get("username"):
            content_parts.append(f"User: {username}")
        
        if job_title := lead.get("job_title"):
            content_parts.append(f"Role: {job_title}")
        
        if company := lead.get("company_name"):
            content_parts.append(f"Company: {company}")
        
        return " | ".join(content_parts)

    async def enrich_lead_with_follow_up(
        self,
        lead: Dict[str, Any],
        business_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate personalized follow-up message based on intent analysis."""
        lead_content = self._extract_lead_content(lead)
        business_summary = business_context.get("business_summary", "")
        ai_response_guide = business_context.get("ai_response_guide", "")
        
        prompt = f"""
You are a sales outreach specialist. Generate a personalized, natural follow-up message.

BUSINESS CONTEXT:
{business_summary}

RESPONSE GUIDELINES:
{ai_response_guide}

LEAD CONTENT:
{lead_content}

LEAD INTENT: {lead.get("intent_type", "unknown")}
RELEVANCE SCORE: {lead.get("ai_relevance_score", "unknown")}

Generate a message that:
1. Directly addresses their specific need or pain point
2. Shows you understand their context
3. Provides clear value proposition
4. Includes natural call-to-action
5. Sounds human and conversational (max 2-3 sentences)
6. Does NOT sound generic or templated

Respond with ONLY the message text, no JSON or formatting.
"""
        
        try:
            messages = [{"role": "user", "content": prompt}]
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=200,
            )
            
            follow_up = response.choices[0].message.content.strip()
            lead["follow_up_message"] = follow_up
            
        except Exception as e:
            print(f"Error generating follow-up: {e}")
        
        return lead
