"""
JobSignalAnalysisService - Analyzes job postings for commercial opportunities
Pattern: Same as IntentAnalysisService but for hiring signals

This service analyzes job postings to identify sales opportunities by:
1. Matching hiring needs to user's solution
2. Scoring hiring urgency
3. Identifying business problems
4. Suggesting decision-makers to contact
"""
from typing import List
from pydantic import BaseModel, Field
import logging

from app.services.AIService import AIService

logger = logging.getLogger(__name__)


class JobSignalResult(BaseModel):
    """Structured response model for job posting analysis"""
    problem_solution_match: float = Field(ge=0, le=1, description="How well user's solution addresses the hiring problem (0-1)")
    hiring_intent_score: float = Field(ge=0, le=1, description="How urgent/serious is the hiring need (0-1)")
    commercial_relevance: float = Field(ge=0, le=1, description="Likelihood company will buy user's solution (0-1)")
    implied_problems: str = Field(description="Business problems this hiring suggests")
    target_seniorities: List[str] = Field(description="Job titles to contact (e.g., ['CTO', 'VP Engineering'])")
    reasoning: str = Field(description="Why this is a sales signal")
    company_confidence: float = Field(ge=0, le=1, description="Confidence that company can be verified/contacted (0-1, PRD Sections 14-16)")


class JobSignalAnalysisService:
    """
    Service for analyzing job postings to identify sales opportunities
    PATTERN: Same as IntentAnalysisService but for hiring signals
    """

    SYSTEM_PROMPT = """You are an expert at analyzing job postings to identify business opportunities for solution providers.

YOUR TASK:
Analyze this job posting to determine if it represents a sales opportunity for the user's product/service.

CRITICAL UNDERSTANDING:
1. Hiring indicates an ACTIVE BUSINESS PROBLEM
2. If a company is hiring for a role, they have a pain point
3. Sometimes buying a solution is better than hiring
4. Focus on the BUSINESS PROBLEM, not the job posting itself

SCORING GUIDELINES:

1. problem_solution_match (0-1):
   - 0.8-1.0: Job directly addresses a problem the user's solution solves perfectly
   - 0.6-0.79: Strong overlap between hiring need and user's solution
   - 0.3-0.59: Moderate relevance - some aspects align
   - 0.0-0.29: Little to no relevance

2. hiring_intent_score (0-1):
   - 0.8-1.0: Urgent hiring (detailed JD, salary listed, "immediate", "ASAP", pain points mentioned)
   - 0.6-0.79: Serious hiring (detailed requirements, tech stack mentioned, clear responsibilities)
   - 0.3-0.59: Casual hiring (vague description, generic requirements)
   - 0.0-0.29: Very vague or likely old/inactive posting

3. commercial_relevance:
   - Automatically calculated as: (0.6 × problem_solution_match) + (0.4 × hiring_intent_score)
   - This will be calculated by the code, not by you

4. company_confidence (0-1) - PRD Sections 14-16:
   - 0.8-1.0: Clear company name, looks like real business, has domain/website info
   - 0.5-0.79: Company name present but generic or missing verification details
   - 0.3-0.49: Vague company name, missing or unverifiable
   - 0.0-0.29: Company name missing, "Confidential", "Stealth Startup", or obviously fake
   - If company_confidence < 0.5, decision-maker lookup will be disabled (PRD Section 16)

5. implied_problems:
   - What specific business challenges does this hiring reveal?
   - Be specific and actionable
   - Focus on pain points the user's solution can address
   - Example: "Struggling with manual deployment processes causing delays and reliability issues"

6. target_seniorities:
   - Which job titles should the user contact?
   - Focus on decision-makers who can buy solutions (CTO, VP, Head of..., Director of...)
   - Map the hiring role to the appropriate decision-maker
   - Examples:
     * DevOps Engineer → ["CTO", "VP Engineering", "Head of Infrastructure"]
     * Marketing Manager → ["CMO", "VP Marketing", "Head of Marketing"]
     * Data Analyst → ["CTO", "Head of Data", "VP Analytics"]
   - ALWAYS EXCLUDE: Recruiters, HR roles, Talent Acquisition
   - Return 1-3 titles maximum

IMPORTANT FILTERING:
- If the job is for Recruiters, HR, or Talent Acquisition roles, set problem_solution_match to 0.0
- If the user's solution has NO relevance to the hiring need, set problem_solution_match to 0.0

OUTPUT FORMAT (CRITICAL - PRD Section 7.2):
For the 'reasoning' field, you MUST follow this exact format:
"{company_name} is hiring {job_title}, this is an opportunity to sell your {user's product/service}"

Example: "TechCorp is hiring a DevOps Engineer, this is an opportunity to sell your cloud infrastructure services"

The reasoning should be a single, clear sentence that follows this pattern exactly."""

    @staticmethod
    def _build_analysis_prompt(
        job_description: str,
        job_title: str,
        company_name: str,
        solution_context: str
    ) -> str:
        """Build the analysis prompt (similar to IntentAnalysisService._build_analysis_prompt)"""

        return f"""Analyze this job posting to determine if it's a sales opportunity:

JOB TITLE: {job_title}
COMPANY: {company_name}
JOB DESCRIPTION:
{job_description}

---

USER'S SOLUTION CONTEXT (what they sell):
{solution_context}

---

ANALYSIS REQUIRED:
1. Does this hiring need indicate a problem the user's solution can solve?
2. How urgent/serious is this hiring need? (Look for pain points, urgency language, detailed requirements)
3. What specific business problems does this hiring suggest?
4. Who should the user contact at this company? (Decision-makers, not recruiters)
5. Why is this a sales signal? (Or why not?)

Remember:
- Focus on whether the user's SOLUTION can address the underlying business problem
- Don't recommend contacting recruiters or HR
- Be specific about implied problems
- Companies hire when they have pain - identify that pain"""

    @staticmethod
    async def analyze_job_posting(
        job_description: str,
        job_title: str,
        company_name: str,
        solution_context: str,
        model: str = "gpt-4o-mini"
    ) -> JobSignalResult:
        """
        Analyze a job posting for commercial opportunity

        PATTERN: Same as IntentAnalysisService.analyze_post()

        Args:
            job_description: Full job posting text
            job_title: Title of the job
            company_name: Company posting the job
            solution_context: User's solution description from lead form
            model: AI model to use (default: gpt-4o-mini)

        Returns:
            JobSignalResult with scores and reasoning
        """

        # Build prompt (same pattern as IntentAnalysisService)
        prompt = JobSignalAnalysisService._build_analysis_prompt(
            job_description, job_title, company_name, solution_context
        )

        # Build AI model (EXACT same pattern as IntentAnalysisService)
        messages = [
            {"role": "system", "content": JobSignalAnalysisService.SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]

        ai_model = AIService.build_ai_model(messages)

        # Get structured response (EXACT same pattern as IntentAnalysisService)
        try:
            ai_response = await AIService.structured_chat_completion(
                ai_model,
                JobSignalResult
            )

            result = AIService.extract_ai_result(ai_response)

            # Calculate commercial_relevance (as per PRD Section 7.3)
            result.commercial_relevance = round(
                0.6 * result.problem_solution_match +
                0.4 * result.hiring_intent_score,
                2
            )

            # Log analysis result
            logger.info(
                f"Job signal analysis for {company_name} - {job_title}: "
                f"match={result.problem_solution_match:.2f}, "
                f"intent={result.hiring_intent_score:.2f}, "
                f"relevance={result.commercial_relevance:.2f}"
            )

            return result

        except Exception as e:
            logger.error(f"Error in job signal analysis: {str(e)}")
            import traceback
            traceback.print_exc()

            # Return default low-score result on error
            return JobSignalResult(
                problem_solution_match=0.0,
                hiring_intent_score=0.0,
                commercial_relevance=0.0,
                implied_problems="Analysis failed due to an error",
                target_seniorities=[],
                reasoning=f"Error analyzing job posting: {str(e)}",
                company_confidence=0.0
            )

    @staticmethod
    def calculate_commercial_relevance(
        problem_solution_match: float,
        hiring_intent_score: float
    ) -> float:
        """
        Calculate commercial relevance score
        Formula from PRD Section 7.3: 60% problem match + 40% hiring intent

        Args:
            problem_solution_match: Score 0-1
            hiring_intent_score: Score 0-1

        Returns:
            Commercial relevance score 0-1
        """
        return round(
            0.6 * problem_solution_match + 0.4 * hiring_intent_score,
            2
        )
