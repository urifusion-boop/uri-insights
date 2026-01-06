"""
JobKeywordGenerationService - Generates job role keywords from business context
PRD Section 5: "The AI uses the prompt and user's onboarding information to pre-fill keyword logic"

This service analyzes user's business description and generates relevant job role keywords
for job board searching.
"""
from typing import List
from pydantic import BaseModel, Field
import logging
import re

from app.services.AIService import AIService
from app.domain.enums.job_keyword_generation_examples import JOB_KEYWORD_GENERATION_EXAMPLES

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

DOMAIN TERM EXTRACTION (CRITICAL):
1. Extract key industry/domain words from the input: "cloud", "security", "marketing", "sales", "HR", etc.
2. Generated keywords MUST contain these domain terms to ensure relevance
3. Example: If input mentions "cloud services" → output MUST include "Cloud Engineer", "Cloud Architect", "Cloud Solutions", etc.
4. Example: If input mentions "cybersecurity" → output MUST include "Security Engineer", "Security Analyst", etc.
5. At least 60% of generated keywords should contain domain terms extracted from the input

GUIDELINES:
1. Return 5-9 specific job role titles
2. Use industry-standard job titles (not company-specific ones)
3. Include seniority variations when relevant (e.g., "Senior Cloud Engineer", "Cloud Engineer")
4. Focus on roles that would directly benefit from or need the user's solution
5. Exclude: Recruiters, HR roles, Talent Acquisition roles (unless HR software is being sold)
6. Be specific: "Cloud Engineer" not just "Engineer", "Marketing Manager" not just "Manager"

RELEVANCE VALIDATION:
- Keywords must be DIRECTLY related to the solution being sold
- Extract domain terms and ensure they appear in job titles
- If user mentions "cloud" → keywords must include Cloud-related roles
- If user mentions "marketing" → keywords must include Marketing roles
- If user mentions "security" → keywords must include Security roles

LEARN FROM THESE EXAMPLES:
""" + JOB_KEYWORD_GENERATION_EXAMPLES + """

IMPORTANT:
- Return ONLY job titles that indicate a hiring need for the user's solution
- Keywords MUST be relevant to the domain/industry mentioned in the input
- Do NOT return generic roles like "Manager" or "Engineer" without domain context
- Do NOT return the user's own company roles
"""

    @staticmethod
    def _extract_domain_terms(business_context: str) -> List[str]:
        """
        Extract key domain/industry terms from business context
        These terms should appear in the generated job keywords
        """
        business_lower = business_context.lower()

        # Common domain terms to look for
        domain_keywords = [
            "cloud", "devops", "infrastructure", "platform",
            "security", "cybersecurity", "compliance",
            "marketing", "digital marketing", "growth", "content",
            "sales", "crm", "business development",
            "hr", "human resources", "talent", "recruiting",
            "accounting", "finance", "financial",
            "data", "analytics", "business intelligence", "bi",
            "support", "customer service", "customer success",
            "supply chain", "logistics", "operations",
            "legal", "compliance", "regulatory",
            "video", "creative", "design", "graphic",
            "construction", "project management",
            "healthcare", "medical", "clinical",
            "e-commerce", "retail", "online store",
            "ai", "machine learning", "ml", "artificial intelligence"
        ]

        found_terms = []
        for term in domain_keywords:
            if term in business_lower:
                found_terms.append(term)

        return found_terms

    @staticmethod
    def _build_generation_prompt(business_context: str) -> str:
        """Build the prompt for job keyword generation"""
        domain_terms = JobKeywordGenerationService._extract_domain_terms(business_context)
        domain_hint = ""
        if domain_terms:
            domain_hint = f"\n\nIMPORTANT: The user's solution is related to: {', '.join(domain_terms)}. Make sure most job keywords contain these domain terms!"

        return f"""Analyze this business description and generate relevant job role keywords:

BUSINESS CONTEXT:
{business_context}{domain_hint}

---

Generate 5-9 job role titles that, when companies are hiring for them, indicate they likely need this solution.

CRITICAL REQUIREMENTS:
- Extract domain/industry terms from the business context (e.g., "cloud", "marketing", "security")
- Generated job titles MUST contain these domain terms to ensure relevance
- At least 60% of keywords should include domain terms from the input
- Focus on job titles that signal a need for the user's product/service
- Use industry-standard job titles
- Include seniority variations if relevant (Junior, Senior, Director, Chief)
- Exclude HR/Recruiting roles (unless the solution is HR software)
- Be specific and actionable: "Cloud Engineer" not just "Engineer"

Example of GOOD output for "cloud services":
["Cloud Engineer", "Senior Cloud Engineer", "DevOps Engineer", "Cloud Architect", "Platform Engineer"]

Example of BAD output for "cloud services":
["Software Engineer", "Technical Support", "Product Manager"] ❌ (None contain "cloud" or related terms)"""

    @staticmethod
    async def generate_job_keywords(
        business_context: str,
        model: str = "gpt-4o-mini",
        max_retries: int = 2
    ) -> JobKeywordResult:
        """
        Generate job search keywords from business context

        Args:
            business_context: Description of what the user's business sells
            model: AI model to use (default: gpt-4o-mini)
            max_retries: Maximum number of retries if validation fails (default: 2)

        Returns:
            JobKeywordResult with job role keywords and reasoning
        """
        domain_terms = JobKeywordGenerationService._extract_domain_terms(business_context)

        for attempt in range(max_retries):
            try:
                # Build prompt
                prompt = JobKeywordGenerationService._build_generation_prompt(business_context)

                # Build AI model with LOWER temperature for consistency (0.2 instead of default 0.7)
                messages = [
                    {"role": "system", "content": JobKeywordGenerationService.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]

                # CRITICAL: Use temperature=0.2 for more consistent, focused keyword generation
                ai_model = AIService.build_ai_model(messages, model=model, temperature=0.2)

                # Get structured response
                ai_response = await AIService.structured_chat_completion(
                    ai_model,
                    JobKeywordResult
                )

                result = AIService.extract_ai_result(ai_response)

                # Validate relevance: Check if keywords match domain terms
                is_valid, validation_message = JobKeywordGenerationService._validate_keyword_relevance(
                    result.job_keywords,
                    domain_terms,
                    business_context
                )

                if is_valid:
                    # Log the successful generation
                    logger.info(
                        f"Generated {len(result.job_keywords)} job keywords from context: "
                        f"{business_context[:100]}..."
                    )
                    logger.info(f"Keywords: {', '.join(result.job_keywords)}")
                    logger.info(f"Domain terms detected: {', '.join(domain_terms)}")
                    return result
                else:
                    # Log validation failure and retry
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries}: Keyword validation failed - {validation_message}"
                    )
                    if attempt == max_retries - 1:
                        # Last attempt failed, return anyway but log warning
                        logger.warning(f"All retries exhausted. Returning keywords despite validation failure.")
                        return result

            except Exception as e:
                logger.error(f"Error generating job keywords (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    import traceback
                    traceback.print_exc()

                    # Return fallback generic keywords on final error
                    return JobKeywordResult(
                        job_keywords=["Software Engineer", "Product Manager", "Marketing Manager"],
                        reasoning=f"Error generating keywords: {str(e)}. Using generic defaults."
                    )

    @staticmethod
    def _validate_keyword_relevance(
        keywords: List[str],
        domain_terms: List[str],
        business_context: str
    ) -> tuple[bool, str]:
        """
        Validate that generated keywords are relevant to the business context

        Args:
            keywords: Generated job keywords
            domain_terms: Extracted domain terms from business context
            business_context: Original business description

        Returns:
            Tuple of (is_valid, validation_message)
        """
        if not keywords:
            return False, "No keywords generated"

        if not domain_terms:
            # If no domain terms detected, we can't validate relevance, so pass
            return True, "No domain terms to validate against"

        # Check how many keywords contain at least one domain term
        matching_keywords = 0
        for keyword in keywords:
            keyword_lower = keyword.lower()
            # Check if any domain term (or related term) appears in the keyword
            for domain_term in domain_terms:
                # Handle multi-word domain terms
                domain_words = domain_term.split()
                if any(word in keyword_lower for word in domain_words):
                    matching_keywords += 1
                    break

        # Calculate relevance percentage
        relevance_percentage = (matching_keywords / len(keywords)) * 100

        # Require at least 50% of keywords to contain domain terms
        if relevance_percentage >= 50:
            return True, f"Relevance check passed: {matching_keywords}/{len(keywords)} keywords ({relevance_percentage:.0f}%) contain domain terms"
        else:
            return False, f"Relevance check failed: Only {matching_keywords}/{len(keywords)} keywords ({relevance_percentage:.0f}%) contain domain terms (minimum 50% required). Domain terms: {', '.join(domain_terms)}"

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
