"""
JobKeywordGenerationService - Generates job role keywords from business context
PRD Section 5: "The AI uses the prompt and user's onboarding information to pre-fill keyword logic"

This service analyzes user's business description and generates relevant job role keywords
for job board searching.
"""
from typing import List
from pydantic import BaseModel, Field
import logging

from app.services.AIService import AIService

logger = logging.getLogger(__name__)


class JobKeywordResult(BaseModel):
    """Structured response model for job keyword generation"""
    job_keywords: List[str] = Field(
        description="List of job role titles to search for (e.g., ['DevOps Engineer', 'Cloud Engineer'])"
    )
    reasoning: str = Field(
        description="Brief explanation of why these job roles were selected"
    )


class JobKeywordGenerationService:
    """
    Service for generating job search keywords from business context
    PRD: "AI uses onboarding information to pre-fill keyword logic"
    """

    SYSTEM_PROMPT = """You are an expert at identifying relevant job roles based on a company's product/service offering.

YOUR TASK:
Given a description of what a company sells (product/service), identify which job roles at OTHER companies would indicate they need this solution.

CRITICAL UNDERSTANDING:
1. The user SELLS a solution - we're looking for companies HIRING roles that indicate they need it
2. If someone sells "cloud infrastructure", look for companies hiring "DevOps Engineers", "Cloud Engineers", etc.
3. If someone sells "marketing automation", look for companies hiring "Marketing Managers", "Growth Marketers", etc.
4. Focus on HIRING signals, not their own company's roles

GUIDELINES:
1. Return 3-8 specific job role titles
2. Use industry-standard job titles (not company-specific ones)
3. Include seniority variations when relevant (e.g., "Senior DevOps Engineer", "DevOps Engineer")
4. Focus on roles that would directly benefit from or need the user's solution
5. Exclude: Recruiters, HR roles, Talent Acquisition roles
6. Be specific: "DevOps Engineer" not just "Engineer"

EXAMPLES:

Input: "We provide cloud infrastructure that reduces DevOps costs"
Output: ["DevOps Engineer", "Senior DevOps Engineer", "Cloud Engineer", "Platform Engineer", "Site Reliability Engineer", "Infrastructure Engineer"]

Input: "We sell marketing automation software for small businesses"
Output: ["Marketing Manager", "Digital Marketing Manager", "Growth Marketing Manager", "Marketing Coordinator", "Marketing Director"]

Input: "We offer accounting software for freelancers"
Output: ["Accountant", "Bookkeeper", "Finance Manager", "Accounting Manager", "Controller"]

IMPORTANT:
- Return ONLY job titles that indicate a hiring need for the user's solution
- Do NOT return generic roles like "Manager" or "Engineer"
- Do NOT return the user's own company roles
"""

    @staticmethod
    def _build_generation_prompt(business_context: str) -> str:
        """Build the prompt for job keyword generation"""
        return f"""Analyze this business description and generate relevant job role keywords:

BUSINESS CONTEXT:
{business_context}

---

Generate 3-8 job role titles that, when companies are hiring for them, indicate they likely need this solution.

Remember:
- Focus on job titles that signal a need for the user's product/service
- Use industry-standard job titles
- Include seniority variations if relevant
- Exclude HR/Recruiting roles
- Be specific and actionable"""

    @staticmethod
    async def generate_job_keywords(
        business_context: str,
        model: str = "gpt-4o-mini"
    ) -> JobKeywordResult:
        """
        Generate job search keywords from business context

        Args:
            business_context: Description of what the user's business sells
            model: AI model to use (default: gpt-4o-mini)

        Returns:
            JobKeywordResult with job role keywords and reasoning
        """
        try:
            # Build prompt
            prompt = JobKeywordGenerationService._build_generation_prompt(business_context)

            # Build AI model (same pattern as other services)
            messages = [
                {"role": "system", "content": JobKeywordGenerationService.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]

            ai_model = AIService.build_ai_model(messages)

            # Get structured response
            ai_response = await AIService.structured_chat_completion(
                ai_model,
                JobKeywordResult
            )

            result = AIService.extract_ai_result(ai_response)

            # Log the generation
            logger.info(
                f"Generated {len(result.job_keywords)} job keywords from context: "
                f"{business_context[:100]}..."
            )
            logger.info(f"Keywords: {', '.join(result.job_keywords)}")

            return result

        except Exception as e:
            logger.error(f"Error generating job keywords: {str(e)}")
            import traceback
            traceback.print_exc()

            # Return fallback generic keywords on error
            return JobKeywordResult(
                job_keywords=["Software Engineer", "Product Manager", "Marketing Manager"],
                reasoning=f"Error generating keywords: {str(e)}. Using generic defaults."
            )

    @staticmethod
    def validate_job_keywords(keywords: List[str]) -> List[str]:
        """
        Validate and clean job keywords

        Args:
            keywords: List of job role keywords

        Returns:
            Cleaned list of valid keywords
        """
        # Filter out invalid keywords
        excluded_terms = ["recruiter", "hr", "talent acquisition", "human resources"]

        valid_keywords = []
        for keyword in keywords:
            keyword_lower = keyword.lower().strip()

            # Skip if empty or contains excluded terms
            if not keyword_lower or any(term in keyword_lower for term in excluded_terms):
                continue

            # Skip if too short (likely not a real job title)
            if len(keyword_lower) < 3:
                continue

            valid_keywords.append(keyword.strip())

        return valid_keywords
