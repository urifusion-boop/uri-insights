from fastapi import APIRouter, BackgroundTasks, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import enforce_feature_limit, get_db_dependency
from app.domain.enums.date_enum import DateFilterEnum
from app.domain.enums.filetype_enum import FileTypeEnum
from app.domain.enums.lead_enum import (
    LeadIndustryTypeEnum,
    LeadStatusEnum,
    LeadInterestLevelEnum,
    LeadSourceEnum,
)
from app.domain.schemas.leadbusinessinfo_schema import (
    LeadBusinessInfoCreate,
    LeadBusinessInfoUpdate,
)
from app.repository.LeadBusinessInfoRepository import LeadBusinessInfoRepository
from app.repository.LeadRepository import LeadRepository
from app.domain.schemas.lead_schema import (
    LeadCreate,
    LeadUpdate,
)
from app.domain.responses.uri_response import UriResponse
from typing import Optional, List, Union, Dict, Any
from fastapi.encoders import jsonable_encoder
from app.services.ApolloService import ApolloService
from app.services.LeadBusinessInfoService import LeadBusinessInfoService
from app.services.LeadService import LeadService
from app.domain.requests.lead_requests import (
    GetLeadsByFiltersRequest,
    LeadAnalyticsRequest,
    LeadEnrichmentRequest,
)
from app.domain.enums.leadform_enum import LeadFormTypeEnum
from app.repository.LeadFormRepository import LeadFormRepository
from app.services.uri_microservices.UriBackendService import UriBackendService


router = APIRouter()


# Create a new lead
@router.post("/create")
async def create_lead(
    lead: LeadCreate, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = LeadRepository.create_lead(db, lead)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Create multiple leads with optional intent analysis
@router.post("/multipleCreate")
async def create_leads(
    leads: List[LeadCreate],
    lead_form_id: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    # If lead_form_id provided, run intent analysis to filter leads
    if lead_form_id:
        lead_form_response = await LeadFormRepository.get_by_id(db, lead_form_id)
        lead_form = lead_form_response.get("responseData", {})

        if lead_form:
            # Run intent analysis and filter leads
            original_count = len(leads)
            leads = await LeadService.analyze_and_filter_leads(
                leads=leads,
                lead_form=lead_form,
                enable_intent_analysis=True
            )
            filtered_count = len(leads)
            print(f"Intent analysis: {original_count} leads -> {filtered_count} qualified")

            if not leads:
                return UriResponse.custom_response(
                    f"No leads passed intent analysis thresholds (0 of {original_count} qualified)",
                    200,
                    True
                )

    data = await LeadRepository.multiple_create_leads(db, leads)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Get a lead by ID
@router.get("/getById")
async def get_lead(lead_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)):
    data = await LeadRepository.get_lead_by_id(db, lead_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Filter leads by assigned_to, status, interest level, source with pagination
@router.get("/getByFilters")
async def filter_leads(
    date_filter: Optional[DateFilterEnum] = None,
    filters: GetLeadsByFiltersRequest = Depends(),
    skip: int = 0,
    limit: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadRepository.get_leads_by_filters(
        db=db,
        filters=filters,
        date_filter=date_filter,
        skip=skip,
        limit=limit,
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Update a lead
@router.post("/update")
async def update_lead(
    lead_id: str,
    updates: LeadUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadRepository.update_lead(db, lead_id, updates)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/updateMany")
async def update_many_leads(
    lead_ids: List[str],
    updates: LeadUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadRepository.update_many_leads(db, lead_ids, updates)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Update lead status
@router.post("/updateStatus")
async def update_lead_status(
    lead_id: str, status: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await LeadRepository.update_lead_status(db, lead_id, status)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Star a lead
@router.post("/star")
async def star_lead(
    lead_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await LeadRepository.star_lead(db, lead_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Unstar a lead
@router.post("/unstar")
async def unstar_lead(
    lead_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await LeadRepository.unstar_lead(db, lead_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.put("/emailed/update")
async def update_lead_emailed_status(
    lead_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    status: bool = True,
):
    data = await LeadRepository.update_emailed(db, lead_id, status)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.put("/called/update")
async def update_lead_called_status(
    lead_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    status: bool = True,
):
    data = await LeadRepository.update_called(db, lead_id, status)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Delete a lead
@router.delete("/delete")
async def delete_lead(
    lead_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await LeadService.delete_lead(db, lead_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.delete("/delete-many")
async def delete_many_leads(
    lead_ids: List[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadRepository.delete_many_leads(db, lead_ids)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


# Search leads by text query
@router.get("/search")
async def search_leads(
    query: str,
    skip: int = 0,
    limit: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadRepository.search_leads(db, query, skip, limit)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/analytics", response_model=dict)
async def get_lead_analytics(
    request: LeadAnalyticsRequest = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Get analytics data for leads based on filtering options.
    """
    data = await LeadRepository.fetch_lead_analytics(db, request)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/business-info/create")
async def create_lead_business_info(
    lead_business_info: LeadBusinessInfoCreate,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadBusinessInfoService.create_lead_business_info(
        db=db, background_tasks=background_tasks, lead_business_info=lead_business_info
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/business-info/getById")
async def get_lead_business_info_by_id(
    lead_business_info_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await LeadBusinessInfoRepository.get_lead_business_info_by_id(
        db, lead_business_info_id
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.get("/business-info/getByFilters")
async def get_lead_business_info_by_filter(
    user_id: str,
    business_name: Optional[str] = Query(None),
    business_website: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 10,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadBusinessInfoRepository.get_lead_business_info_by_filters(
        db, user_id, business_name, business_website, skip, limit
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/business-info/update")
async def update_lead_business_info(
    lead_business_info_id: str,
    updates: LeadBusinessInfoUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadBusinessInfoService.update_leads_business_info(
        db=db,
        lead_business_info_id=lead_business_info_id,
        updates=updates,
        background_tasks=background_tasks,
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.delete("/business-info/delete")
async def delete_lead_business_info(
    lead_business_info_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await LeadBusinessInfoRepository.delete_leads_business_info(
        db, lead_business_info_id
    )
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/enrich")
async def enrich_lead(
    request: LeadEnrichmentRequest,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    _=Depends(enforce_feature_limit),
):
    result = await ApolloService.handle_enrichment_request(
        lead_ids=request.lead_ids,
        db=db,
        reveal_email=request.reveal_email,
        reveal_phone=request.reveal_phone,
        webhook_url=request.webhook_url,
    )
    return UriResponse.get_status_response(response=jsonable_encoder(result))


@router.post("/regenerate-lead-follow-up-message")
async def regenerate_lead_follow_up_message(
    lead_id: str,
    user_prompt: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    data = await LeadService.regenerate_lead_follow_up_message(lead_id, user_prompt, db)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/export-lead")
async def export_lead_report(
    file_type: FileTypeEnum,
    assigned_to: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    date_filter: Optional[DateFilterEnum] = None,
    filters: GetLeadsByFiltersRequest = Depends(),
    skip: int = 0,
    limit: int = 10,
):
    filters.assigned_to = assigned_to
    await LeadService.export_leads_data(
        file_type=file_type,
        db=db,
        filters=filters,
        date_filter=date_filter,
        skip=skip,
        limit=limit,
    )
    return UriResponse.get_single_data_response(
        "Lead report", {"text": "File is being generated"}
    )


@router.delete("/delete-my-leads")
async def delete_my_leads(
    user_id: str, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    data = await LeadRepository.delete_all_leads_for_user(db, user_id)
    response = jsonable_encoder(data)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )


@router.post("/trigger-leads-gen")
async def trigger_conversational_leads_gen(
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    background_tasks.add_task(
        LeadService.generate_conversational_leads_background_job, db
    )

    return UriResponse.custom_response("Leads gen triggered successfully.", 202, True)


# Generate job keywords from business context (PRD Section 5)
@router.post("/generate-job-keywords")
async def generate_job_keywords(
    user_id: str,
    context: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    Generate job role keywords for job board searching
    PRD: "The AI uses the prompt and user's onboarding information to pre-fill keyword logic"
    
    Args:
        user_id: User ID to fetch onboarding data if context not provided
        context: Optional business description (if not provided, fetches from LeadBusinessInfo)
        
    Returns:
        {
            "job_keywords": ["DevOps Engineer", "Cloud Engineer", ...],
            "solution_context": "business description used",
            "source": "provided" | "onboarding_data"
        }
    """
    from app.services.JobKeywordGenerationService import JobKeywordGenerationService
    
    try:
        business_context = context
        source = "provided"
        
        # If no context provided, fetch from user's onboarding data (PRD Section 5)
        if not business_context or business_context.strip() == "":
            print(f"📥 No context provided, fetching onboarding data for user: {user_id}")

            # PRD: "Users have already defined what they sell" - fetch from user.businessDetails
            user_details = await UriBackendService.get_user_details(user_id)

            if user_details and user_details.get("businessDetails"):
                what_you_sell = user_details["businessDetails"].get("whatYouSell")
                if what_you_sell and what_you_sell.strip():
                    business_context = what_you_sell
                    source = "user_onboarding"
                    print(f"✅ Found user onboarding data (whatYouSell): {business_context[:100]}...")

            # Fallback to LeadBusinessInfo if user onboarding doesn't have it
            if not business_context:
                print(f"   Trying LeadBusinessInfo as fallback...")
                business_info_response = await LeadBusinessInfoRepository.get_lead_business_info_by_filters(
                    db, user_id=user_id, skip=0, limit=1
                )

                business_info_list = business_info_response.get("responseData", [])
                if business_info_list and len(business_info_list) > 0:
                    business_context = business_info_list[0].get("business_summary")
                    source = "lead_business_info"
                    print(f"✅ Found LeadBusinessInfo data: {business_context[:100]}...")

            # If still no context found, return error
            if not business_context:
                return UriResponse.custom_response(
                    "No business context provided and no onboarding data found. Please complete your business details in onboarding or provide a description.",
                    400,
                    False
                )
        
        print(f"🤖 Generating job keywords from context (source: {source})")
        
        # Generate job keywords using AI
        result = await JobKeywordGenerationService.generate_job_keywords(business_context)
        
        # Validate and clean keywords
        valid_keywords = JobKeywordGenerationService.validate_job_keywords(result.job_keywords)
        
        response_data = {
            "job_keywords": valid_keywords,
            "solution_context": business_context,
            "source": source,
            "reasoning": result.reasoning
        }
        
        print(f"✅ Generated {len(valid_keywords)} job keywords: {', '.join(valid_keywords)}")
        
        return UriResponse.custom_response(
            "Job keywords generated successfully",
            200,
            True,
            response_data
        )
        
    except Exception as e:
        print(f"❌ Error generating job keywords: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return UriResponse.custom_response(
            f"Error generating job keywords: {str(e)}",
            500,
            False
        )



@router.post("/find-decision-makers")
async def find_decision_makers(
    lead_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    Find decision-makers for a job board signal
    PRD Section 8: Decision-Maker Connection Feature
    """
    from app.repository.LeadRepository import LeadRepository
    from app.services.DecisionMakerMappingService import DecisionMakerMappingService
    from app.core.helpers.apollo_helper import ApolloHelper
    from app.services.uri_microservices.UriBackendService import UriBackendService
    
    lead_response = await LeadRepository.get_lead_by_id(db, lead_id)
    
    if lead_response["responseCode"] != 200:
        return UriResponse.custom_response("Lead not found", 404, False)
    
    lead = lead_response["responseData"]
    
    # PRD Section 16: Eligibility checks
    hiring_company = lead.get("hiring_company")
    company_confidence = lead.get("company_confidence", 0.0)
    problem_solution_match = lead.get("problem_solution_match", 0.0)
    job_title = lead.get("job_title_field")
    
    if not hiring_company:
        return UriResponse.custom_response(
            "Company name is missing",
            400,
            False,
            {"reason": "missing_company_name"}
        )
    
    if company_confidence < 0.5:
        return UriResponse.custom_response(
            "Company identity could not be verified",
            400,
            False,
            {"reason": "low_company_confidence"}
        )
    
    if problem_solution_match < 0.3:
        return UriResponse.custom_response(
            "Problem-solution match too low",
            400,
            False
        )
    
    # Map job title to decision-maker titles
    decision_maker_titles = await DecisionMakerMappingService.map_job_to_decision_makers(job_title)
    
    if not decision_maker_titles:
        return UriResponse.custom_response("No decision-makers found", 404, False)
    
    # Search Apollo for decision-makers at this company
    apollo_params = {
        "person_titles": decision_maker_titles,
        "q_organization_name": hiring_company,
        "page": 1,
        "per_page": 3
    }
    
    try:
        apollo_results = await UriBackendService.search_apollo_persons(apollo_params)
        
        if not apollo_results or apollo_results.get("responseCode") != 200:
            return UriResponse.custom_response("No contacts found", 404, False)
        
        contacts = apollo_results.get("responseData", {}).get("people", [])
        
        # Filter out recruiters/HR
        excluded = ["recruiter", "recruiting", "talent acquisition", "hr ", "human resources"]
        filtered = [c for c in contacts if not any(k in c.get("title", "").lower() for k in excluded)]
        
        return UriResponse.custom_response(
            "Decision-makers found",
            200,
            True,
            {
                "decision_makers": filtered[:3],
                "searched_titles": decision_maker_titles,
                "company": hiring_company
            }
        )
    except Exception as e:
        return UriResponse.custom_response(f"Error: {str(e)}", 500, False)


@router.get("/user-business-details/{user_id}")
async def get_user_business_details(user_id: str):
    """
    Get user's business details from uri-backend for job keyword generation.

    Returns businessDetails object containing:
    - whatYouSell: What the user's business sells/does
    - industry: User's industry
    - businessName: Business name
    - etc.
    """
    try:
        business_details = await UriBackendService.get_user_business_details(user_id)

        if business_details:
            return UriResponse.custom_response(
                "Business details retrieved successfully",
                200,
                True,
                business_details
            )
        else:
            return UriResponse.custom_response(
                "Business details not found for user",
                404,
                False
            )
    except Exception as e:
        print(f"Error getting user business details: {str(e)}")
        import traceback
        traceback.print_exc()
        return UriResponse.custom_response(
            f"Error retrieving business details: {str(e)}",
            500,
            False
        )


# PRD Section 8: Find decision-makers for job signal leads
@router.post("/job-boards/{lead_id}/find-decision-makers")
async def find_decision_makers_for_job_signal(
    lead_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    Find decision-makers at the company from a job signal
    PRD Section 8: Decision-Maker Connection Feature

    Returns 1-3 relevant decision-makers with contact details (name, title, email, phone, LinkedIn)
    """
    try:
        print(f"🔍 DECISION MAKER REQUEST - Lead ID: {lead_id}")

        # Get the job signal lead
        lead_response = await LeadRepository.get_lead_by_id(db, lead_id)

        if lead_response["responseCode"] != 200:
            print("❌ Lead not found")
            return UriResponse.custom_response("Lead not found", 404, False)

        # Extract the actual lead data from the response wrapper
        lead = lead_response["responseData"]

        print(f"📋 Lead found: {lead is not None}")
        if lead:
            print(f"   lead_source: {lead.get('lead_source')}")
            print(f"   hiring_company: {lead.get('hiring_company')}")
            print(f"   job_source: {lead.get('job_source')}")

        # Verify this is a job board signal
        lead_source = lead.get("lead_source")
        print(f"🔎 Checking lead_source: '{lead_source}' == '{LeadSourceEnum.JOB_BOARDS}' ?")

        if lead_source != LeadSourceEnum.JOB_BOARDS:
            print(f"❌ Not a job board lead! lead_source='{lead_source}'")
            return UriResponse.custom_response(
                "This endpoint only works for job board signals",
                400,
                False
            )

        # Extract company name and job title
        company_name = lead.get("hiring_company") or lead.get("company_name")
        job_title = lead.get("job_title_field") or lead.get("job_title")

        if not company_name:
            return UriResponse.custom_response(
                "Company name not found in lead",
                400,
                False
            )

        # Check company confidence (PRD Section 16)
        company_confidence = lead.get("company_confidence", 1.0)
        if company_confidence < 0.5:
            return UriResponse.custom_response(
                "Company confidence too low for decision-maker lookup",
                400,
                False,
                {"company_confidence": company_confidence}
            )

        # Get decision-maker titles from AI analysis (stored in lead)
        # Or map from job title using JobSignalAnalysisService logic
        from app.services.JobSignalAnalysisService import JobSignalAnalysisService

        # Use AI-generated target_seniorities if available, otherwise map from job title
        decision_maker_titles = []
        if hasattr(lead, 'target_seniorities') and lead.target_seniorities:
            decision_maker_titles = lead.target_seniorities
        else:
            # Fallback: map job title to decision-maker titles
            # Basic mapping (can be enhanced)
            job_title_lower = (job_title or "").lower()
            if any(keyword in job_title_lower for keyword in ["devops", "engineer", "developer", "sre"]):
                decision_maker_titles = ["CTO", "VP Engineering", "Head of Engineering", "Director of Engineering"]
            elif any(keyword in job_title_lower for keyword in ["marketing", "growth"]):
                decision_maker_titles = ["CMO", "VP Marketing", "Head of Marketing"]
            elif any(keyword in job_title_lower for keyword in ["sales", "business development"]):
                decision_maker_titles = ["VP Sales", "Head of Sales", "Chief Revenue Officer"]
            elif any(keyword in job_title_lower for keyword in ["data", "analyst", "analytics"]):
                decision_maker_titles = ["Head of Data", "VP Analytics", "Chief Data Officer"]
            elif any(keyword in job_title_lower for keyword in ["operations", "office manager"]):
                decision_maker_titles = ["COO", "Head of Operations", "VP Operations"]
            else:
                # Default fallback
                decision_maker_titles = ["CEO", "COO", "Founder"]

        print(f"🔍 Finding decision-makers at {company_name} with titles: {decision_maker_titles}")

        # Call Apollo API
        try:
            decision_makers = await ApolloService.find_decision_makers(
                company_name=company_name,
                job_titles=decision_maker_titles,
                max_results=3
            )

            # Success - return the decision-makers
            return UriResponse.custom_response(
                f"Found {len(decision_makers)} decision-maker(s)",
                200,
                True,
                {
                    "decision_makers": decision_makers,
                    "company_name": company_name,
                    "job_title": job_title
                }
            )

        except Exception as apollo_error:
            # Apollo API failed - return user-friendly error
            error_message = str(apollo_error)
            print(f"❌ Apollo API error: {error_message}")

            # Return user-friendly message (don't expose internal API issues)
            return UriResponse.custom_response(
                "Decision-maker search is temporarily unavailable. Please try again later.",
                503,  # Service Unavailable
                False,
                {
                    "company_name": company_name,
                    "suggestion": f"You can manually search for contacts at {company_name} on LinkedIn."
                }
            )

    except Exception as e:
        print(f"❌ Error finding decision-makers: {str(e)}")
        import traceback
        traceback.print_exc()
        return UriResponse.custom_response(
            "An error occurred while processing your request. Please try again later.",
            500,
            False
        )

# Validate search context to detect business-keyword mismatch
@router.post("/validate-search-context")
async def validate_search_context(
    request: Dict[str, Any]
):
    """
    Validates if user's search keywords align with their business solution.
    Prevents irrelevant lead generation by detecting mismatches like:
    - Selling laptops but searching for "skin care"
    - Selling marketing software but searching for "plumbing issues"

    Request body:
    {
        "solution_context": "What user sells",
        "category_context": "What people are complaining about (social platforms)",
        "social_keywords": ["keyword1", "keyword2"],
        "job_keywords": ["keyword1", "keyword2"],
        "has_social_platforms": true,
        "has_job_boards": true
    }

    Returns:
    {
        "is_valid": bool,
        "match_score": 0.0-1.0,
        "social_platform_match": 0.0-1.0,
        "job_board_match": 0.0-1.0,
        "recommendation": "proceed" | "use_only_social" | "use_only_job_boards" | "update_search",
        "reasoning": "Explanation",
        "suggested_social_keywords": ["better", "keywords"]
    }
    """
    from app.services.SearchKeywordValidationService import SearchKeywordValidationService

    try:
        solution_context = request.get("solution_context", "")
        category_context = request.get("category_context")
        social_keywords = request.get("social_keywords", [])
        job_keywords = request.get("job_keywords", [])
        has_social_platforms = request.get("has_social_platforms", False)
        has_job_boards = request.get("has_job_boards", False)

        # Validate
        validation_result = await SearchKeywordValidationService.validate_search_context(
            solution_context=solution_context,
            category_context=category_context,
            social_keywords=social_keywords,
            job_keywords=job_keywords,
            has_social_platforms=has_social_platforms,
            has_job_boards=has_job_boards
        )

        return UriResponse.custom_response(
            "Search context validated",
            200,
            True,
            validation_result
        )

    except Exception as e:
        print(f"❌ Validation endpoint error: {e}")
        # Fail open - allow search to proceed
        return UriResponse.custom_response(
            "Validation unavailable, proceeding with search",
            200,
            True,
            {
                "is_valid": True,
                "match_score": 0.5,
                "social_platform_match": 0.5,
                "job_board_match": 0.8,
                "recommendation": "proceed",
                "reasoning": "Validation service unavailable",
                "suggested_social_keywords": []
            }
        )


# ============================================
# SPAM LEAD ENDPOINTS (NEW - Spam Visibility Feature)
# PRD: Lead Gen Enhancement - Spam Visibility & Lead Reclassification
# These endpoints allow users to view and manage filtered leads
# ============================================

@router.get("/spam-leads", tags=["Spam Leads"])
async def get_spam_leads(
    user_id: str,
    lead_form_snapshot_id: Optional[str] = None,
    filter_stage: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    Get spam leads for a user (PRD Section 3.4)

    Spam = Analyzed but Unqualified Items
    These are posts/jobs that were fetched and analyzed but did not meet qualification criteria.

    Args:
        user_id: User ID
        lead_form_snapshot_id: Filter by specific lead form (PRD 4.7: Spam scoped per form)
        filter_stage: Optional filter by stage ("job_board_ai", "intent_analysis", etc.)
        page: Page number (1-indexed)
        page_size: Items per page (default 50)

    Returns:
        Paginated list of spam leads with reasons for disqualification
    """
    from app.repository.SpamLeadRepository import SpamLeadRepository

    try:
        # Filter out "undefined" strings from frontend
        clean_snapshot_id = None if lead_form_snapshot_id == "undefined" else lead_form_snapshot_id
        clean_filter_stage = None if filter_stage == "undefined" else filter_stage

        print(f"🔍 [get_spam_leads] Request params: user_id={user_id}, lead_form_snapshot_id={clean_snapshot_id}, filter_stage={clean_filter_stage}, page={page}, page_size={page_size}")

        spam_leads, total = await SpamLeadRepository.get_spam_leads_by_user(
            db, user_id, clean_snapshot_id, clean_filter_stage, page, page_size
        )

        print(f"✅ [get_spam_leads] Retrieved {len(spam_leads)} spam leads out of {total} total")
        if len(spam_leads) > 0:
            print(f"📋 [get_spam_leads] First spam lead sample: {spam_leads[0].get('spam_id', 'no_id')}, spam_reason: {spam_leads[0].get('spam_reason', 'no_reason')}")

        response = UriResponse.get_paged_data_response(
            entity_name="Spam lead",
            data=spam_leads,
            total=total,
            page=page,
            page_size=page_size,
            message="Spam leads retrieved successfully"
        )

        print(f"📦 [get_spam_leads] Response structure: status={response.get('status')}, responseCode={response.get('responseCode')}, data_count={len(response.get('responseData', {}).get('data', []))}")

        return response

    except Exception as e:
        print(f"Error retrieving spam leads: {str(e)}")
        import traceback
        traceback.print_exc()
        return UriResponse.custom_response(
            f"Error retrieving spam leads: {str(e)}",
            500,
            False
        )


@router.post("/spam-leads/{spam_id}/promote", tags=["Spam Leads"])
async def promote_spam_to_lead(
    spam_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    Promote spam lead to qualified leads (PRD Section 3.5 - "Add to Leads")

    Allows users to recover false negatives by manually promoting spam items to active leads.

    Args:
        spam_id: Spam lead ID

    Returns:
        Success response with promoted lead data
    """
    from app.repository.SpamLeadRepository import SpamLeadRepository
    from app.repository.LeadRepository import LeadRepository
    from app.domain.schemas.lead_schema import LeadCreate

    try:
        # Get spam lead
        spam_lead = await SpamLeadRepository.get_spam_lead_by_id(db, spam_id)

        if not spam_lead:
            return UriResponse.custom_response("Spam lead not found", 404, False)

        # Extract original lead data
        original_data = spam_lead.get("original_lead_data")
        if not original_data:
            return UriResponse.custom_response("Original lead data not found in spam entry", 400, False)

        # Recreate LeadCreate object from original data
        lead = LeadCreate(**original_data)

        # Save to main leads collection
        save_result = await LeadRepository.create_lead(db, lead)

        # Mark spam as promoted (keeps record for analytics)
        await SpamLeadRepository.promote_spam_to_lead(db, spam_id)

        # save_result is already a formatted dict from LeadRepository.create_lead
        return save_result

    except Exception as e:
        print(f"Error promoting spam lead: {str(e)}")
        import traceback
        traceback.print_exc()
        return UriResponse.custom_response(
            f"Error promoting spam lead: {str(e)}",
            500,
            False
        )


@router.post("/leads/{lead_id}/move-to-spam", tags=["Spam Leads"])
async def move_lead_to_spam(
    lead_id: str,
    spam_reason: str = "Manually moved by user",
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    Move qualified lead to spam (PRD Section 3.6 - Reverse action)

    Allows users to demote active leads that turn out to be false positives.

    Args:
        lead_id: Lead ID to move to spam
        spam_reason: Reason for moving to spam

    Returns:
        Success response
    """
    from app.repository.SpamLeadRepository import SpamLeadRepository
    from app.repository.LeadRepository import LeadRepository

    try:
        # Get existing lead
        lead_response = await LeadRepository.get_lead_by_id(db, lead_id)

        if lead_response["responseCode"] != 200:
            return UriResponse.custom_response("Lead not found", 404, False)

        lead_data = lead_response["responseData"]

        # Extract user_id from lead
        user_id = lead_data.get("assigned_to") or lead_data.get("user_id", "")

        # Create spam entry from lead
        spam_entry = await SpamLeadRepository.move_lead_to_spam(
            db=db,
            lead_data=lead_data,
            spam_reason=spam_reason,
            user_id=user_id
        )

        # Delete from leads collection
        delete_result = await LeadRepository.delete_lead(db, lead_id)

        if delete_result["responseCode"] == 200:
            return UriResponse.update_response(
                entity_name="Lead",
                data={"spam_id": spam_entry.get("spam_id"), "deleted_lead_id": lead_id},
                message="Lead moved to spam"
            )
        else:
            return UriResponse.custom_response("Failed to delete lead after moving to spam", 500, False)

    except Exception as e:
        print(f"Error moving lead to spam: {str(e)}")
        import traceback
        traceback.print_exc()
        return UriResponse.custom_response(
            f"Error moving lead to spam: {str(e)}",
            500,
            False
        )


@router.get("/spam-leads/stats", tags=["Spam Leads"])
async def get_spam_stats(
    user_id: str,
    lead_form_snapshot_id: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    Get spam statistics for user/form

    Returns counts by filter stage, spam reason, and user actions.

    Args:
        user_id: User ID
        lead_form_snapshot_id: Optional form filter

    Returns:
        Statistics about spam leads
    """
    from app.repository.SpamLeadRepository import SpamLeadRepository

    try:
        stats = await SpamLeadRepository.get_spam_stats(db, user_id, lead_form_snapshot_id)

        return UriResponse.get_single_data_response(
            entity_name="Spam statistics",
            data=stats,
            message="Spam statistics retrieved successfully"
        )

    except Exception as e:
        print(f"Error retrieving spam stats: {str(e)}")
        import traceback
        traceback.print_exc()
        return UriResponse.custom_response(
            f"Error retrieving spam stats: {str(e)}",
            500,
            False
        )


@router.patch("/spam-leads/{spam_id}/notes", tags=["Spam Leads"])
async def update_spam_notes(
    spam_id: str,
    user_notes: str,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    Add or update user notes on spam lead

    Allows users to document why they reviewed/promoted/dismissed an item.

    Args:
        spam_id: Spam lead ID
        user_notes: User's notes

    Returns:
        Success response
    """
    from app.repository.SpamLeadRepository import SpamLeadRepository

    try:
        success = await SpamLeadRepository.update_spam_notes(db, spam_id, user_notes)

        if success:
            return UriResponse.update_response(
                entity_name="Spam notes",
                data={"spam_id": spam_id},
                message="Spam notes updated"
            )
        else:
            return UriResponse.custom_response("Spam lead not found", 404, False)

    except Exception as e:
        print(f"Error updating spam notes: {str(e)}")
        return UriResponse.custom_response(
            f"Error updating spam notes: {str(e)}",
            500,
            False
        )
