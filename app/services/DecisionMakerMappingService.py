"""
DecisionMakerMappingService - Maps job roles to decision-maker titles
PRD Section 8.3: Decision-Maker Identification Logic

This service maps hiring roles to the appropriate decision-makers who can buy solutions.
Example: DevOps Engineer → CTO, Head of Engineering, VP Engineering
"""
from typing import List
from pydantic import BaseModel, Field
import logging

from app.services.AIService import AIService

logger = logging.getLogger(__name__)


class DecisionMakerMapping(BaseModel):
    """Structured response for decision-maker mapping"""
    decision_maker_titles: List[str] = Field(
        description="1-3 job titles to search for (decision-makers who can buy solutions)"
    )
    reasoning: str = Field(
        description="Why these decision-makers are relevant to this hiring need"
    )


class DecisionMakerMappingService:
    """
    Service for mapping job roles to decision-maker titles
    PRD Section 8: Decision-Maker Connection Feature
    """

    # PRD Section 8.3 - Example mappings
    STATIC_MAPPINGS = {
        # Engineering roles
        "devops engineer": ["CTO", "VP Engineering", "Head of Engineering", "Head of Infrastructure"],
        "senior devops engineer": ["CTO", "VP Engineering", "Head of Engineering"],
        "cloud engineer": ["CTO", "VP Engineering", "Head of Cloud Infrastructure"],
        "platform engineer": ["CTO", "VP Engineering", "Head of Platform"],
        "site reliability engineer": ["CTO", "VP Engineering", "Head of Infrastructure"],
        "data engineer": ["CTO", "Head of Data", "VP Engineering"],
        "data analyst": ["CTO", "Head of Data", "Head of Analytics", "VP Data"],
        "software engineer": ["CTO", "VP Engineering", "Head of Engineering"],

        # Marketing roles
        "marketing manager": ["CMO", "VP Marketing", "Head of Marketing"],
        "content marketing manager": ["CMO", "VP Marketing", "Head of Content"],
        "digital marketing manager": ["CMO", "VP Marketing", "Head of Digital"],
        "growth marketing manager": ["CMO", "VP Growth", "Head of Growth"],
        "brand manager": ["CMO", "VP Marketing", "Head of Brand"],

        # Sales roles
        "sales manager": ["VP Sales", "Head of Sales", "Chief Revenue Officer"],
        "account executive": ["VP Sales", "Head of Sales", "Sales Director"],
        "business development manager": ["VP Business Development", "Head of BD", "Chief Revenue Officer"],

        # Operations roles
        "customer support": ["Head of Operations", "VP Customer Success", "COO"],
        "operations manager": ["COO", "VP Operations", "Head of Operations"],
        "customer success manager": ["VP Customer Success", "Head of Customer Success"],

        # Product roles
        "product manager": ["CPO", "VP Product", "Head of Product"],
        "senior product manager": ["CPO", "VP Product"],

        # Finance roles
        "financial analyst": ["CFO", "VP Finance", "Head of Finance"],
        "accountant": ["CFO", "VP Finance", "Controller"],
    }

    SYSTEM_PROMPT = """You are an expert at identifying which decision-makers to contact based on a company's hiring needs.

YOUR TASK:
Given a job title being hired for, identify 1-3 decision-maker job titles to contact.

CRITICAL RULES:
1. Focus on people who can BUY SOLUTIONS (not recruiters, not HR)
2. Return C-level, VPs, Heads, and Directors
3. Map the hiring role to the department/function decision-maker
4. NEVER return: Recruiters, HR roles, Talent Acquisition, Hiring Manager
5. Return 1-3 titles maximum (most relevant first)

EXAMPLES:

Job Being Hired: "DevOps Engineer"
Decision-Makers: ["CTO", "VP Engineering", "Head of Infrastructure"]
Reasoning: "DevOps hiring indicates infrastructure/deployment challenges, which fall under engineering leadership."

Job Being Hired: "Marketing Manager"
Decision-Makers: ["CMO", "VP Marketing", "Head of Marketing"]
Reasoning: "Marketing hiring indicates need for marketing solutions, overseen by marketing leadership."

Job Being Hired: "Data Analyst"
Decision-Makers: ["CTO", "Head of Data", "VP Analytics"]
Reasoning: "Data analyst hiring suggests data infrastructure or analytics needs, managed by data/tech leadership."

Job Being Hired: "Customer Support Representative"
Decision-Makers: ["Head of Operations", "VP Customer Success", "COO"]
Reasoning: "Customer support hiring indicates customer service challenges, typically managed by operations."

Job Being Hired: "Recruiter"
Decision-Makers: []
Reasoning: "HR/Recruiter roles excluded per PRD - not relevant for solution selling."

FORMATTING:
- Use standard job titles as they appear on LinkedIn (e.g., "VP Engineering", not "VP of Engineering")
- Include seniority: "Head of Marketing" not just "Marketing"
- Be specific: "VP Sales" not "VP"
"""

    @staticmethod
    def _build_mapping_prompt(job_title: str) -> str:
        """Build the decision-maker mapping prompt"""
        return f"""Given this job title being hired for, identify the decision-makers to contact:

JOB BEING HIRED: {job_title}

Return 1-3 decision-maker job titles who would be responsible for this area and could buy solutions to address the underlying business problem.

Remember:
- Focus on C-level, VPs, Heads, Directors
- NO recruiters, NO HR roles
- Be specific about the department/function"""

    @staticmethod
    async def map_job_to_decision_makers(
        job_title: str,
        use_ai: bool = True
    ) -> List[str]:
        """
        Map a job title to decision-maker titles

        Args:
            job_title: The job title being hired for
            use_ai: Whether to use AI mapping (fallback to static if False)

        Returns:
            List of decision-maker job titles (1-3 titles)
        """
        job_title_lower = job_title.lower().strip()

        # First, try static mappings (faster)
        if job_title_lower in DecisionMakerMappingService.STATIC_MAPPINGS:
            titles = DecisionMakerMappingService.STATIC_MAPPINGS[job_title_lower]
            logger.info(f"Static mapping for '{job_title}': {titles}")
            return titles[:3]  # Max 3

        # If AI is disabled or not available, use generic mapping
        if not use_ai:
            return DecisionMakerMappingService._generic_mapping(job_title)

        # Use AI for custom mapping
        try:
            prompt = DecisionMakerMappingService._build_mapping_prompt(job_title)

            messages = [
                {"role": "system", "content": DecisionMakerMappingService.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]

            ai_model = AIService.build_ai_model(messages)

            ai_response = await AIService.structured_chat_completion(
                ai_model,
                DecisionMakerMapping
            )

            result = AIService.extract_ai_result(ai_response)

            logger.info(f"AI mapping for '{job_title}': {result.decision_maker_titles}")
            return result.decision_maker_titles[:3]  # Max 3

        except Exception as e:
            logger.error(f"Error in AI decision-maker mapping: {str(e)}")
            # Fallback to generic mapping
            return DecisionMakerMappingService._generic_mapping(job_title)

    @staticmethod
    def _generic_mapping(job_title: str) -> List[str]:
        """
        Generic fallback mapping based on common patterns

        Args:
            job_title: The job title being hired for

        Returns:
            Generic decision-maker titles
        """
        job_title_lower = job_title.lower()

        # Engineering/Technical roles
        if any(word in job_title_lower for word in ["engineer", "developer", "devops", "sre", "architect", "technical"]):
            return ["CTO", "VP Engineering", "Head of Engineering"]

        # Marketing roles
        if any(word in job_title_lower for word in ["marketing", "content", "brand", "growth"]):
            return ["CMO", "VP Marketing", "Head of Marketing"]

        # Sales roles
        if any(word in job_title_lower for word in ["sales", "account executive", "business development"]):
            return ["VP Sales", "Head of Sales", "Chief Revenue Officer"]

        # Data roles
        if any(word in job_title_lower for word in ["data", "analytics", "analyst"]):
            return ["CTO", "Head of Data", "VP Analytics"]

        # Operations/Support roles
        if any(word in job_title_lower for word in ["operations", "support", "customer success"]):
            return ["COO", "VP Operations", "Head of Customer Success"]

        # Product roles
        if any(word in job_title_lower for word in ["product"]):
            return ["CPO", "VP Product", "Head of Product"]

        # Finance roles
        if any(word in job_title_lower for word in ["finance", "accounting", "financial"]):
            return ["CFO", "VP Finance", "Head of Finance"]

        # Default fallback (C-level)
        return ["CEO", "COO", "CTO"]
